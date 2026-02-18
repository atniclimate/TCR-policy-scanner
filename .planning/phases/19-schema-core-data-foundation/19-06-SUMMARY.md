# Phase 19 Plan 06: Integration & XCUT-04 Compliance Tests Summary

**One-liner:** Cross-plan integration tests verifying schema-builder contracts, tier boundary mapping, vocabulary-enum alignment, FY26 regression guard, and AST-based XCUT-04 encoding/atomic-write compliance scanning across all Phase 19 artifacts.

## Frontmatter

| Key | Value |
|-----|-------|
| phase | 19 |
| plan | 06 |
| subsystem | tests, schemas, packets, vocabulary |
| tags | integration-tests, xcut-04, encoding, atomic-writes, ast-scanning, regression-guard, compliance |
| requires | 19-01 (path constants, doc_types, context), 19-02 (vulnerability schemas), 19-03 (vocabulary), 19-04 (NRI expanded builder), 19-05 (SVI builder) |
| provides | 53 integration + compliance tests (40 cross-plan integration, 13 XCUT-04 compliance) |
| affects | Phase 20+ (new builders must pass encoding/atomic-write scans), all future doc_types changes (FY regression guard) |
| tech-stack.added | None (uses stdlib ast module for source analysis) |
| tech-stack.patterns | AST-based static analysis for encoding compliance, parametrized tier boundary testing |
| duration | ~8 minutes |
| completed | 2026-02-18 |

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Phase 19 cross-plan integration tests | 74bd23f | tests/test_phase19_integration.py |
| 2 | XCUT-04 encoding and atomic write compliance tests | 1add2be | tests/test_xcut04_encoding.py |

## Key Files

### Created
- `tests/test_phase19_integration.py` -- 40 tests across 6 test classes: schema imports (3), builder-to-schema contracts (5), tier boundary mapping (12), vocabulary integrity (4), dynamic fiscal year (6), path constants (10)
- `tests/test_xcut04_encoding.py` -- 13 tests across 3 test classes: encoding compliance via AST scanning (4), atomic write pattern verification (6), existing file compliance (3)

### Modified
- None

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| 19-06-DEC-01 | Only check Doc B/D headings (not Doc A/C/E) for FORBIDDEN_DOC_B_TERMS | Internal-facing headings (Doc A/C/E) intentionally use strategy terms like "Investment Profile" and EXPOSURE_CONTEXT uses "disproportionate" -- these are correct for internal audiences. Only congressional-facing headings (Doc B/D) must avoid forbidden terms. |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Adjusted Doc B forbidden terms test scope**

- **Found during:** Task 1 initial test run
- **Issue:** Plan specified checking all SECTION_HEADINGS, RATING_LABEL, and EXPOSURE_CONTEXT against FORBIDDEN_DOC_B_TERMS. However, Doc A/C headings intentionally contain "Investment Profile" (a forbidden Doc B term) because those are internal strategy documents. EXPOSURE_CONTEXT ("disproportionate exposure") is also internal-only. Checking all constants against Doc B terms would create a false failure.
- **Fix:** Narrowed test to only check Doc B and Doc D headings (the congressional-audience constants) against FORBIDDEN_DOC_B_TERMS. This matches the architectural intent: forbidden terms apply to congressional output, not internal strategy documents.
- **Files modified:** tests/test_phase19_integration.py
- **Commit:** 74bd23f (included in Task 1 commit after fix)

## Test Results

| Metric | Value |
|--------|-------|
| Baseline tests (before) | 1204 passed, 1 skipped |
| New tests added | 53 (40 integration + 13 XCUT-04) |
| Final test count | 1257 passed, 1 skipped |
| Test execution time (new only) | 0.36s |
| Full suite execution time | ~118s |

### Test Class Breakdown

**test_phase19_integration.py (40 tests):**
- TestSchemaImports: 3 tests -- import paths, re-exports, circular import detection
- TestSchemaToBuilderContract: 5 tests -- NRI/SVI/Composite validation, VulnerabilityProfile assembly, optional sub-profiles
- TestTierMapping: 12 tests -- 10 parametrized boundary scores, Tribe-favorable 0.80 rule, all-tiers-reachable
- TestVocabularyIntegrity: 4 tests -- GAP_MESSAGES-enum alignment, TIER_DISPLAYS-enum alignment, no raw "vulnerability" in headings, Doc B/D heading compliance
- TestDynamicFiscalYear: 6 tests -- DOC_A/B/C/D title templates, format_filename, FY26 regression guard (file scan)
- TestPathConstants: 10 tests -- 6 paths under DATA_DIR, helper function, context default, paths.py import-time safety (AST)

**test_xcut04_encoding.py (13 tests):**
- TestEncodingCompliance: 4 tests -- AST scan of nri_expanded.py, svi_builder.py, vocabulary.py, vulnerability.py for open() without encoding=
- TestAtomicWriteCompliance: 6 tests -- os.replace(), tempfile import, contextlib.suppress(OSError) in both builders
- TestExistingFileCompliance: 3 tests -- format_filename dynamic FY, paths.py constants-only, doc_types dynamic titles

## Phase 19 Completion Status

Plan 19-06 is the final plan in Phase 19. All 6 plans are now complete:

| Plan | Name | Tests Added | Status |
|------|------|-------------|--------|
| 19-01 | Dynamic FY & Path Constants | 8 | COMPLETE |
| 19-02 | Vulnerability Schemas | 112 | COMPLETE |
| 19-03 | Vocabulary Constants | 63 | COMPLETE |
| 19-04 | NRI Expanded Builder | 57 | COMPLETE |
| 19-05 | SVI Builder | 54 | COMPLETE |
| 19-06 | Integration & XCUT-04 Tests | 53 | COMPLETE |

**Phase 19 total:** 6 plans complete, 1257 tests (all passing), 1 skipped.

## Next Phase Readiness

Phase 19 (Schema & Core Data Foundation) is COMPLETE. All schemas, builders, vocabulary, path constants, and integration tests are in place.

**Ready for Phase 20 (Flood & Water Data):**
- VulnerabilityProfile schema ready to accept flood data components
- NRIExpandedBuilder and SVIProfileBuilder patterns established for new builders
- XCUT-04 compliance tests will catch encoding violations in new Phase 20 files
- FY26 regression guard will catch any hardcoded fiscal years in new src/packets/ files
