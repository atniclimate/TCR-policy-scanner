# Phase 19: Schema & Core Data Foundation - Research

**Researched:** 2026-02-17
**Domain:** Pydantic v2 schemas, FEMA NRI expansion, CDC SVI integration, sovereignty-first vocabulary
**Confidence:** HIGH (codebase patterns verified against source, data source fields confirmed by 18.5 agents)

## Summary

Phase 19 establishes the data contracts (Pydantic schemas), vulnerability data inputs (NRI expansion + SVI 2022), and sovereignty-first framing vocabulary that all subsequent phases (20-24) build against. Research confirms that every technical component has a verified codebase template to follow: `HazardProfileBuilder` provides the 9-step builder pattern, `src/schemas/models.py` provides the Pydantic v2 validation conventions, and `tribal_county_area_weights.json` provides the reusable area-weighted crosswalk.

Key findings: (1) NRI v1.20 field names `EAL_VALB`, `EAL_VALP`, `EAL_VALA`, `EAL_VALPE`, `RISK_SCORE`, `RESL_SCORE`, `SOVI_SCORE` are confirmed; `RISK_NPCTL` does NOT exist and must be computed at build time. (2) SVI 2022 is confirmed current, available as county CSV from CDC, with `RPL_THEME1`/`RPL_THEME2`/`RPL_THEME4` as the target columns and `-999` as the missing data sentinel. (3) Connecticut's 2022 FIPS change (8 legacy counties to 9 planning regions, codes 09110-09190) affects both NRI and SVI data and requires a FIPS remapping table. (4) No new libraries are needed -- the existing stack (pydantic, csv, json, pathlib, hashlib) covers all Phase 19 requirements.

**Primary recommendation:** Follow the existing `HazardProfileBuilder` pattern step-for-step. Do not invent new patterns. The crosswalk, `_safe_float()`, atomic writes, and path traversal guards are non-negotiable reuse points.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | `>=2.0.0` (2.13.3 current) | Schema validation models | Already in codebase; 19 existing models in `src/schemas/models.py` |
| csv (stdlib) | Python 3.12+ | NRI CSV parsing | Existing pattern in `hazards.py` via `csv.DictReader` |
| json (stdlib) | Python 3.12+ | Cache file read/write | Existing atomic write pattern in `hazards.py` |
| hashlib (stdlib) | Python 3.12+ | SHA256 checksum for NRI version pinning | New for XCUT-03 but stdlib, zero dependencies |
| pathlib (stdlib) | Python 3.12+ | Path constants and traversal guards | Existing pattern in `src/paths.py` |
| math (stdlib) | Python 3.12+ | NaN/Inf detection in `_safe_float()` | Existing pattern in `hazards.py:80` |
| tempfile (stdlib) | Python 3.12+ | Atomic writes via `mkstemp()` | Existing pattern in `hazards.py:1120` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| contextlib (stdlib) | Python 3.12+ | `suppress(OSError)` in cleanup | Atomic write exception handler |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `csv.DictReader` | pandas | Pandas adds 100MB dependency for a 3,200-row CSV. DictReader is sufficient and matches existing pattern. |
| `hashlib.sha256()` | External checksum tool | Stdlib is simpler, cross-platform, and avoids dependency. |
| Custom rank percentile | `scipy.stats.percentileofscore` | scipy is not in requirements. Simple rank-based formula `(rank - 1) / (N - 1) * 100` is sufficient for ~3,200 counties. |

**Installation:** No new packages required. All Phase 19 dependencies are Python stdlib or already in `requirements.txt`.

## Architecture Patterns

### Recommended Project Structure
```
src/
├── schemas/
│   ├── __init__.py          # Updated: re-export vulnerability models
│   ├── models.py            # Existing (1,261 lines, UNCHANGED)
│   └── vulnerability.py     # NEW: ~300 lines, core vulnerability models
├── packets/
│   ├── vulnerability.py     # NEW: VulnerabilityProfileBuilder
│   └── vocabulary.py        # NEW: Sovereignty-first framing constants (REG-04)
├── paths.py                 # MODIFIED: +6 constants, +1 helper
├── config.py                # EXISTING (read for FISCAL_YEAR_SHORT)
└── packets/
    ├── context.py            # MODIFIED: +vulnerability_profile field
    ├── doc_types.py          # MODIFIED: fix FY26 debt, add include_vulnerability
    ├── docx_engine.py        # MODIFIED: fix FY26 debt
    └── docx_template.py      # MODIFIED: fix FY26 debt
```

