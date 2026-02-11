"""PacketOrchestrator — integrates registry, ecoregion, and congress modules.

Coordinates Tribe name resolution, ecoregion classification, and
congressional delegation lookup into a unified TribePacketContext.
Called from CLI via ``--prep-packets --tribe <name>`` or ``--prep-packets --all-tribes``.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from dataclasses import asdict

from src.packets.change_tracker import PacketChangeTracker
from src.packets.context import TribePacketContext
from src.packets.congress import CongressionalMapper
from src.packets.docx_engine import DocxEngine
from src.packets.ecoregion import EcoregionMapper
from src.packets.economic import EconomicImpactCalculator
from src.packets.registry import TribalRegistry
from src.paths import (
    AWARD_CACHE_DIR,
    GRAPH_SCHEMA_PATH,
    HAZARD_PROFILES_DIR,
    PACKET_STATE_DIR,
    PACKETS_OUTPUT_DIR,
    PROJECT_ROOT,
)
from src.packets.relevance import ProgramRelevanceFilter

logger = logging.getLogger(__name__)

_MAX_CACHE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB


class PacketOrchestrator:
    """Orchestrates Tribe packet generation from registry, ecoregion, and congress modules.

    Usage::

        config = load_config()
        programs = load_programs()
        orch = PacketOrchestrator(config, programs)
        orch.run_single_tribe("Navajo Nation")
        orch.run_all_tribes()
    """

    def __init__(self, config: dict, programs: list[dict]) -> None:
        """Initialize the orchestrator with config and program inventory.

        Args:
            config: Application configuration dict (with ``packets`` section).
            programs: List of program dicts from program_inventory.json.
        """
        self.config = config
        self.programs = {p["id"]: p for p in programs}
        self.registry = TribalRegistry(config)
        self.congress = CongressionalMapper(config)
        self.ecoregion = EcoregionMapper(config)

        # Phase 6: Award and hazard cache directories
        packets_cfg = config.get("packets", {})
        raw = packets_cfg.get("awards", {}).get("cache_dir")
        self.award_cache_dir = Path(raw) if raw else AWARD_CACHE_DIR
        if not self.award_cache_dir.is_absolute():
            self.award_cache_dir = PROJECT_ROOT / self.award_cache_dir

        raw = packets_cfg.get("hazards", {}).get("cache_dir")
        self.hazard_cache_dir = Path(raw) if raw else HAZARD_PROFILES_DIR
        if not self.hazard_cache_dir.is_absolute():
            self.hazard_cache_dir = PROJECT_ROOT / self.hazard_cache_dir

        # Phase 7: DOCX generation components
        self.economic_calculator = EconomicImpactCalculator()
        self.relevance_filter = ProgramRelevanceFilter(self.programs)

    def run_single_tribe(self, tribe_name: str) -> None:
        """Resolve a single Tribe by name and display its packet context.

        Handles three resolution outcomes:
          - Single dict (exact or unambiguous match): proceed directly.
          - List of dicts (ambiguous/fuzzy): auto-select best match with warning.
          - None (no match): display fuzzy suggestions and exit.

        Args:
            tribe_name: Tribe name or partial name to resolve.
        """
        result = self.registry.resolve(tribe_name)

        if result is None:
            # No match at all -- show fuzzy suggestions
            print(f"\nError: No Tribe found matching '{tribe_name}'.")
            suggestions = self.registry.fuzzy_search(tribe_name, limit=5)
            if suggestions:
                print("\nDid you mean one of these?")
                for s in suggestions:
                    score = s.get("_match_score", 0)
                    print(f"  - {s['name']} (match: {score:.0f}%)")
            else:
                print("No similar names found in the registry.")
            sys.exit(1)

        if isinstance(result, list):
            # Multiple matches -- auto-select first (best), show alternatives
            tribe = result[0]
            has_scores = "_match_score" in tribe
            if has_scores:
                print(f"\nFuzzy match: using '{tribe['name']}' "
                      f"(score: {tribe['_match_score']:.0f}%)")
                if len(result) > 1:
                    print("Other candidates:")
                    for alt in result[1:]:
                        print(f"  - {alt['name']} "
                              f"(score: {alt['_match_score']:.0f}%)")
            else:
                print(f"\nMultiple matches for '{tribe_name}' -- "
                      f"using '{tribe['name']}'")
                if len(result) > 1:
                    print("Other matches:")
                    for alt in result[1:]:
                        print(f"  - {alt['name']}")
        else:
            # Single exact/unambiguous match
            tribe = result

        context = self._build_context(tribe)
        self._display_tribe_info(context)

        # After displaying info, generate DOCX if configured
        if self.config.get("packets", {}).get("docx", {}).get("enabled", True):
            try:
                path = self.generate_packet_from_context(context, tribe)
                print(f"\n  DOCX packet generated: {path}")
            except Exception as exc:
                logger.error("Failed to generate DOCX for %s: %s", tribe["name"], exc)
                print(f"\n  DOCX generation failed: {exc}")

    def run_all_tribes(self) -> dict:
        """Generate DOCX packets for all Tribes + strategic overview.

        Returns:
            dict with keys: success, errors, total, duration_s
        """
        import gc
        import time

        all_tribes = self.registry.get_all()
        total = len(all_tribes)
        start = time.monotonic()
        success_count = 0
        error_count = 0
        error_tribes: list[str] = []

        for i, tribe in enumerate(all_tribes, 1):
            elapsed = time.monotonic() - start
            print(f"[{i}/{total}] {tribe['name']}...", end="", flush=True)
            try:
                context = self._build_context(tribe)
                self.generate_packet_from_context(context, tribe)
                print(f" OK ({elapsed:.0f}s)")
                success_count += 1
            except Exception as exc:
                print(f" ERROR: {exc}")
                logger.error("Failed: %s: %s", tribe["name"], exc)
                error_count += 1
                error_tribes.append(tribe["name"])
            finally:
                if i % 25 == 0:
                    gc.collect()

        # Strategic overview
        print("\nGenerating Strategic Overview...", end="", flush=True)
        try:
            overview_path = self.generate_strategic_overview()
            print(f" OK ({overview_path})")
        except Exception as exc:
            print(f" ERROR: {exc}")
            logger.error("Strategic overview failed: %s", exc)

        duration = time.monotonic() - start
        print("\n--- Batch Complete ---")
        print(f"Total: {total} | Success: {success_count} | Errors: {error_count}")
        print(f"Duration: {duration:.0f}s")
        if error_tribes:
            print(f"Failed: {', '.join(error_tribes[:10])}")
            if len(error_tribes) > 10:
                print(f"  ... and {len(error_tribes) - 10} more")

        return {
            "success": success_count,
            "errors": error_count,
            "total": total,
            "duration_s": duration,
        }

    def _load_tribe_cache(self, cache_dir: Path, tribe_id: str) -> dict:
        """Load a per-Tribe JSON cache file. Returns empty dict if not found.

        Args:
            cache_dir: Directory containing per-Tribe JSON cache files.
            tribe_id: Tribe identifier (used as filename stem).

        Returns:
            Parsed JSON dict, or empty dict on missing/corrupt files.
        """
        cache_file = cache_dir / f"{tribe_id}.json"
        if not cache_file.exists():
            return {}
        try:
            file_size = cache_file.stat().st_size
        except OSError:
            return {}
        if file_size > _MAX_CACHE_SIZE_BYTES:
            logger.warning(
                "Cache file %s exceeds size limit (%d bytes > %d), skipping",
                cache_file, file_size, _MAX_CACHE_SIZE_BYTES,
            )
            return {}
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load cache %s: %s", cache_file, exc)
            return {}

    def _build_context(self, tribe: dict) -> TribePacketContext:
        """Assemble a TribePacketContext from registry, ecoregion, and congress data.

        Args:
            tribe: Tribe dict from the registry.

        Returns:
            Fully populated TribePacketContext.
        """
        tribe_id = tribe["tribe_id"]
        states = tribe.get("states", [])

        # Ecoregion classification
        ecoregions = self.ecoregion.classify(states)

        # Congressional delegation
        delegation = self.congress.get_delegation(tribe_id)
        districts = delegation.get("districts", []) if delegation else []
        senators = delegation.get("senators", []) if delegation else []
        representatives = delegation.get("representatives", []) if delegation else []

        # Award data (Phase 6)
        award_data = self._load_tribe_cache(self.award_cache_dir, tribe_id)
        awards = award_data.get("awards", [])

        # Hazard profile (Phase 6)
        hazard_data = self._load_tribe_cache(self.hazard_cache_dir, tribe_id)
        hazard_profile = hazard_data.get("sources", {})

        context = TribePacketContext(
            tribe_id=tribe_id,
            tribe_name=tribe["name"],
            states=states,
            ecoregions=ecoregions,
            bia_code=tribe.get("bia_code", ""),
            epa_id=tribe.get("epa_id", tribe_id),
            districts=districts,
            senators=senators,
            representatives=representatives,
            awards=awards,
            hazard_profile=hazard_profile,
            generated_at=datetime.now(timezone.utc).isoformat(),
            congress_session=self.congress.get_congress_session(),
        )

        logger.debug("Built context for %s: %d districts, %d senators, %d reps, "
                      "%d awards, %d hazard sources",
                      tribe["name"], len(districts), len(senators),
                      len(representatives), len(awards),
                      len(hazard_profile))
        return context

    def _display_tribe_info(self, context: TribePacketContext) -> None:
        """Display formatted Tribe identity, delegation, awards, and hazards.

        Args:
            context: The TribePacketContext to display.
        """
        sep = "=" * 72
        print(f"\n{sep}")
        print(f"  TRIBE: {context.tribe_name}")
        print(sep)

        # Identity
        print(f"\n  ID:         {context.tribe_id}")
        print(f"  BIA Code:   {context.bia_code or 'N/A'}")
        print(f"  States:     {', '.join(context.states) if context.states else 'N/A'}")
        print(f"  Ecoregions: {', '.join(context.ecoregions) if context.ecoregions else 'N/A'}")

        # Ecoregion priority programs
        if context.ecoregions:
            print("\n  Priority Programs by Ecoregion:")
            for eco in context.ecoregions:
                programs = self.ecoregion.get_priority_programs(eco)
                prog_names = []
                for pid in programs:
                    prog = self.programs.get(pid)
                    prog_names.append(prog["name"] if prog else pid)
                print(f"    {eco}: {', '.join(prog_names)}")

        # Congressional delegation
        print(f"\n  Congressional Delegation (Session {context.congress_session}):")

        if not context.districts and not context.senators and not context.representatives:
            print("    No congressional delegation data available.")
        else:
            # Districts
            if context.districts:
                print(f"\n  Districts ({len(context.districts)}):")
                for d in context.districts:
                    overlap = d.get("overlap_pct")
                    overlap_str = f" ({overlap:.1f}% overlap)" if overlap is not None else ""
                    print(f"    {d['district']}{overlap_str}")

            # Senators
            if context.senators:
                print(f"\n  Senators ({len(context.senators)}):")
                for s in context.senators:
                    name_str = s.get("formatted_name", s.get("name", "Unknown"))
                    committees = s.get("committees", [])
                    print(f"    {name_str}")
                    if committees:
                        comm_strs = []
                        for c in committees:
                            role = c.get("title") or c.get("role", "")
                            role_str = f" [{role}]" if role and role != "member" else ""
                            comm_strs.append(f"{c.get('committee_name', c.get('committee_id', ''))}{role_str}")
                        print(f"      Committees: {'; '.join(comm_strs)}")

            # Representatives
            if context.representatives:
                print(f"\n  Representatives ({len(context.representatives)}):")
                for r in context.representatives:
                    name_str = r.get("formatted_name", r.get("name", "Unknown"))
                    committees = r.get("committees", [])
                    print(f"    {name_str}")
                    if committees:
                        comm_strs = []
                        for c in committees:
                            role = c.get("title") or c.get("role", "")
                            role_str = f" [{role}]" if role and role != "member" else ""
                            comm_strs.append(f"{c.get('committee_name', c.get('committee_id', ''))}{role_str}")
                        print(f"      Committees: {'; '.join(comm_strs)}")

        # Award history (Phase 6)
        self._display_award_summary(context)

        # Climate hazard profile (Phase 6)
        self._display_hazard_summary(context)

        print(f"\n  Generated: {context.generated_at}")
        print(sep)

    def _display_award_summary(self, context: TribePacketContext) -> None:
        """Display award history summary.

        Args:
            context: The TribePacketContext with awards data.
        """
        print("\n  Award History:")
        if not context.awards:
            print("    No federal climate resilience awards in tracked programs.")
            print("    First-time applicant opportunity.")
            return

        total_obligation = sum(a.get("obligation", 0.0) for a in context.awards)
        count = len(context.awards)
        print(f"    Total Obligation: ${total_obligation:,.0f} across {count} awards")

        # Group by program/CFDA
        program_totals: dict[str, float] = {}
        for award in context.awards:
            prog = award.get("program_id") or award.get("cfda", "Unknown")
            program_totals[prog] = program_totals.get(prog, 0.0) + award.get("obligation", 0.0)

        if program_totals:
            prog_strs = []
            for prog, total in sorted(program_totals.items(), key=lambda x: -x[1]):
                prog_strs.append(f"{prog} (${total:,.0f})")
            print(f"    Programs: {', '.join(prog_strs)}")

    def _display_hazard_summary(self, context: TribePacketContext) -> None:
        """Display climate hazard profile summary.

        Args:
            context: The TribePacketContext with hazard_profile data.
        """
        print("\n  Climate Hazard Profile:")

        if not context.hazard_profile:
            print("    No hazard profile data available.")
            return

        # FEMA NRI section
        nri = context.hazard_profile.get("fema_nri", {})
        composite = nri.get("composite", {})

        risk_rating = composite.get("risk_rating", "")
        risk_score = composite.get("risk_score", 0.0)
        sovi_rating = composite.get("sovi_rating", "")
        sovi_score = composite.get("sovi_score", 0.0)

        if risk_rating or risk_score:
            print(f"    Overall Risk: {risk_rating or 'N/A'} (score: {risk_score:.1f})")
        if sovi_rating or sovi_score:
            print(f"    Social Vulnerability: {sovi_rating or 'N/A'} (score: {sovi_score:.1f})")

        # Top hazards
        top_hazards = nri.get("top_hazards", [])
        if top_hazards:
            print("    Top Hazards:")
            for i, h in enumerate(top_hazards, 1):
                haz_type = h.get("type", "Unknown")
                haz_score = h.get("risk_score", 0.0)
                haz_eal = h.get("eal_total", 0.0)
                print(f"      {i}. {haz_type} (score: {haz_score:.1f}, EAL: ${haz_eal:,.0f})")

        # USFS wildfire section
        usfs = context.hazard_profile.get("usfs_wildfire", {})
        if usfs:
            risk_to_homes = usfs.get("risk_to_homes", 0.0)
            likelihood = usfs.get("wildfire_likelihood", 0.0)
            if risk_to_homes or likelihood:
                print(f"    Wildfire Risk (USFS): Risk to Homes: {risk_to_homes:.2f}, "
                      f"Likelihood: {likelihood:.4f}")

    # ------------------------------------------------------------------
    # Phase 7: DOCX generation
    # ------------------------------------------------------------------

    def generate_packet(self, tribe_name: str) -> Path | None:
        """Generate a complete DOCX advocacy packet for a single Tribe.

        Resolves the Tribe by name, builds context, computes economic
        impact, filters relevant programs, and assembles the full DOCX
        document.

        Args:
            tribe_name: Tribe name or partial name to resolve.

        Returns:
            Path to generated .docx file, or None if Tribe not found.
        """
        result = self.registry.resolve(tribe_name)

        if result is None:
            logger.warning("No Tribe found matching '%s'", tribe_name)
            return None

        if isinstance(result, list):
            tribe = result[0]
            logger.info(
                "Fuzzy match: using '%s' for '%s'", tribe["name"], tribe_name
            )
        else:
            tribe = result

        context = self._build_context(tribe)
        return self.generate_packet_from_context(context, tribe)

    def generate_packet_from_context(
        self, context: TribePacketContext, tribe: dict
    ) -> Path:
        """Generate a DOCX packet from an already-built context.

        Shared implementation between generate_packet() (standalone) and
        run_single_tribe() (display + generate).

        Args:
            context: Fully populated TribePacketContext.
            tribe: Original tribe dict from registry.

        Returns:
            Path to generated .docx file.
        """
        # Compute economic impact
        economic_summary = self.economic_calculator.compute(
            tribe_id=context.tribe_id,
            tribe_name=context.tribe_name,
            awards=context.awards,
            districts=context.districts,
            programs=self.programs,
        )

        # Store economic impact in context
        context.economic_impact = asdict(economic_summary)

        # Filter relevant programs
        relevant = self.relevance_filter.filter_for_tribe(
            hazard_profile=context.hazard_profile,
            ecoregions=context.ecoregions,
            ecoregion_mapper=self.ecoregion,
        )

        # Get omitted programs
        omitted = self.relevance_filter.get_omitted_programs(relevant)

        # Load structural asks
        structural_asks = self._load_structural_asks()

        # Change tracking (OPS-03)
        raw_state = self.config.get("packets", {}).get("state_dir")
        state_dir = Path(raw_state) if raw_state else PACKET_STATE_DIR
        if not state_dir.is_absolute():
            state_dir = PROJECT_ROOT / state_dir
        tracker = PacketChangeTracker(state_dir=state_dir)
        previous_state = tracker.load_previous(context.tribe_id)
        current_state = tracker.compute_current(context, self.programs)

        changes: list[dict] = []
        previous_date: str | None = None
        if previous_state is not None:
            changes = tracker.diff(previous_state, current_state)
            previous_date = previous_state.get("generated_at")

        # Create engine and generate document
        engine = DocxEngine(self.config, self.programs)
        path = engine.generate(
            context=context,
            relevant_programs=relevant,
            economic_summary=economic_summary,
            structural_asks=structural_asks,
            omitted_programs=omitted,
            changes=changes,
            previous_date=previous_date,
        )

        # Persist current state after successful generation
        tracker.save_current(context.tribe_id, current_state)

        logger.info("Generated packet for %s: %s", context.tribe_name, path)
        return path

    def _load_structural_asks(self) -> list[dict]:
        """Load structural asks from graph_schema.json.

        Returns:
            List of structural ask dicts, or empty list on error.
        """
        graph_path = GRAPH_SCHEMA_PATH
        if not graph_path.exists():
            return []
        try:
            file_size = graph_path.stat().st_size
        except OSError:
            return []
        if file_size > _MAX_CACHE_SIZE_BYTES:
            logger.warning(
                "Graph schema %s exceeds size limit (%d bytes > %d), skipping",
                graph_path, file_size, _MAX_CACHE_SIZE_BYTES,
            )
            return []
        try:
            with open(graph_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("structural_asks", [])
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load graph schema: %s", exc)
            return []

    def generate_strategic_overview(self) -> Path:
        """Generate the shared strategic overview DOCX (Document 2).

        Creates a single STRATEGIC-OVERVIEW.docx covering all 16 programs,
        7 ecoregions, and the full structural policy framework. This document
        is generated once (not per-Tribe).

        Uses lazy import of StrategicOverviewGenerator to avoid circular
        imports and keep the module lightweight when strategic overview
        is not needed.

        Returns:
            Path to the generated STRATEGIC-OVERVIEW.docx file.
        """
        from src.packets.strategic_overview import StrategicOverviewGenerator

        raw_out = self.config.get("packets", {}).get("output_dir")
        output_dir = Path(raw_out) if raw_out else PACKETS_OUTPUT_DIR
        if not output_dir.is_absolute():
            output_dir = PROJECT_ROOT / output_dir
        generator = StrategicOverviewGenerator(self.config, self.programs)
        path = generator.generate(output_dir)

        logger.info("Generated strategic overview: %s", path)
        return path
