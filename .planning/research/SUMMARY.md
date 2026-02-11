# Tech Debt Cleanup Research Summary

**Project:** TCR Policy Scanner v1.2 Tech Debt Cleanup
**Domain:** Production Python 3.12 async pipeline refactoring
**Researched:** 2026-02-11
**Confidence:** HIGH

## Executive Summary

This milestone closes 17 documented tech debt items across 5 categories: testing gaps, hardcoded values, code quality, data population, and documentation. The research found that 15 of 17 items require NO new dependencies — only internal refactoring. Two test libraries (aioresponses, vcrpy) are recommended as dev dependencies to enable integration tests with recorded API responses.

The key architectural insight is that v1.2 should prioritize config-driven patterns (fiscal year, file paths) as the foundation, then layer resilience improvements (circuit breaker) and testing infrastructure on top. The existing 287-test suite provides strong regression coverage, making incremental refactoring safe. The critical risk is breaking the production pipeline through incomplete migrations (e.g., moving 5 of 6 FY26 references to config but missing one, resulting in mixed-year data).

Estimated scope: ~585 LOC changed across ~20 files. All changes are backward-compatible with defaults. No breaking changes to the daily scan workflow or weekly packet generation.

## Key Findings

### Stack Additions (Minimal)

**Add to dev dependencies only:**
- **aioresponses >=0.7.8**: Mock aiohttp in integration tests (pytest-native, async-compatible)
- **vcrpy >=8.1.1**: Record/replay HTTP cassettes (optional, for live API response capture)

**Add to source (NO new dependencies):**
- **src/circuit_breaker.py** (~40 lines): Per-source circuit breaker for BaseScraper. Hand-rolled because the project needs exactly 30 lines and existing libraries are either sync-only (pybreaker) or unmaintained (aiobreaker).
- **src/fiscal.py** (~25 lines): US federal fiscal year utilities (fy_start, fy_end, fy_label). No need for the `fiscalyear` library — it's 3 lines of math.
- **src/paths.py** (~45 lines): Frozen dataclass for centralized path config. Uses stdlib only (dataclasses + pathlib).

**DO NOT ADD:**
- circuitbreaker, pybreaker, aiobreaker (trivial to implement)
- fiscalyear (overkill for US federal FY)
- pydantic, dynaconf (config already JSON-driven)

### Fix Definitions (17 Items)

**Category 1: Testing Gaps**
- TD-01 (scraper integration tests): Done = pytest.mark.live tests exist, skip gracefully when API unavailable
- TD-14 (CONGRESS_API_KEY docs): Done = README documents that key is optional, what degrades without it

**Category 2: Hardcoded Values**
- TD-02 (FY26 dates): Done = single config.fiscal_year source, all 6+ hardcoded locations read from config
- TD-03 (graph_schema path): Done = config.paths section exists, all 7+ hardcoded Path() literals read from config
- TD-12 (ROADMAP header): Done = v1.0-ROADMAP.md shows 30/30 not 31/31

**Category 3: Code Quality**
- TD-06 (logger naming): Done = economic.py uses "tcr_scanner.packets.economic" not src.packets.economic
- TD-07 (format_dollars duplicate): Done = shared utility exists, both modules import from it
- TD-08 (program fields): Done = all 16 programs audited for access_type/funding_type/cfda accuracy
- TD-13 (circuit breaker): Done = BaseScraper has per-source breaker, trips after N exhausted-retry failures (not individual 429s)

**Category 4: Data Population**
- TD-04 (award cache): Done = CLI --refresh-cache awards works, populates 592 files via USASpending API
- TD-05 (hazard profiles): Done = CLI --refresh-cache hazards works, documents manual FEMA/USFS download steps

**Category 5: Documentation**
- TD-09 (Phase 8 VERIFICATION.md): Done = file exists, references 6 plan summaries as evidence
- TD-10 (GitHub Pages deploy): Done = README has deployment steps, .github/workflows/generate-packets.yml committed
- TD-11 (SquareSpace URL): Done = README documents placeholder replacement step
- TD-15 (v1.0 summaries): Done = verified all phase VERIFICATION files exist (no gaps found)
- TD-16 (PROJECT.md counts): Done = counts match reality (authorities, barriers, LOC, tests)
- TD-17 (MILESTONES.md update): Done = v1.1 "What's next" section references v1.2

### Architecture Integration

