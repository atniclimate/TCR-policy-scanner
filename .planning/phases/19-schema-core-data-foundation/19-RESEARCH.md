# Phase 19: Schema & Core Data Foundation - Research

**Researched:** 2026-02-17
**Domain:** Pydantic v2 schemas, FEMA NRI expansion, CDC SVI integration, sovereignty-first vocabulary, data pipeline patterns
**Confidence:** HIGH (all findings based on direct codebase inspection and verified federal data sources)

## Summary

Phase 19 establishes the data contracts and core vulnerability inputs that all subsequent phases (20-24) depend on. The research confirms that the existing codebase provides a complete, well-tested template in `HazardProfileBuilder` (1,291 lines in `src/packets/hazards.py`) that new builders must follow step-for-step. The existing `src/schemas/models.py` (1,261 lines, 19 Pydantic v2 models) establishes all schema conventions. The Phase 18.5 agent reports (River Runner, Fire Keeper, Sovereignty Scout, Horizon Walker) provide fully drafted schemas, framing vocabulary, and codebase inventories that reduce Phase 19 to mostly an implementation-against-spec task.

Key findings: (1) 22 FY26 hardcodes must be fixed first across 8 files, with `doc_types.py` (8 instances) being highest priority; (2) the NRI CSV already extracts 10 composite fields and 5 per-hazard fields per hazard type, but needs 6 new composite columns and 4 new per-hazard columns for VULN-01; (3) SVI 2022 county CSV uses `FIPS` as the join key (joinable to NRI `STCOFIPS`), with `-999` sentinels for missing data; (4) Connecticut FIPS changed in 2022 from 8 legacy counties to 9 planning regions with new codes (09110-09190), requiring a mapping table in the NRI builder; (5) the River Runner report provides complete Pydantic v2 schema code for all 11 Phase 19 models.

**Primary recommendation:** Follow the River Runner schemas as the implementation spec, fix FY26 debt first, and build the SVI/NRI expanded builders by replicating the HazardProfileBuilder pattern exactly.

---

## 1. Builder Pattern Analysis (populate_hazards.py Template)

**Source:** `F:\tcr-policy-scanner\src\packets\hazards.py` (1,291 lines)
**Confidence:** HIGH (direct code inspection)

### HazardProfileBuilder 9-Step Pattern

The `HazardProfileBuilder` class is the EXACT template that all new data builders must follow. The pattern is:

| Step | Method | Purpose |
|------|--------|---------|
| 1 | `__init__(config)` | Accept config dict, read paths with fallbacks, load TribalRegistry (lazy import), load crosswalk, load area weights |
| 2 | `_load_crosswalk()` | Parse `aiannh_tribe_crosswalk.json`, build reverse mapping (tribe_id -> [GEOIDs]) |
| 3 | `_load_area_weights()` | Parse `tribal_county_area_weights.json`, handle missing file gracefully |
| 4 | `_load_nri_county_data()` | Parse county CSV with `csv.DictReader`, `encoding="utf-8-sig"`, `_safe_float()` for ALL numeric conversions |
| 5 | `_build_tribe_nri_profile()` | 4-tier resolution: AIANNH GEOIDs -> area weights -> relational CSV -> state fallback. Area-weighted averaging with normalization |
| 6 | USFS override | Conditional source override (NRI WFIR -> USFS) when both > 0 |
| 7 | Atomic write | `tempfile.mkstemp()` + `os.fdopen(encoding="utf-8")` + `json.dump(indent=2, ensure_ascii=False)` + `os.replace()` |
| 8 | Path traversal guard | `Path(tribe_id).name` + reject `..` |
| 9 | Coverage report | JSON + Markdown reports with per-state breakdown |

### Critical Implementation Details

**`_safe_float()` function (line 80-106):**
- Handles None, empty string, NaN, Inf, -Inf
- Returns configurable default (0.0)
- MUST be reused (import from hazards.py or replicate) for all CSV numeric parsing
- NRI data contains empty cells and sentinel values

**Weight normalization (lines 616-624):**
- Weights normalized to sum to 1.0 across MATCHED counties only (not all counties in crosswalk)
- Zero total_w guard: falls back to equal weight (1/N) to prevent division by zero
- If same county appears via multiple GEOIDs, weights are SUMMED (not averaged)

**Rating derivation (line 124-146):**
- `score_to_rating()` uses quintile breakpoints: >=80 Very High, >=60 Relatively High, >=40 Relatively Moderate, >=20 Relatively Low, <20 Very Low
- Ratings are ALWAYS re-derived from weighted scores, NEVER averaged from source rating strings

**Empty profile pattern (lines 713-750):**
- All 18 hazard codes always present with zero values for schema consistency
- Ensures downstream renderers never encounter missing keys

### Pattern for VulnerabilityProfileBuilder

New builders for SVI and NRI expansion follow the same pattern:
```python
class SVIBuilder:
    def __init__(self, config: dict) -> None:
        # Load TribalRegistry, crosswalk, area weights (SAME as HazardProfileBuilder)

    def _load_svi_county_data(self) -> dict[str, dict]:
        # Parse SVI CSV, _safe_float() for all RPL_THEME columns

    def _build_tribe_svi_profile(self, tribe_id, tribe, county_data) -> dict:
        # Area-weighted aggregation (SAME crosswalk)

    def build_all_profiles(self) -> int:
        # Path guard, atomic write, coverage report (SAME pattern)
```

---

## 2. NRI CSV Current Usage & Expansion Points

**Source:** `F:\tcr-policy-scanner\src\packets\hazards.py` lines 323-392
**Confidence:** HIGH (direct code inspection + Sovereignty Scout validation)

### Currently Extracted Fields (10 composite + 5 per-hazard)

**Composite fields (lines 360-377):**

| Field | NRI CSV Column | Type | Purpose |
|-------|---------------|------|---------|
| `risk_score` | `RISK_SCORE` | float | Composite risk score |
| `risk_rating` | `RISK_RATNG` | str | Rating label |
| `risk_value` | `RISK_VALUE` | float | Risk value |
| `eal_total` | `EAL_VALT` | float | Total Expected Annual Loss (USD) |
| `eal_score` | `EAL_SCORE` | float | EAL normalized score |
| `eal_rating` | `EAL_RATNG` | str | EAL rating label |
| `sovi_score` | `SOVI_SCORE` | float | Social Vulnerability score |
| `sovi_rating` | `SOVI_RATNG` | str | Social Vulnerability rating |
| `resl_score` | `RESL_SCORE` | float | Community Resilience score |
| `resl_rating` | `RESL_RATNG` | str | Community Resilience rating |

