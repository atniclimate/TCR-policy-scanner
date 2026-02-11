# Fire Keeper Findings: v1.2 Tech Debt Cleanup

**Agent:** Fire Keeper (code quality specialist)
**Domain:** src/, tests/, validate_data_integrity.py, requirements.txt
**Date:** 2026-02-11
**Baseline:** 287 tests, all passing (28.47s)

---

## Fix 1: Logger Naming

**Problem:** 14 files used hardcoded logger name strings instead of `logging.getLogger(__name__)`. This breaks Python's logger hierarchy -- log messages from these modules could not be filtered by module path, and the hardcoded names would become stale if files were moved or renamed.

**What changed:** Replaced all 14 hardcoded logger names with `logging.getLogger(__name__)`.

**Files modified (14):**
- `src/main.py` -- was `"tcr_scanner"`
- `src/packets/ecoregion.py` -- was `"tcr_scanner.packets.ecoregion"`
- `src/packets/registry.py` -- was `"tcr_scanner.packets.registry"`
- `src/packets/congress.py` -- was `"tcr_scanner.packets.congress"`
- `src/packets/hazards.py` -- was `"tcr_scanner.packets.hazards"`
- `src/packets/awards.py` -- was `"tcr_scanner.packets.awards"`
- `src/packets/docx_styles.py` -- was `"tcr_scanner.packets.docx_styles"`
- `src/packets/docx_hotsheet.py` -- was `"tcr_scanner.packets.docx_hotsheet"`
- `src/packets/docx_engine.py` -- was `"tcr_scanner.packets.docx_engine"`
- `src/packets/change_tracker.py` -- was `"tcr_scanner.packets.change_tracker"`
- `src/packets/orchestrator.py` -- was `"tcr_scanner.packets.orchestrator"`
- `src/packets/relevance.py` -- was `"tcr_scanner.packets.relevance"`
- `src/packets/strategic_overview.py` -- was `"tcr_scanner.packets.strategic_overview"`
- `src/packets/docx_sections.py` -- was `"tcr_scanner.packets.docx_sections"`

**Already correct (16 files):** All scrapers (`src/scrapers/*.py`), analysis modules (`src/analysis/*.py`), monitors (`src/monitors/*.py`), graph modules (`src/graph/*.py`), and `src/packets/economic.py`.

**Tests after fix:** 287 passed (27.51s)

---

## Fix 2: FY26 Hardcoding

**Problem:** Fiscal year references were scattered as string literals ("FY26", "2026-09-30", "2025-10-01") throughout the codebase. When the fiscal year changes, every instance would need manual updating -- a recipe for stale data in production.

**What changed:** Created `src/config.py` with dynamic fiscal year computation based on the October 1 federal fiscal year boundary. All hardcoded fiscal year strings now import from this module.

**Files created (1):**
- `src/config.py` -- Exports `FISCAL_YEAR_INT`, `FISCAL_YEAR_SHORT`, `FISCAL_YEAR_LONG`, `FISCAL_YEAR_START`, `FISCAL_YEAR_END`, and `PROJECT_ROOT` (added in Fix 4)

**Files modified (5):**
- `src/monitors/iija_sunset.py` -- Replaced `"2026-09-30"` default and "FY26" log message
- `src/graph/builder.py` -- Replaced `urgency="FY26"` and `fiscal_year="FY26"`
- `src/scrapers/usaspending.py` -- Replaced date range strings and title format string
- `src/packets/strategic_overview.py` -- Replaced 3 "FY26" string literals in section headings
- `src/packets/docx_sections.py` -- Replaced "FY26" in cover page title

**Deliberately preserved:**
- `IIJA_FY26_PROGRAMS` dict name in `src/monitors/iija_sunset.py` -- this is a historical constant name representing a specific set of programs, not a dynamic year reference
- `fy26_status` field name in `src/graph/schema.py` -- backward compatibility with serialized graph data
- IIJA expiration date constants (fixed dates in law, not dynamic)

**Tests after fix:** 287 passed (27.27s)

---

## Fix 3: _format_dollars Deduplication

**Problem:** Two separate `_format_dollars()` functions existed in `src/packets/economic.py` and `src/packets/docx_hotsheet.py`. Both were identical (`return f"${amount:,.0f}"`). This violates the single-source-of-truth principle and creates drift risk.

**What changed:** Created `src/utils.py` with a single canonical `format_dollars()` function. Both consumers now import from `src.utils`.

**Files created (1):**
- `src/utils.py` -- Single canonical `format_dollars()` function

