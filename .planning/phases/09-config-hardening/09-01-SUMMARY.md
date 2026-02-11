---
phase: 9
plan: 1
subsystem: core-infrastructure
tags: [paths, config, refactor, pathlib, centralization]
requires: []
provides: [centralized-paths-module, project-root-constant, path-helpers]
affects: [09-02, 10-01, 10-02, 11-01, 12-01, 13-01, 14-01]
tech-stack:
  added: []
  patterns: [centralized-path-constants, import-based-path-resolution]
key-files:
  created: [src/paths.py]
  modified: [src/config.py, src/main.py, src/graph/builder.py, src/reports/generator.py, src/analysis/change_detector.py, src/scrapers/base.py, src/monitors/hot_sheets.py]
decisions:
  - id: DEC-0901-01
    summary: "src/paths.py imports only pathlib.Path -- zero project imports to prevent circular dependencies"
  - id: DEC-0901-02
    summary: "src/config.py re-exports PROJECT_ROOT via __all__ for backward compatibility during transition"
  - id: DEC-0901-03
    summary: "Removed unused 'from pathlib import Path' imports from main.py, base.py, hot_sheets.py, generator.py where Path was no longer directly referenced"
metrics:
  duration: "5m01s"
  completed: 2026-02-11
---

# Phase 9 Plan 1: Create src/paths.py + Migrate Core Pipeline Files Summary

**One-liner:** Centralized 162-line src/paths.py with PROJECT_ROOT, 25 path constants, 3 helper functions; migrated 7 core pipeline files from ad-hoc paths to imports.

## Performance

| Metric | Value |
|--------|-------|
| Duration | 5m01s |
| Start | 2026-02-11T07:13:49Z |
| End | 2026-02-11T07:18:50Z |
| Tasks | 2/2 |
| Tests | 383/383 passing |

## Accomplishments

1. **Created `src/paths.py`** (162 lines) -- the single source of truth for all file and directory paths in the project. Contains PROJECT_ROOT, 25 named path constants organized by section (config, data flat files, data subdirectories, outputs, docs, scripts), and 3 helper functions for per-Tribe paths (award_cache_path, hazard_profile_path, packet_state_path).

2. **Migrated 7 core pipeline files** to import from `src.paths` instead of constructing paths ad-hoc:
   - `src/config.py` -- removed local PROJECT_ROOT definition, imports from paths, re-exports via __all__
   - `src/main.py` -- replaced 4 local path definitions (CONFIG_PATH, INVENTORY_PATH, GRAPH_OUTPUT_PATH, MONITOR_OUTPUT_PATH) + 1 inline schema_path with 5 imports from src.paths
   - `src/graph/builder.py` -- replaced local GRAPH_SCHEMA_PATH definition with import
   - `src/reports/generator.py` -- replaced 3 local definitions (OUTPUTS_DIR, ARCHIVE_DIR, CI_HISTORY_PATH)
   - `src/analysis/change_detector.py` -- replaced CACHE_FILE with LATEST_RESULTS_PATH (all references updated)
   - `src/scrapers/base.py` -- replaced local CFDA_TRACKER_PATH definition with import
   - `src/monitors/hot_sheets.py` -- replaced local MONITOR_STATE_PATH definition with import

3. **Cleaned up unused imports** -- removed `from pathlib import Path` from 4 files where Path was no longer directly referenced (main.py, generator.py, base.py, hot_sheets.py). Kept it in change_detector.py where Path is used as a type annotation.

## Task Commits

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Create src/paths.py | 2c440a6 | src/paths.py |
| 2 | Migrate core pipeline files | af30cde | src/config.py, src/main.py, src/graph/builder.py, src/reports/generator.py, src/analysis/change_detector.py, src/scrapers/base.py, src/monitors/hot_sheets.py |

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| src/paths.py | 162 | Centralized path constants and helper functions |

## Files Modified

| File | Change |
|------|--------|
| src/config.py | Import PROJECT_ROOT from paths, add __all__, remove local definition |
| src/main.py | Import 5 constants from paths, remove 4 local defs + 1 inline path |
| src/graph/builder.py | Import GRAPH_SCHEMA_PATH, remove local definition |
| src/reports/generator.py | Import 3 constants, remove 3 local definitions |
| src/analysis/change_detector.py | Import LATEST_RESULTS_PATH, rename CACHE_FILE throughout |
| src/scrapers/base.py | Import CFDA_TRACKER_PATH, remove local definition |
| src/monitors/hot_sheets.py | Import MONITOR_STATE_PATH, remove local definition |

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| DEC-0901-01 | paths.py imports only pathlib.Path | Prevents circular imports since paths.py is imported by config.py and many other modules |
| DEC-0901-02 | config.py re-exports PROJECT_ROOT via __all__ | Backward compatibility -- existing `from src.config import PROJECT_ROOT` still works |
| DEC-0901-03 | Removed unused pathlib imports from 4 files | Clean code -- Path was no longer directly referenced after migration |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed PROJECT_ROOT from main.py import**

- **Found during:** Task 2
- **Issue:** Plan specified importing PROJECT_ROOT in main.py, but after replacing `schema_path = PROJECT_ROOT / "data" / "graph_schema.json"` with `GRAPH_SCHEMA_PATH`, PROJECT_ROOT was no longer used in main.py
- **Fix:** Removed PROJECT_ROOT from the import statement to avoid unused import
- **Files modified:** src/main.py

**2. [Rule 2 - Missing Critical] Removed unused pathlib import from generator.py**

- **Found during:** Task 2
- **Issue:** Plan said to keep `from pathlib import Path` in generator.py because "Path IS used in the class body for Path operations", but inspection showed Path is NOT used as a constructor or type annotation -- only the imported path constants (which are already Path objects) are used
- **Fix:** Removed the unused import
- **Files modified:** src/reports/generator.py

## Issues Encountered

None.

## Verification Results

- All 383 tests pass (`python -m pytest tests/ -x -q`)
- `rg 'Path("outputs/' src/ --glob '!paths.py'` returns 0 results from migrated files
- `rg 'Path("data/' src/ --glob '!paths.py'` returns only packets/change_tracker.py (expected -- migrated in 09-02)
- `python -c "from src.paths import PROJECT_ROOT, SCANNER_CONFIG_PATH, DATA_DIR, OUTPUTS_DIR, award_cache_path; print(PROJECT_ROOT); print(award_cache_path('test'))"` prints valid paths

## Next Phase Readiness

Plan 09-02 can proceed immediately. The packets subsystem (src/packets/*), tests, and scripts still have ad-hoc path construction that should be migrated using the same pattern established here.