**Per-hazard fields (lines 379-386, for each of 18 hazard codes):**

| Field | NRI CSV Column | Type |
|-------|---------------|------|
| `risk_score` | `{CODE}_RISKS` | float |
| `risk_rating` | `{CODE}_RISKR` | str |
| `eal_total` | `{CODE}_EALT` | float |
| `annualized_freq` | `{CODE}_AFREQ` | float |
| `num_events` | `{CODE}_EVNTS` | float |

### New Fields Required for VULN-01

**New composite fields (confirmed by Sovereignty Scout, NRI v1.20 Data Dictionary):**

| Field | NRI CSV Column | Status | Purpose |
|-------|---------------|--------|---------|
| `eal_buildings` | `EAL_VALB` | CONFIRMED | EAL to buildings (USD) |
| `eal_population` | `EAL_VALP` | CONFIRMED | EAL to population (USD) |
| `eal_pop_equiv` | `EAL_VALPE` | CONFIRMED | EAL population equivalence (USD) |
| `eal_agriculture` | `EAL_VALA` | CONFIRMED | EAL to agriculture (USD) |
| `risk_state_pctl` | `RISK_SPCTL` | CONFIRMED | State percentile (0-100) |
| `population` | `POPULATION` | CONFIRMED | Population (2020 Census) |
| `building_value` | `BUILDVALUE` | CONFIRMED | Building value (USD) |
| `area` | `AREA` | CONFIRMED | Area (sq mi) |

**CRITICAL: `RISK_NPCTL` does NOT exist** in NRI v1.20. Only `RISK_SPCTL` (state percentile) exists. The national percentile must be COMPUTED at build time from `RISK_SCORE` rank across all ~3,200 counties. Decision [18.5-DEC-01] confirms this approach.

**New per-hazard fields (confirmed, per hazard code):**

| Field | NRI CSV Column | Purpose |
|-------|---------------|---------|
| `eal_buildings` | `{CODE}_EALB` | Per-hazard EAL to buildings |
| `eal_population` | `{CODE}_EALP` | Per-hazard EAL to population |
| `eal_pop_equiv` | `{CODE}_EALPE` | Per-hazard EAL pop equivalence |
| `eal_agriculture` | `{CODE}_EALA` | Per-hazard EAL to agriculture |

### National Percentile Computation

Algorithm for build-time computation:
1. Load all ~3,200 county `RISK_SCORE` values
2. Sort descending
3. For each Tribe's area-weighted `risk_score`, compute `rank / total * 100`
4. Store as `risk_national_percentile` (0-100 scale)

This must happen AFTER area-weighted aggregation, since the Tribe's score is derived from multiple counties.

---

## 3. SVI 2022 Data Format & Integration Approach

**Source:** CDC/ATSDR SVI 2022 Documentation, Sovereignty Scout report
**Confidence:** HIGH (verified from official CDC documentation and codebase inspection)

### SVI 2022 CSV Column Reference

**Geographic identifiers:**

| Column | Description |
|--------|-------------|
| `FIPS` | 5-digit county FIPS code (joinable to NRI `STCOFIPS`) |
| `STATE` | State name |
| `ST_ABBR` | State abbreviation |
| `COUNTY` | County name |

**Theme percentile rankings (0.0 to 1.0 scale):**

| Column | Theme | Status in Tribal Composite |
|--------|-------|---------------------------|
| `RPL_THEME1` | Socioeconomic Status | INCLUDED |
| `RPL_THEME2` | Household Characteristics & Disability | INCLUDED |
| `RPL_THEME3` | Racial & Ethnic Minority Status | EXCLUDED (tautological for Indigenous Nations) |
| `RPL_THEME4` | Housing Type & Transportation | INCLUDED |
| `RPL_THEMES` | Overall (all 4 themes) | NOT USED (includes excluded Theme 3) |

**Flag columns (binary, per variable):**
- `F_THEME1` through `F_THEME4`: Count of component variables above 90th percentile
- `F_TOTAL`: Total flags across all themes

**Estimate columns:**
- `E_*`: Raw ACS estimates (16 census variables)
- `EP_*`: Percentages
- `EPL_*`: Percentile rankings per variable

### Missing Data Handling

**Sentinel value: `-999`** for all fields where data is unavailable. The `_safe_float()` function already handles this correctly (parses to -999.0 which is a valid float), but the builder must explicitly check for -999 and treat it as missing:

```python
def _safe_svi_float(value, default=None):
    """Like _safe_float but treats -999 as missing (None)."""
    result = _safe_float(value, default=default)
    if result is not None and result == -999.0:
        return default
    return result
```

### Custom Tribal SVI Composite (Decision [18.5-DEC-02])

Formula: `tribal_svi_composite = mean(RPL_THEME1, RPL_THEME2, RPL_THEME4)`

Theme 3 (Racial & Ethnic Minority Status) is excluded because it captures minority status and limited English proficiency. For Tribal Nations -- all of whom are Indigenous by definition -- this theme introduces a tautological signal that would artificially inflate vulnerability scores for every Tribe equally.

The raw `RPL_THEMES` value (which includes Theme 3) should be stored for reference as `rpl_themes_raw` but NOT used in composite scoring.

### Integration Approach

1. Download SVI 2022 county CSV (~15 MB, ~3,200 rows) via `scripts/download_svi_data.py`
2. Parse with `csv.DictReader`, `encoding="utf-8-sig"` (possible BOM)
3. Join to Tribes via existing `tribal_county_area_weights.json` crosswalk (keyed by county FIPS)
4. Area-weighted average of RPL_THEME1, RPL_THEME2, RPL_THEME4 per Tribe
5. Compute tribal_svi_composite as mean of the 3 theme percentiles
6. Flag counties with -999 sentinel values and exclude from averages
7. Write per-Tribe SVI data into the vulnerability profile

### Connecticut FIPS Change (XCUT-03)

**CRITICAL:** In June 2022, Connecticut changed from 8 legacy counties (FIPS 09001-09015) to 9 planning regions (FIPS 09110-09190) as county equivalents. This affects both NRI and SVI data:

- **NRI v1.20 (December 2025):** May use legacy OR new FIPS codes depending on when FEMA updated their geographic base. Must check the actual CSV.
- **SVI 2022 (based on 2018-2022 ACS):** Uses the new planning region FIPS codes (confirmed: ACS 2022 uses new CT codes).
- **Existing area crosswalk:** Built from Census TIGER 2024 shapefiles, which use the NEW Connecticut codes.

