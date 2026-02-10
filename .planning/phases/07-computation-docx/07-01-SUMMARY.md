---
phase: 07-computation-docx
plan: 01
subsystem: computation
tags: [economic-impact, bea-rims-ii, bls-employment, fema-bcr, hazard-relevance, nri]

# Dependency graph
requires:
  - phase: 06-data-acquisition
    provides: Award cache files, hazard profile cache, TribePacketContext with awards/hazard_profile fields
provides:
  - EconomicImpactCalculator with BEA multiplier ranges and FEMA BCR
  - ProgramRelevanceFilter with hazard-based 8-12 program selection
  - TribeEconomicSummary and ProgramEconomicImpact dataclasses
  - Comprehensive test suite (26 tests)
affects: [07-02 Hot Sheet DOCX rendering, 07-03 Federal Overview DOCX, 08-assembly]

# Tech tracking
tech-stack:
  added: []
  patterns: [pure-function computation modules, dataclass result types, published-multiplier methodology]

key-files:
  created:
    - src/packets/economic.py
    - src/packets/relevance.py
    - tests/test_economic.py
  modified: []

key-decisions:
  - "Zero-award Tribes use PROGRAM_BENCHMARK_AVERAGES with is_benchmark=True framing"
  - "Total obligation in TribeEconomicSummary includes both actual and benchmark amounts"
  - "Actual awards sorted before benchmarks in by_program list"
  - "HAZARD_PROGRAM_MAP covers all 18 NRI hazard types with fallback to bia_tcr+fema_bric"
  - "Human hazard names resolved via _HAZARD_NAME_TO_CODE reverse lookup"

patterns-established:
  - "Pure-function modules: no file I/O, no network, stateless computation only"
  - "Dataclass result types: ProgramEconomicImpact and TribeEconomicSummary for typed results"
  - "Published multiplier constants: BEA 1.8-2.4x, BLS 8-15 per $1M, FEMA BCR 4:1"
  - "Methodology citation embedded in every result for citable outputs"

# Metrics
duration: 8min
completed: 2026-02-10
---

# Phase 7 Plan 1: Economic Impact Calculator and Program Relevance Filter Summary

**BEA RIMS II multiplier (1.8-2.4x) economic calculator + NRI hazard-based program relevance filter, both as stateless pure-function modules with 26 tests**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-10T19:38:09Z
- **Completed:** 2026-02-10T19:46:00Z
- **Tasks:** 2/2
- **Files created:** 3

## Accomplishments
- EconomicImpactCalculator computes dollar impact ranges, job estimates, and FEMA BCR for any Tribe's award data
- Zero-award Tribes (primary path) get benchmark-based estimates with First-Time Applicant framing
- ProgramRelevanceFilter scores and selects 8-12 programs per Tribe based on hazard profile, ecoregion priority, and program priority level
- 26 new tests covering all economic and relevance edge cases; 158 total tests passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Create EconomicImpactCalculator module** - `1cd5d48` (feat)
2. **Task 2: Create ProgramRelevanceFilter and comprehensive tests** - `98e6a63` (feat)

## Files Created/Modified
- `src/packets/economic.py` - EconomicImpactCalculator with BEA/BLS/FEMA multipliers, ProgramEconomicImpact and TribeEconomicSummary dataclasses, narrative formatters
- `src/packets/relevance.py` - ProgramRelevanceFilter with HAZARD_PROGRAM_MAP (18 NRI hazard types), MIN/MAX clamping, ecoregion integration
- `tests/test_economic.py` - 14 economic tests + 12 relevance tests covering awards, benchmarks, BCR, districts, narratives, hazard matching, trimming

## Decisions Made
- **Zero-award path is primary:** Since all current award caches have empty awards arrays, the benchmark path with is_benchmark=True is the default behavior
- **Total obligation includes benchmarks:** TribeEconomicSummary.total_obligation sums actual + benchmark obligations for complete economic picture
- **Sorting: actuals before benchmarks:** by_program list places real awards first (sorted by obligation descending) then benchmarks
- **18 NRI hazard codes mapped:** All NRI hazard types have program mappings; unmapped hazards fall back to bia_tcr + fema_bric
- **Dual hazard code resolution:** Handles both "code" field (WFIR) and "type" field (Wildfire) with _HAZARD_NAME_TO_CODE reverse lookup

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test assertion for total_obligation with benchmark programs**
- **Found during:** Task 2 (test_compute_with_awards)
- **Issue:** Test asserted total_obligation == 750k but compute() adds benchmark estimates for programs without awards, making the total higher
- **Fix:** Updated assertion to check actual-award programs specifically rather than total (which includes benchmarks)
- **Files modified:** tests/test_economic.py
- **Verification:** All 26 tests pass
- **Committed in:** 98e6a63 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug in test)
**Impact on plan:** Minor test correction. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- EconomicImpactCalculator ready for Hot Sheet DOCX rendering (07-02)
- ProgramRelevanceFilter ready for program selection in DOCX templates
- Both modules are pure functions, easily testable from any downstream consumer
- All 158 tests passing, no regressions

---
*Phase: 07-computation-docx*
*Completed: 2026-02-10*
