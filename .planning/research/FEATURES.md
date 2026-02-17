# Feature Landscape: Climate Vulnerability Intelligence (v1.4)

**Domain:** Climate vulnerability intelligence for Tribal Nations advocacy
**Researched:** 2026-02-17
**Researcher confidence:** MEDIUM-HIGH (data sources verified; some API specifics remain LOW)
**Context:** Adding climate vulnerability dimensions to existing TCR Policy Scanner serving 592 Tribal Nations. Builds on existing FEMA NRI hazard profiles (573/592 coverage, 18 hazard types, area-weighted crosswalk, USFS wildfire override).

---

## Overview

Climate vulnerability intelligence extends the existing hazard profiling system with three new dimensions: (1) deeper risk metrics from expanded FEMA NRI extraction, (2) social vulnerability indicators from CDC/ATSDR SVI, and (3) forward-looking climate projections from NOAA downscaled data. Together these transform per-Tribe profiles from "what hazards exist" to "how vulnerable is this community and how will it change."

**Primary advocacy use cases:**
- **Grant applications** -- citing specific, quantified climate risks with federal data provenance and dollar-denominated loss estimates
- **Congressional testimony** -- local impact narratives backed by authoritative projections and comparative context
- **Resilience planning** -- identifying priority hazards, vulnerable populations, and capacity gaps

**Data classification:** T0 (Open) -- all data from public federal sources. No Tribal-specific or sensitive data.

---

## Table Stakes

Features users expect in any climate vulnerability intelligence product. Missing = product feels incomplete for the stated use cases.

| # | Feature | Why Expected | Complexity | Dependencies | Notes |
|---|---------|-------------|------------|--------------|-------|
| TS-1 | **CDC/ATSDR SVI integration** | Social vulnerability is the standard complement to hazard data in every federal vulnerability framework. FEMA NRI already incorporates a SOVI_SCORE but CDC SVI provides the authoritative 16-variable breakdown across 4 themes. Grant reviewers at FEMA, HUD, and EPA explicitly reference SVI data. The existing SOVI_SCORE is a coarse single-number summary; CDC SVI provides the granular theme-level detail (socioeconomic status, household characteristics, minority status, housing type/transportation) that grant narratives require. | Medium | Existing AIANNH crosswalk, existing area-weighted aggregation pattern from `hazards.py` | SVI 2022 is the current release (May 2024). Available as CSV at census tract and county levels. Download from CDC at https://atsdr.cdc.gov/place-health/php/svi/svi-data-documentation-download.html. Field naming convention: E_ (estimates), EP_ (percentages), EPL_ (percentiles), SPL_ (theme sums), RPL_ (theme rankings), F_ (flags for 90th percentile). Key field: RPL_THEMES (overall SVI ranking, 0-1 scale). Pipeline pattern: download CSV, map census tracts to Tribal areas via existing area-weighted crosswalk, aggregate theme scores, cache as per-Tribe JSON. Closely follows existing `populate_hazards.py` pattern. |
| TS-2 | **Expanded NRI risk metrics** | Current hazard profiles extract only risk_score, eal_total, annualized_freq, and num_events per hazard. The NRI CSV contains richer data that directly supports grant applications: per-hazard EAL broken down by consequence type (buildings, population, agriculture), exposure values, and historic loss ratios. Dollar-denominated risk estimates are what grant reviewers want to see. | Low | Existing `hazards.py` CSV parsing (extend column extraction) | Already reading NRI_Table_Counties.csv. Additional columns to extract per hazard code: `{CODE}_EALB` (EAL buildings $), `{CODE}_EALP` (EAL population $), `{CODE}_EALA` (EAL agriculture $), `{CODE}_EALS` (EAL score percentile), `{CODE}_EXPT` (exposure total $), `{CODE}_HLRT` (historic loss ratio). Backward-compatible schema extension -- existing profile consumers continue to work, new fields are additive. Verified against existing `NRI_HAZARD_CODES` dict and CSV parsing in `hazards.py`. |
| TS-3 | **Composite vulnerability score** | Users need a single summary metric ("How vulnerable is this Tribe?") for quick comparison and grant narratives. The standard methodology in the domain is: Vulnerability = f(Exposure, Sensitivity, Adaptive Capacity). FEMA NRI uses: Risk = EAL x SoVI / Community Resilience. Using the same formula FEMA uses provides methodological credibility. | Medium | TS-1 (SVI for social vulnerability detail), TS-2 (expanded NRI for exposure/loss detail) | FEMA's existing risk equation already combines EAL_SCORE (exposure), SOVI_SCORE (social vulnerability), and RESL_SCORE (community resilience). These composite scores are already extracted per county in `hazards.py` and area-weighted to Tribal level. The composite vulnerability score enriches this with CDC SVI theme-level breakdown. Implementation: per-Tribe composite = weighted combination of NRI risk score + CDC SVI overall + NRI resilience score. Five rating tiers matching NRI: Very High, Relatively High, Relatively Moderate, Relatively Low, Very Low. |
| TS-4 | **Vulnerability profile in DOCX reports** | Doc A/B already have hazard summary sections rendered by `render_hazard_summary()`. Climate vulnerability assessment is the natural next section. Tribal Leaders reviewing briefing documents expect vulnerability context alongside hazard data -- it answers "so what does this mean for our community?" | Medium | TS-1, TS-2, TS-3, existing DocxEngine + `docx_sections.py` | New DOCX section: "Climate Vulnerability Assessment" rendered after hazard summary. Content: composite vulnerability score with rating badge, top 5 hazards with EAL breakdown (buildings/population/agriculture), SVI theme scores with interpretation, data sources with versions. Must respect Doc A vs Doc B audience differentiation: Doc A includes strategic framing ("This positions the Tribe to..."); Doc B presents facts only with neutral language. New function: `render_vulnerability_assessment()` in `docx_sections.py`. |
| TS-5 | **Data provenance and citation** | Grant applications require specific citations to federal data sources. Every number in a vulnerability profile must trace back to a named dataset with version and date. This is already partially implemented (NRI version tracking via `_nri_version` field in hazard profiles). Extend to all data sources. | Low | All data features | Store in profile metadata: FEMA NRI version and download date, CDC SVI vintage year, NOAA data period. Generate APA-style citations for DOCX appendices. Example: "FEMA National Risk Index v1.20 (December 2025). Social Vulnerability Index, CDC/ATSDR, 2022." |
| TS-6 | **Vulnerability display on website** | The GitHub Pages website currently shows Tribe search, state/ecoregion info, and document downloads. Vulnerability data should be visible on the tribe card before download -- gives users immediate value and a reason to engage with the documents. | Medium-High | TS-3 (composite score), existing web infrastructure (Fuse.js search, app.js, tribe card) | Extend tribe card with: composite vulnerability rating (color-coded badge), top 3 hazards with risk ratings, SVI overall percentile indicator. Data pre-computed and embedded in tribes.json search index (static site, no server). Requires updating `build_web_index.py` to include vulnerability fields, and `app.js` to render new card sections. HTML/CSS additions to `index.html` and `style.css`. |

