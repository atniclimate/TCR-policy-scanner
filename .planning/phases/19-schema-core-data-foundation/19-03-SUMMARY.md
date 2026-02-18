---
phase: 19-schema-core-data-foundation
plan: 03
subsystem: packets
tags: [vocabulary, framing, sovereignty, constants, dataclass, air-gap]

# Dependency graph
requires:
  - phase: 18.5-architectural-review
    provides: "DEC-05 Option D Hybrid framing decisions, vocabulary analysis"
provides:
  - "SECTION_HEADINGS frozen dataclass for Doc A/B/C/D/E heading strings"
  - "RATING_LABEL sovereignty-first label constant"
  - "TIER_DISPLAYS 5-tier investment priority display config with hex colors"
  - "GAP_MESSAGES 6 data gap messages framing federal infrastructure failures"
  - "SVI_THEME3_EXCLUSION_NOTE/SHORT sovereignty framing for Theme 3 exclusion"
  - "FORBIDDEN_DOC_B_TERMS frozenset blocking strategy language in Doc B/D"
  - "CONTEXT_SENSITIVE_TERMS mapping vulnerability to federal proper nouns"
  - "EXPOSURE_CONTEXT and COMPOSITE_METHODOLOGY_BRIEF explanatory text"
affects: [19-04, 19-05, 19-06, 22, 23]

# Tech tracking
tech-stack:
  added: []
  patterns: ["frozen dataclass constants module", "sovereignty-first framing vocabulary"]

key-files:
  created:
    - src/packets/vocabulary.py
    - tests/test_vocabulary.py
  modified: []

key-decisions:
  - "Air gap tests check strategy terms (strategic, leverage, assertive) not investment terms -- 'investment profile' and 'investment priority' are DEC-05 approved heading/label terms"
  - "SOURCE_UNAVAILABLE gap message is generic (any source) and does not require federal framing -- only geographic/assessment gap messages require it"

patterns-established:
  - "Vocabulary constants as leaf module: zero project imports, frozen dataclasses, pure constants"
  - "Air gap testing: strategy terms vs. approved DEC-05 terms are distinct categories"

# Metrics
duration: 8min
completed: 2026-02-17
---

# Phase 19 Plan 03: Sovereignty-First Vocabulary Constants Summary

**Frozen dataclass vocabulary module with 9 constant groups, 52 tests, sovereignty-first framing per DEC-05 Option D Hybrid**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-02-17
- **Completed:** 2026-02-17
- **Tasks:** 2/2
- **Files created:** 2

## Accomplishments
- Created `src/packets/vocabulary.py` as a pure constants leaf module with zero project dependencies
- All 9 constant groups implemented: SECTION_HEADINGS, RATING_LABEL, TIER_DISPLAYS, GAP_MESSAGES, INLINE markers, SVI Theme 3 notes, CONTEXT_SENSITIVE_TERMS, FORBIDDEN_DOC_B_TERMS, EXPOSURE_CONTEXT/COMPOSITE_METHODOLOGY_BRIEF
- 52 tests across 10 test classes covering completeness, immutability, sovereignty framing, and air gap integrity
- Full suite passes: 1084 tests (52 new, zero regressions)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create sovereignty-first vocabulary constants module** - `cb78323` (feat)
2. **Task 2: Write comprehensive vocabulary tests** - `e83b344` (test)

## Files Created/Modified
- `src/packets/vocabulary.py` - Sovereignty-first framing vocabulary constants module (264 lines, 9 constant groups, 2 frozen dataclasses)
- `tests/test_vocabulary.py` - Comprehensive test suite (462 lines, 52 tests, 10 test classes)

## Decisions Made

1. **Air gap test semantics:** The FORBIDDEN_DOC_B_TERMS frozenset includes "investment profile" and "investment priority" (banned from Doc B body text), but these are the DEC-05 approved heading and label terms used by the rendering system. Air gap tests correctly distinguish between strategy language (never in headings) and investment-framing language (approved for headings/labels).

2. **Federal framing scope:** Only geographic/assessment gap messages (MISSING_SVI, PARTIAL_NRI, ZERO_AREA_WEIGHT, ALASKA_PARTIAL) require "federal" framing. SOURCE_UNAVAILABLE is a generic source availability message applicable to any data source and NO_COASTAL_DATA is empty.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed air gap test false positives**
- **Found during:** Task 2 (test_vocabulary.py)
- **Issue:** Three air gap tests had false positive assertions: (a) "investment profile" in FORBIDDEN set matched section headings by design, (b) "investment priority" matched RATING_LABEL by design, (c) SOURCE_UNAVAILABLE does not contain "federal" because it is a generic source message
- **Fix:** Refined test assertions to check strategy terms (strategic, leverage, assertive, etc.) separately from DEC-05 approved investment-framing terms; scoped federal framing check to geographic/assessment gap messages only
- **Files modified:** tests/test_vocabulary.py
- **Verification:** All 52 tests pass
- **Committed in:** e83b344 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug in test logic)
**Impact on plan:** Test logic correction for semantic accuracy. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Vocabulary module ready for import by schema integration (19-04, 19-05, 19-06)
- TIER_DISPLAYS provides color palette for Phase 23 document rendering
- FORBIDDEN_DOC_B_TERMS extends existing audience air gap for Phase 22/23 content filtering
- All constants importable: `from src.packets.vocabulary import SECTION_HEADINGS, RATING_LABEL, ...`

---
*Phase: 19-schema-core-data-foundation*
*Completed: 2026-02-17*
