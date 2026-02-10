---
phase: 07-computation-docx
plan: 03
subsystem: docx-rendering
tags: [python-docx, hotsheet, advocacy, ci-status, economic-impact, structural-asks]

# Dependency graph
requires:
  - phase: 07-01
    provides: EconomicImpactCalculator, ProgramEconomicImpact, TribeEconomicSummary, METHODOLOGY_CITATION
  - phase: 07-02
    provides: StyleManager, add_status_badge, set_cell_shading, apply_zebra_stripe, format_header_row, COLORS, CI_STATUS_COLORS
provides:
  - HotSheetRenderer with render_hotsheet() and render_all_hotsheets()
  - Per-program advocacy sections with 10 sub-sections
  - FRAMING_BY_STATUS constants for defensive/protective/growth framing
  - CFDA normalization helper (_normalize_cfda)
  - Committee-match detection for delegation members
affects: [07-04, phase-8]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Section-renderer pattern: private methods return early on empty data (hide-empty-sections)"
    - "CFDA normalization: _normalize_cfda() handles str/list/None consistently"
    - "Framing-by-status: dict lookup maps CI status to tone/verbs/prefix"
    - "Paragraph shading via OxmlElement for callout background"

key-files:
  created:
    - src/packets/docx_hotsheet.py
    - tests/test_docx_hotsheet.py
  modified: []

key-decisions:
  - "Page breaks between Hot Sheets (not section breaks) to avoid header/footer disruption"
  - "Paragraph-level shading for Key Ask callout (via OxmlElement w:shd) instead of table-based callout"
  - "USFS wildfire data displayed only for programs in _WILDFIRE_PROGRAM_IDS set"
  - "Evidence lines in structural asks derived from award and hazard data at render time"

patterns-established:
  - "Hide-empty-sections: each _add_* method checks data presence and returns early if empty"
  - "CFDA normalization: always call _normalize_cfda() before matching awards"
  - "Framing lookup: FRAMING_BY_STATUS[ci_status] with fallback to STABLE"

# Metrics
duration: 5min
completed: 2026-02-10
---

# Phase 7 Plan 03: Hot Sheet Renderer Summary

**HotSheetRenderer with 10 sub-sections (status badge, award history, hazard relevance, economic impact, advocacy language, Key Ask callout, structural asks, delegation), framing by CI status, and 35 comprehensive tests**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-10T19:49:21Z
- **Completed:** 2026-02-10T19:54:02Z
- **Tasks:** 2/2
- **Files created:** 2

## Accomplishments
- HotSheetRenderer renders complete per-program Hot Sheet sections with all 10 sub-sections in correct order
- Empty sections omitted (hidden, not shown with N/A) via return-early pattern in each private method
- All 6 CI statuses produce correct color badges and framing tone (defensive/protective/growth)
- tightened_language used when present, description+advocacy_lever fallback when absent
- Key Ask callout renders as 3-line ASK/WHY/IMPACT block with callout background shading
- Structural asks link to correct programs via program ID matching with urgency labels
- Committee-match flag highlights delegation members on relevant committees
- CFDA normalization handles string, list, and null types without crashes
- 35 tests across 9 test classes covering all sections and edge cases
- Full suite: 193 tests passing (158 existing + 35 new), zero regressions

## Task Commits

1. **Task 1: Create HotSheetRenderer module** - `c9c5d9c` (feat)
2. **Task 2: Create comprehensive Hot Sheet tests** - `e791d43` (test)

## Files Created/Modified
- `src/packets/docx_hotsheet.py` - HotSheetRenderer with render_hotsheet(), render_all_hotsheets(), 10 private section methods, FRAMING_BY_STATUS constants, CFDA normalization (410 lines)
- `tests/test_docx_hotsheet.py` - 35 tests: rendering, section-specific, advocacy language, structural asks, delegation, edge cases (465 lines)

## Decisions Made
- Page breaks (not section breaks) between Hot Sheets to preserve header/footer continuity
- Paragraph-level XML shading for Key Ask callout background (OxmlElement w:shd on pPr) rather than table-based callout
- USFS wildfire data displayed only for programs in _WILDFIRE_PROGRAM_IDS set (usda_wildfire, fema_bric, fema_tribal_mitigation, bia_tcr)
- Evidence lines in structural asks derived dynamically from award/hazard data at render time
- Box-drawing characters (U+2500) for horizontal rule above methodology footnote

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- HotSheetRenderer ready for integration into DocxEngine.generate() in plan 07-04
- render_all_hotsheets() takes sorted program list + TribeEconomicSummary, making it plug-and-play for the engine
- All rendering tested against real data shapes (awards, hazards, delegation, structural asks)
- Plan 07-04 needs: docx_sections.py (cover page, matrix, hazard summary), engine completion, orchestrator integration

---
*Phase: 07-computation-docx*
*Completed: 2026-02-10*
