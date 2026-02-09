# Phase 1: Pipeline Validation - Research

**Researched:** 2026-02-09
**Domain:** Python async pipeline validation against 4 live federal APIs
**Confidence:** HIGH (direct codebase analysis + API documentation verification)

## Summary

This research investigated the existing TCR Policy Scanner pipeline to determine what needs to be validated (and potentially fixed) before the pipeline can reliably run end-to-end against live federal APIs. The codebase is a brownfield Python 3.12 async project with 4 scrapers, a 5-factor relevance scorer, a knowledge graph builder, a change detector, and a report generator.

The most critical finding is a **Grants.gov API endpoint mismatch**: the scraper uses `{base_url}/opportunities/search` but the current Grants.gov REST API exposes `/v1/api/search2` with different parameter names (`aln` instead of `assistanceListing`, `keyword` instead of separate field names). This will cause the Grants.gov scraper to fail against the live API. The Congress.gov API may also have issues -- the scraper passes a `query` parameter to the `/bill/{congress}/{billType}` endpoint, but API documentation only lists `fromDateTime`, `toDateTime`, `offset`, `limit`, and `format` as valid parameters. The `query` parameter may be silently ignored, returning all bills instead of filtered results.

The Federal Register API and USASpending API endpoints appear correctly configured based on documentation review.

**Primary recommendation:** Run each scraper individually against its live API (`python -m src.main --source {name}`) to identify which endpoints fail, then fix endpoint URLs and parameter names before attempting full pipeline validation.

## Standard Stack

The established libraries/tools already in the project:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| aiohttp | >=3.9.0 | Async HTTP client for all 4 scrapers | Standard Python async HTTP; already in use |
| python-dateutil | >=2.8.0 | Date parsing in relevance scorer | Robust date parsing; handles varied API date formats |
| jinja2 | >=3.1.0 | Template engine (listed in requirements) | Standard Python templating; already imported |

### Supporting (validation-specific)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | latest | Test harness for validation scripts | If writing automated validation checks |
| pytest-asyncio | latest | Async test support | If testing scrapers in isolation |

### Not Needed
| Instead of | Don't Add | Reason |
|------------|-----------|--------|
| aiohttp-retry | Custom retry in BaseScraper | BaseScraper already implements exponential backoff with 403/429 handling |
| httpx | aiohttp | Already committed to aiohttp; no reason to switch |
| requests | aiohttp | Pipeline is fully async; synchronous requests would break pattern |

**Installation (existing):**
```bash
pip install -r requirements.txt
# Installs: aiohttp>=3.9.0, python-dateutil>=2.8.0, jinja2>=3.1.0
```

## Architecture Patterns

### Existing Project Structure (confirmed from codebase)
```
src/
  main.py              # CLI entry point + pipeline orchestrator
  scrapers/
    base.py             # BaseScraper with retry, User-Agent, zombie CFDA
    federal_register.py # Federal Register API (no key)
    grants_gov.py       # Grants.gov API (no key) -- ENDPOINT MISMATCH
    congress_gov.py     # Congress.gov API (requires CONGRESS_API_KEY)
    usaspending.py      # USASpending API (no key)
  analysis/
    relevance.py        # 5-factor weighted scorer
    change_detector.py  # Scan-to-scan diff (JSON file-based)
  graph/
    schema.py           # Dataclass node/edge definitions
    builder.py          # Static seed + dynamic enrichment
  reports/
    generator.py        # Markdown + JSON report output
config/
  scanner_config.json   # Sources, scoring weights, keywords
data/
  program_inventory.json  # 16 programs with CI scores
  policy_tracking.json    # FY26 positions with 6-tier CI
  graph_schema.json       # Authorities, barriers, structural asks
outputs/
  LATEST-BRIEFING.md    # Generated (does not exist yet)
  LATEST-RESULTS.json   # Generated (does not exist yet)
  LATEST-GRAPH.json     # Generated (does not exist yet)
  archive/              # Timestamped copies
.github/workflows/
  daily-scan.yml        # GitHub Actions: weekday 6 AM Pacific
```