---

## Differentiators

Features that set the product apart from generic vulnerability tools. Not expected, but highly valued by Tribal Leaders doing advocacy work.

| # | Feature | Value Proposition | Complexity | Dependencies | Notes |
|---|---------|-------------------|------------|--------------|-------|
| DF-1 | **NOAA climate projections per Tribe** | Most vulnerability tools stop at current/historical risk. Adding mid-century and late-century projections under multiple emissions scenarios shows how risk will change. Extremely powerful for grant narratives: "By 2060, under higher emissions, extreme heat days in our region are projected to increase from X to Y per year." Forward-looking data is the strongest differentiator for this tool. | High | Existing county-FIPS crosswalk for area-weighted aggregation | **Data source recommendation: NOAA Climate Explorer + LOCA2/CMIP6.** Climate Explorer provides county-level projections (CMIP5/LOCA downscaled) under RCP 4.5 and 8.5 from observed (1950-2013) through projected (2020s-2090s). Variables: avg/max/min temperature, precipitation, degree days, days above thresholds. LOCA2/CMIP6 (from UCSD/USGS) is newer, with SSP 2-4.5, 3-7.0, 5-8.5 scenarios. County-level aggregations confirmed available. **Implementation approach:** Pre-download county CSV data for all 3,107 US counties. Aggregate to Tribal areas using existing area-weighted crosswalk. Cache as per-Tribe climate projection JSON. Key metrics to extract: projected temperature change (mid-century vs baseline), projected precipitation change, extreme heat days (days above 95F/100F/105F), cooling/heating degree days. **Risk:** Bulk download workflow for Climate Explorer county data is unverified -- the web interface allows single-county export but programmatic bulk access needs validation. LOCA2 data from USGS ScienceBase has confirmed county-level CSVs. |
| DF-2 | **Grant-ready vulnerability narratives** | Auto-generate paragraph-length narratives formatted for direct insertion into federal grant applications. "The [Tribe Name] faces significant climate risk from [top hazard], with expected annual losses of $[amount] to buildings and $[amount] to agricultural systems. CDC Social Vulnerability indicators show [rating] vulnerability in socioeconomic status (Xth percentile). Based on FEMA National Risk Index data, the community's composite risk score places it in the [Yth] percentile nationally." This saves Tribal staff hours of grant-writing per application. | Medium | TS-1, TS-2, TS-3, TS-4, TS-5 | Template-based narrative generation. 3-5 templates for different grant contexts (FEMA BRIC, EPA Environmental Justice, HUD CDBG-DR, BIA Climate Resilience, generic). Fill data placeholders with Tribe-specific values. Doc A version includes advocacy framing; Doc B version uses neutral citation style. Each narrative includes inline data citations (TS-5). |
| DF-3 | **Hazard-specific trend indicators** | Show whether each hazard type is increasing, stable, or decreasing. A simple directional indicator (increasing/stable/decreasing) next to each hazard in the profile. Extremely useful for testimony: "Wildfire frequency in our region has increased 40% over the past decade." | Medium | TS-2 (expanded NRI for historical frequency data), optionally DF-1 (for projected trends) | NRI provides `{HAZARD}_EVNTS` (total historical events) and `{HAZARD}_AFREQ` (annualized frequency). Can compute trends by comparing NRI v1.20 frequencies against earlier NRI versions (v1.16, v1.18 archived at FEMA). Climate projections (DF-1) add future trajectory. Even without projections, historical trend alone is valuable. Display as arrow icon in DOCX and website. |
| DF-4 | **Community resilience sub-indicators** | FEMA NRI includes RESL_SCORE based on BRIC (Baseline Resilience Indicators for Communities) from University of South Carolina. BRIC has 6 sub-categories: social, economic, community capital, institutional, infrastructural, environmental. Exposing sub-scores helps Tribes identify which resilience dimensions need investment and which grant programs to target. | Medium | Existing NRI data (verify if BRIC sub-scores in NRI CSV), potentially separate BRIC data download | NRI CSV includes RESL_SCORE and RESL_RATNG at county level. **Whether BRIC sub-category scores are included in the NRI CSV columns needs verification during implementation.** If not in NRI CSV, BRIC data may need separate download from USC Hazards and Vulnerability Research Institute. This is a LOW confidence item -- flag for implementation-time research. |
| DF-5 | **Comparative vulnerability context** | Show a Tribe's vulnerability relative to: state average, national average, and ecoregion peer group. "Your wildfire risk score of 78 places you in the 92nd percentile among Pacific Northwest Tribes." Provides crucial advocacy context: "We face disproportionate risk compared to..." | Low-Medium | TS-3 (composite score), existing registry (ecoregion data from Phase 5) | Compute percentile rankings across the 592-Tribe dataset. Group by ecoregion (already in registry). Store distribution statistics (mean, median, percentiles) in a summary JSON. Display in DOCX as contextual sentence and in website as percentile bar. |
| DF-6 | **Interactive vulnerability visualization on website** | Beyond basic vulnerability indicators (TS-6), add visual charts: hazard radar/spider chart showing relative risk across hazard types, SVI theme breakdown bar chart, and vulnerability trend sparkline. Chart.js (~200KB) or similar lightweight library. | Medium-High | TS-6, TS-3, all data features | Progressive enhancement pattern: charts render if JavaScript loads, fall back to text badges if not. Chart.js works without build step (CDN or vendored script). Must work in static site context (no server). All data pre-computed in tribes.json. Radar chart shows 5-8 top hazard types with normalized scores. SVI bar chart shows 4 theme percentiles. No interactive filtering needed -- single Tribe display only. |
| DF-7 | **EAL breakdown by consequence type** | Display Expected Annual Loss split into buildings ($), population ($), and agriculture ($) per hazard type. Helps Tribes identify whether their risk is primarily to infrastructure, human health, or food/agricultural systems. Critical for targeting the right grant programs: infrastructure damage -> FEMA BRIC; population impact -> HHS/ASPR; agriculture loss -> USDA. | Low | TS-2 (expanded NRI extraction provides the data) | NRI CSV columns `{CODE}_EALB`, `{CODE}_EALP`, `{CODE}_EALA` provide the three consequence-type breakdowns per hazard. Already area-weighted per existing methodology. Display as table in DOCX (top 5 hazards with 3-column EAL breakdown) and as stacked bar in website visualization (DF-6). Smallest additional effort once TS-2 extracts the data. |

