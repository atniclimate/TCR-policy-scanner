# Sovereignty Scout Report: Data Source Validation
## Phase 18.5 | TCR Policy Scanner v1.4

### Executive Summary

Of the 12+ federal data sources proposed for v1.4, the core vulnerability pipeline (FEMA NRI expansion, CDC SVI, composite scoring) is validated and ready to build. However, three critical findings require architecture corrections before Phases 19-24 proceed: (1) the FEMA NRI Data Dictionary confirms `RISK_NPCTL` does NOT exist -- the correct field is `RISK_SPCTL` (State Percentile); (2) 229 of 592 tracked Tribal Nations (38.7%) are in Alaska and will have ZERO coverage from LOCA2 climate projections (CONUS-only), making the v1.5+ deferral the correct call; and (3) the `hazards.fema.gov` domain now redirects all documentation pages to FEMA's RAPT platform, signaling an infrastructure shift that must be monitored. The flood, climate, geologic, and infrastructure data sources (FLOOD-01 through INFRA-01) are all confirmed available with active APIs, though several require careful scoping to avoid overengineering.

---

### Data Source Status

#### FEMA NRI Expanded Metrics (VULN-01)
**Status:** CONFIRMED with corrections required

**Current extraction (hazards.py `_load_nri_county_data()`, lines 360-377):**
The existing implementation extracts these fields per county:
- `RISK_SCORE`, `RISK_RATNG`, `RISK_VALUE` (composite risk)
- `EAL_VALT`, `EAL_SCORE`, `EAL_RATNG` (total expected annual loss)
- `SOVI_SCORE`, `SOVI_RATNG` (social vulnerability)
- `RESL_SCORE`, `RESL_RATNG` (community resilience)
- Per-hazard: `{CODE}_RISKS`, `{CODE}_RISKR`, `{CODE}_EALT`, `{CODE}_AFREQ`, `{CODE}_EVNTS`

**NRI Data Dictionary (v1.20, December 2025, 479 fields) confirms:**

| Architecture Field | Actual NRI Field | Status | Notes |
|---|---|---|---|
| `EAL_VALB` | `EAL_VALB` | CONFIRMED | Expected Annual Loss - Building Value - Composite |
| `EAL_VALP` | `EAL_VALP` | CONFIRMED | Expected Annual Loss - Population - Composite |
| `EAL_VALA` | `EAL_VALA` | CONFIRMED | Expected Annual Loss - Agriculture Value - Composite |
| `EAL_VALPE` | `EAL_VALPE` | CONFIRMED | Expected Annual Loss - Population Equivalence - Composite |
| `RISK_NPCTL` | **DOES NOT EXIST** | CORRECTION NEEDED | Correct field is `RISK_SPCTL` (State Percentile). There is NO national percentile field in the NRI CSV. |
| `SOVI_VALUE` | Verify needed | UNCERTAIN | Data dictionary shows `SOVI_SCORE` and `SOVI_RATNG` (already extracted). A raw `SOVI_VALUE` field may exist but was not explicitly confirmed in the v1.20 dictionary. |
| `RESL_VALUE` | Verify needed | UNCERTAIN | Same situation as SOVI_VALUE. `RESL_SCORE` and `RESL_RATNG` already extracted. |
| `POPULATION` | `POPULATION` | CONFIRMED | Population (2020) |
| `BUILDVALUE` | `BUILDVALUE` | CONFIRMED | Building Value ($) |
| `AREA` | `AREA` | CONFIRMED | Area (sq mi) |
| Per-hazard EAL breakdown | `{CODE}_EALB`, `{CODE}_EALP`, `{CODE}_EALA`, `{CODE}_EALPE` | CONFIRMED | All 18 hazard codes have B/P/A/PE breakdowns |

**CRITICAL CORRECTION: `RISK_NPCTL` does not exist.** The architecture document (line 111) and ARCHITECTURE.md composite vulnerability formula (line 595) both reference `RISK_NPCTL` as the "Risk National Percentile." The NRI v1.20 Data Dictionary provides only `RISK_SPCTL` (State Percentile) -- percentile ranking among counties within the same state, NOT nationally. The composite vulnerability score design must be revised to either:
  - (a) Use `RISK_SPCTL` with documentation that it is state-relative, OR
  - (b) Compute a national percentile from `RISK_SCORE` across all ~3,200 counties at build time (recommended -- straightforward rank-based percentile calculation)

