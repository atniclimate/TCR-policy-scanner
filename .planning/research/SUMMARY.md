# Project Research Summary

**Project:** TCR Policy Scanner v1.1 — Tribe-Specific Advocacy Packet Generation
**Domain:** Per-Tribe congressional advocacy intelligence packets (DOCX) for 575 federally recognized Tribes
**Researched:** 2026-02-10
**Confidence:** HIGH

## Executive Summary

The TCR Policy Scanner v1.1 extends the existing monitoring system to generate customized advocacy packets for each of the 575 federally recognized Tribes. Research confirms this capability is feasible using existing stack components plus two new dependencies (python-docx for DOCX generation, rapidfuzz for fuzzy name matching). The core challenge is not technical architecture but data quality: matching USASpending recipient names to Tribal entities, mapping Tribes to congressional districts across multi-state reservations, and assembling hazard profiles from multiple federal data sources.

The recommended approach separates packet generation from the daily monitoring pipeline. A new CLI command (`--prep-packets`) consumes cached monitoring outputs plus six new data layers: Tribal registry (575 Tribes with EPA API), congressional mapping (Census geocoder + Congress.gov API), USASpending award matching (fuzzy matching with curated alias table), hazard profiling (FEMA NRI + USFS wildfire data as downloadable CSVs), economic impact framing (FEMA 4:1 BCR, not paid RIMS II multipliers), and DOCX programmatic construction. All new data layers follow the existing BaseScraper pattern for async HTTP and cache-first architecture.

