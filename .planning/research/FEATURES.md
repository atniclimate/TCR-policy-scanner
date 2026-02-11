# Feature Landscape: v1.2 Tech Debt Cleanup

**Domain:** Tech debt remediation for TCR Policy Scanner
**Researched:** 2026-02-11
**Confidence:** HIGH (all items verified against source code)

---

## Overview

17 documented tech debt items across 5 categories: testing gaps, hardcoded values, code quality, data population, and documentation. Each item below includes what "done" looks like at minimum (table stakes), what a thorough fix looks like (gold standard), and what NOT to do (anti-patterns).

---

## Category 1: Testing Gaps (2 items)

### TD-01: No Live Scraper Integration Tests

**Source:** v1.0 audit, Phase 01
**Severity:** MEDIUM
**Current state:** 4 scrapers (Federal Register, Grants.gov, Congress.gov, USASpending) validated via manual runs only. 287 unit/integration tests exist but none hit live APIs.

**Table stakes (minimum fix):**
- Create `tests/test_scrapers_live.py` with `@pytest.mark.live` marker
- One test per scraper that verifies: connection succeeds, response parses, at least 1 item returned
- `pytest.ini` or `conftest.py` excludes `live` marker by default (so CI does not fail on API rate limits)
- Tests skip gracefully when API key missing (Congress.gov) or network unavailable
- Each test has a 30-second timeout

**Gold standard:**
- Parametrized tests covering all 4 scrapers with shared fixtures
- Response schema validation (verify returned dicts have expected keys: `source_id`, `title`, `source`, `published_date`)
- CI workflow with manual dispatch (`workflow_dispatch`) for on-demand live testing
- Smoke test mode: fetches 1 page per scraper (not full scan window)
- Record/replay with `vcrpy` or `aioresponses` for deterministic CI runs alongside the live marker tests

**Anti-patterns:**
- Do NOT make live tests run in default `pytest` invocation -- they will break CI on every run
- Do NOT hardcode API keys in test files
- Do NOT assert exact item counts (API results vary daily)
- Do NOT test full scan window (slow, rate-limited) -- limit to 1 page or minimal query

**Dependencies:** None. Can be done independently.

---

### TD-14: CONGRESS_API_KEY Optional (Graceful Degradation)

**Source:** v1.0 audit, Phase 01
**Severity:** LOW
**Current state:** `CongressGovScraper.scan()` (line 53-55) already returns `[]` when key is missing and logs a warning. The "tech debt" is that this is undocumented behavior -- users see a warning but no guidance.

**Table stakes (minimum fix):**
- Add a note in README.md under a "Configuration" section explaining that `CONGRESS_API_KEY` is optional
- Document what is lost without it (no legislative bill tracking from Congress.gov)
- Add `--dry-run` output that shows "needs API key" status for congress_gov (already partially exists at line 88 of main.py)

**Gold standard:**
- Add a startup summary that reports which scrapers are active/skipped based on available keys
- Test for graceful degradation: `test_congress_scraper_no_key` that verifies `[]` return and no exception
- Consider: if key is empty string vs not set vs invalid -- all three cases degrade gracefully

**Anti-patterns:**
- Do NOT make the key required (breaks existing behavior)
- Do NOT suppress the warning log (it is useful for operators to know Congress.gov is skipped)

**Dependencies:** None.

---

## Category 2: Hardcoded Values (3 items)

### TD-02: FY26 Dates Hardcoded in Config + DOCX Output

**Source:** v1.0 audit Phase 02 + v1.1 audit H-04
**Severity:** MEDIUM
**Current state:**
- `config/scanner_config.json` line 118: `"fy26_end": "2026-09-30"` -- used by IIJA sunset monitor
- `src/packets/docx_sections.py` line 55: `"FY26 Climate Resilience Program Priorities"` -- cover page title
- `src/packets/strategic_overview.py` lines 3, 182, 195, 227: `"FY26"` in headers and titles
- `src/graph/builder.py` lines 176, 398: `"FY26"` in urgency labels and fiscal year fields
- `data/policy_tracking.json`: `"FY26"` in policy tracking IDs and reasoning text
- `src/monitors/iija_sunset.py`: `IIJA_FY26_PROGRAMS` dict name and docstrings (these are factual -- IIJA does expire in FY26)
- `src/scrapers/usaspending.py` line 216: `"FY26 Obligation"` in title formatting