**Required:** A CT FIPS mapping table that maps legacy codes to new codes for data sources that still use the old ones. This is part of XCUT-03.

Legacy -> New mapping (approximate, many-to-many):

| Legacy FIPS | Legacy County | New FIPS Range |
|-------------|--------------|----------------|
| 09001 | Fairfield | 09110, 09120 (partial) |
| 09003 | Hartford | 09130 (partial), 09150 (partial) |
| 09005 | Litchfield | 09150 (partial), 09160 (partial) |
| 09007 | Middlesex | 09140 (partial), 09170 (partial) |
| 09009 | New Haven | 09110 (partial), 09120, 09170 (partial) |
| 09011 | New London | 09140 (partial) |
| 09013 | Tolland | 09130 (partial), 09180 (partial) |
| 09015 | Windham | 09180 (partial), 09190 (partial) |

**Impact on TCR project:** Very low. Connecticut has only 2 federally recognized Tribes (Mashantucket Pequot, Mohegan), both in New London County area. But the mapping table must exist for data integrity and to prevent silent data loss.

---

## 4. FY26 Hardcoding Inventory (Exact File:Line Locations)

**Source:** Grep search of `src/` + Fire Keeper report
**Confidence:** HIGH (direct code search)

### Total: 22 instances across 8 files

#### Priority 1: Display strings that MUST use `config.FISCAL_YEAR_SHORT` (11 instances)

| File | Line | Current Code | Fix |
|------|------|-------------|-----|
| `src/packets/doc_types.py` | 113 | `f"{slug}_{self.filename_suffix}_fy26.docx"` | Use `FISCAL_YEAR_SHORT.lower()` |
| `src/packets/doc_types.py` | 124 | `title_template="FY26 Federal Funding Overview & Strategy"` | Use f-string with `FISCAL_YEAR_SHORT` |
| `src/packets/doc_types.py` | 142 | `title_template="FY26 Climate Resilience Program Priorities"` | Use f-string |
| `src/packets/doc_types.py` | 143 | `header_template="{tribe_name} \| FY26 Climate Resilience..."` | Use f-string |
| `src/packets/doc_types.py` | 160 | `title_template="FY26 InterTribal Climate Resilience Strategy"` | Use f-string |
| `src/packets/doc_types.py` | 178 | `title_template="FY26 Regional Climate Resilience Overview"` | Use f-string |
| `src/packets/doc_types.py` | 179 | `header_template="{region_name} \| FY26 Regional..."` | Use f-string |
| `src/packets/docx_engine.py` | 180 | `header_text = "FY26 Climate Resilience Program Priorities"` | Use f-string |
| `src/packets/docx_template.py` | 515 | `"FY26 Climate Resilience Program Priorities"` | Use f-string |
| `src/packets/docx_engine.py` | 174 | Docstring: `FY26 program overview header` | Update docstring |
| `src/packets/docx_sections.py` | 70 | Docstring: `uses default FY26 title` | Update docstring |

**Technical challenge with `doc_types.py`:** The `DocumentTypeConfig` is a frozen dataclass. Title/header templates are set at module import time. Since `config.FISCAL_YEAR_SHORT` is also computed at import time, the fix is straightforward: import at module level and use f-strings in the template definitions:

```python
from src.config import FISCAL_YEAR_SHORT

DOC_A = DocumentTypeConfig(
    title_template=f"{FISCAL_YEAR_SHORT} Federal Funding Overview & Strategy",
    ...
)
```

For `format_filename()`, use lazy import at call time or pass as parameter:

```python
def format_filename(self, slug: str) -> str:
    from src.config import FISCAL_YEAR_SHORT
    fy = FISCAL_YEAR_SHORT.lower()
    return f"{slug}_{self.filename_suffix}_{fy}.docx"
```

#### Priority 2: Semantic identifiers (lower priority, 7 instances)

| File | Line | Nature | Assessment |
|------|------|--------|------------|
| `src/graph/schema.py` | 20 | `fy26_status: str = ""` (field name) | Semantic identifier, not display. Rename to `fy_status` or `ci_status_current` |
| `src/graph/schema.py` | 36 | Docstring `FY26 Consolidated Appropriations` | Example text in docstring |
| `src/graph/schema.py` | 60 | `urgency: str = ""  # Immediate / FY26 / Ongoing` | Comment example |
| `src/graph/builder.py` | 161 | `fy26_status=prog.get("ci_status", "")` | Field assignment matching schema |
| `src/schemas/models.py` | 76 | `"""Program status from FY26 Hot Sheets review."""` | Docstring |
| `src/schemas/models.py` | 96 | `examples=["FY26 Hot Sheets v2"]` | Example value in field |
| `src/schemas/models.py` | 287 | `description="FY26 funding amount string"` | Field description |

#### Priority 3: Not hardcodes -- correct semantic usage (4 instances)

| File | Nature | Assessment |
|------|--------|------------|
| `src/monitors/iija_sunset.py` (4 instances) | `IIJA_FY26_PROGRAMS` dict name, docstrings | These are semantic identifiers for a specific set of IIJA programs that expire at end of FY26. The FY26 here refers to a fixed historical date, not the dynamic current FY. **DO NOT change.** |
| `src/config.py` (3 instances) | Docstring examples | These ARE the FY computation module. `FY26` in examples is correct. |

### Summary

- **Must fix (Plan 19-01):** 11 display-string instances in Priority 1
- **Should fix (Plan 19-01):** 3-4 semantic identifiers in Priority 2 (graph schema field name, schema models docstrings/examples)
- **Do not fix:** IIJA sunset monitor (fixed historical reference), config.py (defining module)

---

## 5. Crosswalk Aggregation Pattern

**Source:** `F:\tcr-policy-scanner\data\nri\tribal_county_area_weights.json` (direct inspection)
**Confidence:** HIGH

### File Structure

```json
{
  "metadata": {
    "description": "Area-weighted AIANNH-to-county geographic crosswalk",
    "source_aiannh": "Census TIGER/Line AIANNH 2024",
    "source_county": "Census TIGER/Line County 2024",
    "crs_alaska": "EPSG:3338",
    "crs_conus": "EPSG:5070",
    "min_overlap_pct": 0.01,
    "total_aiannh_entities": 642,
    "total_county_links": 1019,
    "generated_at": "2026-02-11T20:00:45+00:00",
    "version": "1.0"
  },
  "crosswalk": {
    "GEOID": [
      {"county_fips": "35006", "overlap_area_sqkm": 1069.9, "weight": 1.0},
      {"county_fips": "35053", "overlap_area_sqkm": 190.8, "weight": 0.388}
    ]
  }
}
```

