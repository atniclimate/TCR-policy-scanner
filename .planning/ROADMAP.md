# Roadmap: v1.4 Climate Vulnerability Intelligence

**Milestone:** v1.4
**Created:** 2026-02-17
**Phases:** 7 (Phase 18.5 + Phases 19-24, continuing from v1.3 Phase 18)
**Depth:** Quick
**Coverage:** 28/28 requirements mapped + architectural review pre-phase

## Overview

v1.4 adds comprehensive climate vulnerability intelligence to the TCR Policy Scanner. The milestone integrates 12+ federal data sources (expanded FEMA NRI, CDC/ATSDR SVI, NFIP flood insurance, FEMA disaster declarations, NFHL flood zones, USGS streamflow, NOAA Atlas 14, NOAA CO-OPS, drought monitor, NCEI climate data, NWS alerts, state landslide inventories, USGS 3DEP terrain, DHS HIFLD infrastructure) into per-Tribe vulnerability profiles, renders them in existing documents and a new standalone vulnerability report (Doc E), and surfaces vulnerability data on the production website. All data routes through the existing county FIPS crosswalk. Schema-first development and sovereignty-first framing vocabulary are established before any data population or rendering begins.

## Phases

---

### Phase 18.5: Architectural Review & Scaffolding

**Goal:** Ground-truth the v1.4 architecture against the actual codebase and current data sources before any code is written. Four Research Team agents (Sovereignty Scout, Fire Keeper, River Runner, Horizon Walker) validate data source accessibility, extract codebase patterns, design Pydantic schemas, and evaluate vulnerability framing through a sovereignty lens. Produces an Architecture Delta Report with GO/REVISE decision.

**Dependencies:** None (pre-phase, runs before Phase 19)

**Requirements:** None (this phase produces architectural validation, not feature code)

**Success Criteria:**
1. Every data source in the architecture has a verified status (CONFIRMED/CHANGED/UNAVAILABLE) with evidence from live endpoint checks
2. Codebase pattern specification exists grounded in actual code inspection via GitHub MCP, not architecture assumptions
3. Draft Pydantic schemas for vulnerability profiles are written with explicit edge case handling for missing data
4. Composite vulnerability score has been evaluated through a sovereignty lens with alternative framing options proposed
5. At least one data point traced source-to-document with information loss identified at each stage
6. Architecture Delta Report identifies all changes needed to ARCHITECTURE.md before Phase 19 execution
7. GO/REVISE decision made: either the 6-phase plan proceeds as designed, or specific modifications are documented

**Agent Assignments:**
- Sovereignty Scout: Data source validation (NRI fields, CDC SVI endpoint, LOCA2 format, Alaska gap, FEMA FRI status)
- Fire Keeper: Codebase pattern analysis (HazardProfileBuilder template, renderer catalog, tech debt, dependency audit)
- River Runner: Schema design (Pydantic models, composite score edge cases, coverage report spec, test architecture)
- Horizon Walker: Narrative framing (sovereignty lens, information loss audit, multi-format readiness, visualization specs)

**Execution:** Wave 1 (Scout + Fire Keeper parallel) -> Wave 2 (River Runner + Horizon Walker parallel) -> Synthesis

**Detail plan:** `.planning/PHASE-18.5-ARCHITECTURAL-REVIEW.md`

---

### Phase 19: Schema & Core Data Foundation

**Goal:** Pydantic schemas, sovereignty-first framing vocabulary, expanded NRI metrics, and CDC/ATSDR SVI data are validated and cached -- establishing the data contracts and core vulnerability inputs that all subsequent phases depend on.

**Dependencies:** None (first phase of milestone)

**Requirements:**
- REG-03: Pydantic schema models for all vulnerability data structures (schema-first)
- REG-04: Sovereignty-first vulnerability framing vocabulary constants module
- VULN-01: Expanded FEMA NRI metrics (EAL by consequence type, national percentiles, community resilience)
- VULN-02: CDC/ATSDR SVI 2022 integration (3 themes at county level via area-weighted crosswalk)
- XCUT-03: NRI version pinning with SHA256 checksum and CT planning region mapping
- XCUT-04: encoding="utf-8" on all file operations, atomic writes on all cache files

**Plans:** 6 plans

Plans:
- [ ] 19-01-PLAN.md -- Pre-phase tech debt: fix FY26 hardcodes, add path constants, add context field
- [ ] 19-02-PLAN.md -- REG-03: Vulnerability Pydantic v2 schema models (TDD)
- [ ] 19-03-PLAN.md -- REG-04: Sovereignty-first vocabulary constants module
- [ ] 19-04-PLAN.md -- VULN-01 + XCUT-03: NRI expanded builder with version pinning and CT FIPS
- [ ] 19-05-PLAN.md -- VULN-02: SVI 2022 builder with sentinel handling and 3-theme composite
- [ ] 19-06-PLAN.md -- XCUT-04: Integration tests and encoding/atomic write compliance

