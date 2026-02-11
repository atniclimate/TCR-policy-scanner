# Phase 11: API Resilience - Research

**Researched:** 2026-02-11
**Domain:** Circuit breaker pattern, retry/backoff, graceful degradation for async HTTP scrapers
**Confidence:** HIGH

## Summary

Phase 11 adds circuit breaker protection around all 4 external API calls (federal_register, grants_gov, congress_gov, usaspending), configurable retry/backoff, graceful degradation to cached data, and a health check command. The codebase already has a solid foundation: `BaseScraper._request_with_retry()` handles exponential backoff with jitter and rate-limit awareness, `ChangeDetector` persists scan results to `LATEST-RESULTS.json`, and `run_scan()` in `main.py` already catches per-scraper exceptions (returning empty lists on failure). The gap is that there is no circuit breaker state machine, no per-source cached fallback during live scans, retry parameters are hardcoded constants, and there is no health check CLI command.

The recommended approach is to implement a lightweight custom `CircuitBreaker` class (approximately 80-120 lines) in a new `src/scrapers/circuit_breaker.py` module, integrate it into `BaseScraper`, move retry/backoff constants into `scanner_config.json`, add per-source cache loading on circuit-open fallback, and add a `--health-check` CLI command. This avoids adding a new dependency for what amounts to a simple state machine with three states.

**Primary recommendation:** Build a custom async-native `CircuitBreaker` class integrated into `BaseScraper` rather than adding a third-party library. The circuit breaker is approximately 80-120 lines of Python, perfectly matched to the existing architecture, and avoids dependency risk from unmaintained packages.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| aiohttp | >=3.9.0 | Async HTTP client (already in use) | Already the HTTP layer for all scrapers |
| Python stdlib `asyncio` | 3.12 | Async coordination, locks | Already used throughout, no new dep needed |
| Python stdlib `enum` | 3.12 | Circuit breaker state enum | Clean state representation |
| Python stdlib `time` | 3.12 | Monotonic clock for timeouts | Immune to wall-clock adjustments |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `json` (stdlib) | 3.12 | Config loading, cache persistence | Already used everywhere |
| `logging` (stdlib) | 3.12 | State transition logging | Already used via `__name__` pattern |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom circuit breaker | `circuitbreaker` 2.1.3 (PyPI) | Clean decorator API, async support, but 1 new dependency for ~100 LOC of custom code. Last release March 2025. |
| Custom circuit breaker | `aiobreaker` 1.2.0 (PyPI) | Native asyncio fork of pybreaker, but **inactive since May 2021**. Risky for a production pipeline. |
| Custom circuit breaker | `pybreaker` 1.4.1 (PyPI) | Actively maintained (Sep 2025), but **no native asyncio support** -- only Tornado async. Would require wrapping. Requires Python 3.10+. |
| Custom circuit breaker | `tenacity` circuit breaker combo | Tenacity handles retries excellently but is a retry library, not a circuit breaker. Would still need circuit breaker state machine. |

**Why custom wins:** The project already has `BaseScraper._request_with_retry()` with exponential backoff, jitter, and rate-limit handling. A circuit breaker is a simple state machine (3 states, 4 transitions, 1 timer). Adding a third-party library for this introduces dependency risk without meaningful complexity reduction. The custom implementation integrates cleanly into the existing `BaseScraper` class hierarchy and can be tested with 100% coverage using deterministic time controls.

**No new pip dependencies required.**

## Architecture Patterns

### Recommended Project Structure
```
src/scrapers/
    __init__.py
    base.py              # Modified: uses CircuitBreaker, reads config for retry params
    circuit_breaker.py   # NEW: CircuitBreaker class + CircuitState enum
    federal_register.py  # Unchanged
    grants_gov.py        # Unchanged
    congress_gov.py      # Unchanged
    usaspending.py       # Unchanged
src/
    main.py              # Modified: add --health-check command, cache fallback in run_scan
    health.py            # NEW: HealthChecker class for --health-check CLI
config/
    scanner_config.json  # Modified: add resilience section
tests/
    test_circuit_breaker.py  # NEW: 15+ tests for state transitions + degradation
```

