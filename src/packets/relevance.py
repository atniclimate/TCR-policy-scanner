"""Program relevance filter for Tribe-specific advocacy packets.

Filters the full program inventory (16 programs) down to 8-12 relevant
programs per Tribe based on hazard profile, ecoregion priorities, and
program priority levels.

Stateless pure-function module with no file I/O.
"""

import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MIN_PROGRAMS: int = 8
"""Minimum programs to include in a filtered result."""

MAX_PROGRAMS: int = 12
"""Maximum programs to include in a filtered result."""

ABSOLUTE_MIN_PROGRAMS: int = 3
"""Absolute minimum -- never return fewer than this."""

# NRI hazard code -> relevant program IDs
HAZARD_PROGRAM_MAP: dict[str, list[str]] = {
    # Wildfire
    "WFIR": ["usda_wildfire", "fema_bric", "fema_tribal_mitigation", "bia_tcr"],
    # Coastal Flooding
    "CFLD": ["fema_bric", "fema_tribal_mitigation", "epa_stag", "usbr_watersmart"],
    # Inland/Riverine Flooding
    "RFLD": ["fema_bric", "fema_tribal_mitigation", "epa_stag", "usbr_watersmart"],
    # Drought
    "DRGT": ["usbr_watersmart", "usbr_tap", "bia_tcr"],
    # Hurricane
    "HRCN": ["fema_bric", "fema_tribal_mitigation", "hud_ihbg"],
    # Earthquake
    "ERQK": ["fema_bric", "fema_tribal_mitigation"],
    # Heat Wave
    "HWAV": ["bia_tcr", "hud_ihbg", "doe_indian_energy"],
    # Cold Wave
    "CWAV": ["hud_ihbg", "doe_indian_energy", "bia_tcr"],
    # Tornado
    "TRND": ["fema_bric", "fema_tribal_mitigation", "hud_ihbg"],
    # Strong Wind
    "SWND": ["fema_bric", "fema_tribal_mitigation"],
    # Hail
    "HAIL": ["fema_bric", "fema_tribal_mitigation"],
    # Winter Weather
    "WNTW": ["hud_ihbg", "fema_bric", "dot_protect"],
    # Ice Storm
    "ISTM": ["hud_ihbg", "fema_bric", "doe_indian_energy"],
    # Avalanche
    "AVLN": ["fema_bric", "bia_tcr"],
    # Landslide
    "LNDS": ["fema_bric", "fema_tribal_mitigation", "dot_protect"],
    # Volcanic Activity
    "VLCN": ["fema_bric", "bia_tcr"],
    # Tsunami
    "TSUN": ["fema_bric", "fema_tribal_mitigation", "noaa_tribal"],
    # Lightning
    "LTNG": ["fema_bric", "bia_tcr"],
}
"""Mapping of all 18 NRI hazard type codes to relevant program IDs."""

# Human-readable hazard names -> NRI codes for reverse lookup
_HAZARD_NAME_TO_CODE: dict[str, str] = {
    "wildfire": "WFIR",
    "coastal flooding": "CFLD",
    "riverine flooding": "RFLD",
    "drought": "DRGT",
    "hurricane": "HRCN",
    "earthquake": "ERQK",
    "heat wave": "HWAV",
    "cold wave": "CWAV",
    "tornado": "TRND",
    "strong wind": "SWND",
    "hail": "HAIL",
    "winter weather": "WNTW",
    "ice storm": "ISTM",
    "avalanche": "AVLN",
    "landslide": "LNDS",
    "volcanic activity": "VLCN",
    "tsunami": "TSUN",
    "lightning": "LTNG",
}

# Programs that are always relevant (universal applicability)
_ALWAYS_RELEVANT: list[str] = ["bia_tcr", "irs_elective_pay", "epa_gap"]

# Priority weights for scoring
_PRIORITY_WEIGHTS: dict[str, int] = {
    "critical": 30,
    "high": 20,
    "medium": 10,
    "low": 5,
}


# ---------------------------------------------------------------------------
# Filter
# ---------------------------------------------------------------------------

