# River Runner Report: Schema & Validation Architecture
## Phase 18.5 | TCR Policy Scanner v1.4

### Executive Summary

This report defines the complete Pydantic v2 schema hierarchy for vulnerability profiles -- the contract that Phases 19-24 implement against. Key decisions:

1. **Composite score revised to 3-component formula** (LOCA2 deferred): 0.40 hazard exposure + 0.35 social vulnerability + 0.25 adaptive capacity deficit. The climate projection component is structurally present but zeroed in v1.4, with a `data_completeness_factor` discount applied when components are missing.

2. **National percentile computed at build time** from `RISK_SCORE` rank across ~3,200 counties (Sovereignty Scout confirmed `RISK_NPCTL` does not exist in NRI v1.20). Stored as `risk_national_percentile` on `NRIExpandedProfile`.

3. **Custom Tribal SVI composite** from Themes 1+2+4 via simple average of `RPL_THEME1 + RPL_THEME2 + RPL_THEME4` (Theme 3 excluded per requirements). Stored as `tribal_svi_composite` on `SVIProfile`.

4. **37 Pydantic models** organized across 4 schema modules: `vulnerability.py` (core, 11 models), `flood.py` (6 models), `climate.py` (4 models), `infrastructure.py` (4 models) -- plus 12 supporting types.

5. **Test target: ~1,200 tests** by v1.4 completion (964 current + ~240 new across Phases 19-24).

6. **Every model handles missing data** via `Optional` fields with `None` defaults, explicit `coverage_status` enums, and `_safe_float()`-equivalent validation on all numeric fields.

---

### Existing Schema Analysis

#### Pydantic v2 Patterns in `src/schemas/models.py`

The codebase has 1,261 lines of Pydantic v2 models across 19 model classes. Key patterns extracted from actual code inspection:

**Import pattern:**
```python
from __future__ import annotations
from typing import Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator
```

**Validation pattern (frozenset membership):**
```python
CI_STATUSES = frozenset({"SECURE", "STABLE", ...})

@field_validator("status")
@classmethod
def validate_status(cls, v: str) -> str:
    if v not in CI_STATUSES:
        raise ValueError(f"Invalid CI status '{v}'. Must be one of: {sorted(CI_STATUSES)}")
    return v
```

**Model validator pattern (cross-field):**
```python
@model_validator(mode="after")
def validate_specialist_fields(self) -> "ProgramRecord":
    if self.specialist_required and not self.specialist_focus:
        raise ValueError(...)
    return self
```

**Field pattern (defaults, descriptions, examples, constraints):**
```python
risk_score: float = Field(default=0.0, ge=0.0, description="NRI risk score...")
tribe_id: str = Field(..., description="EPA Tribal identifier", examples=["epa_100000001"])
awards: list[FundingRecord] = Field(default_factory=list, description="...")
```

**tribe_id validation pattern (reused in 5 models):**
```python
@field_validator("tribe_id")
@classmethod
def validate_tribe_id_format(cls, v: str) -> str:
    if not v.startswith("epa_"):
        raise ValueError(f"tribe_id must start with 'epa_', got '{v}'")
    numeric_part = v[4:]
    if not numeric_part.isdigit():
        raise ValueError(f"tribe_id numeric portion must be all digits, got '{numeric_part}'")
    return v
```

**Nested model pattern:** Models compose via typed fields (`NRISource` contains `NRIComposite` and `dict[str, HazardDetail]`). The `HazardProfile` model uses `dict` for `sources` with a structure validator, then provides `get_nri_source()` for lazy typed parsing.

**Module organization:**
- `src/schemas/models.py` -- all models in one file (1,261 lines)
- `src/schemas/__init__.py` -- re-exports all models with `__all__`

**Decision for v1.4:** Create `src/schemas/vulnerability.py` as a new module following the same pattern. The existing `models.py` is already at 1,261 lines; adding ~500 lines of vulnerability models there would make it unwieldy. A separate module is consistent with the principle of one file per domain.

---

### Vulnerability Schema Architecture

#### File Organization

```
src/schemas/
    __init__.py              # Updated with vulnerability exports
    models.py                # Existing (unchanged)
    vulnerability.py         # NEW: Core vulnerability models (Phase 19)
    flood.py                 # NEW: Flood data models (Phase 20)
    climate.py               # NEW: Climate & weather models (Phase 21)
    infrastructure.py        # NEW: Geologic & infrastructure models (Phase 21)
```

#### Shared Constants and Validators

```python
# src/schemas/vulnerability.py -- top of file

"""Pydantic v2 validation models for vulnerability profile data structures.

Defines the schema contract for v1.4 Climate Vulnerability Intelligence:
- SVIProfile: CDC/ATSDR Social Vulnerability Index (3 themes, Theme 3 excluded)
- NRIExpandedProfile: Expanded FEMA NRI metrics (EAL components, national percentile)
- ClimateProjectionProfile: LOCA2 placeholder (deferred to v1.5+)
- CompositeVulnerability: Weighted composite score with rating tier
- VulnerabilityProfile: Top-level per-Tribe vulnerability container

All models handle missing data gracefully. Every numeric field that may
originate from CSV parsing uses validators equivalent to hazards._safe_float().

Schema-first: these models are the contract that all population scripts,
builders, and renderers implement against.
"""

from __future__ import annotations

import math
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ── Rating Tiers ──

class VulnerabilityRating(str, Enum):
    """Five-tier vulnerability rating aligned with FEMA NRI methodology.

    Uses the same quintile breakpoints as score_to_rating() in hazards.py
    for consistency across all vulnerability displays.
    """
    VERY_HIGH = "Very High"
    HIGH = "Relatively High"
    MODERATE = "Relatively Moderate"
    LOW = "Relatively Low"
    VERY_LOW = "Very Low"


class CoverageStatus(str, Enum):
    """Data coverage classification for a vulnerability component.

    Used in coverage reports and document rendering to communicate
    data completeness to Tribal Leaders honestly.
    """
    FULL = "full"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"
    NOT_APPLICABLE = "not_applicable"


# ── SVI Theme Identifiers ──

SVI_INCLUDED_THEMES = frozenset({"theme1", "theme2", "theme4"})
"""SVI themes included in the Tribal SVI composite.
Theme 3 (Racial & Ethnic Minority Status) is excluded per requirements --
it introduces a tautological signal for Indigenous Nations."""

NRI_EAL_COMPONENTS = frozenset({"buildings", "population", "agriculture"})
"""EAL consequence types from NRI v1.20 (VALB, VALP, VALA)."""


# ── Shared Validators ──

def _validate_unit_float(v: float | None, field_name: str = "field") -> float:
    """Validate a float is in [0.0, 1.0] range, handling NaN/Inf.

    Equivalent to hazards._safe_float() but for unit-interval fields.
    Returns 0.0 for None/NaN/Inf instead of raising.
    """
    if v is None:
        return 0.0
    if math.isnan(v) or math.isinf(v):
        return 0.0
    return max(0.0, min(1.0, v))


def _validate_nonneg_float(v: float | None) -> float:
    """Validate a non-negative float, handling NaN/Inf.

    Returns 0.0 for None/NaN/Inf. Clamps negative values to 0.0.
    """
    if v is None:
        return 0.0
    if math.isnan(v) or math.isinf(v):
        return 0.0
    return max(0.0, v)
```

#### Core Models (Phase 19)

##### SVIProfile

```python
class SVITheme(BaseModel):
    """Individual SVI theme score from CDC/ATSDR SVI 2022.

    Each theme is a percentile ranking (0-1) representing relative
    social vulnerability for that dimension across US counties.
    """

    theme_id: str = Field(
        ...,
        description="Theme identifier (theme1, theme2, theme4)",
        examples=["theme1", "theme2", "theme4"],
    )
    name: str = Field(
        ...,
        description="Human-readable theme name",
        examples=[
            "Socioeconomic Status",
            "Household Characteristics",
            "Housing Type & Transportation",
        ],
    )
    percentile: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="SVI percentile ranking for this theme (0-1). "
                    "Higher = more vulnerable.",
    )
    flag_count: int = Field(
        default=0,
        ge=0,
        description="Number of component variables above 90th percentile "
                    "(F_* flags from SVI CSV).",
    )

    @field_validator("theme_id")
    @classmethod
    def validate_theme_id(cls, v: str) -> str:
        if v not in SVI_INCLUDED_THEMES:
            raise ValueError(
                f"Invalid theme_id '{v}'. Must be one of: {sorted(SVI_INCLUDED_THEMES)}. "
                f"Theme 3 (Racial & Ethnic Minority Status) is excluded for Tribal Nations."
            )
        return v

    @field_validator("percentile", mode="before")
    @classmethod
    def sanitize_percentile(cls, v: float | None) -> float:
        return _validate_unit_float(v, "percentile")


class SVIProfile(BaseModel):
    """CDC/ATSDR Social Vulnerability Index profile for a Tribal Nation.

    Computed from SVI 2022 county-level data aggregated to Tribal areas
    via the existing area-weighted crosswalk (tribal_county_area_weights.json).

    IMPORTANT: The overall RPL_THEMES column from SVI includes Theme 3
    (Racial & Ethnic Minority Status), which is EXCLUDED for Tribal Nations
    because it is tautological for Indigenous communities. The
    tribal_svi_composite field is computed from Themes 1+2+4 only.
    """

    themes: list[SVITheme] = Field(
        default_factory=list,
        description="SVI theme scores (3 themes: socioeconomic, household, housing). "
                    "Theme 3 excluded per requirements.",
        max_length=3,
    )
    tribal_svi_composite: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Custom Tribal SVI composite: average of Theme 1 + Theme 2 + Theme 4 "
                    "percentiles. Does NOT use RPL_THEMES (which includes excluded Theme 3).",
    )
    rpl_themes_raw: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Original RPL_THEMES value from SVI CSV (includes Theme 3). "
                    "Stored for reference but NOT used in composite scoring.",
    )
    counties_analyzed: int = Field(
        default=0,
        ge=0,
        description="Number of counties contributing to this SVI profile.",
    )
    source_version: str = Field(
        default="SVI 2022",
        description="CDC SVI data version.",
        examples=["SVI 2022"],
    )
    data_vintage: str = Field(
        default="2018-2022 ACS 5-Year",
        description="Underlying ACS data vintage.",
    )
    coverage_status: CoverageStatus = Field(
        default=CoverageStatus.UNAVAILABLE,
        description="Data coverage classification for this Tribe.",
    )

    @field_validator("tribal_svi_composite", mode="before")
    @classmethod
    def sanitize_composite(cls, v: float | None) -> float:
        return _validate_unit_float(v, "tribal_svi_composite")

    @model_validator(mode="after")
    def validate_theme_count(self) -> "SVIProfile":
        """Ensure at most 3 themes and composite is consistent."""
        if len(self.themes) > 3:
            raise ValueError(
                f"SVIProfile may have at most 3 themes (1, 2, 4), got {len(self.themes)}"
            )
        if self.themes and self.counties_analyzed > 0:
            avg = sum(t.percentile for t in self.themes) / len(self.themes)
            # Allow small floating point tolerance
            if abs(self.tribal_svi_composite - avg) > 0.01:
                raise ValueError(
                    f"tribal_svi_composite ({self.tribal_svi_composite:.4f}) does not match "
                    f"average of theme percentiles ({avg:.4f})"
                )
        return self
```

