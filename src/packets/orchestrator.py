"""PacketOrchestrator — integrates registry, ecoregion, and congress modules.

Coordinates Tribe name resolution, ecoregion classification, and
congressional delegation lookup into a unified TribePacketContext.
Called from CLI via ``--prep-packets --tribe <name>`` or ``--prep-packets --all-tribes``.

Supports multi-document generation per Tribe:
  - Doc A (internal strategy) to ``internal/`` subdirectory
  - Doc B (congressional overview) to ``congressional/`` subdirectory

Supports regional document generation for 8 regions:
  - Doc C (InterTribal strategy) to ``regional/internal/`` subdirectory
  - Doc D (regional overview) to ``regional/congressional/`` subdirectory
"""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from dataclasses import asdict

from src.packets.change_tracker import PacketChangeTracker
from src.packets.context import TribePacketContext
from src.packets.congress import CongressionalMapper
from src.packets.doc_types import DOC_A, DOC_B, DocumentTypeConfig
from src.packets.docx_engine import DocxEngine
from src.packets.ecoregion import EcoregionMapper
from src.packets.economic import EconomicImpactCalculator, TribeEconomicSummary
from src.packets.registry import TribalRegistry
from src.paths import (
    AWARD_CACHE_DIR,
    GRAPH_SCHEMA_PATH,
    HAZARD_PROFILES_DIR,
    PACKET_STATE_DIR,
    PACKETS_OUTPUT_DIR,
    PROJECT_ROOT,
)
from src.utils import format_dollars
from src.packets.agent_review import AgentReviewOrchestrator
from src.packets.relevance import ProgramRelevanceFilter

logger = logging.getLogger(__name__)

_MAX_CACHE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB

_TRIBE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


def _sanitize_tribe_id(tribe_id: str) -> str:
    """Validate tribe_id contains only safe characters for file paths.

    Args:
        tribe_id: Tribe identifier to validate.

    Returns:
        The validated tribe_id.

    Raises:
        ValueError: If tribe_id contains unsafe characters.
    """
    if not _TRIBE_ID_PATTERN.match(tribe_id):
        raise ValueError(
            f"Invalid tribe_id '{tribe_id}': must contain only "
            f"alphanumeric characters, underscores, and hyphens"
        )
    return tribe_id