**Download URL confirmed:** `https://www.fema.gov/about/reports-and-data/openfema/nri/v120/NRI_Table_Counties.zip` (the existing `scripts/download_nri_data.py` already uses this exact URL).

**hazards.fema.gov redirect finding:** The NRI Data Glossary, Data Dictionary CSV, and archived technical documentation at `hazards.fema.gov/nri/` now all 301-redirect to `https://www.fema.gov/emergency-managers/practitioners/resilience-analysis-and-planning-tool` (RAPT). The NRI data itself remains available via `fema.gov/about/openfema/data-sets/national-risk-index-data`, but all documentation links in older code comments and README references will break. The v1.20 Data Dictionary is now hosted at an ArcGIS endpoint: `https://fema.maps.arcgis.com/sharing/rest/content/items/4b9db412e99542029b3c37c37ad714bb/data`.

**What this means for Tribal Leaders:** EAL consequence-type breakdowns (buildings, population, agriculture) give Tribal Leaders concrete dollar figures for grant applications. "This Nation faces $1.2M in annual building losses from wildfire and $340K in agricultural losses from drought" is far more compelling in testimony than a composite score. The per-hazard EAL breakdown is the single most grant-relevant data expansion in v1.4.

---

#### CDC/ATSDR Social Vulnerability Index (VULN-02)
**Status:** CONFIRMED

**Version status:** SVI 2022 (based on 2018-2022 ACS 5-year estimates) is the current release, published May 2024. SVI 2024 has NOT been released. The 2020-2024 ACS 5-year estimates were released January 29, 2026, but CDC has not yet produced an SVI update based on them. The architecture's assumption of SVI 2022 as the target version is correct.

**Column names confirmed (from SVI 2022 documentation and third-party validation):**

| Column | Description | Status |
|---|---|---|
| `FIPS` | 5-digit county FIPS code | CONFIRMED (joinable to NRI `STCOFIPS`) |
| `RPL_THEMES` | Overall SVI percentile rank (0-1) | CONFIRMED |
| `RPL_THEME1` | Socioeconomic Status | CONFIRMED |
| `RPL_THEME2` | Household Characteristics (renamed from "Household Composition & Disability" in 2020) | CONFIRMED |
| `RPL_THEME3` | Racial & Ethnic Minority Status | CONFIRMED (excluded per user direction) |
| `RPL_THEME4` | Housing Type & Transportation | CONFIRMED |
| `E_*` columns | Estimate values (16 census variables) | CONFIRMED |
| `EP_*` columns | Percentages | CONFIRMED |
| `EPL_*` columns | Percentile rankings per variable | CONFIRMED |
| `F_*` columns | Binary flags (above 90th percentile) | CONFIRMED |

**Theme 3 exclusion (REQUIREMENTS line 84):** The requirement to EXCLUDE Theme 3 (Racial & Ethnic Minority Status, `RPL_THEME3`) is architecturally sound. Theme 3 captures minority status and limited English proficiency. For Tribal Nations -- all of whom are Indigenous by definition -- this theme introduces a tautological signal. Including it would artificially inflate vulnerability scores for every Tribe equally, adding noise rather than signal. The exclusion is the correct call for Tribal advocacy. The overall `RPL_THEMES` column includes all 4 themes in its calculation, so the architecture should either:
  - (a) Recompute an overall SVI from Themes 1+2+4 only (recommended for consistency), OR
  - (b) Use `RPL_THEMES` as-is with documentation that it includes Theme 3, OR
  - (c) Use a simple average of `RPL_THEME1` + `RPL_THEME2` + `RPL_THEME4` as the Tribal SVI composite

**Download method:** The SVI 2022 county CSV is available at `https://svi.cdc.gov` via the data download page. However, note that the old `svi.cdc.gov` domain may redirect to `atsdr.cdc.gov/place-health/php/svi/svi-data-documentation-download.html`. The download produces a file approximately 15 MB in size with ~3,200 county rows.

**What this means for Tribal Leaders:** SVI theme decomposition tells a Tribal Leader exactly which social vulnerability drivers affect their people -- is it poverty and unemployment (Theme 1), housing overcrowding and mobile homes (Theme 4), or elder/disability demographics (Theme 2)? This specificity drives targeted grant language.