### Pattern 1: Circuit Breaker State Machine
**What:** A class that tracks CLOSED/OPEN/HALF_OPEN state per API source, transitions on failure thresholds, and auto-recovers via half-open probe.
**When to use:** Wraps every external API call in `BaseScraper._request_with_retry()`.
**Example:**
```python
# Source: Custom implementation based on Nygard's "Release It!" pattern
import enum
import time
import logging

logger = logging.getLogger(__name__)

class CircuitState(enum.Enum):
    CLOSED = "CLOSED"         # Normal operation, requests pass through
    OPEN = "OPEN"             # Tripped, all requests fail fast
    HALF_OPEN = "HALF_OPEN"   # Probing: one request allowed to test recovery

class CircuitBreaker:
    """Async-compatible circuit breaker for external API calls.

    State transitions:
        CLOSED -> OPEN:       failure_count >= failure_threshold
        OPEN -> HALF_OPEN:    recovery_timeout elapsed
        HALF_OPEN -> CLOSED:  probe request succeeds
        HALF_OPEN -> OPEN:    probe request fails
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._success_count = 0

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                logger.info("%s circuit breaker -> HALF_OPEN (probing)", self.name)
        return self._state

    def record_success(self) -> None:
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED
            logger.info("%s circuit breaker -> CLOSED (recovered)", self.name)
        self._failure_count = 0

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            logger.warning("%s circuit breaker -> OPEN (probe failed)", self.name)
        elif self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                "%s circuit breaker -> OPEN (%d failures)",
                self.name, self._failure_count,
            )

    @property
    def is_call_permitted(self) -> bool:
        return self.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN)
```

### Pattern 2: Config-Driven Retry Parameters
**What:** Move hardcoded `MAX_RETRIES = 3` and `BACKOFF_BASE = 2` from `base.py` into `scanner_config.json` under a `resilience` section, loaded at scraper init time.
**When to use:** At `BaseScraper.__init__()` time.
**Example:**
```python
# In scanner_config.json:
{
  "resilience": {
    "max_retries": 3,
    "backoff_base": 2,
    "backoff_max": 300,
    "request_timeout": 30,
    "circuit_breaker": {
      "failure_threshold": 5,
      "recovery_timeout": 60
    }
  }
}

# In base.py:
class BaseScraper:
    def __init__(self, source_name: str, config: dict | None = None):
        self.source_name = source_name
        self._headers = {"User-Agent": USER_AGENT}
        resilience = (config or {}).get("resilience", {})
        self.max_retries = resilience.get("max_retries", MAX_RETRIES)
        self.backoff_base = resilience.get("backoff_base", BACKOFF_BASE)
        self.backoff_max = resilience.get("backoff_max", 300)
        self.request_timeout = aiohttp.ClientTimeout(
            total=resilience.get("request_timeout", 30)
        )
        cb_config = resilience.get("circuit_breaker", {})
        self._circuit_breaker = CircuitBreaker(
            name=source_name,
            failure_threshold=cb_config.get("failure_threshold", 5),
            recovery_timeout=cb_config.get("recovery_timeout", 60),
        )
```

### Pattern 3: Graceful Degradation to Cached Data
**What:** When a circuit breaker is OPEN and no API calls can be made, fall back to the most recent cached scan results for that source. The pipeline continues with potentially stale data and logs a degradation warning.
**When to use:** In `run_scan()` in `main.py` when a scraper raises `CircuitOpenError` or returns empty results due to circuit breaker.
**Example:**
```python
# In main.py run_scan():
async def _run_one(source_name: str) -> list[dict]:
    scraper = SCRAPERS[source_name](config)
    try:
        items = await scraper.scan()
        if items:
            _save_source_cache(source_name, items)  # per-source cache
        return items
    except CircuitOpenError:
        logger.warning("DEGRADED: %s circuit open, using cached data", source_name)
        return _load_source_cache(source_name)
    except Exception:
        logger.exception("Failed to scan %s, using cached data", source_name)
        return _load_source_cache(source_name)
```

