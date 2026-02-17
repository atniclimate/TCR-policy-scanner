# Domain Pitfalls: Climate Vulnerability Data Integration

**Domain:** Adding NOAA climate projections, CDC/ATSDR SVI, and expanded FEMA NRI data to an existing Tribal policy intelligence system (TCR Policy Scanner)
**Researched:** 2026-02-17
**System context:** 592 Tribal Nations, 964 tests, 4 document types (A/B/C/D), pre-cache pattern (zero API calls at render time), area-weighted geographic crosswalk, audience air gap

---

## Critical Pitfalls

Mistakes that cause data corruption, sovereignty violations, or require architectural rewrites.

### CRIT-01: Confusing FEMA NRI SOVI with CDC/ATSDR SVI

**What goes wrong:** The system already parses `SOVI_SCORE` and `SOVI_RATING` from the NRI CSV (see `src/packets/hazards.py` lines 371-372). FEMA's NRI originally used its own Social Vulnerability Index (SoVI), but as of NRI v1.19+ changed to use CDC/ATSDR SVI as its social vulnerability component. If the milestone adds CDC SVI data as a separate data source, the two indices may be presented as independent variables when they are now the same underlying measurement. Alternatively, if using an older NRI version alongside a newer CDC SVI version, the scores will contradict each other for the same geography because the methodologies diverged.

**Why it happens:** The names are nearly identical (SoVI vs SVI), and the FEMA NRI CSV column names (`SOVI_SCORE`, `SOVI_RATNG`) do not indicate which methodology backs them. Teams assume "FEMA social vulnerability" and "CDC social vulnerability" are complementary when they are overlapping or identical depending on NRI version.

**Consequences:** Double-counting vulnerability in composite scores. Congressional documents present contradictory social vulnerability ratings for the same Tribe. Loss of credibility with data-literate congressional staff.

**Warning signs:**
- Two different social vulnerability scores appear in the same document section
- NRI SOVI score and CDC SVI score diverge significantly for the same geography
- Confusion in code comments about which "SVI" is being referenced

**Prevention:**
1. Before adding CDC SVI as a separate source, verify the NRI version in use. The current system detects version via `_detect_nri_version()` in `hazards.py` (line 281). If NRI >= v1.19, SOVI_SCORE already IS the CDC SVI.
2. If both are kept, document the relationship explicitly: "NRI Social Vulnerability component uses CDC/ATSDR SVI methodology as of NRI v1.19."
3. Consider CDC SVI data as an ENRICHMENT (tract-level detail, theme decomposition) rather than a separate vulnerability dimension. Use it to decompose the existing SOVI_SCORE into its four themes (Socioeconomic, Household Composition/Disability, Minority Status/Language, Housing Type/Transportation).

**Recovery cost:** HIGH -- requires audit of all 592 cached profiles, document re-generation, and potential data model change.

**Confidence:** HIGH (verified via FEMA NRI change summary v1.19 and CDC SVI documentation)

---

### CRIT-02: Deficit Framing of Tribal Vulnerability

**What goes wrong:** Climate vulnerability data inherently frames communities as "at risk" or "vulnerable." When applied to Tribal Nations without sovereignty-aware language, documents read as colonial assessments of Indigenous deficiency. Phrases like "high vulnerability," "low resilience," "at-risk populations," or "lacking capacity" undermine the sovereignty-first posture the system maintains throughout all other sections.

**Why it happens:** Source data labels (NRI ratings "Very High" risk, SVI "high vulnerability") are designed for generic U.S. communities. Developers copy source terminology directly into rendered documents without reframing. The existing hazard section already does this partially -- `render_hazard_summary()` in `docx_sections.py` uses "Overall Risk Rating" and "Social Vulnerability" labels which are close to source terminology.

**Consequences:** Tribal leaders see their Nations characterized through a deficit lens. Documents become unusable for the stated purpose of advocacy. Violates the project's core value: "Sovereignty is the innovation." Congressional offices receive documents that frame Tribes as helpless rather than as sovereign governments managing complex challenges.

**Warning signs:**
- Document text uses "vulnerable populations" or "at-risk communities" without Tribal agency language
- Vulnerability scores presented without context of Tribal resilience and Traditional Knowledge
- Community resilience scores presented as "deficient" rather than "federal measurement gap"
- Review by Tribal stakeholders flags language concerns

**Prevention:**
1. Establish a framing vocabulary before writing any renderer code:
   - NOT "high vulnerability" but "disproportionate exposure to climate hazards"
   - NOT "low resilience" but "federal resilience metrics do not capture Tribal governance capacity"
   - NOT "at-risk population" but "Tribal Nation facing elevated hazard exposure"
