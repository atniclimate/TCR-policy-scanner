---
phase: 08-assembly-polish
plan: 01
subsystem: docx-generation
tags: [docx, sections, executive-summary, delegation, hazard, structural-asks]
dependency_graph:
  requires: ["07-04"]
  provides: ["8-section document assembly", "render_executive_summary", "render_delegation_section", "render_hazard_summary", "render_structural_asks_section", "forward-compatible generate() params"]
  affects: ["08-02", "08-04"]
tech_stack:
  added: []
  patterns: ["section renderer pattern", "committee keyword filtering", "nested hazard data access", "evidence line builder"]
key_files:
  created:
    - tests/test_doc_assembly.py
  modified:
    - src/packets/docx_sections.py
    - src/packets/docx_engine.py
decisions:
  - id: "exec-summary-always-5-asks"
    description: "Structural asks count hardcoded to 5 per project design"
    rationale: "Project design specifies 5 structural asks; dynamic count would require cross-section coordination"
  - id: "delegation-at-large-senators"
    description: "Senators shown as 'At-Large' in district column"
    rationale: "Senators represent entire state, not specific districts"
  - id: "hazard-eal-format"
    description: "Expected Annual Loss formatted as $X,XXX with no decimals"
    rationale: "Consistent with _format_dollars pattern used in docx_hotsheet.py"
  - id: "ask-evidence-program-id-match"
    description: "Evidence line checks award program_id against ask programs"
    rationale: "Direct match; CFDA cross-reference not needed for standalone section"
metrics:
  duration: "15 minutes"
  completed: "2026-02-10"
  tests_added: 13
  tests_total: 227
  lines_added: 1139
---

# Phase 8 Plan 01: Full Document Assembly Summary

**One-liner:** 4 new section renderers (exec summary, delegation, hazard, structural asks) with 8-section DocxEngine.generate() assembly and 13 comprehensive tests.

## What Was Done

### Task 1: Add 4 new section renderers to docx_sections.py
Commit: `1c7fe21`

Added 4 new render functions to `src/packets/docx_sections.py` (now 675 lines, 7 total renderers):

1. **render_executive_summary()** -- Tribe identity line, top 3 hazards snapshot, funding summary with dollar total, first 3 programs with CI status badges, delegation/district count, structural asks count. Handles zero-award and zero-hazard cases gracefully.

2. **render_delegation_section()** -- 5-column table (Name, Role, State, District, Relevant Committees) with `format_header_row()` and `apply_zebra_stripe()`. Committee filtering uses `RELEVANT_COMMITTEE_KEYWORDS` imported from `docx_hotsheet.py`. Reports count of members with relevant committee assignments. Handles empty delegation gracefully.

3. **render_hazard_summary()** -- FEMA NRI composite ratings (risk + social vulnerability), top 5 hazards table with risk score/rating/EAL, USFS wildfire section. Uses same nested data access pattern as `HotSheetRenderer._add_hazard_relevance()`. Handles missing data gracefully.

4. **render_structural_asks_section()** -- Intro paragraph, each ask with bold name + urgency badge, description, target, programs advanced, and evidence line connecting to Tribe's award/hazard data. Handles empty asks list gracefully.

Also added two helper functions:
- `_filter_relevant_committees()` -- Filters committee list using keyword matching
- `_build_ask_evidence()` -- Builds evidence line from Tribe's award and hazard data

### Task 2: Update DocxEngine.generate() with new section assembly order
Commit: `905a510`

Updated `src/packets/docx_engine.py` (now 252 lines):

- Added imports for 4 new renderers from `docx_sections`
- New 8-section assembly order: cover -> TOC -> exec summary -> delegation -> Hot Sheets -> hazard -> structural asks -> appendix
- Added forward-compatible `changes: list[dict] | None = None` and `previous_date: str | None = None` parameters (stubs for Plan 08-04)
- Updated docstring and logger.info to reflect 8-section structure
- All page breaks use `document.add_page_break()` (not section breaks)

### Task 3: Create tests/test_doc_assembly.py
Commit: `bc8ef75`

Created `tests/test_doc_assembly.py` (697 lines, 13 tests):

| Test | Description |
|------|-------------|
| test_full_assembly_produces_all_sections | All 5 section headings present |
| test_document_opens_without_error | File valid, non-zero size |
| test_executive_summary_contains_tribe_name | Tribe identity in exec summary |
| test_executive_summary_references_programs | Program names in exec summary |
| test_delegation_table_has_senators_and_reps | Table with Senator/Rep roles |
| test_delegation_committee_filtering | Committee keyword matching count > 0 |
| test_multi_state_tribe_delegation | 7 members across 3 states |
| test_hazard_summary_renders_top_hazards | Wildfire in hazard section |
| test_hazard_summary_has_fema_ratings | Risk Rating/Social Vulnerability |
| test_structural_asks_includes_all_five | All 5 ask names present |
| test_zero_data_tribe_produces_valid_docx | Graceful empty sections |
| test_section_order_correct | H2 headings in correct sequence |
| test_existing_tests_unaffected | Regression subprocess check |

## Deviations from Plan

None -- plan executed exactly as written.

## Verification Results

1. All 4 new renderers import: PASS
2. `generate()` has `changes` and `previous_date` params: PASS
3. 13/13 new tests pass: PASS
4. Full suite: 227/227 tests pass (214 existing + 13 new): PASS
5. Section headings in correct order: PASS (verified by test_section_order_correct)
6. Zero-data Tribe DOCX opens and has graceful fallback text: PASS

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Structural asks count hardcoded to 5 | Per project design; dynamic count would require cross-section coordination |
| Senators shown as "At-Large" in district column | Senators represent entire state, not specific districts |
| EAL formatted as $X,XXX (no decimals) | Consistent with _format_dollars pattern in docx_hotsheet.py |
| Evidence line uses program_id match (not CFDA) | Direct match sufficient for standalone section |

## Next Phase Readiness

- DocxEngine.generate() now produces complete 8-section documents
- Forward-compatible `changes` and `previous_date` params ready for Plan 08-04
- All 227 tests pass; no blockers for parallel Plan 08-02 execution
