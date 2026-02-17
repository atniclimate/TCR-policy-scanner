# Fire Keeper Report: Codebase Pattern Analysis
## Phase 18.5 | TCR Policy Scanner v1.4

### Executive Summary

The v1.3 codebase is architecturally clean, pattern-consistent, and ready for v1.4 integration. The HazardProfileBuilder in `src/packets/hazards.py` provides a complete, well-tested template that VulnerabilityProfileBuilder must replicate -- including area-weighted crosswalk aggregation, multi-tier fallback resolution, atomic JSON writes, and path traversal guards. The primary technical debt finding is **22 hardcoded "FY26" string literals** in `doc_types.py`, `docx_engine.py`, and `docx_template.py` that do NOT use the centralized `config.FISCAL_YEAR_SHORT` constant. All other v1.3 known issues (hardcoded loggers, format_dollars duplication, hardcoded graph_schema paths) are fully resolved.

---

### Pattern Conformance Specification

#### HazardProfileBuilder Template

**Source:** `src/packets/hazards.py` (48,882 bytes, SHA: 320b6508)

The `HazardProfileBuilder` is the EXACT template that `VulnerabilityProfileBuilder` must follow. Every step is documented below from actual code inspection.

##### Step 1: Class Initialization (`__init__`)

```python
def __init__(self, config: dict) -> None:
```

- Accepts `config: dict` (the application config)
- Reads paths from `config["packets"]["hazards"][*]` with fallback to path constants
- Uses `_resolve_path()` for relative-to-absolute path conversion
- Loads `TribalRegistry` via lazy import inside `__init__` (avoids circular imports)
- Loads AIANNH crosswalk (GEOID -> tribe_id mapping) and inverts it (tribe_id -> [GEOIDs])
- Loads pre-computed area weights from `TRIBAL_COUNTY_WEIGHTS_PATH`
- Sets `_nri_version: str` as dataset version tracking

**Pattern for VulnerabilityProfileBuilder:**
```python
def __init__(self, config: dict) -> None:
    packets_cfg = config.get("packets", {})
    vuln_cfg = packets_cfg.get("vulnerability", {})
    # Read config paths with fallbacks to constants
    # Load TribalRegistry
    # Load AIANNH crosswalk (same as hazards.py)
    # Load area weights (IDENTICAL to hazards.py)
```

##### Step 2: Crosswalk Loading (`_load_crosswalk`)

- Opens `aiannh_tribe_crosswalk.json` with `encoding="utf-8"`
- Handles `FileNotFoundError` (warns, returns empty) and `json.JSONDecodeError` (errors, returns empty)
- Reads `data["mappings"]` dict (GEOID -> tribe_id)
- Builds reverse mapping: `_tribe_to_geoids: dict[str, list[str]]`
- Logs count summary

**QUIRK:** One Tribe may span multiple AIANNH areas (e.g., Navajo Nation), so the reverse mapping is 1-to-many.

##### Step 3: Area Weights Loading (`_load_area_weights`)

- Checks `TRIBAL_COUNTY_WEIGHTS_PATH.exists()` -- warns and returns `{}` if missing
- Reads JSON with `encoding="utf-8"`
- Handles `json.JSONDecodeError` and `OSError`
- Returns `data["crosswalk"]` dict: GEOID -> list of `{county_fips, weight, overlap_area_sqkm}`
- Logs metadata counts from `data["metadata"]`

##### Step 4: NRI County Data Loading (`_load_nri_county_data`)

- Looks for `self.nri_dir / "NRI_Table_Counties.csv"`
- Opens with `encoding="utf-8-sig"` (handles BOM from FEMA CSV downloads)
- Uses `csv.DictReader` for header-keyed access
- Extracts composite metrics: `RISK_SCORE`, `RISK_RATNG`, `RISK_VALUE`, `EAL_VALT`, `EAL_SCORE`, `EAL_RATNG`, `SOVI_SCORE`, `SOVI_RATNG`, `RESL_SCORE`, `RESL_RATNG`
- Extracts per-hazard metrics for all 18 NRI hazard codes: `{CODE}_RISKS`, `{CODE}_RISKR`, `{CODE}_EALT`, `{CODE}_AFREQ`, `{CODE}_EVNTS`
- Uses `_safe_float()` for ALL numeric conversions (handles None, "", NaN, Inf, -Inf)
- Zero-pads FIPS to 5 digits with `fips.zfill(5)`
- Returns dict keyed by STCOFIPS
- Detects NRI version from sibling ZIP filenames via `_detect_nri_version()`

**CRITICAL QUIRK -- `_safe_float()`:** This function is the NaN/Inf firewall. Returns `default` (0.0) for None, empty string, NaN, Inf, -Inf. VulnerabilityProfileBuilder MUST use this same function (or import it) for all numeric CSV parsing. NRI data contains sentinel values and empty cells.

##### Step 5: Per-Tribe NRI Profile (`_build_tribe_nri_profile`)