2. Add a `VULNERABILITY_FRAMING` constants module (similar to `COLORS` in `docx_styles.py`) that maps raw data labels to sovereignty-respectful alternatives
3. Include a framing disclaimer in vulnerability sections: "Federal risk indices measure physical and infrastructure exposure. They do not capture Tribal governance capacity, Traditional Knowledge, or community resilience practices."
4. Doc A (internal strategy) can use data analytically; Doc B (congressional) must frame as advocacy ammunition, not deficit characterization
5. Apply audience differentiation: the `doc_type_config` pattern already handles this split for strategy content -- extend it to vulnerability language

**Recovery cost:** VERY HIGH -- requires rewriting all document section renderers, re-generating all 992+ documents, and stakeholder review of new language.

**Which phase:** Must be addressed in the FIRST phase that touches document rendering for vulnerability data. Cannot be deferred.

---

### CRIT-03: CDC SVI Tribal Census Tracts Are Not Ranked

**What goes wrong:** The CDC/ATSDR SVI provides tribal census tract data as a SEPARATE database that contains only raw estimates and percentages -- no percentile rankings. Standard census tracts are ranked against each other to produce the 0-1 percentile that makes SVI useful. Tribal tracts are explicitly not ranked "because of geographic separation and cultural diversity." If the system attempts to use tribal tract SVI data the same way it uses county-level NRI data, it will either get raw values without comparative context or accidentally rank tribal tracts against standard tracts (methodologically invalid).

**Why it happens:** Developers see "SVI data for tribal tracts" in the CDC documentation and assume it is functionally equivalent to standard SVI data. The difference (ranked vs unranked) is buried in documentation footnotes.

**Consequences:** SVI percentiles for Tribal lands are either missing (if using tribal tracts correctly) or fabricated (if ranking against non-tribal tracts, which CDC explicitly advises against). Either outcome undermines the data section's credibility.

**Warning signs:**
- SVI code path works for test counties but produces empty/null percentiles for tribal geographies
- Team considers "just ranking tribal tracts against all tracts" as a solution
- SVI values for Tribal areas look anomalous compared to surrounding counties

**Prevention:**
1. Use the COUNTY-LEVEL SVI data through the existing area-weighted crosswalk (same pattern as NRI data). Tribal lands overlap counties; aggregate county-level SVI to Tribal boundaries via `tribal_county_area_weights.json`. Do NOT use the tribal tract database.
2. If tract-level precision is desired, use STANDARD census tracts (not tribal tracts) and build a tract-to-AIANNH crosswalk. Standard tracts ARE ranked and cover the same geography.
3. Document the methodological choice: "SVI scores are derived from county-level CDC/ATSDR SVI data aggregated to Tribal boundaries via area-weighted crosswalk, consistent with the methodology used for FEMA NRI data."

**Recovery cost:** MEDIUM -- requires changing the data ingestion pipeline but does not affect document rendering if the schema is consistent.

**Confidence:** HIGH (CDC SVI FAQ explicitly states tribal tracts are unranked)

---

### CRIT-04: NRI Version Instability -- FEMA Migration to RAPT

**What goes wrong:** FEMA is migrating the National Risk Index into the Resilience Analysis and Planning Tool (RAPT). As of December 2025, NRI v1.20 data is available, but the original hazards.fema.gov/nri URLs are already redirecting to fema.gov/emergency-managers/practitioners/resilience-analysis-and-planning-tool. The existing `download_nri_data.py` script may silently download different data than expected, or fail entirely if URLs change. Version 1.20 introduced significant changes: overhauled tsunami, inland flooding, landslide, and volcanic activity data; Connecticut planning regions replaced counties; social vulnerability and community resilience metrics updated.

**Why it happens:** The system detects NRI version via filename patterns (`_detect_nri_version()`) but does not validate that the data schema matches expectations. Column names could change between versions.

**Consequences:** Silently loading a new NRI version breaks area-weighted aggregation if column names change. Connecticut's 8 planning regions (not counties) break the county FIPS crosswalk for any Tribe in CT. Overhauled hazard scores for 4 hazard types make before/after comparisons meaningless.

**Warning signs:**
- Download script gets HTTP 301/302 redirects
- NRI CSV has unexpected column names or missing expected columns
- Connecticut FIPS codes in crosswalk no longer match NRI data
- Hazard scores for tsunami/inland flooding change dramatically between pipeline runs

**Prevention:**
1. Pin the NRI version explicitly. Store the expected download URL and SHA256 checksum in config. Validate after download.
2. Add schema validation: after CSV load, check that all expected column names (RISK_SCORE, RISK_RATNG, EAL_VALT, SOVI_SCORE, RESL_SCORE, etc.) exist. Fail loudly if missing.
3. Handle Connecticut planning regions: add a mapping from CT planning regions to legacy county FIPS for crosswalk compatibility, or update the crosswalk to handle both.
4. Add a version change detection log: when NRI version changes, emit a WARNING with the old vs new version and flag affected hazard types.

