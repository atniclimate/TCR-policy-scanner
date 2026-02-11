# Architecture Analysis: Tech Debt Integration with Existing TCR Pipeline

**Domain:** Tech debt cleanup in existing Python 3.12 async pipeline
**Researched:** 2026-02-11
**Overall confidence:** HIGH (analysis based on direct reading of all 52 source files)

---

## 1. Current Architecture Map

### 1.1 System Overview

The TCR Policy Scanner has two major subsystems that share configuration but run independently:

```
SUBSYSTEM 1: Daily Scan Pipeline
  CLI (main.py)
    -> Ingest: 4 async scrapers (BaseScraper -> aiohttp)
    -> Normalize: per-source _normalize() methods
    -> Analysis: RelevanceScorer + ChangeDetector
    -> Graph: GraphBuilder (static seed + dynamic enrichment)
    -> Monitors: 5 monitors via MonitorRunner
    -> Decision Engine: program classification
    -> Reporting: Markdown + JSON

SUBSYSTEM 2: Packet Generation Pipeline
  CLI (main.py --prep-packets)
    -> PacketOrchestrator
    -> TribalRegistry (592 Tribes from EPA API cache)
    -> EcoregionMapper + CongressionalMapper
    -> Per-Tribe data: award_cache/*.json + hazard_profiles/*.json
    -> ProgramRelevanceFilter (8-12 programs per Tribe)
    -> EconomicImpactCalculator
    -> DocxEngine (9-section DOCX via python-docx)
    -> StrategicOverviewGenerator
```

### 1.2 Configuration Topology

```
config/scanner_config.json          <-- Single config source
  |-- sources.*                     <-- Scraper endpoints + weights
  |-- scoring.*                     <-- Relevance scoring weights
  |-- monitors.*                    <-- Monitor thresholds + deadlines
  |-- packets.*                     <-- Packet data paths + options
  |     |-- tribal_registry.data_path
  |     |-- congressional_cache.data_path
  |     |-- awards.{alias_path, cache_dir, fuzzy_threshold}
  |     |-- hazards.{nri_dir, usfs_dir, cache_dir, crosswalk_path}
  |     |-- docx.{enabled, output_dir}
  |     \-- output_dir
  |-- search_queries[]              <-- Shared search terms
  |-- tribal_keywords[]             <-- Tribal keyword list
  \-- action_keywords[]             <-- Action keyword list
```

### 1.3 Hardcoded Path Inventory (Tech Debt Item #3)

Every hardcoded path in the codebase, with the file and line where it occurs:

| File | Line | Hardcoded Path | Used For |
|------|------|---------------|----------|
| `src/main.py` | 34 | `Path("config/scanner_config.json")` | Config loading |
| `src/main.py` | 35 | `Path("data/program_inventory.json")` | Program inventory |
| `src/main.py` | 36 | `Path("outputs/LATEST-GRAPH.json")` | Graph output |
| `src/main.py` | 37 | `Path("outputs/LATEST-MONITOR-DATA.json")` | Monitor output |
| `src/main.py` | 104 | `Path("data/graph_schema.json")` | Graph schema (dry-run) |
| `src/scrapers/base.py` | 107 | `Path("outputs/.cfda_tracker.json")` | Zombie CFDA tracker |
| `src/graph/builder.py` | 25 | `Path("data/graph_schema.json")` | Graph schema loading |
| `src/reports/generator.py` | 16 | `Path("outputs")` | Report output dir |
| `src/analysis/change_detector.py` | 13 | `Path("outputs/LATEST-RESULTS.json")` | Scan results cache |
| `src/monitors/hot_sheets.py` | 29 | `Path("outputs/.monitor_state.json")` | Monitor state file |
| `src/packets/change_tracker.py` | 60 | `Path("data/packet_state")` | Packet state dir |
| `src/packets/orchestrator.py` | 537 | `Path("data/graph_schema.json")` | Structural asks loading |

**Pattern observed:** Most hardcoded paths are relative to CWD, not absolute. The packet subsystem already reads most paths from `scanner_config.json["packets"]`, but the scan pipeline uses module-level constants.

### 1.4 Fiscal Year Hardcoding Inventory (Tech Debt Item #2)