Resolution chain (4-tier fallback):
1. **tribe_id -> AIANNH GEOIDs** (from crosswalk)
2. **AIANNH GEOIDs -> county FIPS + area weights** (from area crosswalk, preferred)
3. **Fallback: AIANNH GEOIDs -> county FIPS** (from tribal relational CSV, equal weights)
4. **Last resort: state-level county matching** (equal weights via FIPS prefix)

Aggregation strategy (area-weighted):
- **Weight accumulation:** If same county appears via multiple GEOIDs, weights are SUMMED (not averaged)
- **Weight normalization:** After collecting matched counties, weights are normalized to sum to 1.0 across MATCHED counties only (not all counties in crosswalk)
- **Zero total_w guard:** If total_w == 0, falls back to equal weight (1/N) -- prevents division by zero
- **Percentile scores:** Weighted AVERAGE (risk_score, eal_score, sovi_score, resl_score)
- **Dollar amounts (EAL):** Weighted average (proportional attribution) -- NOT raw sum
- **Rating strings:** Re-derived from weighted scores via `score_to_rating()`, NOT taken from source
- **All 18 hazard types:** Always present in `all_hazards` dict (zeros for missing -- schema consistency)
- **Top 5 hazards:** Filtered to non-zero risk_score, sorted descending, sliced [:5]

**CRITICAL QUIRK -- Ratings are re-derived, not averaged:** When two counties both say "Very High" but have scores 85 and 65, the average score is 75 which maps to "Relatively High". The builder correctly re-derives ratings from weighted scores rather than averaging rating strings.

**CRITICAL QUIRK -- Empty profile schema:** `_empty_nri_profile()` returns all 18 hazard codes with zero values for schema consistency. This ensures downstream renderers never encounter missing keys.

##### Step 6: USFS Wildfire Override

In `build_all_profiles()`:
- Override condition: USFS match exists AND NRI WFIR risk_score > 0 AND USFS risk_to_homes > 0
- Replaces `wfir_entry["risk_score"]` with USFS value
- Re-derives rating from new score
- Marks `wfir_entry["source"] = "USFS"`
- Stores original NRI value as `usfs_profile["nri_wfir_original"]`
- **Re-extracts top 5 after override** (critical -- the override may change rankings)

##### Step 7: Atomic JSON Write

```python
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

- Uses `tempfile.mkstemp()` (not `NamedTemporaryFile`) for cross-platform safety
- `os.fdopen()` wraps the file descriptor with `encoding="utf-8"`
- `json.dump()` with `indent=2, ensure_ascii=False`
- `os.replace()` for atomic rename
- Cleanup in except block with `contextlib.suppress(OSError)`

##### Step 8: Path Traversal Guard

```python
tribe_id = Path(tribe["tribe_id"]).name
if tribe_id != tribe["tribe_id"] or ".." in tribe_id:
    logger.warning("Skipping suspicious tribe_id: %r", tribe["tribe_id"])
    continue
