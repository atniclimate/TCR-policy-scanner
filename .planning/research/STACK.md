# Technology Stack: Climate Vulnerability Data Integration

**Project:** TCR Policy Scanner v1.4 -- Climate Vulnerability Intelligence
**Researched:** 2026-02-17
**Overall confidence:** MEDIUM-HIGH

## Executive Summary

This milestone adds three new data sources (NOAA CMIP6-LOCA2 climate projections, CDC/ATSDR Social Vulnerability Index, expanded FEMA NRI fields) and produces a new standalone vulnerability report document. The existing stack (Python 3.12, geopandas, python-docx, JSON caches) handles the integration pattern well. The primary stack addition is **xarray + netCDF4** for processing USGS LOCA2 county-level climate projection data, which ships as NetCDF files. CDC SVI and expanded NRI data are both CSV -- no new libraries needed for those. Sea level rise data requires careful scoping to avoid overengineering.

---

## Data Sources: Access Methods and Formats

### Source 1: USGS CMIP6-LOCA2 County Spatial Summaries

**What it is:** Statistically downscaled CMIP6 climate projections pre-aggregated to US county boundaries using Census 2023 TIGER/Line shapefiles. 27 climate models, 3 SSP scenarios (ssp245, ssp370, ssp585), monthly resolution, 1950-2100.

| Attribute | Value |
|-----------|-------|
| Provider | USGS via ScienceBase |
| ScienceBase ID | `673d0719d34e6b795de6b593` |
| DOI | `10.5066/P1N9IRWC` |
| Format | NetCDF (.nc) |
| Total download | ~9.1 GB (7 files) |
| Key file | `CMIP6-LOCA2_1950-2100_County2023_monthly.nc` (2.17 GB) |
| Thresholds file | `CMIP6-LOCA2_Thresholds_1950-2100_County2023_annual.nc` (1.74 GB) |
| County ID field | `GEOID` (matches Census FIPS, same as existing NRI `STCOFIPS`) |
| Variables | Temperature (tasmax, tasmin), precipitation (pr), threshold exceedances, extreme event metrics |
| Scenarios | SSP2-4.5, SSP3-7.0, SSP5-8.5 |
| Models | 27 CMIP6 GCMs (ACCESS-CM2, CESM2-LENS, GFDL-CM4, etc.) |
| Pre-computed means | Weighted Multi-Model Mean (WMMM) and Multi-Model Mean (MMM) included |
| Climatology periods | 1981-2010 (baseline), 2025-2049, 2050-2074, 2075-2099 |
| API key required | No (public ScienceBase download) |
| Confidence | HIGH (verified ScienceBase catalog page directly) |

**Why this source:** Pre-aggregated to county level eliminates the need to process raw 6km gridded LOCA2 data (~100+ GB). Counties use GEOID field that matches our existing STCOFIPS-based crosswalk. Pre-computed multi-model means eliminate the need to do ensemble averaging ourselves.

**Integration pattern:** Download NetCDF files once via script. Use xarray to extract county-level climatology summaries for future time periods (2025-2049, 2050-2074, 2075-2099) relative to historical baseline (1981-2010). Compute deltas (projected change from baseline). Write per-county climate projection JSON. Bridge to Tribes via existing `tribal_county_area_weights.json` crosswalk with area-weighted averaging.

**Alternative considered:** NOAA Climate Explorer (drought.gov/data-maps-tools/climate-explorer) provides county-level projections with interactive UI, but lacks bulk download API. The USGS ScienceBase dataset is the authoritative bulk-downloadable source derived from the same underlying LOCA2 data.

### Source 2: CDC/ATSDR Social Vulnerability Index (SVI) 2022

**What it is:** Census-derived social vulnerability rankings for all US counties and census tracts, based on 16 ACS variables grouped into 4 themes. Percentile rankings 0-1 (higher = more vulnerable).

| Attribute | Value |
|-----------|-------|
| Provider | CDC/ATSDR GRASP |
| Download page | `svi.cdc.gov/dataDownloads/data-download.html` |
| Alt download | `atsdr.cdc.gov/place-health/php/svi/svi-data-documentation-download.html` |
| Format | CSV (also available as ESRI Geodatabase) |
| Geographic levels | County, Census Tract, ZCTA (2022 only) |
| Latest year | 2022 (released May 2024) |
| County ID field | `FIPS` (5-digit, text with leading zeros) |
| State field | `ST_ABBR` |
| Confidence | HIGH (verified CDC download page directly) |

