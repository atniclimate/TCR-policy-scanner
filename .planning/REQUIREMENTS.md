# Requirements: v1.4 Climate Vulnerability Intelligence

**Milestone:** v1.4
**Created:** 2026-02-17
**Status:** Roadmap approved -- 28 requirements mapped to 6 phases

## v1.4 Requirements

### Data Registry & Infrastructure (REG)

- [ ] **REG-01**: Data catalog/registry documenting every integrated data source with steward agency, update cadence, spatial resolution, licensing constraints, known limitations, and acquisition URL
- [ ] **REG-02**: Acquisition query logging — all data fetches logged with timestamp, source, query parameters, response size, and status for reproducibility and defensibility
- [ ] **REG-03**: Pydantic schema models for all vulnerability data structures defined before any population scripts (schema-first approach)
- [ ] **REG-04**: Sovereignty-first vulnerability framing vocabulary constants module — approved language for all renderers ("disproportionate exposure to climate hazards," not "vulnerable")

### Core Vulnerability Data (VULN)

- [ ] **VULN-01**: Expanded FEMA NRI metrics — EAL by consequence type (buildings, population, agriculture), national percentiles (RISK_NPCTL), community resilience score (RESL_VALUE) extracted from existing NRI CSV with backward-compatible schema extension
- [ ] **VULN-02**: CDC/ATSDR SVI 2022 integration — 3 themes (socioeconomic, household composition/disability, housing type/transportation) at county level via existing area-weighted crosswalk. Exclude racial/ethnic minority theme per user direction.
- [ ] **VULN-03**: Composite vulnerability score (0-1) per Tribe using FEMA methodology — weighted combination of hazard exposure, social vulnerability, and adaptive capacity deficit with 5 rating tiers (Very High/High/Moderate/Low/Very Low)
- [ ] **VULN-04**: Per-Tribe vulnerability profiles (592 JSON files) in separate vulnerability_profiles/ directory with data provenance metadata

### Flood & Water Data (FLOOD)