```

##### Step 9: Coverage Report

- Generates both JSON and Markdown reports
- Per-state breakdown tracking
- Unmatched Tribes list with names, IDs, states
- Uses same atomic write pattern for report files

**Pattern summary for VulnerabilityProfileBuilder:** Follow Steps 1-9 exactly. The crosswalk, area weights, weight normalization, `_safe_float()`, atomic writes, and path traversal guards are non-negotiable.

---

#### TribePacketContext Expansion

**Source:** `src/packets/context.py` (3,049 bytes, SHA: 39d8cc5d)

##### Current Fields (14 total)

| Field | Type | Default | Phase |
|-------|------|---------|-------|
| `tribe_id` | `str` | (required) | REG-01 |
| `tribe_name` | `str` | (required) | REG-01 |
| `states` | `list[str]` | `[]` | REG-03 |
| `ecoregions` | `list[str]` | `[]` | REG-03 |
| `bia_code` | `str` | `""` | Identity |
| `epa_id` | `str` | `""` | Identity |
| `districts` | `list[dict]` | `[]` | CONG-01 |
| `senators` | `list[dict]` | `[]` | CONG-02 |
| `representatives` | `list[dict]` | `[]` | CONG-02 |
| `awards` | `list[dict]` | `[]` | Phase 6 |
| `hazard_profile` | `dict` | `{}` | Phase 6 |
| `economic_impact` | `dict` | `{}` | Phase 7 |
| `congressional_intel` | `dict` | `{}` | INTEL-06 |
| `generated_at` | `str` | `""` | Metadata |
| `congress_session` | `str` | `"119"` | Metadata |

##### Dict-Typed Fields (4 existing)

1. `hazard_profile: dict` -- NRI composite + per-hazard + USFS wildfire
2. `economic_impact: dict` -- Economic multiplier calculations (from `asdict(TribeEconomicSummary)`)
3. `congressional_intel: dict` -- Bills, delegation activity, scan_date, congress number
4. (None have nested Pydantic models -- all are plain dicts populated by the orchestrator)

##### Adding `vulnerability_profile: dict`

- **No naming collision.** "vulnerability" does not conflict with any existing field.
- **Pattern match:** Follows `hazard_profile`, `economic_impact`, `congressional_intel` exactly.
- **Default:** `field(default_factory=dict)` -- consistent with all other dict fields.
- **`to_dict()`:** Uses `dataclasses.asdict()` which handles nested dicts recursively. No change needed.
- **Recommended placement:** After `congressional_intel`, before metadata fields.

##### Memory Implications for 592-Tribe Batch

- Current context size estimate: ~5-20 KB per Tribe (awards list is largest)
- Adding vulnerability_profile: +5-10 KB per Tribe
- Total batch memory: 592 x ~25 KB = ~15 MB (well within acceptable bounds)
- `gc.collect()` called every 25 Tribes in `run_all_tribes()` (existing pattern)
- The orchestrator builds contexts one at a time, stores in `prebuilt_contexts` dict for regional aggregation
- Worst case: 592 contexts in memory simultaneously = ~15 MB (negligible)

---

#### Renderer Function Catalog

**Source:** `src/packets/docx_sections.py` (51,108 bytes, SHA: da0d4092)

##### Public Section Renderers (10 functions)

| # | Function | Signature | Page Break |
|---|----------|-----------|------------|
| 1 | `render_cover_page` | `(document, context, style_manager, doc_type_config=None)` | Yes |
| 2 | `render_table_of_contents` | `(document, programs, context, style_manager)` | Yes |
| 3 | `render_executive_summary` | `(document, context, relevant_programs, economic_summary, style_manager, doc_type_config=None)` | Yes |
| 4 | `render_delegation_section` | `(document, context, style_manager, doc_type_config=None)` | Yes |
| 5 | `render_hazard_summary` | `(document, context, style_manager, doc_type_config=None)` | Yes |
| 6 | `render_structural_asks_section` | `(document, structural_asks, context, style_manager, doc_type_config=None)` | Yes |
| 7 | `render_bill_intelligence_section` | `(document, context, style_manager, doc_type_config=None)` | Yes |
| 8 | `render_messaging_framework` | `(document, context, style_manager)` | Yes |
| 9 | `render_appendix` | `(document, omitted_programs, context, style_manager, doc_type_config=None)` | No |
| 10 | `render_change_tracking` | `(document, changes, previous_date, style_manager)` | No |

##### Internal Helper Functions (6 functions)

| Function | Purpose |
|----------|---------|
| `_render_bill_full_briefing` | Doc A full bill card with talking points |
| `_render_bill_facts_only` | Doc B facts-only bill entry |
| `_render_bill_compact_card` | Default compact bill card |
| `_render_talking_points` | Doc A talking points for a bill |
| `_render_timing_note` | Doc A timing/urgency note (audience-guarded) |
| `_filter_relevant_committees` | Filter committees by keyword match |
| `_build_ask_evidence` | Build evidence line from context data |

##### Common Parameter Pattern (MANDATORY for new renderers)

```python
def render_vulnerability_section(
    document: Document,              # python-docx Document (positional)
    context: TribePacketContext,     # Full Tribe context (positional)
    style_manager: StyleManager,     # Style manager instance (positional)
    doc_type_config: DocumentTypeConfig | None = None,  # Optional audience filter
) -> None:
```

- Return type: `None` (all renderers modify document in-place)
- All renderers use `logger = logging.getLogger(__name__)` at module level
- All renderers log at INFO or DEBUG level when rendering completes
- Page break at end of section (except appendix and change tracking)

##### Audience-Aware Rendering Pattern

```python
is_internal = doc_type_config is not None and doc_type_config.is_internal
is_congressional = doc_type_config is not None and doc_type_config.is_congressional

if is_internal:
    # Include strategy/approach content
    ...
if is_congressional:
    # Facts-only, source citations
    ...
```

##### Conditional Data Rendering Pattern

```python
# Always check if data exists before rendering
hazard_profile = context.hazard_profile or {}
fema_nri = hazard_profile.get("fema_nri") or hazard_profile.get(
    "sources", {}
).get("fema_nri", {})

if not fema_nri and not usfs_data:
    document.add_paragraph(
        "Hazard profile data not available for this Tribe.",
        style="HS Body",
    )
    document.add_page_break()
    return