| File | Line | Hardcoded Value | Context |
|------|------|----------------|---------|
| `src/scrapers/usaspending.py` | 68 | `"2025-10-01"`, `"2026-09-30"` | FY26 time period filter |
| `src/scrapers/usaspending.py` | 216 | `"FY26 Obligation:"` | Award title prefix |
| `src/monitors/iija_sunset.py` | 53-54 | `"2026-09-30"` | FY26 end date (config-driven via `monitors.iija_sunset.fy26_end`) |
| `src/graph/builder.py` | 161 | `fy26_status` field name | Schema field |
| `src/graph/builder.py` | 176 | `"FY26"` string literal | Urgency classification |
| `src/graph/builder.py` | 398 | `fiscal_year="FY26"` | Dynamic funding vehicle |
| `src/graph/schema.py` | 20, 36, 60, 83 | `fiscal_year` field | Schema dataclass fields |
| `src/packets/strategic_overview.py` | 3, 182, 195, 227 | `"FY26"` | Header text, document title |
| `src/packets/docx_sections.py` | 55 | `"FY26"` | Section title prefix |

**Key finding:** The `iija_sunset` monitor already reads FY end date from config (`monitors.iija_sunset.fy26_end`). But `usaspending.py` has the fiscal year dates hardcoded directly in the API payload. The DOCX generators have "FY26" baked into display strings.

### 1.5 File Dependency Graph

```
scanner_config.json
  |
  +-> src/main.py (load_config)
  |     +-> All scrapers (config dict passed to __init__)
  |     +-> RelevanceScorer(config, programs)
  |     +-> MonitorRunner(config, programs_dict)
  |     +-> DecisionEngine(config, programs_dict)
  |     +-> PacketOrchestrator(config, programs)
  |
  +-> src/packets/orchestrator.py
        +-> TribalRegistry(config)
        +-> CongressionalMapper(config)
        +-> EcoregionMapper(config)
        +-> DocxEngine(config, programs)
        +-> EconomicImpactCalculator() -- NO config dependency!
        +-> ProgramRelevanceFilter(programs)

data/program_inventory.json
  +-> src/main.py (load_programs)
  +-> All downstream via programs dict

data/graph_schema.json
  +-> src/graph/builder.py (GRAPH_SCHEMA_PATH hardcoded)
  +-> src/packets/orchestrator.py (_load_structural_asks, hardcoded)
  +-> src/main.py (dry_run, hardcoded)
```

---

## 2. Tech Debt Item Integration Analysis

### 2.1 Circuit Breaker Pattern (Debt Item #1)

**Current state:** `BaseScraper._request_with_retry()` provides retry with exponential backoff and rate-limit handling. It retries individual requests up to `MAX_RETRIES=3` times. There is no circuit breaker -- if a source is fully down, all queries for that source will individually time out and retry before failing.

**Integration point:** `src/scrapers/base.py` (lines 26-102)

**What needs to change:**

```
BEFORE: Each of 20+ queries per scraper independently retries 3x.
         If API is down: 20 queries x 3 retries x 30s timeout = 30 min hang.

AFTER:  Circuit breaker trips after N consecutive failures per source.
        Remaining queries for that source skip immediately.
        Next scraper proceeds without waiting.
```

**Files to modify:**
- `src/scrapers/base.py`: Add `CircuitBreaker` class or mixin, add state tracking (closed/open/half-open), integrate with `_request_with_retry()`
- No new files needed -- this belongs in `base.py` where the retry logic already lives

**Files NOT to modify:**
- Individual scrapers (`federal_register.py`, `grants_gov.py`, `congress_gov.py`, `usaspending.py`): They call `self._request_with_retry()` which is the correct integration point. Circuit breaker is transparent to subclasses.

**Risk assessment:** LOW. The circuit breaker wraps existing retry logic. If implemented correctly, behavior is identical to current code when APIs are healthy (breaker stays closed). Regression risk is limited to the retry path, which is already tested implicitly by the scraper tests.

**Test strategy:**
- Unit test `CircuitBreaker` state machine directly (closed -> open after N failures, open -> half-open after cooldown, half-open -> closed on success)
- Unit test that `_request_with_retry()` respects breaker state
- Existing scraper tests continue to pass (breaker is transparent when no failures)

**Integration considerations:**
- Circuit breaker state should be per-source (each `BaseScraper` instance has its own). The current `source_name` field already identifies the source.
- The `run_scan()` function in `main.py` runs scrapers concurrently via `asyncio.gather()`. Circuit breaker is per-instance, so concurrent scrapers do not interfere.
- `grants_gov.py` uses `check_zombie_cfda()` from base.py -- this is an analysis function, not an HTTP function, so it is unaffected by circuit breaker changes.