---

#### USGS LOCA2 Climate Projections
**Status:** CONFIRMED DEFERRED (v1.5+) -- deferral validated as correct

**The REQUIREMENTS.md (line 69) correctly defers LOCA2 to v1.5+.** This scout's investigation confirms the deferral was the right call for three reasons:

**Reason 1: Alaska coverage gap is catastrophic.** LOCA2 county summaries cover the "Contiguous United States" only. Of the 592 tracked Tribal Nations, **229 (38.7%) are in Alaska.** These 229 Alaska Native Villages, Tribes, and communities would have ZERO climate projection data from LOCA2. Shipping a climate vulnerability feature that excludes 38.7% of the served population is unacceptable for a tool that centers sovereignty.

**Reason 2: NetCDF dependency is heavy but avoidable.** The primary county summaries dataset (ScienceBase item 673d0719) is NetCDF-only (~9.1 GB across 7 files). HOWEVER, the LOCA2 *Thresholds* dataset (ScienceBase item 65cd1ff2) DOES provide CSV files for the Weighted Multi-Model Mean at county level:
  - `CMIP6-LOCA2_Thresholds_WeightedMultiModelMean_timeseries_by_county_csv.tar.gz` (2.18 GB)

  This CSV includes the extreme event metrics most relevant for Tribal vulnerability:
  - `TX95pDAYS` -- Days above 95F
  - `TXge100F` -- Days above 100F
  - `TXge105F` -- Days above 105F
  - `FD` -- Frost days (below 32F)
  - `ID` -- Ice days (below 0F)
  - `CDD` -- Consecutive dry days
  - `R1in` -- Heavy precipitation days (>1 inch)

  **Missing:** Heating Degree Days (HDD) and Cooling Degree Days (CDD as "energy burden" metric) are NOT in the thresholds dataset. The architecture assumed these would be available.

**Reason 3: Download size is prohibitive for rapid iteration.** The full thresholds dataset is 383.58 GB across 78 files. Even the county CSV extract is 2.18 GB compressed. This requires a careful pre-processing pipeline, not a quick integration.

**Alaska fallback identified:** SNAP (Scenarios Network for Alaska + Arctic Planning) at UAF provides CMIP6-based dynamically downscaled climate projections for Alaska at 10km resolution (20km WRF output, v1.1 August 2023). Available via AWS Open Data Registry. Community-level charts are available at `snap.uaf.edu/tools/community-charts`. A 2025 scientific paper (Nature Scientific Data) provides ensemble downscaled data for Alaska and Hawaii from 23 CMIP6 GCMs under 4 SSP scenarios. This is the path forward for Alaska coverage in v1.5+.

**What this means for Tribal Leaders:** Deferral is the right call because shipping incomplete climate data for 229 Alaska Native communities would undermine trust. When LOCA2 does ship in v1.5+, the CSV thresholds path eliminates the xarray/netCDF4 dependency, and SNAP data covers the Alaska gap.

---

#### FEMA Future Risk Index (FRI)
**Status:** CONFIRMED UNAVAILABLE -- architecture decision validated

The Future Risk Index was launched by FEMA in mid-December 2024, covering 5 hazards under multiple emissions scenarios. It was **removed from FEMA's website in mid-February 2025** by administration order. Key facts:

- The archived version exists at `fulton-ring.github.io/nri-future-risk/` (rebuilt by data scientists)
- On April 15, 2025, public interest groups sued the federal government for removing the FRI
- No restoration to the official FEMA website has occurred as of February 2026
- Commercial alternatives exist (RiskFootprint v18) but are proprietary
- The underlying technical documentation was preserved at Harvard EELP

**Architecture decision validated:** The ARCHITECTURE.md (line 180-187) correctly states "Do NOT depend on this data source." The archived version is static, unmaintained, and politically uncertain. The v1.5+ LOCA2 integration provides an independent, maintained alternative for future climate risk signals.

**What this means for Tribal Leaders:** Federal data removal is itself a sovereignty concern. Tribal Leaders should know that future climate risk data was available and then withdrawn. The absence is worth documenting in vulnerability reports as a data gap, not ignoring silently.

