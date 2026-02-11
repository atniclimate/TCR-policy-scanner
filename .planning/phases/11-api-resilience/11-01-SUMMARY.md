---
phase: 11-api-resilience
plan: 01
subsystem: api
tags: [circuit-breaker, resilience, retry, backoff, aiohttp, state-machine]

# Dependency graph
requires:
  - phase: 10-code-quality
    provides: ruff-clean codebase, consistent logger naming, centralized config
provides:
  - CircuitBreaker class with CLOSED/OPEN/HALF_OPEN 3-state machine
  - CircuitOpenError exception for fail-fast on downed APIs
  - Config-driven retry/backoff/timeout parameters in BaseScraper
  - scanner_config.json resilience section with documented defaults
affects: [11-02 (rate limiter builds on circuit breaker), 12-award-population, 13-hazard-population, 14-integration]

# Tech tracking
tech-stack:
  added: []
  patterns: [circuit-breaker state machine, injectable clock for deterministic testing, config-driven resilience parameters]

key-files:
  created:
    - src/scrapers/circuit_breaker.py
    - tests/test_circuit_breaker.py
  modified:
    - src/scrapers/base.py
    - src/scrapers/federal_register.py
    - src/scrapers/grants_gov.py
    - src/scrapers/congress_gov.py
    - src/scrapers/usaspending.py
    - config/scanner_config.json

key-decisions:
  - "DEC-1101-01: Circuit breaker wraps entire retry loop, not individual attempts (trips only when ALL retries exhausted)"
  - "DEC-1101-02: Injectable clock parameter defaults to time.monotonic, enabling zero-sleep deterministic tests"
  - "DEC-1101-03: Module-level constants (MAX_RETRIES, BACKOFF_BASE, DEFAULT_TIMEOUT) preserved as defaults for backward compatibility"
  - "DEC-1101-04: retries parameter in _request_with_retry changed to None default (falls through to self.max_retries)"

patterns-established:
  - "Circuit breaker: CircuitBreaker(name, failure_threshold, recovery_timeout, clock) with record_success/record_failure"
  - "Config-driven resilience: config['resilience'] dict passed through scraper constructors to BaseScraper"
  - "Deterministic timing tests: MockClock class with advance() method, no real sleeps"

# Metrics
duration: 5min
completed: 2026-02-11
---

# Phase 11 Plan 01: Circuit Breaker + Configurable Resilience Summary

**3-state circuit breaker (CLOSED/OPEN/HALF_OPEN) integrated into BaseScraper with config-driven retry/backoff and 20 tests covering all transitions**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-11T14:31:28Z
- **Completed:** 2026-02-11T14:36:17Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- CircuitBreaker class implementing all 4 state transitions with injectable clock for deterministic testing
- BaseScraper reads max_retries, backoff_base, backoff_max, request_timeout, and circuit_breaker config from scanner_config.json
- All 4 scraper subclasses pass config through to BaseScraper (zero behavior change when config absent)
- 20 tests (16 state machine + 4 integration) with 100% transition coverage and zero real sleeps

## Task Commits

Each task was committed atomically:

1. **Task 1: Create circuit_breaker.py with CircuitBreaker class + tests** - `59f00f7` (feat: TDD red/green cycle)
2. **Task 2: Integrate circuit breaker into BaseScraper + config** - `78efbc3` (feat: integration + config)

**Plan metadata:** (pending)

_Note: Task 1 used TDD -- tests written first (RED: import fails), then implementation (GREEN: 16 pass)._

## Files Created/Modified
- `src/scrapers/circuit_breaker.py` - CircuitBreaker class, CircuitState enum, CircuitOpenError exception (145 lines)
- `tests/test_circuit_breaker.py` - 20 tests: 16 state machine unit tests + 4 BaseScraper integration tests (220 lines)
- `src/scrapers/base.py` - Added config parameter, circuit breaker import/init, fail-fast check, success/failure recording
- `src/scrapers/federal_register.py` - Pass config to super().__init__
- `src/scrapers/grants_gov.py` - Pass config to super().__init__
- `src/scrapers/congress_gov.py` - Pass config to super().__init__
- `src/scrapers/usaspending.py` - Pass config to super().__init__
- `config/scanner_config.json` - Added resilience section with retry/backoff/circuit-breaker defaults

## Decisions Made

1. **DEC-1101-01: Circuit breaker wraps entire retry loop** -- The breaker checks once at entry and records outcome after all retries exhaust. This matches the research recommendation: "retries happen inside CLOSED state; the breaker trips when all retries are exhausted." Individual transient failures don't trip the breaker.

2. **DEC-1101-02: Injectable clock for testing** -- CircuitBreaker accepts an optional `clock` callable (defaults to `time.monotonic`). Tests use a `MockClock` with `advance()` for deterministic timing without real sleeps. This is the standard pattern for time-dependent state machines.

3. **DEC-1101-03: Module-level constants preserved** -- `MAX_RETRIES`, `BACKOFF_BASE`, `DEFAULT_TIMEOUT` kept as module-level constants. They serve as defaults when `BaseScraper.__init__` receives no config. Full backward compatibility.

4. **DEC-1101-04: retries parameter default changed to None** -- `_request_with_retry(retries=None)` falls through to `self.max_retries` (config-driven). This avoids the Python default-argument gotcha where `retries=MAX_RETRIES` would capture the module constant at import time.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Circuit breaker and configurable resilience are ready for plan 11-02 (rate limiter / health endpoint)
- All 403 tests pass (383 existing + 20 new), zero regressions
- RESL-01 (circuit breaker pattern) and RESL-02 (configurable retry/backoff) are satisfied

---
*Phase: 11-api-resilience*
*Completed: 2026-02-11*