```

##### Style Manager Usage

- Heading: `document.add_paragraph("Title", style="Heading 2")`
- Body: `document.add_paragraph(text, style="HS Body")`
- Small: `document.add_paragraph(text, style="HS Small")`
- Section sub-heading: `document.add_paragraph(text, style="HS Section")`
- Title: `document.add_paragraph(text, style="HS Title")`
- Tables: `format_header_row(table, headers)` + `apply_zebra_stripe(table)`
- Colors: `COLORS.muted`, `COLORS.primary_dark` etc. (from `_ColorNamespace`)
- CI badges: `CI_STATUS_LABELS` dict for status label text
- Dollar formatting: `format_dollars()` imported from `src.utils`

##### Specification for `docx_vulnerability_sections.py`

New renderer functions MUST:
1. Accept the standard 4 parameters: `(document, context, style_manager, doc_type_config=None)`
2. Check `context.vulnerability_profile or {}` before rendering
3. Display "data not available" message and return early if empty
4. Use `style="Heading 2"` for section headings (NOT `document.add_heading()`)
5. Use `style="HS Body"` for all body paragraphs
6. Use `format_header_row()` and `apply_zebra_stripe()` for tables
7. Use `format_dollars()` for dollar amounts
8. End with `document.add_page_break()`
9. Log at INFO level on completion
10. Implement audience-aware rendering for Doc A (internal) vs Doc B (congressional)

---

#### DocxEngine Integration

**Source:** `src/packets/docx_engine.py` (15,676 bytes, SHA: 98a7ecc3)

##### Render Sequence in `generate()` (11 steps)

| # | Call | Audience Guard | Notes |
|---|------|----------------|-------|
| 1 | `render_cover_page(doc, ctx, sm, dtc)` | All | |
| 2 | `render_table_of_contents(doc, programs, ctx, sm)` | All | No dtc |
| 3 | `render_executive_summary(doc, ctx, programs, econ, sm, dtc)` | All | Extra params |
| 4 | `render_bill_intelligence_section(doc, ctx, sm, dtc)` | All | Bills-first ordering |
| 5 | `render_delegation_section(doc, ctx, sm, dtc)` | All | |
| 6 | `HotSheetRenderer.render_all_hotsheets(ctx, programs, econ, asks, dtc)` | All | Class-based |
| 7 | `document.add_page_break()` + `render_hazard_summary(doc, ctx, sm, dtc)` | All | Manual page break |
| 8 | `render_structural_asks_section(doc, asks, ctx, sm, dtc)` | All | |
| 9 | `render_messaging_framework(doc, ctx, sm)` | Doc A only | `dtc.include_messaging_framework` |
| 10 | `render_change_tracking(doc, changes, prev_date, sm)` | Internal only | `dtc.is_internal` |
| 11 | `render_appendix(doc, omitted, ctx, sm, dtc)` | All | Last section |

##### Vulnerability Section Insertion Point

Insert vulnerability sections between step 7 (hazard summary) and step 8 (structural asks):

```python
# 7. Hazard profile summary
document.add_page_break()
render_hazard_summary(document, context, style_manager, doc_type_config=dtc)

# 7.5 Vulnerability assessment (v1.4)
if context.vulnerability_profile:
    render_vulnerability_overview(document, context, style_manager, doc_type_config=dtc)
    render_climate_projections_section(document, context, style_manager)
    render_svi_breakdown(document, context, style_manager, doc_type_config=dtc)

# 8. Structural asks standalone
render_structural_asks_section(...)
```

**Rationale:** Vulnerability data is a natural extension of the hazard profile. Placing it immediately after the hazard summary creates a coherent risk-assessment narrative: current hazards -> future vulnerability -> policy asks that address both.

##### Import Pattern

All renderers are imported at the top of `docx_engine.py`:

```python
from src.packets.docx_sections import (
    render_appendix,
    render_bill_intelligence_section,
    render_change_tracking,
    ...
)
```

New vulnerability imports follow the same pattern:

```python
from src.packets.docx_vulnerability_sections import (
    render_vulnerability_overview,
    render_climate_projections_section,
    render_svi_breakdown,
)
```

##### Doc Type Config Resolution

```python
dtc = doc_type_config or self.doc_type_config
```

The `generate()` parameter overrides the instance-level config.

##### Filename Generation

```python
if dtc is not None:
    filename_stem = dtc.format_filename(tribe_id).replace(".docx", "")
else:
    filename_stem = tribe_id
```

---

#### DocumentTypeConfig

**Source:** `src/packets/doc_types.py` (7,078 bytes, SHA: e74d6362)

##### Frozen Dataclass Structure (14 fields)

```python
@dataclass(frozen=True)
class DocumentTypeConfig:
    doc_type: str           # "A", "B", "C", "D"
    audience: str           # "internal" or "congressional"
    scope: str              # "tribal" or "regional"
    title_template: str     # Cover page title
    header_template: str    # Per-page header with {tribe_name}/{region_name}
    footer_template: str    # Per-page footer
    confidential: bool      # CONFIDENTIAL banner
    include_strategy: bool  # Leverage, approach, messaging sections
    include_advocacy_lever: bool      # Per-program advocacy lever text
    include_member_approach: bool     # Member-specific approach recommendations
    include_messaging_framework: bool # Talking points section
    structural_asks_framing: str      # "strategic" or "policy_recommendation"
    narrative_voice: str              # "assertive" or "objective"
    filename_suffix: str              # For generated filenames