---

#### Flood Data Sources (FLOOD-01 through FLOOD-06)

**FLOOD-01: OpenFEMA NFIP Claims Data**
**Status:** CONFIRMED AVAILABLE

- FIMA NFIP Redacted Claims v2: `https://www.fema.gov/openfema-data-page/fima-nfip-redacted-claims-v2`
- Free REST API, no subscription or API key required
- Base path: `https://www.fema.gov/api/open`
- Over 2,000,000 claims transactions with monthly updates
- Fields include Building Damage Amount, Building Property Value, Cause of Damage
- County-level aggregation possible via property location fields
- **Note:** Updated approximately monthly with lag from system of record

**FLOOD-02: FEMA Disaster Declarations**
**Status:** CONFIRMED AVAILABLE

- Disaster Declarations Summaries v2: `https://www.fema.gov/openfema-data-page/disaster-declarations-summaries-v2`
- All federally declared disasters from 1953 to present
- Three declaration types: major disaster, emergency, fire management assistance
- Filterable by county FIPS, disaster type, date range
- Free API, no key required

**FLOOD-03: FEMA NFHL (National Flood Hazard Layer)**
**Status:** CONFIRMED AVAILABLE with limitations

- WMS endpoint: `https://hazards.fema.gov/gis/nfhl/services/public/NFHLWMS/MapServer/WMSServer`
- REST services available
- **WFS limitation:** Requests limited to 1,000 features per request. For larger areas, FEMA recommends downloading NFHL data by state or county from the Map Service Center (`https://msc.fema.gov`)
- Bulk state/county downloads available as shapefiles
- **Tribal land mapping will require geospatial intersection** with AIANNH boundaries, which is more complex than county-FIPS joining. Consider deferring full NFHL integration or using county-level flood zone summary statistics.

**FLOOD-04: USGS Water Services**
**Status:** CONFIRMED AVAILABLE -- MIGRATION WARNING

- Current endpoint: `https://waterservices.usgs.gov/` (Instantaneous Values, Daily Values, Site Service)
- **CRITICAL:** WaterServices will be **decommissioned in early 2027**. Applications must migrate to `https://api.waterdata.usgs.gov/` which implements OGC API - Features
- Legacy service performance expected to degrade starting September 2025
- `gwlevels` endpoint already decommissioned as of November 2025
- **Recommendation:** Build against the NEW API at `api.waterdata.usgs.gov` from the start, not the legacy endpoint

**FLOOD-05: NOAA Atlas 14 / HDSC**
**Status:** CONFIRMED AVAILABLE -- SUPERSESSION WARNING

- PFDS (Precipitation Frequency Data Server): `https://hdsc.nws.noaa.gov/pfds/`
- Point-and-click interface with GIS-compatible ASCII downloads
- **NOAA Atlas 15 is in development:** Preliminary data for CONUS released for peer review in early 2026, with published estimates expected in 2026. Atlas 15 will supersede Atlas 14 and importantly will **account for climate trends** (Atlas 14 does not).
- Full Atlas 15 replacement (including non-CONUS) expected in 2027
- **Recommendation:** Build against Atlas 14 now, plan migration to Atlas 15 when published. The climate-adjusted precipitation frequencies in Atlas 15 will be significantly more valuable for Tribal vulnerability assessment.

**FLOOD-06: NOAA CO-OPS (Tides & Currents)**
**Status:** CONFIRMED AVAILABLE

- Data retrieval API: `https://api.tidesandcurrents.noaa.gov/api/prod/datagetter`
- Metadata API: `https://api.tidesandcurrents.noaa.gov/mdapi/prod/`
- Derived Product API (flood projections, sea level rise scenarios): `https://api.tidesandcurrents.noaa.gov/dpapi/prod/`
- Multiple formats: CSV, XML, JSON, NetCDF
- No API key required
- Recently migrated to cloud infrastructure -- use updated URLs
- **Tribal relevance:** Primarily relevant for coastal Tribal Nations. Most Alaska coastal communities and Pacific Northwest coastal Tribes would benefit.

---

#### Climate Data Sources (CLIM-01 through CLIM-03)

**CLIM-01: US Drought Monitor / NOAA-NIDIS**
**Status:** CONFIRMED AVAILABLE