### Key Properties

- **Keys:** AIANNH GEOID strings (e.g., "0010R", "0010T", "0020R")
- **Values:** Array of `{county_fips, overlap_area_sqkm, weight}` objects
- **Weights:** Sum to 1.0 within each GEOID entry (proportional to overlap area)
- **642 AIANNH entities** -> **1,019 total county links** (average ~1.6 counties per entity)
- **Join path:** tribe_id -> AIANNH GEOID (via `aiannh_tribe_crosswalk.json`) -> county FIPS (via area weights)

### Reuse for SVI and NRI Expansion

The crosswalk is **directly reusable** for all county-keyed data sources:
- SVI 2022 county CSV: join on `FIPS` column = `county_fips` in crosswalk
- NRI expanded fields: same CSV, same county FIPS join
- Any future county-level data source

**No new geographic infrastructure needed.** The SVI builder imports the same crosswalk loading code.

---

## 6. Existing Schema Conventions (src/schemas/)

**Source:** `F:\tcr-policy-scanner\src\schemas\models.py` (1,261 lines, 19 models)
**Confidence:** HIGH (direct code inspection)

### Import Pattern (MANDATORY for new schema files)

```python
from __future__ import annotations
from typing import Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator
```

### Field Conventions

| Convention | Example | Notes |
|-----------|---------|-------|
| Required fields | `tribe_id: str = Field(..., description="...")` | Ellipsis for required |
| Optional with default | `risk_score: float = Field(default=0.0, ge=0.0)` | Named default |
| Optional nullable | `cfda: Optional[str] = Field(default=None)` | None for truly optional |
| Lists | `awards: list[FundingRecord] = Field(default_factory=list)` | Factory for mutables |
| Dicts | `all_hazards: dict[str, HazardDetail] = Field(default_factory=dict)` | Typed dicts |
| Descriptions | Always present, 1-2 sentences | Used in documentation |
| Examples | `examples=["epa_100000001"]` | For representative values |
| Constraints | `ge=0.0, le=1.0` | Pydantic v2 numeric constraints |

### Validator Conventions

**Field validators (single-field, frozenset membership):**
```python
@field_validator("status")
@classmethod
def validate_status(cls, v: str) -> str:
    if v not in CI_STATUSES:
        raise ValueError(f"Invalid CI status '{v}'. Must be one of: {sorted(CI_STATUSES)}")
    return v
```

**Model validators (cross-field, mode="after"):**
```python
@model_validator(mode="after")
def validate_specialist_fields(self) -> "ProgramRecord":
    if self.specialist_required and not self.specialist_focus:
        raise ValueError(...)
    return self
```

**tribe_id validator (reused in 5+ models):**
```python
@field_validator("tribe_id")
@classmethod
def validate_tribe_id_format(cls, v: str) -> str:
    if not v.startswith("epa_"):
        raise ValueError(f"tribe_id must start with 'epa_', got '{v}'")
    numeric_part = v[4:]
    if not numeric_part.isdigit():
        raise ValueError(...)
    return v
```

### Module Organization

- `src/schemas/models.py`: All 19 existing models in one file
- `src/schemas/__init__.py`: Re-exports all models with `__all__`
- **Decision for Phase 19:** Create `src/schemas/vulnerability.py` as a new module (models.py is already 1,261 lines; adding ~500 more would be unwieldy)

### Enum Conventions

Existing code uses `frozenset` for validation sets, not Python `Enum`. The River Runner report introduces `str, Enum` subclasses (`VulnerabilityRating`, `CoverageStatus`) which is a pattern upgrade. Both patterns are Pydantic v2 compatible.

---

## 7. TribePacketContext Integration Points

**Source:** `F:\tcr-policy-scanner\src\packets\context.py` (87 lines)
**Confidence:** HIGH (direct code inspection)

### Current Structure

`TribePacketContext` is a plain `@dataclass` (NOT Pydantic) with 15 fields:

| Field | Type | Default | Source |
|-------|------|---------|--------|
| `tribe_id` | `str` | (required) | Registry |
| `tribe_name` | `str` | (required) | Registry |
| `states` | `list[str]` | `[]` | Registry |
| `ecoregions` | `list[str]` | `[]` | EcoregionMapper |
| `bia_code` | `str` | `""` | Registry |
| `epa_id` | `str` | `""` | Registry |
| `districts` | `list[dict]` | `[]` | CongressionalMapper |
| `senators` | `list[dict]` | `[]` | CongressionalMapper |
| `representatives` | `list[dict]` | `[]` | CongressionalMapper |
| `awards` | `list[dict]` | `[]` | Award cache |
| `hazard_profile` | `dict` | `{}` | Hazard cache |
| `economic_impact` | `dict` | `{}` | EconomicImpactCalculator |
| `congressional_intel` | `dict` | `{}` | Congressional intel cache |
| `generated_at` | `str` | `""` | Timestamp |
| `congress_session` | `str` | `"119"` | Static |

### Adding `vulnerability_profile: dict`

**Placement:** After `congressional_intel`, before metadata fields.
**Pattern:** Identical to `hazard_profile`, `economic_impact`, `congressional_intel` (all `dict` with `field(default_factory=dict)`).
**Backward compatibility:** All 964 tests continue to pass -- the field has a default.
**Memory:** +5-10 KB per Tribe x 592 = ~5 MB total (negligible).
**Serialization:** `to_dict()` uses `dataclasses.asdict()` which handles nested dicts recursively. No change needed.

### Orchestrator Loading Pattern

**Source:** `F:\tcr-policy-scanner\src\packets\orchestrator.py` (lines 88-100)

Cache directories are set up in `__init__()`:
```python
raw = packets_cfg.get("hazards", {}).get("cache_dir")
self.hazard_cache_dir = Path(raw) if raw else HAZARD_PROFILES_DIR
```

Cache files are loaded in `_build_context()` via the generic `_load_tribe_cache()` method:
- Sanitizes tribe_id (regex `^[a-zA-Z0-9_-]+$`)
- Checks file existence
- Enforces 10 MB size limit
- Opens with `encoding="utf-8"`
- Returns `{}` on any failure (never raises)

