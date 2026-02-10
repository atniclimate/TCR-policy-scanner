"""PacketOrchestrator — integrates registry, ecoregion, and congress modules.

Coordinates Tribe name resolution, ecoregion classification, and
congressional delegation lookup into a unified TribePacketContext.
Called from CLI via ``--prep-packets --tribe <name>`` or ``--prep-packets --all-tribes``.
"""

import logging
import sys
from datetime import datetime, timezone

from src.packets.context import TribePacketContext
from src.packets.congress import CongressionalMapper
from src.packets.ecoregion import EcoregionMapper
from src.packets.registry import TribalRegistry

logger = logging.getLogger("tcr_scanner.packets.orchestrator")


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

    def run_all_tribes(self) -> None:
        """Generate packet context for all Tribes in the registry.

        Iterates through all Tribes, builds context for each, and prints
        a summary at completion.
        """
        all_tribes = self.registry.get_all()
        total = len(all_tribes)
        print(f"\nGenerating packet context for {total} Tribes...\n")

        success_count = 0
        error_count = 0

        for i, tribe in enumerate(all_tribes, 1):
            print(f"[{i}/{total}] {tribe['name']}...", end="")
            try:
                self._build_context(tribe)
                print(" OK")
                success_count += 1
            except Exception as exc:
                print(f" ERROR: {exc}")
                logger.error("Failed to build context for %s: %s",
                             tribe["name"], exc)
                error_count += 1

        print(f"\n--- Summary ---")
        print(f"Total: {total}")
        print(f"Success: {success_count}")
        if error_count:
            print(f"Errors: {error_count}")

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
            generated_at=datetime.now(timezone.utc).isoformat(),
            congress_session=self.congress.get_congress_session(),
        )

        logger.debug("Built context for %s: %d districts, %d senators, %d reps",
                      tribe["name"], len(districts), len(senators),
                      len(representatives))
        return context

    def _display_tribe_info(self, context: TribePacketContext) -> None:
        """Display formatted Tribe identity and congressional delegation.

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
            print(f"\n  Priority Programs by Ecoregion:")
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
            print(sep)
            return

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

        print(f"\n  Generated: {context.generated_at}")
        print(sep)