##### NRIExpandedProfile

```python
class EALBreakdown(BaseModel):
    """Expected Annual Loss breakdown by consequence type.

    Provides dollar-denominated loss estimates for buildings, population
    (equivalence), and agriculture. These figures are the single most
    grant-relevant data point in the vulnerability profile -- they give
    Tribal Leaders concrete dollar amounts for testimony and applications.
    """

    buildings: float = Field(
        default=0.0,
        ge=0.0,
        description="Expected Annual Loss to buildings (USD). NRI field: EAL_VALB.",
    )
    population: float = Field(
        default=0.0,
        ge=0.0,
        description="Expected Annual Loss to population equivalence (USD). NRI field: EAL_VALPE.",
    )
    agriculture: float = Field(
        default=0.0,
        ge=0.0,
        description="Expected Annual Loss to agriculture (USD). NRI field: EAL_VALA.",
    )
    total: float = Field(
        default=0.0,
        ge=0.0,
        description="Total Expected Annual Loss (USD). NRI field: EAL_VALT. "
                    "Note: total may exceed sum of B+P+A due to population equivalence methodology.",
    )

    @field_validator("buildings", "population", "agriculture", "total", mode="before")
    @classmethod
    def sanitize_eal(cls, v: float | None) -> float:
        return _validate_nonneg_float(v)


class PerHazardEAL(BaseModel):
    """Per-hazard EAL breakdown for a single NRI hazard type.

    Extends the existing HazardDetail with consequence-type EAL components.
    """

    hazard_code: str = Field(
        ...,
        description="NRI hazard type code (e.g., WFIR, DRGT, HRCN).",
    )
    hazard_name: str = Field(
        default="",
        description="Human-readable hazard name.",
    )
    risk_score: float = Field(default=0.0, ge=0.0)
    risk_rating: str = Field(default="")
    eal_buildings: float = Field(
        default=0.0,
        ge=0.0,
        description="Per-hazard EAL to buildings. NRI field: {CODE}_EALB.",
    )
    eal_population: float = Field(
        default=0.0,
        ge=0.0,
        description="Per-hazard EAL to population equivalence. NRI field: {CODE}_EALPE.",
    )
    eal_agriculture: float = Field(
        default=0.0,
        ge=0.0,
        description="Per-hazard EAL to agriculture. NRI field: {CODE}_EALA.",
    )
    eal_total: float = Field(
        default=0.0,
        ge=0.0,
        description="Per-hazard total EAL. NRI field: {CODE}_EALT.",
    )

    @field_validator(
        "risk_score", "eal_buildings", "eal_population",
        "eal_agriculture", "eal_total", mode="before"
    )
    @classmethod
    def sanitize_floats(cls, v: float | None) -> float:
        return _validate_nonneg_float(v)


class NRIExpandedProfile(BaseModel):
    """Expanded FEMA NRI profile with EAL components and national percentile.

    Extends the existing NRIComposite/NRISource models with:
    - EAL breakdown by consequence type (buildings, population, agriculture)
    - Computed national percentile (from RISK_SCORE rank, since RISK_NPCTL
      does not exist in NRI v1.20)
    - State percentile (RISK_SPCTL from NRI CSV)
    - Community resilience score and rating
    - Population and building value for context

    All fields use _safe_float()-equivalent validation for NaN/Inf/sentinel guards.
    """

    eal_breakdown: EALBreakdown = Field(
        default_factory=EALBreakdown,
        description="EAL by consequence type (buildings, population, agriculture).",
    )
    per_hazard_eal: list[PerHazardEAL] = Field(
        default_factory=list,
        description="Per-hazard EAL breakdowns for top hazards.",
    )
    risk_score: float = Field(
        default=0.0,
        ge=0.0,
        description="Composite NRI risk score (area-weighted across counties).",
    )
    risk_rating: str = Field(
        default="",
        description="Re-derived rating from weighted risk_score.",
    )
    risk_national_percentile: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="National percentile computed from RISK_SCORE rank across "
                    "all ~3,200 US counties at build time. NOT from NRI CSV "
                    "(RISK_NPCTL does not exist in v1.20).",
    )
    risk_state_percentile: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="State percentile from NRI CSV field RISK_SPCTL.",
    )
    community_resilience_score: float = Field(
        default=0.0,
        ge=0.0,
        description="Community resilience score (NRI RESL_SCORE).",
    )
    community_resilience_rating: str = Field(
        default="",
        description="Community resilience rating (re-derived from weighted score).",
    )
    social_vulnerability_score: float = Field(
        default=0.0,
        ge=0.0,
        description="NRI social vulnerability score (SOVI_SCORE). "
                    "Note: This is NRI's internal SOVI, distinct from CDC SVI.",
    )
    social_vulnerability_rating: str = Field(
        default="",
        description="NRI social vulnerability rating.",
    )
    population: int = Field(
        default=0,
        ge=0,
        description="Total population in Tribal area (area-weighted from NRI POPULATION).",
    )
    building_value: float = Field(
        default=0.0,
        ge=0.0,
        description="Total building value in USD (area-weighted from NRI BUILDVALUE).",
    )
    counties_analyzed: int = Field(
        default=0,
        ge=0,
        description="Number of NRI counties contributing to this profile.",
    )
    nri_version: str = Field(
        default="",
        description="NRI data version (e.g., '1.20').",
        examples=["1.20"],
    )
    coverage_status: CoverageStatus = Field(
        default=CoverageStatus.UNAVAILABLE,
        description="Data coverage classification.",
    )

    @field_validator(
        "risk_score", "risk_national_percentile", "risk_state_percentile",
        "community_resilience_score", "social_vulnerability_score",
        "building_value", mode="before"
    )
    @classmethod
    def sanitize_scores(cls, v: float | None) -> float:
        return _validate_nonneg_float(v)

    @field_validator("population", mode="before")
    @classmethod
    def sanitize_population(cls, v: int | float | None) -> int:
        if v is None:
            return 0
        if isinstance(v, float):
            if math.isnan(v) or math.isinf(v):
                return 0
            return max(0, int(round(v)))
        return max(0, v)
```

##### ClimateProjectionProfile (Placeholder)

```python
class ClimateProjectionProfile(BaseModel):
    """PLACEHOLDER: Climate projection data from LOCA2.

    DEFERRED TO v1.5+. This model exists in the schema to establish the
    contract for future climate projection integration. In v1.4, all
    instances will have status=UNAVAILABLE.

    Deferral reasons (validated by Sovereignty Scout):
    1. LOCA2 is CONUS-only -- 229/592 (38.7%) Alaska Tribes have ZERO coverage
    2. Full dataset is 383 GB; county CSV thresholds extract is 2.18 GB
    3. Alaska requires separate SNAP (UAF) data source

    When implemented in v1.5+, use LOCA2 Thresholds CSV (not primary NetCDF)
    to avoid xarray/netCDF4 dependency.
    """

    status: CoverageStatus = Field(
        default=CoverageStatus.UNAVAILABLE,
        description="Always UNAVAILABLE in v1.4. Will be FULL/PARTIAL in v1.5+.",
    )
    reason: str = Field(
        default="LOCA2 climate projections deferred to v1.5+ (CONUS-only; "
                "229 Alaska Native communities have no coverage)",
        description="Human-readable explanation for unavailability.",
    )
    # v1.5+ fields -- all Optional with None defaults
    extreme_heat_days: Optional[float] = Field(
        default=None,
        description="v1.5+: Projected days above 95F (LOCA2 TX95pDAYS).",
    )
    extreme_heat_100f_days: Optional[float] = Field(
        default=None,
        description="v1.5+: Projected days above 100F (LOCA2 TXge100F).",
    )
    frost_days: Optional[float] = Field(
        default=None,
        description="v1.5+: Projected frost days below 32F (LOCA2 FD).",
    )
    consecutive_dry_days: Optional[float] = Field(
        default=None,
        description="v1.5+: Projected consecutive dry days (LOCA2 CDD).",
    )
    heavy_precip_days: Optional[float] = Field(
        default=None,
        description="v1.5+: Projected heavy precipitation days >1in (LOCA2 R1in).",
    )
    scenario: Optional[str] = Field(
        default=None,
        description="v1.5+: SSP scenario (e.g., 'SSP2-4.5', 'SSP5-8.5').",
    )
    projection_period: Optional[str] = Field(
        default=None,
        description="v1.5+: Time period (e.g., '2040-2059', '2080-2099').",
    )
    source: Optional[str] = Field(
        default=None,
        description="v1.5+: Data source ('LOCA2' for CONUS, 'SNAP' for Alaska).",
    )
```

##### CompositeVulnerability