### Pattern 4: Health Check Command
**What:** A `--health-check` CLI command that probes each API endpoint with a lightweight request and reports UP/DOWN/DEGRADED status per source.
**When to use:** As a pre-flight check or monitoring probe.
**Example:**
```python
# src/health.py
class HealthChecker:
    """Probes each API source and reports availability."""

    PROBES = {
        "federal_register": {
            "url": "https://www.federalregister.gov/api/v1/documents.json?per_page=1",
            "method": "GET",
        },
        "grants_gov": {
            "url": "https://api.grants.gov/v1/api/search2",
            "method": "POST",
            "json": {"keyword": "test", "rows": 1},
        },
        "congress_gov": {
            "url": "https://api.congress.gov/v3/bill?limit=1",
            "method": "GET",
            "requires_key": True,
        },
        "usaspending": {
            "url": "https://api.usaspending.gov/api/v2/search/spending_by_award/",
            "method": "POST",
            "json": {"filters": {"award_type_codes": ["02"]}, "limit": 1},
        },
    }

    async def check_all(self) -> dict[str, str]:
        results = {}
        for source, probe in self.PROBES.items():
            status = await self._probe(source, probe)
            results[source] = status
        return results
```

### Anti-Patterns to Avoid
- **Global circuit breaker shared across sources:** Each API source MUST have its own circuit breaker instance. A failure in grants.gov should not trip the circuit for federal_register.
- **Circuit breaker wrapping individual retry attempts:** The circuit breaker should wrap the entire `_request_with_retry()` call, not individual HTTP attempts within it. Retries happen inside CLOSED state; the breaker trips when all retries are exhausted.
- **Time-based recovery using wall clock (`datetime.now`):** Use `time.monotonic()` which is immune to system clock changes (NTP adjustments, DST).
- **Forgetting to record success:** Every successful API call must call `record_success()` to reset the failure counter and transition HALF_OPEN -> CLOSED.
- **Testing with real sleep:** Use dependency injection for time source and sleep function in tests.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Retry with backoff | New retry framework | Existing `_request_with_retry()` in `base.py` | Already handles exponential backoff, jitter, rate limiting (429), method validation. Just make it configurable. |
| Per-source caching | New caching framework | JSON file per source in `outputs/` (same pattern as `LATEST-RESULTS.json`) | Consistent with existing cache patterns, atomic writes already established |
| Config schema validation | Runtime type checking | Pydantic models (already a dependency) | Can validate `resilience` config section with `BaseModel` |
| Health check HTTP probes | Custom HTTP client | Existing `BaseScraper._request_with_retry()` | Already handles timeouts, retries, user-agent |

**Key insight:** The project already has 80% of the resilience infrastructure in `BaseScraper`. This phase is about adding the circuit breaker state machine on top of what exists, making existing parameters configurable, and adding the cache-fallback + health-check features.

## Common Pitfalls

### Pitfall 1: Circuit Breaker Granularity
**What goes wrong:** Using one circuit breaker for all APIs or one per HTTP request instead of one per API source.
**Why it happens:** Confusion about what constitutes an "integration point."
**How to avoid:** One `CircuitBreaker` instance per source name (4 total: federal_register, grants_gov, congress_gov, usaspending). Each scraper creates its own breaker in `__init__`.
**Warning signs:** All scrapers failing when only one API is down.

### Pitfall 2: Race Conditions in State Transitions
**What goes wrong:** Multiple concurrent requests reading stale circuit state, causing thundering herd on half-open recovery.
**Why it happens:** The 4 scrapers run concurrently via `asyncio.gather()` in `run_scan()`. Within a single scraper, multiple search queries run sequentially with `asyncio.sleep()` between them.
**How to avoid:** Since each scraper has its own circuit breaker AND Python's GIL prevents true concurrency within a single event loop, race conditions are not a practical concern for this codebase. Document this assumption. If the codebase later adds multi-threaded scraping, add `asyncio.Lock` to state transitions.
**Warning signs:** Multiple probe requests during HALF_OPEN state.

### Pitfall 3: Stale Cache Masking API Issues
**What goes wrong:** Pipeline silently serves weeks-old cached data because the circuit stays open and nobody notices.
**Why it happens:** Graceful degradation is too graceful -- it works so well that nobody checks the health status.
**How to avoid:** Log a WARNING-level message every time cached data is served. Include cache age in the degradation warning. The health check command should report cache age per source.
**Warning signs:** Scan results never change between runs.

### Pitfall 4: Config Backward Compatibility
**What goes wrong:** Existing `scanner_config.json` files without the new `resilience` section cause crashes.
**Why it happens:** Config loading assumes the section exists.
**How to avoid:** Every config read uses `.get("resilience", {})` with sensible defaults matching the current hardcoded values (`MAX_RETRIES=3`, `BACKOFF_BASE=2`, etc.). The absence of the `resilience` section should produce identical behavior to the current code.
**Warning signs:** Tests that create config dicts without the resilience section failing.