- Drought.gov data download: `https://www.drought.gov/data-download`
- US Drought Monitor data: `https://droughtmonitor.unl.edu/DmData/DataDownload.aspx`
- County-level data available: percent of area, total area, percent of population, total population per drought category (D0-D4) per week
- Web API available returning JSON/GeoJSON
- Free, hosted on Google Cloud Storage with public file URLs
- **Well-suited for Tribal mapping:** Weekly drought severity by county joins directly to existing crosswalk

**CLIM-02: NOAA NCEI Climate Data Online (CDO)**
**Status:** CONFIRMED AVAILABLE -- API TRANSITION IN PROGRESS

- Legacy API: `https://www.ncei.noaa.gov/cdo-web/api/v2/{endpoint}` (DEPRECATED)
- New API: `https://www.ncei.noaa.gov/access/services/data/v1`
- **Requires token** (free, obtained via email at `https://www.ncdc.noaa.gov/cdo-web/token`)
- Rate limits: 5 requests/second, 10,000 requests/day
- 1991-2020 Climate Normals available
- **Recommendation:** Build against the new endpoint, not the deprecated one. Token management needed.

**CLIM-03: NWS API**
**Status:** CONFIRMED AVAILABLE

- Base URL: `https://api.weather.gov/`
- `/alerts` endpoint: past 7 days of alerts; `/alerts/active` for current alerts
- County-based filtering via UGC (Universal Geographic Code): state abbreviation + "C" + FIPS county number
- JSON-LD format (default)
- No API key required
- **Recent update (Jan 2026):** `/forecast` and `/forecast/hourly` endpoints no longer contain past data
- **Tribal relevance:** Active weather alerts mapped to Tribal lands provide real-time hazard awareness context

---

#### Geologic Data (GEO-01, GEO-02)

**GEO-01: State Landslide Inventories (WA/OR)**
**Status:** CONFIRMED AVAILABLE

**Washington DNR:**
- Landslide Inventory Database v1.4 (April 2025)
- REST services: `https://gis.dnr.wa.gov/site1/rest/services/Public_Geology/Landslide_Inventory_Database/MapServer`
- Download: `https://fortress.wa.gov/dnr/geologydata/publications/data_download/ger_portal_landslide_database.zip`
- ESRI file geodatabase format (ArcGIS Pro 3.0)
- Open Data portal: `https://data-wadnr.opendata.arcgis.com/`

**Oregon DOGAMI SLIDO:**
- SLIDO v4.5 (April 2024): 71,318 landslide deposits
- Download: `https://www.oregon.gov/dogami/slido/Pages/data.aspx`
- ESRI ArcGIS 10.7 file geodatabase
- Web map and map services available

**Limitation:** Both datasets are ESRI geodatabase format, requiring geopandas/fiona for parsing. The landslide inventories are point/polygon features that need geospatial intersection with Tribal land boundaries -- this is more complex than county-FIPS joining. **Scope concern:** These cover only WA and OR, which serve a subset of the 592 Tribes. May be better suited as a regional enhancement rather than a core v1.4 feature.

**GEO-02: USGS 3DEP Elevation/Terrain**
**Status:** CONFIRMED AVAILABLE

- National Map Downloader: `https://apps.nationalmap.gov/3depdem/`
- REST, WCS, WMS, WMTS, WFS map services (free, no account required)
- LiDAR point clouds on AWS (Requester Pays bucket)
- 1m and 10m DEMs available
- **Scope concern:** 3DEP data is raw elevation raster data. Converting it to per-Tribe terrain metrics (slope, aspect, flood-prone low-lying areas) requires significant geospatial processing. This is a research-grade task, not a data integration task. **Recommend deferring to v1.5+ unless specific terrain-derived metrics are defined.**

---

#### Infrastructure Data (INFRA-01)

**INFRA-01: DHS HIFLD Critical Infrastructure**
**Status:** CONFIRMED AVAILABLE with access caveats

- Open data portal: `https://hifld-geoplatform.opendata.arcgis.com/`
- Download formats: CSV, KML, Shapefile, GeoJSON, GeoTIFF, PNG
- Sectors include: agriculture, communications, education, emergency services, energy, transportation, water
- **Open datasets** are freely available without authentication
- **Secure/licensed datasets** require GII access, MyHIFLD Profile, and signed Data Use Agreement (DUA) renewed annually
- Tribal partners qualify for secure data access under homeland security mission
- **Recommendation:** Use open datasets only for v1.4 (T0 classification). Critical infrastructure exposure can be derived by spatial overlay of open HIFLD point features with Tribal land boundaries.