**Recovery cost:** MEDIUM -- mostly configuration and validation code, but CT planning region handling requires crosswalk update.

**Confidence:** HIGH (verified via FEMA NRI v1.20 release notes and URL redirect testing)

---

## Technical Debt Patterns

Mistakes that create compounding maintenance burden.

### DEBT-01: Climate Projection Temporal Complexity

**What goes wrong:** NOAA/LOCA2 climate projections have fundamentally different temporal characteristics than current data sources. NRI is a point-in-time snapshot. Awards are historical (FY lookback). Climate projections are multi-scenario, multi-period futures (2025-2049, 2050-2074, 2075-2099 under SSP2-4.5, SSP3-7.0, SSP5-8.5). The per-Tribe JSON cache schema (`{tribe_id}.json`) is flat and does not accommodate temporal dimensions.

**Why it happens:** The existing cache schema evolved for single-point-in-time data. Adding "temperature will be X under scenario Y in period Z" requires a nested structure that does not fit the current pattern.

**Consequences:** Either the schema balloons with redundant keys (`temp_ssp245_2050`, `temp_ssp245_2075`, `temp_ssp370_2050`...) creating hundreds of fields, or projections are collapsed to a single "most likely" value losing the scenario range that makes climate data useful.

**Prevention:**
1. Design the climate projection cache schema BEFORE implementation. Model it as:
   ```json
   {
     "climate_projections": {
       "source": "LOCA2-CMIP6",
       "variables": {
         "temperature": {
           "historical": {"baseline_period": "1981-2010", "value_degF": 52.3},
           "projections": [
             {"period": "2025-2049", "scenario": "SSP2-4.5", "median": 54.1, "range": [53.2, 55.4]},
             {"period": "2050-2074", "scenario": "SSP2-4.5", "median": 56.8, "range": [55.1, 58.9]}
           ]
         }
       }
     }
   }
   ```
2. Use arrays of projection objects rather than flattened key names
3. Decide upfront which scenarios and periods to include (recommend SSP2-4.5 and SSP5-8.5 only -- moderate and high -- for three periods)
4. Document the schema in a JSON Schema or Pydantic model BEFORE writing any data population code

**Which phase:** Must be resolved in data model design, before any population script is written.

---

### DEBT-02: Geographic Crosswalk Proliferation

**What goes wrong:** Each new data source requires a geographic crosswalk. The system already has: AIANNH-to-Tribe crosswalk, area-weighted AIANNH-to-county crosswalk, NRI tribal relational CSV, state-level fallback. Adding NOAA climate data (gridded at ~6km LOCA2 resolution), CDC SVI (census tract level), and expanded NRI (now with CT planning regions) means potentially 3 more crosswalk layers. Each crosswalk has its own CRS assumptions, minimum overlap thresholds, boundary vintage differences, and Alaska-specific handling.

**Why it happens:** Different federal datasets use different geographic units. Developers build one-off crosswalk solutions per source rather than generalizing the crosswalk infrastructure.

**Consequences:** Crosswalk logic is duplicated across scripts. A boundary vintage update (e.g., 2020 vs 2030 census tracts) requires updating N crosswalks independently. Area weight calculations may be inconsistent across sources. Alaska CRS handling (EPSG:3338) must be re-implemented for each crosswalk.

**Prevention:**
1. Refactor crosswalk into a reusable geographic mapping service. The current `build_area_crosswalk.py` is well-structured (dual CRS, minimum overlap filter, atomic writes) -- extract its core logic into a `src/geo/crosswalk.py` module that any data source can use.
2. All new data sources should map to the SAME county FIPS intermediate layer. County is the common geographic denominator across NRI, SVI, and LOCA2 (which provides county-level time series).
3. The area-weighted county-to-Tribe crosswalk (`tribal_county_area_weights.json`) becomes the single bridge. This is already the pattern -- formalize it.
4. Add a crosswalk version metadata field so downstream consumers know which boundary vintage was used.

**Which phase:** Crosswalk refactoring should happen in the first data integration phase.

---

### DEBT-03: Document Engine Section Creep

**What goes wrong:** The DocxEngine currently assembles a 10-section document by calling individual render functions from `docx_sections.py`. Adding a vulnerability assessment section (or multiple -- climate projections, SVI decomposition, expanded hazard detail) increases the section count. Each section needs audience differentiation (internal vs congressional), confidence scoring, and style management. The `generate()` method in `DocxEngine` becomes a monolithic 200+ line function with growing parameter lists.

**Why it happens:** Each milestone adds "just one more section" without restructuring the assembly pipeline. The existing `render_hazard_summary()` is already 100+ lines with conditional audience logic.

**Consequences:** Adding a vulnerability section requires modifying `DocxEngine.generate()`, `docx_sections.py`, and the orchestrator. Testing requires full document generation. Style consistency across sections becomes harder to maintain. The `TribePacketContext` dataclass grows with more optional fields.