The TCR scanner has two subsystems that share configuration but run independently:
1. **Daily scan pipeline** (main.py -> scrapers -> normalize -> graph -> monitors -> reports)
2. **Packet generation pipeline** (main.py --prep-packets -> orchestrator -> DocxEngine)

Tech debt fixes integrate as follows:

**Config layer (foundation):**
- Add fiscal_year + paths sections to scanner_config.json
- All modules read from config instead of hardcoding

**Scraper layer (resilience):**
- Circuit breaker wraps BaseScraper._request_with_retry()
- Per-source state (4 breakers: Federal Register, Grants.gov, Congress.gov, USASpending)
- Trips after 5 consecutive exhausted-retry failures (NOT 429 rate-limit responses)

**CLI layer (automation):**
- --refresh-cache [all|awards|hazards|congress] command
- Orchestrates existing TribalAwardMatcher + HazardProfileBuilder code

**Test layer (verification):**
- Integration tests with @pytest.mark.integration (excluded from default pytest)
- aioresponses mocks for deterministic CI
- VCR.py cassettes for live API response regression (optional)

### Critical Pitfalls (Top 5)

1. **Circuit breaker trips on 429 rate-limit responses**: The existing retry logic already handles 429 with Retry-After headers and does NOT count these as failures. The circuit breaker must exempt 429s or it will trip during normal USASpending batch operations. **Fix:** Only count exhausted-retry final-failures, not intermediate retry attempts.

2. **Partial FY26 migration leaves mixed-year data**: "FY26" appears in 6+ files (usaspending.py dates, docx_sections.py titles, graph/builder.py labels). Missing one location means reports show FY26 in some sections, FY27 in others. **Fix:** Single config.fiscal_year source, derive all dates/labels from it, grep verification post-migration.

3. **Hardcoded paths resolve against CWD not project root**: All relative Path() literals work locally (CWD = project root) but break if run from a different directory. **Fix:** Anchor all paths to PROJECT_ROOT = Path(__file__).resolve().parent.parent in main.py.

4. **Logger name changes break silent observability**: v1.0 uses logging.getLogger(__name__), v1.1 uses "tcr_scanner.packets.*". Unifying these changes logger hierarchy and breaks any external log filtering. **Fix:** Pick one convention (__name__ recommended), single commit, test with before/after --dry-run --verbose diff.

5. **Windows backslash paths in JSON fail on Linux CI**: scanner_config.json edited on Windows might use "data\\award_cache" which creates a single directory named "data\award_cache" on Linux. **Fix:** Mandate forward slashes in config, normalize on read.

## Implications for Roadmap

### Suggested Phase Structure (5 Phases)

Based on dependency analysis and risk assessment:

#### Phase 1: Config Foundation
**Rationale:** Fiscal year and path config are both "add config fields, update consumers" patterns. They share risk profile and can be done together. Config changes are backward-compatible (new fields with defaults). This phase establishes patterns for all subsequent changes.

**Delivers:**
- scanner_config.json with fiscal_year + paths sections
- src/fiscal.py utility (~25 lines)
- src/paths.py utility (~45 lines)
- All 6+ FY26 hardcoded locations read from config
- All 7+ hardcoded Path() literals read from config

**Addresses:**
- TD-02 (FY26 dates)
- TD-03 (graph_schema path)

**Avoids:** C-3 (partial FY migration), C-4 (CWD path assumptions)

**Complexity:** MEDIUM (many files but each change is small string substitution)

#### Phase 2: Code Quality Cleanup
**Rationale:** Quick wins that build momentum. No dependencies on Phase 1. Can be done in parallel or immediately after. These are 1-line to 15-line changes with zero regression risk.

**Delivers:**
- TD-06 fixed (logger naming consistency)
- TD-07 fixed (_format_dollars deduplicated)
- TD-08 fixed (program fields audited)
- TD-12 fixed (ROADMAP header count)

**Addresses:**
- Logger naming inconsistency
- Duplicate utility functions
- Data quality in program_inventory.json

**Complexity:** LOW (4 trivial fixes, ~30 LOC total)

#### Phase 3: Circuit Breaker Resilience
**Rationale:** After config is in place, the circuit breaker can optionally read thresholds from config. This is the highest-risk behavioral change — isolating it to a single phase makes it easy to test and revert if needed.

**Delivers:**
- src/circuit_breaker.py (~40 lines)
- Integration with BaseScraper._request_with_retry()
- Per-source breakers (4 total)
- Configurable thresholds (optional)

