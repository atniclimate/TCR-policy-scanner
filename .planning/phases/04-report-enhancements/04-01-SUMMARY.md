---
phase: 04-report-enhancements
plan: 01
subsystem: report-generation
tags: [reports, markdown, briefing, monitor-data, classifications, advocacy-goals, iija, reconciliation, hot-sheets, structural-asks]
requires: ["03-03"]
provides:
  - Extended ReportGenerator with 5 new format methods (RPT-01, RPT-02, RPT-03, RPT-05, RPT-06)
  - Pipeline wiring passing monitor_data and classifications to reporter
  - LATEST-BRIEFING.md with 11 sections (6 existing + 5 new)
  - LATEST-RESULTS.json with monitor_data and classifications keys
affects: ["04-02"]
tech-stack:
  added: []
  patterns:
    - "Always-render pattern for Reconciliation Watch and IIJA Countdown (Pitfall 7)"
    - "Classified/unclassified split for Advocacy Goals (Pitfall 6)"
    - "Hot Sheets sync indicator via original_ci_status override detection (Pitfall 4)"
key-files:
  created: []
  modified:
    - src/reports/generator.py
    - src/main.py
    - outputs/LATEST-BRIEFING.md
    - outputs/LATEST-RESULTS.json
key-decisions:
  - "Section ordering: urgent (Reconciliation, IIJA) above fold, analytical (Goals, Asks) after FLAGGED, reference (All Items) at end"
  - "CI Dashboard Determination column truncated from 80 to 70 chars to accommodate Hot Sheets column"
  - "All Items section moved to near-end position (was between Critical Updates and CI Dashboard)"
  - "Backward-compatible generate() signature (monitor_data and classifications default to None)"
duration: "5 minutes"
completed: "2026-02-09"
---

# Phase 4 Plan 1: Report Sections and Pipeline Wiring Summary

Extended ReportGenerator with 5 new format methods consuming Phase 3 monitor/decision engine output; wired monitor_data and classifications from run_monitors_and_classify() through to reporter.generate() producing an 11-section LATEST-BRIEFING.md with structural asks, IIJA countdown, reconciliation watch, advocacy goals, and Hot Sheets sync indicators.

## Performance

- Execution time: ~5 minutes
- Pipeline --report-only completes in <2 seconds
- 177 scored items processed, 188 graph nodes, 236 edges
- All 8 verification criteria pass
- Backward-compatible: old callers without monitor_data/classifications still work

## Accomplishments

1. **Extended generate() signature (RPT-*):** Added `monitor_data` and `classifications` as optional keyword parameters to `generate()`, `_build_markdown()`, and `_build_json()`. Backward-compatible -- defaults to None.

2. **Five Structural Asks (RPT-01):** `_format_structural_asks()` queries graph_data nodes for AdvocacyLeverNode with `ask_` prefix. Resolves ADVANCES edges (ask -> program) and MITIGATED_BY edges (barrier -> ask). Renders H3 per ask with urgency badge, target, programs, and mitigated barriers. All 5 asks render correctly.

3. **Hot Sheets Sync Indicator (RPT-02):** Integrated as a column in the CI Dashboard table. Detects ALIGNED (hot_sheets_status matches ci_status), OVERRIDE (original_ci_status differs), or DIVERGED states. All 16 programs show ALIGNED at baseline. Determination column truncated from 80 to 70 chars.

4. **IIJA Sunset Countdown (RPT-03):** `_format_iija_countdown()` always renders (Pitfall 7). Filters monitor_data alerts for `iija_sunset` monitor. Sorts by days_remaining (None sorts last). Shows table with Program, Deadline, Days Remaining, Severity, Type. Currently shows 3 alerts: EPA STAG (233 days), USBR WaterSMART (233 days), USDA Wildfire (fund exhaustion, no deadline).

5. **Reconciliation Watch (RPT-05):** `_format_reconciliation_watch()` always renders (Pitfall 7). Shows "No active reconciliation threats detected in current scan" when no reconciliation alerts exist. Will render severity/title/detail/keywords when alerts are present.

6. **Advocacy Goal Classifications (RPT-06):** `_format_advocacy_goals()` separates classified from unclassified programs (Pitfall 6). Shows table of classified programs with goal, rule, confidence, reason (truncated to 80 chars). Below table, shows count and names of unclassified programs in italic. Currently shows FEMA BRIC and FEMA Tribal Mitigation Plans as URGENT_STABILIZATION (LOGIC-05).

7. **Section Ordering:** Restructured _build_markdown() per RESEARCH.md Pattern 3: Header -> Executive Summary -> Reconciliation Watch -> IIJA Countdown -> New Developments -> Critical Updates -> CI Dashboard (with Hot Sheets) -> FLAGGED -> Advocacy Goals -> Structural Asks -> Barriers -> Authorities -> Advocacy Levers -> All Items -> Footer.

8. **Pipeline Wiring:** Updated run_pipeline() in main.py to pass `monitor_data=monitor_data, classifications=classifications` to `reporter.generate()`. JSON output now includes both keys.

## Task Commits

| # | Task | Commit | Type |
|---|------|--------|------|
| 1 | Extend ReportGenerator with 5 new format methods | 6d30f35 | feat |
| 2 | Wire pipeline and validate end-to-end output | eb869eb | feat |
| - | Restore pipeline outputs with full scan data | a6b506a | fix |

## Files Modified

| File | Changes |
|------|---------|
| src/reports/generator.py | Extended generate/build_markdown/build_json signatures; added 4 new _format_* methods; modified CI Dashboard table with Hot Sheets column; reordered sections |
| src/main.py | Updated reporter.generate() call with monitor_data and classifications kwargs |
| outputs/LATEST-BRIEFING.md | Regenerated with 11 sections including all new content |
| outputs/LATEST-RESULTS.json | Now includes monitor_data and classifications keys |

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Section ordering: urgent above fold, analytical middle, reference at end | Tribal leaders see time-sensitive items first (reconciliation/IIJA), then strategic context, then reference data |
| CI Dashboard Determination column truncated 80 -> 70 chars | Accommodates 5th column (Hot Sheets) without excessive table width |
| All Items section moved to near-end | Items list is reference data; structural analysis sections take priority |
| Always-render pattern for Reconciliation Watch and IIJA Countdown | "No active threats" is valuable information for Tribal leaders preparing for meetings (Pitfall 7) |
| Classified/unclassified split in Advocacy Goals | Prevents table dominated by 14 "No match" rows obscuring the 2 classified programs (Pitfall 6) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Backward-compatibility test overwrote cached scan data**

- **Found during:** Task 2 verification
- **Issue:** Running a backward-compatibility test with empty scored_items list caused ReportGenerator to overwrite LATEST-RESULTS.json with empty scan_results, breaking subsequent --report-only runs
- **Fix:** Restored LATEST-RESULTS.json from git history and re-ran pipeline to regenerate all outputs
- **Files modified:** outputs/LATEST-RESULTS.json, outputs/LATEST-BRIEFING.md, outputs/LATEST-MONITOR-DATA.json
- **Commit:** a6b506a

## Issues Encountered

None beyond the auto-fixed data restoration issue above.

## Next Phase Readiness

Plan 04-02 (CI Trend History) can proceed:
- ReportGenerator signature is extended and ready for additional sections
- The _build_markdown() method has clear insertion points for new sections
- CI history file (.ci_history.json) creation and _format_ci_trends() are Plan 02 scope
- No blockers identified