**Prevention:**
1. Consider the vulnerability data an EXPANSION of the existing hazard section rather than new sections. The `render_hazard_summary()` function already renders NRI composite ratings and USFS wildfire -- extend it with subsections for climate projections and enhanced vulnerability metrics.
2. If new sections are needed, use a section registry pattern: register renderers with metadata (audience filter, ordering, dependencies) and let the engine iterate the registry rather than hardcoding calls.
3. Keep `TribePacketContext` extensible by nesting new data under `hazard_profile` dict rather than adding top-level fields. The context already has `hazard_profile: dict = field(default_factory=dict)` -- use it.
4. Factor audience-differentiated text into a lookup table (not inline if/else blocks in renderers).

**Which phase:** Address during vulnerability section implementation. Plan the document structure before writing renderers.

---

## Integration Gotchas

Pitfalls specific to integrating new data into the existing TCR Policy Scanner architecture.

### INT-01: NRI Expanded Fields Not Parsed by Current CSV Reader

**What goes wrong:** The current `_load_nri_county_data()` in `hazards.py` (lines 323-392) explicitly parses: `RISK_SCORE`, `RISK_RATNG`, `RISK_VALUE`, `EAL_VALT`, `EAL_SCORE`, `EAL_RATNG`, `SOVI_SCORE`, `SOVI_RATNG`, `RESL_SCORE`, `RESL_RATNG`, and per-hazard `{CODE}_RISKS`, `{CODE}_RISKR`, `{CODE}_EALT`, `{CODE}_AFREQ`, `{CODE}_EVNTS`. The milestone wants to add Expected Annual Loss by consequence type (`EAL_VALB` buildings, `EAL_VALP` population, `EAL_VALA` agriculture), Community Resilience subindicators, and per-hazard EAL breakdowns. These fields EXIST in the NRI CSV but are not currently parsed.

**Why it happens:** Phase 13 extracted only the fields needed for hazard profiling. The NRI CSV has 400+ columns; most were ignored.

**Consequences:** If the expanded fields are added without understanding the existing parser, developers may accidentally break the current field extraction, change the cache schema in backward-incompatible ways, or double-parse the CSV.

**Warning signs:**
- Tests for existing hazard profile fields start failing
- Cache file size doubles unexpectedly
- Existing `top_hazards` ranking changes because of parser changes

**Prevention:**
1. Extend `_load_nri_county_data()` incrementally. Add new fields to the `record` dict alongside existing ones. Do NOT restructure the existing fields.
2. Add the expanded fields under a new sub-dict key (e.g., `"eal_breakdown"`, `"resilience_detail"`) rather than at the top level of the record.
3. Run the full hazard population pipeline after changes and diff the output against the current 592 profiles. Any changes to existing fields indicate a regression.
4. Add a test that loads a sample NRI CSV row and verifies both old and new fields are extracted correctly.

**Which phase:** NRI expansion phase (should be early -- it is extending existing infrastructure).

---

### INT-02: Pre-Cache Pattern Violations During Climate Data Integration

**What goes wrong:** The system's cardinal rule is ZERO API calls during document generation. All data is pre-cached as JSON. Climate projection data from NOAA may tempt developers to add on-demand API calls (e.g., fetching projections for a specific lat/lon at render time), especially if the pre-computed county-level LOCA2 data does not perfectly match a Tribe's geographic center.

**Why it happens:** NOAA CDO API (5 req/sec, 10,000/day limit) is "easy" to call. Pre-caching 592 Tribes x multiple variables x multiple scenarios x multiple periods seems like a lot of upfront work. Developers may rationalize "just one API call per Tribe" during generation.

**Consequences:** Document generation becomes network-dependent. Batch generation of 592 Tribes hits rate limits. Pipeline fails in air-gapped or offline environments. Breaks the reproducibility guarantee (same inputs = same outputs).

**Warning signs:**
- `import requests` or `import urllib` appears in any file under `src/packets/`
- New `src/packets/*.py` files make network calls
- Document generation takes minutes instead of seconds
- `--dry-run` behavior changes (previously fast, now slow)

**Prevention:**
1. ENFORCE the boundary: `src/packets/` must NEVER import network libraries. Add a test (cross-cutting compliance, similar to existing `test_xcut_compliance.py`) that scans for network imports in the packets module.
2. All NOAA/climate data must be pre-cached by a `scripts/populate_climate.py` script that follows the same pattern as `scripts/populate_hazards.py` and `scripts/populate_awards.py`.
3. Climate projection data should be stored as per-Tribe JSON in a new `data/climate_projections/` directory (following the `data/hazard_profiles/` pattern).
4. The orchestrator loads climate data from cache, merges into `TribePacketContext.hazard_profile`, and passes to renderers.