### 2.2 Fiscal Year Config Propagation (Debt Item #2)

**Current state:** FY26 is hardcoded in USASpending scraper payloads, graph builder strings, DOCX section titles, and strategic overview headers. The IIJA sunset monitor is the only component that reads fiscal year from config.

**Integration point:** `config/scanner_config.json` (new top-level field) propagating to 5 files

**What needs to change:**

Add to `scanner_config.json`:
```json
{
  "fiscal_year": "FY26",
  "fiscal_year_start": "2025-10-01",
  "fiscal_year_end": "2026-09-30"
}
```

**Files to modify:**

| File | What Changes | Risk |
|------|-------------|------|
| `config/scanner_config.json` | Add `fiscal_year`, `fiscal_year_start`, `fiscal_year_end` | NONE -- additive |
| `src/scrapers/usaspending.py` | Read `config["fiscal_year_start"]` and `config["fiscal_year_end"]` instead of hardcoded dates (lines 68, 216) | LOW -- scraper `__init__` already receives `config` |
| `src/graph/builder.py` | Read `config` fiscal year for dynamic FV creation (line 398). Schema field names (`fy26_status`) are structural -- rename is optional and higher risk. | LOW for string substitution, MEDIUM for field rename |
| `src/packets/strategic_overview.py` | Replace `"FY26"` literals with `config["fiscal_year"]` (lines 182, 195, 227) | LOW -- string substitution |
| `src/packets/docx_sections.py` | Replace `"FY26"` literal (line 55) with config lookup | LOW -- string substitution |

**Files NOT to modify:**
- `src/monitors/iija_sunset.py`: Already reads `monitors.iija_sunset.fy26_end` from config. The monitor-specific FY end date is correct as-is (different semantic: this is the IIJA authorization expiration, not the generic fiscal year).
- `src/graph/schema.py`: `fiscal_year` field names in dataclasses are generic. No change needed.

**Risk assessment:** LOW overall. The highest risk is breaking the USASpending API query if dates are formatted incorrectly. Mitigation: validate date format in `__init__` before storing.

**Propagation path:**
```
scanner_config.json["fiscal_year"]
  -> main.py load_config()
  -> passed to scraper constructors (already receive full config)
  -> passed to PacketOrchestrator (already receives full config)
  -> PacketOrchestrator passes config to DocxEngine and StrategicOverviewGenerator (already receive config)
```

**Test strategy:**
- Add test that loads config and verifies fiscal year fields exist
- Test USASpending scraper with mock config containing fiscal year fields
- Test DOCX sections render with config fiscal year, not hardcoded

### 2.3 Config-Driven Path Resolution (Debt Item #3)

**Current state:** 12 hardcoded paths (see Section 1.3). The packet subsystem already uses config-driven paths. The scan pipeline does not.

**Integration approach:** Centralize path resolution in a single utility, then migrate consumers.

**What needs to change:**

Add to `scanner_config.json`:
```json
{
  "paths": {
    "program_inventory": "data/program_inventory.json",
    "graph_schema": "data/graph_schema.json",
    "graph_output": "outputs/LATEST-GRAPH.json",
    "monitor_output": "outputs/LATEST-MONITOR-DATA.json",
    "scan_results": "outputs/LATEST-RESULTS.json",
    "cfda_tracker": "outputs/.cfda_tracker.json",
    "monitor_state": "outputs/.monitor_state.json",
    "report_output_dir": "outputs"
  }
}
```

**New file needed:**
- `src/config.py` (or add to existing module): A `resolve_path(config, key, default)` helper that reads `config["paths"][key]` with a fallback default. Returns `Path` object. Optionally resolves relative to a project root.

**Files to modify (in order of safest to riskiest):**

