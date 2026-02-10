---
phase: "07"
plan: "04"
subsystem: "packets-docx-pipeline"
tags: ["docx", "orchestrator", "cover-page", "appendix", "integration"]
dependency_graph:
  requires: ["07-02", "07-03"]
  provides: ["generate_packet()", "docx_sections.py", "full-pipeline"]
  affects: ["08-assembly"]
tech_stack:
  added: []
  patterns: ["engine-assembly", "orchestrator-delegation", "atomic-save"]
key_files:
  created:
    - "src/packets/docx_sections.py"
    - "tests/test_docx_integration.py"
  modified:
    - "src/packets/docx_engine.py"
    - "src/packets/orchestrator.py"
    - "config/scanner_config.json"
    - "tests/test_docx_styles.py"
decisions:
  - id: "DEC-0704-01"
    decision: "Always render appendix section even when empty"
    rationale: "Better document structure -- shows reader that all programs were considered"
  - id: "DEC-0704-02"
    decision: "Use dataclasses.asdict() for economic_summary -> context.economic_impact"
    rationale: "TribeEconomicSummary lacks to_dict(); asdict() provides deep conversion"
  - id: "DEC-0704-03"
    decision: "Meta-test uses --collect-only instead of full run to avoid Windows subprocess timeout"
    rationale: "Recursive pytest within pytest times out on Windows; collect-only is fast and reliable"
metrics:
  duration: "11 minutes"
  completed: "2026-02-10"
  tests_added: 21
  tests_total: 214
  tests_passing: 214
---

# Phase 7 Plan 4: DOCX Pipeline Assembly Summary

**One-liner:** Full end-to-end DOCX pipeline: cover page, TOC, Hot Sheets, appendix, orchestrator integration, with 21 integration tests and 214 total tests passing.

## What Was Built

### docx_sections.py (new, 193 lines)
Three document section renderers:
- `render_cover_page()` -- title, Tribe name, delegation summary, states/ecoregions, congress session, date, confidentiality notice, page break
- `render_table_of_contents()` -- numbered program list with inline CI status badges, summary note, page break
- `render_appendix()` -- omitted program descriptions with CI status, access/funding types, and contact guidance. Shows "All tracked programs are included" when nothing is omitted.

### docx_engine.py (completed)
Replaced the stub `generate()` with full assembly pipeline:
1. Create document and style manager
2. Render cover page
3. Render table of contents
4. Create HotSheetRenderer and render all Hot Sheets
5. Render appendix (always, even when empty)
6. Atomic save and return path

Updated signature to include `omitted_programs: list[dict] | None = None` parameter.

### orchestrator.py (extended)
Added Phase 7 DOCX generation capabilities:
- `generate_packet(tribe_name)` -- full standalone pipeline: resolve Tribe, build context, compute economic impact, filter programs, load structural asks, generate DOCX
- `generate_packet_from_context(context, tribe)` -- shared implementation used by both `generate_packet()` and `run_single_tribe()`
- `_load_structural_asks()` -- reads structural asks from `data/graph_schema.json`
- `__init__` now creates `EconomicImpactCalculator` and `ProgramRelevanceFilter`
- `run_single_tribe()` now generates DOCX after display when config enables it

### config/scanner_config.json
Added `packets.docx` section:
```json
"docx": {
    "enabled": true,
    "output_dir": "outputs/packets"
}
```

### test_docx_integration.py (new, 21 tests)
Comprehensive integration tests covering:
- Full pipeline for Tribe with awards and hazards
- Zero-award zero-hazard Tribe edge case (First-Time Applicant framing)
- Path return type verification
- Invalid Tribe returns None
- Cover page content verification (Tribe name, states, ecoregions, congress session)
- Hot Sheet program names presence
- Appendix rendering
- Delegation section presence
- Economic impact content
- Advocacy language content
- Economic summary populated in context after generation
- Config docx section verification
- DOCX re-readability (python-docx Document() reopens)
- Structural asks loading and rendering
- Table of contents program listing
- Existing module importability and minimum test count (regression guard)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_engine_generate_stub to match real implementation**
- **Found during:** Task 1
- **Issue:** Existing test `test_engine_generate_stub` used a minimal MockContext missing senators/representatives fields that the completed `generate()` now accesses through cover page rendering
- **Fix:** Replaced mock with real TribePacketContext and TribeEconomicSummary, renamed to `test_engine_generate_full`
- **Files modified:** tests/test_docx_styles.py
- **Commit:** 522867c

**2. [Rule 1 - Bug] Always render appendix section**
- **Found during:** Task 2 (integration test failure)
- **Issue:** `if omitted_programs:` skipped appendix entirely when empty list, but `render_appendix()` has a proper "All tracked programs are included" handler for empty lists
- **Fix:** Changed to always call `render_appendix()` with `omitted_programs or []`
- **Files modified:** src/packets/docx_engine.py
- **Commit:** 77d3e96

**3. [Rule 3 - Blocking] Meta-test subprocess timeout on Windows**
- **Found during:** Task 2 (integration test failure)
- **Issue:** Recursive `python -m pytest tests/ -q` within a subprocess timed out at 120s on Windows when the test suite itself is running
- **Fix:** Replaced with `--collect-only` for count verification and direct module import check for importability
- **Files modified:** tests/test_docx_integration.py
- **Commit:** 77d3e96

## Key Design Notes

- Cover page does NOT include an image/map (deferred to Phase 8)
- No `add_section()` calls -- all content shares single header/footer via page breaks only
- `generate_packet()` is the standalone public API; `generate_packet_from_context()` is shared between standalone and `run_single_tribe()` flows
- `context.economic_impact` is populated via `dataclasses.asdict(economic_summary)` since TribeEconomicSummary has no `to_dict()` method
- Structural asks are loaded lazily from `data/graph_schema.json` on each call

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 522867c | feat | Create docx_sections.py and complete DocxEngine.generate() |
| 77d3e96 | feat | Wire orchestrator, update config, add 21 integration tests |

## Next Phase Readiness

Phase 7 is now complete. All 4 plans executed:
- 07-01: Economic impact calculator
- 07-02: DOCX engine + styles
- 07-03: Hot Sheet renderer
- 07-04: Pipeline assembly + integration

**Ready for Phase 8 (Assembly + Polish):**
- `PacketOrchestrator.generate_packet("tribe name")` produces a complete .docx
- Generated DOCX has cover page, TOC, Hot Sheets, appendix, economic impact, structural asks, delegation info
- Zero-award Tribes get appropriate "First-Time Applicant" framing throughout
- 214 tests passing with zero failures