### Pitfall 5: BaseScraper Constructor Signature Change
**What goes wrong:** All 4 scraper subclasses need to pass `config` to `BaseScraper.__init__()` but currently only pass `source_name`.
**Why it happens:** `BaseScraper.__init__(source_name)` does not accept config. Subclasses store config locally but do not pass it up.
**How to avoid:** Add `config: dict | None = None` as an optional parameter to `BaseScraper.__init__()`. Update all 4 subclass `__init__` methods to pass config up: `super().__init__("federal_register", config=config)`. The default `None` preserves backward compatibility for any code constructing `BaseScraper` directly.
**Warning signs:** `TypeError: __init__() got an unexpected keyword argument 'config'` in tests.

### Pitfall 6: Testing Circuit Breaker Timing
**What goes wrong:** Tests that depend on `time.sleep()` or `time.monotonic()` are slow and flaky.
**Why it happens:** Real-time dependencies in state transitions.
**How to avoid:** Inject a `clock` callable (defaulting to `time.monotonic`) into `CircuitBreaker.__init__()`. In tests, use a mock clock that can be advanced deterministically. This makes tests instant and reliable.
**Warning signs:** Tests that take >1 second each or that occasionally fail in CI.

## Code Examples

Verified patterns from the existing codebase and official documentation:

### Integrating Circuit Breaker into _request_with_retry
```python
# Modified base.py - wrapping the existing retry logic with circuit breaker
async def _request_with_retry(
    self, session: aiohttp.ClientSession, method: str, url: str,
    retries: int | None = None, **kwargs,
) -> dict:
    """Make HTTP request with circuit breaker + exponential backoff."""
    retries = retries if retries is not None else self.max_retries

    if not self._circuit_breaker.is_call_permitted:
        raise CircuitOpenError(
            f"{self.source_name}: circuit breaker OPEN, refusing request"
        )

    try:
        result = await self._do_request(session, method, url, retries, **kwargs)
        self._circuit_breaker.record_success()
        return result
    except Exception as e:
        self._circuit_breaker.record_failure()
        raise
```

### Per-Source Cache for Degradation Fallback
```python
# Source cache lives alongside LATEST-RESULTS.json
from src.paths import OUTPUTS_DIR

def _source_cache_path(source_name: str) -> Path:
    return OUTPUTS_DIR / f".cache_{source_name}.json"

def _save_source_cache(source_name: str, items: list[dict]) -> None:
    path = _source_cache_path(source_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({
            "source": source_name,
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "items": items,
        }, f, indent=2, default=str)
    tmp.replace(path)

def _load_source_cache(source_name: str) -> list[dict]:
    path = _source_cache_path(source_name)
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        cached_at = data.get("cached_at", "unknown")
        logger.warning(
            "DEGRADED: %s using cached data from %s", source_name, cached_at
        )
        return data.get("items", [])
    except (json.JSONDecodeError, IOError):
        return []
```

### Health Check Output Format
```python
# Example output from --health-check command:
# API Health Check
# ────────────────────────────────────
# federal_register:  UP       (237ms)
# grants_gov:        UP       (412ms)
# congress_gov:      DOWN     (timeout after 30s)
# usaspending:       DEGRADED (cached data from 2026-02-10T14:30:00Z)
```