```python
class ComponentScore(BaseModel):
    """Individual component of the composite vulnerability score.

    Each component represents one dimension of vulnerability with a
    normalized score (0-1), weight, and data availability flag.
    """

    component: str = Field(
        ...,
        description="Component identifier.",
        examples=[
            "hazard_exposure",
            "social_vulnerability",
            "adaptive_capacity_deficit",
            "climate_projection",
        ],
    )
    raw_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Normalized component score (0-1). "
                    "0 = lowest vulnerability, 1 = highest.",
    )
    weight: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Weight applied to this component in the composite. "
                    "Weights across available components sum to 1.0.",
    )
    weighted_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="raw_score * weight.",
    )
    available: bool = Field(
        default=False,
        description="Whether source data exists for this component. "
                    "If False, weight is redistributed to available components.",
    )
    source_description: str = Field(
        default="",
        description="Data source for this component.",
        examples=[
            "FEMA NRI v1.20 risk_national_percentile / 100",
            "CDC SVI 2022 tribal_svi_composite (Themes 1+2+4)",
            "1.0 - (NRI RESL_SCORE / 100) [inverted: higher = more deficit]",
        ],
    )

    @field_validator("raw_score", "weight", "weighted_score", mode="before")
    @classmethod
    def sanitize_unit(cls, v: float | None) -> float:
        return _validate_unit_float(v)

    @model_validator(mode="after")
    def validate_weighted_score(self) -> "ComponentScore":
        expected = round(self.raw_score * self.weight, 6)
        actual = round(self.weighted_score, 6)
        if abs(expected - actual) > 0.001:
            raise ValueError(
                f"weighted_score ({self.weighted_score}) != "
                f"raw_score ({self.raw_score}) * weight ({self.weight}) = {expected}"
            )
        return self


class CompositeVulnerability(BaseModel):
    """Composite vulnerability score for a Tribal Nation.

    Combines hazard exposure, social vulnerability, and adaptive capacity
    deficit into a single 0-1 score with a 5-tier rating.

    v1.4 Formula (3-component, LOCA2 deferred):
        score = 0.40 * hazard_exposure
              + 0.35 * social_vulnerability
              + 0.25 * adaptive_capacity_deficit

    When components are missing, their weights are redistributed
    proportionally across available components, and a
    data_completeness_factor is applied as a quality discount.

    v1.5+ Formula (4-component, with LOCA2):
        score = 0.30 * hazard_exposure
              + 0.25 * social_vulnerability
              + 0.25 * climate_projection
              + 0.20 * adaptive_capacity_deficit
    """

    score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Final composite vulnerability score (0-1). "
                    "Higher = more vulnerable to climate hazards.",
    )
    rating: VulnerabilityRating = Field(
        default=VulnerabilityRating.VERY_LOW,
        description="Five-tier rating derived from score using quintile breakpoints.",
    )
    components: list[ComponentScore] = Field(
        default_factory=list,
        description="Individual component scores contributing to the composite.",
    )
    data_completeness_factor: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Fraction of total weight covered by available data. "
                    "1.0 = all components available; <1.0 = missing data. "
                    "In v1.4 this is always <= 0.75 because climate_projection "
                    "is deferred (0.25 weight unavailable in 4-component formula). "
                    "Under 3-component formula, 1.0 if all 3 present.",
    )
    confidence_note: str = Field(
        default="",
        description="Human-readable note about score reliability. "
                    "Included in documents to communicate data limitations honestly.",
        examples=[
            "Full data: all vulnerability components available.",
            "Partial data: SVI data unavailable for this county. Score based on "
            "hazard exposure and adaptive capacity only.",
            "Limited data: Only hazard exposure data available. "
            "Composite score may not reflect full vulnerability.",
        ],
    )
    formula_version: str = Field(
        default="v1.4-3c",
        description="Formula version identifier. 'v1.4-3c' = 3-component (no LOCA2). "
                    "'v1.5-4c' = 4-component (with LOCA2).",
    )

    @field_validator("score", "data_completeness_factor", mode="before")
    @classmethod
    def sanitize_scores(cls, v: float | None) -> float:
        return _validate_unit_float(v)

    @model_validator(mode="after")
    def validate_rating_consistency(self) -> "CompositeVulnerability":
        """Ensure rating matches score using quintile breakpoints."""
        expected = _score_to_vulnerability_rating(self.score)
        if self.rating != expected:
            raise ValueError(
                f"rating '{self.rating.value}' inconsistent with score {self.score}. "
                f"Expected '{expected.value}'."
            )
        return self


def _score_to_vulnerability_rating(score: float) -> VulnerabilityRating:
    """Convert 0-1 vulnerability score to rating tier.

    Quintile breakpoints (consistent with NRI score_to_rating()):
        >= 0.80 -> Very High
        >= 0.60 -> Relatively High
        >= 0.40 -> Relatively Moderate
        >= 0.20 -> Relatively Low
        <  0.20 -> Very Low
    """
    if score >= 0.80:
        return VulnerabilityRating.VERY_HIGH
    elif score >= 0.60:
        return VulnerabilityRating.HIGH
    elif score >= 0.40:
        return VulnerabilityRating.MODERATE
    elif score >= 0.20:
        return VulnerabilityRating.LOW
    else:
        return VulnerabilityRating.VERY_LOW
```

##### VulnerabilityProfile (Top-Level)

```python
class DataSourceMeta(BaseModel):
    """Provenance metadata for a single data source within the profile."""

    source_name: str = Field(
        ...,
        description="Data source identifier.",
        examples=["FEMA NRI v1.20", "CDC SVI 2022", "OpenFEMA NFIP v2"],
    )
    source_url: str = Field(
        default="",
        description="Canonical URL for the data source.",
    )
    acquisition_date: str = Field(
        default="",
        description="ISO date when data was acquired (YYYY-MM-DD).",
    )
    version: str = Field(
        default="",
        description="Data version or release identifier.",
    )
    coverage_status: CoverageStatus = Field(
        default=CoverageStatus.UNAVAILABLE,
        description="Coverage status for this Tribe.",
    )
    notes: str = Field(
        default="",
        description="Additional context (e.g., 'County-level data aggregated via crosswalk').",
    )


class VulnerabilityProfile(BaseModel):
    """Per-Tribe vulnerability profile composing all data sources.

    Top-level container written to vulnerability_profiles/{tribe_id}.json.
    Consumed by PacketOrchestrator -> TribePacketContext -> renderers.

    Maps to requirement VULN-04: Per-Tribe vulnerability profiles (592 JSON files)
    in vulnerability_profiles/ directory with data provenance metadata.
    """

    tribe_id: str = Field(
        ...,
        description="EPA Tribal identifier.",
        examples=["epa_100000001"],
    )
    tribe_name: str = Field(
        ...,
        description="Official BIA Tribal Nation name.",
    )

    # Core vulnerability components
    composite: CompositeVulnerability = Field(
        default_factory=CompositeVulnerability,
        description="Composite vulnerability score and rating.",
    )
    nri_expanded: NRIExpandedProfile = Field(
        default_factory=NRIExpandedProfile,
        description="Expanded FEMA NRI metrics (EAL components, national percentile).",
    )
    svi: SVIProfile = Field(
        default_factory=SVIProfile,
        description="CDC/ATSDR SVI profile (3 themes, Theme 3 excluded).",
    )
    climate_projections: ClimateProjectionProfile = Field(
        default_factory=ClimateProjectionProfile,
        description="LOCA2 climate projections (UNAVAILABLE in v1.4).",
    )

    # Extended data sources (Phases 20-21)
    flood: Optional["FloodProfile"] = Field(
        default=None,
        description="Flood data composite (Phase 20). None until Phase 20 populates.",
    )
    climate_weather: Optional["ClimateWeatherProfile"] = Field(
        default=None,
        description="Climate & weather data composite (Phase 21). None until Phase 21.",
    )
    geologic: Optional["GeologicProfile"] = Field(
        default=None,
        description="Geologic data composite (Phase 21). None until Phase 21.",
    )
    infrastructure: Optional["InfrastructureProfile"] = Field(
        default=None,
        description="Infrastructure exposure (Phase 21). None until Phase 21.",
    )

    # Metadata
    data_sources: list[DataSourceMeta] = Field(
        default_factory=list,
        description="Provenance metadata for each integrated data source.",
    )
    generated_at: str = Field(
        ...,
        description="ISO 8601 timestamp of profile generation.",
        examples=["2026-02-17T14:30:00+00:00"],
    )
    schema_version: str = Field(
        default="1.4.0",
        description="Schema version for forward compatibility.",
    )

    # Coverage summary
    component_coverage: dict[str, CoverageStatus] = Field(
        default_factory=dict,
        description="Per-component coverage status summary. "
                    "Keys: nri, svi, climate_projections, flood, climate_weather, "
                    "geologic, infrastructure.",
    )

    @field_validator("tribe_id")
    @classmethod
    def validate_tribe_id_format(cls, v: str) -> str:
        if not v.startswith("epa_"):
            raise ValueError(f"tribe_id must start with 'epa_', got '{v}'")
        numeric_part = v[4:]
        if not numeric_part.isdigit():
            raise ValueError(
                f"tribe_id numeric portion must be all digits, got '{numeric_part}'"
            )
        return v

    @model_validator(mode="after")
    def populate_coverage_summary(self) -> "VulnerabilityProfile":
        """Auto-populate component_coverage from sub-profile statuses."""
        self.component_coverage = {
            "nri": self.nri_expanded.coverage_status,
            "svi": self.svi.coverage_status,
            "climate_projections": self.climate_projections.status,
            "flood": (
                self.flood.coverage_status
                if self.flood is not None
                else CoverageStatus.UNAVAILABLE
            ),
            "climate_weather": (
                self.climate_weather.coverage_status
                if self.climate_weather is not None
                else CoverageStatus.UNAVAILABLE
            ),
            "geologic": (
                self.geologic.coverage_status
                if self.geologic is not None
                else CoverageStatus.UNAVAILABLE
            ),
            "infrastructure": (
                self.infrastructure.coverage_status
                if self.infrastructure is not None
                else CoverageStatus.UNAVAILABLE
            ),
        }
        return self

    @property
    def has_vulnerability_data(self) -> bool:
        """Whether any vulnerability component has data."""
        return (
            self.nri_expanded.counties_analyzed > 0
            or self.svi.counties_analyzed > 0
            or self.flood is not None
            or self.climate_weather is not None
        )

    model_config = ConfigDict(
        # Allow forward references to flood/climate/geologic/infrastructure
        # models defined in separate schema modules
        arbitrary_types_allowed=False,
    )
```

#### Flood Models (Phase 20)

