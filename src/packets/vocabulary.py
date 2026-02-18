"""Sovereignty-first vulnerability framing vocabulary constants.

Constants-only module providing the single source of truth for all framing
language used in vulnerability and resilience sections across Doc A/B/C/D/E.

REG-04 requirement: Renderers import these constants at construction time
instead of embedding raw vulnerability/resilience terminology. No classes with
methods. No runtime computation. Pure constants.

Design decisions (Phase 18.5, DEC-05 Option D Hybrid):
- Headings use "Climate Resilience Investment" framing, never "vulnerability"
- "vulnerability" appears ONLY inside federal proper noun strings (e.g.,
  "Social Vulnerability Index", "National Risk Index")
- Data gaps are framed as federal infrastructure failures, never as Tribal
  deficiencies
- SVI Theme 3 exclusion explained through sovereignty framing
- Strategy terms are blocked in congressional-audience documents (Doc B/D)

Import pattern: Only ``from dataclasses import dataclass``. This is a leaf
module with zero project dependencies.
"""

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# 1. Section headings by document type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SectionHeadings:
    """Section heading strings for climate resilience content by document type.

    Each document type receives a distinct heading that reflects its audience
    and scope. None of these headings contain the word "vulnerability" --
    framing uses "Climate Resilience Investment" language per DEC-05.
    """

    doc_a_main: str = "Climate Resilience Investment Profile"
    doc_b_main: str = "Climate Resilience Data Summary"
    doc_c_main: str = "Regional Climate Resilience Investment Profile"
    doc_d_main: str = "Regional Climate Resilience Data Summary"
    doc_e_main: str = "Climate Resilience Investment Assessment"


SECTION_HEADINGS = SectionHeadings()
"""Singleton instance of section headings for all document types."""


# ---------------------------------------------------------------------------
# 2. Rating label
# ---------------------------------------------------------------------------

RATING_LABEL: str = "Resilience Investment Priority"
"""Label used in documents: 'Resilience Investment Priority: [tier]'.

Uses investment-framing language. Does not contain 'vulnerability'.
"""


# ---------------------------------------------------------------------------
# 3. Tier display configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TierDisplay:
    """Display configuration for an investment priority tier.

    Attributes:
        label: Tier name (e.g. "Critical").
        color_hex: Hex color string for badges and website rendering.
        description: One-line description of what this tier signifies.
    """

    label: str
    color_hex: str
    description: str


TIER_DISPLAYS: dict[str, TierDisplay] = {
    "Critical": TierDisplay(
        "Critical",
        "#DC2626",
        "Immediate and significant climate resilience investment needed",
    ),
    "High": TierDisplay(
        "High",
        "#EA580C",
        "Substantial climate resilience investment needed",
    ),
    "Elevated": TierDisplay(
        "Elevated",
        "#B45309",
        "Meaningful climate resilience investment needed",
    ),
    "Moderate": TierDisplay(
        "Moderate",
        "#2563EB",
        "Climate resilience investment beneficial",
    ),
    "Low": TierDisplay(
        "Low",
        "#16A34A",
        "Current resilience capacity addresses primary climate exposures",
    ),
}
"""Tier display configs keyed by tier name. Colors match WCAG-compliant palette."""


# ---------------------------------------------------------------------------
# 4. Data gap messages
# ---------------------------------------------------------------------------

GAP_MESSAGES: dict[str, str] = {
    "MISSING_SVI": (
        "CDC Social Vulnerability Index data is not available for this area. "
        "Federal social determinant surveys do not yet provide complete "
        "coverage for all Tribal geographic boundaries."
    ),
    "PARTIAL_NRI": (
        "FEMA National Risk Index data provides partial coverage for this "
        "Nation's geographic area. Scores reflect partial land area with "
        "federal hazard assessment."
    ),
    "ZERO_AREA_WEIGHT": (
        "Federal geographic datasets do not map county boundaries to this "
        "Nation's land area. This is a federal data infrastructure gap, not "
        "a reflection of climate exposure."
    ),
    "ALASKA_PARTIAL": (
        "Federal climate data infrastructure does not provide county-level "
        "coverage for Alaska. Available data reflects {available_sources}. "
        "Gaps represent federal assessment failures, not absence of "
        "climate risk."
    ),
    "NO_COASTAL_DATA": "",
    "SOURCE_UNAVAILABLE": (
        "{source_name} data was unavailable during the most recent data "
        "acquisition cycle. This profile will be updated when the source "
        "is restored."
    ),
}
"""Data gap messages keyed by gap type.

All non-empty messages frame data absence as federal infrastructure failures,
not Tribal deficiencies. Messages may contain ``{placeholder}`` strings for
runtime formatting.
"""