### Test Pattern: Deterministic Circuit Breaker Testing
```python
# Source: Custom pattern for testability
import pytest

class MockClock:
    """Deterministic clock for circuit breaker tests."""
    def __init__(self, start: float = 0.0):
        self._now = start
    def __call__(self) -> float:
        return self._now
    def advance(self, seconds: float) -> None:
        self._now += seconds

def test_circuit_opens_after_threshold():
    clock = MockClock()
    cb = CircuitBreaker("test", failure_threshold=3, recovery_timeout=60, clock=clock)
    assert cb.state == CircuitState.CLOSED

    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED  # 2 < threshold

    cb.record_failure()
    assert cb.state == CircuitState.OPEN  # 3 >= threshold

def test_half_open_after_timeout():
    clock = MockClock()
    cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=30, clock=clock)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.OPEN

    clock.advance(29)
    assert cb.state == CircuitState.OPEN  # not yet

    clock.advance(2)
    assert cb.state == CircuitState.HALF_OPEN  # 31 >= 30
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Global retry constants | Config-driven resilience parameters | This phase | Operators can tune per-environment |
| Silent empty-list on scraper failure | Circuit breaker + cached fallback + logged degradation | This phase | Pipeline never silently loses data |
| No health visibility | `--health-check` CLI command | This phase | Operators can pre-flight and monitor |
| aiobreaker (asyncio CB library) | Custom lightweight CB | aiobreaker inactive since 2021 | No dead dependency risk |
| pybreaker (maintained CB library) | Custom lightweight CB | pybreaker lacks native asyncio | Avoids Tornado wrapping overhead |

**Deprecated/outdated:**
- `aiobreaker`: Last release May 2021, inactive. Do not use.
- `pybreaker` for async: Only supports Tornado `gen.coroutine`, not native `async/await`. Requires Python 3.10+.

## Open Questions

Things that couldn't be fully resolved:

1. **Per-source vs per-endpoint circuit breakers**
   - What we know: Each source has multiple endpoints (e.g., grants_gov has CFDA search + keyword search). A failure in one endpoint likely means the entire API is down.
   - What's unclear: Should the circuit breaker be per-source (1 for all grants_gov endpoints) or per-endpoint?
   - Recommendation: Start with per-source (4 circuit breakers total). This is simpler and matches the typical failure mode (entire API down, not individual endpoint down). Can be refined later if endpoint-level granularity proves necessary.

2. **Circuit breaker persistence across process restarts**
   - What we know: The circuit breaker state lives in memory. If the scanner process restarts, all breakers reset to CLOSED.
   - What's unclear: Should breaker state survive restarts to avoid hammering a known-down API?
   - Recommendation: Do NOT persist breaker state. The scanner is a batch process (runs, finishes, exits). Each run should start fresh with CLOSED breakers. The retry + backoff logic provides sufficient protection during a single run. If an API was down last run, the cached data fallback handles it.

3. **Health check probe depth**
   - What we know: We need to report UP/DOWN/DEGRADED for each source.
   - What's unclear: Should the health check do a full search query or a minimal probe? Should it check API key validity for congress_gov?
   - Recommendation: Minimal probe (1 result per source). Report DEGRADED when only cached data is available. For congress_gov, verify the API key is set and the endpoint responds with a 200.

4. **Cache staleness threshold**
   - What we know: The config already has `scan_window_days: 14` for how far back to search.
   - What's unclear: At what age should cached data be considered too stale to use?
   - Recommendation: Add a `cache_max_age_hours` config option (default: 168 = 7 days). If cached data is older than this, still use it but upgrade the warning to CRITICAL. Never refuse to serve data -- stale is better than empty for Tribal advocacy packets.

## Sources

### Primary (HIGH confidence)
- Context7 `/websites/tenacity_readthedocs_io_en` - Queried for async retry patterns, exponential backoff, jitter strategies
- Existing codebase: `src/scrapers/base.py` (lines 1-103) - Current retry implementation
- Existing codebase: `src/main.py` (lines 123-145) - Current scraper orchestration
- Existing codebase: `config/scanner_config.json` - Current config structure
- Existing codebase: `src/analysis/change_detector.py` - Existing cache pattern
- [circuitbreaker 2.1.3 on GitHub](https://github.com/fabfuel/circuitbreaker) - API reference for async decorator pattern

### Secondary (MEDIUM confidence)
- [pybreaker 1.4.1 on PyPI](https://pypi.org/project/pybreaker/) - Verified active maintenance (Sep 2025), confirmed Tornado-only async
- [aiobreaker 1.2.0 on PyPI](https://pypi.org/project/aiobreaker/) - Confirmed inactive since May 2021
- [circuitbreaker 2.1.3 on PyPI](https://pypi.org/project/circuitbreaker/) - Confirmed async support, last release March 2025

### Tertiary (LOW confidence)
- General web search results for Python circuit breaker patterns and comparisons

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - No new dependencies; using stdlib + existing aiohttp. Verified all library statuses via PyPI.
- Architecture: HIGH - Patterns based on direct codebase analysis of existing `BaseScraper`, `run_scan()`, `ChangeDetector`, and config structure. Circuit breaker state machine is well-defined (Nygard's pattern).
- Pitfalls: HIGH - Identified from direct code analysis (constructor signatures, config backward compat, cache staleness) and established engineering patterns (monotonic clock, testability).

**Research date:** 2026-02-11
**Valid until:** 2026-03-11 (stable domain, no fast-moving dependencies)
