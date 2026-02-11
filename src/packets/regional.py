"""Regional aggregation system for Doc C/D document generation.

Aggregates TribePacketContext data across all Tribes in a region to produce
RegionalContext objects used by regional document generators (Doc C and Doc D).

Regions are defined in data/regional_config.json with 8 entries:
  - 7 geographic regions (pnw, alaska, plains, southwest, greatlakes, southeast, northeast)
  - 1 cross-cutting virtual region (all 592 Tribes)

Tribe-to-region assignment uses state overlap: a Tribe belongs to a region if
any of its states appear in the region's states list. A Tribe can appear in
multiple regions if it spans multiple states. The cross-cutting region (empty
states list) includes ALL Tribes unconditionally.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from src.packets.context import TribePacketContext

logger = logging.getLogger(__name__)


@dataclass
class RegionalContext:
    """Aggregated context for generating a region's Doc C / Doc D documents.

    Combines data from multiple TribePacketContexts within a geographic
    region into a single render-ready structure for regional documents.

    Identity fields:
        region_id: Region identifier (e.g., "pnw", "alaska", "crosscutting").
        region_name: Full region name from regional_config.json.
        short_name: Short display name for headers and tables.
        core_frame: Regional hazard/policy framing from config.
        treaty_trust_angle: Regional treaty/trust narrative angle.
        key_programs: Priority program IDs for this region.
        states: State abbreviations covered by this region.

    Aggregated data:
        tribe_count: Number of Tribes assigned to this region.
        tribes: Per-Tribe summary dicts (tribe_id, tribe_name, states).
        total_awards: Sum of all Tribe award obligations in region.
        award_coverage: Count of Tribes with at least one award.
        hazard_coverage: Count of Tribes with hazard profile data.
        congressional_coverage: Count of Tribes with delegation data.

    Hazard synthesis:
        top_shared_hazards: Hazards affecting the most Tribes in region.
        composite_risk_score: Average NRI risk score across Tribes with data.

    Economic aggregates:
        aggregate_economic_impact: Summed economic ranges across Tribes.

    Congressional overlap:
        delegation_overlap: Members serving multiple Tribes in region.
        total_senators: Unique senator count across region.
        total_representatives: Unique representative count across region.

    Coverage gaps:
        tribes_without_awards: Tribe IDs with zero awards.
        tribes_without_hazards: Tribe IDs with no hazard data.
        tribes_without_delegation: Tribe IDs with no congressional data.

    Metadata:
        generated_at: ISO timestamp of aggregation.
    """

    # Identity
    region_id: str
    region_name: str
    short_name: str
    core_frame: str
    treaty_trust_angle: str
    key_programs: list[str] = field(default_factory=list)
    states: list[str] = field(default_factory=list)

    # Aggregated data
    tribe_count: int = 0
    tribes: list[dict] = field(default_factory=list)
    total_awards: float = 0.0
    award_coverage: int = 0
    hazard_coverage: int = 0
    congressional_coverage: int = 0

    # Hazard synthesis
    top_shared_hazards: list[dict] = field(default_factory=list)
    composite_risk_score: float = 0.0

    # Economic aggregates
    aggregate_economic_impact: dict = field(default_factory=dict)

    # Congressional overlap
    delegation_overlap: list[dict] = field(default_factory=list)
    total_senators: int = 0
    total_representatives: int = 0

    # Coverage gaps
    tribes_without_awards: list[str] = field(default_factory=list)
    tribes_without_hazards: list[str] = field(default_factory=list)
    tribes_without_delegation: list[str] = field(default_factory=list)

    # Metadata
    generated_at: str = ""


class RegionalAggregator:
    """Aggregates Tribe-level data into regional contexts for Doc C/D generation.

    Loads region definitions from regional_config.json, assigns Tribes to
    regions based on state overlap, and computes aggregate metrics for
    awards, hazards, delegation overlap, economic impact, and coverage gaps.

    Usage::

        aggregator = RegionalAggregator(
            regional_config_path=REGIONAL_CONFIG_PATH,
            registry=registry,
        )
        tribe_ids = aggregator.get_tribe_ids_for_region("pnw")
        regional_ctx = aggregator.aggregate("pnw", tribe_contexts)
    """

    def __init__(
        self,
        regional_config_path: Path,
        registry,
    ) -> None:
        """Load regional config and prepare for aggregation.

        Args:
            regional_config_path: Path to regional_config.json.
            registry: TribalRegistry instance with get_all() method.
        """
        self.config = json.loads(regional_config_path.read_text(encoding="utf-8"))
        self.registry = registry
        self._tribe_region_cache: dict[str, list[str]] = {}

    def get_region_ids(self) -> list[str]:
        """Return all region IDs from config.

        Returns:
            List of region ID strings.
        """
        return list(self.config.get("regions", {}).keys())

    def get_tribe_ids_for_region(self, region_id: str) -> list[str]:
        """Return list of tribe_ids belonging to region based on state overlap.

        For the crosscutting region (empty states list), returns ALL Tribe IDs.
        For geographic regions, returns Tribes whose states overlap the region's.

        Args:
            region_id: Region identifier from regional_config.json.

        Returns:
            List of tribe_id strings assigned to this region.
        """
        if region_id in self._tribe_region_cache:
            return self._tribe_region_cache[region_id]

        region_cfg = self.config.get("regions", {}).get(region_id, {})
        region_states = set(region_cfg.get("states", []))

        all_tribes = self.registry.get_all()

        if not region_states:
            # Crosscutting region: all Tribes
            result = [t["tribe_id"] for t in all_tribes]
        else:
            result = [
                t["tribe_id"]
                for t in all_tribes
                if set(t.get("states", [])) & region_states
            ]

        self._tribe_region_cache[region_id] = result
        return result

    def aggregate(
        self,
        region_id: str,
        tribe_contexts: list[TribePacketContext],
    ) -> RegionalContext:
        """Aggregate multiple TribePacketContexts into a RegionalContext.

        Args:
            region_id: Region identifier.
            tribe_contexts: List of TribePacketContext objects for Tribes
                assigned to this region.

        Returns:
            Fully populated RegionalContext for the region.
        """
        region_cfg = self.config.get("regions", {}).get(region_id, {})

        # Awards aggregation
        total_awards, award_coverage = self._aggregate_awards(tribe_contexts)

        # Hazard synthesis
        top_shared = self._find_shared_hazards(tribe_contexts)
        composite_risk = self._compute_composite_risk(tribe_contexts)
        hazard_coverage = sum(
            1 for ctx in tribe_contexts if self._has_hazard_data(ctx)
        )

        # Congressional delegation overlap
        overlap, total_sens, total_reps = self._find_delegation_overlap(
            tribe_contexts
        )
        congressional_coverage = sum(
            1 for ctx in tribe_contexts
            if ctx.senators or ctx.representatives
        )

        # Economic aggregation
        economic_agg = self._aggregate_economics(tribe_contexts)

        # Coverage gaps
        no_awards, no_hazards, no_delegation = self._identify_gaps(tribe_contexts)

        # Tribe summaries
        tribes_list = [
            {
                "tribe_id": ctx.tribe_id,
                "tribe_name": ctx.tribe_name,
                "states": ctx.states,
            }
            for ctx in tribe_contexts
        ]

        return RegionalContext(
            region_id=region_id,
            region_name=region_cfg.get("name", region_id),
            short_name=region_cfg.get("short_name", region_id),
            core_frame=region_cfg.get("core_frame", ""),
            treaty_trust_angle=region_cfg.get("treaty_trust_angle", ""),
            key_programs=region_cfg.get("key_programs", []),
            states=region_cfg.get("states", []),
            tribe_count=len(tribe_contexts),
            tribes=tribes_list,
            total_awards=total_awards,
            award_coverage=award_coverage,
            hazard_coverage=hazard_coverage,
            congressional_coverage=congressional_coverage,
            top_shared_hazards=top_shared,
            composite_risk_score=composite_risk,
            aggregate_economic_impact=economic_agg,
            delegation_overlap=overlap,
            total_senators=total_sens,
            total_representatives=total_reps,
            tribes_without_awards=no_awards,
            tribes_without_hazards=no_hazards,
            tribes_without_delegation=no_delegation,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    # ------------------------------------------------------------------
    # Private aggregation helpers
    # ------------------------------------------------------------------

    def _aggregate_awards(
        self, contexts: list[TribePacketContext]
    ) -> tuple[float, int]:
        """Sum awards and count Tribes with at least one award.

        Args:
            contexts: List of TribePacketContext objects.

        Returns:
            Tuple of (total_awards, tribes_with_awards_count).
        """
        total = 0.0
        coverage = 0
        for ctx in contexts:
            tribe_total = sum(
                a.get("obligation", 0.0)
                for a in ctx.awards
                if isinstance(a.get("obligation"), (int, float))
            )
            total += tribe_total
            if ctx.awards:
                coverage += 1
        return total, coverage

    def _find_shared_hazards(
        self, contexts: list[TribePacketContext]
    ) -> list[dict]:
        """Find hazards affecting the most Tribes in the region.

        Counts how many Tribes have each hazard type in their top-5, then
        returns the top 5 hazards ranked by Tribe count. Ties are broken
        by average risk score (descending).

        Args:
            contexts: List of TribePacketContext objects.

        Returns:
            List of dicts with hazard_type, tribe_count, avg_score.
        """
        hazard_tribes: Counter = Counter()
        hazard_scores: dict[str, list[float]] = {}

        for ctx in contexts:
            top_hazards = self._extract_top_hazards(ctx)
            for hazard in top_hazards[:5]:
                htype = hazard.get("type", "")
                if not htype:
                    continue
                hazard_tribes[htype] += 1
                score = hazard.get("risk_score", 0.0)
                if isinstance(score, (int, float)):
                    hazard_scores.setdefault(htype, []).append(score)

        # Rank by tribe count, then by average score
        ranked = sorted(
            hazard_tribes.items(),
            key=lambda x: (
                x[1],
                sum(hazard_scores.get(x[0], [0.0]))
                / max(len(hazard_scores.get(x[0], [1])), 1),
            ),
            reverse=True,
        )

        result = []
        for htype, count in ranked[:5]:
            scores = hazard_scores.get(htype, [])
            avg = sum(scores) / len(scores) if scores else 0.0
            result.append({
                "hazard_type": htype,
                "tribe_count": count,
                "avg_score": round(avg, 2),
            })
        return result

    def _compute_composite_risk(
        self, contexts: list[TribePacketContext]
    ) -> float:
        """Compute average composite risk score across Tribes with data.

        Args:
            contexts: List of TribePacketContext objects.

        Returns:
            Average composite NRI risk score, or 0.0 if no data.
        """
        scores = []
        for ctx in contexts:
            nri = self._extract_nri(ctx)
            composite = nri.get("composite", {}) if nri else {}
            risk_score = composite.get("risk_score")
            if isinstance(risk_score, (int, float)) and risk_score > 0:
                scores.append(risk_score)
        return round(sum(scores) / len(scores), 2) if scores else 0.0

    def _find_delegation_overlap(
        self, contexts: list[TribePacketContext]
    ) -> tuple[list[dict], int, int]:
        """Find congressional members serving multiple Tribes in the region.

        Identifies members (by bioguide_id or formatted_name) who appear in
        more than one Tribe's delegation. Returns overlap list ranked by
        Tribe count, plus unique senator and representative counts.

        Args:
            contexts: List of TribePacketContext objects.

        Returns:
            Tuple of (overlap_list, total_unique_senators, total_unique_reps).
        """
        # Track member -> set of tribe_ids they serve
        member_tribes: dict[str, set[str]] = {}
        member_info: dict[str, dict] = {}
        unique_senators: set[str] = set()
        unique_reps: set[str] = set()

        for ctx in contexts:
            for senator in (ctx.senators or []):
                key = senator.get("bioguide_id") or senator.get(
                    "formatted_name", ""
                )
                if not key:
                    continue
                member_tribes.setdefault(key, set()).add(ctx.tribe_id)
                if key not in member_info:
                    member_info[key] = {
                        "member_name": senator.get(
                            "formatted_name", senator.get("name", key)
                        ),
                        "role": "Senator",
                        "committees": [
                            c.get("committee_name", "")
                            for c in senator.get("committees", [])
                        ],
                    }
                unique_senators.add(key)

            for rep in (ctx.representatives or []):
                key = rep.get("bioguide_id") or rep.get(
                    "formatted_name", ""
                )
                if not key:
                    continue
                member_tribes.setdefault(key, set()).add(ctx.tribe_id)
                if key not in member_info:
                    member_info[key] = {
                        "member_name": rep.get(
                            "formatted_name", rep.get("name", key)
                        ),
                        "role": "Representative",
                        "committees": [
                            c.get("committee_name", "")
                            for c in rep.get("committees", [])
                        ],
                    }
                unique_reps.add(key)

        # Build overlap list for members serving 2+ Tribes
        overlap = []
        for key, tribe_set in member_tribes.items():
            if len(tribe_set) >= 2:
                info = member_info.get(key, {})
                overlap.append({
                    "member_name": info.get("member_name", key),
                    "role": info.get("role", "Unknown"),
                    "tribe_count": len(tribe_set),
                    "tribe_ids": sorted(tribe_set),
                    "committees": info.get("committees", []),
                })

        # Sort by tribe_count descending
        overlap.sort(key=lambda x: x["tribe_count"], reverse=True)

        return overlap, len(unique_senators), len(unique_reps)

    def _aggregate_economics(
        self, contexts: list[TribePacketContext]
    ) -> dict:
        """Sum economic impact across all Tribes in region.

        Uses economic_impact data from each TribePacketContext. Falls back
        to zeros if economic_impact is not populated.

        Args:
            contexts: List of TribePacketContext objects.

        Returns:
            Dict with total_low, total_high, total_jobs_low, total_jobs_high.
        """
        total_low = 0.0
        total_high = 0.0
        total_jobs_low = 0.0
        total_jobs_high = 0.0

        for ctx in contexts:
            econ = ctx.economic_impact or {}
            total_low += econ.get("total_impact_low", 0.0)
            total_high += econ.get("total_impact_high", 0.0)
            total_jobs_low += econ.get("total_jobs_low", 0.0)
            total_jobs_high += econ.get("total_jobs_high", 0.0)

        return {
            "total_low": round(total_low, 2),
            "total_high": round(total_high, 2),
            "total_jobs_low": round(total_jobs_low, 2),
            "total_jobs_high": round(total_jobs_high, 2),
        }

    def _identify_gaps(
        self, contexts: list[TribePacketContext]
    ) -> tuple[list[str], list[str], list[str]]:
        """Identify Tribes missing awards, hazards, or delegation data.

        Args:
            contexts: List of TribePacketContext objects.

        Returns:
            Tuple of (tribes_without_awards, tribes_without_hazards,
            tribes_without_delegation) -- each a list of tribe_id strings.
        """
        no_awards = []
        no_hazards = []
        no_delegation = []

        for ctx in contexts:
            if not ctx.awards:
                no_awards.append(ctx.tribe_id)
            if not self._has_hazard_data(ctx):
                no_hazards.append(ctx.tribe_id)
            if not ctx.senators and not ctx.representatives:
                no_delegation.append(ctx.tribe_id)

        return no_awards, no_hazards, no_delegation

    # ------------------------------------------------------------------
    # Hazard profile extraction helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_nri(ctx: TribePacketContext) -> dict:
        """Extract FEMA NRI data from a TribePacketContext's hazard_profile.

        Handles two possible nestings:
          - hazard_profile.fema_nri (direct)
          - hazard_profile.sources.fema_nri (Phase 13 cache format)

        Args:
            ctx: TribePacketContext with hazard_profile field.

        Returns:
            NRI data dict, or empty dict if not found.
        """
        hp = ctx.hazard_profile or {}
        nri = hp.get("fema_nri")
        if nri:
            return nri
        return hp.get("sources", {}).get("fema_nri", {})

    @staticmethod
    def _extract_top_hazards(ctx: TribePacketContext) -> list[dict]:
        """Extract top hazards list from a TribePacketContext.

        Args:
            ctx: TribePacketContext with hazard_profile field.

        Returns:
            List of hazard dicts with type, risk_score, etc.
        """
        nri = RegionalAggregator._extract_nri(ctx)
        return nri.get("top_hazards", []) if nri else []

    @staticmethod
    def _has_hazard_data(ctx: TribePacketContext) -> bool:
        """Check whether a TribePacketContext has meaningful hazard data.

        Args:
            ctx: TribePacketContext to check.

        Returns:
            True if the context has NRI data with a composite score.
        """
        nri = RegionalAggregator._extract_nri(ctx)
        if not nri:
            return False
        composite = nri.get("composite", {})
        return bool(composite.get("risk_score"))