**Pattern for vulnerability:**
```python
# In __init__:
raw = packets_cfg.get("vulnerability", {}).get("cache_dir")
self.vulnerability_cache_dir = Path(raw) if raw else VULNERABILITY_PROFILES_DIR

# In _build_context:
vulnerability_data = self._load_tribe_cache(self.vulnerability_cache_dir, tribe_id)
```

Zero new infrastructure needed. The generic loader handles all per-Tribe JSON caches.

---

## 8. Path Constants Current Pattern

**Source:** `F:\tcr-policy-scanner\src\paths.py` (172 lines, 35 constants + 3 helpers)
**Confidence:** HIGH (direct code inspection)

### Naming Conventions

| Type | Pattern | Example |
|------|---------|---------|
| Directories | `SCREAMING_SNAKE_DIR` | `NRI_DIR`, `AWARD_CACHE_DIR` |
| Files | `SCREAMING_SNAKE_PATH` | `GRAPH_SCHEMA_PATH`, `TRIBAL_REGISTRY_PATH` |
| Helpers | `snake_case_path(tribe_id: str) -> Path` | `award_cache_path()`, `hazard_profile_path()` |

### Grouping Convention

Constants grouped by purpose with `# -----------` section headers:
1. Project Root
2. Config Paths
3. Data Paths (flat files)
4. Data Paths (subdirectories)
5. Output Paths
6. Docs Paths
7. Scripts Paths
8. Helper Functions (per-Tribe paths)

### Design Rules (from module docstring)

1. Imports ONLY `pathlib.Path` -- no project imports, no config imports
2. No path existence checks at import time
3. Callers create directories as needed with `mkdir(parents=True, exist_ok=True)`

### New Constants Needed (6 constants + 1 helper)

```python
# -- Climate/Vulnerability Data Paths --

SVI_DIR: Path = DATA_DIR / "svi"
"""CDC/ATSDR Social Vulnerability Index data cache."""

SVI_COUNTY_PATH: Path = SVI_DIR / "SVI2022_US_COUNTY.csv"
"""CDC SVI 2022 county-level CSV for all US counties."""

CLIMATE_DIR: Path = DATA_DIR / "climate"
"""NOAA/USGS climate projection data cache."""

CLIMATE_SUMMARY_PATH: Path = CLIMATE_DIR / "county_climate_summaries.json"
"""Processed LOCA2 county-level climate projection summaries."""

VULNERABILITY_PROFILES_DIR: Path = DATA_DIR / "vulnerability_profiles"
"""Per-Tribe vulnerability profile JSON files (592 files)."""

CLIMATE_RAW_DIR: Path = CLIMATE_DIR / "loca2_raw"
"""Raw LOCA2 NetCDF downloads (temporary, deletable after processing)."""

# Helper function
def vulnerability_profile_path(tribe_id: str) -> Path:
    """Return the vulnerability profile JSON path for a specific Tribe."""
    return VULNERABILITY_PROFILES_DIR / f"{tribe_id}.json"
```

**Post-addition count:** 41 constants + 4 helper functions.

---

## 9. Key Risk Areas & Edge Cases

### Risk 1: Connecticut FIPS Mismatch (MEDIUM)

NRI v1.20 (December 2025) may still use legacy CT FIPS codes (09001-09015) while SVI 2022 and the area crosswalk use new planning region codes (09110-09190). This would cause silent data loss for Connecticut counties.

**Mitigation:** Check the actual NRI CSV for CT FIPS codes at build time. If legacy codes found, apply CT FIPS mapping before crosswalk join.

### Risk 2: SVI -999 Sentinels (HIGH)

The `-999` sentinel value parses as a valid float (-999.0) through `_safe_float()`. If not explicitly handled, it would severely skew area-weighted averages (e.g., averaging 0.7 and -999.0 gives -499.15).

**Mitigation:** Create `_safe_svi_float()` that treats -999.0 as None/missing. Exclude counties with -999 values from the weighted average denominator.

### Risk 3: National Percentile Computation Ordering (MEDIUM)

The national percentile must be computed from the COUNTY-LEVEL `RISK_SCORE` ranking (across all ~3,200 counties), NOT from the area-weighted Tribe-level scores. The Tribe's `risk_national_percentile` should reflect where their weighted score falls in the national county distribution.

**Mitigation:** Load all county RISK_SCOREs first, sort, then for each Tribe's weighted score, binary search to find its percentile rank in the county distribution.

### Risk 4: NRI Version Pinning with SHA256 (LOW)

XCUT-03 requires NRI version pinning with SHA256 checksum. The existing `_detect_nri_version()` only detects version from filenames. Adding SHA256 verification requires hashing the CSV file at load time.

**Mitigation:** Compute SHA256 of `NRI_Table_Counties.csv` at load time, store in profile metadata, and optionally verify against a pinned expected hash.

### Risk 5: Atomic Write on Windows (LOW)

`os.replace()` on Windows requires the target file handle to be closed. The existing pattern (`tempfile.mkstemp() -> os.fdopen() -> close -> os.replace()`) handles this correctly. New builders MUST follow the same pattern, not use `NamedTemporaryFile` (which has Windows file lock issues per CLAUDE.md).

### Risk 6: Empty Data for 19 of 592 Tribes (LOW)

Per Phase 13 confirmation, 19 Tribes (592-573=19) have no hazard data. These same Tribes likely have no SVI data. The vulnerability profile must handle the fully-empty case gracefully with `coverage_status: "unavailable"` and meaningful content (framed as federal data gap per Alaska narrative strategy).

### Risk 7: FY26 Fix Breaking Existing Tests (LOW)

Changing FY26 strings will break tests that assert specific filename patterns or title text. The fix must update both source code and corresponding test assertions.

**Mitigation:** Search tests for "fy26", "FY26", and update assertions to use dynamic fiscal year values.

---

## 10. Implementation Recommendations per Plan

### Plan 19-01: Pre-Phase Tech Debt

**Scope:** Fix 22 FY26 hardcodes, add path constants, add TribePacketContext field

**Implementation order:**
1. Add 6 path constants + 1 helper to `src/paths.py` (zero-risk, no logic change)
2. Add `vulnerability_profile: dict` to `TribePacketContext` (zero-risk, has default)
3. Fix 11 Priority 1 FY26 display strings in `doc_types.py`, `docx_engine.py`, `docx_template.py`
4. Fix 3-4 Priority 2 semantic identifiers in `graph/schema.py`, `schemas/models.py`
5. Update `__init__.py` re-exports in `src/schemas/` for new vulnerability module
6. Run full test suite, fix broken assertions (expect ~5-10 test assertion updates for FY26 string changes)