```python
# src/schemas/flood.py

"""Pydantic v2 validation models for flood and water data sources.

Covers FLOOD-01 through FLOOD-06:
- NFIPProfile: NFIP claims history and policy counts
- DisasterDeclarationProfile: Historical disaster declarations
- FloodZoneProfile: NFHL flood zone designations
- StreamflowProfile: USGS Water Services gauge data
- PrecipitationProfile: NOAA Atlas 14 precipitation frequency
- CoastalWaterProfile: NOAA CO-OPS tidal/water level data
- FloodProfile: Composite container for all flood sources
"""

from __future__ import annotations

import math
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from src.schemas.vulnerability import CoverageStatus, _validate_nonneg_float


class NFIPClaimSummary(BaseModel):
    """Summary of NFIP flood insurance claims for a county/Tribal area.

    Source: OpenFEMA FIMA NFIP Redacted Claims v2.
    """

    total_claims: int = Field(
        default=0, ge=0,
        description="Total number of NFIP claims filed.",
    )
    total_building_damage: float = Field(
        default=0.0, ge=0.0,
        description="Total building damage amount (USD) across all claims.",
    )
    total_contents_damage: float = Field(
        default=0.0, ge=0.0,
        description="Total contents damage amount (USD).",
    )
    total_payments: float = Field(
        default=0.0, ge=0.0,
        description="Total claim payments (USD).",
    )
    policies_in_force: int = Field(
        default=0, ge=0,
        description="Number of active NFIP policies.",
    )
    loss_ratio: Optional[float] = Field(
        default=None, ge=0.0,
        description="Ratio of claims paid to premiums collected. "
                    "None if no policy data available.",
    )
    repetitive_loss_properties: int = Field(
        default=0, ge=0,
        description="Number of properties with 2+ claims.",
    )
    date_range_start: str = Field(
        default="",
        description="Earliest claim date in dataset (YYYY-MM-DD).",
    )
    date_range_end: str = Field(
        default="",
        description="Latest claim date in dataset (YYYY-MM-DD).",
    )

    @field_validator("total_building_damage", "total_contents_damage",
                     "total_payments", mode="before")
    @classmethod
    def sanitize_dollars(cls, v: float | None) -> float:
        return _validate_nonneg_float(v)


class NFIPProfile(BaseModel):
    """NFIP flood insurance profile for a Tribal area (FLOOD-01)."""

    summary: NFIPClaimSummary = Field(
        default_factory=NFIPClaimSummary,
        description="Aggregated NFIP claims summary.",
    )
    yearly_claims: dict[str, int] = Field(
        default_factory=dict,
        description="Claims count by year (string keys, e.g., '2020': 15).",
    )
    top_causes: list[dict] = Field(
        default_factory=list,
        description="Top causes of damage ranked by total amount. "
                    "Each dict: {cause: str, count: int, total_damage: float}.",
    )
    counties_analyzed: int = Field(default=0, ge=0)
    coverage_status: CoverageStatus = Field(default=CoverageStatus.UNAVAILABLE)
    source_version: str = Field(default="FIMA NFIP Redacted Claims v2")


class DisasterEvent(BaseModel):
    """Individual FEMA disaster declaration."""

    disaster_number: int = Field(..., description="FEMA disaster number.")
    declaration_type: str = Field(
        default="",
        description="Declaration type: DR (major disaster), EM (emergency), FM (fire).",
    )
    disaster_type: str = Field(
        default="",
        description="Type of disaster (e.g., 'Flood', 'Hurricane', 'Severe Storm').",
    )
    declaration_date: str = Field(default="", description="Declaration date (YYYY-MM-DD).")
    title: str = Field(default="", description="Disaster title.")
    state: str = Field(default="", description="State abbreviation.")


class DisasterDeclarationProfile(BaseModel):
    """FEMA disaster declaration history for a Tribal area (FLOOD-02)."""

    total_declarations: int = Field(default=0, ge=0)
    flood_declarations: int = Field(
        default=0, ge=0,
        description="Number of flood-specific declarations.",
    )
    weather_declarations: int = Field(
        default=0, ge=0,
        description="Number of weather-related declarations (including flood).",
    )
    recent_events: list[DisasterEvent] = Field(
        default_factory=list,
        description="Most recent disaster events (up to 10).",
    )
    declarations_per_decade: dict[str, int] = Field(
        default_factory=dict,
        description="Declaration counts by decade (e.g., '2010s': 5).",
    )
    earliest_declaration: str = Field(default="", description="Earliest year (YYYY).")
    coverage_status: CoverageStatus = Field(default=CoverageStatus.UNAVAILABLE)
    source_version: str = Field(default="Disaster Declarations Summaries v2")


class FloodZoneProfile(BaseModel):
    """FEMA NFHL flood zone designations for a Tribal area (FLOOD-03).

    NOTE: Full geospatial intersection with Tribal boundaries is complex.
    Sovereignty Scout recommends county-level summary statistics for v1.4
    rather than parcel-level overlay.
    """

    high_risk_zone_pct: float = Field(
        default=0.0, ge=0.0, le=100.0,
        description="Percentage of Tribal area in high-risk flood zones (A/V zones).",
    )
    moderate_risk_zone_pct: float = Field(
        default=0.0, ge=0.0, le=100.0,
        description="Percentage of Tribal area in moderate-risk zones (B/X-shaded).",
    )
    minimal_risk_zone_pct: float = Field(
        default=0.0, ge=0.0, le=100.0,
        description="Percentage in minimal-risk zones (C/X-unshaded).",
    )
    zones_present: list[str] = Field(
        default_factory=list,
        description="Distinct FEMA flood zone codes present in Tribal area.",
        examples=[["A", "AE", "X", "VE"]],
    )
    sfha_flag: bool = Field(
        default=False,
        description="Whether any Special Flood Hazard Area (SFHA) overlaps Tribal land.",
    )
    coverage_status: CoverageStatus = Field(default=CoverageStatus.UNAVAILABLE)
    source_version: str = Field(default="FEMA NFHL")
    note: str = Field(
        default="",
        description="County-level summary; not parcel-level geospatial intersection.",
    )


class StreamflowProfile(BaseModel):
    """USGS Water Services streamflow data for gauges near Tribal land (FLOOD-04).

    Built against NEW API at api.waterdata.usgs.gov (OGC API - Features),
    NOT the legacy waterservices.usgs.gov endpoint (decommissioning early 2027).
    """

    gauge_count: int = Field(
        default=0, ge=0,
        description="Number of USGS stream gauges within/near Tribal area.",
    )
    gauges: list[dict] = Field(
        default_factory=list,
        description="Gauge metadata: {site_no, station_name, latitude, longitude, "
                    "drainage_area_sqmi}.",
    )
    peak_flow_cfs: Optional[float] = Field(
        default=None, ge=0.0,
        description="Maximum recorded peak flow (cubic feet per second) across gauges.",
    )
    median_annual_flow_cfs: Optional[float] = Field(
        default=None, ge=0.0,
        description="Median annual flow (cfs) for the primary gauge.",
    )
    flood_stage_exceedances: int = Field(
        default=0, ge=0,
        description="Number of times flood stage was exceeded across all gauges.",
    )
    coverage_status: CoverageStatus = Field(default=CoverageStatus.UNAVAILABLE)
    source_version: str = Field(default="USGS Water Data API (OGC)")
    api_note: str = Field(
        default="Built against api.waterdata.usgs.gov (new OGC API). "
                "Legacy waterservices.usgs.gov decommissioning early 2027.",
    )


class PrecipitationProfile(BaseModel):
    """NOAA Atlas 14 precipitation frequency estimates (FLOOD-05).

    NOTE: Atlas 15 (climate-adjusted) in peer review 2026. Build against
    Atlas 14 now, plan migration path when Atlas 15 publishes.
    """

    pf_100yr_24hr: Optional[float] = Field(
        default=None, ge=0.0,
        description="100-year, 24-hour precipitation frequency estimate (inches).",
    )
    pf_100yr_1hr: Optional[float] = Field(
        default=None, ge=0.0,
        description="100-year, 1-hour precipitation frequency estimate (inches).",
    )
    pf_10yr_24hr: Optional[float] = Field(
        default=None, ge=0.0,
        description="10-year, 24-hour precipitation frequency estimate (inches).",
    )
    pf_500yr_24hr: Optional[float] = Field(
        default=None, ge=0.0,
        description="500-year, 24-hour precipitation frequency estimate (inches).",
    )
    station_count: int = Field(
        default=0, ge=0,
        description="Number of HDSC stations used.",
    )
    coverage_status: CoverageStatus = Field(default=CoverageStatus.UNAVAILABLE)
    source_version: str = Field(default="NOAA Atlas 14")
    supersession_note: str = Field(
        default="NOAA Atlas 15 (climate-adjusted) in peer review 2026. "
                "Migration planned when published.",
    )


class CoastalWaterProfile(BaseModel):
    """NOAA CO-OPS coastal water level data for coastal Tribal areas (FLOOD-06).

    Only applicable for coastal Tribal Nations. Interior Tribes will have
    coverage_status=NOT_APPLICABLE.
    """

    station_count: int = Field(
        default=0, ge=0,
        description="Number of CO-OPS tide stations near Tribal area.",
    )
    stations: list[dict] = Field(
        default_factory=list,
        description="Station metadata: {station_id, name, latitude, longitude}.",
    )
    mean_higher_high_water_ft: Optional[float] = Field(
        default=None,
        description="Mean Higher High Water (MHHW) in feet (datum: NAVD88).",
    )
    flood_threshold_ft: Optional[float] = Field(
        default=None,
        description="Minor flood threshold in feet.",
    )
    sea_level_trend_mm_yr: Optional[float] = Field(
        default=None,
        description="Local relative sea level trend (mm/year).",
    )
    days_above_flood_threshold: Optional[int] = Field(
        default=None, ge=0,
        description="Days per year water exceeded flood threshold (most recent year).",
    )
    coverage_status: CoverageStatus = Field(default=CoverageStatus.UNAVAILABLE)
    source_version: str = Field(default="NOAA CO-OPS Tides & Currents")


class FloodProfile(BaseModel):
    """Composite flood data profile combining all flood sources (FLOOD-01 to FLOOD-06).

    Container for all flood-related data. Each sub-source has independent
    coverage_status to handle the reality that coastal data only applies
    to coastal Tribes, and streamflow gauges have sparse Alaska coverage.
    """

    nfip: NFIPProfile = Field(
        default_factory=NFIPProfile,
        description="NFIP flood insurance claims and policies.",
    )
    disaster_declarations: DisasterDeclarationProfile = Field(
        default_factory=DisasterDeclarationProfile,
        description="FEMA disaster declaration history.",
    )
    flood_zones: FloodZoneProfile = Field(
        default_factory=FloodZoneProfile,
        description="FEMA NFHL flood zone designations.",
    )
    streamflow: StreamflowProfile = Field(
        default_factory=StreamflowProfile,
        description="USGS streamflow gauge data.",
    )
    precipitation: PrecipitationProfile = Field(
        default_factory=PrecipitationProfile,
        description="NOAA Atlas 14 precipitation frequency estimates.",
    )
    coastal_water: CoastalWaterProfile = Field(
        default_factory=CoastalWaterProfile,
        description="NOAA CO-OPS coastal water level data.",
    )
    coverage_status: CoverageStatus = Field(
        default=CoverageStatus.UNAVAILABLE,
        description="Overall flood data coverage (FULL if any 3+ sources present).",
    )

    @model_validator(mode="after")
    def compute_overall_coverage(self) -> "FloodProfile":
        """Compute overall coverage from sub-source statuses."""
        statuses = [
            self.nfip.coverage_status,
            self.disaster_declarations.coverage_status,
            self.flood_zones.coverage_status,
            self.streamflow.coverage_status,
            self.precipitation.coverage_status,
            self.coastal_water.coverage_status,
        ]
        available = sum(
            1 for s in statuses
            if s in (CoverageStatus.FULL, CoverageStatus.PARTIAL)
        )
        if available >= 3:
            self.coverage_status = CoverageStatus.FULL
        elif available >= 1:
            self.coverage_status = CoverageStatus.PARTIAL
        else:
            self.coverage_status = CoverageStatus.UNAVAILABLE
        return self
```

