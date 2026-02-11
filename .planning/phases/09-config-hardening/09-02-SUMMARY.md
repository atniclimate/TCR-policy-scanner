# Phase 9 Plan 2: Packets/Tests/Scripts Path Migration Summary

**One-liner:** Migrated all 20 remaining files (9 packets, 4 tests, 4 scripts, 3 test helpers) to import path constants from src/paths.py; zero hardcoded path strings remain in any source file.

## Performance

- **Duration:** ~5 minutes
- **Completed:** 2026-02-11
- **Tests:** 383 passed (0 failed, 0 skipped)

## Accomplishments

1. **Packets subsystem fully migrated (9 files):** Removed all `_DEFAULT_*` path constants and `Path(__file__).resolve().parent.parent.parent` constructions from ecoregion.py, registry.py, congress.py, awards.py, hazards.py, docx_engine.py, change_tracker.py, orchestrator.py, and strategic_overview.py
2. **Test files migrated (4 files):** Replaced local `PROJECT_ROOT` definitions and ad-hoc `Path(...)` constructions in test_schemas.py, test_docx_integration.py, test_doc_assembly.py; test_strategic_overview.py needed no changes (uses tmp_path mocks)
3. **Script files migrated (4 files):** Added `sys.path` insertion and `src.paths` imports to build_registry.py, build_congress_cache.py, build_tribal_aliases.py, build_web_index.py
4. **Backward compatibility preserved:** All config-overridable paths use `Path(raw) if raw else CONSTANT` pattern -- existing `scanner_config.json` overrides still work via PROJECT_ROOT resolution for relative paths
5. **Regression verification confirmed zero violations** across 5 grep checks (hardcoded directory strings, independent PROJECT_ROOT definitions, bare relative Path() construction, stale _DEFAULT_ constants, tests defining own PROJECT_ROOT)

## Task Commits

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Migrate packets subsystem to src/paths imports | fb61466 | src/packets/{ecoregion,registry,congress,awards,hazards,docx_engine,change_tracker,orchestrator,strategic_overview}.py |
| 2 | Migrate tests and scripts to src/paths imports | eb52987 | tests/{test_schemas,test_docx_integration,test_doc_assembly}.py, scripts/{build_registry,build_congress_cache,build_tribal_aliases,build_web_index}.py |

## Files Modified

- `src/packets/ecoregion.py` -- Replaced _DEFAULT_CONFIG_PATH with ECOREGION_CONFIG_PATH import
- `src/packets/registry.py` -- Replaced _DEFAULT_DATA_PATH with TRIBAL_REGISTRY_PATH import
- `src/packets/congress.py` -- Replaced _DEFAULT_CACHE_PATH with CONGRESSIONAL_CACHE_PATH import
- `src/packets/awards.py` -- Replaced _DEFAULT_ALIAS_PATH + _DEFAULT_CACHE_DIR with TRIBAL_ALIASES_PATH + AWARD_CACHE_DIR
- `src/packets/hazards.py` -- Replaced 4 _DEFAULT_* constants with AIANNH_CROSSWALK_PATH, NRI_DIR, USFS_DIR, HAZARD_PROFILES_DIR; simplified _resolve_path to use PROJECT_ROOT
- `src/packets/docx_engine.py` -- Replaced hardcoded "outputs/packets" with PACKETS_OUTPUT_DIR
- `src/packets/change_tracker.py` -- Replaced Path("data/packet_state") with PACKET_STATE_DIR
- `src/packets/orchestrator.py` -- Replaced 5 ad-hoc path constructions with AWARD_CACHE_DIR, HAZARD_PROFILES_DIR, PACKET_STATE_DIR, GRAPH_SCHEMA_PATH, PACKETS_OUTPUT_DIR; removed `from src.config import PROJECT_ROOT`
- `src/packets/strategic_overview.py` -- Replaced PROJECT_ROOT / "data/..." constructions with POLICY_TRACKING_PATH, GRAPH_SCHEMA_PATH, LATEST_MONITOR_DATA_PATH
- `tests/test_schemas.py` -- Replaced local PROJECT_ROOT + 6 ad-hoc path constructions with src.paths imports
- `tests/test_docx_integration.py` -- Replaced Path("config/...") and Path(__file__).parent.parent
- `tests/test_doc_assembly.py` -- Replaced Path(__file__).parent.parent with PROJECT_ROOT import
- `scripts/build_registry.py` -- Added sys.path insert, replaced default with TRIBAL_REGISTRY_PATH
- `scripts/build_congress_cache.py` -- Replaced 4 hardcoded defaults with centralized path constants
- `scripts/build_tribal_aliases.py` -- Replaced 2 module constants with centralized path constants
- `scripts/build_web_index.py` -- Replaced 3 module constants with centralized path constants

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| DEC-0902-01 | Scripts use sys.path insertion pattern for src.paths access | Scripts in `scripts/` are standalone entry points not run as modules; sys.path.insert(0, PROJECT_ROOT) is the idiomatic way to make `src` importable |
| DEC-0902-02 | Config-overridable paths use `Path(raw) if raw else CONSTANT` pattern | Preserves backward compatibility -- if scanner_config.json provides a path string, it takes priority; otherwise the centralized constant is used |
| DEC-0902-03 | Docstring path references left as-is | Strings in docstrings (e.g., `Defaults to ``Path("data/packet_state")``.`) serve documentation purposes and are not executable path constructions |

## Deviations from Plan

None -- plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

Phase 9 (Config Hardening) is **100% complete**. Both plans delivered:
- 09-01: Created `src/paths.py` + migrated 7 core pipeline files
- 09-02: Migrated 9 packets + 4 tests + 4 scripts + regression verification

**Phase 9 success criteria met:**
1. Zero hardcoded path strings in `src/` (verified by 5 grep regression checks)
2. Centralized `src/paths.py` module exists with 30+ constants covering all project paths
3. Changing a data directory location in `src/paths.py` propagates to all consumers
4. All 383 tests pass after refactoring

**Ready for:** Phase 10 (Code Quality) and/or any Wave 2 phases