# ---------------------------------------------------------------------------
# 5. Inline gap markers
# ---------------------------------------------------------------------------

INLINE_PARTIAL: str = "[partial coverage]"
"""Inline marker for partial data coverage in table cells."""

INLINE_GAP: str = "[federal data gap]"
"""Inline marker for complete data gaps in table cells."""


# ---------------------------------------------------------------------------
# 6. SVI Theme 3 exclusion notes
# ---------------------------------------------------------------------------

SVI_THEME3_EXCLUSION_NOTE: str = (
    "Social Vulnerability Methodology\n\n"
    "This assessment uses a custom Tribal Social Vulnerability composite "
    "derived from three CDC SVI 2022 themes: Socioeconomic Status, "
    "Household Characteristics & Disability, and Housing Type & "
    "Transportation.\n\n"
    "The CDC SVI Theme 3 (Racial & Ethnic Minority Status) is intentionally "
    "excluded. Federal racial categorization frameworks impose external "
    "identity classifications that do not reflect Tribal Nations' "
    "self-determined understanding of community resilience factors. Tribal "
    "sovereignty includes the right to define which metrics meaningfully "
    "represent community conditions.\n\n"
    "The resulting 3-theme composite provides a methodologically sound and "
    "culturally appropriate measure of social determinants affecting climate "
    "resilience capacity."
)
"""Full sovereignty-framing text explaining SVI Theme 3 exclusion.

Used in Doc A/C/E methodology sections where space permits detailed
explanation.
"""

SVI_THEME3_SHORT: str = "assessed using 3 CDC SVI themes"
"""Abbreviated SVI methodology note for Doc B/D where brevity is required."""


# ---------------------------------------------------------------------------
# 7. Context-sensitive terms
# ---------------------------------------------------------------------------

CONTEXT_SENSITIVE_TERMS: dict[str, list[str]] = {
    "vulnerable": [
        "Social Vulnerability Index",
        "CDC/ATSDR Social Vulnerability",
    ],
    "vulnerability": [
        "Social Vulnerability Index",
        "National Risk Index",
        "Climate Vulnerability",
    ],
}
"""Terms that may only appear inside federal proper noun contexts.

The words "vulnerable" and "vulnerability" are permitted ONLY when they appear
as part of the listed federal program/dataset proper nouns. They must not be
used as standalone descriptors of Tribal Nations or communities.
"""


# ---------------------------------------------------------------------------
# 8. Forbidden Doc B / Doc D terms
# ---------------------------------------------------------------------------

FORBIDDEN_DOC_B_TERMS: frozenset[str] = frozenset({
    "strategic",
    "strategy",
    "leverage",
    "leveraging",
    "approach",
    "messaging",
    "talking point",
    "talking points",
    "assertive",
    "advocacy lever",
    "member approach",
    "investment priority",
    "investment profile",
    "resilience capacity",
    "adaptive capacity",
    "disproportionate",
    "disproportionately",
})
"""Terms blocked in congressional-audience documents (Doc B and Doc D).

These strategy and advocacy terms must not appear in documents intended for
congressional offices. The air gap ensures Doc B/D contain only objective
facts and policy recommendations.
"""


# ---------------------------------------------------------------------------
# 9. Explanatory framing text
# ---------------------------------------------------------------------------

EXPOSURE_CONTEXT: str = "disproportionate exposure to climate hazards"
"""Standard context phrase for describing climate exposure patterns."""

COMPOSITE_METHODOLOGY_BRIEF: str = (
    "Composite score derived from FEMA National Risk Index hazard exposure, "
    "CDC Social Vulnerability Index social determinants, and NRI community "
    "resilience capacity assessment."
)
"""Brief methodology description for composite vulnerability scoring.

Used in summary sections where full methodology detail is not appropriate.
References federal data sources by their proper names.
"""