| Priority | File | Current | Change To | Risk |
|----------|------|---------|-----------|------|
| 1 | `src/main.py` (lines 34-37) | Module-level `Path()` constants | Read from config after `load_config()` | LOW -- but `CONFIG_PATH` itself must remain hardcoded (bootstrap) |
| 2 | `src/graph/builder.py` (line 25) | `GRAPH_SCHEMA_PATH` constant | Accept path via `__init__` parameter or config | LOW |
| 3 | `src/reports/generator.py` (line 16) | `OUTPUTS_DIR` constant | Accept via `__init__` parameter | LOW |
| 4 | `src/analysis/change_detector.py` (line 13) | `CACHE_FILE` constant | Accept via `__init__` parameter | LOW |
| 5 | `src/scrapers/base.py` (line 107) | `CFDA_TRACKER_PATH` constant | Accept via parameter or config | LOW |
| 6 | `src/monitors/hot_sheets.py` (line 29) | `MONITOR_STATE_PATH` constant | Accept via config | LOW |
| 7 | `src/packets/orchestrator.py` (line 537) | `Path("data/graph_schema.json")` | Read from config | LOW -- packets already config-driven |

**Bootstrap path:** `config/scanner_config.json` itself must remain hardcoded in `main.py` (or accepted via CLI `--config` flag). This is the unavoidable bootstrap -- every config-driven system needs one fixed entry point.

**Risk assessment:** LOW individually, MEDIUM collectively due to the number of files changing. The key risk is that module-level constants (`GRAPH_SCHEMA_PATH`, `CFDA_TRACKER_PATH`, etc.) are currently evaluated at import time. Moving them to runtime config means they must be resolved after `load_config()`, which changes initialization order.

**Mitigation strategy:**
1. Keep module-level constants as defaults
2. Allow override via `__init__` parameter (dependency injection pattern)
3. `main.py` passes config-derived paths at construction time
4. Unit tests continue to work with defaults (no config dependency)

**Test strategy:**
- Existing tests should continue to pass with default paths (backward compatible)
- Add tests that verify config-driven paths override defaults
- Test with `tmp_path` fixture to verify path resolution

### 2.4 CLI Cache Population Automation (Debt Item #4)

**Current state:** Data caches are populated by standalone scripts:
- `scripts/build_registry.py` -> `data/tribal_registry.json`
- `scripts/build_congress_cache.py` -> `data/congressional_cache.json`
- `scripts/build_tribal_aliases.py` -> `data/tribal_aliases.json`
- Award caches: `TribalAwardMatcher.run()` (called from no CLI entry point)
- Hazard caches: `HazardProfileBuilder.build_all_profiles()` (called from no CLI entry point)

**The gap:** There is no single CLI command to populate all caches. A new user must run 3-5 separate scripts in the correct order. Awards and hazards have no CLI at all.

**Integration point:** `src/main.py` (CLI entry point)

**What needs to change:**

Add CLI flag: `--populate-caches` (or `--build-caches`)

```
python -m src.main --populate-caches              # Build all caches
python -m src.main --populate-caches --registry    # Just tribal registry
python -m src.main --populate-caches --congress    # Just congressional cache
python -m src.main --populate-caches --aliases     # Just tribal aliases
python -m src.main --populate-caches --awards      # Just award caches
python -m src.main --populate-caches --hazards     # Just hazard profiles
```

**Files to modify:**
- `src/main.py`: Add `--populate-caches` argparse group, import and call builders
- No changes to existing build scripts -- they remain usable standalone

**Files needed (optional):**
- `src/cache_builder.py`: Orchestration module that coordinates build order:
  1. Registry first (all others depend on it)
  2. Aliases (depends on registry)
  3. Congressional cache (depends on registry)
  4. Awards (depends on registry + aliases)
  5. Hazards (depends on crosswalk from congress cache)

**Dependency ordering:**
```
tribal_registry.json (no deps)
  -> tribal_aliases.json (needs registry)
  -> congressional_cache.json (needs registry)
     -> aiannh_tribe_crosswalk.json (side-effect of congress cache build)
        -> hazard_profiles/*.json (needs crosswalk)
  -> award_cache/*.json (needs registry + aliases)
```

**Risk assessment:** LOW. This is purely additive -- new CLI entry point that calls existing code. No modification to existing functionality.

**Test strategy:**
- Test CLI argument parsing (argparse tests)
- Integration test with mock APIs (using `tmp_path` for output)
- Test dependency ordering (registry must be built before aliases)

### 2.5 Integration Test API Mocking (Debt Item #5)

**Current state:** 287 tests across 13 test modules. All tests use `tmp_path` fixtures with mock JSON data. No tests hit live APIs. No VCR/recorded responses. No integration tests that verify actual API response parsing.

**Test file inventory:**

