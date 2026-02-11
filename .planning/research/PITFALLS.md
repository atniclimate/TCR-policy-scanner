# Domain Pitfalls: Tech Debt Cleanup in a Production Python Async Pipeline

**Domain:** Refactoring 17 tech debt items in a shipping Python 3.12 async pipeline
**Project:** TCR Policy Scanner v1.2 (tech debt milestone)
**Researched:** 2026-02-11
**Confidence:** MEDIUM-HIGH (findings verified against codebase inspection, official Python docs, and community patterns)

**Governing constraint:** 287 tests passing, daily scan workflow running on GitHub Actions, DOCX generation for 592 Tribes on weekly schedule. Every change must preserve all three.

---

## Critical Pitfalls

Mistakes that break the production pipeline, cause data loss, or require emergency rollbacks. These are the ones that turn a "cleanup" milestone into a firefight.

---

### C-1: Circuit Breaker Interacts Badly with Existing Retry Logic in BaseScraper

**What goes wrong:** Adding a circuit breaker to `BaseScraper` that wraps `_request_with_retry` creates a double-fault-handling stack. The existing retry loop (3 attempts with exponential backoff + 429 handling) and the new circuit breaker compete for control. Specific failure modes:

- The circuit breaker trips after seeing N failures, but those "failures" were retryable transient errors that `_request_with_retry` would have recovered from on attempt 2 or 3. The circuit opens prematurely, killing an entire scraper for the rest of the scan.
- The circuit breaker counts 429 rate-limit responses as failures. But the existing code explicitly handles 429 with `Retry-After` headers and does NOT increment the attempt counter (line 74 of `base.py`: `continue # Do NOT increment attempt for server-requested delay`). If the circuit breaker sees 429s as failures, it will trip during normal rate-limited operation of USASpending and Congress.gov.
- In half-open state, the circuit breaker allows one probe request. If that probe happens to be a 429 (which is normal during high-volume batch runs), the circuit re-opens for another full cooldown period, creating a cascading delay.

**Why it happens:** Circuit breakers and retry-with-backoff solve overlapping problems at different layers. Retry handles transient failures within a single operation. Circuit breakers handle sustained service degradation across operations. Layering them naively creates a state machine that is hard to reason about.

**Consequences:** Daily scans that previously succeeded with occasional retries now fail entirely because the circuit breaker opens after 2-3 transient errors. The USASpending scraper (which routinely returns 429s during batch Tribal award fetches) becomes unreliable. The `generate-packets.yml` weekly workflow times out because the circuit is open for extended periods.

**Prevention:**
1. Place the circuit breaker OUTSIDE `_request_with_retry`, not inside it. The circuit breaker should see the final outcome of a retry sequence (success or exhausted retries), not intermediate retry attempts.
2. Configure the circuit breaker to count only exhausted-retry failures (the exception raised on line 102 of `base.py`), NOT individual 429/timeout events within the retry loop.
3. Use per-source circuit breakers, not a global one. A Federal Register outage should not block the Grants.gov scraper. The current `BaseScraper.__init__` takes `source_name` -- use this as the circuit breaker key.
4. Set the failure threshold high enough for the daily scan pattern: the scanner makes roughly 50-80 requests per source. A threshold of 5 consecutive final-failures (not retries) is appropriate. Lower thresholds will trip on normal operation.
5. In half-open state, exempt 429 responses from the "probe failed" determination. A 429 with `Retry-After` is a throttle signal, not a service failure.
6. Provide a fallback in open-circuit state that returns cached data (the existing `ChangeDetector.load_cached()` pattern), not an empty result. The daily scan should degrade to "no new data from source X" rather than "source X produced 0 items."

**Warning signs:** After adding circuit breaker, daily scan logs show `circuit open for <source>` messages. Scan results show 0 items from one or more sources that previously returned data. Batch packet generation takes 3x longer than before.

**Detection:** Add a test that simulates the exact retry sequence from the existing codebase (2 failures, then success) and verify the circuit breaker does NOT trip. Add a test that simulates the 429 + Retry-After sequence and verify the circuit breaker does NOT count it as a failure.

**Severity:** BREAKS PRODUCTION if circuit opens during normal operation.

**Affected items:** Circuit breaker addition to BaseScraper.

---

### C-2: Changing Logger Names Breaks Log Filtering and Monitoring

**What goes wrong:** The codebase has two logger naming patterns:
- **v1.0 modules** use `logging.getLogger(__name__)` (e.g., `src.scrapers.base`, `src.scrapers.federal_register`, `src.reports.generator`, `src.analysis.change_detector`)
- **v1.1 modules** use hardcoded `logging.getLogger("tcr_scanner.packets.xxx")` (e.g., `tcr_scanner.packets.orchestrator`, `tcr_scanner.packets.docx_engine`)