---

### Alaska Coverage Analysis

**Exact count:** 229 out of 592 tracked Tribal Nations (38.7%) are in Alaska.

This is the single largest data coverage concern for v1.4. The breakdown:

| Data Source | Alaska Coverage | Impact |
|---|---|---|
| FEMA NRI | PARTIAL -- NRI includes Alaska boroughs but coverage is uneven for remote villages | ~19 unmatched Tribes in current hazard profiles are Alaska-heavy |
| CDC SVI | YES -- SVI 2022 includes Alaska boroughs/census areas | Full coverage expected |
| LOCA2 Climate | NO -- CONUS only | 229 Tribes with zero climate projections |
| US Drought Monitor | YES -- county-level includes Alaska | Full coverage |
| NOAA CO-OPS | PARTIAL -- limited tide stations in Alaska | Coastal villages covered, interior not applicable |
| USGS Water Services | PARTIAL -- limited gauge network in Alaska | Sparse coverage |
| DHS HIFLD | PARTIAL -- varies by sector | Unknown coverage for remote villages |

**Fallback strategy for climate projections (v1.5+):**
1. **Primary:** SNAP (UAF) CMIP6 downscaled data for Alaska at 10km/20km resolution via AWS Open Data Registry
2. **Secondary:** 2025 ensemble dataset (Nature Scientific Data) providing bias-corrected daily climate data from 23 CMIP6 GCMs for Alaska at 10km under 4 SSP scenarios
3. **Community-level:** SNAP Community Climate Charts (`snap.uaf.edu/tools/community-charts`) for individual Alaska community projections
4. **Minimum viable:** Flag Alaska Tribes in vulnerability profiles with `"climate_projections": {"status": "unavailable", "reason": "LOCA2 covers CONUS only; Alaska projections planned for v1.5+"}` and document the gap transparently

**What this means for Tribal Leaders:** 229 Alaska Native communities cannot be left with blank climate sections. Even without LOCA2, the NRI hazard data + SVI social vulnerability data + drought data provide a meaningful vulnerability profile for Alaska. The climate projection gap must be documented honestly in every Alaska Tribe's report: "Federal climate projection datasets do not yet provide county-level coverage for Alaska. This is a federal data gap, not a reflection of your community's climate exposure."

---

### Architecture Corrections Required

**Correction 1: `RISK_NPCTL` field name (CRITICAL)**
- **Location:** ARCHITECTURE.md lines 111, 595; REQUIREMENTS.md line 18 (VULN-01)
- **Issue:** The field `RISK_NPCTL` does not exist in the NRI v1.20 Data Dictionary. The available field is `RISK_SPCTL` (State Percentile).
- **Fix:** Either use `RISK_SPCTL` (with documentation that it is state-relative) or compute a national percentile from `RISK_SCORE` across all counties at build time. Recommended: compute national percentile at build time for consistency with the composite vulnerability score design.

**Correction 2: NRI Data Dictionary URL**
- **Location:** ARCHITECTURE.md line 119; any references to `hazards.fema.gov/nri/data-glossary` or `hazards.fema.gov/nri/data-resources`
- **Issue:** All `hazards.fema.gov/nri/*` URLs now 301-redirect to RAPT. The Data Dictionary is now at an ArcGIS endpoint.
- **Fix:** Update data source documentation to use `fema.gov/about/openfema/data-sets/national-risk-index-data` as the canonical reference.

**Correction 3: LOCA2 county summaries format**
- **Location:** ARCHITECTURE.md lines 159-161
- **Issue:** Architecture says "NetCDF time series files linked to shapefile geometry via GEOID field" and proposes either pre-processing to JSON or direct NetCDF parsing. The primary county summaries dataset IS NetCDF-only (~9.1 GB). BUT the LOCA2 Thresholds dataset provides **CSV files for the Weighted Multi-Model Mean** at county level (2.18 GB compressed).
- **Fix:** When LOCA2 is built in v1.5+, use the Thresholds CSV (not the primary county summaries NetCDF) to eliminate the xarray/netCDF4 dependency entirely. The Thresholds CSV contains the most relevant extreme event metrics (heat days, frost days, heavy precip, consecutive dry days).