| Test File | Tests | What It Covers |
|-----------|-------|---------------|
| `test_packets.py` | ~70 | Phase 5-6: Registry, ecoregion, congress, awards, hazards |
| `test_decision_engine.py` | ~30 | Decision engine classification logic |
| `test_docx_hotsheet.py` | ~20 | DOCX hot sheet rendering |
| `test_docx_styles.py` | ~15 | DOCX style manager |
| `test_docx_integration.py` | ~25 | DOCX full-document assembly |
| `test_economic.py` | ~20 | Economic impact calculations |
| `test_doc_assembly.py` | ~15 | Document section assembly |
| `test_strategic_overview.py` | ~15 | Strategic overview generation |
| `test_batch_generation.py` | ~20 | Batch 592-Tribe generation |
| `test_change_tracking.py` | ~15 | Packet change tracking |
| `test_web_index.py` | ~10 | Web index generation |
| `test_e2e_phase8.py` | ~30 | End-to-end pipeline tests |

**What needs to change:**

Two approaches, not mutually exclusive:

**Approach A: VCR-style recorded responses (recommended)**
- Record real API responses to JSON/YAML files in `tests/fixtures/`
- Replay during tests using `aioresponses` (aiohttp mock) or custom context manager
- Test files: `tests/fixtures/federal_register_response.json`, etc.

**Approach B: Contract tests**
- Verify that real API response schemas match expected schemas
- Run infrequently (CI nightly, not every push)
- Use `pytest.mark.integration` to separate from unit tests

**Files to create:**
- `tests/conftest.py`: Shared fixtures for API response mocking
- `tests/fixtures/`: Directory for recorded API responses
- `tests/test_scraper_integration.py`: Integration tests with recorded responses

**Files to modify:**
- `src/scrapers/base.py`: Optionally add a session injection point so tests can provide a mock session. Currently `_create_session()` creates a real `aiohttp.ClientSession`. Adding an optional `session` parameter to the constructor would make testing cleaner:

```python
class BaseScraper:
    def __init__(self, source_name: str, session: aiohttp.ClientSession | None = None):
        self.source_name = source_name
        self._headers = {"User-Agent": USER_AGENT}
        self._injected_session = session
```

**Risk assessment:** LOW for test-only changes. MEDIUM if modifying `BaseScraper.__init__` signature (all 4 subclass constructors would need updating, though they call `super().__init__()` which already handles it).

**Test strategy:**
- Record real API responses once (manual step)
- Write tests that replay recorded responses
- Verify normalization output matches expected schema
- Mark integration tests with `@pytest.mark.integration`

---

## 3. Suggested Build Order

The 5 debt items have a natural dependency/safety ordering:

### Phase 1: Test Infrastructure First (Debt #5 partial)

**Rationale:** Before changing production code, establish the test infrastructure that will catch regressions.

**What to build:**
- `tests/conftest.py` with shared API response fixtures
- `tests/fixtures/` directory with recorded/mock API responses
- `aioresponses` or equivalent mock setup
- Optional: session injection in `BaseScraper`

**Files modified:** `src/scrapers/base.py` (minor, optional), new test files only
**Risk:** VERY LOW (test-only changes)
**Existing tests affected:** None

### Phase 2: Config Foundation (Debt #2 + #3)

**Rationale:** Fiscal year config and path config are both "add config fields, then update consumers" patterns. They share the same risk profile and can be done together. Config changes are backward-compatible (add new fields with defaults).

**What to build:**
- Add `fiscal_year`, `fiscal_year_start`, `fiscal_year_end` to config
- Add `paths` section to config
- Create `src/config.py` utility (or inline helpers)
- Update consumers one file at a time, preserving defaults

**Suggested sub-ordering:**
1. Add config fields (additive, zero risk)
2. Update `usaspending.py` to read fiscal year from config (isolated change)
3. Update `graph/builder.py` to use config fiscal year for dynamic strings
4. Update DOCX generators to read fiscal year from config
5. Add `--config` CLI flag to `main.py` (optional, nice-to-have)
6. Migrate hardcoded paths one file at a time (main.py last, most impactful)

**Files modified:** `config/scanner_config.json`, `src/scrapers/usaspending.py`, `src/graph/builder.py`, `src/packets/strategic_overview.py`, `src/packets/docx_sections.py`, `src/main.py`, `src/reports/generator.py`, `src/analysis/change_detector.py`, `src/scrapers/base.py`, `src/monitors/hot_sheets.py`
**Risk:** LOW-MEDIUM (many files but each change is small)
**Existing tests affected:** Tests that construct scrapers/builders with mock configs will need the new config keys in their fixtures. Add default values so existing tests pass without changes.

