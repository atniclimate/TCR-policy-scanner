# Technology Stack: Tech Debt Cleanup

**Project:** TCR Policy Scanner v1.2
**Researched:** 2026-02-11
**Scope:** Patterns, libraries, and tools for 5 tech debt cleanup areas
**Confidence:** HIGH (verified against PyPI, official docs, codebase analysis)

---

## Existing Stack (DO NOT CHANGE)

Already validated across v1.0 and v1.1 -- listed for integration context:

| Technology | Version | Role |
|---|---|---|
| Python | 3.12 | Runtime |
| aiohttp | >=3.9.0 | Async HTTP client (BaseScraper pattern) |
| python-dateutil | >=2.8.0 | Date parsing |
| jinja2 | >=3.1.0 | Template rendering |
| pytest | (dev) | Test framework |
| python-docx | >=1.1.0 | DOCX generation |
| rapidfuzz | >=3.14.0 | Fuzzy name matching |
| openpyxl | >=3.1.0 | XLSX parsing (USFS data) |
| pyyaml | >=6.0.0 | YAML support |

---

## Debt Area 1: Circuit-Breaker for Async Scrapers

### Current State

`BaseScraper._request_with_retry()` (src/scrapers/base.py) implements exponential backoff with jitter and 429-aware retry. However, there is **no circuit-breaker** -- if an API is fully down, all 4 scrapers hammer it through all retries on every CFDA/query combination before moving on.

Concrete impact: USASpending scraper iterates 12 CFDAs. If the API is down, that is `12 x 3 retries x exponential backoff` = ~3-5 minutes of wasted time hitting a dead endpoint, per scraper invocation.

### Recommendation: Hand-Roll a Minimal Circuit Breaker

**Do NOT add a library.** Here is why:

| Library | Version | Async Support | Problem |
|---|---|---|---|
| circuitbreaker | 2.1.3 | Yes (decorator) | Only classifies Python 3.8-3.10; trivial to implement without it |
| pybreaker | 1.4.1 | Tornado only, NO asyncio | Incompatible with aiohttp async/await |
| aiobreaker | 1.1.0 | Yes (asyncio) | Last release unknown date; low maintenance signal |

**Rationale:** The project has exactly 4 scrapers with a shared `BaseScraper`. A circuit breaker needs ~30 lines of code: a failure counter, a state enum (CLOSED/OPEN/HALF_OPEN), and a reset timeout. Adding a library dependency for this is over-engineering.

### Implementation Pattern

```python
from enum import Enum
from datetime import datetime, timezone, timedelta

class CircuitState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Rejecting calls
    HALF_OPEN = "half_open" # Testing one call

class CircuitBreaker:
    """Per-source circuit breaker for BaseScraper.

    Opens after `fail_threshold` consecutive failures.
    Resets after `reset_timeout` seconds.
    """

    def __init__(self, fail_threshold: int = 5, reset_timeout: int = 60):
        self.fail_threshold = fail_threshold
        self.reset_timeout = timedelta(seconds=reset_timeout)
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure: datetime | None = None

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if self._last_failure and (
                datetime.now(timezone.utc) - self._last_failure > self.reset_timeout
            ):
                self._state = CircuitState.HALF_OPEN
        return self._state

    def record_success(self) -> None:
        self._failure_count = 0
        self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure = datetime.now(timezone.utc)
        if self._failure_count >= self.fail_threshold:
            self._state = CircuitState.OPEN

    @property
    def allow_request(self) -> bool:
        s = self.state
        return s in (CircuitState.CLOSED, CircuitState.HALF_OPEN)
```

### Integration Points

- Add a `CircuitBreaker` instance per scraper source (4 total) inside `BaseScraper.__init__`
- Check `self._breaker.allow_request` before `_request_with_retry()`
- Call `record_success()`/`record_failure()` based on outcome
- When circuit is OPEN, immediately return empty results with a WARNING log
- `fail_threshold=5` and `reset_timeout=60` are sane defaults for federal APIs

### Confidence: HIGH

