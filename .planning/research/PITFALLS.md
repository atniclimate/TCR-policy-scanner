# Domain Pitfalls: Tribe-Specific Advocacy Packet Generation

**Domain:** Per-Tribe DOCX advocacy packet generation for 574 federally recognized Tribes
**Project:** TCR Policy Scanner v1.1
**Researched:** 2026-02-10
**Confidence:** MEDIUM-HIGH (most findings verified against official API docs and issue trackers)

---

## Critical Pitfalls

Mistakes that cause incorrect data in advocacy documents, broken generation pipelines, or unusable outputs. These would block shipment or produce documents that undermine credibility with congressional offices.

---

### C-1: Tribal Name Matching Produces False Positives and Misattributed Awards

**What goes wrong:** Fuzzy-matching 574 BIA-listed Tribal names against USASpending recipient names produces incorrect matches. A Tribe gets credited with another Tribe's awards, or awards are missed entirely. For example:
- "Cheyenne River Sioux Tribe" matches "Cheyenne and Arapaho Tribes" (partial overlap)
- "Pueblo of Laguna" matches "Laguna Development Corporation" (subsidiary, not the Tribe)
- "The Confederated Tribes of the Colville Reservation" in BIA list vs "Confederated Tribes Colville Reservation" in USASpending (leading article + prepositions stripped)
- Multiple Tribes share substring tokens: "Sioux" appears in 8+ Tribe names, "Chippewa" in 6+, "Pueblo" in 19+

**Why it happens:** USASpending recipient names come from SAM.gov registrations where Tribes self-report. The BIA Federal Register list uses official legal names with articles ("The"), formal prepositions ("of the"), and parenthetical former names. These are two independent naming authorities that never agreed on a canonical form. Additionally, Tribal enterprises, subsidiaries, and housing authorities register as separate recipients but contain the Tribe's name as a substring.

**Consequences:** A document handed to a congressional office showing $2.3M in FEMA BRIC awards to a Tribe that actually received $0 destroys credibility instantly. False positives are worse than false negatives here -- better to show "no data available" than wrong data.

**Prevention:**
1. Build a curated alias table mapping each of the 574 BIA names to known USASpending recipient name variants. Seed it with systematic transformations (strip "The ", normalize "of the" to "of", collapse whitespace) then manually verify the top 50 recipients by award volume.
2. Use UEI (Unique Entity Identifier) as the primary matching key where possible -- it is deterministic. Fall back to fuzzy name matching only where UEI lookup fails.
3. Use `rapidfuzz` (not `thefuzz`) with `token_sort_ratio` for fuzzy matching, but set a high threshold (>=85) and require manual review for matches between 85-95.
4. Exclude known non-Tribal-government entities: filter out recipients containing "Corporation", "LLC", "Housing Authority", "Development", "Enterprise" unless they are in the curated alias table.
5. Include a `match_confidence` field in every Tribe-award linkage, and surface LOW confidence matches in a validation report rather than silently including them.

**Warning signs:** During testing, if >50 Tribes have 0 matched awards across all 16 programs, the matching logic is too strict. If any Tribe shows awards in programs they clearly do not participate in (e.g., a Southwest desert Tribe showing coastal flooding grants), matching is too loose.

**Detection:** Automated test: for each match, assert that the matched recipient's state overlaps with the Tribe's known state(s). Flag cross-state matches for manual review.

**Severity:** BLOCKS SHIPMENT -- incorrect financial data in congressional documents is unacceptable.

**Phase:** Should be addressed in the earliest data pipeline phase. Build the alias table first and validate it before building anything downstream.

---

### C-2: EPA EJScreen Data Source Is Unavailable -- Tool Was Removed in February 2025

**What goes wrong:** The project plan assumes EPA EJScreen as a data source for environmental justice indicators. EPA removed EJScreen from its website on February 5, 2025, as part of the administration's rollback of environmental justice programs. The EPA placed over 100 employees at the Office of Environmental Justice on leave. The official API endpoint is gone.

**Why it happens:** Executive policy changes eliminated the tool. This is not a temporary outage -- the institutional infrastructure behind the data was dismantled. While the underlying data (ACS demographics, EPA facility data, etc.) still exists in component sources, the pre-computed EJ indices at census-tract level are no longer served by EPA.

**Consequences:** Any code written against `ejscreen.epa.gov` API endpoints will fail with 404/connection errors. The project loses one of its four planned hazard data sources, weakening the hazard profiling capability.