class ProgramRelevanceFilter:
    """Filters program inventory to relevant programs for a specific Tribe.

    Scores each program based on hazard relevance, ecoregion priority,
    and program priority level, then returns 8-12 programs sorted by
    relevance score descending.

    Usage::

        programs = {"bia_tcr": {...}, "fema_bric": {...}, ...}
        filt = ProgramRelevanceFilter(programs)
        relevant = filt.filter_for_tribe(
            hazard_profile=ctx.hazard_profile,
            ecoregions=ctx.ecoregions,
        )
    """

    def __init__(
        self,
        programs: dict[str, dict],
        ecoregion_priority: list[str] | None = None,
    ) -> None:
        """Initialize the filter.

        Args:
            programs: Dict mapping program_id to program metadata dict.
            ecoregion_priority: Optional list of program IDs from ecoregion config.
        """
        self.programs = programs
        self.ecoregion_priority = ecoregion_priority or []

    def filter_for_tribe(
        self,
        hazard_profile: dict,
        ecoregions: list[str],
        ecoregion_mapper=None,
    ) -> list[dict]:
        """Filter programs to those relevant for a specific Tribe.

        Args:
            hazard_profile: Tribe's hazard profile dict (from cache).
                Expected schema: {"fema_nri": {"top_hazards": [...]}, ...}
            ecoregions: List of ecoregion IDs for the Tribe.
            ecoregion_mapper: Optional EcoregionMapper instance for
                get_priority_programs() lookups.

        Returns:
            List of 8-12 program dicts with added ``_relevance_score`` field,
            sorted by relevance score descending. Never fewer than 3 programs.
        """
        scored: dict[str, float] = {}

        # Step 1: Base score from priority level
        for pid, prog in self.programs.items():
            priority = prog.get("priority", "medium")
            scored[pid] = _PRIORITY_WEIGHTS.get(priority, 5)

        # Step 2: Always-relevant programs get a bonus
        for pid in _ALWAYS_RELEVANT:
            if pid in scored:
                scored[pid] += 15

        # Step 3: Critical programs get guaranteed inclusion bonus
        critical_ids: set[str] = set()
        for pid, prog in self.programs.items():
            if prog.get("priority") == "critical":
                scored[pid] += 50  # Ensure they survive trimming
                critical_ids.add(pid)

        # Step 4: Hazard relevance scoring
        top_hazards = self._extract_top_hazards(hazard_profile)
        for rank, hazard in enumerate(top_hazards):
            code = self._resolve_hazard_code(hazard)
            if code is None:
                continue
            relevant_programs = HAZARD_PROGRAM_MAP.get(code, [])
            # Higher-ranked hazards contribute more score
            hazard_bonus = max(25 - (rank * 5), 5)
            for pid in relevant_programs:
                if pid in scored:
                    scored[pid] += hazard_bonus

        # Step 5: Ecoregion priority scoring
        eco_programs: set[str] = set()
        if ecoregion_mapper is not None:
            for eco in ecoregions:
                for pid in ecoregion_mapper.get_priority_programs(eco):
                    eco_programs.add(pid)
        # Also use stored ecoregion_priority
        for pid in self.ecoregion_priority:
            eco_programs.add(pid)

        for pid in eco_programs:
            if pid in scored:
                scored[pid] += 10

        # Step 6: Sort by score descending
        ranked = sorted(scored.items(), key=lambda x: -x[1])

        # Step 7: Build result list
        result: list[dict] = []
        for pid, score in ranked:
            prog = self.programs.get(pid)
            if prog is None:
                continue
            prog_copy = dict(prog)
            prog_copy["_relevance_score"] = score
            result.append(prog_copy)

        # Step 8: Clamp to MIN-MAX range
        # Critical programs are never removed. If the number of critical
        # programs exceeds MAX_PROGRAMS, the result intentionally overflows
        # rather than dropping a legitimately critical program. In practice,
        # the current inventory has only 2-3 critical programs, so this edge
        # case does not activate.
        if len(result) > MAX_PROGRAMS:
            kept: list[dict] = []
            for prog in result:
                if prog["id"] in critical_ids:
                    kept.append(prog)
            for prog in result:
                if prog["id"] not in critical_ids:
                    if len(kept) < MAX_PROGRAMS:
                        kept.append(prog)
            result = kept

        # Ensure minimum (pad from remaining if too few)
        if len(result) < MIN_PROGRAMS:
            included_ids = {p["id"] for p in result}
            for pid, prog in self.programs.items():
                if pid not in included_ids:
                    prog_copy = dict(prog)
                    prog_copy["_relevance_score"] = _PRIORITY_WEIGHTS.get(
                        prog.get("priority", "medium"), 5
                    )
                    result.append(prog_copy)
                    if len(result) >= MIN_PROGRAMS:
                        break

        # Absolute minimum guard
        if len(result) < ABSOLUTE_MIN_PROGRAMS and len(self.programs) >= ABSOLUTE_MIN_PROGRAMS:
            included_ids = {p["id"] for p in result}
            for pid, prog in self.programs.items():
                if pid not in included_ids:
                    prog_copy = dict(prog)
                    prog_copy["_relevance_score"] = 1
                    result.append(prog_copy)
                    if len(result) >= ABSOLUTE_MIN_PROGRAMS:
                        break

        # Final sort by score descending
        result.sort(key=lambda p: -p["_relevance_score"])

        return result

    def get_omitted_programs(self, included: list[dict]) -> list[dict]:
        """Return programs NOT in the included list.

        Args:
            included: List of program dicts from filter_for_tribe().

        Returns:
            List of omitted program dicts, sorted by priority weight descending.
        """
        included_ids = {p["id"] for p in included}
        omitted: list[dict] = []
        for pid, prog in self.programs.items():
            if pid not in included_ids:
                omitted.append(dict(prog))

        omitted.sort(
            key=lambda p: -_PRIORITY_WEIGHTS.get(p.get("priority", "medium"), 5)
        )
        return omitted

    def _extract_top_hazards(self, hazard_profile: dict) -> list[dict]:
        """Extract top hazards from hazard profile dict.

        Handles both the full nested profile format and empty profiles.

        Args:
            hazard_profile: Tribe's hazard profile.

        Returns:
            List of hazard dicts with at least ``type`` or ``code`` field.
        """
        if not hazard_profile:
            return []

        nri = hazard_profile.get("fema_nri") or hazard_profile.get(
            "sources", {}
        ).get("fema_nri", {})
        top_hazards = nri.get("top_hazards", []) if nri else []
        return list(top_hazards)

    def _resolve_hazard_code(self, hazard: dict) -> str | None:
        """Resolve a hazard dict to an NRI hazard code.

        Handles both ``code`` field (e.g. "WFIR") and ``type`` field
        (e.g. "Wildfire") for compatibility.

        Args:
            hazard: Hazard dict from top_hazards list.

        Returns:
            NRI hazard code string, or None if unresolvable.
        """
        code = hazard.get("code")
        if code and code in HAZARD_PROGRAM_MAP:
            return code

        haz_type = hazard.get("type", "")
        normalized = haz_type.lower().strip()
        code = _HAZARD_NAME_TO_CODE.get(normalized)
        if code:
            return code

        # Try partial matching for variations
        for name, c in _HAZARD_NAME_TO_CODE.items():
            if name in normalized or normalized in name:
                return c

        logger.warning("Could not resolve hazard to NRI code: %s", hazard)
        return None