This pattern is well-established. No library needed. The existing `_request_with_retry` already handles per-request resilience; the circuit breaker adds per-source resilience.

---

## Debt Area 2: Dynamic Fiscal Year Configuration

### Current State

FY26 is hardcoded in multiple locations:

| File | What is Hardcoded | Impact |
|---|---|---|
| `src/scrapers/usaspending.py:68` | `"start_date": "2025-10-01", "end_date": "2026-09-30"` | USASpending queries only FY26 |
| `src/packets/docx_sections.py:55` | `"FY26 Climate Resilience Program Priorities"` | Cover page title |
| `src/scrapers/usaspending.py:217` | `f"FY26 Obligation: ..."` | Normalized item titles |
| `src/monitors/iija_sunset.py:53` | `monitor_config.get("fy26_end", "2026-09-30")` | Already config-driven (good) |
| `config/scanner_config.json:118` | `"fy26_end": "2026-09-30"` | Only used by IIJA monitor |

### Recommendation: Config-Driven FY with Utility Functions

**Do NOT add the `fiscalyear` library.** The US federal fiscal year is dead simple: FY starts Oct 1 of the prior calendar year, ends Sep 30. The project needs a function, not a library.

### Implementation Pattern

Add to `scanner_config.json`:

```json
{
  "fiscal_year": {
    "current": 2026,
    "label": "FY26",
    "start_date": "2025-10-01",
    "end_date": "2026-09-30"
  }
}
```

Add a utility module `src/fiscal.py` (~20 lines):

```python
"""Fiscal year utilities.

US federal fiscal year: Oct 1 (prior CY) through Sep 30.
All FY values flow from scanner_config.json["fiscal_year"]["current"].
"""

from datetime import date


def fy_start(fy: int) -> str:
    """Return FY start date as ISO string (YYYY-MM-DD)."""
    return f"{fy - 1}-10-01"


def fy_end(fy: int) -> str:
    """Return FY end date as ISO string (YYYY-MM-DD)."""
    return f"{fy}-09-30"


def fy_label(fy: int) -> str:
    """Return human-readable FY label (e.g., 'FY26')."""
    return f"FY{fy % 100}"


def current_fy() -> int:
    """Determine the current federal fiscal year from today's date.

    Oct-Dec of year N = FY(N+1). Jan-Sep of year N = FY(N).
    Example: Oct 2025 = FY26, Feb 2026 = FY26, Oct 2026 = FY27.
    """
    today = date.today()
    return today.year + 1 if today.month >= 10 else today.year
```

**Important note on auto-detection:** An auto-detect `current_fy()` function is useful for development but the config value should be authoritative. The scanner is a policy tool -- you do NOT want it to silently roll to FY27 on October 1st without human review. The config `fiscal_year.current` is intentionally explicit.

### Files to Update

1. `config/scanner_config.json` -- add `fiscal_year` section
2. `src/scrapers/usaspending.py` -- read FY dates from config
3. `src/packets/docx_sections.py` -- use `fy_label()` for cover page
4. `src/monitors/iija_sunset.py` -- already config-driven, just reference the shared FY end date

### Confidence: HIGH

This is a simple config extraction. No library needed.

---

## Debt Area 3: Integration Testing for Live API Scrapers

### Current State

The test suite (287 tests) is entirely unit tests using mock data. No test ever hits a real API. This is correct for CI, but there is no mechanism to:
- Record real API responses for regression testing
- Verify scraper normalization against real API schemas
- Detect API contract changes (e.g., Grants.gov changing field names)

### Recommendation: aioresponses for Unit Tests + VCR.py for Recorded Integration Tests

**Two-layer strategy:**

| Layer | Library | Purpose | When to Run |
|---|---|---|---|
| Unit (existing) | Mock data (current) | Fast, deterministic | Every CI run |
| Recorded Integration | aioresponses >=0.7.8 | Mock aiohttp at protocol level | Every CI run (replayed) |
| Live Integration | VCR.py >=8.1.1 | Record/replay real HTTP cassettes | Manual, pre-release |

### Library 1: aioresponses (dev dependency)