**Prevention:**
1. Use PEDP (Public Environmental Data Partners) reconstructed EJScreen data at `screening-tools.com` or `pedp-ejscreen.azurewebsites.net`. This is a Harvard/EDGI coalition that recreated EJScreen v2.3 using scraped data from before the shutdown.
2. Design the hazard profiling module with a source-abstraction layer so that EJScreen data can come from PEDP, archived CSVs, or a future restoration of the official tool.
3. Download and cache the PEDP EJScreen dataset locally rather than depending on their API availability (PEDP is a volunteer effort with no SLA).
4. Consider whether FEMA NRI county-level data alone is sufficient for the hazard profile, with EJScreen as an enrichment layer rather than a required source.
5. Document the data provenance clearly: "EJ indicators sourced from PEDP reconstruction of EPA EJScreen v2.3 (pre-Feb 2025 data)" so users know the data is not current.

**Warning signs:** Any HTTP request to `ejscreen.epa.gov` returning non-200 status. Any reference to EJScreen in code comments or docs that assumes the official EPA endpoint.

**Detection:** Integration test that validates all external data source URLs are reachable before starting a batch generation run.

**Severity:** BLOCKS SHIPMENT if EJScreen is a required data source and no alternative is implemented.

**Phase:** Must be resolved during the data source/hazard profiling phase. Cannot be deferred.