```

##### Properties (4)

- `is_internal` -> `audience == "internal"`
- `is_congressional` -> `audience == "congressional"`
- `is_tribal` -> `scope == "tribal"`
- `is_regional` -> `scope == "regional"`

##### Methods (2)

- `format_header(tribe_name=None, region_name=None)` -> substitutes `{tribe_name}` and `{region_name}`
- `format_filename(slug)` -> returns `"{slug}_{suffix}_fy26.docx"` (**NOTE: hardcoded "fy26"**)

##### Adding `include_vulnerability: bool`

Because the dataclass is `frozen=True`, adding a new field with a default value is safe as long as it comes AFTER all existing fields. The field must have a default to maintain backward compatibility:

```python
include_vulnerability: bool = False
```

**WARNING:** The `format_filename()` method hardcodes `"fy26"` instead of using `FISCAL_YEAR_SHORT`. This must be fixed.

##### DOC_E Definition Template

```python
DOC_E = DocumentTypeConfig(
    doc_type="E",
    audience="internal",
    scope="tribal",
    title_template=f"{FISCAL_YEAR_SHORT} Climate Vulnerability Assessment",
    header_template="{tribe_name} | Vulnerability Assessment | CONFIDENTIAL",
    footer_template="Confidential: For Internal Use Only",
    confidential=True,
    include_strategy=True,
    include_advocacy_lever=False,
    include_member_approach=False,
    include_messaging_framework=False,
    structural_asks_framing="strategic",
    narrative_voice="assertive",
    filename_suffix="vulnerability_assessment",
    include_vulnerability=True,  # New field
)
```

Also add to `DOC_TYPES` lookup dict:

```python
DOC_TYPES: dict[str, DocumentTypeConfig] = {
    "A": DOC_A,
    "B": DOC_B,
    "C": DOC_C,
    "D": DOC_D,
    "E": DOC_E,
}
```

---

#### Orchestrator Integration

**Source:** `src/packets/orchestrator.py` (51,115 bytes, SHA: 363887ad)

##### `__init__()` Cache Directory Setup Pattern

```python
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
```

**Pattern for vulnerability:**
```python
raw = packets_cfg.get("vulnerability", {}).get("cache_dir")
self.vulnerability_cache_dir = Path(raw) if raw else VULNERABILITY_PROFILES_DIR
if not self.vulnerability_cache_dir.is_absolute():
    self.vulnerability_cache_dir = PROJECT_ROOT / self.vulnerability_cache_dir
```

##### `_build_context()` Cache Loading Sequence

Current order:
1. Sanitize tribe_id
2. Classify ecoregions
3. Get congressional delegation
4. Load award cache -> `context.awards`
5. Load hazard cache -> `context.hazard_profile`
6. Construct `TribePacketContext`
7. Load congressional intel -> `context.congressional_intel`

**Vulnerability insertion point:** After step 5, before step 6 (context construction):

```python
# Vulnerability profile (v1.4)
vulnerability_data = self._load_tribe_cache(self.vulnerability_cache_dir, tribe_id)
```

Then pass to context constructor:
```python
vulnerability_profile=vulnerability_data,
```

**NOTE:** The current code extracts `hazard_data.get("sources", {})` before setting on context. The vulnerability profile should be set as the FULL dict (not a sub-key) because `VulnerabilityProfileBuilder` will write the profile directly as the top-level object.

##### `_load_tribe_cache()` Generic Loader

This method handles ALL cache loading with:
- `_sanitize_tribe_id()` -- regex `^[a-zA-Z0-9_-]+$`
- File existence check
- 10 MB size limit enforcement (`_MAX_CACHE_SIZE_BYTES = 10 * 1024 * 1024`)
- `encoding="utf-8"` for `open()`
- `json.JSONDecodeError` and `OSError` handling
- Returns `{}` on any failure (never raises)

**Zero new infrastructure needed.** This method works for any per-Tribe JSON cache.

##### `_display_hazard_summary()` CLI Display Pattern

```python
def _display_hazard_summary(self, context: TribePacketContext) -> None:
    print("\n  Climate Hazard Profile:")
    if not context.hazard_profile:
        print("    No hazard profile data available.")
        return
    # Extract nested data
    nri = context.hazard_profile.get("fema_nri", {})
    composite = nri.get("composite", {})
    # Display formatted values
    print(f"    Overall Risk: {risk_rating or 'N/A'} (score: {risk_score:.1f})")
    # Top hazards list
    for i, h in enumerate(top_hazards, 1):
        print(f"      {i}. {haz_type} (score: {haz_score:.1f}, EAL: {format_dollars(haz_eal)})")
```

**Pattern for `_display_vulnerability_summary()`:**
```python
def _display_vulnerability_summary(self, context: TribePacketContext) -> None:
    print("\n  Vulnerability Assessment:")
    if not context.vulnerability_profile:
        print("    No vulnerability data available.")
        return
    # Display composite score, SVI themes, climate projections