**Version:** 0.7.8 (released January 2025)
**Compatibility:** Python 3.12, aiohttp >=3.9.0
**PyPI:** https://pypi.org/project/aioresponses/

**Why aioresponses over alternatives:**

| Option | Verdict | Reason |
|---|---|---|
| aioresponses | USE THIS | Purpose-built for aiohttp mocking, pytest-native |
| responses | No | Only mocks `requests`, not `aiohttp` |
| pytest-httpx | No | Only mocks `httpx`, not `aiohttp` |
| unittest.mock | Fragile | Manual AsyncMock on aiohttp internals is brittle |

**Usage pattern for scraper tests:**

```python
import pytest
from aioresponses import aioresponses

@pytest.fixture
def mock_aiohttp():
    with aioresponses() as m:
        yield m

@pytest.mark.asyncio
async def test_usaspending_scraper(mock_aiohttp):
    """Test USASpending scraper against real API response shape."""
    mock_aiohttp.post(
        "https://api.usaspending.gov/api/v2/search/spending_by_award/",
        payload={
            "results": [
                {
                    "Award ID": "AWARD-123",
                    "Recipient Name": "Navajo Nation",
                    "Award Amount": 500000.00,
                    "Awarding Agency": "Bureau of Indian Affairs",
                    "Start Date": "2025-10-15",
                }
            ],
            "page_metadata": {"hasNext": False},
        },
    )
    scraper = USASpendingScraper(mock_config)
    items = await scraper.scan()
    assert len(items) == 1
    assert items[0]["source"] == "usaspending"
```

### Library 2: VCR.py (dev dependency, optional)

**Version:** 8.1.1 (released January 2026)
**Compatibility:** Python >=3.10 (includes 3.12), aiohttp supported
**PyPI:** https://pypi.org/project/vcrpy/

**Why VCR.py:**
- Records real HTTP responses to YAML "cassettes" on first run
- Replays cassettes on subsequent runs (no network needed)
- Native aiohttp integration (verified in vcrpy/tests/integration/test_aiohttp.py)
- Enables recording golden responses from each federal API for regression testing

**Usage pattern:**

```python
import vcr

@vcr.use_cassette("tests/cassettes/usaspending_tribal_awards.yaml")
async def test_usaspending_real_response():
    """Record and replay real USASpending response."""
    scraper = USASpendingScraper(real_config)
    async with scraper._create_session() as session:
        items = await scraper._fetch_obligations(session, "15.156", "bia_tcr")
    assert len(items) > 0
    assert all("source" in item for item in items)
```

**Cassette management:**
- Store cassettes in `tests/cassettes/` (git-tracked)
- Record with `--record-mode=once` (first run hits network, subsequent replays)
- Re-record periodically (monthly) to detect API schema changes
- Add `tests/cassettes/` to `.gitignore` if cassettes contain sensitive data, or sanitize headers

### What NOT to Use

| Library | Why Not |
|---|---|
| pytest-recording | Wrapper around VCR.py; adds indirection without value for this project |
| pytest-vcr | Older, less maintained than pytest-recording |
| responses | Synchronous only (requests library) |
| wiremock | Java-based, overkill |
| moto | AWS service mocking, not relevant |

### Installation

```bash
pip install -D aioresponses>=0.7.8
# Optional, for recorded integration tests:
pip install -D vcrpy>=8.1.1
```

### Confidence: HIGH

aioresponses is the standard tool for aiohttp test mocking. VCR.py v8.1.1 has verified aiohttp support. Both are actively maintained.

---

## Debt Area 4: Config-Driven File Paths

### Current State

Hardcoded `Path()` strings scattered across 8+ files:

| File | Hardcoded Path | Should Come From |
|---|---|---|
| `src/main.py:34` | `Path("config/scanner_config.json")` | CLI arg or env var (entry point, ok to hardcode) |
| `src/main.py:35` | `Path("data/program_inventory.json")` | Config |
| `src/main.py:36` | `Path("outputs/LATEST-GRAPH.json")` | Config |
| `src/main.py:37` | `Path("outputs/LATEST-MONITOR-DATA.json")` | Config |
| `src/main.py:104` | `Path("data/graph_schema.json")` | Config |
| `src/reports/generator.py:16` | `Path("outputs")` | Config |
| `src/analysis/change_detector.py:13` | `Path("outputs/LATEST-RESULTS.json")` | Config |
| `src/graph/builder.py:25` | `Path("data/graph_schema.json")` | Config |
| `src/scrapers/base.py:107` | `Path("outputs/.cfda_tracker.json")` | Config |
| `src/monitors/hot_sheets.py:29` | `Path("outputs/.monitor_state.json")` | Config |
| `src/packets/orchestrator.py:537` | `Path("data/graph_schema.json")` | Config |

### Recommendation: Frozen Dataclass Config + scanner_config.json

**Do NOT use pydantic, dynaconf, or any config library.** The project already has a working JSON config pattern. Extend it.

### Implementation Pattern

Add a `paths` section to `scanner_config.json`:

```json
{
  "paths": {
    "data_dir": "data",
    "output_dir": "outputs",
    "config_dir": "config",
    "program_inventory": "data/program_inventory.json",
    "graph_schema": "data/graph_schema.json",
    "latest_graph": "outputs/LATEST-GRAPH.json",
    "latest_results": "outputs/LATEST-RESULTS.json",
    "latest_monitor_data": "outputs/LATEST-MONITOR-DATA.json",
    "cfda_tracker": "outputs/.cfda_tracker.json",
    "monitor_state": "outputs/.monitor_state.json"
  }
}
```

Add a frozen dataclass in `src/paths.py` (~40 lines):

```python
"""Centralized path configuration.

All file paths flow from scanner_config.json["paths"].
Each module reads from this config instead of hardcoding Path() literals.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    """Immutable project path configuration."""

    data_dir: Path
    output_dir: Path
    program_inventory: Path
    graph_schema: Path
    latest_graph: Path
    latest_results: Path
    latest_monitor_data: Path
    cfda_tracker: Path
    monitor_state: Path

    @classmethod
    def from_config(cls, config: dict, project_root: Path | None = None) -> "ProjectPaths":
        """Build from scanner_config.json paths section."""
        paths_cfg = config.get("paths", {})
        root = project_root or Path.cwd()

        def _resolve(key: str, default: str) -> Path:
            return root / paths_cfg.get(key, default)

        return cls(
            data_dir=_resolve("data_dir", "data"),
            output_dir=_resolve("output_dir", "outputs"),
            program_inventory=_resolve("program_inventory", "data/program_inventory.json"),
            graph_schema=_resolve("graph_schema", "data/graph_schema.json"),
            latest_graph=_resolve("latest_graph", "outputs/LATEST-GRAPH.json"),
            latest_results=_resolve("latest_results", "outputs/LATEST-RESULTS.json"),
            latest_monitor_data=_resolve("latest_monitor_data", "outputs/LATEST-MONITOR-DATA.json"),
            cfda_tracker=_resolve("cfda_tracker", "outputs/.cfda_tracker.json"),
            monitor_state=_resolve("monitor_state", "outputs/.monitor_state.json"),
        )
```

### Migration Strategy

1. Add `paths` section to `scanner_config.json` (backward-compatible: defaults match current hardcoded values)
2. Create `src/paths.py` with `ProjectPaths` dataclass
3. Construct `ProjectPaths.from_config(config)` once in `main.py` after loading config
4. Pass `ProjectPaths` instance (or individual paths) to components that need them
5. Remove hardcoded `Path()` literals one module at a time
6. Each module's constructor gains a path parameter with the current hardcoded value as default (backward-compatible)

### What NOT to Do

- Do NOT use environment variables for paths (this is a data pipeline, not a web app)
- Do NOT use pydantic Settings (adds a heavy dependency for 10 paths)
- Do NOT use dynaconf/python-decouple (adds dependency for something a dataclass handles)
- Do NOT make paths CLI arguments (too many; config file is the right place)

### Confidence: HIGH

