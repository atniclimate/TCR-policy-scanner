---
phase: 03-monitoring-logic
plan: 03
subsystem: monitoring-pipeline-integration
tags: [monitors, tribal-consultation, hot-sheets, pipeline, decision-engine, regex]
requires: ["03-01", "03-02"]
provides:
  - TribalConsultationMonitor (MON-03) with tiered regex detection
  - HotSheetsValidator (MON-04) with CI override and state persistence
  - Full pipeline integration of monitors + decision engine into main.py
  - LATEST-MONITOR-DATA.json output file for Phase 4 reporting
affects: ["04-01", "04-02"]
tech-stack:
  added: []
  patterns:
    - "Monitor state persistence via outputs/.monitor_state.json"
    - "In-memory CI override (HotSheets mutates program dicts, not inventory file)"
    - "Centralized run_monitors_and_classify() function for stages 3.5-3.6"
key-files:
  created:
    - src/monitors/tribal_consultation.py
    - src/monitors/hot_sheets.py
    - outputs/LATEST-MONITOR-DATA.json
  modified:
    - data/program_inventory.json
    - src/monitors/__init__.py
    - src/main.py
key-decisions:
  - "HotSheetsValidator runs first in monitor order to apply CI overrides before decision engine"
  - "Hot Sheets status aligned at baseline (no initial divergences)"
  - "Tribal consultation signals are INFO severity, not threats (no THREATENS edges)"
  - "Monitor data saved to separate JSON file rather than modifying ReportGenerator (Phase 4)"
duration: "5 minutes"
completed: "2026-02-09"
---

# Phase 3 Plan 3: Signal Monitors and Pipeline Integration Summary

Tribal consultation tracker and Hot Sheets sync validator complete the 5-monitor suite; pipeline integration wires monitors and decision engine between graph construction and reporting, producing LATEST-MONITOR-DATA.json with alerts and advocacy goal classifications for all 16 programs.

## Performance

- Execution time: ~5 minutes
- All 5 monitors register and execute without errors
- 45 decision engine tests pass (no regressions)
- Full pipeline (--report-only) completes in <2 seconds
- All CLI modes (--dry-run, --graph-only, --report-only, --programs) work correctly

## Accomplishments

1. **TribalConsultationMonitor (MON-03):** Three-tier regex pattern matching for DTLL, EO 13175, and consultation notices. Compiled at module level for performance. INFO severity (informational, not threats). One alert per signal_type per item.

2. **HotSheetsValidator (MON-04):** Compares scanner CI status with Hot Sheets positions from program inventory. Staleness check warns when data exceeds configurable threshold. Divergence detection with first-time (WARNING) vs known (INFO) distinction. Applies in-memory CI override so downstream code sees Hot Sheets status. Persists known divergences to outputs/.monitor_state.json.

3. **Program Inventory Update:** Added hot_sheets_status field to all 16 programs with current-date baseline aligned to scanner CI status. Establishes the foundation for manual Hot Sheets position updates.

4. **MonitorRunner Registration:** All 5 monitors registered with correct execution order: HotSheetsValidator first (CI overrides), then threat monitors (IIJA, reconciliation, DHS), then consultation (informational).

5. **Pipeline Integration:** New run_monitors_and_classify() function runs monitors and decision engine between graph construction and reporting. Monitor data saved to LATEST-MONITOR-DATA.json. Console output shows alert and classification summaries. --dry-run shows monitor configuration. All CLI modes run monitors on cached data.

## Task Commits

| # | Task | Commit | Type |
|---|------|--------|------|
| 1 | Tribal consultation monitor, Hot Sheets validator, and inventory data | 80aaa14 | feat |
| 2 | Wire monitors and decision engine into pipeline | a7a7e20 | feat |

## Files Created

| File | Purpose |
|------|---------|
| src/monitors/tribal_consultation.py | TribalConsultationMonitor (MON-03) with tiered regex |
| src/monitors/hot_sheets.py | HotSheetsValidator (MON-04) with CI override and state persistence |

## Files Modified

| File | Changes |
|------|---------|
| data/program_inventory.json | Added hot_sheets_status field to all 16 programs |
| src/monitors/__init__.py | Registered HotSheetsValidator and TribalConsultationMonitor; ordered HotSheets first |
| src/main.py | Added MonitorRunner/DecisionEngine imports, run_monitors_and_classify(), MONITOR_OUTPUT_PATH, monitor summary in console output, monitor config in --dry-run |

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| HotSheetsValidator runs first in monitor order | CI overrides must be applied before decision engine classifies programs |
| Hot Sheets status aligned at baseline (no initial divergences) | Clean starting point; when Hot Sheets positions change, user updates inventory manually |
| Tribal consultation signals are INFO severity | Consultations are informational engagement signals, not threats -- no THREATENS edges created |
| Monitor data saved to separate JSON file | ReportGenerator modification is Phase 4 scope; separate file provides clean data interface |
| run_monitors_and_classify() as standalone function | Keeps pipeline stages modular; returns (alerts, classifications, monitor_data) tuple for flexible use |

## Deviations from Plan

None -- plan executed exactly as written.

## Issues Encountered

None. All monitors integrated cleanly with existing framework.

## Next Phase Readiness

Phase 3 is now COMPLETE. All 10 requirements (MON-01 through MON-05, LOGIC-01 through LOGIC-05) are implemented and working.

Phase 4 (Report Enhancements) can now proceed:
- LATEST-MONITOR-DATA.json provides all alert and classification data for report sections
- Monitor alerts are serialized with full metadata for display formatting
- Classifications include goal_label, rule, confidence, reason, and secondary_rules
- Program dicts carry Hot Sheets override data (original_ci_status when divergent)
- No blockers identified for Phase 4
