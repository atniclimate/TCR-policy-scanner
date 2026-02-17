# Architecture Patterns: Climate Vulnerability Data Integration

**Domain:** Climate vulnerability intelligence for 592 Tribal Nations
**Researched:** 2026-02-17
**Overall Confidence:** HIGH (existing codebase patterns well-understood; data source formats verified)

---

## System Overview

### Current Architecture (v1.3)

```
                          EXISTING PIPELINE
  ============================================================

  scripts/                     data/                    src/packets/
  +-----------------------+    +-------------------+    +------------------+
  | download_nri_data.py  |--->| nri/              |    |                  |
  | build_area_crosswalk  |--->| tribal_county_    |    |                  |
  | download_usfs_data.py |--->| area_weights.json |    |                  |
  | populate_hazards.py   |--->| hazard_profiles/  |--->| orchestrator.py  |
  |                       |    |   epa_*.json (592)|    |   _build_context |
  | populate_awards.py    |--->| award_cache/      |--->|   _load_tribe_   |
  |                       |    |   epa_*.json (592)|    |    cache()       |
  | build_congress_cache  |--->| congressional_    |--->|                  |
  |                       |    |   cache.json      |    |   TribePacket    |
  | build_congressional_  |--->| congressional_    |--->|    Context       |
  |   intel.py            |    |   intel.json      |    |                  |
  +-----------------------+    +-------------------+    +-------+----------+
                                                                |
                                                                v
                                                    +-----------+---------+
                                                    | DocxEngine          |
                                                    |  docx_sections.py   |
                                                    |  docx_hotsheet.py   |
                                                    |  docx_regional_.py  |
                                                    +---------------------+
                                                                |
                                                                v
                                                    outputs/packets/
                                                      internal/     Doc A
                                                      congressional/ Doc B
                                                      regional/     Doc C/D
```

### Proposed Architecture (v1.4 additions shown with >>>)

```
  scripts/                     data/                    src/packets/
  +-----------------------+    +-------------------+    +------------------+
  | download_nri_data.py  |--->| nri/              |    |                  |
  | build_area_crosswalk  |--->| tribal_county_    |    |                  |
  | download_usfs_data.py |--->| area_weights.json |    |                  |
  | populate_hazards.py   |--->| hazard_profiles/  |--->| orchestrator.py  |
  |   (EXPANDED NRI)      |    |   epa_*.json (592)|    |   _build_context |
  |                       |    |                   |    |                  |
>>> download_climate_    |--->| climate/          |    |                  |
>>>   projections.py     |    |   county_climate_ |    |                  |
>>>                      |    |   summaries.json  |    |                  |
>>> download_svi_data.py |--->| svi/              |    |                  |
>>>                      |    |   SVI2022_US_     |    |                  |
>>>                      |    |   COUNTY.csv      |    |                  |
>>> populate_            |--->| vulnerability_    |--->|                  |
>>>   vulnerability.py   |    |   profiles/       |    |   TribePacket    |
>>>                      |    |   epa_*.json (592)|    |    Context       |
  | populate_awards.py    |--->| award_cache/      |--->|    (EXPANDED)    |
  | build_congress_cache  |--->| congressional_*   |--->|                  |
  +-----------------------+    +-------------------+    +-------+----------+
                                                                |
                                                                v
                                                    +-----------+---------+
                                                    | DocxEngine          |
                                                    |  docx_sections.py   |
>>>                                                 |  docx_vulnerability |
>>>                                                 |    _sections.py     |
                                                    |  docx_hotsheet.py   |
                                                    |  docx_regional_.py  |
                                                    +---------------------+
                                                                |
                                                                v
                                                    outputs/packets/
                                                      internal/      Doc A (expanded)
                                                      congressional/  Doc B (expanded)
                                                      regional/       Doc C/D (expanded)
>>>                                                   vulnerability/  Doc E (new)
```

---

## Data Sources: Detailed Analysis

### 1. FEMA NRI Expanded Metrics (ALREADY PARTIALLY INGESTED)

**Confidence:** HIGH -- We already parse this CSV. The expanded fields are in the same file.

**Current state:** `hazards.py` lines 360-377 already extract `RISK_SCORE`, `RISK_RATNG`, `RISK_VALUE`, `EAL_VALT`, `EAL_SCORE`, `EAL_RATNG`, `SOVI_SCORE`, `SOVI_RATNG`, `RESL_SCORE`, `RESL_RATNG` from `NRI_Table_Counties.csv`. These are area-weighted and stored in `hazard_profiles/epa_*.json` under `sources.fema_nri.composite`.