**Addresses:**
- TD-13 (circuit breaker)

**Avoids:** C-1 (circuit trips on 429s), M-5 (batch run behavior)

**Complexity:** LOW-MEDIUM (isolated to base.py, transparent to subclasses)

#### Phase 4: Test Infrastructure
**Rationale:** With all production changes in place (config, circuit breaker), establish integration test patterns. This phase is test-only — no production code changes except optional session injection in BaseScraper.

**Delivers:**
- tests/conftest.py with aioresponses fixtures
- tests/fixtures/ with recorded API responses
- tests/test_scraper_integration.py (@pytest.mark.integration)
- pytest.ini with integration marker config

**Addresses:**
- TD-01 (scraper integration tests)
- TD-14 (CONGRESS_API_KEY docs)

**Avoids:** M-2 (flaky CI)

**Complexity:** MEDIUM (new test patterns, ~150 LOC)

#### Phase 5: Automation & Documentation
**Rationale:** Last phase wraps up CLI automation and documentation. Depends on config paths from Phase 1. All code changes are additive (no modification to existing functionality).

**Delivers:**
- CLI --refresh-cache command
- Cache orchestration (award, hazard, congress)
- All 7 documentation items (TD-09 through TD-17)

**Addresses:**
- TD-04 (award cache)
- TD-05 (hazard profiles)
- TD-09 through TD-17 (documentation)

**Avoids:** M-3 (cache schema issues)

**Complexity:** MEDIUM (CLI wiring + docs, ~110 LOC code + 6 doc files)

### Phase Ordering Rationale

- **Config first** because fiscal year and paths are referenced by multiple later phases
- **Code quality second** because quick wins build momentum and don't depend on config
- **Circuit breaker third** because it benefits from config patterns established in Phase 1
- **Tests fourth** because they validate all prior phases without changing production code
- **Automation last** because it builds on config paths and can test against the full pipeline

### Research Flags

**Phases needing deeper research:** NONE. All 17 items verified against source code. Patterns are standard Python refactoring (config extraction, path resolution, async mocking).

**Phases with standard patterns (skip research-phase):** ALL 5. The STACK/FEATURES/ARCHITECTURE/PITFALLS research covered all technical unknowns.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All recommendations verified on PyPI, official docs, codebase inspection |
| Features | HIGH | All 17 debt items traced to source code locations with line numbers |
| Architecture | HIGH | Complete file dependency graph, integration points mapped |
| Pitfalls | HIGH | Critical pitfalls verified by reading existing retry logic, path resolution, logger usage |

**Overall confidence:** HIGH

### Gaps to Address

1. **Circuit breaker threshold tuning**: Research recommends failure_threshold=5 and reset_timeout=60s based on federal API patterns, but actual tuning requires production observation. Mitigate by making these configurable (Phase 1 config patterns support this).

2. **Integration test VCR.py cassette management**: Research identified vcrpy as the right tool, but the project must decide whether to commit cassettes to git or regenerate them periodically. Decision deferred to Phase 4 execution.

3. **Logger naming final convention**: Research recommends `__name__` for all modules, but the team must verify no external log parsing depends on the current `tcr_scanner.packets.*` format. Validate during Phase 2.

None of these gaps block planning or execution — they're tuning decisions to be made during implementation.

## Sources

### Primary (HIGH confidence)
- Direct reading of all 52 source files in src/
- Direct reading of all 13 test files in tests/
- config/scanner_config.json structure
- .github/workflows/ daily-scan.yml and generate-packets.yml
- [aioresponses 0.7.8 on PyPI](https://pypi.org/project/aioresponses/)
- [VCR.py 8.1.1 on PyPI](https://pypi.org/project/vcrpy/)
- [Python logging docs](https://docs.python.org/3/library/logging.html)
- [Python pathlib docs](https://docs.python.org/3/library/pathlib.html)

### Secondary (MEDIUM confidence)
- [aiobreaker on GitHub](https://github.com/arlyon/aiobreaker) — async circuit breaker evaluation
- [pybreaker on GitHub](https://github.com/danielfm/pybreaker) — sync circuit breaker (rejected)
- Circuit breaker + retry pattern best practices (Atomic Object blog)

### Tertiary (LOW confidence)
- Half-open state behavior for federal API 429 patterns (inferred, needs production validation)

---
*Research completed: 2026-02-11*
*Ready for roadmap: yes*
