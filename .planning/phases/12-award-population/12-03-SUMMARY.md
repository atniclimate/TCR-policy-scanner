---
phase: 12-award-population
plan: 03
subsystem: scripts
tags: [usaspending, cli, orchestration, award-population, pydantic, api-fix]

# Dependency graph
requires:
  - phase: 12-award-population
    provides: "Batch query engine (12-01) and matching/caching engine (12-02)"
provides:
  - "scripts/populate_awards.py CLI for full award population pipeline"
  - "592 award cache files with real USASpending data (418 Tribes matched)"
  - "outputs/award_population_report.json coverage and match statistics"
  - "TRIBAL_AWARD_TYPE_CODE_GROUPS constant for USASpending API compliance"
  - "Updated Pydantic schemas matching real cache data structure"
  - "_last_unmatched_awards tracking on TribalAwardMatcher"
affects: [13-hazard-population, 14-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Award type group splitting: USASpending API rejects mixed award_type_codes groups"
    - "Unmatched award tracking via _last_unmatched_awards instance attribute"
    - "Local import pattern for scripts/ in tests (avoids E402 lint errors)"

key-files:
  created:
    - scripts/populate_awards.py
    - tests/test_populate_awards.py
  modified:
    - src/scrapers/usaspending.py
    - src/packets/awards.py
    - src/schemas/models.py
    - src/schemas/__init__.py
    - tests/test_usaspending_batch.py
    - tests/test_schemas.py

key-decisions:
  - "DEC-1203-01: USASpending API requires award_type_codes from a single group per request; split TRIBAL_AWARD_TYPE_CODES into TRIBAL_AWARD_TYPE_CODE_GROUPS"
  - "DEC-1203-02: 418/592 coverage (70.6%) accepted below 450 target; housing authority names dominate unmatched (structural gap requiring alias expansion)"
  - "DEC-1203-03: Data files (award_cache/*.json, outputs/*.json) NOT committed to git per plan instruction"

patterns-established:
  - "Two-pass API querying: grants group [02-05] then direct_payments group [06,10] per USASpending constraint"
  - "Coverage reporting: top_unmatched + consortium_summary for operational visibility"
  - "Pydantic schema evolution: stub -> real data schema (FundingRecord, CFDASummaryEntry, FiscalYearRange)"

# Metrics
duration: 20min
completed: 2026-02-11
---

# Phase 12, Plan 03: Pipeline Integration Summary

**Standalone CLI script orchestrating USASpending fetch/dedup/match/cache pipeline, producing 592 cache files with real award data for 418 Tribes across FY22-FY26**

## Performance

- **Duration:** 20 min
- **Started:** 2026-02-11T15:20:59Z
- **Completed:** 2026-02-11T15:40:48Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Created `scripts/populate_awards.py` CLI with --dry-run, --tribe, --report, --fy-start, --fy-end flags
- Fixed critical USASpending API bug: mixed award_type_codes groups cause 422 errors
- Populated 592 award cache files with real data: 8,973 raw awards -> 4,293 deduped -> 2,953 matched to 418 Tribes
- Updated Pydantic schemas (FundingRecord, AwardCacheFile) to match actual cache data structure
- Added _last_unmatched_awards tracking for reporting pipeline visibility
- 477 tests passing (6 new + 471 existing), zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Create populate_awards.py CLI script + tests** - `4b1d27d` (feat)
2. **Task 2: Fix API constraint, update schemas, run population** - `1caf7a2` (fix)

## Files Created/Modified
- `scripts/populate_awards.py` - Standalone CLI orchestrating fetch -> dedup -> match -> cache pipeline (196 lines)
- `tests/test_populate_awards.py` - 6 tests for CLI argument parsing (86 lines)
- `src/scrapers/usaspending.py` - Split TRIBAL_AWARD_TYPE_CODES into grouped constants, updated fetch methods
- `src/packets/awards.py` - Added _last_unmatched_awards list and tracking in match_all_awards()
- `src/schemas/models.py` - Updated FundingRecord fields, added CFDASummaryEntry + FiscalYearRange models
- `src/schemas/__init__.py` - Exported CFDASummaryEntry and FiscalYearRange
- `tests/test_usaspending_batch.py` - Updated 4 tests for two-group API querying behavior
- `tests/test_schemas.py` - Updated FundingRecord defaults test for new field names

## Decisions Made
- **DEC-1203-01:** USASpending API requires award_type_codes from a single group per request. The API returns a 422 error with message "'award_type_codes' must only contain types from one group." Split queries into grants [02-05] and other_financial_assistance [06,10] groups, merging results per (CFDA, FY) pair.
- **DEC-1203-02:** Coverage is 418/592 Tribes (70.6%), below the aspirational 450+ target. Root cause: HUD IHBG awards go to Tribal Housing Authorities whose names don't match the alias table (e.g., "NAVAJO HOUSING AUTHORITY" not in aliases for Navajo Nation). 15 of the top 20 unmatched recipients by obligation are housing authorities. Fixing this requires a dedicated housing authority alias mapping -- a future enhancement, not in scope for Phase 12.
- **DEC-1203-03:** Per plan instructions, 592 data/award_cache/*.json files and outputs/award_population_report.json are NOT committed to git. They are generated artifacts that can be reproduced by re-running the script.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] USASpending API rejects mixed award_type_codes groups**
- **Found during:** Task 2 (pipeline execution)
- **Issue:** TRIBAL_AWARD_TYPE_CODES mixed grants [02-05] with other_financial_assistance [06,10], causing HTTP 422 on every API call. This was introduced in Plan 12-01 (DEC-1201-01).
- **Fix:** Created TRIBAL_AWARD_TYPE_CODE_GROUPS constant splitting codes into API-compliant groups. Updated fetch_tribal_awards_by_year() and fetch_tribal_awards_for_cfda() to iterate over each group. Preserved flat TRIBAL_AWARD_TYPE_CODES for backward compatibility.
- **Files modified:** src/scrapers/usaspending.py, tests/test_usaspending_batch.py
- **Verification:** API returns 200 for each group; 8,973 awards fetched successfully
- **Committed in:** 1caf7a2

**2. [Rule 2 - Missing Critical] _last_unmatched_awards tracking for coverage reporting**
- **Found during:** Task 1 (script design)
- **Issue:** TribalAwardMatcher.match_all_awards() logged unmatched count but didn't store the actual unmatched names/obligations needed for the coverage report's top_unmatched section.
- **Fix:** Added unmatched_awards list tracking alongside existing consortium_awards pattern. Stored as _last_unmatched_awards instance attribute.
- **Files modified:** src/packets/awards.py
- **Verification:** Report top_unmatched correctly populated with 20 entries
- **Committed in:** 4b1d27d (part of Task 1)

**3. [Rule 1 - Bug] Pydantic schema mismatch with real cache data**
- **Found during:** Task 2 (test suite verification)
- **Issue:** FundingRecord had stale stub fields (amount, award_type, cfda_number, fiscal_year) that didn't match actual cache output (obligation, cfda, recipient_name_raw). AwardCacheFile had cfda_summary typed as dict[str, float] but actual data is dict[str, {count, total}]. Missing fiscal_year_range, yearly_obligations, trend fields.
- **Fix:** Updated FundingRecord fields to match actual output. Added CFDASummaryEntry and FiscalYearRange models. Updated AwardCacheFile schema with all new fields.
- **Files modified:** src/schemas/models.py, src/schemas/__init__.py, tests/test_schemas.py
- **Verification:** All 96 schema tests pass including real data validation
- **Committed in:** 1caf7a2

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 missing critical)
**Impact on plan:** Bug #1 was the root cause of complete pipeline failure (0 awards fetched). All fixes were essential for pipeline operation. No scope creep.

## Pipeline Results

```
=== Award Population Report ===
Fiscal years: FY22 - FY26
Queries: 70 (14 CFDAs x 5 FYs)
Awards fetched: 8,973 (after dedup: 4,293)
Matched: 2,953 (68.8%) | Unmatched: 1,276 | Consortium: 64
Coverage: 418/592 Tribes (70.6%) -- target 450+: NOT MET
Cache files written: 592
```

**Coverage gap analysis:** Housing Authority names account for 15 of the top 20 unmatched recipients ($3.9B in obligations). A dedicated housing authority -> Tribe alias mapping would significantly improve coverage. This is a targeted future enhancement.

## Issues Encountered
- USASpending API returns 422 when mixing award_type_codes from different groups. This was not documented in the API's official documentation and was discovered through runtime testing. The error message helpfully lists the valid groups, enabling the fix.
- The circuit breaker tripped after 5 consecutive 422 failures, causing all subsequent queries to fail immediately. Creating a new scraper instance in the fixed pipeline reset the circuit breaker state.

## User Setup Required
None - no external service configuration required. USASpending API is free and requires no authentication.

## Next Phase Readiness
- Phase 12 (Award Population) is COMPLETE: all 3 plans executed
- 592 award cache files populated with real data (FY22-FY26)
- 418 Tribes have matched awards (coverage 70.6%)
- Enhanced cache schema with yearly_obligations and trend ready for DOCX packet generation
- Pydantic schemas updated to validate real data
- 477 total tests pass, zero regressions
- Ready for Phase 13 (Hazard Population) and Phase 14 (Integration)

---
*Phase: 12-award-population*
*Completed: 2026-02-11*