**Key SVI 2022 columns (verified from documentation):**

| Column prefix | Meaning |
|---------------|---------|
| `E_` | Estimate (raw census value) |
| `M_` | Margin of error |
| `EP_` | Percentile of estimate |
| `EPL_` | Percentile ranking (0-1) |
| `SPL_THEME1` | Sum of percentile rankings for Theme 1 |
| `RPL_THEME1` | Percentile ranking for Theme 1: Socioeconomic Status |
| `RPL_THEME2` | Percentile ranking for Theme 2: Household Characteristics |
| `RPL_THEME3` | Percentile ranking for Theme 3: Racial & Ethnic Minority Status |
| `RPL_THEME4` | Percentile ranking for Theme 4: Housing Type & Transportation |
| `RPL_THEMES` | Overall SVI percentile ranking (0-1) |
| `F_THEME1` through `F_THEMES` | Flag variables (1 = 90th percentile or above) |

**Null value:** `-999` indicates no data.

**Integration pattern:** Download CSV once via script (manual download from CDC web interface -- no programmatic API, no stable direct URL pattern found). Parse with Python `csv` module (same pattern as NRI). Key by `FIPS` code. Bridge to Tribes via existing county crosswalk with area-weighted averaging. Store per-Tribe SVI summary in vulnerability profile JSON.

**Why this is valuable:** Provides social vulnerability context distinct from FEMA NRI's built-in `SOVI_SCORE`. The CDC SVI uses different census variables and methodology. Together they give a more complete vulnerability picture: NRI SOVI measures social vulnerability in terms of disaster impact amplification, while CDC SVI measures broader community vulnerability to external stresses. For Tribal Nations, combining both provides the strongest advocacy basis for funding justification.

### Source 3: Expanded FEMA NRI Data (Already Partially Integrated)

**What it is:** The same NRI CSV already used (`NRI_Table_Counties.csv`) contains fields we are not yet extracting. No new download needed.

| Attribute | Value |
|-----------|-------|
| Provider | FEMA |
| Current version | v1.20 (December 2025) |
| Format | CSV (already downloaded to `data/nri/`) |
| Confidence | HIGH (verified from existing codebase) |

**Fields already extracted (from `hazards.py` lines 355-387):**

| Field | Description | How Used |
|-------|-------------|----------|
| `STCOFIPS` | County FIPS code | Key field |
| `RISK_SCORE` | Composite Risk Index score | Area-weighted average |
| `RISK_RATNG` | Risk Index rating (text) | Display |
| `RISK_VALUE` | Risk Index value | Display |
| `EAL_VALT` | Expected Annual Loss total ($) | Area-weighted sum |
| `EAL_SCORE` | Expected Annual Loss score | Area-weighted average |
| `EAL_RATNG` | Expected Annual Loss rating | Display |
| `SOVI_SCORE` | Social Vulnerability score | Area-weighted average |
| `SOVI_RATNG` | Social Vulnerability rating | Display |
| `RESL_SCORE` | Community Resilience score | Area-weighted average |
| `RESL_RATNG` | Community Resilience rating | Display |
| `{HAZCODE}_RISKS` | Per-hazard risk score | Area-weighted average |
| `{HAZCODE}_RISKR` | Per-hazard risk rating | Display |
| `{HAZCODE}_EALT` | Per-hazard EAL total | Area-weighted sum |
| `{HAZCODE}_AFREQ` | Annualized frequency | Area-weighted average |
| `{HAZCODE}_EVNTS` | Number of events | Area-weighted sum |

**Fields to ADD (same CSV, zero new downloads):**

