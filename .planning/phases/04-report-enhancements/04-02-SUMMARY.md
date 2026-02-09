---
phase: 04-report-enhancements
plan: 02
subsystem: report-generation
tags: [reports, ci-trends, history, persistence, trend-table, markdown]
requires: ["04-01"]
provides:
  - CI history persistence with append-only outputs/.ci_history.json
  - _format_ci_trends() rendering score trajectories with changed/stable grouping
  - Complete LATEST-BRIEFING.md with all 6 Phase 4 sections (RPT-01 through RPT-06)
affects: []
tech-stack:
  added: []
  patterns:
    - "Append-only JSON history with 90-entry cap (Pitfall 3)"
    - "Timestamp deduplication for idempotent re-runs"
    - "Changed vs stable program grouping in trend table (Open Question 3)"
key-files:
  created:
    - outputs/.ci_history.json
  modified:
    - src/reports/generator.py
    - outputs/LATEST-BRIEFING.md
    - outputs/LATEST-RESULTS.json
key-decisions:
  - "CI history capped at 90 entries to prevent unbounded growth"
  - "Stable programs shown as compact summary instead of full table rows"
  - "CI Trends section positioned after Advocacy Levers, before All Items (position 14)"
  - "Delta threshold of 0.02 (2%) for trend indicators"
duration: "3 minutes"
completed: "2026-02-09"
---

# Phase 4 Plan 2: CI Score History and Trend Visualization Summary

Append-only CI history persistence via outputs/.ci_history.json with 90-entry cap, timestamp deduplication, and _format_ci_trends() rendering a score trajectory table with changed/stable program grouping and +N%/-N%/STABLE delta indicators. Completes all 6 RPT requirements for Phase 4.

## Performance

- Execution time: ~3 minutes
- Pipeline --report-only completes in <2 seconds
- 16 programs tracked per snapshot, 2 history entries validated
- Dedup verified: same-day re-runs do not create duplicate entries
- All 6 Phase 4 sections present in final LATEST-BRIEFING.md

## Accomplishments

1. **CI_HISTORY_PATH constant:** Added `outputs/.ci_history.json` path constant at module level alongside OUTPUTS_DIR and ARCHIVE_DIR.

2. **_save_ci_snapshot() (RPT-04):** Builds a snapshot dict with timestamp and per-program CI/status. De-duplicates by checking existing timestamps (same-day re-runs are idempotent). Caps history at 90 entries by trimming oldest when exceeded. Writes back with json.dump(indent=2).

3. **_load_ci_history() (RPT-04):** Returns empty list if file does not exist. Catches JSONDecodeError and OSError with warning log, returning empty list on corruption. Follows existing .monitor_state.json persistence pattern.

4. **_format_ci_trends() (RPT-04):** Always renders H2 header. With <2 scans: shows informational message about needing 2+ scan cycles. With 2+ scans: shows last 10 scans in a table with per-program CI percentages and trend indicators. Programs with no CI changes across the window are grouped into a compact "*N program(s) stable across window*" summary line. Programs with actual changes get full table rows with delta indicators (+N%, -N%, or STABLE for delta <= 0.02).

5. **generate() wiring:** Calls _save_ci_snapshot(timestamp) before building the report, then loads ci_history and passes it to _build_markdown(). History is persisted even if report generation fails afterward.

6. **_build_markdown() integration:** CI Score Trends section inserted after Advocacy Levers and before All Relevant Items (position 14 per RESEARCH.md section ordering).

## Task Commits

| # | Task | Commit | Type |
|---|------|--------|------|
| 1 | Add CI history persistence and trend formatting | 000abed | feat |
| 2 | Validate end-to-end CI trend tracking with pipeline | b67e9f4 | feat |

## Files Modified

| File | Changes |
|------|---------|
| src/reports/generator.py | Added CI_HISTORY_PATH constant; added _save_ci_snapshot(), _load_ci_history(), _format_ci_trends() methods; wired generate() and _build_markdown() with ci_history parameter |
| outputs/.ci_history.json | Created with 2 scan entries (seeded 2026-02-08 + live 2026-02-09) |
| outputs/LATEST-BRIEFING.md | Regenerated with CI Score Trends section showing trend table |
| outputs/LATEST-RESULTS.json | Regenerated with current scan data |

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| CI history capped at 90 entries | Prevents unbounded growth per Pitfall 3; ~3 months of daily scans is ample for trend analysis |
| Stable programs as compact summary | Reduces table clutter when most programs are unchanged; addresses Open Question 3 from RESEARCH.md |
| CI Trends at position 14 (before All Items) | Reference data belongs near end of briefing; tribal leaders read urgent/analytical sections first |
| Delta threshold 0.02 (2%) | Prevents noise from floating-point rounding; only shows meaningful CI changes |
| Seeded second entry for testing | Synthetic prior-day entry with -0.03 shift validates trend table rendering with visible deltas |

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Phase 4 Completion Status

All 6 RPT requirements are satisfied across Plans 01 and 02:

| Requirement | Section | Plan | Status |
|-------------|---------|------|--------|
| RPT-01 | Five Structural Asks | 04-01 | Complete |
| RPT-02 | Hot Sheets Sync Indicator | 04-01 | Complete |
| RPT-03 | IIJA Sunset Countdown | 04-01 | Complete |
| RPT-04 | CI Score Trends | 04-02 | Complete |
| RPT-05 | Reconciliation Watch | 04-01 | Complete |
| RPT-06 | Advocacy Goal Classifications | 04-01 | Complete |

LATEST-BRIEFING.md is now a complete advocacy intelligence product with 12 sections covering urgent alerts, strategic analysis, historical trends, and reference data.