class PacketOrchestrator:
    """Orchestrates Tribe packet generation from registry, ecoregion, and congress modules.

    Usage::

        config = load_config()
        programs = load_programs()
        orch = PacketOrchestrator(config, programs)
        orch.run_single_tribe("Navajo Nation")
        orch.run_all_tribes()
    """

    def __init__(
        self,
        config: dict,
        programs: list[dict],
        enable_agent_review: bool = False,
    ) -> None:
        """Initialize the orchestrator with config and program inventory.

        Args:
            config: Application configuration dict (with ``packets`` section).
            programs: List of program dicts from program_inventory.json.
            enable_agent_review: Enable the 3-pass agent review cycle for
                DOCX Hot Sheet production. Default ``False`` (opt-in).
        """
        self.config = config
        self.programs = {p["id"]: p for p in programs}
        self.enable_agent_review = enable_agent_review
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
        """Generate multi-doc packets for all Tribes, regional docs, and quality review.

        Generates Doc A + Doc B per Tribe (based on data completeness),
        Doc C + Doc D per region (8 regions), a strategic overview,
        and runs automated quality review on all outputs.

        Returns:
            dict with keys: success, errors, total, duration_s,
            doc_a_count, doc_b_count, regional_results, quality_report_path
        """
        import gc
        import time

        from src.packets.quality_review import DocumentQualityReviewer

        all_tribes = self.registry.get_all()
        total = len(all_tribes)
        start = time.monotonic()
        success_count = 0
        error_count = 0
        error_tribes: list[str] = []
        doc_a_count = 0
        doc_b_count = 0
        prebuilt_contexts: dict[str, "TribePacketContext"] = {}

        for i, tribe in enumerate(all_tribes, 1):
            elapsed = time.monotonic() - start
            print(f"[{i}/{total}] {tribe['name']}...", end="", flush=True)
            try:
                context = self._build_context(tribe)
                prebuilt_contexts[tribe["tribe_id"]] = context
                paths = self.generate_tribal_docs(context, tribe)
                for p in paths:
                    if "internal" in str(p):
                        doc_a_count += 1
                    elif "congressional" in str(p):
                        doc_b_count += 1
                print(f" OK ({len(paths)} docs, {elapsed:.0f}s)")
                success_count += 1
            except Exception as exc:
                print(f" ERROR: {exc}")
                logger.error("Failed: %s: %s", tribe["name"], exc)
                error_count += 1
                error_tribes.append(tribe["name"])
            finally:
                if i % 25 == 0:
                    gc.collect()

        # Regional documents (Doc C + Doc D)
        print("\nGenerating Regional Documents...", flush=True)
        regional_results = {}
        try:
            regional_results = self.generate_regional_docs(
                prebuilt_contexts=prebuilt_contexts,
            )
            for region_id, paths in regional_results.items():
                if paths:
                    print(f"  {region_id}: {len(paths)} docs OK")
                else:
                    print(f"  {region_id}: FAILED")
        except Exception as exc:
            print(f"  Regional generation ERROR: {exc}")
            logger.error("Regional generation failed: %s", exc)

        # Strategic overview
        print("\nGenerating Strategic Overview...", end="", flush=True)
        try:
            overview_path = self.generate_strategic_overview()
            print(f" OK ({overview_path})")
        except Exception as exc:
            print(f" ERROR: {exc}")
            logger.error("Strategic overview failed: %s", exc)

        # Quality review
        output_dir = self._get_output_dir()
        print("\nRunning Quality Review...", flush=True)
        quality_report_path = None
        try:
            reviewer = DocumentQualityReviewer()
            batch_result = reviewer.review_batch(output_dir)
            report = reviewer.generate_report(batch_result)
            quality_report_path = output_dir / "quality_report.md"
            quality_report_path.write_text(report, encoding="utf-8")
            print(
                f"  Quality review: {batch_result.total_passed}/"
                f"{batch_result.total_reviewed} passed "
                f"({batch_result.critical_issues} critical, "
                f"{batch_result.warning_issues} warnings)"
            )
        except Exception as exc:
            print(f"  Quality review ERROR: {exc}")
            logger.error("Quality review failed: %s", exc)

        duration = time.monotonic() - start
        print("\n--- Batch Complete ---")
        print(f"Total: {total} | Success: {success_count} | Errors: {error_count}")
        print(f"Doc A (internal): {doc_a_count} | Doc B (congressional): {doc_b_count}")
        print(f"Regional: {sum(1 for v in regional_results.values() if v)} regions")
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
            "doc_a_count": doc_a_count,
            "doc_b_count": doc_b_count,
            "regional_results": regional_results,
            "quality_report_path": quality_report_path,
        }

    def _load_tribe_cache(self, cache_dir: Path, tribe_id: str) -> dict:
        """Load a per-Tribe JSON cache file. Returns empty dict if not found.

        Args:
            cache_dir: Directory containing per-Tribe JSON cache files.
            tribe_id: Tribe identifier (used as filename stem).

        Returns:
            Parsed JSON dict, or empty dict on missing/corrupt files.
        """
        tribe_id = _sanitize_tribe_id(tribe_id)
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
        tribe_id = _sanitize_tribe_id(tribe["tribe_id"])
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
        print(f"    Total Obligation: {format_dollars(total_obligation)} across {count} awards")

        # Group by program/CFDA
        program_totals: dict[str, float] = {}
        for award in context.awards:
            prog = award.get("program_id") or award.get("cfda", "Unknown")
            program_totals[prog] = program_totals.get(prog, 0.0) + award.get("obligation", 0.0)

        if program_totals:
            prog_strs = []
            for prog, total in sorted(program_totals.items(), key=lambda x: -x[1]):
                prog_strs.append(f"{prog} ({format_dollars(total)})")
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
                print(f"      {i}. {haz_type} (score: {haz_score:.1f}, EAL: {format_dollars(haz_eal)})")

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

    def _enrich_context_with_economics(
        self, context: TribePacketContext
    ) -> TribeEconomicSummary:
        """Compute economic impact and store in context.

        Shared between generate_packet_from_context() and
        generate_tribal_docs() to avoid duplicating the computation.

        Args:
            context: TribePacketContext to enrich (modified in-place).

        Returns:
            The computed TribeEconomicSummary.
        """
        economic_summary = self.economic_calculator.compute(
            tribe_id=context.tribe_id,
            tribe_name=context.tribe_name,
            awards=context.awards,
            districts=context.districts,
            programs=self.programs,
        )
        context.economic_impact = asdict(economic_summary)
        return economic_summary

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
        economic_summary = self._enrich_context_with_economics(context)

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

        # Agent review cycle (opt-in)
        reviewer = AgentReviewOrchestrator(enabled=self.enable_agent_review)
        if reviewer.enabled:
            logger.info(
                "Agent review enabled for %s — "
                "awaiting critique registration via review agents",
                context.tribe_name,
            )
            # NOTE: In the current workflow, critiques are registered
            # externally by Claude Code agents via the review-orchestrator
            # agent definition.  The Python-side reviewer stores protocol
            # state and will be populated when the orchestrator agent calls
            # register_critiques() with each agent's output.

        # Persist current state after successful generation
        tracker.save_current(context.tribe_id, current_state)

        logger.info("Generated packet for %s: %s", context.tribe_name, path)
        return path

    # ------------------------------------------------------------------
    # Phase 14: Multi-document generation (INTG-02)
    # ------------------------------------------------------------------

    def _has_complete_data(self, context: TribePacketContext) -> bool:
        """Check if a Tribe has sufficient data for full Doc A generation.

        Complete data requires: awards, hazard profile, and congressional
        delegation. Tribes with partial data get Doc B only.

        Args:
            context: TribePacketContext to check.

        Returns:
            True if context has enough data for internal strategy doc.
        """
        has_awards = bool(context.awards)
        has_hazards = bool(context.hazard_profile)
        has_delegation = bool(context.senators or context.representatives)
        return has_awards and has_hazards and has_delegation

    def _generate_single_doc(
        self,
        context: TribePacketContext,
        tribe: dict,
        doc_type_config: DocumentTypeConfig,
        economic_summary=None,
        relevant=None,
        omitted=None,
        structural_asks=None,
        changes=None,
        previous_date=None,
    ) -> Path:
        """Generate a single document of a specific type for a Tribe.

        Creates a DocxEngine with the specified doc_type_config, saves
        to the appropriate subdirectory (internal/ or congressional/).

        Args:
            context: Fully populated TribePacketContext.
            tribe: Original tribe dict from registry.
            doc_type_config: Document type configuration.
            economic_summary: Pre-computed economic summary (optional).
            relevant: Pre-filtered relevant programs (optional).
            omitted: Pre-computed omitted programs (optional).
            structural_asks: Pre-loaded structural asks (optional).
            changes: Pre-computed changes (optional).
            previous_date: Previous generation date (optional).

        Returns:
            Path to generated .docx file.
        """
        # Determine output subdirectory
        base_dir = self._get_output_dir()
        if doc_type_config.is_internal:
            output_dir = base_dir / "internal"
        else:
            output_dir = base_dir / "congressional"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create config with overridden output dir
        doc_config = dict(self.config)
        doc_config["packets"] = dict(doc_config.get("packets", {}))
        doc_config["packets"]["output_dir"] = str(output_dir)

        engine = DocxEngine(
            doc_config, self.programs, doc_type_config=doc_type_config
        )
        path = engine.generate(
            context=context,
            relevant_programs=relevant or [],
            economic_summary=economic_summary,
            structural_asks=structural_asks or [],
            omitted_programs=omitted,
            changes=changes,
            previous_date=previous_date,
            doc_type_config=doc_type_config,
        )

        logger.info(
            "Generated %s doc for %s: %s",
            doc_type_config.doc_type,
            context.tribe_name,
            path,
        )
        return path

    def _get_output_dir(self) -> Path:
        """Get the base output directory from config.

        Returns:
            Path to the packets output directory.
        """
        raw_dir = self.config.get("packets", {}).get("output_dir")
        output_dir = Path(raw_dir) if raw_dir else PACKETS_OUTPUT_DIR
        if not output_dir.is_absolute():
            output_dir = PROJECT_ROOT / output_dir
        return output_dir

    def generate_tribal_docs(
        self,
        context: TribePacketContext,
        tribe: dict,
        doc_types: list[DocumentTypeConfig] | None = None,
    ) -> list[Path]:
        """Generate multiple document types for a single Tribe.

        For complete-data Tribes (awards + hazards + delegation): generates
        both Doc A (internal strategy) and Doc B (congressional overview).
        For partial-data Tribes: generates Doc B only.

        Args:
            context: Fully populated TribePacketContext.
            tribe: Original tribe dict from registry.
            doc_types: Optional list of DocumentTypeConfig to generate.
                If None, auto-selects based on data completeness.

        Returns:
            List of Paths to generated .docx files.
        """
        # Compute shared data once
        economic_summary = self._enrich_context_with_economics(context)

        relevant = self.relevance_filter.filter_for_tribe(
            hazard_profile=context.hazard_profile,
            ecoregions=context.ecoregions,
            ecoregion_mapper=self.ecoregion,
        )
        omitted = self.relevance_filter.get_omitted_programs(relevant)
        structural_asks = self._load_structural_asks()

        # Change tracking
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

        # Determine doc types to generate
        if doc_types is None:
            if self._has_complete_data(context):
                doc_types = [DOC_A, DOC_B]
            else:
                doc_types = [DOC_B]

        paths: list[Path] = []
        for dtc in doc_types:
            path = self._generate_single_doc(
                context=context,
                tribe=tribe,
                doc_type_config=dtc,
                economic_summary=economic_summary,
                relevant=relevant,
                omitted=omitted,
                structural_asks=structural_asks,
                changes=changes,
                previous_date=previous_date,
            )
            paths.append(path)

        # Persist current state after successful generation
        tracker.save_current(context.tribe_id, current_state)

        return paths

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

    # ------------------------------------------------------------------
    # Phase 14: Regional document generation (INTG-02, Doc C/D)
    # ------------------------------------------------------------------

    def generate_regional_docs(
        self,
        skip_context_build: bool = False,
        prebuilt_contexts: dict[str, TribePacketContext] | None = None,
    ) -> dict[str, list[Path]]:
        """Generate Doc C + Doc D for all 8 regions.

        Pre-aggregates all Tribe contexts, then generates 2 documents per
        region (internal InterTribal strategy + congressional overview).

        Args:
            skip_context_build: If True, skip building contexts (use
                prebuilt_contexts instead).
            prebuilt_contexts: Optional dict mapping tribe_id to
                TribePacketContext. Useful when run_all_tribes() has
                already built contexts.

        Returns:
            Dict mapping region_id to [path_c, path_d] for each region.
        """
        from src.packets.doc_types import DOC_C, DOC_D
        from src.packets.regional import RegionalAggregator
        from src.paths import REGIONAL_CONFIG_PATH

        # Step 1: Build all TribePacketContexts
        if prebuilt_contexts is not None:
            all_contexts = prebuilt_contexts
        else:
            all_contexts = {}
            all_tribes = self.registry.get_all()
            for tribe in all_tribes:
                try:
                    ctx = self._build_context(tribe)
                    all_contexts[tribe["tribe_id"]] = ctx
                except Exception as exc:
                    logger.warning(
                        "Failed to build context for %s: %s",
                        tribe.get("name", tribe.get("tribe_id", "?")),
                        exc,
                    )

        # Step 2: Create aggregator
        aggregator = RegionalAggregator(
            regional_config_path=REGIONAL_CONFIG_PATH,
            registry=self.registry,
        )

        results: dict[str, list[Path]] = {}

        for region_id in aggregator.get_region_ids():
            try:
                # Get Tribe IDs for this region
                tribe_ids = aggregator.get_tribe_ids_for_region(region_id)
                skipped = [
                    tid for tid in tribe_ids if tid not in all_contexts
                ]
                if skipped:
                    logger.warning(
                        "Region %s: skipping %d Tribes with missing context: %s",
                        region_id, len(skipped), skipped[:5],
                    )
                region_contexts = [
                    all_contexts[tid]
                    for tid in tribe_ids
                    if tid in all_contexts
                ]

                # Aggregate
                regional_ctx = aggregator.aggregate(
                    region_id, region_contexts
                )

                # Generate Doc C (internal)
                path_c = self._generate_regional_doc(
                    regional_ctx, DOC_C
                )

                # Generate Doc D (congressional)
                path_d = self._generate_regional_doc(
                    regional_ctx, DOC_D
                )

                results[region_id] = [path_c, path_d]
                logger.info(
                    "Regional docs for %s: %d Tribes aggregated",
                    region_id,
                    len(region_contexts),
                )
            except Exception as exc:
                logger.error(
                    "Failed to generate regional docs for %s: %s",
                    region_id,
                    exc,
                )
                results[region_id] = []

        return results

    def _generate_regional_doc(
        self,
        regional_ctx,
        doc_type_config: DocumentTypeConfig,
    ) -> Path:
        """Generate a single regional document (Doc C or Doc D).

        Creates the DOCX document with regional section renderers and
        saves to the appropriate subdirectory.

        Args:
            regional_ctx: RegionalContext with aggregated region data.
            doc_type_config: DOC_C or DOC_D configuration.

        Returns:
            Path to the generated .docx file.
        """
        import os
        import tempfile

        from docx import Document as DocxDocument

        from src.packets.docx_regional_sections import (
            render_regional_appendix,
            render_regional_award_landscape,
            render_regional_cover_page,
            render_regional_delegation,
            render_regional_executive_summary,
            render_regional_hazard_synthesis,
        )
        from src.packets.docx_styles import StyleManager

        # Create document with styles
        document = DocxDocument()
        style_manager = StyleManager(document)

        # Configure page margins
        from docx.shared import Inches

        for section in document.sections:
            section.top_margin = Inches(1)
            section.bottom_margin = Inches(1)
            section.left_margin = Inches(1)
            section.right_margin = Inches(1)

        # Apply doc-type-specific headers/footers
        engine = DocxEngine(
            self.config, self.programs, doc_type_config=doc_type_config
        )
        engine._setup_header_footer(
            document,
            header_text=doc_type_config.format_header(
                region_name=regional_ctx.region_name,
            ),
            footer_text=doc_type_config.footer_template,
            confidential=doc_type_config.confidential,
        )

        # Render regional sections
        render_regional_cover_page(
            document, regional_ctx, style_manager, doc_type_config
        )
        render_regional_executive_summary(
            document, regional_ctx, style_manager, doc_type_config
        )
        render_regional_hazard_synthesis(
            document, regional_ctx, style_manager
        )
        render_regional_award_landscape(
            document, regional_ctx, style_manager
        )
        render_regional_delegation(
            document, regional_ctx, style_manager, doc_type_config
        )
        render_regional_appendix(
            document, regional_ctx, style_manager
        )

        # Determine output path
        base_dir = self._get_output_dir()
        if doc_type_config.is_internal:
            output_dir = base_dir / "regional" / "internal"
        else:
            output_dir = base_dir / "regional" / "congressional"
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = doc_type_config.format_filename(regional_ctx.region_id)
        output_path = output_dir / filename

        # Atomic write
        tmp_fd = tempfile.NamedTemporaryFile(
            dir=str(output_dir), suffix=".docx", delete=False
        )
        tmp_name = tmp_fd.name
        tmp_fd.close()
        try:
            document.save(tmp_name)
            os.replace(tmp_name, str(output_path))
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

        logger.info(
            "Generated regional %s doc for %s: %s",
            doc_type_config.doc_type,
            regional_ctx.region_name,
            output_path,
        )
        return output_path