```

---

#### Path Constants

**Source:** `src/paths.py` (4,953 bytes, SHA: 793167f9)

##### Current Count: 35 Path constants + 3 helper functions

##### Naming Conventions

- **Directories:** `SCREAMING_SNAKE_DIR` (e.g., `DATA_DIR`, `NRI_DIR`, `AWARD_CACHE_DIR`)
- **Files:** `SCREAMING_SNAKE_PATH` (e.g., `GRAPH_SCHEMA_PATH`, `TRIBAL_REGISTRY_PATH`)
- **Helper functions:** `snake_case_path(tribe_id: str) -> Path` (e.g., `award_cache_path()`, `hazard_profile_path()`)

##### Grouping Convention

Constants are grouped by purpose with section headers:
1. Project Root
2. Config Paths
3. Data Paths (flat files)
4. Data Paths (subdirectories)
5. Output Paths
6. Docs Paths
7. Scripts Paths
8. Helper Functions (per-Tribe paths)

##### New Constants Needed (6 constants + 1 helper)

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

def vulnerability_profile_path(tribe_id: str) -> Path:
    """Return the vulnerability profile JSON path for a specific Tribe."""
    return VULNERABILITY_PROFILES_DIR / f"{tribe_id}.json"
```

**Post-addition count: 41 Path constants + 4 helper functions**

---

### Technical Debt Report

#### 1. Hardcoded Loggers: **RESOLVED**

Search for `getLogger("` with string literals (not `__name__`) in `src/`:

**Result: Zero matches.** All loggers use `logging.getLogger(__name__)`.

#### 2. Hardcoded FY Literals: **INHERITED (22 instances)**

Search for `FY26` string literals in `src/` (excluding config.py comments):

| File | Count | Nature |
|------|-------|--------|
| `src/packets/doc_types.py` | 8 | Title templates, header templates, filename suffix (`_fy26.docx`) |
| `src/packets/docx_engine.py` | 2 | Default header text, docstring |
| `src/packets/docx_template.py` | 1 | Hardcoded header string |
| `src/packets/docx_sections.py` | 1 | Docstring reference to "FY26 title" |
| `src/graph/schema.py` | 2 | Field name `fy26_status`, docstring |
| `src/graph/builder.py` | 1 | Field assignment `fy26_status=` |
| `src/schemas/models.py` | 3 | Field names and descriptions |
| `src/monitors/iija_sunset.py` | 4 | Variable names and dict keys (semantic, not display) |

**Assessment:** `doc_types.py` is the most critical. It hardcodes "FY26" in 4 title templates, 2 header templates, and the `format_filename()` method. These should all import and use `FISCAL_YEAR_SHORT` from `src.config`. The `graph/schema.py` and `schemas/models.py` instances are field NAMES (`fy26_status`) which are semantic identifiers, not display strings -- lower priority but still debt.

**Impact on v1.4:** DOC_E definition MUST use `FISCAL_YEAR_SHORT` instead of hardcoding "FY26". Recommend fixing all `doc_types.py` instances as part of v1.4 to prevent drift.

#### 3. format_dollars Duplication: **RESOLVED**

Search for `_format_dollars` or `def format_dollars` in `src/`:

**Result:** Single canonical definition at `src/utils.py:9`. All imports reference `src.utils.format_dollars`. Zero local duplicates.

#### 4. graph_schema Hardcoded Paths: **RESOLVED**

Search for `"graph_schema.json"` as a string literal in `src/`:

**Result:** Only instance is the path constant definition itself at `src/paths.py:51`. All other references use `GRAPH_SCHEMA_PATH`.

#### 5. NEW DEBT DISCOVERED: `docx_engine.py` Default Header

`_setup_header_footer()` at line 180 hardcodes:
```python
header_text = "FY26 Climate Resilience Program Priorities"
```

This should be:
```python
from src.config import FISCAL_YEAR_SHORT
header_text = f"{FISCAL_YEAR_SHORT} Climate Resilience Program Priorities"
```

#### 6. NEW DEBT DISCOVERED: `format_filename()` Hardcoded Year

`doc_types.py` line 113:
```python
return f"{slug}_{self.filename_suffix}_fy26.docx"
```

This should use the FISCAL_YEAR_SHORT constant. However, since `DocumentTypeConfig` is a frozen dataclass imported at module level, and `config.py` computes FISCAL_YEAR_SHORT dynamically, the fix requires either:
- (a) Making `format_filename()` import the constant at call time (lazy import), or
- (b) Passing fiscal year as a parameter

---

### Test Architecture

**Source:** `tests/` directory listing from GitHub (31 test files)

##### Organization: By Module/Feature

