---
phase: 11-api-resilience
plan: 02
subsystem: api
tags: [circuit-breaker, graceful-degradation, health-check, caching, aiohttp, resilience]

# Dependency graph
requires:
  - phase: 11-api-resilience (plan 01)
    provides: CircuitBreaker state machine, CircuitOpenError, config-driven resilience in BaseScraper
provides:
  - Per-source cache save/load with atomic writes for graceful degradation
  - CircuitOpenError and Exception fallback to cached data in run_scan
  - Cache staleness detection (WARNING + CRITICAL levels)
  - HealthChecker class probing all 4 federal APIs
  - "--health-check" CLI command with UP/DOWN/DEGRADED status
  - cache_max_age_hours config parameter (default 168h = 7 days)
affects: [14-integration, daily-scan workflow, operator monitoring]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-source cache: OUTPUTS_DIR/.cache_{source}.json with atomic write"
    - "Graceful degradation: CircuitOpenError -> cache fallback in async pipeline"
    - "Health probe: minimal single-result requests per API with 10s timeout"
    - "Degraded status: API down + cache exists = DEGRADED (not DOWN)"

key-files:
  created:
    - src/health.py
  modified:
    - src/main.py
    - config/scanner_config.json
    - tests/test_circuit_breaker.py

key-decisions:
  - "DEC-1102-01: Cache path uses dotfile convention (.cache_{source}.json) in OUTPUTS_DIR for gitignore compatibility"
  - "DEC-1102-02: 10MB file size cap on cache load prevents memory exhaustion from corrupted/bloated cache files"
  - "DEC-1102-03: Health probes use aiohttp directly (not BaseScraper) to avoid circuit breaker interference with diagnostics"
  - "DEC-1102-04: Async tests use asyncio.run() instead of pytest-asyncio to avoid adding a test dependency"

patterns-established:
  - "Cache fallback: try scan -> save on success -> catch CircuitOpenError/Exception -> load cache"
  - "Health status tri-state: UP (API responding), DOWN (unreachable + no cache), DEGRADED (unreachable + cache)"
  - "Staleness escalation: WARNING for any cached data use, CRITICAL when beyond configured max age"

# Metrics
duration: 19min
completed: 2026-02-11
---

# Phase 11 Plan 02: Graceful Degradation + Health Check Summary

**Per-source caching with CircuitOpenError fallback in run_scan, HealthChecker probing all 4 federal APIs, and --health-check CLI command reporting UP/DOWN/DEGRADED per source**

## Performance

- **Duration:** 19 min
- **Started:** 2026-02-11T14:39:43Z
- **Completed:** 2026-02-11T14:58:58Z
- **Tasks:** 2/2
- **Files created:** 1 (src/health.py)
- **Files modified:** 3 (src/main.py, config/scanner_config.json, tests/test_circuit_breaker.py)

## Accomplishments

- Pipeline continues producing reports even when 1+ APIs are unreachable (uses cached data)
- Per-source cache files saved atomically on every successful scan with timestamp metadata
- CircuitOpenError and general Exception both fall back to cached data (not empty lists)
- Cache staleness logged at WARNING level; CRITICAL when beyond configurable max age (168h default)
- HealthChecker probes all 4 federal APIs with minimal 1-result requests
- Health check reports DEGRADED (not DOWN) when API is unreachable but cached data exists
- `--health-check` CLI command prints formatted status table for operator monitoring
- 14 new tests (8 cache + 6 health) bringing test_circuit_breaker.py to 34 total

## Task Commits

Each task was committed atomically:

1. **Task 1: Add per-source cache and graceful degradation to run_scan** - `a7e7a2a` (feat)
2. **Task 2: Create HealthChecker and --health-check CLI command** - `434c4df` (feat)

## Files Created/Modified

- `src/health.py` - HealthChecker class with probe definitions for all 4 APIs, format_report() for console output
- `src/main.py` - _source_cache_path(), _save_source_cache(), _load_source_cache(), CircuitOpenError fallback in run_scan, --health-check CLI handler
- `config/scanner_config.json` - cache_max_age_hours: 168 added to resilience section
- `tests/test_circuit_breaker.py` - 14 new tests: TestSourceCache (8) + TestHealthChecker (6)

## Decisions Made

- **DEC-1102-01:** Cache files use dotfile convention (`.cache_{source}.json`) in OUTPUTS_DIR, consistent with existing `.ci_history.json` and `.cfda_tracker.json` patterns
- **DEC-1102-02:** 10MB file size cap on cache load before JSON parsing prevents memory exhaustion from corrupted/bloated files (security pattern from MEMORY.md)
- **DEC-1102-03:** Health probes use aiohttp directly rather than BaseScraper to avoid circuit breaker interference with diagnostic probes
- **DEC-1102-04:** Async health check tests use `asyncio.run()` instead of `@pytest.mark.asyncio` to avoid adding pytest-asyncio as a dependency (Rule 3 - Blocking deviation)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed pytest-asyncio dependency for async tests**
- **Found during:** Task 2 (health check tests)
- **Issue:** Plan specified `@pytest.mark.asyncio` decorators but pytest-asyncio is not installed
- **Fix:** Rewrote async tests to use `asyncio.run()` instead, which works without additional dependencies
- **Files modified:** tests/test_circuit_breaker.py
- **Verification:** All 6 health tests pass
- **Committed in:** `434c4df` (Task 2 commit)

**2. [Rule 1 - Bug] Fixed unused import lint violation**
- **Found during:** Post-Task 2 verification
- **Issue:** `import pytest` was unused after removing `@pytest.mark.asyncio` decorators, causing ruff F401 violation
- **Fix:** Removed unused import
- **Files modified:** tests/test_circuit_breaker.py
- **Committed in:** Folded into concurrent agent commit (minor fix)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both fixes necessary for correctness. No scope creep. All functionality delivered as specified.

## Issues Encountered

- Concurrent agent (12-01) committed between Task 2 commit and lint fix amend, causing the amend to modify the wrong commit. The lint fix (removing unused `import pytest`) was absorbed into the 12-01 commit. Functional impact: zero. All tests pass.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **Phase 11 COMPLETE:** All 4 RESL requirements delivered (circuit breaker, config-driven resilience, graceful degradation, health check)
- **Phase 14 (Integration):** Can now test end-to-end pipeline resilience with `--health-check` and simulated API failures
- **Operator monitoring:** `python -m src.main --health-check` available for daily-scan.yml pre-flight checks
- **No blockers** for Phase 12 (Award Population) or Phase 13 (Hazard Population)

---
*Phase: 11-api-resilience*
*Completed: 2026-02-11*