---

## Anti-Features

Features to explicitly NOT build. Common mistakes in the climate vulnerability domain.

| # | Anti-Feature | Why Avoid | What to Do Instead |
|---|-------------|-----------|-------------------|
| AF-1 | **Real-time climate modeling or simulation** | Computationally intractable, scientifically inappropriate for a policy tool, and creates false precision. Climate modeling is a multi-institution, supercomputer-scale endeavor. Running climate models is not what this tool does. | Consume pre-computed projections from authoritative federal sources (NOAA Climate Explorer, LOCA2/CMIP6 from USGS). Present their data with proper citation, not our own calculations. |
| AF-2 | **Tribal-specific data collection or surveys** | Violates T0 data classification. Collecting data about Tribal communities raises sovereignty and privacy concerns. The Tribal Climate Adaptation Guidebook explicitly notes that vulnerability assessments should braid western science with Traditional Knowledge -- but that braiding is for Tribes to do, not for this tool. | Use only federally published public datasets (NRI, SVI, NOAA, USFS). Acknowledge data limitations transparently. Let Tribes supplement with their own Traditional Knowledge -- our tool provides the federal data baseline. |
| AF-3 | **Health impact predictions** | Projecting specific health outcomes (mortality, morbidity, disease incidence) from climate data requires epidemiological expertise and peer review. Wrong predictions could harm advocacy credibility and create liability. | Present CDC SVI health-adjacent indicators (disability status, age demographics, uninsured populations) as vulnerability factors without projecting outcomes. Link to CDC Climate and Health resources and EPA Environmental Justice screening tool (EJScreen) for health-specific analysis. |
| AF-4 | **Census tract-level granularity in reports** | Most Tribal areas span multiple census tracts. Showing tract-level data creates noise without actionable insight for Tribal Leaders. Census tract boundaries do not align with Tribal governance boundaries. | Aggregate census tract data to Tribal area level using existing area-weighted crosswalk methodology (proven in Phase 13). Show single composite scores per Tribe, not per-tract breakdowns. Maintain tract-level data in pipeline internals for accuracy; present Tribe-level summaries in outputs. |
| AF-5 | **Interactive GIS/map interface** | Building a map-based interface requires a tile server, geographic data pipeline, and ongoing hosting costs incompatible with static GitHub Pages deployment. The existing site is a static file distribution system, not a GIS application. | Use pre-computed vulnerability scores and display as cards/charts on existing static site. Provide links to FEMA NRI Interactive Map (https://hazards.fema.gov/nri/map) and CDC SVI Interactive Map for users who want geographic exploration. These official tools are already built and maintained by federal agencies. |
| AF-6 | **Proprietary vulnerability scoring methodology** | Inventing a novel vulnerability index invites methodological criticism and reduces trust with grant reviewers. Federal grant applications work best when citing recognized federal frameworks. | Use FEMA NRI's own risk equation (Risk = EAL x SoVI / Community Resilience) as the composite methodology. Cite it explicitly. For SVI integration, use CDC's published percentile ranking methodology. Transparency in methodology builds trust with reviewers. |
| AF-7 | **Climate adaptation recommendations** | Generating specific adaptation strategies (e.g., "build seawalls," "relocate infrastructure," "implement drought-resistant crops") requires local engineering, ecological, and cultural knowledge we don't have. Generic recommendations could be harmful or culturally inappropriate. | Present vulnerability data and risk context. Link to Tribal Climate Adaptation Guidebook (tribalclimateadaptationguidebook.org), BIA Tribal Climate Resilience Program for adaptation planning support, and UW Climate Impacts Group Tribal tools (cig.uw.edu/resources/tribal-vulnerability-assessment-resources/). |
| AF-8 | **Real-time weather or extreme event alerts** | This is a policy intelligence and advocacy tool, not an emergency management system. Weather alerting requires 24/7 monitoring infrastructure, push notification systems, and liability frameworks that are far outside scope. | Present historical and projected climate trends for planning and advocacy. Link to NWS alerts and FEMA Emergency Alert System for real-time information. |

---

## Feature Dependencies

```
TS-2 (Expanded NRI) -----> TS-3 (Composite Score) -----> TS-4 (DOCX Section)
                    \                              \
                     \                              --> DF-2 (Grant Narratives)
                      \
                       --> DF-7 (EAL Breakdown)     --> TS-6 (Website Display)
                                                         |
TS-1 (CDC SVI) ---------> TS-3 (Composite Score)        |
                                    |                    v
                                    v               DF-6 (Visualization)
                              DF-5 (Peer Context)

DF-1 (NOAA Projections) --> DF-3 (Trend Indicators)
                        \
                         --> DF-2 (Grant Narratives, enhanced)

TS-5 (Data Provenance) --- independent, threads through all outputs

DF-4 (Resilience Sub-indicators) --- extends existing NRI data (independent track)
```

**Critical path:** TS-2 (Expanded NRI) -> TS-1 (CDC SVI) -> TS-3 (Composite Score) -> TS-4 (DOCX) -> TS-6 (Website)

**Independent parallel tracks:**
- DF-1 (NOAA Projections) can proceed in parallel with SVI integration but is highest risk
- TS-5 (Data Provenance) threads through all features with no upstream dependencies
- DF-4 (Resilience Sub-indicators) depends only on NRI CSV verification

---

## Data Source Inventory

### Available Federal Data Sources (Verified)

| Source | Data | Geographic Level | Format | Access Method | Status | Confidence |
|--------|------|------------------|--------|---------------|--------|------------|
| FEMA NRI v1.20 | 18 hazard types, EAL (total + by consequence type), risk/exposure/frequency scores, SoVI, BRIC resilience | County, Census Tract | CSV, Shapefile, GDB | OpenFEMA download | ALREADY INTEGRATED (partially) | HIGH |
| CDC/ATSDR SVI 2022 | 16 variables, 4 themes, percentile rankings (0-1) | Census Tract, County, ZCTA | CSV, Shapefile | CDC data download page | NOT YET INTEGRATED | HIGH |
| NOAA Climate Explorer | Temperature, precipitation, degree days, extreme day counts (observed 1950-2013, projected through 2090s under RCP 4.5/8.5) | County (FIPS) | CSV via web export | Web interface with per-county data export | NOT YET INTEGRATED | MEDIUM |
| NOAA nClimGrid | Monthly temperature (avg/max/min), precipitation (1895-present) | County (FIPS), gridded | CSV, NetCDF | FTP, AWS Open Data | NOT YET INTEGRATED | HIGH |
| LOCA2/CMIP6 | Downscaled projections (temperature, precipitation) under SSP 2-4.5, 3-7.0, 5-8.5 (1950-2100) | County aggregations, 6km gridded | NetCDF, CSV | UCSD LOCA server, USGS ScienceBase | NOT YET INTEGRATED | MEDIUM |
| NRI Tribal Relational CSV | AIANNH GEOID -> county FIPS mapping | AIANNH areas | CSV | FEMA download | ALREADY INTEGRATED | HIGH |
| Census AIANNH Shapefiles | Tribal area boundaries (TIGER/Line) | National | Shapefile | Census Bureau | ALREADY INTEGRATED (crosswalk built) | HIGH |
| NOAA CDO API | Historical weather observations by station/county | Station, County (FIPS) | JSON, CSV | REST API (free token, 10K req/day) | NOT YET INTEGRATED | HIGH |

### CDC/ATSDR SVI 2022 Variables (16 variables, 4 themes)

**Theme 1: Socioeconomic Status**
1. Below 150% poverty (EP_POV150 / EPL_POV150)
2. Unemployed (EP_UNEMP / EPL_UNEMP)
3. Housing cost burden (EP_HBURD / EPL_HBURD)
4. No health insurance (EP_UNINSUR / EPL_UNINSUR)
5. No high school diploma (EP_NOHSDP / EPL_NOHSDP)

**Theme 2: Household Characteristics**
6. Aged 65 and older (EP_AGE65 / EPL_AGE65)
7. Aged 17 and younger (EP_AGE17 / EPL_AGE17)
8. Civilian with a disability (EP_DISABL / EPL_DISABL)
9. Single-parent households (EP_SNGPNT / EPL_SNGPNT)
10. English language proficiency (EP_LIMENG / EPL_LIMENG)

**Theme 3: Racial and Ethnic Minority Status**
11-16. Six racial/ethnic categories with percentile rankings

**Theme summaries:** RPL_THEME1 through RPL_THEME4 (0-1 percentile for each theme)
**Overall SVI:** RPL_THEMES (composite 0-1 percentile)
**Flags:** F_THEME1 through F_THEME4, F_TOTAL (1 if in 90th percentile)

**Confidence:** MEDIUM -- variable list reconstructed from multiple documentation sources. Exact 2022 field names (especially Theme 3 which changed from prior years) must be verified against actual CSV download during implementation.

### NRI CSV Columns: Currently Extracted vs. Needed

| Field Pattern | Meaning | Currently Extracted | Action |
|---------------|---------|---------------------|--------|
| `{CODE}_RISKS` | Risk score (percentile) | YES | Keep |
| `{CODE}_RISKR` | Risk rating (text) | YES | Keep |
| `{CODE}_EALT` | Expected Annual Loss total ($) | YES | Keep |
| `{CODE}_AFREQ` | Annualized frequency | YES | Keep |
| `{CODE}_EVNTS` | Number of events | YES | Keep |
| `{CODE}_EALB` | EAL - Buildings ($) | NO | **Add in TS-2** |
| `{CODE}_EALP` | EAL - Population ($) | NO | **Add in TS-2** |
| `{CODE}_EALA` | EAL - Agriculture ($) | NO | **Add in TS-2** |
| `{CODE}_EALS` | EAL score (percentile) | NO | **Add in TS-2** |
| `{CODE}_EXPT` | Exposure total ($) | NO | **Add in TS-2** |
| `{CODE}_HLRT` | Historic loss ratio | NO | **Add in TS-2** |
| `SOVI_SCORE` | Social Vulnerability score | YES (composite) | Keep |
| `SOVI_RATNG` | Social Vulnerability rating | YES (composite) | Keep |
| `RESL_SCORE` | Community Resilience score | YES (composite) | Keep |
| `RESL_RATNG` | Community Resilience rating | YES (composite) | Keep |
| `RISK_SCORE` | Overall Risk score | YES | Keep |
| `EAL_VALT` | Total EAL all hazards ($) | YES | Keep |

**NRI hazard codes (18):** AVLN, CFLD, CWAV, DRGT, ERQK, HAIL, HWAV, HRCN, ISTM, IFLD, LNDS, LTNG, SWND, TRND, TSUN, VLCN, WFIR, WNTW
(Verified from existing `NRI_HAZARD_CODES` dict in `src/packets/hazards.py`)

---

## Vulnerability Assessment Framework

The standard vulnerability assessment framework used by federal agencies and documented in the U.S. Climate Resilience Toolkit and Tribal Climate Adaptation Guidebook:

**Vulnerability = f(Exposure, Sensitivity, Adaptive Capacity)**

| Component | What It Measures | Data Sources in TCR | Existing? |
|-----------|------------------|---------------------|-----------|
| **Exposure** | Presence of assets in places affected by climate hazards | FEMA NRI hazard scores + EAL, NOAA climate projections | Partial (NRI integrated, NOAA not yet) |
| **Sensitivity** | Degree to which assets are affected | CDC SVI (social factors), NRI EAL by consequence type | No (SVI not integrated, EAL breakdown not extracted) |
| **Adaptive Capacity** | Ability to cope with and recover from impacts | FEMA NRI RESL_SCORE (Community Resilience/BRIC), SVI economic indicators | Partial (RESL_SCORE integrated as composite) |

### Assessment Approaches Documented for Tribal Nations

From the Tribal Climate Adaptation Guidebook, five approaches used by Tribes:

1. **Qualitative staff input** (Tohono O'odham Nation) -- staff-driven assessment using local knowledge
2. **Vulnerability and risk assessment** (Confederated Salish and Kootenai Tribes) -- matrix-based scoring
3. **Guided staff input** (Jamestown S'Klallam Tribe) -- structured workshops with data support
4. **Vulnerability indexing** (Shoshone-Bannock Tribes) -- quantitative index from federal data
5. **Multi-criteria analysis** (Swinomish Indian Tribal Community) -- weighted multi-factor scoring

TCR Policy Scanner serves approach #4 (vulnerability indexing from federal data). Tribal Nations can layer their own Traditional Knowledge and staff input (approaches #1-3, #5) on top of our federal data baseline.

---

## MVP Recommendation (v1.4 Scope)

### Phase 1: Data Foundation (Build First)

Extend existing data pipeline with minimal architectural risk. All features follow proven patterns from Phase 13 hazard profiling.

1. **TS-2: Expanded NRI risk metrics** -- LOW complexity. Extend existing CSV column extraction in `_load_nri_county_data()` to pull 6 additional fields per hazard type. Backward-compatible schema extension. Same area-weighted aggregation. Immediate value: dollar-denominated EAL breakdowns for grant applications.

2. **TS-1: CDC/ATSDR SVI integration** -- MEDIUM complexity. New pipeline following proven pattern: download SVI 2022 CSV -> map census tracts to Tribal areas via existing crosswalk -> aggregate theme scores with area weighting -> cache as per-Tribe JSON. New files: `scripts/download_svi_data.py`, `scripts/populate_svi.py`, `src/packets/svi.py`. Pattern closely mirrors `scripts/populate_hazards.py` + `src/packets/hazards.py`.

3. **TS-3: Composite vulnerability score** -- MEDIUM complexity. Combine NRI risk score + CDC SVI overall + NRI resilience into single per-Tribe composite. Use FEMA's own equation for methodological credibility. Five rating tiers. Depends on TS-1 and TS-2.

4. **TS-5: Data provenance and citation** -- LOW complexity. Metadata tracking threaded through all outputs. Extend existing `generated_at` and `version` patterns.

### Phase 2: Report Integration (Build Second)

Surface new data in documents. Extend existing DOCX rendering infrastructure.

5. **TS-4: Vulnerability profile in DOCX** -- MEDIUM complexity. New `render_vulnerability_assessment()` function in `docx_sections.py`. Composite score with badge, top hazards with EAL breakdown, SVI themes, data citations. Audience-differentiated (Doc A strategy vs Doc B facts).

6. **DF-7: EAL by consequence type** -- LOW complexity. Table in DOCX showing buildings/population/agriculture split for top 5 hazards. Data already available from TS-2.

7. **DF-2: Grant-ready narratives** -- MEDIUM complexity. Template-based paragraph generation. High value for Tribal staff time savings.

8. **DF-5: Comparative vulnerability** -- LOW-MEDIUM complexity. Percentile rankings across 592 Tribes grouped by ecoregion. Contextual sentence in DOCX.

### Phase 3: Web Integration (Build Third)

Update website to display vulnerability data.

9. **TS-6: Website vulnerability display** -- MEDIUM-HIGH complexity. Extend tribe card, update search index JSON, add vulnerability badges.

10. **DF-6: Vulnerability visualization** -- MEDIUM-HIGH complexity. Chart.js radar chart for hazards, bar chart for SVI themes. Progressive enhancement.

### Defer to v1.5+

- **DF-1: NOAA climate projections** -- HIGH complexity, HIGH value, HIGH risk. New data pipeline with uncertain bulk download workflow. Needs dedicated research sprint to validate data access before committing. Recommend as v1.5 headline feature.
- **DF-3: Hazard trend indicators** -- Partially feasible with historical NRI data alone; full implementation needs DF-1.
- **DF-4: Community resilience sub-indicators (BRIC sub-scores)** -- Blocked on verifying whether BRIC sub-scores exist in NRI CSV or require separate data source.

---

## Feature Prioritization Matrix

| Feature | User Value | Technical Risk | Complexity | Data Available? | Priority |
|---------|-----------|---------------|------------|-----------------|----------|
| TS-2: Expanded NRI | HIGH | LOW | LOW | YES (same CSV already loaded) | **P0 -- Do first** |
| TS-1: CDC SVI | HIGH | LOW | MEDIUM | YES (CSV download from CDC) | **P0 -- Do first** |
| TS-3: Composite Score | HIGH | LOW | MEDIUM | YES (derived from TS-1 + TS-2) | **P0 -- After TS-1/2** |
| TS-5: Provenance | MEDIUM | LOW | LOW | N/A (metadata) | **P0 -- Thread through** |
| TS-4: DOCX Vulnerability | HIGH | LOW | MEDIUM | YES (from data pipeline) | **P1 -- After data** |
| DF-7: EAL Breakdown | MEDIUM | LOW | LOW | YES (from TS-2 extraction) | **P1 -- With TS-4** |
| DF-2: Grant Narratives | HIGH | LOW | MEDIUM | YES (from data) | **P1 -- After TS-4** |
| DF-5: Peer Context | MEDIUM | LOW | LOW-MED | YES (derived from 592 Tribes) | **P1 -- After TS-3** |
| TS-6: Website Display | MEDIUM | MEDIUM | MEDIUM-HIGH | YES (pre-computed) | **P2 -- After reports** |
| DF-6: Web Visualization | LOW-MED | MEDIUM | MEDIUM-HIGH | YES (pre-computed) | **P2 -- After TS-6** |
| DF-1: NOAA Projections | HIGH | HIGH | HIGH | MAYBE (bulk download TBD) | **P3 -- v1.5 candidate** |
| DF-3: Trend Indicators | MEDIUM | MEDIUM | MEDIUM | PARTIAL (historical yes, projected no) | **P3 -- After DF-1** |
| DF-4: BRIC Sub-scores | LOW-MED | MEDIUM | MEDIUM | UNKNOWN (verify in NRI CSV) | **P3 -- Verify first** |

---

## Tribal Advocacy Use Case Mapping

### Grant Applications

**Data points that directly support grant writing (features in parentheses):**
- Total Expected Annual Loss in dollars (TS-2)
- EAL broken down by buildings/population/agriculture -- targets grant program type (DF-7)
- Top hazards with risk scores, ratings, and dollar impact (existing + TS-2 enrichment)
- Social vulnerability percentile with theme-level breakdown (TS-1)
- Composite vulnerability score with methodology citation to FEMA NRI (TS-3)
- Federal data provenance citations formatted for appendices (TS-5)
- Pre-written vulnerability narrative paragraph ready for insertion (DF-2)
- Comparative context: "92nd percentile among Pacific NW Tribes" (DF-5)
- Future: Climate projections for 2040/2060 planning horizons (DF-1, v1.5)

### Congressional Testimony

**Data points that support persuasive testimony:**
- Overall vulnerability rating with plain-language explanation (TS-3)
- Specific hazard trends with directional indicators (DF-3)
- Future projections: "by 2060, extreme heat days projected to increase Y%" (DF-1, v1.5)
- Dollar-denominated risk: "$X million in expected annual losses" (TS-2)
- Social vulnerability factors: "X% of our community below poverty" (TS-1)
- Peer comparison: "more vulnerable than X% of Tribes in our state" (DF-5)
- EAL by consequence: "most of our risk is to agricultural systems" (DF-7)

### Resilience Planning

**Data points that support internal planning:**
- All 18 hazard types ranked by risk score (existing + TS-2 enrichment)
- EAL breakdown showing infrastructure vs population vs agriculture risk (DF-7)
- SVI themes identifying most vulnerable population segments (TS-1)
- Community resilience sub-indicators showing capacity gaps (DF-4, v1.5)
- Climate projections for 20/40/60 year planning horizons (DF-1, v1.5)
- Trend indicators showing which hazards are worsening (DF-3)

---

## Implementation Patterns (from existing codebase)

The existing hazard profiling pipeline (`src/packets/hazards.py`, `scripts/populate_hazards.py`) establishes patterns that new vulnerability features should follow:

| Pattern | Existing Example | New Feature Application |
|---------|-----------------|------------------------|
| Download script | `scripts/download_nri_data.py` | `scripts/download_svi_data.py`, `scripts/download_noaa_data.py` |
| Population script | `scripts/populate_hazards.py` | `scripts/populate_svi.py`, `scripts/populate_climate_projections.py` |
| Builder class | `HazardProfileBuilder` in `hazards.py` | `SVIProfileBuilder` in `svi.py`, `ClimateProjectionBuilder` in `climate.py` |
| Area-weighted aggregation | `_build_tribe_nri_profile()` with `norm_weights` | Same crosswalk, same weight normalization, same aggregation |
| Per-Tribe JSON cache | `data/hazard_profiles/{tribe_id}.json` | `data/svi_profiles/{tribe_id}.json`, `data/climate_profiles/{tribe_id}.json` |
| Coverage report | `outputs/hazard_coverage_report.json` | `outputs/svi_coverage_report.json` |
| Score-to-rating conversion | `score_to_rating()` quintile thresholds | Reuse for composite vulnerability rating |
| Atomic file writes | `tempfile.mkstemp()` + `os.replace()` | Same pattern in all new cache writers |
| Path management | `src/paths.py` constants | Add SVI_DIR, SVI_PROFILES_DIR, CLIMATE_DIR, etc. |
| Config integration | `config["packets"]["hazards"]` | `config["packets"]["svi"]`, `config["packets"]["climate"]` |

---

## Sources

### HIGH Confidence (Official Documentation + Verified Code)

- FEMA National Risk Index: https://www.fema.gov/flood-maps/products-tools/national-risk-index
- FEMA NRI Data v1.20 (December 2025): https://www.fema.gov/about/openfema/data-sets/national-risk-index-data
- CDC/ATSDR SVI main page: https://www.atsdr.cdc.gov/place-health/php/svi/index.html
- CDC SVI Data Download: https://atsdr.cdc.gov/place-health/php/svi/svi-data-documentation-download.html
- CDC SVI 2022 Documentation PDF: https://www.atsdr.cdc.gov/place-health/media/pdfs/2024/10/SVI2022Documentation.pdf
- Existing `src/packets/hazards.py` -- verified NRI field patterns and aggregation methodology from production code
- Existing `scripts/populate_hazards.py` -- verified pipeline orchestration pattern
- NOAA CDO API documentation: https://www.ncdc.noaa.gov/cdo-web/webservices/v2
- NOAA nClimGrid county data: https://www.ncei.noaa.gov/news/noaa-offers-climate-data-counties

### MEDIUM Confidence (WebSearch Verified with Official Source)

- NOAA Climate Explorer: https://crt-climate-explorer.nemac.org/about/
- LOCA2/CMIP6 downscaled projections: https://loca.ucsd.edu/
- USGS LOCA2 county-level data: https://www.usgs.gov/data/cmip6-loca2-temperature-and-precipitation-variables-resilient-roadway-design-1950-2100
- U.S. Climate Resilience Toolkit vulnerability framework: https://toolkit.climate.gov/assess-vulnerability-and-risk
- Tribal Climate Adaptation Guidebook: https://tribalclimateadaptationguidebook.org/step-3-assess-vulnerability/
- UW Climate Impacts Group Tribal resources: https://cig.uw.edu/resources/tribal-vulnerability-assessment-resources/
- FEMA NRI Community Resilience (BRIC): https://hazards.fema.gov/nri/community-resilience

### LOW Confidence (WebSearch Only, Needs Implementation-Time Validation)

- SVI 2022 exact 16-variable field names -- reconstructed from multiple documentation sources; Theme 3 changed from prior SVI years; must verify against actual CSV column headers during download
- BRIC sub-category score availability in NRI CSV -- not confirmed in any documentation; may require separate USC HVRI data download
- NOAA Climate Explorer programmatic bulk download -- web interface confirmed, but county-level CSV bulk export for all 3,107 counties needs validation
- LOCA2 county-level CSV pre-aggregation download workflow -- confirmed in USGS ScienceBase catalog but actual download process untested

---

*Research completed: 2026-02-17*
*Mode: Ecosystem (Feature Landscape -- Climate Vulnerability Intelligence)*
*Ready for requirements definition: YES*