**Success Criteria:**
1. Running `python -c "from src.schemas.vulnerability import ..."` imports all vulnerability Pydantic models without error, and each model validates sample data with correct field types and constraints
2. A VULNERABILITY_FRAMING constants module exists with approved language, and importing it provides string constants that renderers will use instead of raw vulnerability terminology
3. Regenerated hazard profiles for all 592 Tribes contain EAL breakdown by consequence type (buildings, population, agriculture), national risk percentile (RISK_NPCTL), and community resilience score (RESL_VALUE) -- and all previously existing fields remain unchanged (regression test passes)
4. CDC/ATSDR SVI 2022 data for 3 themes (socioeconomic, household composition/disability, housing type/transportation) is parsed at county level and aggregated to Tribal areas via the existing area-weighted crosswalk, with coverage reported as percentage of 592 Tribes
5. NRI CSV loading validates version and column headers on startup, rejects unexpected schema changes, maps Connecticut planning region FIPS codes correctly, and all new cache files use atomic writes with utf-8 encoding

---

### Phase 20: Flood & Water Data

**Goal:** Six flood and water data sources are fetched, parsed, and cached per Tribe -- giving the vulnerability pipeline comprehensive flood exposure, insurance loss history, disaster declaration history, streamflow context, extreme precipitation metrics, and coastal water level data.

**Dependencies:** Phase 19 (Pydantic schemas define the cache structure; XCUT-04 atomic write patterns established)

**Requirements:**
- FLOOD-01: NFIP flood insurance data (claims history, policy counts per county from OpenFEMA)
- FLOOD-02: FEMA disaster declarations (historical flood/weather events per county from OpenFEMA)
- FLOOD-03: FEMA NFHL flood zone designations mapped to Tribal lands
- FLOOD-04: USGS Water Services streamflow data for gauges near/within Tribal lands
- FLOOD-05: NOAA Atlas 14 precipitation frequency estimates at county/station level
- FLOOD-06: NOAA CO-OPS coastal water levels and flood thresholds for coastal Tribal areas

**Plans:** 7 plans

Plans:
- [ ] 20-01-PLAN.md -- Flood Pydantic schemas, shared infrastructure, path constants, reference data
- [ ] 20-02-PLAN.md -- FLOOD-01: NFIP flood insurance builder (OpenFEMA claims)
- [ ] 20-03-PLAN.md -- FLOOD-02: Disaster declarations builder (OpenFEMA + PA/HMGP dollar joins)
- [ ] 20-04-PLAN.md -- FLOOD-03: NFHL community status builder (OpenFEMA Community Status Book)
- [ ] 20-05-PLAN.md -- FLOOD-04: USGS streamflow builder (OGC API + dataretrieval peak flows)
- [ ] 20-06-PLAN.md -- FLOOD-05 + FLOOD-06: Atlas 14 precipitation + NOAA CO-OPS coastal builders
- [ ] 20-07-PLAN.md -- CLI orchestrator, combined FloodProfile, coverage report

**Success Criteria:**
1. For a sample coastal Tribe and a sample inland Tribe, running the flood data population script produces cached JSON files containing NFIP claims/policies, disaster declarations, flood zone designations, nearby streamflow gauges, precipitation frequency estimates, and (for coastal Tribe) tidal/water level data -- all with data provenance metadata
2. All six flood data sources route through the existing county FIPS crosswalk (tribal_county_area_weights.json) with no new geographic bridge files created
3. Population scripts log every API fetch with timestamp, source URL, query parameters, response size, and HTTP status -- and these logs are queryable for reproducibility
4. Coverage report shows percentage of 592 Tribes with data from each flood source (coastal sources expected to cover only coastal Tribes; NFIP and disaster declarations expected to cover most Tribes)

---

### Phase 21: Climate, Geologic & Infrastructure Data

**Goal:** Drought monitoring, historical climate records, NWS hazard alerts, state landslide inventories, terrain screening data, and critical infrastructure exposure are fetched, parsed, and cached per Tribe -- completing the full data source inventory for vulnerability profiling.

**Dependencies:** Phase 19 (Pydantic schemas, atomic write patterns), Phase 20 (flood data population patterns established and reusable)

**Requirements:**
- CLIM-01: US Drought Monitor / NOAA-NIDIS weekly drought severity at county level
- CLIM-02: NOAA NCEI Climate Data Online historical weather/climate records
- CLIM-03: NWS API current forecasts, active alerts, and hazard warnings for Tribal areas
- GEO-01: State geological agency landslide data (WA DNR, OR DOGAMI via ArcGIS REST)
- GEO-02: USGS 3DEP elevation/terrain datasets for hazard screening
- INFRA-01: DHS HIFLD critical infrastructure exposure mapped to Tribal areas