| Field | Description | Why Add |
|-------|-------------|---------|
| `EAL_VALB` | EAL - Building value ($) | Breakdown of loss by type for vulnerability narrative |
| `EAL_VALP` | EAL - Population value ($) | Breakdown of loss by type |
| `EAL_VALA` | EAL - Agriculture value ($) | Relevant for rural Tribal Nations |
| `EAL_VALPE` | EAL - Population equivalence | Normalized comparison metric |
| `RESL_VALUE` | Community Resilience raw value | More granular than rating alone |
| `SOVI_VALUE` | Social Vulnerability raw value | More granular than rating alone |
| `RISK_NPCTL` | Risk Index national percentile | National ranking context |
| `EAL_NPCTL` | EAL national percentile | National ranking context |
| `SOVI_NPCTL` | SOVI national percentile | National ranking context |
| `RESL_NPCTL` | RESL national percentile | National ranking context |
| `{HAZCODE}_EALB` | Per-hazard EAL buildings ($) | Detailed loss analysis per hazard |
| `{HAZCODE}_EALP` | Per-hazard EAL population ($) | Detailed loss analysis per hazard |
| `{HAZCODE}_EALA` | Per-hazard EAL agriculture ($) | Detailed loss analysis per hazard |
| `{HAZCODE}_EXPT` | Per-hazard exposure total ($) | Exposure vs. loss comparison |

**Note on field names:** The exact names above follow NRI v1.18 naming patterns confirmed in the existing codebase. FEMA NRI v1.20 (December 2025) may have added or renamed fields. **LOW confidence on exact v1.20 field names for the NEW fields** -- verify against the actual CSV headers when downloaded. The fields already in `hazards.py` are confirmed correct.

**Integration pattern:** Extend `_load_nri_county_data()` in `hazards.py` to extract additional fields from the same CSV already being parsed. No new data download. No new libraries. Pure code change.

### Source 4: Sea Level Rise Projections

**What it is:** NOAA/Interagency 2022 Sea Level Rise Technical Report provides projections to 2150 at tide gauge stations and 1-degree coastal grid cells. Five scenarios: Low (0.3m), Intermediate-Low (0.5m), Intermediate (1.0m), Intermediate-High (1.5m), High (2.0m) by 2100.

| Attribute | Value |
|-----------|-------|
| Provider | NOAA/Interagency Task Force |
| Download | `earth.gov/sealevel/us/resources/2022-sea-level-rise-technical-report/` |
| Interactive tool | NASA Interagency Sea Level Rise Scenario Tool (`sealevel.nasa.gov/data_tools/18`) |
| Format | ZIP archive with CSV data inside (not confirmed -- MEDIUM confidence) |
| Resolution | Tide gauge stations + 1-degree grid (NOT county-level) |
| Scenarios | Low, Int-Low, Intermediate, Int-High, High |
| Projections | By decade, 2020-2150 |
| Confidence | MEDIUM (exact download format not verified) |

**RECOMMENDATION: Scope sea level rise carefully.** This data is NOT county-level. It would require spatial joining from coastal grid/station points to counties, then bridging to Tribes via the existing crosswalk. Only ~200 of 592 Tribes are in coastal or near-coastal counties. Consider these options:

- **Option A (recommended for MVP):** Use pre-baked FEMA NRI coastal flooding hazard data (`CFLD_*` fields) already in the NRI CSV as a proxy for sea level risk. Already integrated. Just surface it more prominently in the vulnerability report.
- **Option B (if differentiator needed):** Download the NOAA SLR scenario data, spatially join to coastal counties, and integrate. Adds complexity but provides forward-looking projections that NRI does not have.
- **Option C (defer):** Defer sea level rise projections to a future milestone entirely.

---

## Recommended Stack Additions

### New Dependencies (pip install)

| Library | Version | Purpose | Why This Library |
|---------|---------|---------|-----------------|
| `xarray` | `>=2025.12.0` | Read and slice NetCDF climate data | Standard for multi-dimensional labeled data in Python. Required to read USGS LOCA2 county NetCDF files. Calendar-versioned; 2026.1.0 is latest as of Feb 2026. |
| `netCDF4` | `>=1.7.3` | NetCDF4 file I/O backend for xarray | Required by xarray for reading NetCDF4 files. v1.7.4 (Jan 2026) is latest. Provides HDF5-based compressed storage. Pre-built wheels available for Windows/Linux/macOS. |

**That is the complete list.** Two libraries. Everything else reuses the existing stack.

### Why Only Two New Libraries

