---
phase: 02-data-model-graph
plan: 01
subsystem: data
tags: [policy-tracking, scanner-config, grants-gov, cfda, reconciliation, status-tiers]

# Dependency graph
requires:
  - phase: 01-pipeline-validation
    provides: "Phase 1 validated pipeline end-to-end; Phase 2 Plan 01 enriches data model files consumed by that pipeline"
provides:
  - "7-tier CI threshold model with TERMINATED status in policy_tracking.json"
  - "Broad reconciliation/repeal trigger keywords in scanner_config.json"
  - "CFDA 15.124 mapping for BIA TCR Awards in grants_gov.py"
affects: [02-data-model-graph/plan-02, 03-monitoring-logic, 04-report-enhancements]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CI threshold tiers map to status definitions via floor values (score >= floor = tier)"
    - "CFDA_NUMBERS dict maps Assistance Listing numbers to program_inventory IDs for targeted scraping"

key-files:
  created: []
  modified:
    - data/policy_tracking.json
    - config/scanner_config.json
    - src/scrapers/grants_gov.py

key-decisions:
  - "flagged_floor raised from 0.0 to 0.10 to preserve FEMA BRIC (CI 0.12) classification as FLAGGED"
  - "terminated_floor set at 0.0 as absolute floor for confirmed-dead programs"
  - "Reconciliation keywords added as general scanner terms, not per-program overrides"

patterns-established:
  - "Status tier expansion pattern: add threshold floor + definition pair, verify existing programs unaffected"

# Metrics
duration: 2min
completed: 2026-02-09
---

# Phase 2 Plan 1: Data File Gaps (Policy Tracking, Scanner Config, CFDA) Summary

**7-tier CI threshold model with TERMINATED status added to policy_tracking.json, 6 reconciliation/repeal action keywords and 4 search queries added to scanner_config.json, CFDA 15.124 mapped to bia_tcr_awards in grants_gov.py**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-02-09
- **Completed:** 2026-02-09
- **Tasks:** 3/3 (all auto)
- **Files modified:** 3

## Accomplishments

- Added TERMINATED as 7th status tier to policy_tracking.json with terminated_floor threshold at 0.0
- Raised flagged_floor from 0.0 to 0.10, keeping FEMA BRIC (CI 0.12) correctly classified as FLAGGED
- Added TERMINATED status definition: "Program confirmed terminated; advocacy pivots to replacement mechanism"
- Added 6 reconciliation/repeal action_keywords: reconciliation, reconciliation bill, budget reconciliation, revenue offsets, repeal, section 6417
- Added 4 reconciliation-focused search_queries: budget reconciliation tribal, IRA repeal tribal, reconciliation bill energy, section 6417 repeal
- Mapped CFDA 15.124 to bia_tcr_awards in grants_gov.py CFDA_NUMBERS dict (12 total, was 11)
- All 16 programs and 16 positions remain intact with no schema changes

## Task Commits

1. **Task 1: Add TERMINATED status tier to policy tracking** - `933f9f2`
2. **Task 2: Add broad reconciliation/repeal keywords to scanner config** - `5e75769`
3. **Task 3: Add BIA TCR Awards CFDA to Grants.gov scraper** - `9796d4f`

## Files Created/Modified

- `data/policy_tracking.json` - Added terminated_floor threshold and TERMINATED status definition
- `config/scanner_config.json` - Added 6 action_keywords and 4 search_queries for reconciliation/repeal
- `src/scrapers/grants_gov.py` - Added CFDA 15.124 -> bia_tcr_awards mapping

## Decisions Made

- **flagged_floor raised to 0.10:** FEMA BRIC at CI 0.12 stays FLAGGED. The gap between 0.10 and 0.0 is reserved for TERMINATED programs only.
- **terminated_floor at 0.0:** Absolute floor -- only programs confirmed fully dead should reach this tier.
- **Reconciliation keywords as shared scanner terms:** Added to the global action_keywords/search_queries arrays rather than per-program extensible_fields, so all scrapers benefit from broader reconciliation coverage.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- DATA-02 (TERMINATED tier), DATA-04 (reconciliation keywords), DATA-05 (CFDA mapping) requirements addressed
- Ready for Phase 2 Plan 2: Graph Schema and Builder Enhancements
- No blockers or concerns

---
*Phase: 02-data-model-graph*
*Completed: 2026-02-09*