**Table stakes (minimum fix):**
- Add `"fiscal_year": "FY26"` and `"fiscal_year_end": "2026-09-30"` to the top level of `scanner_config.json`
- Modify `docx_sections.py` cover page to read fiscal year from config: `f"{fiscal_year} Climate Resilience Program Priorities"`
- Modify `strategic_overview.py` to use config-driven fiscal year in all document headings
- Modify `iija_sunset.py` to read `fy26_end` from monitor config (already does this -- line 118 of config)
- Pass fiscal year string through to any renderer that needs it (via config dict or as parameter)

**Gold standard:**
- Single source of truth: `config.fiscal_year` flows through entire pipeline
- `graph/builder.py` uses `config["fiscal_year"]` for urgency and fiscal year fields
- `usaspending.py` uses config for title formatting
- Changing the config value from `"FY26"` to `"FY27"` makes the entire system update -- documents, monitors, graph labels
- Note: `policy_tracking.json` and `program_inventory.json` contain FY26 in narrative text (ci_determination strings) -- these are authored content, not computed values. They should be updated manually when the fiscal year changes, not templated.

**Anti-patterns:**
- Do NOT template the narrative text in `program_inventory.json` (e.g., do not replace `"FY26 funded at $34.291M"` with `"{fiscal_year} funded at $34.291M"` -- this is authored policy analysis, not a computed string)
- Do NOT rename `IIJA_FY26_PROGRAMS` -- the IIJA genuinely expires in FY26; this is a factual constant, not a configurable value
- Do NOT over-abstract -- a simple string substitution in 4-5 renderer files is sufficient
- Do NOT create a FiscalYear class or date calculation library

**Dependencies:** Touches docx_sections, strategic_overview, graph builder, usaspending scraper. Low risk -- string substitutions only.

---

### TD-03: graph_schema.json Path Hardcoded

**Source:** v1.1 audit D-02
**Severity:** MEDIUM
**Current state:** The path `"data/graph_schema.json"` appears hardcoded in 4 locations:
- `src/main.py` line 104: `Path("data/graph_schema.json")` in dry_run display
- `src/graph/builder.py` line 25: `GRAPH_SCHEMA_PATH = Path("data/graph_schema.json")`
- `src/packets/orchestrator.py` line 537: `graph_path = Path("data/graph_schema.json")`
- `src/packets/strategic_overview.py` line 84: `self._load_json("data/graph_schema.json")`

**Table stakes (minimum fix):**
- Add `"graph_schema_path": "data/graph_schema.json"` to `scanner_config.json`
- Modify `graph/builder.py` to accept path from config (falling back to current default)
- Modify `orchestrator.py` `_load_structural_asks()` to read path from `self.config`
- Modify `strategic_overview.py` to read path from config
- Modify `main.py` dry_run to read path from config

**Gold standard:**
- All data file paths centralized in config under a `"data_paths"` section:
  ```json
  "data_paths": {
    "graph_schema": "data/graph_schema.json",
    "program_inventory": "data/program_inventory.json",
    "policy_tracking": "data/policy_tracking.json"
  }
  ```
- Every module reads paths from config, never hardcodes them
- Makes it possible to run with alternative data directories (useful for testing)

**Anti-patterns:**
- Do NOT create an environment variable for this -- config file is the right place
- Do NOT create a PathResolver class -- a simple config key is sufficient
- Do NOT move the actual file -- just make the path configurable

**Dependencies:** Requires config changes. Low risk but touches 4 modules.

---

### TD-12: Stale ROADMAP Header Count

**Source:** v1.0 audit, meta
**Severity:** LOW
**Current state:** v1.0 ROADMAP.md header says "31/31 requirements" but actual count is 30. This is in the archived milestone file at `.planning/milestones/v1.0-ROADMAP.md`.

**Table stakes (minimum fix):**
- Fix the header count in `v1.0-ROADMAP.md` from 31 to 30
- One-line edit

**Gold standard:**
- Same as table stakes -- this is an archived milestone file, not a living document

**Anti-patterns:**
- Do NOT add automated count validation tooling for this -- it is a one-time typo fix in an archived file

**Dependencies:** None. Standalone 1-line fix.