| Capability Needed | Library | Already in Stack? |
|-------------------|---------|-------------------|
| CSV parsing (SVI, expanded NRI) | `csv` (stdlib) | Yes (built-in) |
| JSON cache writes | `json` (stdlib) | Yes (built-in) |
| HTTP downloads | `requests` | Yes (requirements.txt) |
| Geographic crosswalk | `geopandas` + existing `tribal_county_area_weights.json` | Yes |
| DOCX generation | `python-docx` | Yes |
| Data validation | `pydantic` | Yes |
| Fuzzy matching (Tribe names) | `rapidfuzz` | Yes |
| Excel reading (USFS) | `openpyxl` | Yes |
| Date handling | `python-dateutil` | Yes |
| Area-weighted aggregation | Existing code in `hazards.py` | Yes |
| Per-Tribe profile generation | Existing pattern in `populate_hazards.py` | Yes |

### What NOT to Add (and Why)

| Library | Why NOT |
|---------|---------|
| `scipy` | No spatial interpolation needed -- LOCA2 data is pre-aggregated to counties |
| `rioxarray` | No raster/GeoTIFF operations -- we work with tabular county summaries, not gridded data |
| `regionmask` | No spatial masking needed -- county aggregation already done by USGS |
| `dask` | Dataset fits in memory (~2 GB for the monthly file; we extract summary stats, not full timeseries). xarray uses lazy loading by default. |
| `h5py` | netCDF4 handles HDF5 backend already |
| `sciencebasepy` | The USGS ScienceBase Python SDK is for catalog browsing; we just need direct HTTP download of known URLs via `requests` |
| `pandas` | Already an implicit dependency via geopandas; no need to add explicitly |
| `matplotlib` / `plotly` | No chart generation in the pipeline; DOCX and website handle visualization |
| `xclim` | We consume pre-computed climate summaries, not raw daily data needing climate index calculation |
| `climate_indices` | Same as xclim -- pre-computed data eliminates the need |
| `cdsapi` / `ecmwflibs` | Copernicus/ECMWF APIs -- not needed; USGS ScienceBase provides LOCA2 data |
| `cfgrib` | GRIB format reader -- LOCA2 county data is NetCDF, not GRIB |

---

## Integration Architecture

### Data Flow (Extending Existing Patterns)

```
scripts/download_climate_data.py         (NEW)
  -> downloads LOCA2 NetCDF from ScienceBase via requests
  -> downloads CDC SVI CSV (manual step documented)
  -> saves to data/climate/ and data/svi/

scripts/process_climate_projections.py   (NEW)
  -> reads LOCA2 NetCDF via xarray
  -> extracts county climatology summaries (baseline + future periods)
  -> computes deltas (change from historical baseline)
  -> writes data/climate/county_climate_projections.json

scripts/process_svi_data.py              (NEW)
  -> reads CDC SVI county CSV via csv module
  -> extracts RPL_THEMES and 4 theme rankings per county
  -> writes data/svi/county_svi.json

src/packets/hazards.py                   (MODIFY - extend _load_nri_county_data)
  -> extract additional NRI fields (EAL breakdown, percentiles)
  -> no new data download needed

scripts/build_vulnerability_profiles.py  (NEW)
  -> reads:
     - existing hazard_profiles/ (NRI + USFS per Tribe)
     - county_climate_projections.json
     - county_svi.json
     - tribal_county_area_weights.json (existing crosswalk)
  -> computes area-weighted vulnerability profile per Tribe
  -> writes data/vulnerability_profiles/{tribe_id}.json (592 files)

src/packets/vulnerability.py             (NEW)
  -> reads vulnerability profile JSON per Tribe
  -> provides data to DocxEngine for vulnerability report doc type
```

### Key Integration Points

1. **County FIPS as universal join key:**
   - NRI: `STCOFIPS` (already used, confirmed in `hazards.py` line 355)
   - SVI: `FIPS` (same 5-digit format, verified from CDC docs)
   - LOCA2: `GEOID` (same 5-digit format, Census TIGER 2023, verified from ScienceBase)
   - Crosswalk: `tribal_county_area_weights.json` maps AIANNH GEOID -> county FIPS with weights

2. **Area-weighted aggregation (existing pattern from `hazards.py`):**
   - Dollar values (EAL): weighted sum
   - Scores/percentiles (RISK_SCORE, SOVI_SCORE, RESL_SCORE, RPL_THEMES): weighted average
   - Climate deltas (temperature change, precipitation change): weighted average
   - SVI rankings: weighted average
   - Resilience: weighted average (report min for worst-case resilience)

3. **JSON cache pattern (existing pattern):**
   - Each data source produces a county-level JSON cache (processing step)
   - Per-Tribe profiles combine county data via crosswalk (build step)
   - Document generation reads only from per-Tribe JSON (zero API/file access)