#### Climate & Weather Models (Phase 21)

```python
# src/schemas/climate.py

"""Pydantic v2 validation models for climate and weather data sources.

Covers CLIM-01 through CLIM-03:
- DroughtProfile: US Drought Monitor severity data
- HistoricalClimateProfile: NOAA NCEI climate records
- NWSAlertProfile: National Weather Service active alerts
- ClimateWeatherProfile: Composite container
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from src.schemas.vulnerability import CoverageStatus, _validate_nonneg_float


# Drought Monitor severity categories
DROUGHT_CATEGORIES = frozenset({"D0", "D1", "D2", "D3", "D4", "None"})


class DroughtSeverity(BaseModel):
    """Weekly drought severity breakdown for a county/Tribal area.

    Categories: D0 (Abnormally Dry) through D4 (Exceptional Drought).
    Percentages represent fraction of area in each category.
    """

    category: str = Field(
        ...,
        description="Drought Monitor category (D0-D4 or 'None').",
    )
    area_pct: float = Field(
        default=0.0, ge=0.0, le=100.0,
        description="Percentage of area in this drought category.",
    )
    population_pct: float = Field(
        default=0.0, ge=0.0, le=100.0,
        description="Percentage of population in this drought category.",
    )


class DroughtProfile(BaseModel):
    """US Drought Monitor drought severity profile (CLIM-01).

    Source: drought.gov / droughtmonitor.unl.edu
    Weekly county-level data joined via existing FIPS crosswalk.
    """

    current_severity: list[DroughtSeverity] = Field(
        default_factory=list,
        description="Current week drought severity breakdown.",
    )
    max_severity_52wk: str = Field(
        default="None",
        description="Maximum drought category in past 52 weeks.",
    )
    weeks_in_drought_52wk: int = Field(
        default=0, ge=0, le=52,
        description="Number of weeks with any drought (D0+) in past 52 weeks.",
    )
    weeks_in_severe_drought_52wk: int = Field(
        default=0, ge=0, le=52,
        description="Number of weeks with severe drought (D2+) in past 52 weeks.",
    )
    trend: str = Field(
        default="",
        description="Drought trend: 'improving', 'worsening', 'stable', or 'none'.",
    )
    snapshot_date: str = Field(
        default="",
        description="Date of the drought data snapshot (YYYY-MM-DD).",
    )
    coverage_status: CoverageStatus = Field(default=CoverageStatus.UNAVAILABLE)
    source_version: str = Field(default="US Drought Monitor")


class ClimateNormal(BaseModel):
    """1991-2020 Climate Normal for a variable at a station or county."""

    variable: str = Field(
        ...,
        description="Climate variable identifier.",
        examples=["TAVG", "TMAX", "TMIN", "PRCP"],
    )
    annual_value: Optional[float] = Field(
        default=None,
        description="Annual normal value (deg F for temp, inches for precip).",
    )
    monthly_values: dict[str, Optional[float]] = Field(
        default_factory=dict,
        description="Monthly normal values keyed by month number ('01'-'12').",
    )
    unit: str = Field(
        default="",
        description="Measurement unit (e.g., 'deg_F', 'inches').",
    )


class HistoricalClimateProfile(BaseModel):
    """NOAA NCEI historical climate records (CLIM-02).

    Source: NOAA NCEI Climate Data Online (new endpoint: ncei.noaa.gov/access/services/data/v1).
    NOTE: Requires API token (free, obtained via email).

    Built against the new API endpoint, NOT the deprecated CDO API v2.
    """

    normals: list[ClimateNormal] = Field(
        default_factory=list,
        description="1991-2020 Climate Normals for key variables.",
    )
    avg_annual_temp_f: Optional[float] = Field(
        default=None,
        description="Average annual temperature (degrees F).",
    )
    avg_annual_precip_in: Optional[float] = Field(
        default=None,
        description="Average annual precipitation (inches).",
    )
    record_high_temp_f: Optional[float] = Field(
        default=None,
        description="All-time record high temperature (degrees F).",
    )
    record_low_temp_f: Optional[float] = Field(
        default=None,
        description="All-time record low temperature (degrees F).",
    )
    extreme_precip_event: Optional[str] = Field(
        default=None,
        description="Most extreme precipitation event on record (description).",
    )
    station_count: int = Field(default=0, ge=0)
    coverage_status: CoverageStatus = Field(default=CoverageStatus.UNAVAILABLE)
    source_version: str = Field(default="NOAA NCEI Climate Data Online (v1 API)")
    api_note: str = Field(
        default="Built against ncei.noaa.gov/access/services/data/v1. "
                "Legacy CDO API v2 is deprecated.",
    )


class NWSAlert(BaseModel):
    """Individual National Weather Service alert."""

    alert_id: str = Field(default="", description="NWS alert identifier.")
    event: str = Field(
        default="",
        description="Alert event type (e.g., 'Flood Watch', 'Winter Storm Warning').",
    )
    severity: str = Field(
        default="",
        description="Alert severity: Extreme, Severe, Moderate, Minor, Unknown.",
    )
    urgency: str = Field(
        default="",
        description="Alert urgency: Immediate, Expected, Future, Past, Unknown.",
    )
    headline: str = Field(default="", description="Alert headline.")
    onset: str = Field(default="", description="Alert onset datetime (ISO 8601).")
    expires: str = Field(default="", description="Alert expiration datetime (ISO 8601).")
    area_desc: str = Field(default="", description="Affected area description.")


class NWSAlertProfile(BaseModel):
    """NWS active alerts and hazard warnings for Tribal areas (CLIM-03).

    Source: api.weather.gov /alerts endpoint.
    County-based filtering via UGC codes (state + "C" + FIPS county number).
    """

    active_alerts: list[NWSAlert] = Field(
        default_factory=list,
        description="Currently active NWS alerts for Tribal area counties.",
    )
    active_alert_count: int = Field(
        default=0, ge=0,
        description="Number of currently active alerts.",
    )
    alert_types_7d: list[str] = Field(
        default_factory=list,
        description="Distinct alert event types in past 7 days.",
    )
    alert_count_7d: int = Field(
        default=0, ge=0,
        description="Total alerts in past 7 days.",
    )
    snapshot_date: str = Field(
        default="",
        description="Date of alert data capture (ISO 8601).",
    )
    coverage_status: CoverageStatus = Field(default=CoverageStatus.UNAVAILABLE)
    source_version: str = Field(default="NWS API (api.weather.gov)")
    note: str = Field(
        default="NWS /alerts provides only past 7 days. "
                "/forecast and /forecast/hourly no longer contain past data (Jan 2026 update).",
    )


class ClimateWeatherProfile(BaseModel):
    """Composite climate and weather profile (CLIM-01 through CLIM-03).

    Container for drought, historical climate, and NWS alert data.
    """

    drought: DroughtProfile = Field(
        default_factory=DroughtProfile,
        description="US Drought Monitor data.",
    )
    historical_climate: HistoricalClimateProfile = Field(
        default_factory=HistoricalClimateProfile,
        description="NOAA NCEI historical climate records.",
    )
    nws_alerts: NWSAlertProfile = Field(
        default_factory=NWSAlertProfile,
        description="NWS active alerts and hazard warnings.",
    )
    coverage_status: CoverageStatus = Field(default=CoverageStatus.UNAVAILABLE)

    @model_validator(mode="after")
    def compute_overall_coverage(self) -> "ClimateWeatherProfile":
        statuses = [
            self.drought.coverage_status,
            self.historical_climate.coverage_status,
            self.nws_alerts.coverage_status,
        ]
        available = sum(
            1 for s in statuses
            if s in (CoverageStatus.FULL, CoverageStatus.PARTIAL)
        )
        if available >= 2:
            self.coverage_status = CoverageStatus.FULL
        elif available >= 1:
            self.coverage_status = CoverageStatus.PARTIAL
        else:
            self.coverage_status = CoverageStatus.UNAVAILABLE
        return self
```

#### Geologic & Infrastructure Models (Phase 21)