Unifying these creates a breaking change either way:
- If v1.0 modules switch to `"tcr_scanner.xxx"` format, the logger hierarchy changes. Any downstream log aggregation, filtering, or monitoring that looks for `src.scrapers.*` log patterns will stop matching.
- If v1.1 modules switch to `__name__`, their logger names become `src.packets.xxx` instead of `tcr_scanner.packets.xxx`. This changes the logger hierarchy parent from `tcr_scanner` (non-existent root logger) to `src` (actual package root).
- The root logger is configured in `main.py` line 305 with `logging.basicConfig()`. This configures the ROOT logger, which catches all loggers regardless of name. But if any external consumer (GitHub Actions log parsing, grep-based alerting) uses logger name patterns, changing names breaks them.

**Why it happens:** v1.0 followed Python best practice (`__name__`). v1.1 used explicit names because the `src.packets` package was added later and the developer wanted a consistent `tcr_scanner.packets.*` prefix that matches the `main.py` root logger name `tcr_scanner`. Neither approach is wrong, but mixing them creates inconsistency that is tempting to "fix."

**Consequences:** Moderate -- log filtering breaks silently. You do not get an error; you just stop seeing logs you expected. This is dangerous in production because a broken scraper might be silently failing and the log line that would alert you is now under a different logger name.

**Prevention:**
1. Pick ONE convention and apply it consistently, but do it in a SINGLE commit that changes ONLY logger names, nothing else. This makes it trivially revertable if problems appear.
2. The recommended convention is `__name__` for all modules. This is Python standard practice, produces hierarchical logger names that match the package structure, and requires zero maintenance when modules move.
3. Before changing, audit all places that reference logger names:
   - `main.py` `logging.basicConfig()` -- uses root logger, unaffected.
   - GitHub Actions workflow YAML -- no log filtering, unaffected.
   - Any `grep` or monitoring scripts on the outputs -- check for logger name patterns.
4. Update `basicConfig` in `main.py` to set the root logger name explicitly if needed, or add a `tcr_scanner` logger that propagates to root.
5. Test by running `python -m src.main --dry-run --verbose` before and after, diff the log output to verify same messages appear under new names.

**Warning signs:** After renaming, `--verbose` output appears different (different prefix on log lines). Monitoring dashboards show a drop in log volume.

**Detection:** Before/after diff of `--dry-run --verbose` output capturing logger names.

**Severity:** DEGRADES OBSERVABILITY -- silent failure, hard to detect.

**Affected items:** Logger naming pattern fix.

---

### C-3: Making FY26 Configurable Breaks Hardcoded References in 6+ Modules

**What goes wrong:** "FY26" is hardcoded in at least 6 locations across the codebase:
- `usaspending.py` line 68: `"start_date": "2025-10-01", "end_date": "2026-09-30"` (API filter)
- `usaspending.py` line 216: `f"FY26 Obligation: ..."` (display string in normalized output)
- `graph/builder.py` line 176: `urgency="FY26"` (graph node property)
- `graph/builder.py` line 398: `fiscal_year="FY26"` (graph node property)
- `monitors/iija_sunset.py` line 53: `fy26_end` config key and `"2026-09-30"` default
- `packets/strategic_overview.py` lines 182, 195, 227: `"FY26 Federal Funding Overview"` (DOCX text)
- `packets/docx_sections.py` line 55: `"FY26 Climate Resilience Program Priorities"` (DOCX text)
- `config/scanner_config.json` line 118: `"fy26_end": "2026-09-30"` (monitor config)

Making FY configurable requires touching all of these locations. The risk is threefold:
1. **Partial migration:** You move 5 of 6 locations to config but miss one. Now the pipeline produces mixed-FY data (e.g., USASpending queries FY27 data but the graph labels it FY26).
2. **Display vs. query divergence:** The fiscal year date range (Oct 1 - Sep 30) and the display label ("FY26") are semantically coupled but stored separately. If config has `fiscal_year: 2027` but someone forgets to update `fy26_end` in the monitor config, the IIJA sunset monitor uses stale dates.
3. **Test fixtures use hardcoded FY26:** The mock programs in `test_e2e_phase8.py` (line 41: `"ci_determination": "FY26 budget uncertainty."`) and other test files contain FY26 strings. If the configurable FY propagates to test assertions, existing tests break.

**Why it happens:** FY26 was correctly hardcoded during initial development because the product has a specific fiscal year focus. Making it configurable is a reasonable improvement, but the hardcoded values have proliferated into test fixtures, display strings, graph properties, and API query parameters -- each with different update semantics.

**Consequences:**
- Mixed-FY data in reports (some sections say FY26, others FY27)
- IIJA sunset monitor miscalculates days remaining
- USASpending queries wrong date range
- Test suite breaks on FY transition

**Prevention:**
1. Create a single config key `fiscal_year` (integer: `2026`) and derive ALL dependent values from it:
   - `fy_start_date = f"{fiscal_year - 1}-10-01"`
   - `fy_end_date = f"{fiscal_year}-09-30"`
   - `fy_label = f"FY{fiscal_year % 100:02d}"`
   - `fy_end = fy_end_date` (for monitors)