4. **Build-time vs. runtime separation (existing pattern):**
   - `xarray` and `netCDF4` are build-time only (like `geopandas`)
   - Processing scripts run once, produce JSON caches
   - Main pipeline and tests never import xarray

### New Path Constants (for `src/paths.py`)

```python
CLIMATE_DIR: Path = DATA_DIR / "climate"
"""USGS LOCA2 climate projection data cache."""

SVI_DIR: Path = DATA_DIR / "svi"
"""CDC/ATSDR Social Vulnerability Index data cache."""

VULNERABILITY_PROFILES_DIR: Path = DATA_DIR / "vulnerability_profiles"
"""Per-Tribe composite vulnerability profile JSON files (592 files)."""

COUNTY_CLIMATE_PROJECTIONS_PATH: Path = CLIMATE_DIR / "county_climate_projections.json"
"""Pre-processed county-level climate projection summaries."""

COUNTY_SVI_PATH: Path = SVI_DIR / "county_svi.json"
"""Pre-processed county-level SVI rankings."""

def vulnerability_profile_path(tribe_id: str) -> Path:
    """Return the vulnerability profile JSON path for a specific Tribe."""
    return VULNERABILITY_PROFILES_DIR / f"{tribe_id}.json"
```

---

## Data Processing Details

### LOCA2 NetCDF Processing (xarray)

The processing script (`scripts/process_climate_projections.py`) will:

1. Open `CMIP6-LOCA2_1950-2100_County2023_monthly.nc` with `xarray.open_dataset()`
2. Select the pre-computed Weighted Multi-Model Mean (WMMM) to avoid processing 27 individual models
3. Extract county-level climatology for key periods:
   - Baseline: 1981-2010 (30-year historical mean)
   - Near-term: 2025-2049
   - Mid-century: 2050-2074
   - Late-century: 2075-2099
4. For SSP2-4.5 (moderate) and SSP5-8.5 (high emissions) scenarios
5. Compute deltas: `future_period_mean - baseline_mean` for temperature (degrees C); `(future / baseline - 1) * 100` for precipitation (percent change)
6. Write per-county JSON keyed by FIPS/GEOID

**Example output structure per county:**

```json
{
  "06037": {
    "county_name": "Los Angeles",
    "state": "CA",
    "baseline_1981_2010": {
      "tasmax_annual_mean_c": 25.3,
      "tasmin_annual_mean_c": 12.1,
      "pr_annual_total_mm": 380.5
    },
    "projections": {
      "ssp245": {
        "2025_2049": {
          "tasmax_delta_c": 1.2,
          "tasmin_delta_c": 1.0,
          "pr_pct_change": -5.2
        },
        "2050_2074": {
          "tasmax_delta_c": 2.1,
          "tasmin_delta_c": 1.8,
          "pr_pct_change": -8.1
        },
        "2075_2099": {
          "tasmax_delta_c": 2.8,
          "tasmin_delta_c": 2.4,
          "pr_pct_change": -11.3
        }
      },
      "ssp585": {
        "2025_2049": {
          "tasmax_delta_c": 1.4,
          "tasmin_delta_c": 1.2,
          "pr_pct_change": -4.8
        },
        "2050_2074": {
          "tasmax_delta_c": 3.2,
          "tasmin_delta_c": 2.7,
          "pr_pct_change": -12.5
        },
        "2075_2099": {
          "tasmax_delta_c": 5.1,
          "tasmin_delta_c": 4.3,
          "pr_pct_change": -18.7
        }
      }
    }
  }
}
```

**Memory consideration:** The monthly file is ~2.17 GB. xarray uses lazy loading by default (backed by netCDF4/HDF5), so only the requested slices are loaded into memory. The multi-model mean extraction and period averaging should peak at well under 1 GB RAM. No Dask cluster needed.

**LOW confidence items that need verification during implementation:**
- Exact variable names in the county NetCDF (`tasmax`, `tasmin`, `pr` assumed from CMIP6 conventions)
- Whether the multi-model mean is a separate variable or a model dimension value
- Exact dimension structure (county x time x model x scenario vs. separate files per scenario)

### CDC SVI Processing (csv stdlib)

Standard CSV parsing, identical pattern to existing NRI parsing in `hazards.py`:

1. Read with `csv.DictReader`, `encoding="utf-8-sig"` (CDC CSVs may have BOM, same as NRI)
2. Key by `FIPS` field (pad to 5 digits with `zfill(5)`)
3. Extract key columns: `RPL_THEMES`, `RPL_THEME1` through `RPL_THEME4`, selected `E_` estimates
4. Handle `-999` null values -> `None`
5. Write per-county JSON keyed by FIPS

**Example output structure per county:**

```json
{
  "06037": {
    "fips": "06037",
    "county": "Los Angeles",
    "state": "CA",
    "overall_svi": 0.8234,
    "theme1_socioeconomic": 0.7891,
    "theme2_household": 0.8456,
    "theme3_minority": 0.9012,
    "theme4_housing_transport": 0.6789,
    "flag_overall": 1,
    "data_year": 2022
  }
}
```

### Expanded NRI Processing (existing code extension)

Modify `hazards.py::_load_nri_county_data()` starting at line 360:

1. Add new fields to the `record` dict construction
2. Use same `_safe_float()` and `row.get()` pattern already in place
3. Update the per-Tribe aggregation to handle new fields appropriately (sums vs. averages)
4. Extend the hazard profile JSON schema with new fields

---

## Installation

### Add to `requirements.txt`:

```
# Climate data processing (build-time only - for scripts/process_climate_projections.py)
xarray>=2025.12.0
netCDF4>=1.7.3
```

### Full install command:

```bash
pip install xarray>=2025.12.0 netCDF4>=1.7.3
```

### Build-time vs. runtime dependency note

Like `geopandas`, the `xarray` and `netCDF4` libraries are **build-time only** dependencies. They are used by data processing scripts that run once to produce JSON caches. The main pipeline (`src/main.py`), document generation (`src/packets/`), and the test suite do NOT import xarray or netCDF4. This matches the existing pattern where `geopandas` is used only by `scripts/build_area_crosswalk.py`.

The comment grouping in `requirements.txt` should mirror the existing geopandas section:

```
# Geospatial (build-time only - for scripts/build_area_crosswalk.py)
geopandas>=1.0.0
shapely>=2.0.0
pyproj>=3.3.0
pyogrio>=0.7.2

# Climate data processing (build-time only - for scripts/process_climate_projections.py)
xarray>=2025.12.0
netCDF4>=1.7.3
```

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not Alternative |
|----------|-------------|-------------|---------------------|
| NetCDF reader | xarray + netCDF4 | h5netcdf (lighter HDF5 backend) | netCDF4 is the standard backend for climate data; h5netcdf is lighter but less battle-tested with LOCA2 specifically |
| NetCDF reader | xarray | Raw netCDF4 API only | xarray provides labeled dimensions, slicing by time period, and aggregation that would require ~5x more code with raw netCDF4 |
| Climate data source | USGS LOCA2 county summaries | Raw LOCA2 6km grid from loca.ucsd.edu | County summaries are pre-aggregated (2 GB vs 100+ GB). Our pipeline maps to counties anyway. |
| Climate data source | USGS LOCA2 county summaries | NOAA Climate Explorer | Climate Explorer has no bulk download API; LOCA2 ScienceBase has direct file URLs |
| Climate data source | USGS LOCA2 county summaries | NASA NEX-GDDP-CMIP6 | NEX-GDDP is global gridded (25km), not county-aggregated. Would need geopandas spatial join. |
| SVI data access | Manual CSV download from CDC | ArcGIS Online REST API | CSV download is simpler, more reliable, and provides the exact same data |
| SVI data access | Manual CSV download from CDC | `findSVI` Python package | Adds unnecessary dependency; we just need to read a CSV, not compute SVI from raw census data |
| SLR projections | Defer / use NRI CFLD fields | NOAA SLR scenario downloads | SLR data is at tide-gauge/grid level, not county level. Requires spatial join. NRI already has coastal flooding risk scores. |
| Large file download | `requests` (existing) | `sciencebasepy` | We know the exact download URL from ScienceBase; no need for catalog browsing SDK |
| Data parallelism | Sequential xarray processing | Dask distributed | County-level NetCDF fits in memory; Dask overhead not justified for a one-time processing step |

---

## Version Compatibility Matrix