This is stdlib-only (dataclasses + pathlib). The pattern already exists in `src/packets/hazards.py` which uses `_resolve_path()` -- just needs to be formalized and centralized.

---

## Debt Area 5: Data Cache Population Automation

### Current State

Three data caches must be populated via manual scripts or live API calls before packet generation works:

| Cache | Source | Current Method | Files |
|---|---|---|---|
| Award cache | USASpending API | `TribalAwardMatcher.run(scraper)` | data/award_cache/*.json (592 files) |
| Hazard profiles | FEMA NRI CSV + USFS XLSX | `HazardProfileBuilder.build_all_profiles()` | data/hazard_profiles/*.json (592 files) |
| Congressional cache | Congress.gov API | `scripts/build_congress_cache.py` | data/congressional_cache.json |

The award cache requires a live USASpending API call (`fetch_all_tribal_awards()` -- paginates across 12 CFDAs). The hazard profiles require downloading FEMA NRI CSV and USFS XLSX files manually, then running the builder. There is no unified command to refresh all caches.

### Recommendation: CLI Subcommand + Makefile Target

**No new libraries needed.** The infrastructure already exists in `src/packets/awards.py` and `src/packets/hazards.py`. The gap is orchestration and CLI access.

### Implementation Pattern

Add a `--refresh-cache` CLI subcommand to `src/main.py`:

```python
parser.add_argument("--refresh-cache", type=str, nargs="?", const="all",
                    choices=["all", "awards", "hazards", "congress"],
                    help="Refresh data caches (awards, hazards, congress, or all)")
```

The handler calls existing code:

```python
if args.refresh_cache:
    target = args.refresh_cache
    if target in ("all", "awards"):
        from src.packets.awards import TribalAwardMatcher
        from src.scrapers.usaspending import USASpendingScraper
        matcher = TribalAwardMatcher(config)
        scraper = USASpendingScraper(config)
        result = matcher.run(scraper)
        print(f"Awards: {result}")

    if target in ("all", "hazards"):
        from src.packets.hazards import HazardProfileBuilder
        builder = HazardProfileBuilder(config)
        count = builder.build_all_profiles()
        print(f"Hazard profiles: {count} files written")

    if target in ("all", "congress"):
        from scripts.build_congress_cache import main as build_congress
        build_congress()
        print("Congressional cache refreshed")
    return
```

### Cache Freshness Tracking

Add a metadata file `data/.cache_manifest.json`:

```json
{
  "awards": {
    "last_refreshed": "2026-02-11T00:00:00Z",
    "files_count": 592,
    "source": "USASpending API"
  },
  "hazards": {
    "last_refreshed": "2026-02-11T00:00:00Z",
    "files_count": 592,
    "source": "FEMA NRI + USFS"
  },
  "congress": {
    "last_refreshed": "2026-02-11T00:00:00Z",
    "source": "Congress.gov API"
  }
}
```

The `--refresh-cache` command updates this manifest. The `--prep-packets` command checks it and warns if caches are stale (e.g., >30 days old).

### Data Source Download Guidance

For FEMA NRI and USFS data (which require manual download), add clear instructions:

```
# In --refresh-cache hazards output:
"Hazard profiles require manual data downloads:
  1. FEMA NRI: https://hazards.fema.gov/nri/data-resources
     -> Download 'NRI Table: Counties' CSV -> data/nri/NRI_Table_Counties.csv
     -> Download 'Tribal County Relational Database' CSV -> data/nri/
  2. USFS: https://wildfirerisk.org/
     -> Download XLSX -> data/usfs/

Then run: python -m src.main --refresh-cache hazards"
```

### Confidence: HIGH

The code already exists. This is pure orchestration wiring.

---

## Summary: What to Add vs What NOT to Add

### ADD (dev dependencies only)

| Package | Version | Purpose | Size |
|---|---|---|---|
| aioresponses | >=0.7.8 | Mock aiohttp in integration tests | Small |
| vcrpy | >=8.1.1 | Record/replay HTTP cassettes (optional) | Small |

### ADD (new source files, no dependencies)

| File | Purpose | Lines |
|---|---|---|
| `src/circuit_breaker.py` | Per-source circuit breaker for BaseScraper | ~40 |
| `src/fiscal.py` | FY date utilities (fy_start, fy_end, fy_label) | ~25 |
| `src/paths.py` | Frozen dataclass for centralized path config | ~45 |

### DO NOT ADD

| Library | Why Not |
|---|---|
| circuitbreaker | Only 30 lines needed; library adds dependency for trivial code |
| pybreaker | No asyncio support (Tornado only) |
| aiobreaker | Low maintenance, uncertain compatibility |
| fiscalyear | US federal FY is 3 lines of code; library is overkill |
| pydantic | Heavy dependency for 10 path fields |
| dynaconf | Config management library; project already has JSON config |
| pytest-recording | Thin wrapper over VCR.py; use VCR.py directly |

### MODIFY (existing files)

| File | Change |
|---|---|
| `config/scanner_config.json` | Add `fiscal_year` and `paths` sections |
| `src/scrapers/base.py` | Add circuit breaker integration |
| `src/scrapers/usaspending.py` | Read FY dates from config |
| `src/packets/docx_sections.py` | Use fy_label() for cover page |
| `src/main.py` | Add --refresh-cache, construct ProjectPaths |
| `src/graph/builder.py` | Accept graph_schema path from config |
| `src/analysis/change_detector.py` | Accept cache path from config |
| `src/reports/generator.py` | Accept output dir from config |
| `src/monitors/hot_sheets.py` | Accept state path from config |
| `requirements.txt` | No changes to production deps |

---

## Installation Changes

```bash
# Production dependencies: NO CHANGES
# (circuit breaker and fiscal year are hand-rolled)

# Dev dependencies (add to requirements-dev.txt or test extras):
pip install aioresponses>=0.7.8
pip install vcrpy>=8.1.1  # optional, for recorded integration tests
```

---

## Phase Ordering Recommendation

Based on dependency analysis:

1. **Config-driven paths (Debt 4)** -- Foundation. Other changes need config access patterns.
2. **Fiscal year config (Debt 2)** -- Depends on config pattern from step 1.
3. **Circuit breaker (Debt 1)** -- Independent, but benefits from config for thresholds.
4. **Integration tests (Debt 3)** -- Can test all the above changes.
5. **Cache automation (Debt 5)** -- CLI wiring, builds on everything else.

This order minimizes rework: each phase builds on the prior one.

---

## Sources

- [circuitbreaker 2.1.3 on PyPI](https://pypi.org/project/circuitbreaker/) -- Verified async support, Python 3.8-3.10 classifiers
- [pybreaker on GitHub](https://github.com/danielfm/pybreaker) -- Confirmed Tornado-only async, no asyncio
- [aiobreaker on GitHub](https://github.com/arlyon/aiobreaker) -- Fork of pybreaker for asyncio
- [aioresponses on PyPI](https://pypi.org/project/aioresponses/) -- v0.7.8, aiohttp mock library
- [aioresponses on GitHub](https://github.com/pnuckowski/aioresponses) -- Usage patterns and examples
- [VCR.py on PyPI](https://pypi.org/project/vcrpy/) -- v8.1.1, Python >=3.10, aiohttp integration verified
- [VCR.py aiohttp integration tests](https://github.com/kevin1024/vcrpy/blob/master/tests/integration/test_aiohttp.py) -- Confirmed aiohttp cassette support
- [aiohttp testing docs](https://docs.aiohttp.org/en/stable/testing.html) -- Official testing guidance
- [fiscalyear on PyPI](https://pypi.org/project/fiscalyear/) -- Evaluated and rejected (overkill)
- [Dataclass config patterns](https://grueter.dev/blog/dataclass-patterns/) -- Frozen dataclass best practices
- [Python pathlib docs](https://docs.python.org/3/library/pathlib.html) -- Official pathlib reference
- Codebase analysis: `src/scrapers/base.py`, `src/main.py`, `config/scanner_config.json`, all 4 scrapers, `src/packets/orchestrator.py`, `src/packets/awards.py`, `src/packets/hazards.py`