**Sources:**
- [EPA Removes EJScreen](https://envirodatagov.org/epa-removes-ejscreen-from-its-website/) (MEDIUM confidence)
- [PEDP Screening Tools](https://screening-tools.com) (MEDIUM confidence)
- [Harvard EJScreen Reconstruction](https://eelp.law.harvard.edu/tracker/epa-added-environmental-health-indicators-to-ejscreen/) (MEDIUM confidence)

---

### C-3: BEA RIMS II Multipliers Are Paid ($500/region), Not Freely Available via API

**What goes wrong:** The economic impact synthesis assumes BEA regional multipliers can be queried programmatically for each Tribe's county/region. In reality, RIMS II multipliers are a paid product ($500 per region as of August 2025, $150 per industry) ordered through the BEA website. There is no free public API. Purchasing multipliers for all relevant regions covering 574 Tribes across 50 states would cost thousands of dollars.

**Why it happens:** BEA RIMS II is a commercial product, not an open data endpoint. The project description says "BEA regional multipliers" as if they were freely available like FEMA NRI data.

**Consequences:** Either the project cannot include district-level economic multiplier framing (a key differentiator of the advocacy packets), or it must find an alternative methodology, or it must budget for RIMS II data purchases.

**Prevention:**
1. Use publicly available, defensible approximations instead of RIMS II:
   - FEMA's standard 4:1 benefit-cost ratio for pre-disaster mitigation (this is already in the project spec and is free/public)
   - IMPLAN multipliers if available through institutional access
   - Published academic literature on federal spending multipliers by region type (rural/urban/tribal)
2. Use a tiered approach: apply the FEMA 4:1 BCR as the primary framing ("every $1 of FEMA BRIC investment returns $4 in avoided disaster costs") and note it as the standard federal methodology.
3. For employment multiplier estimates, use BLS county-level employment data (free) combined with published federal spending employment multiplier ranges from CBO or academic sources.
4. Do NOT present approximations as if they are RIMS II outputs. Label the methodology clearly.

**Warning signs:** Any code that attempts to call a BEA RIMS II API endpoint. Any test that assumes multiplier data is retrievable programmatically.

**Detection:** Review economic impact module for data source assumptions during design review.

**Severity:** DEGRADES QUALITY if no alternative is found. Does not block shipment if FEMA BCR is used as fallback.

**Phase:** Must be resolved during economic impact synthesis design. The approach should be decided before code is written.

**Sources:**
- [BEA RIMS II Online Order System](https://apps.bea.gov/regional/rims/rimsii/) (HIGH confidence)
- [BEA RIMS II Pricing Update](https://www.bea.gov/news/blog/2025-03-10/need-info-regional-impacts-rims-ii-you) (HIGH confidence)

---

### C-4: Tribes Spanning Multiple States and Congressional Districts

**What goes wrong:** The system assumes a simple 1:1 mapping of Tribe-to-congressional-district. In reality, many Tribes have lands in multiple congressional districts, and some span multiple states. The Navajo Nation has lands in 4 congressional districts across 3 states (Arizona, New Mexico, Utah). Other large reservations (Pine Ridge, Flathead, Yakama) also cross district boundaries. A CRS report (R48107, September 2024) documents this systematically.

Additionally, Alaska has 229 federally recognized Tribes in a single at-large congressional district. The Census Bureau does not delimit Alaska Native Village boundaries -- it uses statistical areas (ANVSAs) instead. This means geographic intersection with TIGER shapefiles will not work for Alaska Tribes.

**Why it happens:** Congressional districts are drawn by state legislatures without regard for Tribal boundaries. Tribal lands follow treaty boundaries, executive orders, and trust acquisitions that predate modern district maps. Alaska's at-large structure and ANCSA's unique land framework create a category of Tribes that cannot be geographically mapped to sub-state districts.

**Consequences:**
- Advocacy packets for multi-district Tribes that only list one representative will be incomplete and potentially insulting ("you forgot my district")
- Packets that duplicate the full Tribe's award data in each district's section will overcount
- Alaska Native Villages with no geographic boundary data will have empty hazard profiles and no district mapping

**Prevention:**
1. Model the Tribe-to-district relationship as many-to-many from day one. A Tribe can have multiple district mappings, each with an area proportion if geographic data allows.
2. Use the CRS Table A-3 from R48107 as the authoritative Tribe-to-district mapping rather than computing it from scratch. This table lists every federally recognized Tribe with its state(s) and congressional district(s).
3. For Alaska: all 229 Tribes map to the at-large district (AK-AL) with both senators. Do not attempt geographic intersection for Alaska Tribes.
4. For multi-district Tribes: list ALL relevant representatives in the packet. Do not attempt to apportion award amounts across districts -- show the full Tribe-level total in each district's context.
5. Design the data model with `List[DistrictMapping]` per Tribe, not a single `district` field.

**Warning signs:** Data model has a `congressional_district: str` field on the Tribe model (should be a list). Test Tribe count for Alaska is not 229.

**Detection:** Validate that the Navajo Nation maps to at least 3 states and 4 districts in the test suite. Validate that Alaska Tribe count matches BIA list.

**Severity:** BLOCKS SHIPMENT for multi-district Tribes (their packets would be incomplete). DEGRADES QUALITY for Alaska Tribes.

**Phase:** Must be addressed in the Tribal Registry and Congressional Mapping phases. The data model decision cascades through everything downstream.

**Sources:**
- [CRS R48107: Selected Tribal Lands in 118th Congressional Districts](https://www.congress.gov/crs-product/R48107) (HIGH confidence)
- [Census TIGER 2025 Technical Documentation](https://www2.census.gov/geo/pdfs/maps-data/data/tiger/tgrshp2025/TGRSHP2025_TechDoc.pdf) (HIGH confidence)

---

### C-5: API Rate Limits and Throttling at Scale (574 Tribes x Multiple APIs)

**What goes wrong:** Batch generation for 574 Tribes requires thousands of API calls across multiple federal APIs. Without proper rate limiting, the system gets throttled (429), temporarily banned, or produces incomplete data with silent gaps.

Scale math:
- **USASpending:** 574 Tribes x 12 CFDA numbers = 6,888 queries (current scraper does 12 queries total)
- **FEMA NRI:** Downloadable as CSV -- not an API concern if pre-cached
- **Congress.gov:** 574 Tribes x 1 member lookup each (but Tribes in multiple districts multiply this). Rate limit: 5,000 requests/hour.
- **EPA EJScreen/PEDP:** Unknown rate limits on volunteer infrastructure
- **Total:** Potentially 10,000+ API calls per batch run

**Why it happens:** The existing v1.0 scraper architecture was designed for a single daily scan of ~50 queries total across 4 APIs. Scaling to per-Tribe data collection is a 100x increase in API volume that the current `asyncio.sleep(0.3)` rate limiting does not account for.

**Consequences:**
- USASpending API starts returning 429s, causing incomplete award data for Tribes processed later in the batch
- Congress.gov hits its 5,000/hour rate limit mid-batch, stopping member lookups
- PEDP volunteer infrastructure gets overwhelmed by automated bulk queries, potentially getting the project's IP banned
- Batch run that should take 20 minutes takes 4+ hours due to exponential backoff retries

**Prevention:**
1. **Pre-cache static data:** Download FEMA NRI county CSV, CRS district mapping, and Congress.gov member lists as local data files. These change infrequently (NRI: annually, districts: every 2-10 years, members: every 2 years). Do not query APIs per-Tribe for data that is the same across Tribes.
2. **Batch USASpending queries intelligently:** Instead of querying per-Tribe-per-CFDA, query per-CFDA with `recipient_type_names: ["tribal"]` filter to get ALL Tribal awards in one call per program. Then match locally. This reduces 6,888 calls to ~12 calls.
3. **Implement adaptive rate limiting:** Replace the fixed `asyncio.sleep(0.3)` with a rate limiter that respects `Retry-After` headers and backs off dynamically. The existing `BaseScraper._request_with_retry` already handles 429s, but the caller loop needs a semaphore-based rate limiter.
4. **Congress.gov:** Fetch the full member list for the current Congress once (`/member/congress/119`), cache it, and do local lookups per district. One API call instead of 574+.
5. **Add progress reporting:** 574 Tribes x multiple data sources = long-running operation. Users need a progress bar or logging to know the batch is working, not hung.

**Warning signs:** Batch run logs showing multiple 429 responses. Inconsistent award counts between ad-hoc (single Tribe) and batch (all Tribes) runs for the same Tribe. Batch runtime exceeding 30 minutes.

**Detection:** Integration test that counts API calls during a batch run and asserts the count is below a threshold (e.g., <100 total external calls).

**Severity:** BLOCKS SHIPMENT if batch generation cannot complete reliably.

**Phase:** Must be addressed in the data pipeline architecture phase, before per-Tribe data collection is implemented.

**Sources:**
- [Congress.gov API rate limit: 5,000/hour](https://github.com/LibraryOfCongress/api.congress.gov) (HIGH confidence)
- [USASpending API search filters](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/search_filters.md) (HIGH confidence)
- [OpenFEMA API docs](https://www.fema.gov/about/openfema/api) (HIGH confidence)

---

## Moderate Pitfalls

Mistakes that cause delays, technical debt, or subtle data quality issues. These degrade the product but do not necessarily block release.

---

### M-1: python-docx Memory Consumption at Scale (574 Documents)

**What goes wrong:** Generating 574 DOCX documents in a single batch run consumes excessive memory. python-docx is known to use significantly more memory than the output file size suggests (a 3MB DOCX can consume 1.5GB in memory). Creating large tables (each Tribe doc has 16 program Hot Sheets with tables) exacerbates this. Memory is not reliably released between document creations due to reference cycles in the lxml-backed XML tree.

**Why it happens:** python-docx builds the entire document XML tree in memory. Large tables with many cells create deep nested element trees. Python's garbage collector does not always collect lxml element trees promptly due to C-extension reference cycles. If 574 documents are created in a tight loop without explicit cleanup, memory grows monotonically.

**Prevention:**
1. Create each document in a separate function scope. After `document.save()`, explicitly `del document` and call `gc.collect()` to free the XML tree.
2. Process Tribes in configurable batches (e.g., 50 at a time) with explicit GC between batches.
3. Monitor memory usage during batch runs. Add a memory high-water-mark log entry per batch.
4. Keep per-document table sizes reasonable. If a program has no awards for a Tribe, show a compact "No awards in current FY" line instead of an empty table structure.
5. Test with the full 574-Tribe batch on CI to catch memory issues before production.

**Warning signs:** Batch run memory usage exceeding 2GB. Later documents in the batch taking progressively longer to generate. OOM kills in GitHub Actions.

**Detection:** Profile memory usage during a 574-Tribe batch run. GitHub Actions runners have limited memory (7GB for standard runners).

**Severity:** DEGRADES QUALITY (batch may fail or require manual intervention).

**Phase:** DOCX generation engine phase. Should be tested with full batch before declaring phase complete.

**Sources:**
- [python-docx memory leak issue #1364](https://github.com/python-openxml/python-docx/issues/1364) (HIGH confidence)
- [python-docx large table performance issue #174](https://github.com/python-openxml/python-docx/issues/174) (HIGH confidence)
- [python-docx slow creation issue #158](https://github.com/python-openxml/python-docx/issues/158) (HIGH confidence)

---

### M-2: Font Rendering Differences Between Windows Development and Linux CI/Deployment

**What goes wrong:** Documents generated on Windows (development) look different from documents generated on Linux (GitHub Actions). Fonts like Calibri, Cambria, and Arial are proprietary Microsoft fonts not available on Linux by default. LibreOffice (if used for PDF conversion) substitutes different fonts, changing layout, line breaks, page counts, and table column widths.

**Why it happens:** python-docx embeds font names in the DOCX XML but does NOT embed the font files themselves. The rendering application (Word, LibreOffice) must have the named fonts installed. Windows has Microsoft fonts; Linux does not. Even installing `ttf-mscorefonts-installer` on Linux only provides a subset of older Microsoft fonts (Arial, Times New Roman) but not Calibri or Cambria (introduced with Office 2007).

**Consequences:**
- Documents generated in CI look different from those generated locally
- If the project ever needs PDF output (common for print-ready advocacy docs), Linux-generated PDFs will have wrong fonts
- Table column widths calculated based on font metrics may shift, breaking carefully designed layouts

**Prevention:**
1. Use only fonts guaranteed available cross-platform, or use fonts that are visually identical cross-platform. Liberation Sans (Linux) is metrically compatible with Arial. Liberation Serif is compatible with Times New Roman.
2. Specify all font properties explicitly in code (font name, size, bold/italic) at the Run level. Do not rely on document-level style defaults, which may resolve differently.
3. Test document generation on both Windows and Linux. Compare page counts and visual layout.
4. If Calibri/Cambria are required for brand consistency with existing congressional materials, install `microsoft-fonts` in the GitHub Actions workflow, or switch to a font that is already available on both platforms.
5. Pin python-docx version to avoid XML serialization changes between versions.

**Warning signs:** Locally generated documents look correct but CI-generated documents have wrong fonts or shifted layouts. Page counts differ between environments.

**Detection:** Add a CI step that generates a sample document and checks page count matches expected value.

**Severity:** DEGRADES QUALITY (documents look unprofessional with wrong fonts).

**Phase:** DOCX generation engine phase.

---

### M-3: Congressional Data Staleness -- Redistricting, Resignations, and Committee Changes

**What goes wrong:** The system caches congressional district boundaries and member assignments, but these change:
- **Redistricting:** 5 states redrew boundaries for the 2024 elections (Alabama, Georgia, Louisiana, New York, North Carolina). More will change after the 2030 census.
- **Member turnover:** Deaths, resignations, and special elections change who represents a district mid-Congress.
- **Committee assignments:** Change at the start of each Congress and sometimes mid-session.

If the system uses stale data, advocacy packets will name the wrong representative or wrong committee chair.

**Why it happens:** Congressional data has multiple temporal dimensions (redistricting cycle, election cycle, committee assignment cycle) that do not align. Caching "the current Congress" as static data assumes stability within a 2-year window, which is not always true.

**Prevention:**
1. Cache Congress.gov member data with an explicit `fetched_date` and display it in generated documents ("Congressional delegation as of [date]").
2. Build a refresh mechanism that re-fetches member data monthly or on-demand before a batch generation run.
3. For redistricting: use TIGER shapefiles with the year in the filename. When new redistricting occurs, updating the shapefile triggers a re-mapping of Tribe-to-district assignments.
4. Log a WARNING when member data is older than 30 days at generation time.
5. The CRS R48107 table (Tribe-to-district mapping) is updated periodically. Pin to a specific version and document when it was last checked.

**Warning signs:** Packets generated months apart show the same member data without any refresh. Users report a packet naming a representative who has since left office.

**Detection:** Automated check: compare cached member data age against a threshold before batch generation.

**Severity:** DEGRADES QUALITY (wrong representative named is embarrassing but packets are otherwise usable).

**Phase:** Congressional Mapping phase.

---

### M-4: USASpending Pagination Limits Causing Incomplete Award Data

**What goes wrong:** The existing USASpending scraper uses `"limit": 10` in its queries, returning only the top 10 awards by amount per CFDA. For per-Tribe matching, this is catastrophically insufficient. If a CFDA program has 500+ awards to Tribal recipients, and the system only fetches the top 10, most Tribes will show $0 in awards.

Additionally, the current scraper filters by fiscal year 2025-2026 hard-coded date range (`"2025-10-01"` to `"2026-09-30"`). Historical award data (previous fiscal years) is not captured, but the advocacy packets need multi-year funding history to show trends.

**Why it happens:** The v1.0 scraper was designed to get a sample of obligation activity for the daily briefing, not to be a comprehensive award database. The `limit: 10` was intentional for the original use case (top awards for the CI dashboard) but is wrong for the v1.1 use case.

**Consequences:**
- Most Tribes show $0 in awards because their specific awards were not in the top 10
- Multi-year trend data is missing entirely
- Award totals per program are understated

**Prevention:**
1. For per-Tribe award matching, use paginated queries that fetch ALL results. USASpending supports pagination via `page` parameter. Iterate until results are exhausted.
2. Alternatively, use the `recipient_type_names` filter to get all Tribal government awards in a single query per CFDA, then match locally. This is far more efficient than per-Tribe queries.
3. Expand the date range to cover multiple fiscal years (FY22-FY26) for trend data, or use separate queries per FY.
4. Consider using USASpending bulk download files instead of the API for historical data. Bulk downloads are available as CSV and do not have pagination limits.
5. Do NOT modify the existing v1.0 scraper's `limit: 10` behavior -- it is correct for its purpose. Build a separate data collection module for per-Tribe award data.

**Warning signs:** Award match rate <50% of Tribes for major programs like BIA TCR or FEMA BRIC. Per-Tribe totals that seem implausibly low.

**Detection:** Compare per-program total from paginated query against USASpending website totals. They should be within 5%.

**Severity:** DEGRADES QUALITY (packets show no data where data exists).

**Phase:** USASpending Award Matching phase. Must be designed before implementation starts.

**Sources:**
- [USASpending spending_by_award endpoint docs](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/search/spending_by_award.md) (HIGH confidence)
- [USASpending result limits community question](https://onevoicecrm.my.site.com/usaspending/s/question/0D53d00000rVe5aCAC/result-limits-for-spending-by-award-api) (MEDIUM confidence)

---

### M-5: DOCX Programmatic Construction Without Templates Creates Brittle Layouts

**What goes wrong:** Building complex document layouts entirely in code (no template DOCX file) means every formatting detail -- margins, column widths, cell padding, header/footer styles, page breaks, section breaks -- must be specified programmatically. This creates:
- Hundreds of lines of formatting code that is hard to review and maintain
- Difficulty reproducing the look of the reference DOCX documents
- No way for non-developer staff to adjust formatting without code changes
- Subtle formatting bugs that only appear on certain page breaks or table sizes

**Why it happens:** The project spec explicitly chose "programmatic DOCX, no template files" to avoid template management complexity. This is a reasonable architectural decision, but the implementation cost of pixel-perfect formatting in code is often underestimated.

**Prevention:**
1. Create a `DocxStyles` class that centralizes ALL formatting constants (colors, fonts, sizes, margins, spacing). Changes to formatting should require editing one file, not hunting through document construction code.
2. Build a visual regression test: generate a reference document, then compare future generations against it. If layout changes unexpectedly, the test fails.
3. Invest time in studying the reference DOCX documents (`FY26_TCR_Program_Priorities.docx`, `FY26_Federal_Funding_Strategy.docx`) to catalog every formatting detail before writing code.
4. Build the document structure iteratively: start with plain text content, add basic formatting, then refine. Do not try to match the reference document perfectly in the first pass.
5. Consider a hybrid approach: create a minimal template DOCX with styles defined, then populate it programmatically. python-docx can open an existing DOCX and add content to it. This gives you template-defined styles with programmatic content.

**Warning signs:** DOCX generation code exceeds 500 lines of pure formatting logic. Formatting bugs that require changes in multiple places to fix.

**Detection:** Side-by-side visual comparison of generated document against reference document during code review.

**Severity:** DEGRADES QUALITY (documents look unprofessional) and SLOWS DEVELOPMENT (formatting is time-consuming to debug).

**Phase:** DOCX Generation Engine phase.

---

### M-6: Change Tracking Between Packet Generations Is Harder Than It Looks

**What goes wrong:** The project requires tracking "what shifted between packet generations" for 574 Tribes. This sounds simple but involves comparing complex nested data structures across time:
- Award amounts changed (new awards appeared, amounts modified)
- Hazard profiles changed (NRI data updated)
- Congressional delegation changed (new representative after special election)
- Program CI status changed (from STABLE to AT_RISK)
- District boundaries changed (redistricting)

Naive approaches (diff the JSON, diff the DOCX) either produce too much noise or miss semantically important changes.

**Why it happens:** The existing `ChangeDetector` is designed for scan-to-scan change detection on a flat list of scored items. Per-Tribe change tracking requires comparing structured, multi-dimensional Tribe snapshots across time, which is a fundamentally different problem.

**Prevention:**
1. Define a `TribeSnapshot` data structure that captures all per-Tribe data at generation time. Store snapshots as JSON alongside generated DOCX files.
2. Implement typed change detection: `AwardChange`, `DelegationChange`, `HazardChange`, `StatusChange` -- each with its own comparison logic and significance threshold.
3. Use significance thresholds: a $100 change in a $5M award is not worth reporting. A new representative IS worth reporting.
4. Store snapshots with generation timestamps. The "since last packet" diff compares the current snapshot against the most recent prior snapshot for that Tribe.
5. Keep change history bounded (e.g., last 5 generations) to prevent unbounded storage growth. Follow the existing CI history 90-entry cap pattern from v1.0.

**Warning signs:** Change tracking produces hundreds of "changes" per Tribe that are mostly noise (rounding differences, timestamp updates). Change detection code duplicates logic from the existing `ChangeDetector` instead of extending it.

**Detection:** Review change tracking output for a sample Tribe and verify that flagged changes are actually meaningful.

**Severity:** DEGRADES QUALITY (noisy change reports are ignored; meaningful changes are missed).

**Phase:** Change Tracking phase (should be one of the later phases, after data pipelines are stable).

---

## Minor Pitfalls

Mistakes that cause annoyance, rework, or minor issues but are straightforward to fix.

---

### m-1: FEMA NRI County-Level Data Does Not Map Directly to Tribal Lands

**What goes wrong:** FEMA NRI provides hazard scores at the county level and census tract level. Tribal reservations do not align with county boundaries. A Tribe's reservation may span parts of multiple counties, or a county may contain multiple reservations. Assigning a single county's NRI score to a Tribe is an approximation that may be misleading.

**Prevention:**
1. Use census tract-level NRI data where possible (finer granularity than county).
2. For Tribes spanning multiple counties, aggregate NRI scores across relevant counties using area-weighted averaging or worst-case (maximum hazard score).
3. Document the methodology clearly in the generated packet: "Hazard data based on FEMA NRI county-level scores for [County Name(s)]."
4. Do not imply that the hazard score is specific to the reservation -- it represents the broader geographic area.

**Severity:** MINOR DATA QUALITY (approximation, not error).

**Phase:** Hazard Profiling phase.

---

### m-2: Existing Pipeline Integration -- New Modules Must Not Break Daily Scans

**What goes wrong:** Adding new modules (Tribal registry, DOCX generator, hazard profiler) to the existing codebase introduces import errors, configuration conflicts, or runtime failures that break the daily scan pipeline that is already running in production via GitHub Actions.

**Prevention:**
1. New v1.1 modules should be in separate packages (e.g., `src/tribes/`, `src/packets/`) that are NOT imported by the existing `src/main.py` pipeline unless explicitly invoked via new CLI arguments.
2. Add new CLI commands (e.g., `--generate-packets`, `--single-tribe`) rather than modifying the existing `--source` or `--report-only` flags.
3. New data files (Tribal registry, NRI cache, etc.) should go in `data/tribes/` not in the existing `data/` directory root.
4. Run the existing test suite (`pytest`) after every phase to verify no regressions.
5. New dependencies (python-docx, rapidfuzz, geopandas) should be in a separate `requirements-packets.txt` or optional dependency group to keep the core scanner lightweight.

**Warning signs:** Existing GitHub Actions workflow fails after a v1.1 commit. Import errors in `src/main.py` referencing new modules.

**Detection:** CI pipeline green/red status. Add a "smoke test" that runs `python -m src.main --dry-run` as part of CI.

**Severity:** MINOR (easily fixable but disruptive if it breaks production scans).

**Phase:** Every phase must verify this. Should be a gate in each phase's verification checklist.

---

### m-3: Windows/Linux Path Handling in DOCX File I/O

**What goes wrong:** Development happens on Windows (`F:\tcr-policy-scanner`), deployment on Linux (GitHub Actions at `/root/...`). Path handling differences cause:
- Backslash paths in DOCX file references break on Linux
- `Path.write_text()` without `encoding="utf-8"` produces locale-dependent encoding on Windows
- Temporary file paths during DOCX generation may use OS-specific temp directories

**Prevention:**
1. Use `pathlib.Path` consistently (the existing codebase already does this well).
2. Always pass `encoding="utf-8"` to all file operations (the existing codebase already follows this pattern -- maintain it).
3. Use `os.sep`-agnostic path construction. Never hard-code backslashes or forward slashes.
4. For DOCX output paths, use a configurable output directory rather than hard-coded paths.
5. Test document generation on both platforms in CI.

**Warning signs:** Tests pass on Windows but fail on Linux, or vice versa. File not found errors in CI that do not reproduce locally.

**Detection:** CI runs on Linux; local runs on Windows. Divergent results flag path issues.

**Severity:** MINOR (well-understood fix patterns exist in the codebase).

**Phase:** All phases.

---

### m-4: Tribal Names Containing Special Characters in DOCX Filenames

**What goes wrong:** Some Tribal names contain characters that are invalid in filenames on one or both platforms:
- Apostrophes: "Ho-Chunk Nation" (hyphen is fine, but some names have apostrophes)
- Long names: "Confederated Tribes of the Chehalis Reservation" (47 chars -- fine, but combined with prefix/suffix could exceed limits)
- Accented characters: Not currently in the BIA list, but future additions could include them
- Forward slashes: Some historical Tribal name references use "/" which is invalid on both platforms

**Prevention:**
1. Sanitize Tribal names for filenames using a consistent function: replace special characters, truncate to a maximum length, add a unique suffix (Tribe ID or hash) to prevent collisions.
2. Use a predictable naming convention: `FY26_{tribe_id}_{sanitized_name}.docx`
3. Keep the full Tribal name inside the document content and metadata, not in the filename.
4. Test filename generation against all 574 Tribal names before the DOCX generation phase.

**Warning signs:** File creation errors on Windows for specific Tribes. Filename collisions when names are truncated.

**Detection:** Unit test that generates filenames for all 574 Tribes and asserts no duplicates and no invalid characters.

**Severity:** MINOR (easy to fix once identified).

**Phase:** DOCX Generation Engine phase.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Severity | Mitigation |
|-------------|---------------|----------|------------|
| Tribal Registry | C-4: Multi-state/multi-district Tribes + Alaska | CRITICAL | Many-to-many data model, CRS R48107 table, Alaska special case |
| USASpending Award Matching | C-1: Name matching false positives | CRITICAL | UEI-first matching, curated alias table, high fuzzy threshold |
| USASpending Award Matching | M-4: Pagination limits (limit:10) | MODERATE | Paginate fully or use recipient_type_names bulk filter |
| Hazard Profiling | C-2: EJScreen unavailable | CRITICAL | PEDP alternative, local data cache, source abstraction |
| Hazard Profiling | m-1: NRI county != tribal boundary | MINOR | Multi-county aggregation, clear methodology labeling |
| Economic Impact | C-3: RIMS II is paid, not API-accessible | CRITICAL | FEMA 4:1 BCR as primary, published multiplier ranges |
| Congressional Mapping | M-3: Data staleness (redistricting, turnover) | MODERATE | Refresh mechanism, fetched_date display, monthly cache refresh |
| DOCX Generation | M-1: Memory at scale | MODERATE | Per-document GC, batch processing, memory monitoring |
| DOCX Generation | M-2: Cross-platform font differences | MODERATE | Liberation fonts, explicit font specification, CI visual test |
| DOCX Generation | M-5: Brittle programmatic layouts | MODERATE | Centralized style constants, reference doc analysis first |
| DOCX Generation | m-4: Special characters in filenames | MINOR | Filename sanitization function, tribe_id in filename |
| Change Tracking | M-6: Semantic diff complexity | MODERATE | Typed change detection, significance thresholds, bounded history |
| Data Pipeline (all) | C-5: API rate limits at 574x scale | CRITICAL | Pre-cache static data, batch queries, adaptive rate limiting |
| Integration | m-2: Breaking existing daily scans | MINOR | Separate packages, new CLI commands, regression testing |
| All phases | m-3: Windows/Linux path handling | MINOR | pathlib, encoding="utf-8", no hard-coded paths |

---

## Sources

### Verified (HIGH confidence)
- [USASpending API endpoint documentation](https://api.usaspending.gov/docs/endpoints)
- [USASpending search filters](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/search_filters.md)
- [USASpending recipient endpoint](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/recipient.md)
- [Congress.gov API GitHub](https://github.com/LibraryOfCongress/api.congress.gov) -- 5,000 requests/hour rate limit
- [FEMA NRI data resources](https://hazards.fema.gov/nri/data-resources) -- CSV downloads, county + tract level
- [OpenFEMA API documentation](https://www.fema.gov/about/openfema/api) -- no key required, 10k record limit per page
- [BEA RIMS II ordering system](https://apps.bea.gov/regional/rims/rimsii/) -- $500/region, not free API
- [Census TIGER 2025 shapefiles](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html)
- [CRS R48107: Tribal Lands in Congressional Districts](https://www.congress.gov/crs-product/R48107)
- [BIA Federal Register Tribal entities list](https://www.federalregister.gov/documents/2024/01/08/2024-00109/indian-entities-recognized-by-and-eligible-to-receive-services-from-the-united-states-bureau-of)
- [python-docx memory issues](https://github.com/python-openxml/python-docx/issues/1364)
- [python-docx large table performance](https://github.com/python-openxml/python-docx/issues/174)
- [RapidFuzz documentation](https://rapidfuzz.github.io/RapidFuzz/)

### Partially verified (MEDIUM confidence)
- [EPA EJScreen removal](https://envirodatagov.org/epa-removes-ejscreen-from-its-website/)
- [PEDP EJScreen reconstruction](https://screening-tools.com)
- [Cross-platform font issues](https://ask.libreoffice.org/t/cross-platform-font-incompatibility-across-windows-mac-and-linux/46122)
- [USASpending data quality concerns (CRS R44027)](https://www.congress.gov/crs-product/R44027)

### Training data only (LOW confidence -- needs validation)
- Alaska Native Village boundary limitations (based on Census Bureau documentation patterns)
- python-docx XML tree garbage collection behavior (based on known lxml patterns)
- Specific Tribal name matching examples (based on domain knowledge of BIA naming conventions)