- [ ] **FLOOD-01**: NFIP flood insurance data — claims history and policy counts per county from OpenFEMA API, mapped to Tribal lands via crosswalk, with emphasis on costly impacts
- [ ] **FLOOD-02**: FEMA disaster declarations — historical disaster declarations per county from OpenFEMA API, filtered for flood/weather events, mapped to Tribal areas
- [ ] **FLOOD-03**: FEMA National Flood Hazard Layer (NFHL) — flood zone designations from FEMA web services (https://hazards.fema.gov/), mapped to Tribal land boundaries
- [ ] **FLOOD-04**: USGS Water Services — streamflow data and site metadata from USGS Water Data APIs (https://waterservices.usgs.gov/) for gauges near/within Tribal lands
- [ ] **FLOOD-05**: NOAA Atlas 14 — precipitation frequency estimates and extreme rainfall metrics from NOAA HDSC (https://hdsc.nws.noaa.gov/pfds/) at county or station level
- [ ] **FLOOD-06**: NOAA CO-OPS — coastal water levels, tidal records, and flood thresholds from NOAA Tides and Currents API (https://api.tidesandcurrents.noaa.gov/) for coastal Tribal areas

### Climate & Weather Data (CLIM)

- [ ] **CLIM-01**: US Drought Monitor / NOAA-NIDIS — weekly drought severity data at county level, integrated with historical drought patterns for Tribal areas
- [ ] **CLIM-02**: NOAA NCEI Climate Data Online — historical weather and climate records from CDO API (https://www.ncdc.noaa.gov/cdo-web/webservices/) at county/station level
- [ ] **CLIM-03**: NWS API — current forecasts, active alerts, and hazard warnings from National Weather Service API (https://www.weather.gov/documentation/services-web-api) relevant to Tribal areas

### Geologic & Terrain Data (GEO)

- [ ] **GEO-01**: State geological agency landslide data — landslide inventories from WA DNR Open Data (https://data-wadnr.opendata.arcgis.com/) and OR DOGAMI GIS (https://gis.dogami.oregon.gov/) via ArcGIS REST services
- [ ] **GEO-02**: USGS 3DEP elevation/terrain — elevation and terrain datasets from 3D Elevation Program (https://registry.opendata.aws/usgs-lidar/) for hazard screening where terrain context is needed

### Infrastructure Exposure (INFRA)

- [ ] **INFRA-01**: DHS HIFLD infrastructure data — critical infrastructure exposure datasets from Homeland Infrastructure Foundation-Level Data (https://www.dhs.gov/gmo/hifld) mapped to Tribal areas

### Document Generation (DOC)

- [ ] **DOC-01**: Vulnerability sections in Doc A and Doc B — compact vulnerability block in existing per-Tribe documents with audience air gap enforcement (SVI theme decomposition in Doc A only; Doc B shows composite only)
- [ ] **DOC-02**: Doc E standalone vulnerability report — new document type with full-detail per-Tribe vulnerability assessment including all integrated data sources, grant-ready narrative paragraphs, and data citations
- [ ] **DOC-03**: EAL consequence-type breakdown table in documents — buildings/population/agriculture per top hazard for costly impact emphasis

### Website Enhancement (WEB)

- [ ] **WEB-01**: Vulnerability badges in Tribe cards — composite rating and top hazard indicator in search results with ARIA compliance and dark mode support
- [ ] **WEB-02**: On-demand per-Tribe detail loading — vulnerability JSON loaded when user clicks, keeping tribes.json payload under 1.5 MB
- [ ] **WEB-03**: Chart.js visualizations — hazard radar chart and SVI theme bar charts with progressive enhancement

### Cross-Cutting (XCUT)

- [ ] **XCUT-01**: All data sources routed through existing county FIPS crosswalk (tribal_county_area_weights.json) — one geographic truth
- [ ] **XCUT-02**: Zero API calls during document generation — all data pre-cached in population scripts
- [ ] **XCUT-03**: NRI version pinning with SHA256 checksum validation and Connecticut planning region mapping for v1.20 compatibility
- [ ] **XCUT-04**: encoding="utf-8" on all file operations, atomic writes (tmp + os.replace) on all cache files
- [ ] **XCUT-05**: Compliance tests blocking network imports in src/packets/ and enforcing audience air gap for vulnerability content

## Future Requirements (v1.5+)

- [ ] NOAA LOCA2 climate projections (NetCDF, county-level temperature/precipitation change) — deferred due to HIGH complexity and Alaska coverage gaps
- [ ] Hazard trend indicators (needs LOCA2 for forward trajectory)
- [ ] BRIC resilience sub-indicators (verify availability in NRI CSV first)
- [ ] Peer comparison context (percentile among 592 Tribes + ecoregion group)
- [ ] Additional state geological agency integrations beyond WA/OR

## Out of Scope

- Real-time climate modeling or simulation (computationally intractable for a policy tool)
- Tribal-specific data collection or surveys (T0 classification boundary)
- Health impact predictions (requires epidemiological expertise not present)
- Census tract granularity in documents (aggregate to Tribal level only via crosswalk)
- Interactive GIS/map interface (incompatible with static GitHub Pages deployment)
- Proprietary vulnerability scoring methodology (federal credibility requires FEMA/CDC methodology citation)
- Climate adaptation recommendations (requires local knowledge outside scope)
- CDC SVI racial/ethnic minority theme (Theme 3) — excluded per user direction
- Raw gridded climate data (use county-level summaries only)

## Traceability

| Requirement | Phase | Description | Status |
|-------------|-------|-------------|--------|
| REG-01 | Phase 22 | Data catalog/registry | Pending |
| REG-02 | Phase 22 | Acquisition query logging | Pending |
| REG-03 | Phase 19 | Pydantic schema models (schema-first) | Pending |
| REG-04 | Phase 19 | Sovereignty-first framing vocabulary | Pending |
| VULN-01 | Phase 19 | Expanded FEMA NRI metrics | Pending |
| VULN-02 | Phase 19 | CDC/ATSDR SVI 2022 integration | Pending |
| VULN-03 | Phase 22 | Composite vulnerability score | Pending |
| VULN-04 | Phase 22 | Per-Tribe vulnerability profiles | Pending |
| FLOOD-01 | Phase 20 | NFIP flood insurance data | Pending |
| FLOOD-02 | Phase 20 | FEMA disaster declarations | Pending |
| FLOOD-03 | Phase 20 | FEMA NFHL flood zones | Pending |
| FLOOD-04 | Phase 20 | USGS Water Services streamflow | Pending |
| FLOOD-05 | Phase 20 | NOAA Atlas 14 precipitation | Pending |
| FLOOD-06 | Phase 20 | NOAA CO-OPS coastal water levels | Pending |
| CLIM-01 | Phase 21 | US Drought Monitor / NOAA-NIDIS | Pending |
| CLIM-02 | Phase 21 | NOAA NCEI Climate Data Online | Pending |
| CLIM-03 | Phase 21 | NWS API forecasts/alerts | Pending |
| GEO-01 | Phase 21 | State landslide data (WA/OR) | Pending |
| GEO-02 | Phase 21 | USGS 3DEP elevation/terrain | Pending |
| INFRA-01 | Phase 21 | DHS HIFLD infrastructure | Pending |
| DOC-01 | Phase 23 | Vulnerability sections in Doc A/B | Pending |
| DOC-02 | Phase 23 | Doc E standalone vulnerability report | Pending |
| DOC-03 | Phase 23 | EAL breakdown table | Pending |
| WEB-01 | Phase 24 | Vulnerability badges in Tribe cards | Pending |
| WEB-02 | Phase 24 | On-demand detail loading | Pending |
| WEB-03 | Phase 24 | Chart.js visualizations | Pending |
| XCUT-01 | Phase 22 | County FIPS crosswalk (one geographic truth) | Pending |
| XCUT-02 | Phase 22 | Zero API calls during doc generation | Pending |
| XCUT-03 | Phase 19 | NRI version pinning + SHA256 + CT mapping | Pending |
| XCUT-04 | Phase 19 | utf-8 encoding + atomic writes | Pending |
| XCUT-05 | Phase 22 | Compliance tests (network imports, air gap) | Pending |

---
*Created: 2026-02-17*
*Requirements: 28 (REG: 4, VULN: 4, FLOOD: 6, CLIM: 3, GEO: 2, INFRA: 1, DOC: 3, WEB: 3, XCUT: 5)*
*Traceability updated: 2026-02-17 -- all 28 requirements mapped to Phases 19-24*