### Phase 3: Circuit Breaker (Debt #1)

**Rationale:** Standalone change to `base.py`. Does it after config changes so the circuit breaker can optionally read thresholds from config.

**What to build:**
- `CircuitBreaker` class in `src/scrapers/base.py`
- Integration with `_request_with_retry()`
- Unit tests for circuit breaker state machine
- Optional: circuit breaker config in `scanner_config.json`

**Files modified:** `src/scrapers/base.py`
**Risk:** LOW (isolated to retry path, transparent to subclasses)
**Existing tests affected:** None (circuit breaker is invisible when APIs work)

### Phase 4: CLI Cache Automation (Debt #4)

**Rationale:** After config and circuit breaker are in place, the cache builder can use config-driven paths and benefit from circuit breaker during API calls.

**What to build:**
- `src/cache_builder.py` (orchestration module)
- CLI `--populate-caches` flag in `main.py`
- Sub-flags for individual cache types
- Integration tests

**Files modified:** `src/main.py` (CLI extension), new `src/cache_builder.py`
**Risk:** LOW (additive, no changes to existing functionality)
**Existing tests affected:** None

### Phase 5: Integration Tests (Debt #5 completion)

**Rationale:** With all production changes done and test infrastructure from Phase 1 in place, write the actual integration tests.

**What to build:**
- `tests/test_scraper_integration.py`: Recorded response tests for all 4 scrapers
- `tests/test_pipeline_integration.py`: End-to-end pipeline with mocked APIs
- Contract tests for API response schemas
- `@pytest.mark.integration` markers

**Files modified:** Test files only
**Risk:** NONE (test-only)
**Existing tests affected:** None

---

## 4. Risk Matrix

| Debt Item | Files Changed | Regression Risk | Test Coverage Before | Test Coverage After |
|-----------|--------------|----------------|---------------------|-------------------|
| #1 Circuit Breaker | 1 (base.py) | LOW | Implicit (scraper tests) | Explicit (state machine tests) |
| #2 Fiscal Year Config | 5 (config + 4 consumers) | LOW | No fiscal year tests | Config validation + consumer tests |
| #3 Path Resolution | 8 (config + 7 consumers) | MEDIUM | Tests use defaults | Config override tests |
| #4 Cache CLI | 2 (main.py + new cache_builder) | LOW | No CLI cache tests | CLI + integration tests |
| #5 Integration Tests | 0 production + 3 test files | NONE | 287 unit tests | 287 unit + ~30 integration |

### 4.1 Highest-Risk Changes