**Correction 4: Missing HDD/CDD in LOCA2 Thresholds**
- **Location:** ARCHITECTURE.md lines 170-171
- **Issue:** The architecture lists "Heating/Cooling Degree Days (energy burden)" as a target climate variable. The LOCA2 Thresholds dataset does NOT include HDD or CDD. These would need to be derived from the primary LOCA2 county summaries (NetCDF-only) or sourced from NOAA Climate Normals.
- **Fix:** Remove HDD/CDD from LOCA2 scope or source from NOAA NCEI Climate Data Online (historical normals).

**Correction 5: SVI `RPL_THEMES` includes Theme 3**
- **Location:** ARCHITECTURE.md line 129; composite vulnerability formula line 599
- **Issue:** `RPL_THEMES` is the overall SVI percentile computed across ALL 4 themes including Theme 3 (Racial & Ethnic Minority Status), which is excluded per requirements. Using `RPL_THEMES` directly as the social vulnerability component contradicts the Theme 3 exclusion directive.
- **Fix:** Compute a custom Tribal SVI composite from Themes 1+2+4 only. Either average `RPL_THEME1` + `RPL_THEME2` + `RPL_THEME4`, or re-rank from the underlying `EPL_*` variables for Themes 1, 2, and 4.

**Correction 6: USGS Water Services endpoint deprecation**
- **Location:** REQUIREMENTS.md line 28 (FLOOD-04)
- **Issue:** Requirements reference `https://waterservices.usgs.gov/` which will be decommissioned in early 2027, with performance degradation starting September 2025.
- **Fix:** Build against the new OGC API endpoint: `https://api.waterdata.usgs.gov/`

**Correction 7: NOAA Atlas 14 supersession**
- **Location:** REQUIREMENTS.md line 29 (FLOOD-05)
- **Issue:** NOAA Atlas 15 (climate-adjusted precipitation frequencies) is in peer review for CONUS in 2026 and will supersede Atlas 14.
- **Fix:** Build against Atlas 14 now, document Atlas 15 migration path. Atlas 15 Volume 2 will provide future-projected precipitation frequencies -- highly relevant for Tribal climate vulnerability.

**Correction 8: NOAA NCEI CDO API deprecation**
- **Location:** REQUIREMENTS.md line 36 (CLIM-02)
- **Issue:** The CDO API v2 endpoint (`ncei.noaa.gov/cdo-web/api/v2`) is deprecated. The replacement is `ncei.noaa.gov/access/services/data/v1`.
- **Fix:** Update CLIM-02 to reference the new endpoint.

---

### Recommendations for Phase 19-24 Plan

**Phase 19 (Data Foundation) -- Proceed as planned with corrections:**
1. NRI expansion: Fix `RISK_NPCTL` -> compute national percentile from `RISK_SCORE` at build time
2. SVI integration: Compute custom Tribal SVI from Themes 1+2+4, NOT raw `RPL_THEMES`
3. Schema models (REG-03): Add validation that `RISK_SPCTL` and computed national percentile are both present
4. LOCA2: Confirmed deferred to v1.5+ -- do not include in Phase 19

**Phase 20 (Flood Data) -- Proceed with scoping adjustments:**
1. FLOOD-01 and FLOOD-02 (OpenFEMA): Low-risk, proceed. Free API, no key, county-level.
2. FLOOD-03 (NFHL): **Reduce scope.** Full geospatial intersection is complex. Consider county-level flood zone summary statistics rather than parcel-level overlay.
3. FLOOD-04 (USGS Water): Build against NEW API (`api.waterdata.usgs.gov`), not legacy endpoint.
4. FLOOD-05 (Atlas 14): Proceed, document Atlas 15 migration path.
5. FLOOD-06 (CO-OPS): Proceed. Most relevant for coastal Tribes.