### Pattern 1: VulnerabilityProfileBuilder (Follow HazardProfileBuilder)
**What:** Builder class for per-Tribe vulnerability profiles, following the 9-step template from `hazards.py`.
**When to use:** Always. This is the only acceptable builder pattern for v1.4.
**Source:** `src/packets/hazards.py` (48,882 bytes, lines 80-1283)

The 9 steps are:
1. `__init__(config: dict)` -- Accept config, resolve paths, load crosswalk + area weights
2. `_load_crosswalk()` -- Read `aiannh_tribe_crosswalk.json`, build reverse mapping
3. `_load_area_weights()` -- Read `tribal_county_area_weights.json`, return GEOID -> [{county_fips, weight}]
4. CSV data loading -- Read NRI/SVI CSVs with `encoding="utf-8-sig"`, use `csv.DictReader`, apply `_safe_float()` to ALL numerics
5. Per-Tribe aggregation -- Area-weighted crosswalk with weight normalization (see Pattern 3 below)
6. Override integration -- USFS wildfire pattern (for v1.4: no overrides needed, but pattern exists)
7. Atomic JSON write -- `tempfile.mkstemp()` + `os.fdopen()` + `os.replace()` with cleanup
8. Path traversal guard -- `Path(tribe_id).name` + reject `..`
9. Coverage report -- JSON + Markdown summary with per-state breakdown

### Pattern 2: Pydantic v2 Schema Conventions (Follow `src/schemas/models.py`)
**What:** Validation model conventions established in the existing 19 models.
**When to use:** All new models in `src/schemas/vulnerability.py`.
**Source:** `src/schemas/models.py` (1,261 lines)

Key conventions extracted from the codebase:

```python
# Import pattern (MANDATORY)
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator

# Validation constants as frozenset
SVI_INCLUDED_THEMES = frozenset({"theme1", "theme2", "theme4"})

# Field pattern with defaults, constraints, descriptions
risk_score: float = Field(default=0.0, ge=0.0, description="...")
tribe_id: str = Field(..., description="...", examples=["epa_100000001"])
awards: list[FundingRecord] = Field(default_factory=list, description="...")

# field_validator with mode="before" for sanitization
@field_validator("percentile", mode="before")
@classmethod
def sanitize_percentile(cls, v: float | None) -> float:
    return _validate_unit_float(v, "percentile")

# model_validator with mode="after" for cross-field checks
@model_validator(mode="after")
def validate_theme_count(self) -> "SVIProfile":
    if len(self.themes) > 3:
        raise ValueError(...)
    return self

# tribe_id validation (reused in 5+ models)
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

**Critical rule:** Use `mode="before"` for sanitization validators that handle None/NaN/Inf. Use `mode="after"` for cross-field consistency checks that need typed values.

### Pattern 3: Area-Weighted Crosswalk Aggregation
**What:** How to aggregate county-level data to per-Tribe using the existing crosswalk.
**When to use:** SVI theme aggregation (identical to NRI aggregation in `hazards.py`).
**Source:** `src/packets/hazards.py` lines 570-644

```python
# Step 1: Collect county weights from crosswalk
county_weights = {}
for geoid in geoids:
    entries = self._area_weights.get(geoid, [])
    for entry in entries:
        fips = entry["county_fips"]
        weight = entry["weight"]
        # If same county appears via multiple GEOIDs, SUM the weights
        county_weights[fips] = county_weights.get(fips, 0.0) + weight

# Step 2: Normalize to matched counties only
total_w = sum(county_weights.get(c["fips"], 0.0) for c in matched_counties)
if total_w == 0:
    total_w = len(matched_counties)  # Equal weight fallback
    norm_weights = {c["fips"]: 1.0 / total_w for c in matched_counties}
else:
    norm_weights = {
        c["fips"]: county_weights.get(c["fips"], 0.0) / total_w
        for c in matched_counties
    }

# Step 3: Weighted average (for percentile-type scores like SVI RPL_*)
svi_theme1 = sum(
    c["rpl_theme1"] * norm_weights[c["fips"]]
    for c in matched_counties
)
```

**Critical rules:**
- Weights are SUMMED when same county appears via multiple GEOIDs
- Weights are normalized to MATCHED counties only (not all counties in crosswalk)
- Zero `total_w` falls back to equal weight `1/N` (prevents division by zero)
- Ratings are RE-DERIVED from weighted scores, never averaged from source strings

### Pattern 4: Atomic JSON Write
**What:** Crash-safe file write pattern used for all JSON cache files.
**When to use:** Every cache file write in the builder.
**Source:** `src/packets/hazards.py` lines 1110-1130

```python
import contextlib
import os
import tempfile