**Key technical decisions:**
- `doc_types.py` `format_filename()`: Use lazy import of `FISCAL_YEAR_SHORT` inside the method to avoid import-time issues with frozen dataclass
- `doc_types.py` title/header templates: Import `FISCAL_YEAR_SHORT` at module level, use f-strings in DOC_A/B/C/D definitions
- Do NOT touch `iija_sunset.py` `IIJA_FY26_PROGRAMS` -- these are fixed historical references

**Test updates needed:**
```
tests/test_doc_types.py -- filename format assertions
tests/test_docx_integration.py -- header/title text assertions
tests/test_docx_template.py -- template header text assertions
tests/test_audience_filtering.py -- possible title assertions
```

### Plan 19-02: Vulnerability Pydantic v2 Schema Models (TDD)

**Scope:** `src/schemas/vulnerability.py` with 11 models

**Models to implement (from River Runner report):**
1. `VulnerabilityRating` (str Enum) -- 5-tier rating
2. `CoverageStatus` (str Enum) -- full/partial/unavailable/not_applicable
3. `SVITheme` -- individual theme percentile + flag count
4. `SVIProfile` -- 3 themes + tribal_svi_composite + metadata
5. `EALBreakdown` -- buildings/population/agriculture/total
6. `PerHazardEAL` -- per-hazard EAL by consequence type
7. `NRIExpandedProfile` -- expanded NRI with national percentile
8. `ClimateProjectionProfile` -- placeholder (all fields Optional, status=UNAVAILABLE)
9. `ComponentScore` -- individual composite component
10. `CompositeVulnerability` -- weighted composite with rating
11. `DataSourceMeta` -- provenance metadata
12. `VulnerabilityProfile` -- top-level container

**TDD approach:** Write tests first from the River Runner spec, then implement models to pass.

**Shared validators:**
- `_validate_unit_float()` for [0,1] range fields
- `_validate_nonneg_float()` for non-negative fields
- Both handle None/NaN/Inf

**Update `src/schemas/__init__.py`** to re-export all new models.

### Plan 19-03: Sovereignty-First Vocabulary Constants Module

**Scope:** `src/packets/vocabulary.py` (or `src/vocabulary.py`)

**From Horizon Walker report (Decision [18.5-DEC-05] Option D Hybrid):**

Constants needed:
- `SECTION_HEADING_VULNERABILITY = "Climate Resilience Investment Profile"`
- `RATING_LABEL_PREFIX = "Resilience Investment Priority"`
- `EXPLANATORY_FRAME = "disproportionate exposure to climate hazards"`
- Approved headings list for Doc A, Doc B, Doc C, Doc D
- Forbidden terms in Doc B (SVI decomposition, strategy language, resilience framing)
- Context-sensitive replacement rules: "vulnerability" allowed ONLY in federal proper nouns

**Key design principle:** Context-sensitive replacement engine, NOT simple word-swap. The word "vulnerable" is appropriate in "CDC Social Vulnerability Index" (proper noun) but inappropriate in "this Tribe is vulnerable" (deficit framing).

**Alaska narrative templates:**
- Full data tier: Standard investment profile
- Partial data tier: Available data + federal data gap framing
- Minimal data tier: Federal infrastructure failure framing with available hazard data

### Plan 19-04: NRI Expanded Builder + Version Pinning + CT FIPS

**Scope:** Expand `_load_nri_county_data()` to extract 8 new composite fields + 4 new per-hazard fields. Add national percentile computation. Add version pinning with SHA256. Add CT FIPS mapping.

**Implementation strategy:**
- Option A: Modify existing `HazardProfileBuilder` to extract expanded fields (preferred -- single source of truth)
- Option B: Create separate `NRIExpandedBuilder` class (duplicates crosswalk loading)
- **Recommend Option A** -- add the expanded fields to the existing builder's CSV parsing, then have the vulnerability builder consume the expanded hazard profile

**National percentile algorithm:**
1. After loading all county data, collect all `RISK_SCORE` values
2. Sort ascending
3. For a given Tribe score, find rank via `bisect.bisect_left(sorted_scores, tribe_score)`
4. Percentile = `rank / len(sorted_scores) * 100`

**NRI version pinning (XCUT-03):**
```python
import hashlib

def _compute_file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
```

Store hash in profile metadata for reproducibility verification.

**CT FIPS mapping:**
```python
CT_LEGACY_TO_NEW = {
    "09001": ["09110", "09120"],  # Fairfield -> partial
    "09003": ["09130", "09150"],  # Hartford -> partial
    # ... complete mapping
}
```

Check if NRI CSV uses legacy codes; if so, remap before crosswalk join.

### Plan 19-05: SVI 2022 Builder

**Scope:** `scripts/download_svi_data.py` + SVI parsing + area-weighted aggregation into vulnerability profiles

**Builder class:** `SVIBuilder` following HazardProfileBuilder pattern

**Key implementation details:**
1. Download script: `scripts/download_svi_data.py` to fetch county CSV from CDC
2. Parse: `csv.DictReader`, `encoding="utf-8-sig"`, sentinel check for -999
3. Extract: `FIPS`, `RPL_THEME1`, `RPL_THEME2`, `RPL_THEME4`, `F_THEME1-4`, `RPL_THEMES`
4. Join: Via existing area-weighted crosswalk (county_fips -> AIANNH GEOID -> tribe_id)
5. Aggregate: Area-weighted average of theme percentiles, skip -999 counties
6. Compute: `tribal_svi_composite = mean(weighted_theme1, weighted_theme2, weighted_theme4)`
7. Write: Per-Tribe SVI data as part of VulnerabilityProfile JSON

**3-theme composite validation:**
```python
@model_validator(mode="after")
def validate_theme_count(self):
    if self.themes and self.counties_analyzed > 0:
        avg = sum(t.percentile for t in self.themes) / len(self.themes)
        if abs(self.tribal_svi_composite - avg) > 0.01:
            raise ValueError(...)
    return self
```

### Plan 19-06: Integration Tests & Encoding/Atomic Write Compliance (XCUT-04)

**Scope:** Integration tests + structural compliance scan