**Which phase:** Must be enforced from the very first data integration phase. Add the compliance test before writing any population scripts.

---

### INT-03: Area-Weighted Aggregation Invalid for Climate Extremes

**What goes wrong:** The existing area-weighted crosswalk works well for NRI risk scores because risk is roughly proportional to geographic area (more area in a high-risk county = more exposure). For climate projections (temperature, precipitation), area-weighting is still valid for spatial averaging. BUT for extreme event metrics (days above 100F, 100-year flood depths), area-weighted averaging is INVALID. A Tribe whose land is 60% in a low-risk county and 40% in a high-risk county should not report an average extreme -- they experience the extreme in the 40% of their land that is exposed.

**Why it happens:** Developers reuse the existing aggregation function without considering that climate variables have different aggregation semantics.

**Consequences:** Extreme climate risks are systematically understated for Tribes spanning diverse geographies. A Tribe with land in both a flood plain and upland area gets a "moderate" flood risk instead of correctly reporting "severe flooding on portions of Tribal land."

**Warning signs:**
- Climate projections for multi-county Tribes look unremarkably average
- Extreme event counts (days > 100F) are fractional (e.g., 7.3 days), which is mathematically correct but physically meaningless
- Tribes known to face severe climate impacts show moderate scores

**Prevention:**
1. Define aggregation rules per variable type:
   - **Means** (average temperature, annual precipitation): area-weighted average (valid)
   - **Extremes** (max temperature, days above threshold): area-weighted MAX or report the worst-case county
   - **Counts** (extreme event days): area-weighted average for central tendency, but also report the range (min county, max county)
2. Store both the area-weighted aggregate AND the per-county values in the cache, so document renderers can say "X on average, up to Y in the most exposed portion of Tribal land."
3. Add unit tests with a known multi-county Tribe where counties have very different climate profiles.

**Which phase:** Climate projection population script phase.

---

### INT-04: Audience Air Gap Leakage in Vulnerability Data

**What goes wrong:** The system maintains a strict air gap between Doc A/C (internal strategy, confidential) and Doc B/D (congressional, facts-only). No strategy words, advocacy levers, or organizational names cross the gap. Vulnerability data creates NEW air gap risks: internal documents might include "leverage this vulnerability data to argue for increased funding" while congressional documents should present the same data factually. If vulnerability narrative text is not audience-filtered, strategy language leaks into congressional documents.

**Why it happens:** Vulnerability data is inherently interpretive. Writing "high vulnerability" is factual; writing "this vulnerability justifies emergency funding" is strategic. The line is blurry. Developers write a single renderer and forget to branch on `doc_type_config.include_strategy`.

**Consequences:** Congressional documents contain strategic language, violating the air gap. Audit tools (`test_audience_filtering.py`) catch this in tests, but only if the forbidden word list is updated to include vulnerability-specific strategy terms.

**Warning signs:**
- `test_audience_filtering.py` does not have test cases for vulnerability section
- Vulnerability section renderer has no `if doc_type_config:` branching
- Words like "leverage," "exploit," "capitalize," "argue," "justify" appear in vulnerability section text

**Prevention:**
1. Before writing the vulnerability renderer, update the audience filtering test to include vulnerability-specific forbidden words for Doc B/D.
2. Use the established pattern: check `doc_type_config.is_congressional` before any interpretive text. Use the same branching pattern as `render_hazard_summary()` (line 529-531 of `docx_sections.py`).
3. Write the congressional version first (facts-only is harder than strategy), then add strategy layer for internal docs.
4. Add vulnerability sections to the structural validator that already validates 992/992 documents.

**Which phase:** Document rendering phase for vulnerability sections.

---

### INT-05: Website Data Size Explosion

**What goes wrong:** The existing `tribes.json` served by the static website is a compact index for search. Adding vulnerability data (climate projections per scenario per period, SVI themes, expanded NRI metrics) to the web data layer can balloon the JSON payload from manageable (< 1MB) to multi-megabyte. The website uses vanilla JS with no build system, no code splitting, no lazy loading -- it fetches `tribes.json` on page load.

**Why it happens:** Developers add vulnerability fields to `build_web_index.py` output without measuring payload size impact. Each Tribe's climate projection data could be 2-5KB; multiply by 592 Tribes = 1.2-3MB additional payload on a site designed for minimal data transfer.

**Consequences:** Page load time increases significantly, especially on mobile/low-bandwidth connections common in rural Tribal communities. The site may become unusable for the very audience it serves.

**Warning signs:**
- `tribes.json` file size exceeds 2MB
- Page load time exceeds 3 seconds on 3G simulation
- Browser console shows long JSON parse times