```python
# src/schemas/infrastructure.py

"""Pydantic v2 validation models for geologic and infrastructure data.

Covers GEO-01, GEO-02, INFRA-01:
- LandslideProfile: WA DNR / OR DOGAMI landslide inventory data
- TerrainProfile: USGS 3DEP elevation/terrain screening
- InfrastructureExposureProfile: DHS HIFLD critical infrastructure
- GeologicProfile: Composite geologic container
- InfrastructureProfile: Infrastructure exposure container
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, model_validator

from src.schemas.vulnerability import CoverageStatus


# States with landslide inventory data in v1.4
LANDSLIDE_INVENTORY_STATES = frozenset({"WA", "OR"})


class LandslideProfile(BaseModel):
    """State geological agency landslide inventory data (GEO-01).

    SCOPE: WA and OR only in v1.4. Tribes in all other states will have
    coverage_status=NOT_APPLICABLE. This is a regional enhancement, not
    a core feature.

    Source: WA DNR Landslide Inventory Database v1.4, OR DOGAMI SLIDO v4.5.
    Both are ESRI geodatabase format requiring geopandas/fiona.
    """

    landslide_count: int = Field(
        default=0, ge=0,
        description="Number of recorded landslide features within/near Tribal area.",
    )
    deposit_area_sqkm: float = Field(
        default=0.0, ge=0.0,
        description="Total landslide deposit area (sq km).",
    )
    susceptibility_rating: str = Field(
        default="",
        description="Overall landslide susceptibility: 'High', 'Moderate', 'Low', or ''.",
    )
    source_state: str = Field(
        default="",
        description="State source (WA or OR). Empty if not applicable.",
    )
    source_version: str = Field(
        default="",
        description="Data version (e.g., 'WA DNR v1.4', 'OR DOGAMI SLIDO v4.5').",
    )
    coverage_status: CoverageStatus = Field(
        default=CoverageStatus.NOT_APPLICABLE,
        description="NOT_APPLICABLE for non-WA/OR Tribes.",
    )


class TerrainProfile(BaseModel):
    """USGS 3DEP elevation/terrain screening data (GEO-02).

    NOTE: 3DEP is raw elevation raster data. Per Sovereignty Scout,
    full terrain analysis is DEFERRED to v1.5+. v1.4 captures only
    basic screening metrics if available from pre-processed data.
    """

    mean_elevation_ft: Optional[float] = Field(
        default=None,
        description="Mean elevation of Tribal area (feet above sea level).",
    )
    max_slope_pct: Optional[float] = Field(
        default=None, ge=0.0,
        description="Maximum slope gradient (percent) in Tribal area.",
    )
    low_lying_area_pct: Optional[float] = Field(
        default=None, ge=0.0, le=100.0,
        description="Percentage of Tribal area below 10ft elevation (flood-prone screening).",
    )
    coverage_status: CoverageStatus = Field(
        default=CoverageStatus.UNAVAILABLE,
        description="UNAVAILABLE until pre-processed terrain metrics exist.",
    )
    source_version: str = Field(default="USGS 3DEP")
    deferral_note: str = Field(
        default="Full terrain analysis deferred to v1.5+. "
                "v1.4 includes screening metrics only if available.",
    )


class GeologicProfile(BaseModel):
    """Composite geologic data profile (GEO-01 + GEO-02)."""

    landslide: LandslideProfile = Field(
        default_factory=LandslideProfile,
        description="Landslide inventory data (WA/OR only).",
    )
    terrain: TerrainProfile = Field(
        default_factory=TerrainProfile,
        description="Terrain screening data.",
    )
    coverage_status: CoverageStatus = Field(default=CoverageStatus.UNAVAILABLE)

    @model_validator(mode="after")
    def compute_coverage(self) -> "GeologicProfile":
        has_landslide = self.landslide.coverage_status in (
            CoverageStatus.FULL, CoverageStatus.PARTIAL
        )
        has_terrain = self.terrain.coverage_status in (
            CoverageStatus.FULL, CoverageStatus.PARTIAL
        )
        if has_landslide or has_terrain:
            self.coverage_status = CoverageStatus.PARTIAL
        else:
            # Check if NOT_APPLICABLE (non-WA/OR state)
            if self.landslide.coverage_status == CoverageStatus.NOT_APPLICABLE:
                self.coverage_status = CoverageStatus.NOT_APPLICABLE
            else:
                self.coverage_status = CoverageStatus.UNAVAILABLE
        return self


class FacilityTypeCount(BaseModel):
    """Count of critical infrastructure facilities by sector."""

    sector: str = Field(
        ...,
        description="HIFLD infrastructure sector.",
        examples=[
            "Education", "Emergency Services", "Energy",
            "Communications", "Transportation", "Water",
            "Agriculture", "Healthcare",
        ],
    )
    facility_count: int = Field(default=0, ge=0)
    within_hazard_zone: int = Field(
        default=0, ge=0,
        description="Facilities within a recognized hazard zone (flood, wildfire, etc.).",
    )


class InfrastructureExposureProfile(BaseModel):
    """DHS HIFLD critical infrastructure exposure (INFRA-01).

    Source: HIFLD Open Data (hifld-geoplatform.opendata.arcgis.com).
    Uses open datasets only (T0 classification boundary).
    Secure/licensed datasets require DUA and are excluded from v1.4.
    """

    total_facilities: int = Field(
        default=0, ge=0,
        description="Total critical infrastructure facilities in Tribal area.",
    )
    facilities_by_sector: list[FacilityTypeCount] = Field(
        default_factory=list,
        description="Facility counts broken down by infrastructure sector.",
    )
    facilities_in_flood_zone: int = Field(
        default=0, ge=0,
        description="Facilities in FEMA Special Flood Hazard Areas.",
    )
    facilities_in_wildfire_zone: int = Field(
        default=0, ge=0,
        description="Facilities in high/very-high wildfire risk zones.",
    )
    coverage_status: CoverageStatus = Field(default=CoverageStatus.UNAVAILABLE)
    source_version: str = Field(default="DHS HIFLD Open Data")
    note: str = Field(
        default="Open datasets only (T0 boundary). Secure datasets excluded.",
    )


class InfrastructureProfile(BaseModel):
    """Infrastructure exposure composite (INFRA-01).

    Wrapper providing a consistent interface for the VulnerabilityProfile
    container. Currently contains only HIFLD exposure; future versions
    may add additional infrastructure data sources.
    """

    hifld: InfrastructureExposureProfile = Field(
        default_factory=InfrastructureExposureProfile,
        description="DHS HIFLD critical infrastructure exposure.",
    )
    coverage_status: CoverageStatus = Field(default=CoverageStatus.UNAVAILABLE)

    @model_validator(mode="after")
    def compute_coverage(self) -> "InfrastructureProfile":
        self.coverage_status = self.hifld.coverage_status
        return self
```

---

### Composite Score Design

#### v1.4 Formula (3-component, no LOCA2)

**Decision: Option B with Option C as a quality signal.**

With LOCA2 deferred to v1.5+, the v1.4 composite uses 3 components. Rather than redistributing the missing climate weight (which would inflate the remaining components), the formula uses purpose-built 3-component weights:

```
v1.4_score = 0.40 * hazard_exposure
           + 0.35 * social_vulnerability
           + 0.25 * adaptive_capacity_deficit
```

**Justification for weights:**
- **Hazard exposure (0.40)**: The single most directly measurable component. NRI risk scores are well-validated and area-weighted. This is the strongest signal.
- **Social vulnerability (0.35)**: SVI provides the second-strongest signal. With Theme 3 excluded, the 3-theme composite is a clean measure of non-racial/ethnic social vulnerability factors relevant to Tribal Nations.
- **Adaptive capacity deficit (0.25)**: Inverted community resilience score (1 - RESL_SCORE/100). Lower weight because NRI's RESL_SCORE has broader confidence intervals than RISK_SCORE.

**Component derivation:**

| Component | Source | Normalization |
|-----------|--------|--------------|
| hazard_exposure | NRI `risk_national_percentile` | percentile / 100 (already 0-100 scale) |
| social_vulnerability | CDC SVI `tribal_svi_composite` | Already 0-1 scale |
| adaptive_capacity_deficit | NRI `community_resilience_score` | `1.0 - (resl_score / 100)` (inverted: higher = more deficit) |

**`data_completeness_factor`:**
This is stored as a quality signal but does NOT discount the score in v1.4. It is computed as the fraction of total weight covered by components with actual data. When all 3 components have data, `data_completeness_factor = 1.0`. When SVI is missing, `data_completeness_factor = 0.65` (only hazard + adaptive capacity available with weights 0.40 + 0.25 = 0.65). This factor is displayed in documents and used by renderers to add confidence caveats.

**When components are missing, redistribution works as follows:**

```python
def compute_composite(
    hazard_score: float | None,      # 0-1
    svi_score: float | None,         # 0-1
    adaptive_deficit: float | None,  # 0-1
) -> tuple[float, float, str]:
    """Compute composite vulnerability score with weight redistribution.

    Returns: (score, data_completeness_factor, confidence_note)
    """
    components = []
    base_weights = {
        "hazard_exposure": 0.40,
        "social_vulnerability": 0.35,
        "adaptive_capacity_deficit": 0.25,
    }

    if hazard_score is not None:
        components.append(("hazard_exposure", hazard_score))
    if svi_score is not None:
        components.append(("social_vulnerability", svi_score))
    if adaptive_deficit is not None:
        components.append(("adaptive_capacity_deficit", adaptive_deficit))

    if not components:
        return 0.0, 0.0, "No vulnerability data available."

    # Redistribute weights proportionally across available components
    available_weight = sum(base_weights[c[0]] for c in components)
    data_completeness = available_weight  # Fraction of original weight covered

    score = 0.0
    for name, raw in components:
        normalized_weight = base_weights[name] / available_weight
        score += raw * normalized_weight

    # Confidence note
    missing = set(base_weights.keys()) - {c[0] for c in components}
    if not missing:
        note = "Full data: all vulnerability components available."
    elif len(missing) == 1:
        note = f"Partial data: {missing.pop()} unavailable. Score based on remaining components."
    else:
        note = f"Limited data: {', '.join(sorted(missing))} unavailable."

    return round(score, 4), round(data_completeness, 2), note
```

#### Edge Case Matrix

| Edge Case | Handling | Score | completeness | Confidence Note |
|-----------|----------|-------|-------------|-----------------|
| All 3 components present | Standard formula | 0.40h + 0.35s + 0.25a | 1.0 | "Full data..." |
| Missing SVI (county not in SVI CSV) | Redistribute to hazard + adaptive | 0.615h + 0.385a | 0.65 | "Partial data: SVI unavailable..." |
| NRI -999 sentinel values | `_safe_float()` returns 0.0; `counties_analyzed=0`; component marked unavailable | 0.0 (if all NRI) | varies | "NRI data contains sentinel values..." |
| Alaska Tribe with partial county coverage | Area-weighted from available counties; `counties_analyzed` reflects actual count; coverage_status=PARTIAL | Weighted from available | varies | "Based on {n} of {m} counties..." |
| Tribe spanning multiple counties with conflicting ratings | Area-weighted averaging; rating RE-DERIVED from weighted score (not averaged from ratings) | Area-weighted | 1.0 | "Full data..." |
| Zero area weight for all counties | No score produced; `coverage_status=UNAVAILABLE`; composite score = 0.0 | 0.0 | 0.0 | "No geographic overlap data..." |
| Only hazard data, no SVI, no RESL | Redistribute to hazard only | 1.0 * h | 0.40 | "Limited data: only hazard exposure..." |
| SVI county has RPL_THEME value of -999 | `_safe_float()` catches; theme percentile defaults to 0.0; that theme excluded from average | Adjusted | varies | "SVI theme data partially missing..." |