| Package | Min Version | Latest Verified | Python Compat | Notes |
|---------|-------------|-----------------|---------------|-------|
| xarray | 2025.12.0 | 2026.1.0 (Jan 28, 2026) | 3.11+ | Calendar versioning; requires numpy>=1.26, pandas>=2.2 |
| netCDF4 | 1.7.3 | 1.7.4 (Jan 5, 2026) | 3.9-3.14 | v1.7.4 adds Python 3.14 wheels, compression plugins |
| Python | 3.12 | 3.12 (project standard) | -- | Both xarray and netCDF4 fully support 3.12 |
| numpy | 1.26+ | (via xarray) | 3.12+ | Already implicit dependency via geopandas |
| pandas | 2.2+ | (via xarray) | 3.12+ | Already implicit dependency via geopandas |
| geopandas | 1.0.0+ | (existing) | 3.12+ | No change needed |
| requests | 2.31+ | (existing) | 3.12+ | Used for ScienceBase file download |

**Potential conflict check:** xarray requires `pandas>=2.2` and `numpy>=1.26`. Since `geopandas>=1.0.0` is already in requirements, these transitive dependencies should already be satisfied. Verify with `pip check` after install.

---

## API Access Requirements Summary

| Data Source | Access Method | API Key | Rate Limits | Auth | Download Size |
|-------------|---------------|---------|-------------|------|---------------|
| USGS LOCA2 | Direct HTTPS from ScienceBase | None | None (bulk file) | None | ~2.2 GB (monthly file only) |
| CDC SVI | Manual download from CDC web interface | None | N/A (manual) | None | ~5-10 MB CSV |
| FEMA NRI | Already downloaded to `data/nri/` | None | N/A | None | 0 (already have it) |
| NOAA SLR (if used) | Download from earth.gov | None | None | None | Unknown |

**No new API keys required.** All data sources are public, unrestricted downloads.

---

## Disk Space Requirements

| Dataset | Raw Size | Processed JSON | Location |
|---------|----------|----------------|----------|
| LOCA2 monthly NetCDF | ~2.17 GB | ~15 MB | `data/climate/` |
| LOCA2 thresholds NetCDF (optional) | ~1.74 GB | ~10 MB | `data/climate/` |
| CDC SVI county CSV | ~5-10 MB | ~2 MB | `data/svi/` |
| Expanded NRI fields | 0 (same CSV) | ~0 (extends existing profiles) | `data/nri/` (existing) |
| Per-Tribe vulnerability profiles | -- | ~5 MB (592 files) | `data/vulnerability_profiles/` |
| **Total new raw data** | **~2.2-4 GB** | **~32 MB processed** | |

**Note:** The raw NetCDF files are only needed during the one-time processing step. After generating `county_climate_projections.json`, they could be deleted to save disk space. However, keeping them allows re-processing if the extraction logic changes. Same pattern as keeping NRI CSVs in `data/nri/`.

**Git exclusions (consistent with existing DEC-1203-03 practice):**

```gitignore
data/climate/*.nc
data/climate/county_climate_projections.json
data/svi/*.csv
data/svi/county_svi.json
data/vulnerability_profiles/
```

---

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| LOCA2 NetCDF file too large for memory | Processing script fails | LOW (xarray lazy-loads) | Extract one variable/period at a time; xarray only loads requested slices |
| CDC SVI download URL or interface changes | Cannot download SVI data | LOW | Download is manual anyway; document the procedure. Data changes biannually. |
| FEMA NRI v1.20 renamed fields vs. v1.18 | New field extraction returns null | MEDIUM | Use defensive `row.get()` with defaults (existing pattern). Log warnings. Verify against actual CSV headers. |
| LOCA2 dataset moved on ScienceBase | Download URL breaks | LOW | Pin the ScienceBase item ID (`673d0719d34e6b795de6b593`). ScienceBase uses stable DOI-backed URLs. |
| xarray/netCDF4 install fails on Windows | Developer blocked | LOW | Both have pre-built wheels for Windows on PyPI since 2024+. `pip install` should work. |
| LOCA2 variable names differ from CMIP6 convention | xarray extraction code fails | MEDIUM | Inspect dataset with `ds = xarray.open_dataset(path); print(ds)` as first step. Adapt variable names. |
| LOCA2 multi-model mean not pre-computed | Must average 27 models ourselves | MEDIUM | ScienceBase page says WMMM is included. Verify by inspecting the file. If not included, compute `ds.mean(dim='model')`. |