**Prevention:**
1. Keep `tribes.json` as a summary index (name, states, ecoregion, doc availability). Do NOT embed full vulnerability data.
2. If vulnerability data needs to be on the website, create per-Tribe JSON files (`data/profiles/{tribe_id}.json`) loaded on-demand when a Tribe is selected. This follows a detail-on-demand pattern.
3. Use summary indicators in the index (e.g., `"climate_risk": "high"`, `"top_hazard": "Wildfire"`) instead of full projection arrays.
4. Measure payload size as part of the web build script and fail if `tribes.json` exceeds a threshold (e.g., 1.5MB).

**Which phase:** Website update phase (likely last).

---

## Performance Traps

### PERF-01: NOAA API Rate Limits and Pre-Caching 592 Tribes

**What goes wrong:** The NOAA CDO API allows 5 requests per second and 10,000 per day. If climate data requires per-Tribe API calls (e.g., station-based observations for 592 Tribes), the pipeline needs at minimum 592 calls. With retry logic and multiple variables, this can reach thousands of calls. The existing USASpending pipeline already demonstrated this problem: 14 CFDAs x 5 FYs = 70 sequential queries with circuit breaker resilience.

**Why it happens:** Per-Tribe granularity seems necessary, but NOAA API is not designed for bulk extraction.

**Consequences:** Population script takes hours. Rate limit errors require circuit breaker and retry logic. Daily limit (10,000) may be exhausted in a single run if multiple variables are queried.

**Prevention:**
1. Use BULK DOWNLOAD instead of API calls. LOCA2 county-level time series are available as NetCDF files from USGS. Download once, extract per-county, aggregate via crosswalk.
2. If API is necessary, implement the circuit breaker pattern from `src/scrapers/circuit_breaker.py` (already proven in USASpending pipeline).
3. Cache raw API responses as intermediate files before per-Tribe aggregation. A single county-level response serves all Tribes overlapping that county.
4. Consider the NASA NEX-GDDP-CMIP6 dataset as an alternative -- available on AWS Open Data with no API limits for bulk download.

**Which phase:** Climate data population script phase.

---

### PERF-02: NetCDF/GeoTIFF Processing Memory Requirements

**What goes wrong:** If using gridded climate data (LOCA2 at ~6km resolution), the raw NetCDF files for a single variable across CONUS can be multi-GB. Loading these into memory with xarray/rasterio for spatial extraction requires significant RAM. The current pipeline runs on commodity hardware with typical developer machine resources.

**Why it happens:** Climate data is fundamentally large. Downscaled projections at daily resolution across decades and multiple models generate massive datasets.

**Consequences:** Population script crashes with MemoryError. Processing time becomes hours instead of minutes. Cannot run on CI/CD or lightweight environments.

**Prevention:**
1. Use pre-aggregated county-level CSV/NetCDF from USGS rather than raw grid data. County-level LOCA2 time series are already computed and available.
2. If grid extraction is necessary, use chunked processing with xarray (`chunks` parameter) and extract one county at a time.
3. Add memory monitoring to the population script (similar to the `gc.collect()` call every 25 Tribes in `run_all_tribes()` in the orchestrator).
4. Document hardware requirements: "Climate data population requires X GB RAM, Y GB disk."

**Which phase:** Climate data population script phase.

---

## Security and Data Governance Pitfalls

### SEC-01: T0 Classification Boundary for Vulnerability Data

**What goes wrong:** The system is classified T0 (Open) -- all data comes from public federal sources. CDC SVI data at the census tract level, while publicly available, can be combined with Tribal boundary data to reveal granular socioeconomic conditions of specific Tribal communities. This approaches sensitive territory even though each individual dataset is public.

**Why it happens:** Data combination creates emergent sensitivity. Publicly available socioeconomic data + publicly available Tribal boundaries = detailed Tribal vulnerability profiles that may not align with how Tribal Nations choose to represent themselves.

**Consequences:** Tribal Nations may object to detailed SVI decomposition being published or shared with congressional offices. Potential violation of data sovereignty principles even with public-source data.

**Warning signs:**
- SVI theme scores (poverty rate, disability rate, language isolation) appear in congressional documents
- Per-Tribe socioeconomic detail exceeds what Tribal Nations themselves publish
- No consultation process for what vulnerability data appears in documents

**Prevention:**
1. SVI data in documents should be at the COMPOSITE level only (overall SVI rank), not decomposed into themes that reveal specific socioeconomic conditions.
2. Internal documents (Doc A/C) may include theme decomposition for strategic planning, but congressional documents (Doc B/D) should show only composite scores with source citation.
3. Consider adding a Tribal opt-out mechanism: a config file where specific Tribes can suppress vulnerability detail.
4. Frame SVI data as a characteristic of the GEOGRAPHY, not the PEOPLE: "Counties overlapping Tribal land have SVI score of X" rather than "This Tribal Nation has vulnerability score of X."

**Which phase:** Data model design phase and document rendering phase.

---

### SEC-02: Climate Projection Misrepresentation Risk