#### v1.5 Formula (4-component, with LOCA2)

When LOCA2 ships in v1.5+, the formula reverts to the 4-component design:

```
v1.5_score = 0.30 * hazard_exposure
           + 0.25 * social_vulnerability
           + 0.25 * climate_projection
           + 0.20 * adaptive_capacity_deficit
```

**Backward compatibility:** The `formula_version` field ("v1.4-3c" vs "v1.5-4c") in `CompositeVulnerability` ensures consumers can distinguish formula generations. The `ComponentScore.weight` values will change, so any code that checks specific weight values must use the `formula_version` field. The 5-tier rating scale and 0-1 score range remain identical.

**Alaska handling in v1.5+:** Alaska Tribes will use SNAP data (not LOCA2) for the climate_projection component. The `ClimateProjectionProfile.source` field distinguishes "LOCA2" (CONUS) from "SNAP" (Alaska).

---

### Coverage Report Specification

The `vulnerability_coverage_report.json` follows the pattern of the existing `hazard_coverage_report.json` (written by `HazardProfileBuilder._generate_coverage_report()`).

```json
{
  "generated_at": "2026-02-17T14:30:00+00:00",
  "schema_version": "1.4.0",
  "summary": {
    "total_tribes": 592,
    "profiles_generated": 592,
    "full_coverage": 450,
    "partial_coverage": 100,
    "no_coverage": 42,
    "full_coverage_pct": 76.0,
    "partial_coverage_pct": 16.9,
    "no_coverage_pct": 7.1
  },
  "per_source_coverage": {
    "nri_expanded": {
      "tribes_with_data": 573,
      "coverage_pct": 96.8,
      "note": "Matches existing hazard profile NRI coverage"
    },
    "svi": {
      "tribes_with_data": 565,
      "coverage_pct": 95.4,
      "note": "SVI 2022 county coverage minus counties without SVI data"
    },
    "flood_nfip": {
      "tribes_with_data": 540,
      "coverage_pct": 91.2,
      "note": "County-level NFIP claims available for most counties"
    },
    "flood_disaster_declarations": {
      "tribes_with_data": 550,
      "coverage_pct": 92.9
    },
    "flood_zones": {
      "tribes_with_data": 480,
      "coverage_pct": 81.1,
      "note": "County-level summary; not parcel-level"
    },
    "streamflow": {
      "tribes_with_data": 350,
      "coverage_pct": 59.1,
      "note": "Sparse gauge network in Alaska and remote areas"
    },
    "precipitation": {
      "tribes_with_data": 400,
      "coverage_pct": 67.6,
      "note": "Station-based; coverage depends on HDSC station proximity"
    },
    "coastal_water": {
      "tribes_with_data": 80,
      "coverage_pct": 13.5,
      "note": "Only applicable for coastal Tribes"
    },
    "drought": {
      "tribes_with_data": 575,
      "coverage_pct": 97.1,
      "note": "Excellent county-level coverage including Alaska"
    },
    "historical_climate": {
      "tribes_with_data": 500,
      "coverage_pct": 84.5,
      "note": "Depends on NCEI station proximity"
    },
    "nws_alerts": {
      "tribes_with_data": 580,
      "coverage_pct": 98.0,
      "note": "County-based UGC codes; near-universal coverage"
    },
    "landslide": {
      "tribes_with_data": 30,
      "coverage_pct": 5.1,
      "note": "WA and OR Tribes only (v1.4 scope)"
    },
    "terrain": {
      "tribes_with_data": 0,
      "coverage_pct": 0.0,
      "note": "Deferred to v1.5+"
    },
    "infrastructure": {
      "tribes_with_data": 450,
      "coverage_pct": 76.0,
      "note": "Open HIFLD datasets only"
    },
    "climate_projections": {
      "tribes_with_data": 0,
      "coverage_pct": 0.0,
      "note": "LOCA2 deferred to v1.5+"
    }
  },
  "composite_score_reliability": {
    "high_reliability": {
      "count": 450,
      "pct": 76.0,
      "criteria": "All 3 composite components (hazard, SVI, adaptive capacity) available"
    },
    "medium_reliability": {
      "count": 100,
      "pct": 16.9,
      "criteria": "2 of 3 composite components available"
    },
    "low_reliability": {
      "count": 42,
      "pct": 7.1,
      "criteria": "1 or 0 composite components available"
    }
  },
  "per_tribe": [
    {
      "tribe_id": "epa_100000001",
      "tribe_name": "Example Tribe",
      "composite_coverage": "full",
      "composite_score": 0.62,
      "composite_rating": "Relatively High",
      "data_completeness_factor": 1.0,
      "components": {
        "nri": "full",
        "svi": "full",
        "climate_projections": "unavailable",
        "flood": "partial",
        "climate_weather": "full",
        "geologic": "not_applicable",
        "infrastructure": "full"
      },
      "missing_sources": ["climate_projections"],
      "notes": []
    }
  ],
  "unmatched_tribes": [
    {
      "tribe_id": "epa_100000999",
      "tribe_name": "Unmatched Tribe Example",
      "states": ["AK"],
      "reason": "No county crosswalk entries for this Tribal area"
    }
  ],
  "alaska_coverage_summary": {
    "total_alaska_tribes": 229,
    "with_nri_data": 210,
    "with_svi_data": 225,
    "with_composite_score": 200,
    "climate_projections": 0,
    "note": "LOCA2 is CONUS-only. 229 Alaska Tribes have zero climate projection data. Alaska climate projections via SNAP planned for v1.5+."
  }
}
```

**NOTE:** The `per_tribe` array will contain 592 entries. The example values above are illustrative. Actual coverage numbers will be determined during Phase 19-22 implementation.

---

### Test Architecture

#### Test Structure

```
tests/
    test_vulnerability_schemas.py          # Phase 19: Schema validation tests
        TestSVITheme                       # Theme ID validation, percentile bounds
        TestSVIProfile                     # Composite calculation, theme count, coverage
        TestEALBreakdown                   # Dollar amount validation, NaN/Inf guards
        TestNRIExpandedProfile             # Percentile bounds, population sanitization
        TestClimateProjectionProfile       # Placeholder validation, deferred status
        TestComponentScore                 # Weight * raw = weighted validation
        TestCompositeVulnerability         # Rating consistency, formula version
        TestVulnerabilityProfile           # Full model construction, coverage auto-population
        TestCoverageStatus                 # Enum values
        TestVulnerabilityRating            # Enum values, score_to_rating conversion

    test_vulnerability_builder.py          # Phase 19/22: Builder unit tests
        TestSVIParsing                     # SVI CSV parsing, _safe_float for RPL columns
        TestNRIExpansion                   # New NRI fields extraction
        TestNationalPercentileComputation  # Rank-based percentile from RISK_SCORE
        TestAreaWeightedSVI                # SVI area-weighted aggregation
        TestCompositeScoreComputation      # 3-component formula, weight redistribution
        TestMissingDataHandling            # Edge cases from edge case matrix
        TestAtomicProfileWrites            # Atomic write verification
        TestPathTraversalGuard             # Path sanitization
        TestEmptyProfileSchema             # Schema consistency with empty data
        TestCoverageReportGeneration       # Coverage report JSON/Markdown output

    test_flood_schemas.py                  # Phase 20: Flood schema validation
        TestNFIPProfile                    # Claims, policies, loss ratio
        TestDisasterDeclarationProfile     # Event types, date ranges
        TestFloodZoneProfile               # Zone percentages sum <= 100
        TestStreamflowProfile              # Gauge data, API version note
        TestPrecipitationProfile           # Frequency estimates, Atlas 15 note
        TestCoastalWaterProfile            # Sea level trend, NOT_APPLICABLE for inland
        TestFloodProfile                   # Composite coverage computation

    test_flood_builder.py                  # Phase 20: Flood data population tests
        TestNFIPDataFetch                  # OpenFEMA API response parsing
        TestDisasterFetch                  # Disaster declaration filtering
        TestFloodZoneSummary               # County-level zone statistics
        TestStreamflowFetch                # New OGC API response parsing
        TestPrecipitationFetch             # Atlas 14 data parsing
        TestCoastalWaterFetch              # CO-OPS API response parsing

    test_climate_schemas.py                # Phase 21: Climate schema validation
        TestDroughtProfile                 # Severity categories, 52-week window
        TestHistoricalClimateProfile       # Normals, API note
        TestNWSAlertProfile                # Alert structure, 7-day window
        TestClimateWeatherProfile          # Composite coverage

    test_climate_builder.py                # Phase 21: Climate data population tests
        TestDroughtFetch                   # Drought Monitor API parsing
        TestNCEIFetch                      # New NCEI API (token management)
        TestNWSFetch                       # NWS API UGC code construction

    test_geologic_infrastructure.py        # Phase 21: Geo & infra tests
        TestLandslideProfile               # WA/OR scoping, NOT_APPLICABLE elsewhere
        TestTerrainProfile                 # Deferred status
        TestInfrastructureExposure         # Facility counts by sector
        TestGeologicProfile                # Composite coverage

    test_vulnerability_rendering.py        # Phase 23: DOCX rendering tests
        TestVulnerabilityOverview          # Composite score display, rating badge
        TestSVIBreakdown                   # Theme decomposition rendering
        TestEALBreakdownTable              # Buildings/population/agriculture table
        TestAudienceFiltering              # Doc A (full detail) vs Doc B (composite only)
        TestEmptyDataHandling              # Graceful empty-state rendering
        TestDocEGeneration                 # Standalone vulnerability report

    test_vulnerability_web.py              # Phase 24: Website integration tests
        TestVulnerabilityBadges            # Badge rendering in Tribe cards
        TestOnDemandLoading                # Detail JSON loading
        TestChartVisualization             # Chart.js data preparation
```

#### Fixtures Needed

