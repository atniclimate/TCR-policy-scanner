"""Economic impact calculator for Tribe-specific advocacy packets.

Transforms raw USASpending award data into structured economic impact
estimates using published federal multipliers:
  - BEA RIMS II output multiplier range (1.8-2.4x)
  - BLS employment requirements (8-15 jobs per $1M)
  - FEMA/NIBS MitSaves benefit-cost ratio (4:1 for mitigation)

All calculations are stateless pure functions with no file I/O.
"""

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BEA_MULTIPLIER_LOW: float = 1.8
"""BEA RIMS II lower-bound output multiplier for federal spending."""

BEA_MULTIPLIER_HIGH: float = 2.4
"""BEA RIMS II upper-bound output multiplier for federal spending."""

BLS_JOBS_PER_MILLION_LOW: int = 8
"""BLS lower-bound employment per $1M federal spending."""

BLS_JOBS_PER_MILLION_HIGH: int = 15
"""BLS upper-bound employment per $1M federal spending."""

FEMA_BCR_OVERALL: float = 4.0
"""FEMA/NIBS National Institute of Building Sciences overall BCR for mitigation."""

FEMA_BCR_BY_HAZARD: dict[str, float] = {
    "flood": 5.0,
    "wind": 5.0,
    "hurricane": 5.0,
    "earthquake": 1.5,
}
"""FEMA/NIBS MitSaves hazard-specific benefit-cost ratios."""

MITIGATION_PROGRAM_IDS: set[str] = {
    "fema_bric",
    "fema_tribal_mitigation",
    "usda_wildfire",
}
"""Program IDs where FEMA BCR applies (mitigation-focused programs)."""

METHODOLOGY_CITATION: str = (
    "Economic impact estimates derived from Bureau of Economic Analysis (BEA) "
    "RIMS II regional input-output multipliers (output multiplier range 1.8-2.4x "
    "for federal government spending). Employment estimates based on Bureau of "
    "Labor Statistics (BLS) employment requirements tables (8-15 jobs per $1M in "
    "federal spending). Benefit-cost ratio for mitigation programs from "
    "FEMA/National Institute of Building Sciences (NIBS) Natural Hazard "
    "Mitigation Saves (MitSaves) 2018 Interim Report, reporting $4 average "
    "return per $1 invested in federal mitigation grants."
)
"""Full methodology footnote text for economic impact estimates."""

PROGRAM_BENCHMARK_AVERAGES: dict[str, float] = {
    "bia_tcr": 150_000.0,
    "fema_bric": 500_000.0,
    "irs_elective_pay": 200_000.0,
    "epa_stag": 100_000.0,
    "epa_gap": 75_000.0,
    "fema_tribal_mitigation": 300_000.0,
    "dot_protect": 250_000.0,
    "usda_wildfire": 350_000.0,
    "doe_indian_energy": 200_000.0,
    "hud_ihbg": 400_000.0,
    "noaa_tribal": 150_000.0,
    "fhwa_ttp_safety": 180_000.0,
    "usbr_watersmart": 250_000.0,
    "usbr_tap": 120_000.0,
    "bia_tcr_awards": 100_000.0,
    "epa_tribal_air": 80_000.0,
}
"""Average obligation per program, used for zero-award Tribes (benchmark path)."""


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ProgramEconomicImpact:
    """Economic impact estimate for a single program's awards to a Tribe.

    Attributes:
        program_id: Unique program identifier.
        total_obligation: Total federal obligation amount in dollars.
        multiplier_low: BEA lower-bound output multiplier.
        multiplier_high: BEA upper-bound output multiplier.
        estimated_impact_low: Low estimate of total economic impact.
        estimated_impact_high: High estimate of total economic impact.
        jobs_estimate_low: Low estimate of jobs supported.
        jobs_estimate_high: High estimate of jobs supported.
        fema_bcr: FEMA benefit-cost ratio (4.0 for mitigation, None otherwise).
        methodology_citation: Full methodology footnote text.
        is_benchmark: True when using program averages instead of Tribe data.
    """

    program_id: str
    total_obligation: float
    multiplier_low: float = BEA_MULTIPLIER_LOW
    multiplier_high: float = BEA_MULTIPLIER_HIGH
    estimated_impact_low: float = 0.0
    estimated_impact_high: float = 0.0
    jobs_estimate_low: float = 0.0
    jobs_estimate_high: float = 0.0
    fema_bcr: float | None = None
    methodology_citation: str = METHODOLOGY_CITATION
    is_benchmark: bool = False