| Test File | LOC | Focus Area |
|-----------|-----|------------|
| `test_packets.py` | 53,932 | Core packet generation, orchestrator, context |
| `test_e2e_congressional.py` | 39,163 | Congressional intel end-to-end |
| `test_schemas.py` | 35,522 | Pydantic model validation |
| `test_pagination.py` | 34,846 | Scraper pagination |
| `test_decision_engine.py` | 33,939 | Decision engine rules |
| `test_hazard_aggregation.py` | 31,988 | NRI aggregation, area weighting |
| `test_strategic_overview.py` | 32,049 | Strategic overview document |
| `test_e2e_phase8.py` | 31,814 | Phase 8 end-to-end |
| `test_docx_integration.py` | 29,054 | DOCX integration tests |
| `test_congressional_rendering.py` | 28,382 | Congressional section rendering |
| `test_regional.py` | 28,819 | Regional document generation |
| `test_docx_hotsheet.py` | 28,119 | Hot Sheet rendering |
| `test_doc_assembly.py` | 25,940 | Document assembly |
| `test_audience_filtering.py` | 24,536 | Audience-differentiated content |
| `test_docx_template.py` | 24,608 | Template-based document creation |
| `test_circuit_breaker.py` | 24,109 | Circuit breaker resilience |
| `test_awards.py` | 23,439 | Award matching/population |
| `test_economic.py` | 23,888 | Economic impact calculations |
| `test_xcut_compliance.py` | 21,914 | Cross-cutting compliance |
| `test_web_index.py` | 21,967 | Web index builder |
| `test_congressional_models.py` | 21,206 | Congressional Pydantic models |
| `test_quality_review.py` | 17,627 | Document quality review |
| `test_change_tracking.py` | 15,424 | Change detection |
| `test_batch_generation.py` | 14,965 | Batch document generation |
| `test_docx_styles.py` | 14,825 | DOCX style application |
| `test_validate_coverage.py` | 13,769 | Coverage validation |
| `test_usaspending_batch.py` | 13,363 | USASpending batch queries |
| `test_confidence.py` | 10,825 | Confidence scoring |
| `test_doc_types.py` | 11,220 | Document type config |
| `test_usfs_override_integration.py` | 11,039 | USFS wildfire override |
| `test_housing_authority_aliases.py` | 7,768 | Housing authority aliases |
| `test_populate_awards.py` | 2,612 | Award population script |

##### Common Fixtures (from `test_hazard_aggregation.py`)

```python
@pytest.fixture
def base_fixture(self, tmp_path: Path) -> dict:
    """Provide reusable test dirs and registry."""
    # Create mini registry JSON
    # Create crosswalk JSON
    # Create NRI/USFS directories
    return {"tmp_path": ..., "reg_path": ..., "crosswalk_path": ..., ...}
```

- `tmp_path` (pytest built-in) is the primary fixture for test directories
- Test data files are created inline via helper functions (`_write_json`, `_make_nri_csv`, etc.)
- `unittest.mock.patch` used for path constant overrides
- No shared `conftest.py` with project-wide fixtures (each test file is self-contained)

##### Test Naming Conventions

- Classes: `TestClassName` (e.g., `TestAreaWeightedAggregation`, `TestSafeFloat`)
- Methods: `test_descriptive_name` (e.g., `test_single_county_passthrough`, `test_nan_string_returns_default`)
- Docstrings: Required, describe the behavior being tested
- Structural tests: Inspect source code via `inspect.getsource()` to verify patterns (e.g., atomic write, path sanitization)

##### Recommended Test Structure for v1.4

```
tests/
  test_vulnerability.py          # VulnerabilityProfileBuilder unit tests
    TestSVIParsing               # SVI CSV parsing, _safe_float for RPL columns
    TestClimateProjectionParsing # Climate JSON loading, summary extraction
    TestCompositeVulnerability   # Composite score computation, weights, thresholds
    TestAreaWeightedSVI          # SVI area-weighted aggregation (mirrors TestAreaWeightedAggregation)
    TestAtomicProfileWrites      # Atomic write verification
    TestPathTraversalGuard       # Path sanitization
    TestEmptyProfileSchema       # Schema consistency with empty data
    TestCoverageReport           # Coverage report generation

  test_vulnerability_rendering.py # DOCX vulnerability section tests
    TestVulnerabilityOverview    # Composite score display, rating badge
    TestClimateProjections       # Temperature table, extreme event display
    TestSVIBreakdown             # 4-theme breakdown rendering
    TestAudienceFiltering        # Doc A vs Doc B content differences
    TestEmptyDataHandling        # Graceful empty-state rendering

  test_doc_e.py                  # Doc E integration tests
    TestDocEConfig               # DocumentTypeConfig for DOC_E
    TestDocEGeneration           # Full Doc E generation pipeline
    TestDocEFilename             # Filename format verification
```

**Expected test count:** ~80-120 new tests for v1.4 vulnerability features, bringing total to ~1,050-1,090.

---

### Dependency Compatibility Matrix

| Package | Pinned Version | Current Stable | Breaking Changes | Notes |
|---------|---------------|----------------|------------------|-------|
| pydantic | `>=2.0.0` | 2.13.3 | No | Already on v2. No v1 migration needed. |
| python-docx | `>=1.1.0` | 1.2.0 | No | Minor release only. No API changes. |
| geopandas | `>=1.0.0` | 1.1.2 | No | Build-time only (crosswalk generation). |
| openpyxl | `>=3.1.0` | 3.1.5 | No | USFS XLSX parsing. Stable API. |
| requests | `>=2.31.0` | 2.32.3 | No | HTTP downloads. Stable API. |
| rapidfuzz | `>=3.14.0` | 3.13.0+ | No | Fuzzy matching. Stable API. |
| aiohttp | `>=3.9.0` | 3.11.x | No | Async HTTP. Not used in vulnerability pipeline. |
| shapely | `>=2.0.0` | 2.0.7 | No | Build-time only. Stable API. |
| xarray | (not yet added) | 2026.1.0 | N/A | NEW for LOCA2 NetCDF. Requires Python 3.10+. |
| netCDF4 | (not yet added) | 1.7.4 | N/A | NEW backend for xarray. C library dependency. |