2. Create a `FiscalYear` utility class or module that computes all derived values. This prevents divergence.
3. Use a grep/search to find EVERY instance of "FY26", "2025-10-01", "2026-09-30" in the codebase before starting. The list above has at least 8 locations but there may be more in test files and data files.
4. For display strings in DOCX output, use `f"FY{fy % 100:02d}"` format consistently.
5. Update test fixtures to either use the config value or hardcode a test-specific FY that is distinct from production (e.g., FY99) to make it obvious when a test is using a fixture vs. production config.
6. Add a regression test: load config, verify all FY-dependent computed values are consistent with each other.

**Warning signs:** `grep -r "FY26" src/` still returns matches after the change. USASpending data looks empty (querying a future FY). IIJA sunset shows negative days remaining.

**Detection:** Post-migration: `grep -rn "FY26\|2025-10-01\|2026-09-30" src/ tests/` should return zero matches outside of test fixture comments.

**Severity:** BREAKS DATA INTEGRITY if partial migration. Display-only issues are cosmetic; query issues are data-corrupting.

**Affected items:** FY26 configurability.

---

### C-4: Moving Hardcoded Paths to Config Changes Working Directory Assumptions

**What goes wrong:** The codebase uses 20+ relative paths as module-level constants:
- `main.py`: `Path("config/scanner_config.json")`, `Path("data/program_inventory.json")`, `Path("outputs/LATEST-GRAPH.json")`
- `base.py`: `Path("outputs/.cfda_tracker.json")`
- `graph/builder.py`: `Path("data/graph_schema.json")`
- `hot_sheets.py`: `Path("outputs/.monitor_state.json")`
- `change_detector.py`: `Path("outputs/LATEST-RESULTS.json")`
- All `packets/*.py` modules: various `data/` and `outputs/` paths

All of these are relative paths that resolve against the **current working directory** (CWD). This works because:
- **Locally:** You run `python -m src.main` from `F:\tcr-policy-scanner`
- **GitHub Actions:** The checkout action sets CWD to the repo root

Moving these to config introduces two failure modes:
1. **Config file itself needs a path:** If all paths are in config, how do you find the config file? You need at least one hardcoded path to bootstrap. If that bootstrap path changes, everything breaks.
2. **Relative paths in config resolve against CWD, not config file location:** If someone runs the scanner from a different directory (e.g., `cd /tmp && python -m src.main`), all the relative config paths resolve against `/tmp`, not the project root. This is a known Python pitfall.
3. **Module-level `Path()` constants are evaluated at import time:** If you change `CFDA_TRACKER_PATH = Path("outputs/.cfda_tracker.json")` to `CFDA_TRACKER_PATH = Path(config["cfda_tracker_path"])`, you need the config to be loaded before the module is imported. This creates an import-order dependency that does not exist today.

**Why it happens:** The current hardcoded relative paths work because of an implicit contract: CWD = project root. This contract is fragile but functional. Config-based paths are more flexible in theory but introduce resolution ambiguity.

**Consequences:**
- `FileNotFoundError` on `config/scanner_config.json` when run from a different directory
- Data files written to wrong directory (e.g., CFDA tracker in `/tmp/outputs/` instead of project `outputs/`)
- GitHub Actions workflow breaks if checkout path changes or a step changes CWD

**Prevention:**
1. Establish a `PROJECT_ROOT` anchor early in `main.py` using `Path(__file__).resolve().parent.parent` (the `src/main.py` is two levels deep). All paths should resolve relative to this anchor, not CWD.
2. Move paths to config as RELATIVE strings (e.g., `"outputs_dir": "outputs"`) and resolve them against `PROJECT_ROOT` at config-load time, not at module import time.
3. Keep the config file path as the ONLY remaining hardcoded path, resolved relative to `PROJECT_ROOT`.
4. Do NOT move module-level `Path()` constants to config if they are only used within that module. Internal implementation paths (like `CFDA_TRACKER_PATH`, `MONITOR_STATE_PATH`) can stay as module constants but should be resolved against `PROJECT_ROOT` instead of CWD.
5. Test from a non-root directory: `cd /tmp && python -m src.main --dry-run` must still work after the change.
6. Update both GitHub Actions workflows (`daily-scan.yml` and `generate-packets.yml`) if any path assumptions change.

**Warning signs:** Tests pass locally but GitHub Actions fails with `FileNotFoundError`. Running `--dry-run` from a subdirectory fails.

**Detection:** Add a CI test that runs `python -m src.main --dry-run` from a temporary directory (not project root) to verify path resolution works.

**Severity:** BREAKS PRODUCTION if paths resolve incorrectly on Linux CI.

**Affected items:** Hardcoded paths to config migration.

---

## Moderate Pitfalls

Mistakes that cause test failures, subtle bugs, or significant rework but do not break the production pipeline if caught during development.

---

### M-1: Deduplicating CFDA Mappings Creates an Import Dependency That Did Not Exist

**What goes wrong:** The CFDA-to-program mapping is defined in two places:
- `grants_gov.py` line 23: `CFDA_NUMBERS = {"15.156": "bia_tcr", ...}` (12 entries)
- `usaspending.py` line 21: `CFDA_TO_PROGRAM = {"15.156": "bia_tcr", ...}` (12 entries)