---

## Category 3: Code Quality (4 items)

### TD-06: Logger Naming Inconsistency (economic.py)

**Source:** v1.1 audit H-01
**Severity:** LOW
**Current state:** `src/packets/economic.py` line 15 uses `logging.getLogger(__name__)` which produces `src.packets.economic`. All other packets modules use explicit hierarchical names like `"tcr_scanner.packets.docx_hotsheet"`. The inconsistency means log filtering by `tcr_scanner.packets.*` would miss economic.py logs.

**Table stakes (minimum fix):**
- Change `economic.py` line 15 from `logging.getLogger(__name__)` to `logging.getLogger("tcr_scanner.packets.economic")`

**Gold standard:**
- Audit all logger names across the entire codebase for consistency
- The v1.0 modules (scrapers, monitors, graph, analysis, reports) use `__name__` while v1.1 modules (packets/*) use explicit `"tcr_scanner.packets.*"` names. Two conventions coexist:
  - v1.0: `__name__` pattern (produces `src.scrapers.base`, `src.monitors.iija_sunset`, etc.)
  - v1.1: explicit `"tcr_scanner.packets.*"` pattern
- Gold standard: pick one convention and apply it everywhere. Recommendation: explicit `"tcr_scanner.*"` names everywhere, because `src.*` is an implementation detail that leaks module structure into logs.
- However: changing all v1.0 loggers is a larger scope change. For v1.2, just fix economic.py to match its siblings.

**Anti-patterns:**
- Do NOT change all v1.0 logger names in this milestone (scope creep)
- Do NOT create a custom Logger factory class
- Do NOT remove the logger -- it is used for legitimate warnings

**Dependencies:** None. One-line change.

---

### TD-07: _format_dollars() Duplicated in 2 Files

**Source:** v1.1 audit L-01
**Severity:** LOW
**Current state:** Identical function `_format_dollars(amount: float) -> str` exists in:
- `src/packets/economic.py` line 386-395 (used by `EconomicImpactCalculator.format_impact_narrative`)
- `src/packets/docx_hotsheet.py` line 110-112 (used by `HotSheetRenderer._add_award_history`, `_add_economic_impact`)

Both return `f"${amount:,.0f}"`.

**Table stakes (minimum fix):**
- Remove `_format_dollars` from `docx_hotsheet.py`
- Import it from `economic.py`: `from src.packets.economic import _format_dollars`
- Or better: rename to `format_dollars` (drop underscore) since it is now a shared utility, and put it in economic.py as a public function

**Gold standard:**
- Create a small `src/packets/formatting.py` utility module with `format_dollars()` and any other shared formatting functions
- Both `economic.py` and `docx_hotsheet.py` import from `formatting.py`
- This avoids economic.py importing from docx_hotsheet.py or vice versa (keeps dependency direction clean)

**Anti-patterns:**
- Do NOT create a large `utils.py` kitchen-sink module
- Do NOT leave both copies and add a comment "see also economic.py" -- actually deduplicate
- Do NOT change the function signature or behavior -- it works fine, just consolidate it

**Dependencies:** None. Safe refactor -- no behavior change.

---

### TD-08: Incomplete Program Fields (access_type/funding_type)

**Source:** v1.1 audit M-03
**Severity:** LOW
**Current state:** All 16 programs in `program_inventory.json` actually DO have `access_type` and `funding_type` fields (verified by grep). The original tech debt note may have been about programs with `null` CFDA fields or about values that could be more specific. Let me verify:
- `epa_tribal_air` has `"cfda": null` (line 354)
- All 16 programs have non-null `access_type` and `funding_type`

The actual gap is: some `access_type` values might not be fully populated or precise. The renderers handle missing values gracefully (empty string check before display).

**Table stakes (minimum fix):**
- Audit all 16 programs and verify `access_type` and `funding_type` are accurate
- Fill in any null CFDAs where the Assistance Listing Number is known
- Document which programs intentionally have null CFDA (e.g., `epa_tribal_air` may not have a single CFDA)

**Gold standard:**
- Add CFDA numbers for all programs where they exist on SAM.gov
- Add a `"cfda_source"` field documenting where each CFDA was verified
- Validate that CFDA numbers match SAM.gov current listings

**Anti-patterns:**
- Do NOT invent CFDA numbers -- if a program does not have one, null is correct
- Do NOT add mandatory validation that rejects null CFDA -- some programs legitimately lack them
- Do NOT restructure the program_inventory.json schema -- just fill in missing data

**Dependencies:** None. Data file edit only.

---

### TD-13: No Circuit-Breaker Retry Pattern

**Source:** v1.0 audit Phase 03
**Severity:** LOW
**Current state:** `BaseScraper._request_with_retry()` in `base.py` already has:
- Exponential backoff (line 94: `BACKOFF_BASE ** attempt + random.uniform(0, 1)`)
- 3 retries (MAX_RETRIES = 3)
- 429 rate-limit handling with Retry-After header respect
- 403 retry with backoff
- Timeout handling

What is missing is a **circuit breaker** -- if a source has failed N times across multiple calls in a scan, stop trying for the rest of the scan instead of retrying every individual request.

**Table stakes (minimum fix):**
- Add a simple per-scraper failure counter to `BaseScraper`
- After N consecutive failures (e.g., 3 full retry cycles), mark the scraper as "tripped" and short-circuit remaining requests with a warning
- Reset on successful request

**Gold standard:**
- Implement a lightweight `CircuitBreaker` class with three states: CLOSED (normal), OPEN (failing, reject fast), HALF_OPEN (try one request)
- Configurable failure threshold and cooldown period
- Log state transitions at WARNING level
- Could be a simple 30-line class inside `base.py` -- no external library needed

**Anti-patterns:**
- Do NOT install a circuit-breaker library (e.g., `pybreaker`) for this -- the use case is simple enough for 30 lines of code
- Do NOT add circuit breaker config to scanner_config.json unless there is a real need to tune thresholds
- Do NOT break the existing retry logic -- circuit breaker wraps around it, not replaces it
- Do NOT add state persistence (circuit breaker state should reset each scan run)

**Dependencies:** Touches `base.py` only. All scrapers inherit from it. Low risk.

---

## Category 4: Data Population (2 items)

### TD-04: Award Cache Requires Live API Run to Populate

**Source:** v1.1 audit, Phase 06
**Severity:** MEDIUM
**Current state:** 592 award cache files exist in `data/award_cache/`, but they were seeded with empty or minimal structures during Phase 6 development. Real award data requires running `TribalAwardMatcher.run(scraper)` against the live USASpending API, which does full pagination across all CFDAs for all 592 Tribes.

**Table stakes (minimum fix):**
- Add a CLI command: `python -m src.main --populate-awards`
- This triggers `TribalAwardMatcher` to run against USASpending for all 592 Tribes
- Include progress output (N/592, elapsed time, errors)
- Document in README.md under "Data Population" section
- Handle graceful interruption (Ctrl+C saves progress so far)

**Gold standard:**
- Incremental population: `--populate-awards --since 2024-01-01` to fetch only recent awards
- Resume support: if interrupted, re-running skips Tribes with recent cache files (check modified time)
- Rate limiting: respect USASpending rate limits (no API key needed, but courtesy delays between requests)
- Cache freshness tracking: each cache file includes `"fetched_at"` timestamp
- Validation: after population, report summary (N Tribes with awards, total obligation, N empty)

**Anti-patterns:**
- Do NOT run population as part of the normal `--prep-packets` pipeline -- it should be a separate explicit step
- Do NOT require population to succeed for all 592 Tribes before allowing packet generation (partial data is useful)
- Do NOT store API responses raw -- continue using the normalized cache format
- Do NOT run all 592 in parallel (will hit rate limits) -- sequential or small batches with delays

**Dependencies:** Requires `src/packets/awards.py` (already built). CLI integration in `main.py`.

---

### TD-05: Hazard Profiles Require Manual Data Download

**Source:** v1.1 audit, Phase 06
**Severity:** MEDIUM
**Current state:** 592 hazard profile files exist in `data/hazard_profiles/`, seeded during Phase 6. Real profiles require:
1. Downloading FEMA NRI CSV (National Risk Index) from FEMA's data portal
2. Downloading USFS Wildfire Risk to Communities XLSX from USFS portal
3. Running `build_all_profiles()` to process and cache per-Tribe profiles

**Table stakes (minimum fix):**
- Add a CLI command: `python -m src.main --populate-hazards`
- Document the manual download steps clearly in README.md:
  - Step 1: Download NRI CSV from [FEMA NRI URL]
  - Step 2: Download USFS XLSX from [USFS URL]
  - Step 3: Place in `data/raw/` directory
  - Step 4: Run `--populate-hazards`
- Script processes the raw files into per-Tribe JSON profiles
- Validate output: report how many Tribes got NRI data, how many got USFS data

**Gold standard:**
- Automated download via `--populate-hazards --download` that fetches the source files directly (if their URLs are stable and public)
- Data validation: warn if NRI CSV has unexpected columns or USFS XLSX schema changed
- Staleness check: track download dates and warn if data is older than 1 year
- Incremental update: if only NRI or only USFS is available, update just that portion of each profile

**Anti-patterns:**
- Do NOT bundle the raw NRI/USFS data in the repository (too large, license concerns)
- Do NOT assume download URLs are permanent -- document the manual fallback path
- Do NOT block packet generation if hazard data is empty -- packets already handle missing hazard profiles gracefully
- Do NOT parse NRI/USFS data at document generation time -- always pre-cache

**Dependencies:** Requires `src/packets/hazards.py` (already built). CLI integration in `main.py`.

---

## Category 5: Documentation (7 items)

### TD-09: Missing Phase 8 VERIFICATION.md

**Source:** v1.1 audit, Phase 08
**Severity:** LOW
**Current state:** Phase 8 has 6 plan summaries (08-01 through 08-06) that serve as equivalent verification evidence, but no formal `08-VERIFICATION.md` file. All other phases (01-07) have verification files.

**Table stakes (minimum fix):**
- Create `.planning/phases/08-assembly-polish/08-VERIFICATION.md`
- Follow the same format as other VERIFICATION files (e.g., `07-VERIFICATION.md`)
- Reference the 6 plan summaries as evidence
- Include test counts from Phase 8 (73 tests, 8 E2E integration tests)
- Mark as retroactively verified

**Gold standard:**
- Same as table stakes -- this is a process artifact, not a code change

**Anti-patterns:**
- Do NOT re-run Phase 8 verification from scratch -- summarize existing evidence
- Do NOT add new tests just to fill this file -- the 73 existing tests are sufficient

**Dependencies:** None. Documentation only.

---

### TD-10: GitHub Pages Deployment Config Docs

**Source:** v1.1 audit, Phase 08
**Severity:** LOW
**Current state:** The GitHub Pages deployment requires:
1. Repository Settings > Pages enabled (source: `docs/web/` directory or GitHub Actions)
2. Repository Secrets: `CONGRESS_API_KEY` and `SAM_API_KEY` for the Actions workflow
3. Actions workflow file not yet in repo (`.github/workflows/` directory is empty or missing)

README.md (line 274+) has a "Web Distribution" section but lacks step-by-step deployment instructions.

**Table stakes (minimum fix):**
- Add a "Deployment" section in README.md with:
  - Step 1: Enable GitHub Pages in repository settings
  - Step 2: Add repository secrets (CONGRESS_API_KEY, SAM_API_KEY)
  - Step 3: Configure Pages source (docs/web directory)
  - Step 4: Trigger first workflow run
- Create `.github/workflows/generate-packets.yml` with the CI workflow (weekly cron + manual dispatch) described in Phase 8 plans

**Gold standard:**
- Include a `DEPLOYMENT.md` with complete deployment guide
- GitHub Actions workflow tested and committed
- Badge in README showing deployment status
- Troubleshooting section for common issues (Pages not deploying, secrets missing, workflow permissions)

**Anti-patterns:**
- Do NOT assume the user knows GitHub Actions -- provide copy-paste-ready workflow YAML
- Do NOT hardcode repository URLs in the workflow -- use `${{ github.repository }}` variable
- Do NOT require manual packet generation before Pages works -- workflow should handle it

**Dependencies:** TD-11 (SquareSpace URL) can be addressed in the same README edit.

---

### TD-11: SquareSpace Placeholder URL

**Source:** v1.1 audit, Phase 08
**Severity:** LOW
**Current state:** `docs/web/index.html` line 45 has `src="https://yourusername.github.io/tcr-policy-scanner/"` as a placeholder in the SquareSpace embed comment.

**Table stakes (minimum fix):**
- This is intentionally a placeholder -- each deployment will have a different GitHub Pages URL
- Add a note in README.md making it clear the user must replace `yourusername` with their actual GitHub username
- Optionally: add a configuration variable or comment making the required edit obvious

**Gold standard:**
- Same as table stakes plus: add a deployment script or setup guide that prompts for the GitHub username and auto-generates the correct embed code

**Anti-patterns:**
- Do NOT hardcode a specific repository URL -- it must remain a template
- Do NOT remove the placeholder -- it is useful documentation

**Dependencies:** Can be addressed in same README edit as TD-10.

---

### TD-15: Missing v1.0 Phase Summaries

**Source:** v1.0 audit, meta
**Severity:** LOW
**Current state:** v1.0 phases (01-04) DO have plan-level SUMMARY files (01-01-SUMMARY, 01-02-SUMMARY, etc.) -- they were created during execution. The audit noted that phases "executed before GSD verification workflow" -- meaning the VERIFICATION.md files were created after the fact. All 4 v1.0 phases already have VERIFICATION files. The actual gap may refer to the v1.0 milestone not having a formal `v1.0-REQUIREMENTS.md` before the audit created one.

**Table stakes (minimum fix):**
- Verify all v1.0 phase directories have VERIFICATION.md (they do: 01-, 02-, 03-, 04-)
- Verify v1.0 milestone archive is complete (v1.0-ROADMAP.md, v1.0-REQUIREMENTS.md, v1.0-MILESTONE-AUDIT.md all exist)
- If anything is missing, create it retroactively from existing evidence
- Close this item as "already addressed" if no gaps found

**Gold standard:**
- Same as table stakes

**Anti-patterns:**
- Do NOT create elaborate retroactive documentation for a shipped milestone
- Do NOT re-audit v1.0 -- just verify files exist

**Dependencies:** None.

---

### TD-16: Stale PROJECT.md Counts

**Source:** v1.0 audit, meta
**Severity:** LOW
**Current state:** PROJECT.md was last updated 2026-02-11 when v1.2 milestone started. The v1.0 audit noted stale counts: "21 authorities/14 barriers (actual 20/13), pipeline shows 5 stages (actual 6)". These were likely fixed during v1.1 but should be verified.

**Table stakes (minimum fix):**
- Verify current PROJECT.md counts match reality:
  - graph_schema.json: count authorities, barriers, funding_vehicles
  - Pipeline stages: Ingest -> Normalize -> Graph -> Monitors -> Decision Engine -> Reporting (6 stages)
  - Source files, LOC, test counts
- Fix any remaining stale numbers

**Gold standard:**
- Same as table stakes. PROJECT.md is a living document that gets updated with each milestone.

**Anti-patterns:**
- Do NOT add automated count verification -- just fix the numbers
- Do NOT restructure PROJECT.md -- just update stale counts

**Dependencies:** Should be done last (after all other items change counts).

---

### TD-17: MILESTONES.md Update

**Source:** v1.0 audit, meta (extended)
**Severity:** LOW
**Current state:** MILESTONES.md last line says "Planning next milestone." -- should be updated to reflect v1.2 is in progress.

**Table stakes (minimum fix):**
- Update MILESTONES.md v1.1 section "What's next" to reference v1.2 Tech Debt Cleanup

**Gold standard:**
- Same as table stakes. Will get a full v1.2 section when the milestone ships.

**Anti-patterns:**
- Do NOT add the v1.2 section yet -- it has not shipped

**Dependencies:** None.

---

## Feature Dependencies

```
Independent clusters (can be done in any order):

Cluster A: Code Quality (no dependencies between items)
  TD-06 (logger naming)
  TD-07 (_format_dollars dedup)
  TD-08 (program fields)
  TD-12 (ROADMAP header count)

Cluster B: Configuration (should be done together)
  TD-02 (FY26 hardcoding) --> TD-03 (graph_schema path)
  These both modify scanner_config.json and multiple renderers.
  Do TD-03 first (adds data_paths section), then TD-02 (adds fiscal_year).

Cluster C: Testing + Resilience
  TD-01 (scraper integration tests)
  TD-13 (circuit breaker) --> TD-01 benefits from circuit breaker
  TD-14 (CONGRESS_API_KEY docs)

Cluster D: Data Population (should be done together)
  TD-04 (award cache) --> TD-05 (hazard profiles)
  Both add CLI commands to main.py. Similar patterns.

Cluster E: Documentation (do last, after code changes)
  TD-09 (Phase 8 VERIFICATION.md)
  TD-10 (GitHub Pages deployment)
  TD-11 (SquareSpace URL)
  TD-15 (v1.0 phase summaries)
  TD-16 (PROJECT.md counts) -- must be last
  TD-17 (MILESTONES.md update)
```

**Recommended ordering:**
1. Cluster A first (quick wins, build momentum)
2. Cluster B second (config changes affect multiple modules)
3. Cluster C third (testing infrastructure)
4. Cluster D fourth (data population -- needs working CLI)
5. Cluster E last (documentation reflects final state)

---

## Complexity Estimates

| Item | Complexity | Files Changed | Lines Changed (est.) |
|------|-----------|---------------|---------------------|
| TD-01 | Medium | 2-3 new test files | ~150 |
| TD-02 | Medium | 5-6 source files + config | ~40 |
| TD-03 | Low-Medium | 4 source files + config | ~25 |
| TD-04 | Medium | 1-2 source files (main.py, awards.py) | ~80 |
| TD-05 | Medium | 1-2 source files (main.py, hazards.py) | ~80 |
| TD-06 | Trivial | 1 file | 1 |
| TD-07 | Low | 2-3 files | ~15 |
| TD-08 | Low | 1 data file | ~10 |
| TD-09 | Low | 1 new file | ~30 |
| TD-10 | Low-Medium | 1-2 files (README + workflow YAML) | ~80 |
| TD-11 | Trivial | 1 file (README) | ~5 |
| TD-12 | Trivial | 1 file | 1 |
| TD-13 | Low-Medium | 1 file (base.py) | ~40 |
| TD-14 | Low | 1-2 files | ~15 |
| TD-15 | Trivial | 0-1 files | ~0-20 |
| TD-16 | Trivial | 1 file | ~10 |
| TD-17 | Trivial | 1 file | ~3 |

**Total estimated:** ~585 lines changed across ~20 files

---

## MVP Recommendation

**Must-have for v1.2 (all 17 items):**
All items are scoped as tech debt cleanup. The whole point of this milestone is to close all 17. None should be deferred.

**If time-constrained, prioritize MEDIUM items first:**
1. TD-02 (FY26 hardcoding) -- prevents the system from going stale when FY27 arrives
2. TD-03 (graph_schema path) -- config hygiene
3. TD-04 (award cache population) -- enables real data in packets
4. TD-05 (hazard profile population) -- enables real data in packets
5. TD-01 (scraper integration tests) -- testing confidence
6. TD-13 (circuit breaker) -- resilience

**LOW items are quick wins (do in bulk):**
TD-06, TD-07, TD-08, TD-09, TD-10, TD-11, TD-12, TD-14, TD-15, TD-16, TD-17

---

## Sources

All findings verified directly against source code at `F:\tcr-policy-scanner`:
- `src/scrapers/base.py` -- retry logic, circuit breaker gap
- `src/packets/economic.py` -- logger naming, _format_dollars
- `src/packets/docx_hotsheet.py` -- _format_dollars duplicate
- `src/packets/docx_sections.py` -- FY26 hardcoding
- `src/packets/orchestrator.py` -- graph_schema path
- `src/packets/strategic_overview.py` -- FY26 hardcoding, graph_schema path
- `src/graph/builder.py` -- FY26 hardcoding, graph_schema path
- `src/main.py` -- graph_schema path, CLI entry point
- `src/scrapers/congress_gov.py` -- CONGRESS_API_KEY handling
- `config/scanner_config.json` -- FY26 date, monitor config
- `data/program_inventory.json` -- access_type/funding_type fields
- `docs/web/index.html` -- SquareSpace placeholder
- `.planning/milestones/v1.0-MILESTONE-AUDIT.md` -- original tech debt list
- `.planning/milestones/v1.1-MILESTONE-AUDIT.md` -- updated tech debt list
- `.planning/PROJECT.md` -- stale counts
- `.planning/MILESTONES.md` -- milestone tracking
