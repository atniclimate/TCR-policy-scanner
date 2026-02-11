---
phase: 14-integration
plan: 03
subsystem: packet-generation
tags: [docx, audience-filtering, content-differentiation, orchestrator, multi-doc, hazard-integration]
requires:
  - "Phase 7: DOCX generation engine (DocxEngine, StyleManager, HotSheetRenderer)"
  - "Phase 8: Section renderers (cover page, TOC, exec summary, delegation, hazards, asks)"
  - "Plan 14-02: DocumentTypeConfig dataclass with 4 pre-built instances (DOC_A/B/C/D)"
provides:
  - "Audience-differentiated section rendering (internal vs. congressional content)"
  - "Messaging framework section (Doc A only)"
  - "Hazard-to-program alignment narrative in economic impact sections (INTG-01)"
  - "Orchestrator multi-doc generation: Doc A + Doc B per Tribe with internal/congressional directories"
  - "Evidence-only Key Ask boxes for congressional documents"
  - "Strategic Notes subsection in delegation for internal documents"
  - "21 audience filtering tests proving zero strategy content leakage"
affects:
  - "Plan 14-04: Regional documents (uses audience-filtered renderers for Doc C/D)"
  - "Plan 14-05: Batch generation (uses generate_tribal_docs for multi-doc output)"
  - "Plan 14-06: CLI integration (wires doc_types into --prep-packets flags)"
tech-stack:
  added: []
  patterns:
    - "Conditional rendering via doc_type_config flags in section renderers"
    - "Orchestrator multi-doc pattern: compute shared data once, generate N documents"
    - "Output directory routing: internal/ vs congressional/ subdirectories"
    - "Hazard-economic integration: hazard context woven into economic narrative"
key-files:
  created:
    - tests/test_audience_filtering.py
  modified:
    - src/packets/docx_engine.py
    - src/packets/docx_sections.py
    - src/packets/docx_hotsheet.py
    - src/packets/orchestrator.py
key-decisions:
  - id: DEC-1403-01
    decision: "Section renderers use keyword argument doc_type_config=None for backward compatibility"
    rationale: "All existing callers pass no config; adding keyword-only avoids breaking signatures"
  - id: DEC-1403-02
    decision: "Congressional Key Ask uses program description instead of advocacy_lever for ASK line"
    rationale: "Advocacy lever text contains strategic framing ('Increase', 'Restore', 'Defend') that violates air gap; description is factual"
  - id: DEC-1403-03
    decision: "Orchestrator _has_complete_data checks awards AND hazards AND delegation"
    rationale: "All three data sources needed for meaningful internal strategy document; partial data gets Doc B only"
  - id: DEC-1403-04
    decision: "Hazard alignment paragraph in economic impact for all doc types (not just internal)"
    rationale: "Hazard-economic connection is factual ('wildfire risk profile reinforces the economic case'); safe for congressional docs"
  - id: DEC-1403-05
    decision: "Change tracking excluded from congressional docs (dtc.is_internal gate)"
    rationale: "Change tracking reveals strategic evolution over time; congressional docs should be point-in-time snapshots"
duration: ~9 minutes
completed: 2026-02-11
---

# Phase 14 Plan 03: Content Filtering & Multi-Doc Generation Summary

Audience-filtered section rendering with conditional strategy/leverage/messaging inclusion, orchestrator multi-doc generation routing Doc A to internal/ and Doc B to congressional/, plus hazard-economic integration (INTG-01) weaving hazard context into per-program economic narratives.

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~9 minutes |
| Start | 2026-02-11T20:34:57Z |
| End | 2026-02-11T20:44:14Z |
| Tasks | 2/2 |
| Files created | 1 |
| Files modified | 4 |
| Tests added | 21 |
| Total tests passing | 691 (647 existing + 21 new + 23 pre-existing) |

## Accomplishments

1. **Audience-differentiated section rendering** -- All 7 section renderers (executive summary, delegation, hazard summary, structural asks, hot sheet, key ask, appendix) accept `doc_type_config` and conditionally include/exclude content. Internal docs (Doc A) get strategic framing, Strategic Notes, hazard-to-program alignment, advocacy language, and messaging framework. Congressional docs (Doc B) get evidence-only content with factual citations.

2. **Messaging framework section** -- New `render_messaging_framework()` for Doc A only. Contains core message with hazard context, congressional office framing guidance, and committee-specific talking points. Never appears in Doc B.