**What goes wrong:** Climate projections are probability distributions, not predictions. Presenting a single "projected temperature increase of 3.5F by 2050" without scenario context, model spread, or confidence intervals can be cited as authoritative fact by congressional offices and used in ways that misrepresent the science.

**Why it happens:** Documents need to be accessible. Showing ranges and confidence intervals is complex. Developers simplify for readability.

**Consequences:** Congressional staff cite the document's projection numbers in hearings or legislation without uncertainty context. If projections prove different from reality, the system's credibility is damaged. May also expose the project to accusations of cherry-picking scenarios.

**Prevention:**
1. Always present projections as ranges: "2.1-4.8F increase by mid-century depending on emissions pathway."
2. Name the scenarios: "Under moderate emissions (SSP2-4.5)" and "Under high emissions (SSP5-8.5)."
3. Include the model count: "Based on N climate models from CMIP6."
4. Add a standardized footnote to every climate projection: "Climate projections represent model-based estimates under specific emissions scenarios. Actual outcomes depend on future emissions trajectories and natural variability."
5. In Doc B/D (congressional), present only the range. In Doc A/C (internal), the full scenario breakdown can be included.

**Which phase:** Document rendering phase for climate sections.

---

## "Looks Done But Isn't" Checklist

Common false-completion signals when integrating climate vulnerability data.

### DONE-01: "All 592 Tribes Have Climate Data"

**Reality check:** Coverage completeness requires verifying:
- [ ] LOCA2 county-level data covers ALL counties in the crosswalk (it covers CONUS but NOT territories)
- [ ] Alaska climate data uses appropriate grid/station data (LOCA2 covers Alaska but with caveats on coastal areas)
- [ ] CDC SVI data exists for all counties in the crosswalk (some rural counties have suppressed data)
- [ ] Expanded NRI fields exist for all hazard types (only 14 of 18 have EAL data)
- [ ] The 19 Tribes with no NRI crosswalk match (from Phase 13) still have no match -- vulnerability data does not fix geographic coverage gaps
- [ ] Connecticut's planning region change in NRI v1.20 does not break any Tribe's crosswalk

The existing coverage report pattern (`hazard_coverage_report.json`) should be extended to track climate and SVI coverage separately.

### DONE-02: "The Vulnerability Section Renders Correctly"

**Reality check:** A section that renders without errors may still be wrong:
- [ ] Area-weighted values are mathematically correct (spot-check against manual calculation for a known multi-county Tribe)
- [ ] Temperature values use consistent units (F vs C -- the system serves U.S. audience, use Fahrenheit)
- [ ] Dollar values (EAL) go through `utils.format_dollars()` -- the ONLY dollar formatter
- [ ] Confidence scoring (`section_confidence()`) is applied to the vulnerability section
- [ ] Audience filtering is applied (no strategy words in Doc B/D)
- [ ] Sovereignty-respectful framing is used throughout
- [ ] Empty data gracefully renders "Data not available" instead of zeros or blank space

### DONE-03: "The Data Pipeline Is Complete"

**Reality check:** A pipeline that produces output files is not complete until:
- [ ] Schema validation exists for new cache files (like the structural validator for DOCX)
- [ ] Coverage report generates for each new data source
- [ ] Atomic writes used for all cache files (existing pattern: tempfile + os.replace)
- [ ] encoding="utf-8" on all file operations (Windows requirement)
- [ ] 10MB size cap check for any JSON loaded at render time
- [ ] Circuit breaker covers all external API calls
- [ ] Dry-run mode works without network access
- [ ] Single-Tribe mode works for debugging (`--tribe epa_001`)

### DONE-04: "The Website Shows Vulnerability Data"

**Reality check:**
- [ ] `tribes.json` payload size is measured and within budget
- [ ] Dark mode styling applies to new vulnerability UI elements
- [ ] ARIA attributes exist for any new interactive elements
- [ ] No innerHTML usage (existing XSS prevention pattern)
- [ ] Works on mobile viewport (Tribal communities often mobile-first)
- [ ] Vulnerability data loads on-demand, not on page load

---

## Pitfall-to-Phase Mapping