cache_file = self.cache_dir / f"{tribe_id}.json"
tmp_fd, tmp_path = tempfile.mkstemp(
    dir=self.cache_dir, suffix=".tmp", prefix=f"{tribe_id}_"
)
try:
    with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, cache_file)
except Exception:
    with contextlib.suppress(OSError):
        os.unlink(tmp_path)
    raise
```

**Critical rules:**
- Use `tempfile.mkstemp()` (NOT `NamedTemporaryFile`) for cross-platform safety
- Use `os.fdopen()` to wrap file descriptor with `encoding="utf-8"`
- Use `os.replace()` for atomic rename (works cross-platform)
- Clean up temp file in except block with `contextlib.suppress(OSError)`
- `json.dump()` with `indent=2, ensure_ascii=False`

### Pattern 5: `_safe_float()` NaN/Inf Firewall
**What:** Universal numeric converter that handles None, empty strings, NaN, Inf.
**When to use:** ALL numeric values parsed from CSV files (NRI and SVI).
**Source:** `src/packets/hazards.py` lines 80-106

```python
def _safe_float(value, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return default
        return result
    s = str(value).strip()
    if not s:
        return default
    try:
        result = float(s)
        if math.isnan(result) or math.isinf(result):
            return default
        return result
    except (ValueError, TypeError):
        return default
```

**For SVI data:** Also check for `-999` sentinel: `if result == -999: return default`.

### Pattern 6: Vocabulary Constants Module
**What:** Frozen dataclass + dict constants for sovereignty-first framing.
**When to use:** REG-04 implementation. Renderers import these constants at construction time.
**Source:** Horizon Walker report vocabulary specification

```python
# src/packets/vocabulary.py
from dataclasses import dataclass

@dataclass(frozen=True)
class SectionHeadings:
    doc_a_main: str = "Climate Resilience Investment Profile"
    doc_b_main: str = "Climate Resilience Data Summary"
    # ...

SECTION_HEADINGS = SectionHeadings()
RATING_LABEL = "Resilience Investment Priority"

# Context-sensitive: "vulnerability" only inside proper nouns
CONTEXT_SENSITIVE_TERMS: dict[str, list[str]] = {
    "vulnerable": ["Social Vulnerability Index", "CDC/ATSDR Social Vulnerability"],
    "vulnerability": ["Social Vulnerability Index", "National Risk Index"],
}

# Forbidden in Doc B/D (extends existing air gap)
FORBIDDEN_DOC_B_TERMS: frozenset[str] = frozenset({
    "strategic", "strategy", "leverage", ...
})

CAVEAT_TEMPLATES: dict[str, str] = {
    "composite_full": "...",
    "source_compact": "...",
    "partial_data": "...",
    "theme3_exclusion": "...",
    "methodology": "...",
    "alaska_gap": "...",
}
```

**Critical rule:** This is NOT a post-processing text filter. Renderers import constants and use them during section construction. Enforcement is at render time, validated by air gap tests.

### Anti-Patterns to Avoid
- **Do NOT use `RPL_THEMES` directly.** It includes Theme 3. Compute custom 3-theme composite: `average(RPL_THEME1, RPL_THEME2, RPL_THEME4)`.
- **Do NOT reference `RISK_NPCTL`.** It does not exist in NRI v1.20. Compute national percentile from `RISK_SCORE` rank at build time.
- **Do NOT average rating strings.** Two "Very High" counties with scores 85 and 65 average to 75, which maps to "Relatively High". Always re-derive from weighted scores.
- **Do NOT use `NamedTemporaryFile` on Windows.** It cannot be read by another process while open. Use `tempfile.mkstemp()`.
- **Do NOT hardcode "FY26".** Import `FISCAL_YEAR_SHORT` from `src.config`.
- **Do NOT use `open()` without `encoding`.** Always pass `encoding="utf-8"` (or `"utf-8-sig"` for CSVs with BOM).
- **Do NOT put all vulnerability models in `models.py`.** That file is already 1,261 lines. Create `src/schemas/vulnerability.py`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Crosswalk loading | Custom GEOID->county mapper | `hazards.py._load_crosswalk()` + `_load_area_weights()` | Identical data structures, tested edge cases |
| Numeric sanitization | Custom float parser | `hazards.py._safe_float()` (import or replicate) | Handles None, "", NaN, Inf, -Inf, type coercion |
| Weight normalization | Custom weight math | Existing pattern from `hazards.py` lines 616-624 | Zero-weight fallback, multi-GEOID summing |
| Atomic writes | Custom file writer | `tempfile.mkstemp()` + `os.replace()` pattern | Windows-safe, crash-safe, proven in 7 files |
| Path traversal guard | Custom sanitizer | `Path(tribe_id).name` + reject `..` | Existing pattern in `hazards.py` |
| NRI version detection | Custom parser | `hazards.py._detect_nri_version()` | Regex-based, handles multiple naming conventions |
| Rating derivation | Average of rating strings | `score_to_rating()` from weighted scores | Prevents the "two Very Highs average to High" error |
| SHA256 checksums | External tool | `hashlib.sha256()` with file chunks | Stdlib, handles large files (>100MB NRI ZIP) |
| National percentile | scipy dependency | `(rank - 1) / (N - 1) * 100` formula | Simple, exact for rank-based percentile over ~3,200 counties |
| FIPS zero-padding | String slicing | `fips.zfill(5)` | Existing pattern in `hazards.py:389` |

**Key insight:** Phase 19 should produce ZERO novel infrastructure. Every component either exists in the codebase or is a straightforward extension of an existing pattern.

## Common Pitfalls

### Pitfall 1: SVI `-999` Sentinel Values
**What goes wrong:** `-999` appears as a valid float in SVI CSV, passes NaN/Inf checks, and contaminates weighted averages (e.g., theme average becomes negative).
**Why it happens:** `_safe_float()` in `hazards.py` does not check for `-999` because NRI uses empty strings for missing data, not sentinels.
**How to avoid:** Add sentinel check to the SVI-specific float parser: `if result == -999: return default`. SVI 2022 documentation confirms `-999` means null/no data.
**Warning signs:** Negative SVI theme scores in output profiles. Any `RPL_THEME*` value outside [0.0, 1.0].

### Pitfall 2: Connecticut FIPS Remapping
**What goes wrong:** NRI v1.20 (December 2025) may use the new Connecticut planning region FIPS codes (09110-09190), but SVI 2022 (May 2024) uses the old county FIPS codes (09001-09015). Crosswalk join fails silently for Connecticut counties, producing zero-coverage profiles for CT Tribes.
**Why it happens:** Census Bureau changed Connecticut county-equivalent geography in 2022. Different data products adopted the change at different times.
**How to avoid:** Build a bidirectional FIPS remapping table for Connecticut. At CSV load time, normalize all CT FIPS to one canonical form. Check which form NRI v1.20 actually uses (inspect CSV headers at build time). If old codes: remap to new. If new codes: remap to old for SVI join.
**Warning signs:** Zero SVI data for any Connecticut Tribe. County count mismatch between NRI and SVI for CT.

Connecticut planning region FIPS codes (9 regions):
| FIPS | Planning Region |
|------|----------------|
| 09110 | Capitol |
| 09120 | Greater Bridgeport |
| 09130 | Lower Connecticut River Valley |
| 09140 | Naugatuck Valley |
| 09150 | Northeastern Connecticut |
| 09160 | Northwest Hills |
| 09170 | South Central Connecticut |
| 09180 | Southeastern Connecticut |
| 09190 | Western Connecticut |

Legacy county FIPS codes (8 counties, many-to-many mapping):
| County FIPS | County | Maps to Region(s) |
|-------------|--------|-------------------|
| 09001 | Fairfield | Greater Bridgeport (09120), Western Connecticut (09190) |
| 09003 | Hartford | Capitol (09110), Naugatuck Valley (09140), Northwest Hills (09160) |
| 09005 | Litchfield | Northwest Hills (09160), Naugatuck Valley (09140), Western Connecticut (09190) |
| 09007 | Middlesex | Lower CT River Valley (09130), Capitol (09110) |
| 09009 | New Haven | Naugatuck Valley (09140), South Central CT (09170) |
| 09011 | New London | Southeastern CT (09180), Lower CT River Valley (09130) |
| 09013 | Tolland | Capitol (09110) |
| 09015 | Windham | Northeastern CT (09150), Capitol (09110) |

**Note:** This is a many-to-many mapping. A single legacy county may split across multiple planning regions. The NRI may have adopted new codes while SVI has not. Must inspect actual data at build time.

### Pitfall 3: NRI CSV BOM Encoding
**What goes wrong:** FEMA CSV downloads include a UTF-8 BOM (Byte Order Mark). `open(encoding="utf-8")` reads the BOM as invisible characters prepended to the first column header, causing `DictReader` key lookup failures.
**Why it happens:** Windows Excel exports add BOM by default. FEMA CSVs are likely generated on Windows.
**How to avoid:** Use `encoding="utf-8-sig"` for NRI CSV files (existing pattern in `hazards.py:351`). For SVI CSV, test both `utf-8-sig` and `utf-8` -- CDC may or may not include BOM.
**Warning signs:** First column key has invisible prefix characters. `row.get("STCOFIPS")` returns `None` when the data visually appears correct.

### Pitfall 4: Weight Normalization Over Matched Counties Only
**What goes wrong:** Normalizing weights over ALL counties in the crosswalk (including those not in the NRI/SVI data) produces weights that don't sum to 1.0, deflating scores.
**Why it happens:** Some counties in the crosswalk may not exist in the data (e.g., small/new counties, or CT remapping mismatch).
**How to avoid:** Normalize weights to MATCHED counties only. The existing `hazards.py` pattern (line 616) does this correctly. Copy it exactly.
**Warning signs:** Total normalized weight < 0.95 for a Tribe. Scores systematically lower than expected.

### Pitfall 5: National Percentile Must Be Computed Before Area Weighting
**What goes wrong:** Computing national percentile from the area-weighted composite score produces incorrect rankings because the composite is a blend of multiple county scores, not a single county position.
**Why it happens:** Percentile is a rank-order concept. The weighted average of two county scores does not correspond to a meaningful rank in the national distribution.
**How to avoid:** Compute national percentile FOR EACH COUNTY from its raw `RISK_SCORE` rank across all ~3,200 counties. Then area-weight the PERCENTILES (just like other scores). Store both the area-weighted percentile and the area-weighted raw score.
**Warning signs:** National percentiles outside [0, 100]. Percentile distribution heavily clustered near 50 (which happens when averaging percentiles across many counties).

### Pitfall 6: Pydantic v2 `model_validator` Return Type
**What goes wrong:** `model_validator(mode="after")` must return `self` (or an instance of the model). Forgetting `return self` causes `None` to be returned, which Pydantic interprets as model deletion.
**Why it happens:** Unlike `field_validator` which returns a value, `model_validator(mode="after")` is an instance method that must return the instance.
**How to avoid:** Every `model_validator(mode="after")` method must end with `return self`. Use `-> "ClassName"` or `-> Self` (from `typing_extensions`) as the return type hint.
**Warning signs:** `ValidationError` with cryptic message about `None`. Model fields suddenly all `None` after validation.

### Pitfall 7: `data_completeness_factor` With Missing Components
**What goes wrong:** When SVI data is missing for a Tribe, the composite formula uses only 2 of 3 components but doesn't adjust weights, producing a score that understates the actual vulnerability.
**Why it happens:** The formula `0.40 * hazard + 0.35 * svi + 0.25 * adaptive` produces a lower score when `svi = 0.0` (missing) vs. when it has its actual value.
**How to avoid:** Redistribute weights proportionally across available components. With SVI missing: `0.40/(0.40+0.25) * hazard + 0.25/(0.40+0.25) * adaptive` = `0.615 * hazard + 0.385 * adaptive`. Set `data_completeness_factor` = `(0.40 + 0.25) / 1.0` = `0.65`.
**Warning signs:** Tribes with missing SVI consistently scoring lower than Tribes with similar hazard profiles but available SVI.

## Code Examples

### National Percentile Computation from RISK_SCORE
```python
# Source: Architecture Delta Report, 18.5-DEC-01
def compute_national_percentiles(county_data: dict[str, dict]) -> dict[str, float]:
    """Compute national percentile for each county from RISK_SCORE rank.

    Args:
        county_data: Dict keyed by FIPS -> {risk_score: float, ...}

    Returns:
        Dict keyed by FIPS -> national percentile (0-100).
    """
    scored = [
        (fips, d["risk_score"])
        for fips, d in county_data.items()
        if d["risk_score"] > 0
    ]
    # Sort ascending (lowest risk = lowest percentile)
    scored.sort(key=lambda x: x[1])
    n = len(scored)
    percentiles = {}
    for rank_0, (fips, _score) in enumerate(scored):
        if n > 1:
            percentiles[fips] = round(rank_0 / (n - 1) * 100, 2)
        else:
            percentiles[fips] = 50.0  # Single county edge case
    # Counties with zero risk_score get 0th percentile
    for fips, d in county_data.items():
        if fips not in percentiles:
            percentiles[fips] = 0.0
    return percentiles
```

### SVI CSV Parsing with Sentinel Check
```python
# Source: Sovereignty Scout report + existing hazards.py pattern
def _safe_svi_float(value, default: float = 0.0) -> float:
    """Convert SVI CSV value to float, handling -999 sentinel.

    SVI uses -999 to represent null/no data. NRI uses empty strings.
    This function handles both conventions.
    """
    result = _safe_float(value, default=default)
    if result == -999 or result == -999.0:
        return default
    return result

def load_svi_county_data(csv_path: Path) -> dict[str, dict]:
    """Parse SVI 2022 county CSV.

    Returns dict keyed by FIPS (5-digit, zero-padded) -> {
        rpl_theme1: float,  # Socioeconomic Status (0-1)
        rpl_theme2: float,  # Household Characteristics (0-1)
        rpl_theme4: float,  # Housing Type & Transportation (0-1)
        rpl_themes: float,  # Overall (includes Theme 3, stored for reference)
        e_totpop: int,      # Total population
        f_theme1: int,      # Flag count Theme 1
        f_theme2: int,      # Flag count Theme 2
        f_theme4: int,      # Flag count Theme 4
    }
    """
    county_data = {}
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fips = (row.get("STCNTY") or row.get("FIPS") or "").strip()
            if not fips or len(fips) < 5:
                continue
            fips = fips.zfill(5)
            county_data[fips] = {
                "rpl_theme1": _safe_svi_float(row.get("RPL_THEME1")),
                "rpl_theme2": _safe_svi_float(row.get("RPL_THEME2")),
                "rpl_theme4": _safe_svi_float(row.get("RPL_THEME4")),
                "rpl_themes": _safe_svi_float(row.get("RPL_THEMES")),
                "e_totpop": int(_safe_svi_float(row.get("E_TOTPOP"))),
                "f_theme1": int(_safe_svi_float(row.get("F_THEME1"))),
                "f_theme2": int(_safe_svi_float(row.get("F_THEME2"))),
                "f_theme4": int(_safe_svi_float(row.get("F_THEME4"))),
            }
    return county_data
```

### SHA256 Checksum for NRI Version Pinning
```python
# Source: XCUT-03 requirement, stdlib hashlib
import hashlib

def compute_sha256(file_path: Path, chunk_size: int = 65536) -> str:
    """Compute SHA256 hex digest of a file.

    Reads in chunks to handle large files (NRI ZIP is ~200MB).
    """
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            sha.update(chunk)
    return sha.hexdigest()

def validate_nri_checksum(
    csv_path: Path,
    expected_sha: str | None = None,
) -> dict:
    """Validate NRI CSV integrity and return version metadata.

    Returns:
        Dict with keys: version, sha256, row_count, column_count, validated.
    """
    actual_sha = compute_sha256(csv_path)
    # Count rows and validate headers
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        row_count = sum(1 for _ in reader)

    required_headers = {
        "STCOFIPS", "RISK_SCORE", "RISK_RATNG", "EAL_VALT",
        "EAL_VALB", "EAL_VALP", "EAL_VALA", "EAL_VALPE",
        "SOVI_SCORE", "RESL_SCORE", "POPULATION", "BUILDVALUE",
    }
    missing = required_headers - set(headers)

    return {
        "version": _detect_nri_version(csv_path),
        "sha256": actual_sha,
        "row_count": row_count,
        "column_count": len(headers),
        "validated": actual_sha == expected_sha if expected_sha else None,
        "missing_headers": sorted(missing),
        "has_required_headers": len(missing) == 0,
    }
```

### Composite Vulnerability Score with Weight Redistribution
```python
# Source: Architecture Delta Report, 18.5-DEC-04
# v1.4 formula: 0.40 hazard + 0.35 social + 0.25 adaptive capacity deficit

V14_WEIGHTS = {
    "hazard_exposure": 0.40,
    "social_vulnerability": 0.35,
    "adaptive_capacity_deficit": 0.25,
}

def compute_composite(
    hazard_pctl: float | None,  # National percentile / 100 (0-1)
    svi_composite: float | None,  # Custom 3-theme SVI (0-1)
    resl_score: float | None,  # NRI RESL_SCORE (0-100)
) -> tuple[float, float, list[dict]]:
    """Compute composite vulnerability score with weight redistribution.

    Returns:
        (score, data_completeness_factor, component_details)
    """
    components = []

    # Hazard exposure: national percentile / 100
    if hazard_pctl is not None and hazard_pctl > 0:
        components.append({
            "component": "hazard_exposure",
            "raw_score": min(1.0, hazard_pctl),
            "base_weight": V14_WEIGHTS["hazard_exposure"],
            "available": True,
        })

    # Social vulnerability: custom Tribal SVI
    if svi_composite is not None and svi_composite > 0:
        components.append({
            "component": "social_vulnerability",
            "raw_score": min(1.0, svi_composite),
            "base_weight": V14_WEIGHTS["social_vulnerability"],
            "available": True,
        })

    # Adaptive capacity deficit: 1 - (RESL_SCORE / 100)
    if resl_score is not None and resl_score >= 0:
        deficit = 1.0 - min(1.0, resl_score / 100.0)
        components.append({
            "component": "adaptive_capacity_deficit",
            "raw_score": max(0.0, deficit),
            "base_weight": V14_WEIGHTS["adaptive_capacity_deficit"],
            "available": True,
        })

    if not components:
        return 0.0, 0.0, []

    # Redistribute weights proportionally across available components
    total_base = sum(c["base_weight"] for c in components)
    for c in components:
        c["weight"] = c["base_weight"] / total_base
        c["weighted_score"] = round(c["raw_score"] * c["weight"], 6)

    score = sum(c["weighted_score"] for c in components)
    score = max(0.0, min(1.0, score))
    completeness = total_base  # Fraction of total weight covered

    return round(score, 4), round(completeness, 4), components
```

### Connecticut FIPS Remapping Table
```python
# Source: Federal Register 2022-12063, Census Bureau
# Many-to-many: one legacy county may map to multiple planning regions
CT_LEGACY_TO_PLANNING: dict[str, list[str]] = {
    "09001": ["09120", "09190"],  # Fairfield -> Greater Bridgeport, Western CT
    "09003": ["09110", "09140", "09160"],  # Hartford -> Capitol, Naugatuck, NW Hills
    "09005": ["09160", "09140", "09190"],  # Litchfield -> NW Hills, Naugatuck, Western
    "09007": ["09130", "09110"],  # Middlesex -> Lower CT River, Capitol
    "09009": ["09140", "09170"],  # New Haven -> Naugatuck, South Central
    "09011": ["09180", "09130"],  # New London -> Southeastern, Lower CT River
    "09013": ["09110"],           # Tolland -> Capitol
    "09015": ["09150", "09110"],  # Windham -> Northeastern, Capitol
}

CT_PLANNING_TO_LEGACY: dict[str, list[str]] = {
    "09110": ["09003", "09007", "09013", "09015"],
    "09120": ["09001"],
    "09130": ["09007", "09011"],
    "09140": ["09003", "09005", "09009"],
    "09150": ["09015"],
    "09160": ["09003", "09005"],
    "09170": ["09009"],
    "09180": ["09011"],
    "09190": ["09001", "09005"],
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pydantic v1 `validator` | Pydantic v2 `field_validator` / `model_validator` | v2.0 (2023) | Already using v2 in codebase |
| `RISK_NPCTL` from NRI CSV | Compute national percentile from `RISK_SCORE` rank | NRI v1.20 (Dec 2025) | `RISK_NPCTL` never existed; only `RISK_SPCTL` (state percentile) |
| `RPL_THEMES` for overall SVI | Custom 3-theme composite (Themes 1+2+4) | Architecture decision | Theme 3 tautological for Tribal Nations |
| 4-component composite score | 3-component (LOCA2 deferred to v1.5+) | Phase 18.5 decision | Climate projection component zeroed in v1.4 |
| CT 8 counties (09001-09015) | CT 9 planning regions (09110-09190) | Census Bureau June 2022 | Must handle both in NRI/SVI data |
| `svi.cdc.gov` download page | `atsdr.cdc.gov/place-health/php/svi/` redirect | 2024 site reorganization | Old URLs redirect; use new ATSDR path |
| `hazards.fema.gov/nri/` docs | RAPT platform redirect | Late 2025 | All NRI documentation URLs redirect |

**Deprecated/outdated:**
- `hazards.fema.gov/nri/data-glossary` -- now 301 redirects to RAPT
- `hazards.fema.gov/nri/data-resources` -- redirects, use `fema.gov/about/openfema/data-sets/national-risk-index-data`
- `svi.cdc.gov` direct domain -- redirects to `atsdr.cdc.gov/place-health/php/svi/`

## Open Questions

1. **SVI 2022 County CSV Exact Download URL**
   - What we know: Available at `atsdr.cdc.gov/place-health/php/svi/svi-data-documentation-download.html`, select 2022 + County + CSV + United States. File is approximately 15 MB with ~3,200 rows.
   - What's unclear: The exact direct download URL (dynamically generated by the download page). Filename convention is likely `SVI2022_US_COUNTY.csv` based on prior SVI releases.
   - Recommendation: Build a download script (`scripts/download_svi_data.py`) that either uses the known URL pattern or documents the manual download step. Store at `data/svi/SVI2022_US_COUNTY.csv` per the path constants.
   - Confidence: MEDIUM -- file format and columns confirmed, exact URL needs runtime verification.

2. **NRI v1.20 Connecticut FIPS Format**
   - What we know: NRI v1.20 released December 2025. Census adopted planning regions in 2022. It is likely but not certain that NRI v1.20 uses the new FIPS codes.
   - What's unclear: Whether the `STCOFIPS` column in `NRI_Table_Counties.csv` uses 09001 (legacy) or 09110 (planning region) format for Connecticut.
   - Recommendation: Inspect the actual CSV at build time. Include both-direction lookup table. Log a warning if CT codes don't match expected format.
   - Confidence: MEDIUM -- the mapping table is confirmed, but which codes NRI uses requires runtime inspection.

3. **SVI 2022 County FIPS Column Name**
   - What we know: SVI documentation references `FIPS` (for tract-level) and `STCNTY` (for county-level). County-level CSV may use either `FIPS` or `STCNTY` as the 5-digit county FIPS column.
   - What's unclear: Which exact column header the county CSV uses.
   - Recommendation: Try both `STCNTY` and `FIPS` with fallback: `fips = (row.get("STCNTY") or row.get("FIPS") or "")`.
   - Confidence: MEDIUM -- both column names are documented, exact header depends on download variant.

4. **SVI 2022 BOM Encoding**
   - What we know: NRI CSVs have BOM (handled by `utf-8-sig`). SVI CSVs may or may not have BOM.
   - What's unclear: Whether CDC includes BOM in their county CSV downloads.
   - Recommendation: Use `utf-8-sig` by default (it handles both BOM and no-BOM correctly). `utf-8-sig` reads BOM if present and ignores if absent.
   - Confidence: HIGH -- `utf-8-sig` is safe regardless.

## Sources

### Primary (HIGH confidence)
- `src/packets/hazards.py` -- 9-step builder template, `_safe_float()`, atomic writes, area-weighted aggregation
- `src/schemas/models.py` -- Pydantic v2 validation conventions (19 models, 1,261 lines)
- `src/paths.py` -- Path constant naming conventions (35 constants + 3 helpers)
- `src/config.py` -- Dynamic fiscal year computation
- `src/packets/context.py` -- TribePacketContext dataclass structure
- `src/packets/doc_types.py` -- DocumentTypeConfig frozen dataclass pattern
- `.planning/phases/18.5-architectural-review/sovereignty-scout-report.md` -- NRI field name confirmation, SVI column verification
- `.planning/phases/18.5-architectural-review/fire-keeper-report.md` -- 9-step builder template, FY26 debt inventory
- `.planning/phases/18.5-architectural-review/river-runner-report.md` -- 37 Pydantic model drafts, composite score formula
- `.planning/phases/18.5-architectural-review/horizon-walker-report.md` -- Option D framing, vocabulary spec, Doc A/B voice
- `.planning/phases/18.5-architectural-review/ARCHITECTURE-DELTA-REPORT.md` -- 8 corrections, GO decision
- `.planning/phases/19-schema-core-data/19-CONTEXT.md` -- User decisions, 5-tier scale, data gap messages
- Pydantic v2 official docs via Context7 (`/llmstxt/pydantic_dev_llms-full_txt`) -- `model_validator`, `field_validator`, `ConfigDict`

### Secondary (MEDIUM confidence)
- [CDC SVI Data Download](https://atsdr.cdc.gov/place-health/php/svi/svi-data-documentation-download.html) -- Download page confirmed
- [FEMA NRI Data](https://www.fema.gov/about/openfema/data-sets/national-risk-index-data) -- Current canonical URL
- [Federal Register: CT County Equivalents](https://www.federalregister.gov/documents/2022/06/06/2022-12063/change-to-county-equivalents-in-the-state-of-connecticut) -- CT FIPS change
- [CT Planning Regions FIPS](https://www.zip-codes.com/connecticut-change-to-planning-regions.asp) -- Complete FIPS table
- [CDC SVI 2022 Documentation PDF](https://www.atsdr.cdc.gov/place-health/media/pdfs/2024/10/SVI2022Documentation.pdf) -- Column names, -999 sentinel

### Tertiary (LOW confidence)
- SVI 2022 exact download URL -- needs runtime verification (dynamically generated)
- NRI v1.20 CT FIPS format -- needs CSV inspection at build time

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all stdlib or already in requirements.txt; verified against codebase
- Architecture: HIGH -- all patterns extracted from actual source code (hazards.py, models.py, paths.py)
- Data sources: HIGH -- NRI fields confirmed by Sovereignty Scout against v1.20 Data Dictionary; SVI columns confirmed by documentation
- Pitfalls: HIGH -- CT FIPS, BOM encoding, -999 sentinel, weight normalization all documented with specific handling
- Vocabulary: HIGH -- Full spec from Horizon Walker with implementation skeleton

**Research date:** 2026-02-17
**Valid until:** 2026-03-17 (stable domain -- NRI/SVI release cycles are annual)