1. **`src/main.py` path migration (Debt #3):** This file is the entry point for both subsystems. Changing how `CONFIG_PATH`, `INVENTORY_PATH`, `GRAPH_OUTPUT_PATH`, and `MONITOR_OUTPUT_PATH` are resolved affects every run mode. The bootstrap problem (config path must be known before config is loaded) requires keeping at least `CONFIG_PATH` hardcoded or accepting it via CLI.

2. **`src/graph/builder.py` fiscal year changes (Debt #2):** The graph builder creates nodes with `fy26_status` field names. Renaming these to generic `fiscal_year_status` is a schema change that would break any downstream consumer reading graph JSON. Recommend: keep field names, only change string *values* that display to users.

3. **`src/scrapers/base.py` circuit breaker + session injection (Debt #1 + #5):** Two changes to the same file. Should be done in a single phase to avoid merge conflicts. The `__init__` signature change (session injection) affects all 4 scraper subclasses.

### 4.2 Safest Changes (Do First)

1. **Adding config fields to `scanner_config.json`:** Pure additive. Zero risk.
2. **New test fixtures and files:** No production code changes.
3. **New `src/cache_builder.py`:** New file, no existing code modified.
4. **DOCX string substitutions (FY26 -> config):** Isolated to rendering, tested by existing DOCX tests.

---

## 5. Component Boundary Analysis

### 5.1 Where Changes Are Contained

```
              SCAN PIPELINE              PACKET PIPELINE
              ============              ================

config.json  [MODIFIED: +fiscal_year, +paths]
    |                          |
    v                          v
main.py      [MODIFIED: paths, CLI]     [MODIFIED: --populate-caches]
    |                          |
    v                          v
base.py      [MODIFIED: circuit breaker, session injection]
    |                          |
    +-- federal_register.py    |  (unchanged -- inherits from base)
    +-- grants_gov.py          |  (unchanged -- inherits from base)
    +-- congress_gov.py        |  (unchanged -- inherits from base)
    +-- usaspending.py  [MODIFIED: fiscal year from config]
    |                          |
    v                          v
builder.py   [MODIFIED: fiscal year strings]
    |                          |
    v                          v
generator.py [MODIFIED: output path from config]
change_detector.py [MODIFIED: cache path from config]
hot_sheets.py [MODIFIED: state path from config]
    |                          |
    |                          v
    |              orchestrator.py  (unchanged -- already config-driven)
    |              docx_engine.py   (unchanged)
    |              docx_sections.py [MODIFIED: FY26 -> config]
    |              strategic_overview.py [MODIFIED: FY26 -> config]
    |                          |
    |                          v
    |              cache_builder.py [NEW: CLI cache orchestration]
    |
    v
test infrastructure [NEW: conftest, fixtures, integration tests]
```

### 5.2 Unchanged Components (Verified Safe)

These files need NO changes across all 5 debt items:

- `src/analysis/relevance.py` -- scoring logic, no paths or FY references
- `src/analysis/decision_engine.py` -- classification logic, no paths or FY references
- `src/packets/registry.py` -- already config-driven
- `src/packets/congress.py` -- already config-driven
- `src/packets/ecoregion.py` -- already config-driven
- `src/packets/context.py` -- pure dataclass, no I/O
- `src/packets/economic.py` -- pure computation, no config dependency
- `src/packets/relevance.py` -- pure filtering, no I/O
- `src/packets/awards.py` -- already config-driven
- `src/packets/hazards.py` -- already config-driven
- `src/packets/docx_engine.py` -- already config-driven
- `src/packets/docx_hotsheet.py` -- rendering only, no config
- `src/packets/docx_styles.py` -- style definitions, no config
- `src/packets/change_tracker.py` -- already config-driven (via `state_dir` param)
- `src/monitors/iija_sunset.py` -- already reads FY from config
- `src/monitors/reconciliation.py` -- keyword-based, no paths
- `src/monitors/dhs_funding.py` -- date from config
- `src/monitors/tribal_consultation.py` -- keyword-based, no paths
- `src/monitors/__init__.py` -- runner framework, no paths
- `src/graph/schema.py` -- dataclass definitions only
- `validate_data_integrity.py` -- standalone validator
- All existing test files (backward-compatible changes preserve defaults)

---

## 6. Configuration Schema Evolution

### 6.1 Current Schema (v1.1)

```json
{
  "domain": "tcr",
  "domain_name": "Tribal Climate Resilience",
  "sources": { ... },
  "scoring": { ... },
  "tribal_keywords": [ ... ],
  "action_keywords": [ ... ],
  "search_queries": [ ... ],
  "scan_window_days": 14,
  "monitors": { ... },
  "packets": { ... }
}
```

### 6.2 Proposed Schema (v2.0 -- post debt cleanup)

```json
{
  "domain": "tcr",
  "domain_name": "Tribal Climate Resilience",
  "fiscal_year": "FY26",
  "fiscal_year_start": "2025-10-01",
  "fiscal_year_end": "2026-09-30",
  "paths": {
    "config": "config/scanner_config.json",
    "program_inventory": "data/program_inventory.json",
    "graph_schema": "data/graph_schema.json",
    "graph_output": "outputs/LATEST-GRAPH.json",
    "monitor_output": "outputs/LATEST-MONITOR-DATA.json",
    "scan_results": "outputs/LATEST-RESULTS.json",
    "cfda_tracker": "outputs/.cfda_tracker.json",
    "monitor_state": "outputs/.monitor_state.json",
    "report_output_dir": "outputs"
  },
  "circuit_breaker": {
    "failure_threshold": 3,
    "recovery_timeout_seconds": 60,
    "half_open_max_calls": 1
  },
  "sources": { ... },
  "scoring": { ... },
  "tribal_keywords": [ ... ],
  "action_keywords": [ ... ],
  "search_queries": [ ... ],
  "scan_window_days": 14,
  "monitors": { ... },
  "packets": { ... }
}
```

**Backward compatibility:** All new fields have sensible defaults coded in the consumers. If `fiscal_year` is absent, fall back to `"FY26"`. If `paths` is absent, fall back to current hardcoded defaults. If `circuit_breaker` is absent, use reasonable defaults.

---

## 7. Testing Architecture Recommendations

### 7.1 Test Hierarchy

```
tests/
  conftest.py                   # Shared fixtures: mock config, mock registry, API mocks
  fixtures/
    federal_register_200.json   # Recorded successful response
    grants_gov_200.json         # Recorded successful response
    congress_gov_200.json       # Recorded successful response
    usaspending_200.json        # Recorded successful response
    federal_register_429.json   # Rate limit response
    federal_register_500.json   # Server error response
  test_circuit_breaker.py       # NEW: Circuit breaker state machine tests
  test_config.py                # NEW: Config loading, path resolution, fiscal year
  test_cache_builder.py         # NEW: CLI cache automation
  test_scraper_integration.py   # NEW: Scrapers with recorded responses
  test_pipeline_integration.py  # NEW: End-to-end with mocked APIs
  test_decision_engine.py       # Existing (unchanged)
  test_packets.py               # Existing (unchanged)
  test_docx_hotsheet.py         # Existing (unchanged)
  test_docx_styles.py           # Existing (unchanged)
  test_docx_integration.py      # Existing (unchanged)
  test_economic.py              # Existing (unchanged)
  test_doc_assembly.py          # Existing (unchanged)
  test_strategic_overview.py    # Existing (unchanged)
  test_batch_generation.py      # Existing (unchanged)
  test_change_tracking.py       # Existing (unchanged)
  test_web_index.py             # Existing (unchanged)
  test_e2e_phase8.py            # Existing (unchanged)
```

### 7.2 Recommended Mock Library

For aiohttp mocking, use `aioresponses` (already proven in the Python async testing ecosystem):

```python
# tests/conftest.py
from aioresponses import aioresponses

@pytest.fixture
def mock_aiohttp():
    with aioresponses() as m:
        yield m
```

This allows tests to register URL patterns and return recorded JSON responses without any network access.

### 7.3 Test Markers

```python
# pytest.ini or pyproject.toml
[tool.pytest.ini_options]
markers = [
    "integration: marks tests that use recorded API responses (deselect with '-m not integration')",
    "slow: marks tests that take >5s (deselect with '-m not slow')",
]
```

---

## 8. Summary: Files Modified Per Debt Item

### Complete File Modification Matrix

| File | Debt #1 (CB) | Debt #2 (FY) | Debt #3 (Paths) | Debt #4 (CLI) | Debt #5 (Tests) |
|------|:---:|:---:|:---:|:---:|:---:|
| `config/scanner_config.json` | opt | YES | YES | - | - |
| `src/scrapers/base.py` | YES | - | YES | - | opt |
| `src/scrapers/usaspending.py` | - | YES | - | - | - |
| `src/graph/builder.py` | - | YES | YES | - | - |
| `src/reports/generator.py` | - | - | YES | - | - |
| `src/analysis/change_detector.py` | - | - | YES | - | - |
| `src/monitors/hot_sheets.py` | - | - | YES | - | - |
| `src/packets/orchestrator.py` | - | - | YES | - | - |
| `src/packets/strategic_overview.py` | - | YES | - | - | - |
| `src/packets/docx_sections.py` | - | YES | - | - | - |
| `src/main.py` | - | - | YES | YES | - |
| `src/cache_builder.py` (NEW) | - | - | - | YES | - |
| `src/config.py` (NEW, optional) | - | - | YES | - | - |
| `tests/conftest.py` (NEW) | - | - | - | - | YES |
| `tests/test_circuit_breaker.py` (NEW) | YES | - | - | - | - |
| `tests/test_config.py` (NEW) | - | YES | YES | - | - |
| `tests/test_cache_builder.py` (NEW) | - | - | - | YES | - |
| `tests/test_scraper_integration.py` (NEW) | - | - | - | - | YES |

**Total production files modified:** 11 existing + 2-3 new
**Total test files created:** 4-5 new
**Total existing tests broken:** 0 (all changes are backward-compatible with defaults)

---

## Sources

- Direct reading of all 52 source files in `F:\tcr-policy-scanner\src\`
- Direct reading of all 13 test files in `F:\tcr-policy-scanner\tests\`
- Direct reading of `config/scanner_config.json`
- Direct reading of 3 build scripts in `scripts/`
- Existing architecture research in `.planning/research/ARCHITECTURE.md` (v1.1)
- MEMORY.md patterns (atomic writes, python-docx patterns, security patterns)