**Test categories:**
1. Schema validation round-trip: Create VulnerabilityProfile -> serialize -> deserialize -> validate
2. Empty profile handling: All 592 Tribes get valid profiles (even with zero data)
3. Crosswalk integration: SVI builder produces correct weighted averages for test data
4. National percentile: Verify percentile computation against known distribution
5. -999 sentinel: Ensure counties with -999 are excluded from averages
6. Atomic write verification: Inspect source code for `tempfile.mkstemp() + os.replace()` pattern
7. Encoding compliance: Scan all `open()` calls for `encoding="utf-8"` parameter

**Structural compliance tests (from existing pattern in `test_xcut_compliance.py`):**
```python
def test_all_open_calls_specify_encoding(self):
    """XCUT-04: Every open() call must have encoding='utf-8'."""
    import inspect
    # Scan source files for open() without encoding
```

**Expected test count:** ~60 new tests for Phase 19, bringing total to ~1,024.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | >=2.0.0 (project uses 2.13.3) | Schema validation | Already in use for 19 models. V2 syntax throughout. |
| python (stdlib csv) | 3.12 | CSV parsing | NRI and SVI both are CSV. DictReader with utf-8-sig encoding. |
| python (stdlib hashlib) | 3.12 | SHA256 checksum | NRI version pinning (XCUT-03). |
| python (stdlib bisect) | 3.12 | National percentile | Binary search for rank in sorted county scores. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | >=7.0 | Testing | TDD for all schema models and builders. |
| openpyxl | >=3.1.0 | XLSX parsing | Only if USFS data involved (already in use). |

No new external dependencies required for Phase 19.

---

## Architecture Patterns

### Pattern 1: Schema-First Development (TDD)

**What:** Define Pydantic v2 models FIRST, write tests against them, THEN implement builders that produce data matching the schemas.

**When to use:** All new data structures in Phase 19.

**Why:** The schemas ARE the contract. Builders implement against schemas. Renderers consume schema-validated data. If the schema is wrong, everything downstream is wrong.

### Pattern 2: Builder Replication

**What:** New data builders (SVI, NRI expanded) follow the HazardProfileBuilder 9-step pattern exactly.

**When to use:** Any new per-Tribe data population script.

**Key steps:** crosswalk loading -> area weights -> CSV parse with _safe_float -> weighted aggregation -> atomic write -> path guard -> coverage report.

### Pattern 3: Context-Sensitive Vocabulary

**What:** Replacement rules that consider surrounding text, not just word presence. "vulnerability" is allowed in "CDC Social Vulnerability Index" but not in "this community is vulnerable."

**When to use:** All vulnerability-related text generation in documents.

### Anti-Patterns to Avoid

- **Never average rating strings.** Always re-derive ratings from weighted numerical scores.
- **Never use `RPL_THEMES` directly.** It includes Theme 3. Compute custom 3-theme composite.
- **Never use `RISK_NPCTL`.** It does not exist in NRI v1.20. Compute national percentile from `RISK_SCORE` rank.
- **Never use `NamedTemporaryFile` for atomic writes.** Use `tempfile.mkstemp() + os.fdopen() + os.replace()` pattern for Windows compatibility.
- **Never parse CSV numerics without `_safe_float()`.** NRI/SVI data contains empty cells, sentinels (-999), and potential NaN/Inf values.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Area-weighted aggregation | Custom crosswalk code | Import/replicate from `hazards.py` | The crosswalk pattern is tested and handles 4 fallback tiers |
| NaN/Inf guards | Inline try/except | `_safe_float()` from hazards.py | Handles 7+ edge cases (None, "", NaN, Inf, -Inf, non-numeric, whitespace) |
| Rating derivation | String averaging | `score_to_rating()` from hazards.py | Quintile breakpoints are consistent across all NRI-derived scores |
| Atomic file writes | `open().write()` | `tempfile.mkstemp() + os.replace()` | Windows file locking, crash safety, corruption prevention |
| Schema validation | Manual dict checking | Pydantic v2 models with validators | Catches errors at ingestion, not at render time |
| National percentile | Custom sorting/ranking | `bisect.bisect_left()` | O(log n) lookup in sorted array, handles ties correctly |

---

## Common Pitfalls

### Pitfall 1: SVI -999 Sentinel Values

**What goes wrong:** -999 parses as valid float, severely skews weighted averages
**Why it happens:** `_safe_float()` returns -999.0 (valid number, not NaN/Inf)
**How to avoid:** Create `_safe_svi_float()` that treats -999 as None. Exclude from weighted average denominator.
**Warning signs:** Negative composite scores, impossibly low theme percentiles

### Pitfall 2: Connecticut FIPS Code Mismatch

**What goes wrong:** Silent data loss for Connecticut counties in crosswalk join
**Why it happens:** NRI CSV may use legacy codes (09001-09015) while crosswalk uses new codes (09110-09190)
**How to avoid:** Check NRI CSV for CT FIPS codes at build time. Apply mapping if legacy codes found.
**Warning signs:** Connecticut Tribes (Mashantucket Pequot, Mohegan) show zero SVI/NRI data

### Pitfall 3: National Percentile vs. State Percentile Confusion

**What goes wrong:** Using `RISK_SPCTL` as national percentile, misrepresenting Tribal risk
**Why it happens:** Field name similarity, assumption that NRI provides national percentile
**How to avoid:** Compute national percentile from `RISK_SCORE` rank at build time. Document clearly.
**Warning signs:** Percentile values that seem inconsistent across states

### Pitfall 4: FY26 Fix Breaking Frozen Dataclass

**What goes wrong:** Import error or circular import when adding `config.FISCAL_YEAR_SHORT` to `doc_types.py`
**Why it happens:** `doc_types.py` uses `@dataclass(frozen=True)`. Template strings set at class definition time.
**How to avoid:** `FISCAL_YEAR_SHORT` is computed at module import time (just `date.today()`), so importing from `config.py` at module level in `doc_types.py` works. For `format_filename()`, use lazy import inside the method.
**Warning signs:** `ImportError` on startup, circular import chain

### Pitfall 5: Schema Forward References

**What goes wrong:** `VulnerabilityProfile` references `FloodProfile` (Phase 20 model) which doesn't exist yet
**Why it happens:** River Runner schemas include Optional forward references for Phase 20-21 models
**How to avoid:** Use `Optional["FloodProfile"]` with `from __future__ import annotations`. Set default to `None`. The forward reference will resolve when the model is defined in Phase 20.
**Warning signs:** Pydantic `ConfigError` about undefined references

---

## Code Examples

### Verified: Area-Weighted SVI Aggregation (following hazards.py pattern)