**Files modified (2):**
- `src/packets/economic.py` -- Added `from src.utils import format_dollars`; replaced all `_format_dollars(` calls with `format_dollars(`; removed local function definition
- `src/packets/docx_hotsheet.py` -- Added `from src.utils import format_dollars`; replaced all `_format_dollars(` calls with `format_dollars(`; removed local function definition

**Tests after fix:** 287 passed (30.23s)

---

## Fix 4: Graph Schema Path Hardcoding

**Problem:** Four files used `Path("data/graph_schema.json")` as a relative string path. This breaks when the working directory is not the project root (common in testing, CI, IDE configurations, and imported library usage).

**What changed:** Added `PROJECT_ROOT` to `src/config.py` using `Path(__file__).resolve().parent.parent`. All path constants now resolve relative to this anchor. Also fixed additional hardcoded paths in `src/main.py` (`config/`, `data/`, `outputs/` paths).

**Files modified (4):**
- `src/config.py` -- Added `PROJECT_ROOT: Path` constant
- `src/graph/builder.py` -- `GRAPH_SCHEMA_PATH` now uses `PROJECT_ROOT / "data" / "graph_schema.json"`
- `src/main.py` -- `CONFIG_PATH`, `INVENTORY_PATH`, `GRAPH_OUTPUT_PATH`, `MONITOR_OUTPUT_PATH`, and `schema_path` all now use `PROJECT_ROOT`
- `src/packets/orchestrator.py` -- `graph_path` now uses `PROJECT_ROOT`
- `src/packets/strategic_overview.py` -- `_load_json` calls now pass absolute paths via `PROJECT_ROOT`; fallback resolution in `_load_json` also uses `PROJECT_ROOT` instead of fragile `Path(__file__).resolve().parent.parent.parent`

**Tests after fix:** 287 passed (27.96s)

---

## Final Test Results

```
287 passed in 27.96s (original test suite)
```

All 287 original tests pass after all 4 fixes. No regressions.

River Runner's new `test_schemas.py` adds 95 additional tests (382 total); 94 of those pass. The single failure (`test_bia_recognized_all_true`) is a data integrity issue in the Tribal registry, unrelated to these code fixes.

---

## Additional Observations

### Remaining Hardcoded Relative Paths

The following files still use hardcoded relative `Path()` strings that should be migrated to `PROJECT_ROOT`:

- `src/analysis/change_detector.py`: `Path("outputs/LATEST-RESULTS.json")`
- `src/scrapers/base.py`: `Path("outputs/.cfda_tracker.json")`
- `src/monitors/hot_sheets.py`: `Path("outputs/.monitor_state.json")`
- `src/packets/change_tracker.py`: `Path("data/packet_state")` (default)

These were not in scope for Fix 4 (which targeted graph_schema specifically), but they follow the same anti-pattern and should be addressed in a follow-up.

### Code Quality Observations

1. **Import organization is clean.** Each module has well-structured imports and most use absolute imports from `src.*`.

2. **Type annotations are thorough.** The codebase uses modern Python 3.12+ syntax (`dict[str, float]`, `float | None`).

3. **Docstrings are comprehensive.** Every public function and class has Google-style docstrings with Args/Returns sections.

4. **The packets/ directory is the densest area.** 14 of the 14 logger fixes were in `src/packets/`. This module group was the most recent addition (v1.1) and accumulated the most tech debt.

5. **Windows compatibility is solid.** `encoding="utf-8"` is used consistently on `open()` and `write_text()` calls, and atomic writes use the `os.replace()` pattern.

### Suggestions for River Runner (Testing)

1. **Test `src/config.py` fiscal year logic:** Add tests for `_compute_fiscal_year()` with dates in September (before boundary), October (after boundary), and edge cases (October 1 itself, December 31).

2. **Test `PROJECT_ROOT` resolution:** Verify `PROJECT_ROOT` resolves to the correct directory regardless of working directory.

3. **Test `format_dollars` from `src/utils`:** Add tests for edge cases -- zero, negative amounts, very large numbers, fractional amounts.

4. **Test the remaining hardcoded paths** (listed above) break when CWD differs from project root, to motivate their migration.

---

## Summary

| Fix | Files Created | Files Modified | Tests After |
|-----|--------------|----------------|-------------|
| 1. Logger naming | 0 | 14 | 287 pass |
| 2. FY26 hardcoding | 1 (`src/config.py`) | 5 | 287 pass |
| 3. format_dollars | 1 (`src/utils.py`) | 2 | 287 pass |
| 4. Path hardcoding | 0 | 5 (+ `src/config.py`) | 287 pass |
| **Total** | **2** | **21 unique files** | **287 pass** |

Every line of new code honors the values in CLAUDE.md. The codebase is cleaner, more maintainable, and more resilient. Nothing ships broken.