These are nearly identical but live in separate modules. The obvious deduplication is to create a shared `constants.py` or move one to `base.py`. However:

1. `awards.py` already imports from `usaspending.py` (line 25: `from src.scrapers.usaspending import CFDA_TO_PROGRAM`). If you move `CFDA_TO_PROGRAM` to `base.py`, the `awards.py` import breaks.
2. `main.py` imports from `grants_gov.py` (line 92: `from src.scrapers.grants_gov import CFDA_NUMBERS`). If you consolidate into `CFDA_TO_PROGRAM` only, the `main.py` import breaks.
3. Creating a new `src/scrapers/constants.py` is clean but adds an import that did not exist. If any of the existing modules has a latent circular dependency (e.g., through `base.py` importing from a child module), the new shared import could trigger it.

**Why it happens:** The two mappings were created independently in v1.0 during different phases. They serve the same semantic purpose but have different variable names reflecting their original context.

**Prevention:**
1. Create `src/constants.py` (project-level, not scraper-level) with `CFDA_PROGRAM_MAP` as the canonical name. This avoids any circular import risk because `constants.py` imports nothing from the project.
2. Update all three import sites: `grants_gov.py`, `usaspending.py`, `awards.py`, and `main.py`.
3. Keep backward-compatible aliases in the old locations for one release cycle:
   ```python
   # grants_gov.py
   from src.constants import CFDA_PROGRAM_MAP as CFDA_NUMBERS  # deprecated alias
   ```
4. Run `pytest` after moving the constant but BEFORE changing any other code. Verify all 287 tests pass with just the move.

**Warning signs:** `ImportError` on test run. Circular import traceback.

**Detection:** `python -c "from src.scrapers.grants_gov import CFDA_NUMBERS"` succeeds after the change.

**Severity:** BREAKS TESTS (easily caught) but could create circular imports (harder to diagnose).

**Affected items:** Utility deduplication.

---

### M-2: Integration Tests for Live Scrapers Create Flaky CI

**What goes wrong:** Adding integration tests that call live federal APIs (Federal Register, Grants.gov, Congress.gov, USASpending) to the test suite makes CI unreliable:

1. **Rate limiting in CI:** GitHub Actions runners share IP ranges. If multiple repos run similar tests, the shared IP hits rate limits. Congress.gov has a 5,000/hour limit; the runner IP may already be partially consumed.
2. **API availability:** Federal APIs have maintenance windows, unscheduled outages, and weekend/holiday reduced capacity. The weekly packet generation workflow runs Sunday mornings (line 6 of `generate-packets.yml`). If integration tests also run on push/PR, they hit the APIs frequently.
3. **Data drift:** Live API results change daily. A test that asserts "Federal Register returns at least 5 results for 'tribal climate resilience'" may fail during slow news periods or pass with 50 results during active rulemaking.
4. **Secrets in CI:** Congress.gov requires `CONGRESS_API_KEY`. If integration tests run on PRs from forks, the secret is not available (`${{ secrets.CONGRESS_API_KEY }}` is empty for fork PRs). The existing `congress_gov.py` already handles this (line 53: returns `[]` if no key), but tests asserting non-empty results will fail.
5. **Test contamination:** Integration tests that write to `outputs/` or `data/` directories can contaminate the state used by unit tests that check for cached data absence.

**Why it happens:** The 287 existing tests all use `tmp_path` fixtures with mock data and no network access. Adding live API tests changes the testing paradigm.

**Prevention:**
1. Mark integration tests with `@pytest.mark.integration` and exclude them from default `pytest` runs. Use `pytest -m integration` explicitly.
2. Run integration tests on a schedule (weekly, matching the packet generation cadence) rather than on every push.
3. Create a separate GitHub Actions workflow for integration tests that runs on `workflow_dispatch` and weekly schedule, not on `push` or `pull_request`.
4. Assert structural properties, not specific data: "response has `results` key" not "results contain at least N items." Assert the scraper runs without exception, not that it returns specific data.
5. Use `tmp_path` for all output files in integration tests. Never write to the real `outputs/` or `data/` directories.
6. Handle missing API keys gracefully: `pytest.mark.skipif(not os.environ.get("CONGRESS_API_KEY"), reason="No API key")`.

**Warning signs:** CI becomes "red" intermittently. Tests pass locally but fail in Actions. Tests pass on weekdays but fail weekends.

**Detection:** Check CI run history for intermittent failures correlated with time-of-day or day-of-week.

**Severity:** DEGRADES CI RELIABILITY -- developers stop trusting test results and start ignoring failures.

**Affected items:** Integration tests for live scrapers.

---

### M-3: Populating Data Caches Creates Side Effects That Surprise Other Modules

**What goes wrong:** Some tech debt items involve populating data caches that currently require manual API runs (e.g., award caches in `data/award_cache/`, hazard profiles in `data/hazard_profiles/`). Making this automatic (e.g., a `--refresh-caches` CLI flag) creates side effects:

1. **Cache-dependent modules see different data between runs:** The `PacketOrchestrator._load_tribe_cache()` method reads from `data/award_cache/{tribe_id}.json`. If a cache refresh runs concurrently with (or immediately before) packet generation, some Tribes get new data while others get stale data, producing inconsistent packets in the same batch.
2. **Cache format changes are invisible:** If the cache refresh code writes a different JSON structure than what `_load_tribe_cache` expects (e.g., adds a new top-level key, changes `awards` to `award_records`), the loading code silently returns `{}` (line 213 of `orchestrator.py`: `except (json.JSONDecodeError, OSError)` catches the wrong error -- `KeyError` from accessing a missing key is NOT caught).
3. **Cache files on disk are not versioned:** There is no schema version in the cache JSON. When cache format evolves, old cached files produce silently wrong results rather than clear errors.

**Why it happens:** The cache layer was designed as a simple pass-through: scripts populate JSON files, orchestrator reads them. There is no contract enforcement between writer and reader.

**Prevention:**
1. Add a `schema_version` key to all cache files. The reader checks the version and raises a clear error if it does not match the expected version, rather than silently returning empty data.
2. When adding `--refresh-caches`, make it a separate CLI command that completes BEFORE packet generation starts (sequential, not concurrent). The existing `run_pipeline()` in `main.py` already runs stages sequentially -- follow this pattern.
3. Add a `KeyError` to the exception tuple in `_load_tribe_cache` (line 213 of `orchestrator.py`): `except (json.JSONDecodeError, OSError, KeyError)`. Better yet, validate the structure after loading.
4. Write cache files atomically (the existing tmp-file + `os.replace()` pattern is already used in `docx_engine.py` and `reports/generator.py` -- apply it consistently to all cache writers).
5. Add a test that writes a cache file with the expected structure and verifies `_load_tribe_cache` returns the correct data. Then add a test with a WRONG structure and verify it returns `{}` with a warning log.

**Warning signs:** Packet generation shows $0 awards for Tribes that have cached award data. Log shows "Failed to load cache" warnings after a cache refresh.

**Detection:** Add a `--validate-caches` flag that checks all cache files for schema conformance without generating packets.

**Severity:** DEGRADES DATA QUALITY -- silent incorrect results in generated packets.

**Affected items:** Cache population, data integrity.

---

### M-4: Deduplicating Utility Functions Across Modules Can Break Subtle Behavioral Differences

**What goes wrong:** Beyond CFDA mappings, there are utility patterns repeated across modules that look duplicated but have intentional differences:

1. **JSON write patterns:** Multiple modules implement atomic JSON write (tmp file + replace). The pattern in `reports/generator.py` uses `shutil.copy2` for archival, `base.py` uses `Path.replace()`, and `docx_engine.py` uses `os.replace()`. These are subtly different: `Path.replace()` and `os.replace()` are atomic on POSIX but not on Windows for cross-volume moves; `shutil.copy2` preserves metadata.
2. **`_write_json` helper:** Both `test_e2e_phase8.py` and `test_packets.py` define identical `_write_json(path, data)` helper functions. Deduplicating these into a shared `tests/conftest.py` fixture is safe, but if you also add it to `src/` as a production utility, you need to handle the `encoding="utf-8"` parameter and atomic-write semantics differently than the test version.
3. **`_load_json` patterns:** `orchestrator.py._load_tribe_cache()` and `strategic_overview.py._load_json()` both load JSON files with size limits and error handling, but with different size limits and different error handling behavior. Consolidating them requires parameterizing the size limit and error behavior, which may be more complex than the duplication.

**Why it happens:** Similar code is not always duplicate code. When two modules implement the same pattern with different error handling, size limits, or platform behavior, they are solving related but distinct problems.

**Prevention:**
1. Before deduplicating, make a table of each "duplicated" function with its:
   - Error handling behavior
   - Return value on failure
   - Platform-specific behavior (atomic writes on Windows vs. POSIX)
   - Size limits or guards
2. Only deduplicate functions that are truly identical in ALL dimensions. For functions that differ in parameters but share structure, create a parameterized utility only if 3+ call sites exist.
3. For the atomic JSON write pattern, create a single `write_json_atomic(path, data, **kwargs)` that uses the `os.replace()` pattern (it works correctly on both platforms when source and destination are on the same volume, which they always are in this codebase).
4. For test utilities, use `conftest.py` fixtures rather than shared modules. Test helpers should not leak into production code.
5. Run the full test suite after EACH function consolidation, not after consolidating all of them. This makes it easy to identify which consolidation broke something.

**Warning signs:** A consolidated utility works for module A but fails for module B because module B relied on a behavioral difference (e.g., different exception handling).

**Detection:** Diff the behavior of each "duplicate" pair before and after consolidation.

**Severity:** BREAKS TESTS or DEGRADES RELIABILITY -- depends on which difference is lost.

**Affected items:** Utility deduplication.

---

### M-5: Circuit Breaker State Persistence Across Daily Scan Runs