3. **Economic-hazard integration (INTG-01)** -- When hazard profile has real data, hot sheet economic impact sections include a "Hazard Alignment" paragraph connecting the Tribe's top hazard exposure to the economic case for continued program investment.

4. **Congressional Key Ask differentiation** -- Doc B Key Ask boxes use program description for the ASK line (factual) instead of advocacy lever text (strategic). WHY and IMPACT lines preserved in both doc types.

5. **Orchestrator multi-doc generation (INTG-02)** -- `generate_tribal_docs()` computes shared economic/relevance/change data once, then generates N documents routed to `internal/` or `congressional/` subdirectories. Complete-data Tribes get Doc A + Doc B; partial-data Tribes get Doc B only.

6. **21 audience filtering tests** -- Comprehensive test suite proving: Doc A contains strategy content (6 tests), Doc B excludes strategy content (5 tests), cover page differentiation (2 tests), Key Ask differentiation (3 tests), economic-hazard integration (2 tests), orchestrator multi-doc generation (2 tests), and air gap compliance (1 test).

## Task Commits

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Audience-filtered section rendering | `983a493` | docx_engine.py, docx_sections.py, docx_hotsheet.py |
| 2 | Orchestrator multi-doc + audience filtering tests | `4e9aaa8` | orchestrator.py, tests/test_audience_filtering.py |

## Files Created

- `tests/test_audience_filtering.py` -- 21 tests across 8 test classes (530 lines)

## Files Modified

- `src/packets/docx_engine.py` -- generate() passes doc_type_config to all section renderers; conditional messaging framework and change tracking; doc-type-aware filename generation
- `src/packets/docx_sections.py` -- 5 renderers accept doc_type_config; new render_messaging_framework(); audience-calibrated intros for exec summary, delegation, hazards, structural asks
- `src/packets/docx_hotsheet.py` -- render_hotsheet/render_all_hotsheets accept doc_type_config; conditional advocacy language; congressional Key Ask uses description; hazard alignment in economic impact
- `src/packets/orchestrator.py` -- generate_tribal_docs(), _has_complete_data(), _generate_single_doc(), _get_output_dir(); imports DOC_A/DOC_B/DocumentTypeConfig

## Decisions Made

1. **DEC-1403-01: Keyword argument for backward compatibility** -- All section renderers use `doc_type_config=None` as keyword-only parameter, ensuring all existing callers (48 tests, orchestrator, CLI) continue working without modification.

2. **DEC-1403-02: Congressional Key Ask uses program description** -- The advocacy_lever field contains strategic framing ("Increase TCR funding to $50M annually", "Restore BRIC funding and Tribal set-aside") that would violate the air gap. Congressional Key Ask ASK line uses the factual program description instead.

3. **DEC-1403-03: Complete data = awards AND hazards AND delegation** -- All three data sources must be present for a Tribe to receive Doc A (internal strategy). Missing any one reduces the document to Doc B only, since internal strategy without data backing is not useful.

4. **DEC-1403-04: Hazard alignment in economic impact for all doc types** -- The hazard alignment paragraph ("Tribe's wildfire risk profile reinforces the economic case...") is factual and safe for congressional docs. It appears whenever hazard data exists, regardless of doc type.

5. **DEC-1403-05: Change tracking excluded from congressional docs** -- Change tracking reveals strategic evolution between generations, which is internal context. Congressional docs are point-in-time snapshots.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added `from __future__ import annotations` to docx_hotsheet.py**

- **Found during:** Task 1, test verification
- **Issue:** TYPE_CHECKING import of DocumentTypeConfig kept the name unavailable at runtime; method signatures using `DocumentTypeConfig | None` caused NameError
- **Fix:** Added `from __future__ import annotations` to make all type hints lazy-evaluated strings
- **Files modified:** src/packets/docx_hotsheet.py
- **Committed in:** `983a493` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Standard Python typing import pattern. No scope change.

## Issues Encountered

None -- plan executed cleanly after the `__future__` import fix.

## Next Phase Readiness

Plan 14-04 (Regional Documents) can proceed immediately:
- All section renderers accept `doc_type_config` for audience differentiation
- DOC_C and DOC_D configurations are pre-built in doc_types.py
- Orchestrator has `_generate_single_doc()` routing pattern for internal/congressional directories
- `render_messaging_framework()` is available (Doc C does not use it per DOC_C config: `include_messaging_framework=False`)
- Regional documents need `region_name` header substitution (already supported by `dtc.format_header(region_name=...)`)

---
*Phase: 14-integration*
*Completed: 2026-02-11*