Critical risks center on data source availability and quality. EPA EJScreen was removed in February 2025 (mitigation: use PEDP community reconstruction). BEA RIMS II multipliers cost $500/region (mitigation: use FEMA's published 4:1 benefit-cost ratio plus standard federal multiplier ranges). Tribal name matching produces false positives without curation (mitigation: UEI-first matching, curated alias table, manual validation). The 575 Tribe count requires careful pre-caching of static data to avoid API rate limit failures during batch generation. With these mitigations, the system can generate all 575 packets in under 2 minutes.

## 1. Key Stack Additions

**Adding 2 new runtime dependencies to existing Python 3.12 + aiohttp stack:**

### python-docx (>=1.1.2, <2.0)
- **Purpose:** Programmatic DOCX generation for advocacy packets
- **Why:** Only production-stable pure-Python library for .docx creation. No viable alternatives (Aspose is proprietary/paid, docxtpl adds unwanted templating complexity for our dynamic table/section structure)
- **Integration:** Synchronous library called after async data collection completes. Document construction is CPU-bound (<1s per packet), not I/O-bound
- **Capabilities verified:** Tables with cell merging, headers/footers, page breaks, inline images, paragraph/character formatting, section properties

### rapidfuzz (>=3.6.0, <4.0)
- **Purpose:** Fuzzy string matching for USASpending recipient name → Tribal entity matching
- **Why:** C++ core (10-100x faster than thefuzz), MIT license (thefuzz is GPL), API-compatible drop-in replacement
- **Integration:** Used in USASpending award-matching layer to match 575 Tribal names (current + historical aliases from EPA API) against thousands of recipient names from existing USASpending scraper
- **Critical need:** Matching "THE NAVAJO NATION" (USASpending) to "Navajo Nation" (EPA registry) requires token_sort_ratio with 75+ threshold to avoid false positives

### Libraries explicitly NOT adding
- **censusgeocode:** Sync-only wrapper; trivial to call Census API via existing aiohttp stack
- **geopandas/shapely:** Massive GIS dependencies for simple lat/lng lookups; FEMA NRI + Census geocoder provide needed data as CSVs
- **openpyxl:** Not needed at runtime; USFS wildfire data converts XLSX to CSV once at build time
- **thefuzz/fuzzywuzzy:** GPL license risk, pure Python (too slow for 575 Tribes x 1000s recipients)

## 2. Critical Data Source Findings

### 575 Tribes (not 574)
As of January 30, 2026, there are **575** federally recognized Tribes (Lumbee Tribe of North Carolina added via FY2026 NDAA, Federal Register 2026-01899). EPA Tribes Names Service API provides authoritative list with BIA codes, current names, historical name variants, and state/EPA region mappings. This is the data backbone for all per-Tribe operations.

### EJScreen Removed by EPA (February 5, 2025)
EPA removed EJScreen from its website as part of environmental justice program rollback. Official API at ejscreen.epa.gov is down. **Mitigation:** PEDP (Public Environmental Data Partners) coalition reconstructed EJScreen v2.3 from archived data, available at screening-tools.com and Zenodo. Download and bundle CSV data locally rather than depending on volunteer infrastructure API. Design hazard profiler with source abstraction layer so EJScreen is enrichment, not required.

### RIMS II Multipliers Are Paid ($500/region)
BEA RIMS II regional multipliers are a commercial product with NO free API. At $500/region or $150/industry, purchasing multipliers for all regions covering 575 Tribes is cost-prohibitive. **Mitigation:** Use FEMA's published 4:1 benefit-cost ratio for hazard mitigation (already standard federal methodology) plus published literature-based multiplier estimates (~2.0x total output for direct federal spending). Frame economic impact using FEMA BCA rather than RIMS II precision.

### EPA Tribes Names Service (New Primary Source)
| Attribute | Value |
|-----------|-------|
| **Base URL** | `https://cdxapi.epa.gov/oms-tribes-rest-services` |
| **Key endpoint** | `GET /api/v1/tribes` (all 575 Tribes, basic data) |
| **Authentication** | None required (public API) |
| **Critical fields** | `currentName`, `currentBIATribalCode`, `epaLocations` (state/region), `names` (historical aliases for fuzzy matching) |
| **Integration** | Fetch once on first run, cache as JSON (changes ~1x/year) |
| **Use** | Foundation for Tribal registry + fuzzy name matching corpus |

### Multi-District Tribes (CRS R48107)
Many Tribes span multiple congressional districts. Navajo Nation has lands in 4 districts across 3 states. Alaska has 229 Tribes in a single at-large district with no sub-district boundaries. **Critical:** Model Tribe-to-district as many-to-many from day one. Use CRS Table A-3 from R48107 as authoritative mapping rather than computing from TIGER shapefiles (which fail for Alaska and multi-state reservations).

## 3. Architecture Summary

### Separate Command, Not Daily Pipeline Integration
Packet generation runs as **separate CLI command** (`--prep-packets`), NOT as a stage in the daily scan pipeline. Different cadence (quarterly/ad-hoc vs daily), different data dependencies (Tribal registry, hazard data, congressional mapping), and different user needs (selective generation for specific Tribes vs always-on monitoring).

### 8 New Modules Under Two Packages
```
src/
  packets/                    # NEW: Packet generation orchestration
    __init__.py               # PacketOrchestrator (top-level entry)
    tribal_registry.py        # TribeRegistry: load/query 575 Tribes
    congressional.py          # CongressionalMapper: Tribe -> delegation
    hazard_profile.py         # HazardProfiler: NRI + USFS + NOAA
    award_matcher.py          # AwardMatcher: fuzzy USASpending matching
    economic_impact.py        # EconomicImpact: BEA data + BCR framing
    docx_builder.py           # DocxBuilder: programmatic DOCX construction
    overview_builder.py       # OverviewBuilder: shared strategic doc

  scrapers/
    usaspending.py            # MODIFIED: add paginated Tribal query method
```

### Pre-Cache Pattern for Static Data
**Critical anti-pattern to avoid:** Calling APIs per-Tribe during DOCX generation. 575 Tribes x multiple APIs = thousands of requests, rate limits, and 4+ hour runtimes.

**Instead:** Pre-fetch and cache all data layers before DOCX generation:
1. **FEMA NRI:** Download tribal-specific CSV once (quarterly refresh). 3,200 county rows, ~50MB.
2. **Congress.gov members:** Fetch full member list for 119th Congress once, cache, do local district lookups. Changes every 2 years.
3. **USASpending awards:** Query per-CFDA with `recipient_type_names: ["tribal"]` filter to get ALL Tribal awards in ~12 calls total, then match locally with rapidfuzz.
4. **Census geocoder:** Pre-compute all 575 Tribe → congressional district mappings using CRS R48107 table, not real-time API calls.
5. **Hazard profiles:** Store per-Tribe JSON files in `data/hazard_profiles/{tribe_id}.json`, load on-demand.

This reduces per-packet API overhead to zero. DOCX generation reads only from local JSON/CSV files.

### Integration with Existing Pipeline
**Zero modifications to existing v1.0 logic.** Packet system is pure consumer of cached outputs:
- Reads `outputs/LATEST-GRAPH.json` for barriers, authorities, structural asks
- Reads `outputs/LATEST-MONITOR-DATA.json` for monitor alerts per program
- Reads `data/program_inventory.json` for advocacy goals, tightened language
- Uses existing `BaseScraper` for new data collection modules

New modules import from existing codebase but existing code does NOT import new modules. Regression-safe.

## 4. Feature Categories

### Table Stakes (8 features — ship all or packet is unusable)
1. **Per-Tribe document identity:** Each DOCX names the specific Tribe (not generic). Congressional staff must see "Navajo Nation Climate Resilience Program Priorities" to engage.
2. **Per-program Hot Sheets:** Each of 16 tracked programs gets its own section with Tribe-specific award history, hazard relevance, economic impact, delegation.
3. **Congressional delegation section:** Senators (2), House rep(s), committee assignments relevant to 16 programs.
4. **USASpending award history per Tribe per program:** Total obligations, FY breakdown, project descriptions. "We have successfully used this program" is most persuasive advocacy framing.
5. **Advocacy language per program:** Ready-made talking points from decision engine's advocacy goals + tightened language + Five Structural Asks.
6. **DOCX output format:** Not PDF, not Markdown. Word files are editable by Tribal policy staff and accepted by congressional offices.
7. **Shared strategic overview document:** Single DOCX covering overall FY26 landscape, 7 ecoregion priorities, FEMA analysis, cross-cutting framework. Companion to per-Tribe packets.
8. **Batch and ad-hoc generation modes:** CLI supports `--all-tribes` (574 packets) and `--tribe <name>` (single packet) for pre-event prep vs urgent requests.

### Differentiators (5 features — unique value, not expected)
1. **Hazard profiling per Tribe:** FEMA NRI (18 hazard types), USFS wildfire risk, climate data. "Standing Rock Sioux: HIGH drought risk, MODERATE wildfire, inland flooding." No other Tribal advocacy tool combines federal hazard data with program-level funding asks.
2. **District economic impact framing:** USASpending obligations x regional multipliers + FEMA 4:1 BCR. "BIA TCR funding generated $4.1M economic activity in OK-02, supporting 28 jobs." Reframes Tribal funding as district economic investment.
3. **Change tracking ("Since Last Packet"):** Diff between packet generations showing CI status changes, new awards, advocacy goal shifts. Urgency for repeat advocacy events.
4. **Ecoregion priority framework:** 7 ecoregions with differentiated program prioritization. Arctic Tribes prioritize permafrost/coastal erosion, Southwest prioritizes drought/wildfire.
5. **Five Structural Asks integration:** Weave cross-cutting advocacy levers from knowledge graph into per-program Hot Sheets with Tribe-specific evidence.

### Anti-Features (6 things to NOT build)
1. **DO NOT collect Tribal-specific sensitive data:** Enrollment, governance docs, internal plans, cultural sites violate data sovereignty. Use only public federal data (T0 classification).
2. **DO NOT use AI/LLM text generation:** Hallucination risk unacceptable for congressional documents. Use template-based assembly from verified data fields only.
3. **DO NOT build real-time editing/collaboration:** DOCX files open in Word. Users have existing review workflows. Duplicating Word is scope creep.
4. **DO NOT auto-select programs per Tribe:** All 16 programs relevant to all 575 Tribes at policy level. Show "No awards to date — potential new program" instead of dropping.
5. **DO NOT build web UI:** CLI users, GitHub Actions integration, no deployment complexity.
6. **DO NOT purchase RIMS II multipliers:** Cost-prohibitive. Use FEMA BCR + published standard multipliers instead.

## 5. Critical Pitfalls to Address

### C-1: Tribal Name Matching False Positives (BLOCKS SHIPMENT)
**Problem:** Fuzzy-matching 575 BIA Tribal names against USASpending recipients produces misattributions. "Cheyenne River Sioux" matches "Cheyenne and Arapaho Tribes." Showing wrong award data in congressional document destroys credibility instantly.

**Prevention:**
1. Build curated alias table mapping 575 BIA names to known USASpending variants
2. Use UEI (Unique Entity Identifier) as primary key, fuzzy matching only as fallback
3. rapidfuzz with token_sort_ratio, threshold >=85, manual review for 85-95 range
4. Exclude recipients containing "Corporation", "LLC", "Housing Authority" unless in alias table
5. Include `match_confidence` field, surface LOW confidence in validation report

**Detection:** Assert matched recipient's state overlaps Tribe's known state(s). Flag cross-state matches.

### C-2: EJScreen Data Source Unavailable (BLOCKS IF REQUIRED)
**Problem:** EPA removed EJScreen in February 2025. Official API gone. Code against ejscreen.epa.gov fails with 404.

**Prevention:**
1. Use PEDP reconstruction at screening-tools.com OR download Zenodo archive
2. Design hazard profiler with source abstraction layer (EJScreen enrichment, not required)
3. Download and cache locally rather than API dependency on volunteer infrastructure
4. Document provenance: "EJ indicators from PEDP EJScreen v2.3 (pre-Feb 2025 data)"

### C-3: BEA RIMS II Multipliers Are Paid (DEGRADES IF NO ALTERNATIVE)
**Problem:** RIMS II costs $500/region, no free API. Purchasing for 575 Tribes across 50 states = thousands of dollars.

**Prevention:**
1. Use FEMA's published 4:1 BCR for pre-disaster mitigation (already standard federal methodology)
2. Apply published federal spending multiplier ranges (~2.0x for direct grants) with citations
3. Do NOT present approximations as RIMS II outputs — label methodology clearly

### C-4: Multi-State/Multi-District Tribes (BLOCKS FOR AFFECTED TRIBES)
**Problem:** Navajo Nation spans 4 districts across 3 states. Alaska has 229 Tribes in single at-large district. Simple 1:1 Tribe-to-district mapping breaks.

**Prevention:**
1. Model Tribe-to-district as many-to-many from day one (List[DistrictMapping], not single field)
2. Use CRS R48107 Table A-3 as authoritative mapping, not computed from TIGER shapefiles
3. For Alaska: all 229 Tribes → AK-AL at-large, no geographic intersection
4. For multi-district Tribes: list ALL representatives, show full Tribe-level award total in each context

### C-5: API Rate Limits at 574x Scale (BLOCKS BATCH GENERATION)
**Problem:** 575 Tribes x 12 CFDAs = 6,888+ API calls. Without pre-caching, batch run hits rate limits, takes 4+ hours, produces incomplete data.

**Prevention:**
1. Pre-cache static data: NRI CSV download, CRS district mapping, Congress.gov member list
2. Batch USASpending: query per-CFDA with `recipient_type_names: ["tribal"]` filter (12 calls total, not 6,888)
3. Implement adaptive rate limiting with Retry-After header handling
4. Congress.gov: fetch full member list once, cache, do local lookups
5. Progress reporting for long-running operations

## 6. Recommended Build Order (4 Phases, Dependency-Driven)

### Phase 1: Foundation (No External API Dependencies)
**Rationale:** Establish data backbone and CLI skeleton before tackling complex data acquisition. Enables testing with mock data while Phase 2 progresses.

**Delivers:**
- Tribal registry module + `data/tribal_registry.json` (575 Tribes with EPA API integration)
- Congressional mapping module + `data/congressional_map.json` (CRS R48107 pre-computed)
- CLI extension (`--prep-packets`, `--tribe`, `--all-tribes` flags)
- PacketOrchestrator skeleton with TribePacketContext dataclass
- Graph schema additions (TribeNode, HazardNode, CongressionalDistrictNode)

**Addresses:**
- TS-01 (Per-Tribe identity) — registry provides canonical names
- C-4 (Multi-district Tribes) — many-to-many model from start

**Avoids:**
- C-4 pitfall by using CRS table + many-to-many architecture
- m-2 integration pitfall by separating new packages from existing pipeline

### Phase 2: Data Acquisition Layers
**Rationale:** Hardest data quality challenges (fuzzy matching, multi-source hazard data). Phase 1 skeleton provides test harness. Pre-cache static data to avoid Phase 3 rate limit issues.

**Delivers:**
- Award matcher with curated alias table + fuzzy fallback (rapidfuzz integration)
- Modified USASpendingScraper for paginated Tribal queries
- Hazard profiler ingesting NRI CSV, USFS wildfire CSV, NOAA ACIS API
- Per-Tribe hazard profile cache (`data/hazard_profiles/{tribe_id}.json`)

**Addresses:**
- TS-04 (USASpending awards per Tribe) — fuzzy matching with quality gates
- DF-01 (Hazard profiling) — FEMA NRI + USFS data

**Avoids:**
- C-1 (name matching false positives) via UEI-first + curated aliases + 85+ threshold
- C-2 (EJScreen unavailable) via source abstraction + PEDP/Zenodo fallback
- C-5 (rate limits) via pre-caching NRI, batch USASpending queries
- M-4 (pagination limits) via full result iteration, not limit:10

### Phase 3: Computation + DOCX Generation
**Rationale:** Data layers from Phase 2 feed economic impact calculations and DOCX construction. All data flows before assembly.

**Delivers:**
- Economic impact calculator (FEMA 4:1 BCR + standard multipliers, NOT RIMS II)
- DOCX builder with python-docx programmatic construction
- Per-section builder methods (cover, executive summary, delegation, Hot Sheets, hazard profile)
- Style reference document (`data/docx_templates/packet_styles.docx`)

**Addresses:**
- TS-06 (DOCX output) — programmatic generation with style reference
- TS-02 (Per-program Hot Sheets) — dynamic table/section assembly
- DF-02 (Economic impact) — FEMA BCR framing

**Avoids:**
- C-3 (RIMS II paid) via FEMA BCR + published multiplier ranges
- M-1 (memory consumption) via per-document scope + explicit GC
- M-5 (brittle layouts) via centralized DocxStyles class + reference doc analysis

### Phase 4: Assembly + Operational Features
**Rationale:** Final integration after core packet generation proven. Adds operational features (change tracking, batch modes, overview doc).

**Delivers:**
- Per-program Hot Sheet assembly (TS-02) with Tribe-specific data
- Advocacy language integration (TS-05) from existing inventory
- Structural Asks weaving (DF-05) from knowledge graph
- Shared strategic overview document (TS-07)
- Batch/ad-hoc CLI modes (TS-08)
- Change tracking (DF-03) with TribeSnapshot diff logic
- Ecoregion priority framework (DF-04)

**Addresses:**
- Full per-Tribe packet assembly (Document 1)
- Shared overview (Document 2)
- Operational modes for real-world usage

**Avoids:**
- M-6 (change tracking complexity) via typed change detection + significance thresholds

### Phase Ordering Rationale
1. **Foundation first:** Establishes test harness with no external dependencies. Data model decisions (many-to-many districts) cascade downstream.
2. **Data acquisition second:** Hardest data quality challenges isolated with Phase 1 providing structure. Pre-caching prevents Phase 3 rate limit failures.
3. **Generation third:** All data flowing enables DOCX construction. By this point, end-to-end pipeline testable.
4. **Polish last:** Change tracking and operational features build on proven core.

### Research Flags

**Phases needing deeper research during planning:**
- **Phase 2 (Award Matching):** Fuzzy matching quality calibration requires sampling real USASpending recipient data against EPA registry. Budget 2-3 days for manual alias curation and validation.
- **Phase 2 (Hazard Profiling):** Multi-source data reconciliation (NRI county-level + Tribal boundaries) may need geographic analysis. Consider whether census tract-level NRI data improves accuracy.
- **Phase 3 (DOCX Construction):** python-docx styling for professional documents requires reference doc analysis. Unknown: table cell merging complexity for variable-row Hot Sheets.

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (Foundation):** Tribal registry is straightforward JSON loading. Congressional mapping uses established CRS table. CLI extension follows existing argparse patterns.
- **Phase 4 (Assembly):** Hot Sheet assembly combines existing data structures. Change tracking extends existing ChangeDetector pattern.

## 7. Risk Register

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| **Tribal name matching false positives** | CRITICAL (wrong data in congressional doc destroys credibility) | HIGH (575 names x 1000s recipients) | UEI-first matching, curated alias table, 85+ threshold, state overlap validation |
| **EJScreen data becomes fully unavailable** | MEDIUM (one of 4 hazard sources) | MEDIUM (volunteer PEDP may discontinue) | Zenodo archive durable, source abstraction layer, FEMA NRI covers core needs |
| **API rate limits during batch generation** | CRITICAL (incomplete packets) | HIGH (6,888+ calls naive approach) | Pre-cache all static data, batch USASpending queries, adaptive rate limiting |
| **Multi-district Tribes incomplete delegation** | CRITICAL (missing representatives) | MEDIUM (affects ~50 large Tribes) | Many-to-many model, CRS R48107 authoritative table, validate Navajo = 4 districts |
| **RIMS II multipliers needed for accuracy** | MEDIUM (degrades economic framing) | LOW (FEMA BCR acceptable alternative) | FEMA 4:1 BCR standard federal methodology, published multiplier ranges with citations |
| **python-docx memory consumption (574 docs)** | MEDIUM (batch may fail) | MEDIUM (known issue in python-docx) | Per-document GC, batch processing (50 at a time), memory monitoring |
| **Congressional data staleness** | LOW (embarrassing but packets usable) | MEDIUM (resignations, redistricting) | Fetched_date display, monthly refresh mechanism, CRS table version pinning |
| **Font rendering cross-platform** | LOW (visual quality) | MEDIUM (Windows dev, Linux CI) | Liberation fonts (metrically compatible), explicit font specs, CI visual test |

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| **Stack** | HIGH | python-docx and rapidfuzz verified on PyPI with stable releases. Integration patterns proven (existing aiohttp stack handles all new APIs). |
| **Features** | MEDIUM | Table stakes well-defined from domain requirements. Differentiators based on data source availability research. Economic impact framing depends on FEMA BCR acceptance vs RIMS II precision. |
| **Architecture** | HIGH | Separate command architecture matches existing `--report-only` pattern. Pre-cache approach verified against API rate limit math. Module layout extends existing src/ structure cleanly. |
| **Pitfalls** | HIGH | Critical pitfalls (name matching, EJScreen, RIMS II, multi-district, rate limits) verified with official docs and issue trackers. Mitigations designed based on existing codebase patterns (alias tables, cache-first, BaseScraper). |

**Overall confidence:** HIGH

### Gaps to Address During Planning

1. **Fuzzy matching threshold calibration:** Research provides 85+ recommendation but requires validation against real data. Plan for manual review cycle during Phase 2.

2. **Census tract vs county NRI granularity:** Research confirms FEMA NRI available at both levels. County-level simpler but less accurate for Tribes spanning multiple counties. Decision needed during hazard profiler design.

3. **DOCX styling reference document:** Need to obtain/analyze actual reference DOCX files (`FY26_TCR_Program_Priorities.docx`, `FY26_Federal_Funding_Strategy.docx`) to catalog formatting requirements before Phase 3.

4. **Ecoregion-to-Tribe mapping completeness:** Research identifies 7 ecoregion framework but does not provide the 575 Tribe classification. Source needed during Phase 1 registry construction.

5. **Change tracking significance thresholds:** Research recommends typed change detection with thresholds but specific values ($100 award delta? 5% change?) require domain expert input during Phase 4.

## Sources

### Primary (HIGH confidence)
- **EPA Tribes Names Service:** Official API documentation, verified endpoints, no-auth public access
- **Federal Register 2026-01899:** 575 Tribes count (Lumbee addition), legal authority
- **FEMA NRI Data Resources:** CSV download availability, tribal datasets confirmed, v1.20 Dec 2025
- **USFS Wildfire Risk to Communities:** Download URL verified, tribal area tabular data confirmed
- **Congress.gov API GitHub:** Rate limits (5,000/hr), member endpoints, committee structure
- **Census Geocoder API:** Endpoint format, coordinates lookup verified
- **BEA RIMS II Pricing:** $500/region confirmed via apps.bea.gov order system
- **python-docx PyPI:** Version 1.2.0, capabilities verified against official docs
- **rapidfuzz PyPI:** Version 3.14.3, MIT license, C++ performance claims verified
- **CRS R48107:** Tribal lands in congressional districts, Table A-3 multi-district mappings

### Secondary (MEDIUM confidence)
- **EJScreen Removal:** EDGI/PEDP reports Feb 2025 EPA takedown, Zenodo archive available
- **PEDP EJScreen Reconstruction:** Community effort at screening-tools.com, volunteer infrastructure
- **USASpending Recipient Matching:** Community reports of name inconsistency, pagination behavior
- **python-docx Memory Issues:** GitHub issues #1364, #174, #158 document large-table performance

### Tertiary (LOW confidence — needs validation)
- **Alaska Native Village boundaries:** Census TIGER documentation implies ANVSA statistical areas, not legal boundaries
- **NOAA Climate Projections:** ACIS API provides historical data, projections availability at county level unclear
- **Ecoregion classification:** 7 ecoregion framework referenced in project scope but mapping source not identified

---
**Research completed:** 2026-02-10
**Ready for roadmap:** Yes
**Next step:** Roadmap creation with 4 phases (Foundation, Data Acquisition, Generation, Assembly)