**What goes wrong:** A circuit breaker that lives only in memory resets every time the scanner runs. This is fine for the daily scan (fresh process each run). But for the weekly batch packet generation (`--prep-packets --all-tribes`), which is a single long-running process making thousands of API calls, the circuit breaker state must persist across the full run.

The subtler problem: if the circuit breaker opens during a batch run at Tribe #200 of 592, what happens to Tribes #201-592? Options:
- **Skip them:** Produces incomplete batch (200 packets instead of 592).
- **Use cached data:** Produces packets with stale data for 392 Tribes -- which may be acceptable if the cache is recent, but misleading if caches are empty (first-time applicant Tribes show as having awards).
- **Wait for cooldown:** Adds 5-30 minutes of dead time, potentially causing the `timeout-minutes: 30` in `generate-packets.yml` to expire.

**Why it happens:** Circuit breaker design typically assumes a long-running service with continuous traffic, not a batch process that runs for 20 minutes weekly.

**Prevention:**
1. For the batch packet generation path, implement a "degrade gracefully" strategy: if the circuit opens, log a warning and continue generating packets using cached data, flagging which Tribes used stale data.
2. Set the circuit breaker cooldown period to be short (30-60 seconds) for batch mode, long (5 minutes) for individual operations. The batch run can afford to pause briefly and retry.
3. Do NOT persist circuit breaker state to disk between runs. Each daily scan and each batch run should start with fresh circuit breaker state (all circuits closed).
4. Track which Tribes were affected by open circuits and emit a summary at the end of the batch run: "15 Tribes used cached data due to USASpending circuit open."

**Warning signs:** Batch run produces fewer packets than expected. Batch run fails with timeout in GitHub Actions.

**Detection:** Add a post-batch summary that reports circuit breaker trip counts per source.

**Severity:** DEGRADES BATCH QUALITY -- partial or stale results.

**Affected items:** Circuit breaker + batch generation interaction.

---

### M-6: Windows/Linux Path Separator in Newly Configurable Paths

**What goes wrong:** The existing hardcoded `Path("data/award_cache")` works on both platforms because Python's `pathlib.Path` normalizes forward slashes. But if paths move to `scanner_config.json`:

```json
"awards": {
    "cache_dir": "data\\award_cache"
}
```

A config file edited on Windows might use backslashes. When this config is committed to git and deployed on Linux via GitHub Actions, `Path("data\\award_cache")` on Linux creates a single directory named `data\award_cache` (with a literal backslash in the name) instead of `data/award_cache` (nested directories).

This is not hypothetical: the project has dual-platform development (Windows at `F:\tcr-policy-scanner`, Linux on GitHub Actions).

**Why it happens:** JSON does not normalize path separators. `pathlib.Path` normalizes forward slashes to the platform separator, but does NOT convert backslashes on Linux (backslash is a valid filename character on Linux).

**Prevention:**
1. Mandate forward slashes in all JSON config paths. Add a comment in `scanner_config.json`: `// All paths use forward slashes (works on both Windows and Linux)`.
2. When loading paths from config, normalize them: `Path(config_path.replace("\\", "/"))`.
3. Add a config validation step at startup that checks all configured paths for backslashes and warns.
4. Better yet: store paths as lists of components and join them with `Path()`:
   ```python
   cache_dir = Path(*config["awards"]["cache_dir_parts"])  # ["data", "award_cache"]
   ```
   This is more verbose but platform-safe. However, it is a non-standard pattern that may confuse contributors.
5. The simplest approach: keep forward slashes in config, add a one-line normalize on read.

**Warning signs:** GitHub Actions `FileNotFoundError` for a path that works locally. A directory with a backslash in its name appears on the Linux runner.

**Detection:** CI test that validates all config paths resolve to existing directories (or can be created).

**Severity:** BREAKS CI if backslash paths are committed.

**Affected items:** Hardcoded paths to config.

---

## Minor Pitfalls

Mistakes that cause rework, annoyance, or minor issues but are straightforward to fix once identified.

---

### m-1: Existing Tests Assume Exact Import Paths That Change During Deduplication

**What goes wrong:** Tests import directly from implementation modules:
- `from src.scrapers.usaspending import CFDA_TO_PROGRAM` (in `awards.py` and potentially tests)
- `from src.scrapers.grants_gov import CFDA_NUMBERS` (in `main.py`)

When these constants move to a shared module, any test that imports them from the OLD location breaks with `ImportError` unless backward-compatible re-exports are maintained.

**Prevention:** When moving a public constant, add a re-export in the old location: `from src.constants import CFDA_PROGRAM_MAP as CFDA_TO_PROGRAM`. Remove the re-export in a subsequent release, not in the same commit.

**Severity:** MINOR -- `ImportError` is immediately visible in test runs.

**Affected items:** Utility deduplication.

---

### m-2: asyncio.run() Cannot Be Called from Inside a Running Event Loop

**What goes wrong:** If integration tests use `asyncio.run()` to call async scraper methods, they conflict with pytest-asyncio's event loop. The existing `main.py` uses `asyncio.run(run_scan(...))` at line 237, which works in the CLI context. But integration tests running under `pytest-asyncio` already have an event loop, and calling `asyncio.run()` inside it raises `RuntimeError: This event loop is already running`.