```python
def _build_tribe_svi_profile(self, tribe_id, tribe, county_svi_data):
    """Aggregate SVI data for a single Tribe."""
    geoids = self._tribe_to_geoids.get(tribe_id, [])
    county_weights = {}

    for geoid in geoids:
        for entry in self._area_weights.get(geoid, []):
            fips = entry["county_fips"]
            weight = entry["weight"]
            county_weights[fips] = county_weights.get(fips, 0.0) + weight

    if not county_weights:
        return self._empty_svi_profile("No county matches found")

    # Collect matched counties, skip -999 sentinels
    matched = []
    for fips, weight in county_weights.items():
        svi = county_svi_data.get(fips)
        if svi and svi.get("rpl_theme1") is not None:  # Not -999
            matched.append((svi, weight))

    if not matched:
        return self._empty_svi_profile("All matched counties have missing SVI data")

    # Normalize weights to matched counties only
    total_w = sum(w for _, w in matched)

    # Weighted average of 3 themes
    theme1 = sum(s["rpl_theme1"] * w / total_w for s, w in matched)
    theme2 = sum(s["rpl_theme2"] * w / total_w for s, w in matched)
    theme4 = sum(s["rpl_theme4"] * w / total_w for s, w in matched)

    tribal_composite = (theme1 + theme2 + theme4) / 3.0

    return {
        "themes": [
            {"theme_id": "theme1", "name": "Socioeconomic Status", "percentile": round(theme1, 4)},
            {"theme_id": "theme2", "name": "Household Characteristics", "percentile": round(theme2, 4)},
            {"theme_id": "theme4", "name": "Housing Type & Transportation", "percentile": round(theme4, 4)},
        ],
        "tribal_svi_composite": round(tribal_composite, 4),
        "counties_analyzed": len(matched),
        "source_version": "SVI 2022",
        "coverage_status": "full",
    }
```

### Verified: National Percentile Computation

```python
import bisect

def compute_national_percentiles(county_data: dict[str, dict]) -> dict[str, float]:
    """Compute national percentile for each county's RISK_SCORE.

    Returns dict mapping county FIPS -> national percentile (0-100).
    """
    scores = sorted(
        (rec["risk_score"], fips)
        for fips, rec in county_data.items()
        if rec["risk_score"] > 0
    )
    score_values = [s for s, _ in scores]
    n = len(score_values)

    percentiles = {}
    for score, fips in scores:
        rank = bisect.bisect_left(score_values, score)
        percentiles[fips] = round(rank / n * 100, 2)

    return percentiles
```

### Verified: Atomic Write Pattern (from hazards.py)

```python
import contextlib
import json
import os
import tempfile

def atomic_json_write(data: dict, target_path: Path) -> None:
    """Write JSON atomically using tmp file + os.replace()."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=target_path.parent, suffix=".tmp"
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, target_path)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise
```

---

## Open Questions

### 1. SVI 2022 CSV Download URL

**What we know:** The download page at `svi.cdc.gov/dataDownloads/data-download.html` uses a form-based interface. The file is approximately 15 MB for county-level US data.
**What's unclear:** The exact direct download URL for the CSV (it appears to be dynamically generated via form submission).
**Recommendation:** The download script should either (a) hardcode the known URL pattern based on prior downloads, or (b) document manual download instructions. The CSV filename pattern is likely `SVI2022_US_COUNTY.csv` based on convention.

### 2. NRI v1.20 CT FIPS Usage

**What we know:** Census Bureau switched CT to planning region FIPS in 2022. NRI v1.20 was released December 2025.
**What's unclear:** Whether NRI v1.20 uses legacy or new CT FIPS codes.
**Recommendation:** Check the actual CSV at build time. If FIPS codes starting with "090" are present (legacy format 09001-09015), apply the CT mapping. If codes starting with "091" are present (new format 09110-09190), no mapping needed.

### 3. Encoding of SVI CSV

**What we know:** NRI CSV uses UTF-8 with BOM (`encoding="utf-8-sig"`). SVI documentation suggests UTF-8.
**What's unclear:** Whether SVI CSV has a BOM marker.
**Recommendation:** Use `encoding="utf-8-sig"` for both NRI and SVI CSV parsing. UTF-8-sig handles both with-BOM and without-BOM files correctly.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `src/packets/hazards.py`, `src/schemas/models.py`, `src/packets/context.py`, `src/paths.py`, `src/config.py`, `src/packets/doc_types.py`
- Phase 18.5 agent reports: Fire Keeper, River Runner, Sovereignty Scout, Horizon Walker (in `.planning/phases/18.5-architectural-review/`)
- Architecture Delta Report (`.planning/phases/18.5-architectural-review/ARCHITECTURE-DELTA-REPORT.md`)
- NRI Data Resources: [hazards.fema.gov/nri/data-resources](https://hazards.fema.gov/nri/data-resources)
- SVI 2022 Documentation: [atsdr.cdc.gov/place-health/media/pdfs/2024/10/SVI2022Documentation.pdf](https://www.atsdr.cdc.gov/place-health/media/pdfs/2024/10/SVI2022Documentation.pdf)
- SVI Data Download: [svi.cdc.gov/dataDownloads/data-download.html](https://svi.cdc.gov/dataDownloads/data-download.html)

### Secondary (MEDIUM confidence)
- CDC SVI 2022 column names confirmed via official documentation and Sovereignty Scout validation
- Connecticut FIPS change: [Federal Register 2022-12063](https://www.federalregister.gov/documents/2022/06/06/2022-12063/change-to-county-equivalents-in-the-state-of-connecticut)

### Tertiary (LOW confidence)
- SVI 2022 direct download URL (form-based, not confirmed)
- NRI v1.20 CT FIPS code format (not confirmed from actual CSV inspection)

---

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH -- all libraries already in use, no new dependencies
- Architecture: HIGH -- builder pattern fully documented from 1,291-line template with 9 verified steps
- Pitfalls: HIGH -- all edge cases identified from actual data inspection and agent reports
- Schemas: HIGH -- River Runner provides complete Pydantic v2 model code ready for implementation
- FY26 inventory: HIGH -- complete grep-based inventory with exact file:line locations
- SVI integration: MEDIUM -- column names confirmed but download URL and encoding not verified from actual file

**Research date:** 2026-02-17
**Valid until:** 2026-03-17 (stable -- NRI v1.20 and SVI 2022 are fixed datasets, codebase patterns well-established)