| Phase Topic | Likely Pitfall | Mitigation | Severity |
|---|---|---|---|
| NRI expansion (adding EAL breakdown, RESL detail) | INT-01: Existing CSV parser regression | Extend incrementally, diff cache output | HIGH |
| NRI expansion | CRIT-04: NRI v1.20 schema changes, CT planning regions | Pin version, validate schema, handle CT | HIGH |
| CDC SVI integration | CRIT-01: Confusion with NRI SOVI | Clarify relationship, use county-level SVI | CRITICAL |
| CDC SVI integration | CRIT-03: Tribal tracts are unranked | Use county-level SVI through existing crosswalk | HIGH |
| CDC SVI integration | SEC-01: Socioeconomic detail sensitivity | Composite only in Doc B/D, theme detail in Doc A/C only | HIGH |
| NOAA climate projections | DEBT-01: Temporal schema complexity | Design schema before implementation | HIGH |
| NOAA climate projections | INT-03: Invalid aggregation for extremes | Per-variable aggregation rules | HIGH |
| NOAA climate projections | PERF-01: API rate limits | Use bulk download, not API | MEDIUM |
| NOAA climate projections | SEC-02: Projection misrepresentation | Always present ranges with scenario context | HIGH |
| Document rendering | CRIT-02: Deficit framing | Framing vocabulary module, sovereignty-first language | CRITICAL |
| Document rendering | INT-04: Audience air gap leakage | Test vulnerability sections against forbidden words | HIGH |
| Document rendering | DEBT-03: Section creep in DocxEngine | Extend hazard section, use section registry | MEDIUM |
| Website integration | INT-05: Data size explosion | Summary in index, detail on-demand | MEDIUM |
| Crosswalk infrastructure | DEBT-02: Crosswalk proliferation | Reusable crosswalk service, county as common denominator | MEDIUM |

---

## Sources

### HIGH confidence (official documentation, verified)
- [FEMA NRI Data Resources](https://hazards.fema.gov/nri/data-resources) -- NRI data download, column definitions
- [FEMA NRI Social Vulnerability](https://hazards.fema.gov/nri/social-vulnerability) -- NRI SOVI methodology change to CDC SVI
- [FEMA NRI v1.19 Change Summary](https://hazards.fema.gov/nri/change-summary-v119) -- Social vulnerability methodology change
- [CDC/ATSDR SVI Data & Documentation](https://atsdr.cdc.gov/place-health/php/svi/svi-data-documentation-download.html) -- SVI methodology, versions
- [CDC/ATSDR SVI FAQ](https://www.atsdr.cdc.gov/place-health/php/svi/svi-frequently-asked-questions-faqs.html) -- Tribal tracts not ranked
- [Census Tribal Tract vs Standard Tracts](https://www.census.gov/newsroom/blogs/random-samplings/2012/07/decoding-state-county-census-tracts-versus-tribal-census-tracts.html)
- [NOAA CDO API v2 Documentation](https://www.ncdc.noaa.gov/cdo-web/webservices/v2) -- 5 req/sec, 10,000/day limits
- [FEMA NRI FAQ December 2025](https://www.fema.gov/sites/default/files/documents/fema_national-risk-index_faq-page-documentation.pdf) -- v1.20 changes

### MEDIUM confidence (verified with multiple sources)
- [USGS CMIP6-LOCA2 County Data](https://www.usgs.gov/data/cmip6-loca2-temperature-and-precipitation-variables-resilient-roadway-design-1950-2100) -- County-level time series availability
- [NASA NEX-GDDP-CMIP6](https://www.nccs.nasa.gov/services/data-collections/land-based-products/nex-gddp-cmip6) -- Downscaled climate projections
- [LOCA2 Downscaling](https://loca.ucsd.edu/) -- Methodology and known biases
- [Climate Vulnerability Assessment Resources](https://cig.uw.edu/resources/tribal-vulnerability-assessment-resources/) -- Tribal vulnerability assessment framing
- [U.S. Climate Resilience Toolkit - Tribal Nations](https://toolkit.climate.gov/topic/tribal-nations) -- Sovereignty and assessment practices
- [NHGIS Geographic Crosswalks](https://www.nhgis.org/geographic-crosswalks) -- Census tract crosswalk methodologies

### LOW confidence (single source or unverified)
- FEMA RAPT migration timeline -- URL redirects observed but migration completion date uncertain
- NRI v1.20 Connecticut planning region impact on existing crosswalks -- inferred from release notes, not tested against system
- LOCA2 moisture projection bias -- mentioned in single academic source, impact on this use case unclear

### Codebase references (verified by reading source)
- `src/packets/hazards.py` -- NRI CSV parser, area-weighted aggregation, USFS override pattern
- `scripts/build_area_crosswalk.py` -- Area-weighted crosswalk (dual CRS, 1% overlap filter, atomic writes)
- `src/packets/context.py` -- TribePacketContext dataclass (hazard_profile dict field)
- `src/packets/docx_engine.py` -- Document assembly pipeline, save with atomic writes
- `src/packets/docx_sections.py` -- Section renderers including `render_hazard_summary()` (line 482+)
- `src/packets/doc_types.py` -- Document type configuration (A/B/C/D audience differentiation)
- `src/paths.py` -- Centralized path constants (35 constants, including HAZARD_PROFILES_DIR)
- `src/packets/orchestrator.py` -- PacketOrchestrator with hazard cache loading pattern
- `docs/web/js/app.js` -- Static website, vanilla JS, tribes.json payload loading