### Pattern 1: Sequential Scraper Execution with Graceful Failure
**What:** Each scraper runs in sequence within `run_scan()`. If one fails, the exception is caught and logged, and the pipeline continues with the remaining scrapers.
**When to use:** This is the existing pattern. Validation must confirm it works.
**Example:**
```python
# Source: src/main.py lines 112-128
async def run_scan(config, programs, sources):
    all_items = []
    for source_name in sources:
        scraper_cls = SCRAPERS[source_name]
        scraper = scraper_cls(config)
        try:
            items = await scraper.scan()
            all_items.extend(items)
        except Exception:
            logger.exception("Failed to scan %s", source_name)
    return all_items
```

### Pattern 2: Change Detection via JSON File Diff
**What:** The ChangeDetector saves scored results to `outputs/LATEST-RESULTS.json` and compares against previous scan on next run. Items are keyed by `source:source_id`.
**When to use:** Validation of PIPE-04 requires two consecutive runs.
**Example:**
```python
# Source: src/analysis/change_detector.py
# Key generation for deduplication:
def _item_key(item): return f"{item.get('source', '')}:{item.get('source_id', '')}"
```

### Pattern 3: CLI Invocation Modes
**What:** `src/main.py` supports multiple modes via argparse.
**Modes available:**
- `python -m src.main` -- full scan (all 4 sources)
- `python -m src.main --source federal_register` -- single source
- `python -m src.main --dry-run` -- show config without API calls
- `python -m src.main --report-only` -- regenerate from cache
- `python -m src.main --graph-only` -- export graph from cache
- `python -m src.main --verbose` -- debug logging

### Anti-Patterns to Avoid
- **Do NOT run all 4 scrapers at once for initial validation:** Test each individually with `--source` first. A single broken scraper can mask other issues.
- **Do NOT skip the `--dry-run` step:** It validates config loading and CFDA mappings without making API calls.
- **Do NOT test change detection without a baseline:** The first scan has no previous results, so all items appear as "new." The second scan is needed to test actual change detection.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP retry with backoff | Custom retry loop | `BaseScraper._request_with_retry()` | Already handles 403, 429, 5xx, timeouts with configurable backoff |
| Item deduplication | Custom dedup logic | `seen_urls`/`seen_ids` sets in each scraper | Already implemented per-source; also `ChangeDetector._item_key()` for cross-source |
| API response validation | Schema validators | `_normalize()` methods on each scraper | Already map API-specific fields to standard schema with safe `.get()` defaults |
| Date parsing | `datetime.strptime()` | `dateutil.parser.parse()` | Already used in `RelevanceScorer._recency()`; handles varied date formats from APIs |
| Output archival | Manual copy scripts | `ReportGenerator.generate()` | Already archives to `outputs/archive/` with timestamps |

**Key insight:** The existing codebase has robust infrastructure for scraping, scoring, and reporting. The validation phase should NOT add new infrastructure -- it should verify the existing infrastructure works against live APIs and fix any endpoint mismatches.

## Common Pitfalls

### Pitfall 1: Grants.gov Endpoint Mismatch (CRITICAL)
**What goes wrong:** The `GrantsGovScraper` constructs URLs using `{base_url}/opportunities/search` (line 115-116 of grants_gov.py), but the current Grants.gov REST API endpoint is `/v1/api/search2`.
**Why it happens:** The Grants.gov API was modernized (announced March 2025). The new `search2` endpoint uses different parameter names:
- `aln` instead of `assistanceListing`
- `keyword` instead of separate field names
- Response structure uses `oppHits` (which the code already expects)
**How to avoid:** Update `_search_cfda()` and `_search()` methods to use the correct endpoint URL and parameter names. The `base_url` in config is `https://api.grants.gov/v1` -- the endpoint path needs to change from `/opportunities/search` to `/api/search2`.
**Warning signs:** HTTP 404 or unexpected JSON structure when running `--source grants_gov`.
**Confidence:** HIGH -- verified against official Grants.gov API documentation at grants.gov/api/api-guide and grants.gov/api/common/search2.