**Why it happens:** Integration tests for async scrapers need to call the same `scan()` methods that production code calls. But the production entry point wraps them in `asyncio.run()`, which cannot be nested.

**Prevention:**
1. Integration tests should use `@pytest.mark.asyncio` and `await scraper.scan()` directly, NOT `asyncio.run()`.
2. Test the `run_scan()` coroutine from `main.py`, not `run_pipeline()` (which wraps it in `asyncio.run()`).
3. If testing the CLI entry point end-to-end, use `subprocess.run(["python", "-m", "src.main", ...])` to invoke it in a separate process.

**Severity:** MINOR -- immediate `RuntimeError` with clear message.

**Affected items:** Integration tests for live scrapers.

---

### m-3: Circuit Breaker Library Choice Affects async Compatibility

**What goes wrong:** Several circuit breaker libraries exist for Python:
- `pybreaker`: Synchronous only. Will block the event loop if used in async code.
- `aiobreaker`: Async-native, but has not been updated since 2022.
- `circuitbreaker`: Synchronous decorator pattern. Not compatible with async/await.
- `aiomisc.CircuitBreaker`: Part of the `aiomisc` utility library (actively maintained).

Choosing a sync-only library for an async codebase (all scrapers use `aiohttp` with `async/await`) will silently work in tests but block the event loop in production, causing the entire scan to serialize instead of running concurrently.

**Prevention:**
1. Use an async-native circuit breaker: either `aiobreaker` or `aiomisc.CircuitBreaker`.
2. Alternatively, implement a minimal circuit breaker in `base.py` itself (20-30 lines of async-compatible code). The pattern is simple: counter, threshold, timestamp, and three states. This avoids adding a dependency and gives full control over the 429-exemption behavior needed (see C-1).
3. If implementing custom, test it with `asyncio.gather()` to verify it does not serialize concurrent requests.

**Severity:** MINOR -- easy to detect in development (scan becomes slow), easy to fix.

**Affected items:** Circuit breaker technology choice.

---

### m-4: Test Count May Decrease When Deduplicating Test Helpers

**What goes wrong:** Both `test_packets.py` and `test_e2e_phase8.py` define identical `_write_json()` helpers. Consolidating them into a shared `conftest.py` fixture is correct, but if you also remove tests that were implicitly testing the helper (e.g., a test that writes and reads JSON), the test count drops. The MEMORY.md records "287 tests" -- if the count drops below this, it looks like a regression.

**Prevention:** Verify test count before and after deduplication: `pytest --co -q | tail -1` should show the same or higher count.

**Severity:** MINOR -- cosmetic, but creates confusion about "did we lose coverage?"

**Affected items:** Utility deduplication.

---

### m-5: Monitoring Configuration Keys Contain "fy26" Which Needs Migration

**What goes wrong:** The config key path `monitors.iija_sunset.fy26_end` contains a hardcoded fiscal year in the KEY NAME itself (not just the value). Making FY configurable requires either:
- Renaming the key (breaking change for anyone with a custom config)
- Keeping the old key name but having it mean something generic (confusing: `fy26_end` actually means `fy_end`)

**Prevention:** Rename to `fiscal_year_end` with the value `"2026-09-30"`, computed from the `fiscal_year` config. Add a deprecation check that reads `fy26_end` and warns if found (backward compatibility for one release).

**Severity:** MINOR -- config is internal, not user-facing at scale.

**Affected items:** FY26 configurability.

---

## Phase-Specific Warnings

| Tech Debt Item | Likely Pitfall | Severity | Mitigation |
|----------------|---------------|----------|------------|
| Circuit breaker on BaseScraper | C-1: Interferes with existing retry + 429 handling | CRITICAL | Place outside retry loop, exempt 429s, per-source breakers |
| Circuit breaker on BaseScraper | M-5: Batch run behavior when circuit opens | MODERATE | Degrade to cached data, short cooldown, summary report |
| Circuit breaker on BaseScraper | m-3: Sync vs async library choice | MINOR | Use async-native or implement custom |
| FY26 configurable | C-3: Partial migration leaves mixed-FY data | CRITICAL | Single source of truth, grep verification, derived values |
| FY26 configurable | m-5: Config key name contains "fy26" | MINOR | Rename key, deprecation warning |
| Hardcoded paths to config | C-4: CWD assumption breaks on different run directory | CRITICAL | PROJECT_ROOT anchor, resolve all paths against it |
| Hardcoded paths to config | M-6: Backslash paths in JSON config on Linux | MODERATE | Mandate forward slashes, normalize on read |
| Integration tests | M-2: Flaky CI from live API dependency | MODERATE | Separate workflow, structural assertions, skip markers |
| Integration tests | m-2: asyncio.run() inside running event loop | MINOR | Use pytest-asyncio with await, not asyncio.run() |
| Cache population | M-3: Schema-less caches cause silent data errors | MODERATE | Schema version, atomic writes, validation |
| Utility deduplication (CFDA) | M-1: Import dependencies and circular imports | MODERATE | Project-level constants.py, backward-compatible aliases |
| Utility deduplication (general) | M-4: Behavioral differences in "duplicate" code | MODERATE | Behavior comparison table before consolidating |
| Utility deduplication (tests) | m-1: Import paths change, tests break | MINOR | Re-export aliases, single-commit moves |
| Utility deduplication (tests) | m-4: Test count decrease | MINOR | Pre/post count verification |
| Logger naming | C-2: Breaks log filtering and monitoring | CRITICAL | Single convention, single commit, before/after diff |