```python
# Shared fixtures (in individual test files, following codebase pattern)

@pytest.fixture
def sample_nri_county_row() -> dict:
    """Single NRI county CSV row with all expanded fields."""
    return {
        "STCOFIPS": "53033",
        "STATE": "Washington",
        "COUNTY": "King",
        "RISK_SCORE": "45.2",
        "RISK_RATNG": "Relatively Moderate",
        "RISK_SPCTL": "62.5",
        "EAL_VALT": "150000.50",
        "EAL_VALB": "85000.25",
        "EAL_VALP": "40000.10",
        "EAL_VALA": "25000.15",
        "EAL_VALPE": "40000.10",
        "SOVI_SCORE": "35.8",
        "SOVI_RATNG": "Relatively Low",
        "RESL_SCORE": "55.2",
        "RESL_RATNG": "Relatively Moderate",
        "POPULATION": "2252782",
        "BUILDVALUE": "500000000000",
        "AREA": "2126.04",
        # Per-hazard fields for WFIR as example
        "WFIR_RISKS": "78.5",
        "WFIR_RISKR": "Very High",
        "WFIR_EALT": "45000.00",
        "WFIR_EALB": "30000.00",
        "WFIR_EALP": "10000.00",
        "WFIR_EALA": "5000.00",
        "WFIR_EALPE": "10000.00",
        "WFIR_AFREQ": "2.5",
        "WFIR_EVNTS": "15",
    }


@pytest.fixture
def sample_svi_county_row() -> dict:
    """Single SVI 2022 county CSV row."""
    return {
        "FIPS": "53033",
        "RPL_THEMES": "0.6542",
        "RPL_THEME1": "0.4523",
        "RPL_THEME2": "0.7234",
        "RPL_THEME3": "0.8912",  # Excluded from Tribal composite
        "RPL_THEME4": "0.5678",
        "F_THEME1": "2",
        "F_THEME2": "3",
        "F_THEME3": "4",
        "F_THEME4": "1",
    }


@pytest.fixture
def sample_vulnerability_profile() -> dict:
    """Complete vulnerability profile JSON for rendering tests."""
    return {
        "tribe_id": "epa_100000342",
        "tribe_name": "Confederated Tribes of Warm Springs",
        "composite": {
            "score": 0.62,
            "rating": "Relatively High",
            "components": [
                {
                    "component": "hazard_exposure",
                    "raw_score": 0.72,
                    "weight": 0.40,
                    "weighted_score": 0.288,
                    "available": True,
                    "source_description": "FEMA NRI v1.20 risk_national_percentile / 100",
                },
                {
                    "component": "social_vulnerability",
                    "raw_score": 0.58,
                    "weight": 0.35,
                    "weighted_score": 0.203,
                    "available": True,
                    "source_description": "CDC SVI 2022 tribal_svi_composite (Themes 1+2+4)",
                },
                {
                    "component": "adaptive_capacity_deficit",
                    "raw_score": 0.52,
                    "weight": 0.25,
                    "weighted_score": 0.130,
                    "available": True,
                    "source_description": "1.0 - (NRI RESL_SCORE / 100)",
                },
            ],
            "data_completeness_factor": 1.0,
            "confidence_note": "Full data: all vulnerability components available.",
            "formula_version": "v1.4-3c",
        },
        "nri_expanded": {
            "eal_breakdown": {
                "buildings": 85000.25,
                "population": 40000.10,
                "agriculture": 25000.15,
                "total": 150000.50,
            },
            "risk_national_percentile": 72.0,
            "risk_state_percentile": 62.5,
            "community_resilience_score": 48.0,
            "community_resilience_rating": "Relatively Moderate",
            "counties_analyzed": 3,
            "nri_version": "1.20",
            "coverage_status": "full",
        },
        "svi": {
            "themes": [
                {"theme_id": "theme1", "name": "Socioeconomic Status", "percentile": 0.45, "flag_count": 2},
                {"theme_id": "theme2", "name": "Household Characteristics", "percentile": 0.72, "flag_count": 3},
                {"theme_id": "theme4", "name": "Housing Type & Transportation", "percentile": 0.57, "flag_count": 1},
            ],
            "tribal_svi_composite": 0.58,
            "rpl_themes_raw": 0.65,
            "counties_analyzed": 3,
            "coverage_status": "full",
        },
        "climate_projections": {
            "status": "unavailable",
            "reason": "LOCA2 deferred to v1.5+",
        },
        "generated_at": "2026-02-17T14:30:00+00:00",
        "schema_version": "1.4.0",
    }
```

#### Test Count Estimates

| Phase | New Test Files | New Tests | Running Total | Notes |
|-------|---------------|-----------|---------------|-------|
| 19    | test_vulnerability_schemas.py, test_vulnerability_builder.py | ~80 | ~1,044 | Schema validation + builder unit tests |
| 20    | test_flood_schemas.py, test_flood_builder.py | ~50 | ~1,094 | 6 flood sources, each ~8 tests |
| 21    | test_climate_schemas.py, test_climate_builder.py, test_geologic_infrastructure.py | ~40 | ~1,134 | 6 sources, some simpler (NWS alerts, drought) |
| 22    | (extend test_vulnerability_builder.py) | ~30 | ~1,164 | Composite integration, pipeline loading, compliance |
| 23    | test_vulnerability_rendering.py | ~40 | ~1,204 | Rendering, audience air gap, Doc E |
| 24    | test_vulnerability_web.py | ~20 | ~1,224 | Web badges, detail loading, charts |
| **Total** | **~9 new test files** | **~260** | **~1,224** | |

#### Critical Test Scenarios

These tests MUST exist before Phase 22 composite score computation:

1. **NaN/Inf guard on all numeric fields** -- Every float field in every vulnerability model must reject NaN, Inf, -Inf via validator (mirrors TestSafeFloat pattern)
2. **Theme 3 rejection** -- SVIProfile must reject `theme_id="theme3"` with an error message explaining WHY Theme 3 is excluded
3. **tribal_svi_composite vs RPL_THEMES** -- Test that composite is computed from Themes 1+2+4, NOT from RPL_THEMES
4. **National percentile computation** -- Test rank-based percentile across mock county set (10 counties, verify rank math)
5. **Area-weighted SVI** -- Multi-county Tribe with different SVI values; verify weighted average matches expected (mirrors TestAreaWeightedAggregation)
6. **Weight redistribution** -- Missing SVI: verify hazard+adaptive weights are renormalized to sum to 1.0
7. **Zero-county edge case** -- Tribe with no crosswalk entries: verify score=0.0, coverage=UNAVAILABLE, non-null profile (schema consistency)
8. **Alaska partial coverage** -- Alaska Tribe with 2 of 5 counties matched: verify `counties_analyzed=2`, coverage_status=PARTIAL
9. **Rating consistency** -- For every score in {0.0, 0.19, 0.20, 0.39, 0.40, 0.59, 0.60, 0.79, 0.80, 1.0}, verify `_score_to_vulnerability_rating()` returns the correct tier
10. **Atomic write** -- Structural test (via `inspect.getsource()`) that VulnerabilityProfileBuilder uses `tempfile.mkstemp()` + `os.replace()` pattern
11. **Path traversal guard** -- tribe_id with `../` or `.` rejected before file write
12. **Coastal vs inland** -- CoastalWaterProfile: inland Tribe gets NOT_APPLICABLE, coastal Tribe gets data
13. **Landslide scoping** -- OK Tribe gets NOT_APPLICABLE, WA Tribe gets data
14. **Formula version field** -- Composite with `formula_version="v1.4-3c"` passes; unknown version flagged
15. **Schema version forward compat** -- `schema_version="1.4.0"` accepted; `"1.3.0"` triggers warning or validation

---

### Recommendations

#### Schema Decisions Needed Before Phase 19

1. **DECIDE: National percentile computation method.** Recommendation: rank-based percentile (`scipy.stats.percentileofscore()` or manual rank / N * 100) computed over all ~3,200 counties at build time in `VulnerabilityProfileBuilder`. Store as `risk_national_percentile` on `NRIExpandedProfile`. This is a one-time computation per build cycle, not per-Tribe.

2. **DECIDE: Tribal SVI composite method.** Recommendation: simple average of `RPL_THEME1 + RPL_THEME2 + RPL_THEME4` (not re-ranking from EPL_* variables). Simple average is defensible, transparent, and consistent with the SVI methodology of percentile aggregation. Re-ranking would require recomputing from underlying census variables -- overkill for v1.4.

3. **DECIDE: SVI -999 sentinel handling.** The SVI CSV uses -999 for missing data (counties with suppressed census data). Recommendation: treat -999 as `None` in parsing, exclude that theme from the average, reduce `flag_count` accordingly, set `coverage_status=PARTIAL`.

4. **DECIDE: Schema module file vs single file.** Recommendation: 4 separate files (`vulnerability.py`, `flood.py`, `climate.py`, `infrastructure.py`) as documented above. Keeps each file focused and allows Phase 20/21 to add models without touching Phase 19 code.

5. **DECIDE: VulnerabilityProfile forward references.** The `VulnerabilityProfile` model references `FloodProfile`, `ClimateWeatherProfile`, `GeologicProfile`, and `InfrastructureProfile` as `Optional` with `None` defaults. These models are defined in separate files. Use Pydantic v2 forward reference resolution via `model_rebuild()` in `__init__.py` after all modules are imported. Alternatively, type them as `Optional[dict]` in Phase 19 and convert to typed references in Phase 20/21. Recommendation: use `Optional[dict]` initially (consistent with `hazard_profile: dict` in `TribePacketContext`), add typed schema validation as a model method (like `HazardProfile.get_nri_source()`).

6. **PRE-PHASE 19 CODE CHANGE:** Add `vulnerability_profile: dict = field(default_factory=dict)` to `TribePacketContext` in `src/packets/context.py`. Zero-risk, all 964 tests pass, enables immediate integration testing. Place after `congressional_intel` field, before metadata fields.

7. **PRE-PHASE 19 CODE CHANGE:** Add path constants to `src/paths.py`:
   - `SVI_DIR`, `SVI_COUNTY_PATH`, `VULNERABILITY_PROFILES_DIR`
   - `vulnerability_profile_path()` helper function
   - Follow the exact naming conventions documented by Fire Keeper

8. **DO NOT add xarray/netCDF4 to requirements.txt.** LOCA2 is deferred. When v1.5+ implements climate projections, use the Thresholds CSV (not primary NetCDF) to avoid the xarray dependency entirely. If NetCDF is eventually needed, use the guarded-import pattern with helpful error message.

9. **FIX FY26 HARDCODING before Phase 19.** Fire Keeper identified 22 instances. At minimum fix `doc_types.py` (8 instances) and `docx_engine.py` (2 instances) before defining DOC_E. Otherwise DOC_E inherits the same debt pattern.

---

*River Runner | Phase 18.5 | 2026-02-17*
*Schema-first: if the types are right, the code follows.*
*Sovereignty is the innovation. Relatives, not resources.*