### Pitfall 2: Congress.gov Query Parameter May Be Ignored
**What goes wrong:** The `CongressGovScraper._search_congress()` passes a `query` parameter to the `/bill/{congress}/{billType}` endpoint (line 99-111 of congress_gov.py). The Congress.gov API v3 documentation only lists `fromDateTime`, `toDateTime`, `offset`, `limit`, `format`, and `api_key` as valid parameters for this endpoint.
**Why it happens:** The `query` parameter may have been valid in an earlier API version, or it may be an undocumented parameter. If silently ignored, the endpoint returns ALL bills for the given congress/type within the date window, not filtered by keyword.
**How to avoid:** Test with `--source congress_gov --verbose` and inspect the response. If the result count is unexpectedly large (hundreds of bills), the `query` parameter is likely being ignored. The v3 API may require using the `/summaries` endpoint or a different approach for text-based search.
**Warning signs:** Unexpectedly high item count (>100) from Congress.gov scraper; irrelevant bills appearing in results.
**Confidence:** MEDIUM -- the official API docs do not explicitly list `query` as a parameter, but it may be an undocumented feature that works. Testing will confirm.

### Pitfall 3: Missing API Keys
**What goes wrong:** The Congress.gov scraper requires `CONGRESS_API_KEY` env var. Without it, the scraper logs a warning and returns an empty list (graceful degradation), but this means 1 of 4 sources produces no data.
**Why it happens:** API keys are not stored in the repo (correct). Developers must set them locally and in GitHub Actions secrets.
**How to avoid:** Before running validation, ensure `CONGRESS_API_KEY` is set. The `SAM_API_KEY` is referenced in the workflow but not used by any current scraper (Grants.gov and USASpending don't require keys).
**Warning signs:** Log message "Congress.gov: CONGRESS_API_KEY not set, skipping" during pipeline run.
**Confidence:** HIGH -- directly verified in code (congress_gov.py line 51-52).

### Pitfall 4: First Scan Change Detection Shows All-New
**What goes wrong:** The first scan has no `outputs/LATEST-RESULTS.json` baseline. The ChangeDetector returns all items as "new" and zero as "updated" or "removed." This is correct behavior but does not validate PIPE-04 (change detection).
**Why it happens:** By design -- `_load_previous()` returns `[]` when no cache exists.
**How to avoid:** PIPE-04 validation requires TWO consecutive scans. Between them, some policy items will naturally change (new items posted, old items expire). Alternatively, manually inject a known change to the cache between runs.
**Warning signs:** Change summary shows new_count = total_current and removed_count = 0.
**Confidence:** HIGH -- directly verified in code (change_detector.py lines 74-85).

### Pitfall 5: Windows vs Linux Path Issues
**What goes wrong:** Development on Windows (`F:\tcr-policy-scanner`) but deployment on GitHub Actions (Linux). The codebase uses `pathlib.Path` throughout, which handles cross-platform paths correctly. However, any hardcoded backslashes or Windows-specific paths will break in CI.
**Why it happens:** Dual workspace design.
**How to avoid:** Verify all paths use `Path()` objects (they do). Test locally with `python -m src.main` from the project root. The `CONFIG_PATH`, `INVENTORY_PATH`, and other constants use relative `Path()` objects that work on both platforms.
**Warning signs:** `FileNotFoundError` in CI but not locally.
**Confidence:** HIGH -- codebase audit confirms `Path()` usage throughout.

### Pitfall 6: USASpending Hardcoded FY26 Date Range
**What goes wrong:** The `USASpendingScraper._fetch_obligations()` method has a hardcoded `time_period` of `2025-10-01` to `2026-09-30` (line 67 of usaspending.py). This is correct for FY26 but will become stale if the scanner runs beyond September 2026.
**Why it happens:** FY26 focus baked into the scraper.
**How to avoid:** For Phase 1 validation, this is fine -- it correctly queries FY26 data. Flag for future maintenance.
**Warning signs:** Zero results from USASpending after September 2026.
**Confidence:** HIGH -- directly verified in code.

### Pitfall 7: Rate Limiting and IP Blocking
**What goes wrong:** Federal APIs (especially Federal Register and Grants.gov) may rate-limit or block IPs that make too many requests. The BaseScraper handles 429 with Retry-After and 403 with exponential backoff, but running the full pipeline makes many requests across 4 APIs in quick succession.
**Why it happens:** The scrapers iterate through search queries and CFDA numbers sequentially, making dozens of API calls. Each scraper has `asyncio.sleep(0.3-0.5)` delays between requests, but this may not be sufficient during validation when running repeatedly.
**How to avoid:** During validation, test one source at a time with pauses between tests. Monitor for 429/403 responses in verbose logs.
**Warning signs:** Increasing number of retry attempts in logs; 403 errors appearing on subsequent runs.
**Confidence:** MEDIUM -- based on general federal API behavior; specific rate limits vary by API.

## Code Examples

### Running Individual Scraper Validation
```bash
# Source: src/main.py CLI args
# Test each source individually with verbose logging:

# 1. Federal Register (no key needed)
python -m src.main --source federal_register --verbose

# 2. Grants.gov (no key needed -- but endpoint may need fixing first)
python -m src.main --source grants_gov --verbose

# 3. Congress.gov (requires CONGRESS_API_KEY)
set CONGRESS_API_KEY=your_key_here  # Windows
python -m src.main --source congress_gov --verbose

# 4. USASpending (no key needed)
python -m src.main --source usaspending --verbose

# Full pipeline (all sources):
python -m src.main --verbose
```

### Verifying Output Files Exist
```bash
# After a successful pipeline run, these files should exist:
# outputs/LATEST-BRIEFING.md  (Markdown briefing)
# outputs/LATEST-RESULTS.json (JSON with scan_results array)
# outputs/LATEST-GRAPH.json   (Knowledge graph)
# outputs/archive/briefing-YYYY-MM-DD.md  (archived copy)
# outputs/archive/results-YYYY-MM-DD.json (archived copy)
```

### Validating Change Detection (PIPE-04)
```python
# Validation approach for change detection:
# 1. Run full scan -> creates LATEST-RESULTS.json baseline
# 2. Wait or introduce a change
# 3. Run full scan again -> ChangeDetector compares against baseline
# 4. Verify changes.summary has non-zero counts where expected

# Manual baseline injection (for controlled testing):
import json
from pathlib import Path

# Load current results, modify one item, save as "previous"
results_path = Path("outputs/LATEST-RESULTS.json")
data = json.loads(results_path.read_text())
# Remove one item to simulate a "new" item on next scan
data["scan_results"] = data["scan_results"][1:]
results_path.write_text(json.dumps(data, indent=2))
# Next scan should show at least 1 "new" item
```

### Dry Run Validation (Pre-Flight Check)
```bash
# Validates config loading, CFDA mappings, search queries
# without making any API calls:
python -m src.main --dry-run
```

### GitHub Actions Manual Trigger
```bash
# Trigger the daily-scan workflow manually via gh CLI:
gh workflow run daily-scan.yml

# Monitor the run:
gh run list --workflow=daily-scan.yml --limit=1
gh run watch  # interactive watch
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Grants.gov `/opportunities/search` | Grants.gov `/v1/api/search2` | March 2025 | **Scraper endpoint URL and parameters must be updated** |
| `assistanceListing` parameter | `aln` parameter | March 2025 | CFDA-based queries use wrong parameter name |
| Congress.gov API v2 | Congress.gov API v3 | Pre-existing | Scraper already targets v3; but `query` param may not be supported |

**Deprecated/outdated:**
- Grants.gov `/opportunities/search` endpoint: replaced by `/v1/api/search2`. The old endpoint may still work but is not documented in current API guide.
- Response field `oppHits` appears in the new API too, so the normalizer may still work if the endpoint is fixed.

## API Status Summary

| API | Base URL | Auth | Status | Scraper Compatibility |
|-----|----------|------|--------|-----------------------|
| Federal Register | `https://www.federalregister.gov/api/v1` | None | Active, stable | GOOD -- endpoint and params match |
| Grants.gov | `https://api.grants.gov/v1` | None | Active, modernized | NEEDS FIX -- wrong endpoint path and parameter names |
| Congress.gov | `https://api.congress.gov/v3` | API key (CONGRESS_API_KEY) | Active | UNCERTAIN -- `query` parameter may not be supported on `/bill` endpoint |
| USASpending | `https://api.usaspending.gov/api/v2` | None | Active, stable | GOOD -- endpoint, filters, and response format match |

## Validation Sequence

The recommended validation order for Plan 1.1:

1. **Dry run** -- `python -m src.main --dry-run` (validates config loading)
2. **Federal Register** -- `--source federal_register` (most likely to work unchanged)
3. **USASpending** -- `--source usaspending` (no key needed, well-documented API)
4. **Congress.gov** -- `--source congress_gov` (requires key; test query behavior)
5. **Grants.gov** -- `--source grants_gov` (likely needs endpoint fix first)
6. **Full pipeline** -- `python -m src.main --verbose` (all sources together)
7. **Second scan** -- run again to validate change detection (PIPE-04)

For Plan 1.2 (CI Workflow Validation):

1. **Verify secrets** -- Ensure CONGRESS_API_KEY and SAM_API_KEY are set in GitHub repo secrets
2. **Manual trigger** -- `gh workflow run daily-scan.yml`
3. **Verify schedule** -- Confirm cron `0 13 * * 1-5` = 6 AM Pacific on weekdays (correct)
4. **Check output** -- Verify committed files in `outputs/` after workflow completes

## Open Questions

Things that couldn't be fully resolved:

1. **Congress.gov `query` parameter behavior**
   - What we know: The official API documentation does not list `query` as a parameter on the `/bill/{congress}/{billType}` endpoint. Only `fromDateTime`, `toDateTime`, `offset`, `limit`, `format`, and `api_key` are documented.
   - What's unclear: Whether `query` is an undocumented but functional parameter, or if it is silently ignored.
   - Recommendation: Test with `--source congress_gov --verbose` and inspect result counts. If results are unfiltered (too many), the scraper needs a different approach -- possibly using the Congress.gov website's advanced search or a different endpoint.

2. **Grants.gov `opportunities/search` endpoint availability**
   - What we know: The documented current endpoint is `/v1/api/search2`. There is no documentation for `/opportunities/search`.
   - What's unclear: Whether the old endpoint still works (undocumented but not removed).
   - Recommendation: Try the existing scraper first. If it fails, update to `/v1/api/search2` with parameter mapping: `assistanceListing` -> `aln`, keep `keyword`, keep `oppStatuses`, keep `rows`. Response field `oppHits` appears unchanged.

3. **SAM_API_KEY usage**
   - What we know: The GitHub Actions workflow passes `SAM_API_KEY` as an env var, but no scraper currently uses it. Grants.gov search2 requires no authentication.
   - What's unclear: Whether SAM_API_KEY was intended for a future Grants.gov feature or a different endpoint.
   - Recommendation: Leave in workflow for now; does not affect validation.

4. **Grants.gov search2 response field mapping**
   - What we know: The search2 endpoint returns `oppHits` with fields including `id`, `number`, `title`, `agencyCode`, `openDate`, `closeDate`, `oppStatus`, `docType`, `alnist`. The current normalizer expects some of these but also looks for `synopsis` (abstract), `awardCeiling`, `awardFloor`, `eligibleApplicants`.
   - What's unclear: Whether the search2 response includes these additional fields or if they were specific to the old endpoint.
   - Recommendation: Fetch a sample response from search2 and compare fields against the normalizer expectations. Some fields may need name mapping.

## Sources

### Primary (HIGH confidence)
- **Codebase analysis** -- Direct reading of all source files in `F:\tcr-policy-scanner\src\`
- **Federal Register API docs** -- https://www.federalregister.gov/developers/documentation/api/v1 (no key needed, RESTful, JSON responses)
- **Grants.gov API guide** -- https://www.grants.gov/api/api-guide (search2 endpoint, no auth)
- **Grants.gov search2 docs** -- https://www.grants.gov/api/common/search2 (parameter names: `aln`, `keyword`, `oppStatuses`, `rows`)
- **USASpending API contracts** -- https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/search/spending_by_award.md
- **Congress.gov API docs** -- https://api.congress.gov (v3, API key required)

### Secondary (MEDIUM confidence)
- **Congress.gov GitHub** -- https://github.com/LibraryOfCongress/api.congress.gov (bill endpoint parameters)
- **Grants.gov RESTful API announcement** -- https://grantsgovprod.wordpress.com/2025/03/13/2-restful-apis-are-now-available-for-system-to-system-users/ (March 2025 modernization)

### Tertiary (LOW confidence)
- **Congress.gov `query` parameter** -- No official documentation found confirming or denying the parameter. Needs live testing to resolve.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- directly verified from requirements.txt and source imports
- Architecture: HIGH -- complete codebase audit performed; all files read
- Pitfalls: HIGH for Grants.gov endpoint mismatch (verified against official docs); MEDIUM for Congress.gov query parameter (could not fully resolve without live testing)
- API compatibility: HIGH for Federal Register and USASpending; LOW-MEDIUM for Grants.gov and Congress.gov until live testing

**Research date:** 2026-02-09
**Valid until:** 2026-03-09 (30 days -- APIs are stable; Grants.gov modernization is the main risk)