---

## Cross-Cutting Concerns

### Regression Testing Strategy

Every tech debt item touches code that is already covered by 287 tests. The safest approach:

1. **One item per branch/PR.** Do not batch unrelated tech debt fixes. If the circuit breaker breaks something, you need to revert only the circuit breaker, not the circuit breaker + logger rename + FY26 config.
2. **Run full test suite after each atomic change.** Not after all changes. After EACH change.
3. **Smoke test the daily scan workflow.** After each PR merge, trigger `workflow_dispatch` on `daily-scan.yml` to verify the production pipeline still works.
4. **Do not change behavior and structure simultaneously.** If moving a constant to a new module, that commit should produce IDENTICAL behavior. The commit that changes behavior (e.g., making FY configurable) should be separate.

### Platform Parity Traps

| Risk | Windows (dev) | Linux (CI) | Detection |
|------|--------------|------------|-----------|
| Path separators in config JSON | Works with `\` | Fails with `\` | CI failure on any path test |
| `os.replace()` atomicity | NOT atomic cross-volume | Atomic same-filesystem | Tests with tmp_path are same-volume |
| `NamedTemporaryFile` `delete=False` | Required (file locking) | Optional but harmless | Already handled in docx_engine.py |
| `encoding` parameter | Locale-dependent default | Usually UTF-8 | Existing codebase already passes encoding="utf-8" |
| `asyncio.run()` | ProactorEventLoop (default) | SelectorEventLoop (default) | aiohttp works on both, but edge cases exist |

### Order of Operations Recommendation

Based on dependency analysis and risk assessment:

1. **Logger naming** (C-2) -- Zero functional impact, establishes consistent naming before other changes add new loggers.
2. **Utility deduplication** (M-1, M-4, m-1) -- Structural cleanup, no behavior change, reduces noise for subsequent diffs.
3. **FY26 configurable** (C-3, m-5) -- Data-level change, affects all modules, should be done before circuit breaker (which may add FY-dependent config).
4. **Hardcoded paths to config** (C-4, M-6) -- Infrastructure change, affects all modules, should be done while config is being touched for FY.
5. **Circuit breaker** (C-1, M-5, m-3) -- Highest-risk behavioral change, should be done last when all other structural changes are stable.
6. **Integration tests** (M-2, m-2) -- Additive only (new tests), does not change production code, can be done in parallel with anything.
7. **Cache population** (M-3) -- Additive functionality, depends on config paths being settled first.

---

## Sources

### Verified (HIGH confidence)
- Codebase inspection: `src/scrapers/base.py`, `src/main.py`, `src/scrapers/usaspending.py`, `src/scrapers/grants_gov.py`, `src/scrapers/congress_gov.py`, `src/scrapers/federal_register.py`, `src/reports/generator.py`, `src/packets/orchestrator.py`, `src/packets/docx_engine.py`, `src/packets/docx_styles.py`, `config/scanner_config.json`, `.github/workflows/daily-scan.yml`, `.github/workflows/generate-packets.yml`
- [Python logging documentation](https://docs.python.org/3/library/logging.html) -- logger hierarchy and `__name__` behavior
- [Python pathlib documentation](https://docs.python.org/3/library/pathlib.html) -- path separator normalization

### Partially verified (MEDIUM confidence)
- [aiobreaker (async circuit breaker for Python)](https://pypi.org/project/aiobreaker/) -- async-native circuit breaker library
- [aiomisc circuit breaker docs](https://aiomisc.readthedocs.io/en/latest/circuit_breaker.html) -- asyncio circuit breaker with configurable error ratios
- [pybreaker (Python circuit breaker)](https://pypi.org/project/pybreaker/) -- synchronous circuit breaker (not recommended for this codebase)
- [Nautobot logging issue #3160](https://github.com/nautobot/nautobot/issues/3160) -- real-world logger naming migration discussion
- [Python circular imports guide (DataCamp)](https://www.datacamp.com/tutorial/python-circular-import) -- circular dependency strategies
- [Circuit Breaker and Retry patterns (Atomic Object)](https://spin.atomicobject.com/retry-circuit-breaker-patterns/) -- layering retry and circuit breaker patterns

### Training data only (LOW confidence -- needs validation)
- Half-open state behavior for aiohttp with federal API 429 patterns (inferred from general circuit breaker docs, not tested against these specific APIs)
- Windows `os.replace()` atomicity behavior (known from POSIX specs, Windows behavior varies by filesystem)
- pytest-asyncio event loop nesting behavior (known pattern, version-dependent)