**Success Criteria:**
1. For a sample Pacific Northwest Tribe (WA or OR) and a sample Great Plains Tribe, population scripts produce cached JSON files containing drought severity history, historical climate records, active NWS alerts (if any), landslide inventory data (for PNW Tribe), terrain summary, and infrastructure exposure counts -- all with provenance metadata
2. All climate, geologic, and infrastructure data sources route through the existing county FIPS crosswalk with no new geographic bridge files
3. State landslide data (GEO-01) is correctly scoped to WA and OR Tribes only, with other states showing "not available" rather than empty/null
4. Coverage report shows percentage of 592 Tribes with data from each source, with expected partial coverage noted (landslide = WA/OR only, coastal metrics = coastal only)

---

### Phase 22: Vulnerability Profiles & Pipeline Integration

**Goal:** All data sources are composed into per-Tribe composite vulnerability profiles with 5-tier ratings, the pipeline loads vulnerability data into document context for all 592 Tribes, and compliance tests enforce the pre-cache and air gap patterns before any rendering begins.

**Dependencies:** Phase 19 (expanded NRI, SVI), Phase 20 (flood data), Phase 21 (climate, geologic, infrastructure data)

**Requirements:**
- VULN-03: Composite vulnerability score (0-1) per Tribe with 5 rating tiers (Very High/High/Moderate/Low/Very Low)
- VULN-04: Per-Tribe vulnerability profiles (592 JSON files) in vulnerability_profiles/ with data provenance
- REG-01: Data catalog documenting every integrated data source with steward, cadence, resolution, licensing, limitations, URL
- REG-02: Acquisition query logging for reproducibility and defensibility
- XCUT-01: All data sources routed through county FIPS crosswalk (one geographic truth)
- XCUT-02: Zero API calls during document generation (all data pre-cached)
- XCUT-05: Compliance tests blocking network imports in src/packets/ and enforcing air gap for vulnerability content

**Success Criteria:**
1. Running the vulnerability profile builder produces 592 JSON files in vulnerability_profiles/, each containing a composite vulnerability score (0-1), a 5-tier rating (Very High through Very Low), component scores for hazard exposure, social vulnerability, and adaptive capacity deficit, plus source-specific data sections with provenance metadata
2. A compliance test that scans src/packets/ for network/HTTP imports passes, confirming zero API call capability during document generation
3. Audience air gap tests updated with vulnerability-specific forbidden terms (SVI theme decomposition, strategy language) pass for Doc B/D rendering paths
4. A data catalog file exists documenting all integrated sources with agency, update cadence, spatial resolution, licensing, known limitations, and acquisition URL -- and every source in the vulnerability profiles is listed
5. The PacketOrchestrator loads vulnerability profiles into TribePacketContext for all 592 Tribes using the same cache-loading pattern as hazard and award data, with a CLI summary display showing vulnerability coverage

---

### Phase 23: Document Rendering

**Goal:** Vulnerability data renders correctly in existing Doc A/B/C/D packets with audience-appropriate content, and a new standalone Doc E vulnerability report provides full-detail per-Tribe vulnerability assessments with grant-ready narrative paragraphs.

**Dependencies:** Phase 22 (vulnerability profiles in pipeline context, compliance tests passing, framing vocabulary in use)

**Requirements:**
- DOC-01: Vulnerability sections in Doc A and Doc B with air gap enforcement (SVI decomposition in Doc A only; Doc B composite only)
- DOC-02: Doc E standalone vulnerability report with full-detail assessment, grant-ready narratives, and data citations
- DOC-03: EAL consequence-type breakdown table (buildings/population/agriculture per top hazard)

**Success Criteria:**
1. Generated Doc A for a sample Tribe contains a vulnerability section showing composite score, top hazards, SVI theme decomposition, EAL breakdown table (buildings/population/agriculture), and sovereignty-first framing language from the VULNERABILITY_FRAMING constants
2. Generated Doc B for the same Tribe contains a vulnerability section showing composite score and top hazards but NO SVI theme decomposition, NO strategy language, and NO terms from the air gap forbidden list -- verified by the existing audience filtering test suite
3. Generated Doc E for a sample Tribe is a standalone document containing all vulnerability data sources, grant-ready narrative paragraphs, data citations with version/date, and passes structural validation
4. Doc C (regional) and Doc D (regional congressional) include aggregated vulnerability summaries with the same air gap enforcement as Doc A/B respectively
5. The structural validator is extended to validate Doc E and reports pass/fail for the full document corpus including the new document type

---

### Phase 24: Website & Delivery