**What is already captured:**
- Composite risk score/rating
- Expected Annual Loss total and score/rating
- Social Vulnerability score/rating (SOVI -- FEMA's own social vulnerability component)
- Community Resilience score/rating (RESL)
- Per-hazard risk scores, EAL, annualized frequency, event counts (all 18 types)

**What is NOT yet captured but available in the same CSV:**
- `EAL_VALB` -- EAL Buildings component ($)
- `EAL_VALP` -- EAL Population component ($)
- `EAL_VALA` -- EAL Agriculture component ($)
- `EAL_VALPE` -- EAL Population Equivalence
- `RISK_NPCTL` -- Risk National Percentile (vs current state-relative score)
- `SOVI_VALUE` -- Social Vulnerability raw value
- `RESL_VALUE` -- Community Resilience raw value
- Per-hazard EAL component breakdowns (`{CODE}_EALB`, `{CODE}_EALP`, `{CODE}_EALA`)
- `POPULATION`, `BUILDVALUE`, `AREA` -- demographic/structural context

**Architecture decision:** Expand `_load_nri_county_data()` in `hazards.py` to extract these additional fields. No new data download needed. The expanded fields flow into the existing per-Tribe JSON cache via the same area-weighted aggregation pipeline. This is the lowest-friction change in the entire milestone.

**Source:** [FEMA NRI Data Resources](https://www.fema.gov/about/openfema/data-sets/national-risk-index-data) (HIGH confidence)

### 2. CDC/ATSDR Social Vulnerability Index (SVI)

**Confidence:** HIGH -- Official CSV downloads verified at svi.cdc.gov.

**Data format:** CSV download from [svi.cdc.gov/dataDownloads](https://svi.cdc.gov/dataDownloads/data-download.html), county-level, available as "United States" (all counties ranked nationally). Latest release: SVI 2022 based on 2018-2022 ACS 5-year estimates.

**Key columns (from SVI 2022 documentation):**
- `FIPS` -- 5-digit county FIPS (directly joinable to NRI `STCOFIPS`)
- `RPL_THEMES` -- Overall SVI percentile rank (0-1, higher = more vulnerable)
- `RPL_THEME1` -- Socioeconomic Status theme rank
- `RPL_THEME2` -- Household Characteristics theme rank
- `RPL_THEME3` -- Racial & Ethnic Minority Status theme rank
- `RPL_THEME4` -- Housing Type & Transportation theme rank
- `E_*` columns -- Estimate values for each of 16 census variables
- `EP_*` columns -- Percentages
- `EPL_*` columns -- Percentile rankings per variable
- `F_*` columns -- Binary flags (above 90th percentile)

**Architecture decision:** SVI data joins to NRI data via county FIPS. The existing area-weighted crosswalk (`tribal_county_area_weights.json`) maps AIANNH GEOIDs to county FIPS with normalized weights. SVI scores can be area-weighted using the EXACT same machinery already built for NRI. This is a natural extension, not a new architecture.

**Note on FEMA NRI SOVI vs CDC SVI:** The NRI already has its own Social Vulnerability score (`SOVI_SCORE`/`SOVI_RATNG`). CDC SVI is a SEPARATE index with different methodology (16 census variables in 4 themes vs NRI's social vulnerability component). Both are valuable -- NRI SOVI feeds into risk calculation, while CDC SVI provides more granular social determinant breakdowns. Recommendation: Include BOTH. Label clearly in output documents.

**Source:** [CDC/ATSDR SVI Data Download](https://svi.cdc.gov/dataDownloads/data-download.html) (HIGH confidence), [SVI 2022 Documentation PDF](https://www.atsdr.cdc.gov/place-health/media/pdfs/2024/10/SVI2022Documentation.pdf) (HIGH confidence)

### 3. NOAA/USGS Climate Projections (LOCA2/CMIP6)

**Confidence:** MEDIUM -- Data exists at county level via USGS, but format is NetCDF (not CSV), and bulk download approach needs validation during phase research.

**Best source identified:** USGS "CMIP6-LOCA2 spatial summaries of counties (TIGER 2023) from 1950-2100 for the Contiguous United States" ([ScienceBase](https://www.sciencebase.gov/catalog/item/673d0719d34e6b795de6b593))

**What this provides:**
- County-level time series averaged from LOCA2 6km grid
- 27 GCMs under SSP245, SSP370, SSP585 scenarios
- Temperature and precipitation projections
- 36 annual + 4 monthly extreme event metrics (Climdex-based)
- Periods: 1950-2100 (we want 2025-2049 and 2050-2074 summaries)
- Keyed by county GEOID (same 5-digit FIPS as NRI)

**Data format:** NetCDF time series files linked to shapefile geometry via GEOID field. This means we need either:
- (a) A pre-processing step to extract summary statistics to JSON (recommended), or
- (b) Direct NetCDF parsing with `netCDF4` or `xarray` in the population script

**Alternative source:** NOAA Climate Explorer ([crt-climate-explorer.nemac.org](https://crt-climate-explorer.nemac.org/)) provides per-county projections interactively but has NO bulk download API. Not suitable for programmatic 592-Tribe processing.

**Relevant climate variables for Tribal vulnerability:**
- Days above 95F / 100F / 105F (extreme heat)
- Days below 32F / 0F (extreme cold)
- Consecutive dry days (drought proxy)
- Heavy precipitation days (>1 inch)
- Heating/Cooling Degree Days (energy burden)
- Total annual precipitation change
- Mean temperature change (mid-century vs baseline)

**Architecture decision:** Create `scripts/download_climate_projections.py` that downloads USGS LOCA2 county NetCDF files, extracts mid-century summary statistics, and writes a county-level JSON summary cache. The vulnerability profile builder then area-weights these (same crosswalk). This is the most complex new data source because of the NetCDF format and multi-scenario aggregation.

**Key risk -- Alaska coverage:** LOCA2 county summaries cover CONUS only. Alaska boroughs may need separate handling. For the 70+ Alaska Native entities, we may need a fallback data source or accept partial coverage and flag those Tribes. This needs deeper research during the climate projections phase.

**Source:** [USGS CMIP6-LOCA2 County Summaries](https://www.usgs.gov/data/cmip6-loca2-spatial-summaries-counties-tiger-2023-1950-2100-contiguous-united-states) (HIGH confidence), [ScienceBase Catalog](https://www.sciencebase.gov/catalog/item/673d0719d34e6b795de6b593) (HIGH confidence)

### 4. FEMA NRI Future Risk Index (ARCHIVED -- DO NOT USE)

**Confidence:** LOW -- Data was removed from FEMA website in February 2025. Archived on GitHub by data scientists.

FEMA launched the Future Risk Index (FRI) in December 2024, covering 5 hazards (Coastal Flooding, Drought, Extreme Heat, Hurricane, Wildfire) under multiple emissions scenarios. It was removed from FEMA's website in February 2025 by administration order. An archived version exists at [fulton-ring.github.io/nri-future-risk](https://fulton-ring.github.io/nri-future-risk/).

**Architecture decision:** Do NOT depend on this data source. It is archived, not maintained, and its political status is uncertain. Instead, derive future risk signals from the USGS LOCA2 climate projections (which are maintained by USGS and are not subject to the same removal). This gives us an independent, current source of future climate intelligence.

---

## Component Architecture

### New Components (files to CREATE)

| Component | File Path | Responsibility |
|-----------|-----------|----------------|
| Climate data downloader | `scripts/download_climate_projections.py` | Download USGS LOCA2 county NetCDF, extract summaries to JSON |
| SVI data downloader | `scripts/download_svi_data.py` | Download CDC SVI 2022 county CSV |
| Vulnerability profiler | `scripts/populate_vulnerability.py` | Orchestrate: read NRI expanded + SVI + climate, area-weight per Tribe, write `vulnerability_profiles/` |
| Vulnerability builder | `src/packets/vulnerability.py` | `VulnerabilityProfileBuilder` class (mirrors `HazardProfileBuilder` pattern) |
| Vulnerability model | `src/schemas/vulnerability.py` | Pydantic models for vulnerability profile schema |
| DOCX vulnerability renderer | `src/packets/docx_vulnerability_sections.py` | Render vulnerability sections into DOCX documents |
| Doc E config | `src/packets/doc_types.py` (modify) | `DOC_E` DocumentTypeConfig for standalone vulnerability report |
| Web vulnerability display | `docs/web/js/vulnerability.js` | Render vulnerability summary cards on website |

### Modified Components (files to CHANGE)

| Component | File Path | Change Description |
|-----------|-----------|-------------------|
| Hazard builder | `src/packets/hazards.py` | Extract additional NRI fields (`EAL_VALB/P/A`, `RISK_NPCTL`, `POPULATION`, `BUILDVALUE`) in `_load_nri_county_data()` |
| Path constants | `src/paths.py` | Add `CLIMATE_DIR`, `SVI_DIR`, `VULNERABILITY_PROFILES_DIR`, `CLIMATE_SUMMARY_PATH`, `SVI_COUNTY_PATH` |
| Context dataclass | `src/packets/context.py` | Add `vulnerability_profile: dict` field to `TribePacketContext` |
| Orchestrator | `src/packets/orchestrator.py` | Load vulnerability cache in `_build_context()`, wire to `vulnerability_cache_dir` |
| DOCX engine | `src/packets/docx_engine.py` | Import and call vulnerability section renderers |
| DOCX sections | `src/packets/docx_sections.py` | Expand hazard summary to include EAL component breakdown |
| Doc types | `src/packets/doc_types.py` | Add `DOC_E` definition, add `include_vulnerability: bool` flag to `DocumentTypeConfig` |
| Web index builder | `scripts/build_web_index.py` | Include vulnerability summary fields in `tribes.json` |
| Web app | `docs/web/js/app.js` | Render vulnerability data in Tribe cards |
| Web styles | `docs/web/css/style.css` | Styles for vulnerability visualization components |

### Unchanged Components

| Component | Why Unchanged |
|-----------|--------------|
| `src/scrapers/` (all) | Vulnerability data uses flat files/bulk downloads, not scraped APIs |
| `src/analysis/` | Relevance scoring, change detection unaffected |
| `src/graph/` | Graph schema not impacted by vulnerability data |
| `src/monitors/` | Monitors operate on policy data, not vulnerability metrics |
| `scripts/build_area_crosswalk.py` | Crosswalk already built and reusable as-is for all new data sources |
| `src/packets/docx_hotsheet.py` | Hot sheets not impacted by vulnerability data |
| `src/packets/confidence.py` | Confidence scoring operates on existing context fields |
| `scripts/populate_awards.py` | Award pipeline independent of vulnerability |
| `scripts/build_congress_cache.py` | Congressional pipeline independent of vulnerability |

---

## Data Flow: New Vulnerability Pipeline

### Phase A: Data Acquisition (one-time or periodic refresh)

```
  scripts/download_svi_data.py
    |
    | HTTP GET from svi.cdc.gov (select: Year=2022, Geography=United States,
    |   Geo Type=Counties, File Type=CSV)
    v
  data/svi/SVI2022_US_COUNTY.csv        (~3,200 rows, ~15 MB)


  scripts/download_climate_projections.py
    |
    | HTTP GET from USGS ScienceBase (DOI: 10.5066/P1N9IRWC)
    | Downloads NetCDF county time series files
    | Extracts mid-century (2040-2069) vs baseline (1981-2010) statistics
    | Writes JSON summary keyed by county FIPS
    v
  data/climate/county_climate_summaries.json   (~3,200 entries, ~5-10 MB)


  (NRI CSV already downloaded by existing scripts/download_nri_data.py)
```

### Phase B: Profile Building (after data acquisition)

```
  scripts/populate_vulnerability.py
    |
    +-- Reads data/nri/NRI_Table_Counties.csv     (ALREADY DOWNLOADED)
    |     Extracts expanded NRI fields (EAL components, national percentiles,
    |     population, building value)
    |
    +-- Reads data/svi/SVI2022_US_COUNTY.csv      (NEW)
    |     Extracts RPL_THEMES and 4 theme rankings per county
    |
    +-- Reads data/climate/county_climate_         (NEW)
    |     summaries.json
    |     Extracts mid-century temp change, extreme heat days, heavy precip, etc.
    |
    +-- Reads data/nri/tribal_county_area_         (ALREADY BUILT)
    |     weights.json
    |     Uses IDENTICAL AIANNH-to-county crosswalk and area weights
    |
    +-- For each of 592 Tribes:
    |     1. Look up AIANNH GEOIDs from crosswalk (same as hazards.py)
    |     2. Get county FIPS + normalized area weights
    |     3. Area-weight SVI scores across overlapping counties
    |     4. Area-weight climate projection metrics
    |     5. Combine with expanded NRI data (also area-weighted)
    |     6. Compute composite vulnerability score
    |     7. Atomic write JSON to vulnerability_profiles/epa_*.json
    |
    +-- Generate coverage report
    |     vulnerability_coverage_report.json + .md
    v
  data/vulnerability_profiles/epa_*.json  (592 files, ~5-10 KB each)
  outputs/vulnerability_coverage_report.{json,md}
```

### Phase C: Document Generation (reads only from caches)

```
  PacketOrchestrator._build_context()
    |
    +-- _load_tribe_cache(vulnerability_cache_dir, tribe_id)
    |     Uses IDENTICAL cache loading pattern as awards + hazards
    |
    v
  TribePacketContext.vulnerability_profile = {
    "svi": {
      "overall": 0.72,
      "theme1_socioeconomic": 0.65,
      "theme2_household": 0.58,
      "theme3_minority": 0.81,
      "theme4_housing": 0.43,
    },
    "climate_projections": {
      "scenario": "SSP245",
      "period": "2040-2069",
      "baseline_period": "1981-2010",
      "temp_change_f": 3.2,
      "extreme_heat_days_95f": 28,
      "extreme_heat_days_100f": 8,
      "heavy_precip_days": 5.2,
      "consecutive_dry_days": 18,
      "cooling_degree_days": 1850,
      "heating_degree_days": 4200,
      "precip_change_pct": -8.5,
    },
    "nri_expanded": {
      "eal_buildings": 1234567.89,
      "eal_population": 234567.89,
      "eal_agriculture": 567890.12,
      "risk_national_percentile": 72.3,
      "population": 45000,
      "building_value": 890000000.0,
    },
    "composite_vulnerability": {
      "score": 0.68,
      "rating": "High",
      "components": {
        "hazard_exposure": 0.55,
        "social_vulnerability": 0.72,
        "climate_trajectory": 0.65,
        "adaptive_capacity_deficit": 0.71,
      },
    },
    "generated_at": "2026-02-17T...",
    "data_versions": {
      "nri": "NRI_v1.20",
      "svi": "SVI_2022",
      "climate": "CMIP6-LOCA2",
    },
  }
```

---

## Integration Points with Existing Architecture

### 1. Geographic Crosswalk (REUSE -- zero changes)

The area-weighted AIANNH-to-county crosswalk is the linchpin. All three new data sources key by county FIPS:
- NRI expanded fields: already joined via `STCOFIPS`
- CDC SVI: `FIPS` column (5-digit, same format)
- LOCA2 climate: `GEOID` field (same 5-digit county FIPS)

**No new crosswalk needed.** The `tribal_county_area_weights.json` (built by `scripts/build_area_crosswalk.py`) provides normalized weights for 592 Tribes. The vulnerability builder reuses it exactly as `HazardProfileBuilder` does.

```python
# Existing pattern in hazards.py (lines 569-577):
if geoids and self._area_weights:
    for geoid in geoids:
        entries = self._area_weights.get(geoid, [])
        for entry in entries:
            fips = entry["county_fips"]
            weight = entry["weight"]
            county_weights[fips] = county_weights.get(fips, 0.0) + weight

# IDENTICAL pattern reused in vulnerability.py for SVI, climate, expanded NRI
```

### 2. PacketOrchestrator._build_context() (EXTEND -- minimal changes)

The orchestrator's `_build_context()` method (lines 336-400) loads hazard and award caches via `_load_tribe_cache()`. Adding vulnerability follows the exact same pattern:

```python
# In orchestrator.py __init__() -- add alongside hazard_cache_dir:
raw = packets_cfg.get("vulnerability", {}).get("cache_dir")
self.vulnerability_cache_dir = Path(raw) if raw else VULNERABILITY_PROFILES_DIR
if not self.vulnerability_cache_dir.is_absolute():
    self.vulnerability_cache_dir = PROJECT_ROOT / self.vulnerability_cache_dir

# In _build_context() -- add after hazard_profile loading:
vulnerability_data = self._load_tribe_cache(
    self.vulnerability_cache_dir, tribe_id
)
# ... set on context:
context.vulnerability_profile = vulnerability_data.get("vulnerability", {})
```

The `_load_tribe_cache()` generic method (lines 305-334) already handles:
- Path sanitization (`_sanitize_tribe_id`)
- File existence check
- Size limit enforcement (10 MB cap)
- JSON parse error handling
- Encoding (UTF-8)

Zero new infrastructure needed for cache loading.

### 3. TribePacketContext (EXTEND -- one field addition)

Add one field to the dataclass in `context.py`:

```python
# Vulnerability data (v1.4)
vulnerability_profile: dict = field(default_factory=dict)
```

This follows the pattern of `hazard_profile`, `awards`, `economic_impact`, and `congressional_intel` -- all are `dict` fields populated by the orchestrator.

### 4. DocxEngine (EXTEND -- add renderer calls)

The engine's `generate()` method calls section renderers in sequence. Adding vulnerability sections follows the existing pattern:

```python
from src.packets.docx_vulnerability_sections import (
    render_vulnerability_overview,
    render_climate_projections_section,
    render_svi_breakdown,
    render_vulnerability_synthesis,
)

# In generate() method, after hazard summary, before structural asks:
if context.vulnerability_profile:
    render_vulnerability_overview(document, context, style_manager, doc_type_config)
    render_climate_projections_section(document, context, style_manager)
    render_svi_breakdown(document, context, style_manager, doc_type_config)
```

### 5. Document Types (EXTEND -- add DOC_E and include_vulnerability flag)

Add `DOC_E` for standalone vulnerability report. Follow frozen dataclass pattern:

```python
DOC_E = DocumentTypeConfig(
    doc_type="E",
    audience="internal",
    scope="tribal",
    title_template="FY26 Climate Vulnerability Assessment",
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
)
```

Adding `include_vulnerability: bool` to `DocumentTypeConfig` requires care because it is `@dataclass(frozen=True)`. Add the field with a default of `False` to maintain backward compatibility with existing DOC_A through DOC_D:

```python
include_vulnerability: bool = False  # True only for DOC_E
```

For Doc A and Doc B: vulnerability data renders as a SUBSECTION of the existing hazard summary (compact). For Doc E: vulnerability data renders as the PRIMARY content with full detail.

### 6. Website (EXTEND -- add vulnerability display to Tribe cards)

The `tribes.json` index (built by `scripts/build_web_index.py`) currently includes name, states, ecoregion, document links, and freshness. Adding vulnerability summary fields:

```json
{
  "tribe_id": "epa_100000001",
  "name": "Absentee-Shawnee Tribe...",
  "states": ["OK"],
  "vulnerability": {
    "score": 0.68,
    "rating": "High",
    "svi_overall": 0.72,
    "top_climate_risk": "Extreme Heat (+28 days >95F by 2050)",
    "top_hazard": "Ice Storm"
  },
  "documents": { ... }
}
```

The website card rendering in `app.js` extends to display a vulnerability badge/summary alongside the existing state/ecoregion info. No new JS framework needed -- vanilla DOM manipulation as per existing pattern.

---

## New Data Directory Structure

```
data/
  nri/                              # EXISTING (unchanged)
    NRI_Table_Counties.csv          # EXISTING (already downloaded)
    tribal_county_area_weights.json # EXISTING (already built, REUSED)
    aiannh/                         # EXISTING (shapefiles)
    county/                         # EXISTING (shapefiles)

  svi/                              # NEW
    SVI2022_US_COUNTY.csv           # ~3,200 rows, county-level, ~15 MB

  climate/                          # NEW
    loca2_raw/                      # Raw NetCDF downloads (temporary, deletable)
    county_climate_summaries.json   # Processed: county FIPS -> projection stats

  hazard_profiles/                  # EXISTING (592 files, EXPANDED schema)
    epa_100000001.json              # Existing fields + expanded NRI metrics
    ...

  vulnerability_profiles/           # NEW (592 files)
    epa_100000001.json              # SVI + climate projections + composite score
    ...

  award_cache/                      # EXISTING (unchanged)
  packet_state/                     # EXISTING (unchanged)
```

### Why Separate vulnerability_profiles/ Instead of Expanding hazard_profiles/

1. **Data isolation** -- Vulnerability data updates on a different cadence than hazard data (SVI is biannual, climate projections are static, NRI is annual)
2. **Independent validation** -- Can validate vulnerability coverage separately
3. **Backward compatibility** -- Existing hazard profiles keep working during migration; 964 existing tests remain unaffected
4. **Incremental deployment** -- Can ship expanded NRI in hazard profiles AND add vulnerability profiles without coupling
5. **Schema clarity** -- Vulnerability profile has a fundamentally different structure (SVI themes, climate projections, composite score) vs hazard profile (NRI hazards + USFS wildfire)
6. **Size management** -- Keeping profiles separate keeps each under the 10 MB cache limit

### Why EXPAND hazard_profiles/ for NRI Fields

The additional NRI fields (EAL breakdown, national percentiles, demographics) are extensions of data already extracted from the SAME CSV. They use the SAME area-weighting logic. They belong in the existing profile structure:

```json
{
  "sources": {
    "fema_nri": {
      "composite": {
        "risk_score": 55.47,
        "eal_total": 27544487.08,
        "eal_buildings": 18234567.00,   // NEW
        "eal_population": 5234567.00,   // NEW
        "eal_agriculture": 4075353.08,  // NEW
        "risk_national_percentile": 72.3, // NEW
        "population": 45000,            // NEW
        "building_value": 890000000.0,  // NEW
        ...existing fields...
      }
    }
  }
}
```

---

## New paths.py Constants

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


def vulnerability_profile_path(tribe_id: str) -> Path:
    """Return the vulnerability profile JSON path for a specific Tribe."""
    return VULNERABILITY_PROFILES_DIR / f"{tribe_id}.json"
```

---

## Composite Vulnerability Score Design

The composite vulnerability score synthesizes four dimensions into a single 0-1 metric:

```
Composite Vulnerability = weighted average of:

  (1) Hazard Exposure (weight 0.30):
      NRI composite risk national percentile / 100
      Source: FEMA NRI RISK_NPCTL field

  (2) Social Vulnerability (weight 0.25):
      CDC SVI RPL_THEMES (already 0-1 scale)
      Source: CDC/ATSDR SVI 2022

  (3) Climate Trajectory (weight 0.25):
      Normalized projection severity index combining:
        - Temperature change (degrees F, normalized 0-1 by max observed)
        - Extreme heat days increase (normalized 0-1)
        - Heavy precipitation change (normalized 0-1)
      Source: USGS LOCA2/CMIP6 county summaries

  (4) Adaptive Capacity DEFICIT (weight 0.20):
      1 - (NRI RESL_SCORE / 100)
      Inverted because low resilience = high vulnerability
      Source: FEMA NRI RESL_SCORE field
```

**Rating thresholds** (same quintile approach as NRI `score_to_rating()`):
- Very High: >= 0.80
- High: >= 0.60
- Moderate: >= 0.40
- Low: >= 0.20
- Very Low: < 0.20

**Why these weights:**
- Hazard exposure (0.30) gets highest weight because it reflects immediate, measurable risk from observed hazard data
- Social vulnerability (0.25) amplifies hazard impacts on populations with fewer resources
- Climate trajectory (0.25) captures worsening future conditions
- Adaptive capacity deficit (0.20) gets lowest weight because NRI RESL data is the coarsest input (derived from fewer variables)

**Important caveat for documents:** Every Tribe has unique circumstances (Traditional Knowledge, governance capacity, cultural resilience) that no federal dataset captures. Frame composite scores as "based on available federal datasets" with explicit caveats. The composite score is a starting point for conversation, not a verdict on Tribal vulnerability. Sovereignty is the innovation.

---

## Suggested Build Order

### Layer 1: Data Foundation (no rendering, no docs)

**Build first because everything else depends on data being available.**

```
Step 1: Expand NRI extraction in hazards.py
  MODIFY: src/packets/hazards.py (_load_nri_county_data, _build_tribe_nri_profile)
  ADD: EAL_VALB, EAL_VALP, EAL_VALA, RISK_NPCTL, POPULATION, BUILDVALUE
  TEST: Regenerate hazard_profiles/ with expanded data, verify schema
  RISK: Very Low (same CSV, same parsing logic, same aggregation)
  DEPENDENCIES: None

Step 2: Download + parse CDC SVI
  CREATE: scripts/download_svi_data.py
  ACTION: HTTP download of SVI2022_US_COUNTY.csv (~15 MB)
  ACTION: Parse CSV, validate FIPS column, county count
  RISK: Low (well-documented CSV, single download)
  DEPENDENCIES: None (can run in parallel with Step 1)

Step 3: Download + extract LOCA2 climate projections
  CREATE: scripts/download_climate_projections.py
  ACTION: Download NetCDF from USGS ScienceBase
  ACTION: Extract mid-century (2040-2069) vs baseline (1981-2010) summaries
  ACTION: Write county_climate_summaries.json keyed by FIPS
  RISK: MEDIUM (NetCDF format, multi-scenario, large files, Alaska gap)
  NEEDS DEEPER RESEARCH: NetCDF parsing approach, xarray vs netCDF4,
    file sizes, Alaska borough handling
  DEPENDENCIES: None (can run in parallel with Steps 1-2)

Step 4: Build vulnerability profiles
  CREATE: src/packets/vulnerability.py (VulnerabilityProfileBuilder)
  CREATE: scripts/populate_vulnerability.py
  CREATE: src/schemas/vulnerability.py (Pydantic models)
  ACTION: Read expanded NRI + SVI + climate + area crosswalk
  ACTION: Area-weight all data sources per Tribe (reuse crosswalk)
  ACTION: Compute composite vulnerability score
  ACTION: Write 592 vulnerability_profiles/epa_*.json
  ACTION: Generate coverage report
  RISK: Low (follows HazardProfileBuilder pattern exactly)
  DEPENDENCIES: Steps 1, 2, 3 must complete first
```

### Layer 2: Pipeline Integration (wiring, no rendering)

**Build second because rendering needs populated context.**

```
Step 5: Extend src/paths.py with new constants
  ADD: SVI_DIR, SVI_COUNTY_PATH, CLIMATE_DIR, CLIMATE_SUMMARY_PATH,
       VULNERABILITY_PROFILES_DIR, vulnerability_profile_path()
  RISK: Very Low (no logic changes, just path definitions)

Step 6: Extend TribePacketContext
  MODIFY: src/packets/context.py
  ADD: vulnerability_profile: dict = field(default_factory=dict)
  RISK: Very Low (one line addition to dataclass)

Step 7: Extend PacketOrchestrator._build_context()
  MODIFY: src/packets/orchestrator.py
  ADD: vulnerability_cache_dir in __init__()
  ADD: vulnerability loading in _build_context()
  RISK: Low (follows exact pattern of hazard/award cache loading)

Step 8: Add _display_vulnerability_summary() to orchestrator
  MODIFY: src/packets/orchestrator.py
  ADD: CLI display of vulnerability data (mirrors _display_hazard_summary)
  RISK: Very Low (display-only method)
```

### Layer 3: Document Rendering

**Build third. Data is available, context is populated, now render it.**

```
Step 9: Create docx_vulnerability_sections.py
  CREATE: src/packets/docx_vulnerability_sections.py
  IMPLEMENT:
    - render_vulnerability_overview() -- composite score, rating, data sources
    - render_climate_projections_section() -- temp change, extreme days, table
    - render_svi_breakdown() -- 4-theme breakdown with percentile bars
    - render_vulnerability_synthesis() -- narrative combining all data
  RISK: Medium (new rendering code, but follows docx_sections.py patterns)

Step 10: Integrate into existing Doc A/B sections
  MODIFY: src/packets/docx_engine.py (add vulnerability renderer imports/calls)
  MODIFY: src/packets/docx_sections.py (expand hazard summary with EAL breakdown)
  RISK: Low (additive changes, no existing section removal)

Step 11: Create Doc E (standalone vulnerability assessment)
  MODIFY: src/packets/doc_types.py (add DOC_E, add include_vulnerability flag)
  MODIFY: src/packets/orchestrator.py (wire DOC_E into generate_tribal_docs)
  RISK: Medium (new document type, but follows DOC_A-D pattern exactly)

Step 12: Extend regional docs (Doc C/D) with vulnerability aggregation
  MODIFY: src/packets/docx_regional_sections.py
  ADD: render_regional_vulnerability_synthesis()
  RISK: Medium (regional aggregation of vulnerability is new logic --
    averaging per-Tribe composite scores across a region)
```

### Layer 4: Website + Polish

**Build last. Everything works in documents first.**

```
Step 13: Extend build_web_index.py to include vulnerability data
  MODIFY: scripts/build_web_index.py
  ADD: Load vulnerability profiles, extract summary fields for tribes.json
  RISK: Low (follows existing pattern of loading hazard/award data)

Step 14: Extend app.js to render vulnerability cards
  MODIFY: docs/web/js/app.js
  ADD: Vulnerability badge/summary in Tribe card UI
  RISK: Low (vanilla JS DOM manipulation, follows existing card pattern)

Step 15: Add vulnerability CSS styles
  MODIFY: docs/web/css/style.css
  ADD: Styles for vulnerability indicators, rating badges, color coding
  RISK: Very Low (CSS only)

Step 16: Coverage validation + comprehensive testing
  ADD: Vulnerability coverage checks to validate_coverage.py
  ADD: Tests for VulnerabilityProfileBuilder
  ADD: Tests for docx_vulnerability_sections.py
  ADD: Tests for Doc E generation
  ADD: Integration tests for full pipeline
  RISK: Low (testing, not new feature development)
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Modifying hazard_profiles/ Schema for SVI/Climate

**What:** Cramming SVI themes and climate projections into the existing `hazard_profiles/epa_*.json` files.
**Why bad:** Hazard profiles have a well-established schema (`sources.fema_nri` + `sources.usfs_wildfire`). Adding completely different data structures creates schema confusion, makes independent updating impossible, and risks breaking 964 existing tests that validate hazard profile structure.
**Instead:** Create separate `vulnerability_profiles/` directory with its own schema. The orchestrator loads both caches independently. Expanded NRI fields (EAL breakdown, etc.) DO go in hazard_profiles because they extend the existing NRI data structure.

### Anti-Pattern 2: Calling APIs During Document Generation

**What:** Making SVI or climate data API calls inside `DocxEngine.generate()` or section renderers.
**Why bad:** The pipeline generates 592 x 2+ documents. API calls during generation would be O(1000+) HTTP requests, would fail in offline environments, and would violate the zero-API-during-docgen architectural invariant.
**Instead:** Pre-cache everything. The `populate_vulnerability.py` script runs BEFORE document generation. DocxEngine reads ONLY from local JSON caches.

### Anti-Pattern 3: Different Crosswalk for Different Data Sources

**What:** Building a separate geographic crosswalk for SVI-to-Tribe or climate-to-Tribe mapping.
**Why bad:** The existing area-weighted AIANNH-to-county crosswalk required significant engineering (dual CRS projection, geopandas overlays, sliver filtering, weight normalization). Building a second crosswalk would duplicate effort and potentially produce inconsistent geographic mappings.
**Instead:** ALL county-level data sources join through the ONE existing crosswalk (`tribal_county_area_weights.json`). SVI, NRI, and LOCA2 all key by 5-digit county FIPS. One source of geographic truth.

### Anti-Pattern 4: Over-Engineering Climate Projection Aggregation

**What:** Processing all 27 GCMs x 3 SSP scenarios x 150 years of data for each county.
**Why bad:** The LOCA2 dataset is massive (potentially gigabytes of NetCDF). Processing all of it for a Tribal advocacy document is overkill and would make the download/processing pipeline prohibitively slow.
**Instead:** Pick ONE scenario (SSP245 = mid-range emissions, defensible choice) and ONE period (2040-2069 = mid-century). Pre-extract the 5-7 most relevant metrics (extreme heat days, heavy precip, temp change, CDD, HDD, consecutive dry days). Store as a simple JSON dict per county (~3,200 entries), then area-weight. Multi-model median across all 27 GCMs for robustness.

### Anti-Pattern 5: Making Composite Score Appear Authoritative

**What:** Presenting the composite vulnerability score as THE definitive measure of a Tribe's vulnerability without caveat.
**Why bad:** Every Tribal Nation has unique circumstances -- Traditional Knowledge, governance capacity, cultural resilience, treaty rights -- that no federal dataset captures. A data-derived score from CDC/FEMA/NOAA reflects federal data availability, not Tribal reality.
**Instead:** Frame scores as "based on available federal datasets." Include explicit caveats. Label the composite clearly as a screening tool, not a determination. Honor sovereignty in framing.

### Anti-Pattern 6: Coupling Doc E Generation to Doc A/B

**What:** Making Doc E generation depend on Doc A or Doc B being generated first, or vice versa.
**Why bad:** Creates fragile ordering dependencies. If Doc A fails for a Tribe, Doc E should still generate.
**Instead:** Each document type reads independently from TribePacketContext. The orchestrator populates context once, then generates each doc type independently. Failed generation of one doc type does not block others.

---

## Scalability Considerations

| Concern | Current (592 Tribes) | Notes |
|---------|---------------------|-------|
| Vulnerability profile build time | ~2-5 minutes (all 592) | Bounded by county count (~3,200), not Tribe count |
| Profile file size | ~5-10 KB per Tribe | Well within 10 MB cache limit |
| Memory during build | ~200-300 MB (NRI CSV + SVI CSV + climate JSON in memory) | Manageable on any modern dev machine |
| NetCDF download size | ~500 MB - 2 GB (one-time) | Download once, extract summaries, can delete raw NetCDF |
| SVI download size | ~15 MB (one-time) | Trivial |
| Website index growth | tribes.json ~2 MB currently | +vulnerability fields adds ~20% -> ~2.4 MB |
| Doc generation time | ~1.5 min for 592 Tribes x 2 docs | Vulnerability sections add ~0.1s per doc |
| Total doc generation with Doc E | ~3 min for 592 x 3 docs | Linear scaling, acceptable |

---

## New Python Dependencies

| Package | Purpose | Version | Notes |
|---------|---------|---------|-------|
| `xarray` | NetCDF file reading | >=2024.1 | For LOCA2 climate data extraction only |
| `netCDF4` | NetCDF backend for xarray | >=1.6 | Required by xarray for .nc file format |

**Note:** `geopandas`, `openpyxl`, `requests`, and other data packages are already in requirements.txt. The `xarray`/`netCDF4` dependency is isolated to `scripts/download_climate_projections.py` -- it is NOT needed for document generation or the main pipeline. Consider making it an optional dependency (`pip install tcr-policy-scanner[climate]`).

No new JavaScript dependencies needed. Website uses vanilla JS + Fuse.js 7.1.0.

---

## Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| LOCA2 NetCDF format complexity | Medium | Medium | Research xarray parsing patterns during Phase 1 Step 3; have CSV fallback plan |
| Alaska coverage gap in LOCA2 | Medium | HIGH | LOCA2 = CONUS only; accept partial coverage for AK Tribes, flag in reports |
| CDC SVI download URL changes | Low | Low | URL pattern has been stable since 2014; add URL to config for flexibility |
| NRI version update breaks parsing | Low | Low | Column names stable across v1.17-v1.20; version detection already implemented |
| Composite score framing concerns | High | Medium | Work with Tribal partners on framing; explicit caveats in all documents |
| Doc E scope creep | Medium | Medium | Define Doc E as VULNERABILITY-ONLY; resist adding economic/congressional content |

---

## Sources

**Direct codebase inspection (HIGH confidence):**
- `src/packets/hazards.py` -- HazardProfileBuilder, NRI field extraction, area-weighted aggregation
- `src/packets/orchestrator.py` -- PacketOrchestrator, _build_context(), _load_tribe_cache()
- `src/packets/context.py` -- TribePacketContext dataclass structure
- `src/packets/doc_types.py` -- DocumentTypeConfig frozen dataclass, DOC_A-D definitions
- `src/packets/docx_engine.py` -- DocxEngine render pipeline
- `src/packets/docx_sections.py` -- Section renderer function signatures
- `scripts/build_area_crosswalk.py` -- Geographic crosswalk architecture
- `scripts/populate_hazards.py` -- Hazard population pipeline
- `src/paths.py` -- Centralized path constants (35 constants)
- `data/hazard_profiles/epa_100000001.json` -- Existing hazard profile JSON schema
- `docs/web/js/app.js` -- Website rendering approach
- `docs/web/index.html` -- Website structure

**Verified external sources (HIGH confidence):**
- [FEMA NRI Data Resources](https://www.fema.gov/about/openfema/data-sets/national-risk-index-data) -- NRI v1.20, CSV format, field availability
- [CDC/ATSDR SVI Data Download](https://svi.cdc.gov/dataDownloads/data-download.html) -- SVI 2022, county CSV, theme structure
- [CDC/ATSDR SVI 2022 Documentation](https://www.atsdr.cdc.gov/place-health/media/pdfs/2024/10/SVI2022Documentation.pdf) -- RPL_THEMES, 4 themes, variable definitions
- [USGS CMIP6-LOCA2 County Summaries](https://www.usgs.gov/data/cmip6-loca2-spatial-summaries-counties-tiger-2023-1950-2100-contiguous-united-states) -- LOCA2 county time series, NetCDF format
- [USGS ScienceBase LOCA2 Catalog](https://www.sciencebase.gov/catalog/item/673d0719d34e6b795de6b593) -- Data access, GEOID keying, 27 GCMs

**External sources (LOW confidence, use with caution):**
- [Archived FEMA Future Risk Index](https://fulton-ring.github.io/nri-future-risk/) -- Removed from FEMA, not recommended as data source