**Key finding:** The project is on Pydantic v2 already (`>=2.0.0` in requirements.txt). No migration concerns. The `src/schemas/models.py` and `src/schemas/` directory use Pydantic v2 syntax (Field, model_validator, etc.).

---

### Dependency Isolation Assessment

#### Current State

- `pyproject.toml` contains ONLY ruff lint config (no `[project]` table)
- `requirements.txt` is the sole dependency specification
- GitHub Actions CI installs ALL deps via `pip install -r requirements.txt`
- geopandas/shapely/pyproj/pyogrio are already listed as "Geospatial (build-time only)" in requirements.txt

#### Optional Dependency Evaluation for xarray/netCDF4

**Recommendation: YES, make xarray/netCDF4 optional.**

Rationale:
1. xarray/netCDF4 are only needed by `scripts/download_climate_projections.py` (data acquisition)
2. They are NOT needed for document generation, vulnerability profile loading, or rendering
3. netCDF4 has C library dependencies (HDF5, netCDF-C) that complicate installation
4. The main pipeline reads pre-processed JSON, not raw NetCDF

**Implementation approach (two-tier):**

**Tier 1: Requirements file approach (simpler, recommended for now)**

```
# requirements.txt
aiohttp>=3.9.0
pydantic>=2.0.0
...existing deps...

# Climate data processing (optional - for scripts/download_climate_projections.py)
# Install with: pip install xarray netCDF4
# xarray>=2024.1
# netCDF4>=1.6
```

Comment them out in requirements.txt. Add a guard in the download script:

```python
try:
    import xarray as xr
    import netCDF4
except ImportError:
    sys.exit(
        "xarray and netCDF4 are required for climate data processing.\n"
        "Install with: pip install xarray netCDF4"
    )
```

**Tier 2: pyproject.toml extras (more formal, future option)**

```toml
[project]
name = "tcr-policy-scanner"
requires-python = ">=3.12"

[project.optional-dependencies]
climate = ["xarray>=2024.1", "netCDF4>=1.6"]
geo = ["geopandas>=1.0.0", "shapely>=2.0.0", "pyproj>=3.3.0", "pyogrio>=0.7.2"]
```

Then: `pip install .[climate]` or `pip install .[geo]`

**CI/CD Impact:**

- The `generate-packets.yml` workflow does NOT run climate projection downloads (it uses cached data)
- Adding optional deps would NOT break CI -- the download script is not called in CI
- If a future CI workflow needs climate downloads, add a separate job with `pip install .[climate]`
- The existing `pip install -r requirements.txt` step continues to work unchanged

---

### Recommendations

#### Pre-Phase 19 Changes (do before starting v1.4 implementation)

1. **Fix FY26 hardcoding in `doc_types.py`** (HIGH priority)
   - Import `FISCAL_YEAR_SHORT` from `src.config`
   - Replace all 4 title templates and 2 header templates
   - Fix `format_filename()` to use `FISCAL_YEAR_SHORT` instead of `"fy26"`
   - This prevents DOC_E from inheriting the same debt

2. **Fix FY26 hardcoding in `docx_engine.py`** (HIGH priority)
   - Line 180: Replace hardcoded default header text

3. **Fix FY26 hardcoding in `docx_template.py`** (MEDIUM priority)
   - Line 515: Replace hardcoded header text

4. **Add `vulnerability_profile: dict` to TribePacketContext** (can be done early)
   - Zero-risk change: `field(default_factory=dict)` is backward compatible
   - All 964 tests will continue to pass

5. **Add path constants to `src/paths.py`** (can be done early)
   - 6 new constants + 1 helper function
   - Zero-risk: no logic changes, just new definitions

#### Architecture Conformance Rules for v1.4

1. `VulnerabilityProfileBuilder` MUST use `_safe_float()` from `hazards.py` (or equivalent) for all numeric parsing
2. All JSON writes MUST use the atomic `tempfile.mkstemp()` + `os.replace()` pattern
3. All tribe_id usage MUST pass through `Path(tribe_id).name` sanitization
4. All `open()` calls MUST specify `encoding="utf-8"` (or `"utf-8-sig"` for CSV with BOM)
5. All dollar formatting MUST use `src.utils.format_dollars()`
6. All loggers MUST use `logging.getLogger(__name__)`
7. All section renderers MUST accept the 4-parameter signature: `(document, context, style_manager, doc_type_config=None)`
8. All section renderers MUST check for empty data and render gracefully
9. The composite vulnerability score MUST include explicit caveats about federal data limitations
10. xarray/netCDF4 MUST be optional (guarded import with clear error message)

---

*Fire Keeper | Phase 18.5 | 2026-02-17*
*The codebase is the living record. Read it, not the docs.*
*Sovereignty is the innovation. Relatives, not resources.*