**Goal:** The production website displays vulnerability intelligence inline with search results and provides on-demand detailed vulnerability views with visualizations -- all within the static site constraint and payload budget.

**Dependencies:** Phase 22 (vulnerability profiles for data), Phase 23 (document rendering patterns proven)

**Requirements:**
- WEB-01: Vulnerability badges in Tribe cards (composite rating, top hazard) with ARIA compliance and dark mode
- WEB-02: On-demand per-Tribe detail loading (vulnerability JSON loaded on click, tribes.json under 1.5 MB)
- WEB-03: Chart.js visualizations (hazard radar chart, SVI theme bar charts) with progressive enhancement

**Success Criteria:**
1. The Tribe search results page shows a vulnerability badge (composite rating tier and top hazard indicator) for each Tribe, correctly styled in both light and dark mode, with ARIA labels readable by screen readers
2. Clicking a Tribe card loads detailed vulnerability data from a per-Tribe JSON file (not embedded in tribes.json), and the tribes.json payload remains under 1.5 MB as verified by the build script
3. Chart.js hazard radar chart and SVI theme bar charts render correctly for Tribes with full data, degrade gracefully for Tribes with partial data, and do not render at all (no broken chart) for Tribes with no vulnerability data
4. All vulnerability UI elements meet WCAG 2.1 AA requirements: keyboard navigable, minimum 4.5:1 contrast ratio, mobile responsive with 44px minimum touch targets

---

## Progress

| Phase | Name | Requirements | Status |
|-------|------|-------------|--------|
| 18.5 | Architectural Review & Scaffolding | — (pre-phase) | **Complete** (2026-02-17) |
| 19 | Schema & Core Data Foundation | REG-03, REG-04, VULN-01, VULN-02, XCUT-03, XCUT-04 | Pending |
| 20 | Flood & Water Data | FLOOD-01 to FLOOD-06 | Pending |
| 21 | Climate, Geologic & Infrastructure Data | CLIM-01 to CLIM-03, GEO-01, GEO-02, INFRA-01 | Pending |
| 22 | Vulnerability Profiles & Pipeline Integration | VULN-03, VULN-04, REG-01, REG-02, XCUT-01, XCUT-02, XCUT-05 | Pending |
| 23 | Document Rendering | DOC-01, DOC-02, DOC-03 | Pending |
| 24 | Website & Delivery | WEB-01, WEB-02, WEB-03 | Pending |

## Coverage Map

| Requirement | Phase | Description |
|-------------|-------|-------------|
| REG-01 | 22 | Data catalog/registry |
| REG-02 | 22 | Acquisition query logging |
| REG-03 | 19 | Pydantic schema models (schema-first) |
| REG-04 | 19 | Sovereignty-first framing vocabulary |
| VULN-01 | 19 | Expanded FEMA NRI metrics |
| VULN-02 | 19 | CDC/ATSDR SVI 2022 integration |
| VULN-03 | 22 | Composite vulnerability score |
| VULN-04 | 22 | Per-Tribe vulnerability profiles |
| FLOOD-01 | 20 | NFIP flood insurance data |
| FLOOD-02 | 20 | FEMA disaster declarations |
| FLOOD-03 | 20 | FEMA NFHL flood zones |
| FLOOD-04 | 20 | USGS Water Services streamflow |
| FLOOD-05 | 20 | NOAA Atlas 14 precipitation |
| FLOOD-06 | 20 | NOAA CO-OPS coastal water levels |
| CLIM-01 | 21 | US Drought Monitor / NOAA-NIDIS |
| CLIM-02 | 21 | NOAA NCEI Climate Data Online |
| CLIM-03 | 21 | NWS API forecasts/alerts |
| GEO-01 | 21 | State landslide data (WA/OR) |
| GEO-02 | 21 | USGS 3DEP elevation/terrain |
| INFRA-01 | 21 | DHS HIFLD infrastructure |
| DOC-01 | 23 | Vulnerability sections in Doc A/B |
| DOC-02 | 23 | Doc E standalone vulnerability report |
| DOC-03 | 23 | EAL breakdown table in documents |
| WEB-01 | 24 | Vulnerability badges in Tribe cards |
| WEB-02 | 24 | On-demand detail loading |
| WEB-03 | 24 | Chart.js visualizations |
| XCUT-01 | 22 | County FIPS crosswalk (one geographic truth) |
| XCUT-02 | 22 | Zero API calls during doc generation |
| XCUT-03 | 19 | NRI version pinning + SHA256 + CT mapping |
| XCUT-04 | 19 | utf-8 encoding + atomic writes |
| XCUT-05 | 22 | Compliance tests (network imports, air gap) |

---
*Created: 2026-02-17*
*28 requirements mapped across 6 phases (Phase 19-24)*
