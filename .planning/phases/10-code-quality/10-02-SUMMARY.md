# Phase 10 Plan 2: Ruff-Clean Codebase Summary

**One-liner:** Achieved zero ruff violations across the entire codebase by adding pyproject.toml linter config, auto-fixing 54 violations (35 unused imports, 19 placeholder f-strings), manually fixing 8 violations (7 unused variables, 1 ambiguous name), fixing 1 E402 import ordering, and redirecting the CFDA_TRACKER_PATH import chain from base.py re-export to direct src.paths import.

## Performance

- **Duration:** ~5 minutes
- **Completed:** 2026-02-11
- **Tests:** 383 passed (0 failed, 0 skipped)

## Accomplishments

1. **Created pyproject.toml with ruff configuration:**
   - target-version py312, line-length 120
   - Lint rules: E4, E7, E9, F (pyflakes + pycodestyle errors)
   - Per-file-ignores: scripts/*.py exempt from E402 (DEC-0902-01 sys.path pattern)

2. **Auto-fixed 54 violations via `ruff check --fix`:**
   - 35 F401 (unused imports) removed across 21 files
   - 19 F541 (f-strings without placeholders) converted to plain strings

3. **Fixed CFDA_TRACKER_PATH import chain:**
   - grants_gov.py previously imported CFDA_TRACKER_PATH via base.py re-export
   - Redirected to import directly from src.paths (canonical source)
   - Prevents ruff from flagging base.py import as unused

4. **Fixed E402 import ordering in src/packets/hazards.py:**
   - Moved src.paths import block above module-level code (NRI_HAZARD_CODES dict)
   - Import was placed after constant definitions, violating E402

5. **Manually fixed 8 remaining violations:**
   - validate_data_integrity.py: removed dead `expected_prog_id` assignment (F841)
   - scripts/build_congress_cache.py: removed dead `parent_id` assignment (F841)
   - tests/test_e2e_phase8.py: removed unused `original_overview` capture (F841)
   - tests/test_docx_integration.py: removed unused `original_load` capture (F841)
   - tests/test_docx_integration.py: renamed `l` to `line` in list comprehension (E741)
   - tests/test_docx_styles.py: removed unused `engine` variable, kept side-effect call (F841)
   - tests/test_strategic_overview.py: removed unused `original_generate` capture (F841)
   - tests/test_packets.py: removed unused `count` variable, kept side-effect call (F841)

## Task Commits

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Create pyproject.toml and auto-fix 54 violations | 167340f | pyproject.toml, 21 source/test files |
| 2 | Manually fix remaining F841 and E741 violations | d3c4e02 | 7 source/test files |

## Files Modified

**Created:**
- `pyproject.toml` -- Ruff linter configuration with per-file-ignores for scripts

**Modified (auto-fix, 21 files):**
- `src/main.py` -- removed unused imports, fixed f-strings
- `src/packets/docx_engine.py` -- removed unused imports
- `src/packets/docx_hotsheet.py` -- removed unused imports
- `src/packets/docx_sections.py` -- removed unused imports
- `src/packets/docx_styles.py` -- removed unused import
- `src/packets/hazards.py` -- moved import to top of file (E402), removed unused imports
- `src/packets/orchestrator.py` -- removed unused imports, fixed f-strings
- `src/reports/generator.py` -- fixed f-string
- `src/scrapers/base.py` -- removed CFDA_TRACKER_PATH re-export (now unused)
- `src/scrapers/grants_gov.py` -- redirected CFDA_TRACKER_PATH import to src.paths
- `tests/test_batch_generation.py` -- removed unused imports
- `tests/test_change_tracking.py` -- removed unused import
- `tests/test_decision_engine.py` -- removed unused import
- `tests/test_doc_assembly.py` -- removed unused import
- `tests/test_docx_hotsheet.py` -- removed unused imports
- `tests/test_docx_styles.py` -- removed unused import
- `tests/test_e2e_phase8.py` -- removed unused imports
- `tests/test_schemas.py` -- removed unused imports, fixed f-strings
- `tests/test_strategic_overview.py` -- removed unused import
- `tests/test_web_index.py` -- removed unused import
- `validate_data_integrity.py` -- removed unused import, fixed f-strings

**Modified (manual fix, 7 files):**
- `validate_data_integrity.py` -- removed dead variable assignment
- `scripts/build_congress_cache.py` -- removed dead variable assignment
- `tests/test_e2e_phase8.py` -- removed unused variable capture
- `tests/test_docx_integration.py` -- removed unused variable, renamed ambiguous `l`
- `tests/test_docx_styles.py` -- removed unused variable from side-effect call
- `tests/test_strategic_overview.py` -- removed unused variable capture
- `tests/test_packets.py` -- removed unused variable from side-effect call

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| DEC-1002-01 | E402 suppressed via per-file-ignores for scripts/*.py only | Scripts use sys.path.insert() pattern (DEC-0902-01) requiring imports after path manipulation. This is intentional, not a bug. |
| DEC-1002-02 | CFDA_TRACKER_PATH import redirected from base.py to src.paths | base.py was re-exporting from src.paths; grants_gov.py was importing through the re-export. Direct import from canonical source is cleaner and avoids ruff flagging the re-export as unused. |
| DEC-1002-03 | Unused variable assignments prefixed with _ or removed based on side effects | For pure computation (no side effects), removed entirely. For calls with side effects (DocxEngine constructor, build_all_profiles), kept the call but removed the variable assignment. |
| DEC-1002-04 | hazards.py E402 fixed by moving import above constant definitions | The src.paths import was placed after NRI_HAZARD_CODES dict definition. Moved it to join other imports at file top. Not in scripts, so per-file-ignores doesn't apply. |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] E402 in src/packets/hazards.py**

- **Found during:** Task 1
- **Issue:** src/packets/hazards.py had an E402 violation (import not at top of file) that was not covered by the scripts per-file-ignores. The plan did not mention this file needing an E402 fix.
- **Fix:** Moved the `from src.paths import ...` block above the NRI_HAZARD_CODES constant definition to join the other imports at file top.
- **Files modified:** src/packets/hazards.py
- **Commit:** 167340f (included in Task 1 commit)

## Issues Encountered

None.

## Next Phase Readiness

Phase 10 complete. Both QUAL-01 (program metadata completeness) and QUAL-02 (ruff-clean codebase) requirements are satisfied.

**Ready for:** Phase 11 (API Resilience) -- Wave 2