**Phase 21 (Climate & Geologic) -- Proceed with scope guard:**
1. CLIM-01 (Drought Monitor): Excellent Tribal fit, county-level, weekly cadence. Proceed.
2. CLIM-02 (NCEI CDO): Use new API endpoint. Token management needed.
3. CLIM-03 (NWS API): Proceed. Real-time alerts are high value for Tribal awareness.
4. GEO-01 (Landslides): **Consider deferring.** WA/OR-only coverage serves a limited subset of 592 Tribes. Geodatabase format requires additional geospatial dependencies (geopandas/fiona already in requirements, but intersection logic is non-trivial).
5. GEO-02 (3DEP): **Recommend deferring to v1.5+.** Raw elevation data requires research-grade processing to derive meaningful Tribal-level terrain metrics.
6. INFRA-01 (HIFLD): Proceed with open datasets only (T0 boundary).

**Phase 22 (Vulnerability Profiles) -- Proceed with formula corrections:**
1. Composite score formula: Replace `RISK_NPCTL / 100` with computed national percentile
2. SVI component: Use custom Theme 1+2+4 composite, not `RPL_THEMES`
3. Alaska handling: Explicit `"status": "partial"` for Tribes with incomplete data coverage

**Phase 23 (Document Generation) -- Proceed as planned.**

**Phase 24 (Website) -- Proceed as planned.**

**New risk: Federal data infrastructure instability.** The `hazards.fema.gov` redirect to RAPT, the USGS WaterServices deprecation, the NOAA CDO API deprecation, and the FEMA FRI removal all signal that federal data infrastructure is in active transition. **Recommendation:** Add a data source health-check script (`scripts/check_data_sources.py`) that validates all download URLs and API endpoints, with alerts when HTTP status codes change. This prevents silent pipeline failures when agencies reorganize their web infrastructure.

---

### Appendix: Data Source Quick Reference

| Source | URL | Format | Auth | County Key | Alaska | Status |
|---|---|---|---|---|---|---|
| FEMA NRI v1.20 | fema.gov/.../nri/v120/ | CSV/ZIP | None | STCOFIPS | Partial | CONFIRMED |
| CDC SVI 2022 | svi.cdc.gov | CSV | None | FIPS | Yes | CONFIRMED |
| LOCA2 County | sciencebase.gov/673d... | NetCDF | None | GEOID | No | DEFERRED |
| LOCA2 Thresholds CSV | sciencebase.gov/65cd... | CSV/tar.gz | None | County | No | DEFERRED |
| OpenFEMA NFIP | fema.gov/api/open | JSON API | None | County | Yes | CONFIRMED |
| OpenFEMA Disasters | fema.gov/api/open | JSON API | None | County | Yes | CONFIRMED |
| FEMA NFHL | hazards.fema.gov/gis | WMS/WFS | None | Geospatial | Yes | CONFIRMED |
| USGS Water (new) | api.waterdata.usgs.gov | OGC API | None | Station | Partial | CONFIRMED |
| NOAA Atlas 14 | hdsc.nws.noaa.gov/pfds | ASCII | None | Station | Partial | CONFIRMED |
| NOAA CO-OPS | api.tidesandcurrents | JSON/CSV | None | Station | Partial | CONFIRMED |
| Drought Monitor | drought.gov | JSON/GeoJSON | None | County | Yes | CONFIRMED |
| NOAA NCEI (new) | ncei.noaa.gov/access | JSON | Token | Station | Yes | CONFIRMED |
| NWS API | api.weather.gov | JSON-LD | None | UGC/County | Yes | CONFIRMED |
| WA DNR Landslide | gis.dnr.wa.gov | Geodatabase | None | Geospatial | No | CONFIRMED |
| OR DOGAMI SLIDO | oregon.gov/dogami | Geodatabase | None | Geospatial | No | CONFIRMED |
| USGS 3DEP | apps.nationalmap.gov | Raster | None | Geospatial | Partial | CONFIRMED |
| DHS HIFLD Open | hifld-geoplatform | CSV/SHP | None | Geospatial | Partial | CONFIRMED |
| FEMA FRI | (removed) | N/A | N/A | N/A | N/A | UNAVAILABLE |

---

*Sovereignty Scout | Phase 18.5 | 2026-02-17*
*Every finding answers: does this serve the Tribal Leaders who will read these documents?*
*229 Alaska Native communities cannot wait for perfect data. Ship what serves them now, document what is missing honestly, and build the rest in v1.5+.*