@dataclass
class TribeEconomicSummary:
    """Aggregated economic impact summary for a single Tribe.

    Attributes:
        tribe_id: Unique Tribe identifier.
        tribe_name: Official BIA Tribe name.
        total_obligation: Sum of all program obligations.
        total_impact_low: Sum of all low impact estimates.
        total_impact_high: Sum of all high impact estimates.
        total_jobs_low: Sum of all low job estimates.
        total_jobs_high: Sum of all high job estimates.
        by_program: Per-program economic impact breakdowns.
        by_district: Per-district impact allocation (proportional by overlap_pct).
    """

    tribe_id: str
    tribe_name: str
    total_obligation: float = 0.0
    total_impact_low: float = 0.0
    total_impact_high: float = 0.0
    total_jobs_low: float = 0.0
    total_jobs_high: float = 0.0
    by_program: list[ProgramEconomicImpact] = field(default_factory=list)
    by_district: dict[str, dict] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Calculator
# ---------------------------------------------------------------------------

class EconomicImpactCalculator:
    """Calculates economic impact estimates from award data using published multipliers.

    Pure-function module: no file I/O, no network access.

    Usage::

        calc = EconomicImpactCalculator()
        summary = calc.compute(
            tribe_id="epa_001",
            tribe_name="Alpha Tribe",
            awards=[{"obligation": 500000, "program_id": "bia_tcr", "cfda": "15.156"}],
            districts=[{"district": "AZ-02", "overlap_pct": 95.0}],
            programs={"bia_tcr": {"id": "bia_tcr", "name": "BIA TCR", "priority": "critical"}},
        )
    """

    def compute(
        self,
        tribe_id: str,
        tribe_name: str,
        awards: list[dict],
        districts: list[dict],
        programs: dict[str, dict],
    ) -> TribeEconomicSummary:
        """Calculate economic impact for a Tribe across all programs.

        Args:
            tribe_id: Unique Tribe identifier.
            tribe_name: Official Tribe name.
            awards: List of award dicts with ``obligation``, ``program_id``, ``cfda``.
            districts: Congressional district dicts with ``district`` and ``overlap_pct``.
            programs: Dict mapping program_id to program metadata dict.

        Returns:
            TribeEconomicSummary with per-program and per-district breakdowns.
        """
        # Step 1: Group awards by program_id
        program_obligations: dict[str, float] = {}
        for award in awards:
            obligation = award.get("obligation", 0.0)
            if not isinstance(obligation, (int, float)):
                try:
                    obligation = float(obligation)
                except (ValueError, TypeError):
                    continue
            if obligation <= 0:
                continue

            program_id = award.get("program_id")
            if not program_id:
                # Fall back to CFDA normalization
                cfda = award.get("cfda")
                cfda_list = [cfda] if isinstance(cfda, str) else (cfda or [])
                program_id = cfda_list[0] if cfda_list else "unknown"

            program_obligations[program_id] = (
                program_obligations.get(program_id, 0.0) + obligation
            )

        # Step 2: Calculate impacts for programs WITH awards
        by_program: list[ProgramEconomicImpact] = []
        programs_with_awards: set[str] = set()

        for program_id, obligation in program_obligations.items():
            impact = self._calculate_program_impact(
                program_id=program_id,
                obligation=obligation,
                is_benchmark=False,
            )
            by_program.append(impact)
            programs_with_awards.add(program_id)

        # Step 3: For zero-award programs, use benchmark averages
        for program_id in programs:
            if program_id in programs_with_awards:
                continue
            benchmark = PROGRAM_BENCHMARK_AVERAGES.get(program_id)
            if benchmark is None:
                continue
            impact = self._calculate_program_impact(
                program_id=program_id,
                obligation=benchmark,
                is_benchmark=True,
            )
            by_program.append(impact)

        # Sort: actual awards first, then benchmarks, by obligation descending
        by_program.sort(
            key=lambda p: (p.is_benchmark, -p.total_obligation)
        )

        # Step 4: Aggregate totals
        total_obligation = sum(p.total_obligation for p in by_program)
        total_impact_low = sum(p.estimated_impact_low for p in by_program)
        total_impact_high = sum(p.estimated_impact_high for p in by_program)
        total_jobs_low = sum(p.jobs_estimate_low for p in by_program)
        total_jobs_high = sum(p.jobs_estimate_high for p in by_program)

        # Step 5: District allocation
        by_district: dict[str, dict] = {}
        valid_districts = [
            d for d in districts
            if d.get("overlap_pct") is not None and d["overlap_pct"] > 0
        ]

        for district_info in valid_districts:
            district_key = district_info.get("district", "unknown")
            overlap_frac = district_info["overlap_pct"] / 100.0
            by_district[district_key] = {
                "overlap_pct": district_info["overlap_pct"],
                "impact_low": total_impact_low * overlap_frac,
                "impact_high": total_impact_high * overlap_frac,
                "jobs_low": total_jobs_low * overlap_frac,
                "jobs_high": total_jobs_high * overlap_frac,
                "obligation": total_obligation * overlap_frac,
            }

        return TribeEconomicSummary(
            tribe_id=tribe_id,
            tribe_name=tribe_name,
            total_obligation=total_obligation,
            total_impact_low=total_impact_low,
            total_impact_high=total_impact_high,
            total_jobs_low=total_jobs_low,
            total_jobs_high=total_jobs_high,
            by_program=by_program,
            by_district=by_district,
        )

    def _calculate_program_impact(
        self,
        program_id: str,
        obligation: float,
        is_benchmark: bool,
    ) -> ProgramEconomicImpact:
        """Calculate economic impact for a single program.

        Args:
            program_id: Program identifier.
            obligation: Total obligation amount in dollars.
            is_benchmark: True if using benchmark average (not actual awards).

        Returns:
            ProgramEconomicImpact with calculated multiplier ranges.
        """
        impact_low = obligation * BEA_MULTIPLIER_LOW
        impact_high = obligation * BEA_MULTIPLIER_HIGH
        jobs_low = (obligation / 1_000_000) * BLS_JOBS_PER_MILLION_LOW
        jobs_high = (obligation / 1_000_000) * BLS_JOBS_PER_MILLION_HIGH

        fema_bcr: float | None = None
        if program_id in MITIGATION_PROGRAM_IDS:
            fema_bcr = FEMA_BCR_OVERALL

        return ProgramEconomicImpact(
            program_id=program_id,
            total_obligation=obligation,
            estimated_impact_low=impact_low,
            estimated_impact_high=impact_high,
            jobs_estimate_low=jobs_low,
            jobs_estimate_high=jobs_high,
            fema_bcr=fema_bcr,
            is_benchmark=is_benchmark,
        )

    def format_impact_narrative(
        self,
        impact: ProgramEconomicImpact,
        tribe_name: str,
        program_name: str,
    ) -> str:
        """Format a natural-language economic impact narrative.

        Args:
            impact: The ProgramEconomicImpact to describe.
            tribe_name: Official Tribe name for the narrative.
            program_name: Human-readable program name.

        Returns:
            Narrative string suitable for DOCX rendering.
        """
        low_str = _format_dollars(impact.estimated_impact_low)
        high_str = _format_dollars(impact.estimated_impact_high)
        jobs_low = int(round(impact.jobs_estimate_low))
        jobs_high = int(round(impact.jobs_estimate_high))

        if impact.is_benchmark:
            return (
                f"Based on program averages, a successful {program_name} "
                f"application could generate an estimated {low_str}-{high_str} "
                f"in regional economic impact, supporting approximately "
                f"{jobs_low}-{jobs_high} jobs (BEA RIMS II methodology, "
                f"output multiplier range 1.8-2.4x; BLS employment "
                f"requirements methodology)."
            )

        return (
            f"{program_name} funding to {tribe_name} generated an estimated "
            f"{low_str}-{high_str} in regional economic activity "
            f"(BEA RIMS II methodology, output multiplier range 1.8-2.4x), "
            f"supporting approximately {jobs_low}-{jobs_high} jobs "
            f"(BLS employment requirements methodology)."
        )

    def format_bcr_narrative(
        self, impact: ProgramEconomicImpact
    ) -> str | None:
        """Format a FEMA BCR narrative for mitigation programs.

        Args:
            impact: The ProgramEconomicImpact to check.

        Returns:
            BCR narrative string for mitigation programs, None otherwise.
        """
        if impact.fema_bcr is None:
            return None

        return (
            "Every federal dollar invested in hazard mitigation generates an "
            f"estimated ${impact.fema_bcr:.0f} in future avoided costs "
            "(FEMA/NIBS MitSaves, 2018)."
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_dollars(amount: float) -> str:
    """Format a dollar amount with commas and no decimals.

    Args:
        amount: Dollar amount.

    Returns:
        Formatted string like "$1,234,567".
    """
    return f"${amount:,.0f}"