---

## Script Execution Order (Data Pipeline)

The data processing scripts should be run in this order (matching existing hazard pipeline pattern):

```bash
# Step 0: Prerequisites (existing -- already run for v1.0+)
python scripts/download_nri_data.py        # Already done
python scripts/build_area_crosswalk.py     # Already done (produces tribal_county_area_weights.json)

# Step 1: Download new data sources
python scripts/download_climate_data.py    # NEW: Downloads LOCA2 NetCDF from ScienceBase
# Manual: Download SVI 2022 US County CSV from svi.cdc.gov, place in data/svi/

# Step 2: Process raw data into county-level JSON caches
python scripts/process_climate_projections.py  # NEW: NetCDF -> JSON (requires xarray)
python scripts/process_svi_data.py             # NEW: SVI CSV -> JSON (stdlib only)

# Step 3: Build per-Tribe vulnerability profiles
python scripts/build_vulnerability_profiles.py # NEW: Combines all sources per Tribe

# Step 4: Generate documents (existing pipeline, extended)
python -m src.main --prep-packets --all-tribes  # Existing, now includes vulnerability report
```

---

## Sources

### Verified (HIGH confidence)
- [USGS CMIP6-LOCA2 County Spatial Summaries - ScienceBase](https://www.sciencebase.gov/catalog/item/673d0719d34e6b795de6b593) -- Dataset catalog page, file list, sizes, GEOID field, DOI
- [USGS CMIP6-LOCA2 County Summaries - USGS.gov](https://www.usgs.gov/data/cmip6-loca2-spatial-summaries-counties-tiger-2023-1950-2100-contiguous-united-states) -- 27 models, 3 SSPs, TIGER 2023, WMMM included
- [CDC SVI Data Download](https://svi.cdc.gov/dataDownloads/data-download.html) -- CSV + geodatabase, county/tract/ZCTA, 2022 latest
- [CDC SVI 2022 Documentation PDF](https://www.atsdr.cdc.gov/place-health/media/pdfs/2024/10/SVI2022Documentation.pdf) -- Column naming conventions (E_, M_, EP_, EPL_, RPL_, SPL_, F_)
- [FEMA NRI Data page](https://www.fema.gov/about/openfema/data-sets/national-risk-index-data) -- v1.20 December 2025
- [FEMA NRI Expected Annual Loss](https://hazards.fema.gov/nri/expected-annual-loss) -- EAL components (building, population, agriculture)
- [FEMA NRI Community Resilience](https://hazards.fema.gov/nri/community-resilience) -- RESL scoring methodology
- [xarray on PyPI](https://pypi.org/project/xarray/) -- v2026.1.0, requires Python 3.11+, netCDF4>=1.6.0
- [netCDF4 on PyPI](https://pypi.org/project/netCDF4/) -- v1.7.4, Jan 5, 2026, Python 3.9-3.14
- [xarray installation docs](https://docs.xarray.dev/en/stable/getting-started-guide/installing.html) -- Dependency requirements
- Existing codebase: `src/packets/hazards.py` lines 355-387 -- confirmed NRI field names and parsing pattern
- Existing codebase: `scripts/build_area_crosswalk.py` -- confirmed area-weighted crosswalk pattern with EPSG:5070/3338
- Existing codebase: `src/paths.py` -- confirmed path constant pattern and directory structure

### Partially verified (MEDIUM confidence)
- [NOAA 2022 Sea Level Rise Technical Report Data](https://earth.gov/sealevel/us/resources/2022-sea-level-rise-technical-report/) -- Download exists but exact format not confirmed
- [NASA Interagency SLR Scenario Tool](https://sealevel.nasa.gov/data_tools/18) -- Interactive tool, bulk download capability unclear
- NRI v1.20 expanded field names (EAL_VALB, EAL_VALP, RISK_NPCTL, etc.) -- based on v1.18 naming patterns, not verified against actual v1.20 CSV headers

### Needs verification (LOW confidence)
- Exact LOCA2 variable names in county NetCDF (tasmax, tasmin, pr assumed from CMIP6 conventions -- verify by inspecting file)
- Whether LOCA2 multi-model mean is a named variable or requires computation from model dimension
- CDC SVI direct download URL (may require manual web interface interaction rather than scripted download)
- Exact NetCDF dimension structure for county data (county x time x scenario dimensions)
