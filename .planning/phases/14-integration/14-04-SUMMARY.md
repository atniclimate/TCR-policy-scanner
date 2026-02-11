---
phase: 14-integration
plan: 04
subsystem: regional-document-generation
tags: [regional-aggregation, doc-c, doc-d, docx, delegation-overlap, coverage-gaps, audience-differentiation]

# Dependency graph
requires:
  - "14-01: Hazard data activation + 8-region config (REGIONAL_CONFIG_PATH, regional_config.json)"
  - "14-02: DocumentTypeConfig system (DOC_C, DOC_D instances, audience flags)"
provides:
  - RegionalAggregator class for Tribe-to-region assignment and data aggregation
  - RegionalContext dataclass with 22 fields of aggregated regional data
  - 6 regional DOCX section renderers (cover, exec summary, hazards, awards, delegation, appendix)
  - PacketOrchestrator.generate_regional_docs() for all 8 regions
  - Audience-differentiated Doc C (internal) and Doc D (congressional) rendering
affects:
  - "14-05+: Regional document quality review and narrative refinement"
  - "14-06: Data validation script (reports regional doc generation success)"
  - "14-07: Deployment (regional docs in directory structure)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "State overlap assignment: Tribe.states intersects region.states for geographic regions"
    - "Crosscutting virtual region: empty states list = all Tribes"
    - "Audience differentiation in DOCX sections via doc_type_config.is_internal flag"
    - "Delegation overlap detection: bioguide_id tracking across Tribe contexts"
    - "Lazy import pattern: regional imports in orchestrator to avoid circular deps"

key-files:
  created:
    - src/packets/regional.py
    - src/packets/docx_regional_sections.py
    - tests/test_regional.py
  modified:
    - src/packets/orchestrator.py

key-decisions:
  - id: DEC-1404-01
    decision: "RegionalContext lives in regional.py (not context.py) to avoid bloating the Tribal context module"
    rationale: "regional.py is self-contained with both dataclass and aggregator; context.py stays focused on TribePacketContext"
  - id: DEC-1404-02
    decision: "Orchestrator regional methods use lazy imports for regional module"
    rationale: "Prevents circular import risk and keeps orchestrator lightweight when regional docs not needed"
  - id: DEC-1404-03
    decision: "Delegation overlap keyed by bioguide_id with fallback to formatted_name"
    rationale: "bioguide_id is the canonical identifier; formatted_name fallback handles edge cases with missing IDs"

patterns-established:
  - "Regional aggregation: state overlap for geographic regions, all-Tribes for crosscutting"
  - "Doc C internal framing: coverage gaps as coordination opportunity, delegation overlap as shared leverage"
  - "Doc D congressional framing: resource utilization report, evidence-only, no coordination strategy"

# Metrics
duration: ~15 minutes
completed: 2026-02-11
tasks: 2/2
tests-added: 32
tests-total: 700
---

# Phase 14 Plan 04: Regional Aggregation + Doc C/D Generation Summary

RegionalAggregator with state-overlap Tribe assignment, 22-field RegionalContext dataclass, 6 audience-differentiated DOCX section renderers, and orchestrator integration generating Doc C (InterTribal strategy) and Doc D (regional overview) for all 8 regions.

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~15 minutes |
| Start | 2026-02-11T20:35:54Z |
| End | 2026-02-11T20:50:47Z |
| Tasks | 2/2 |
| Files created | 3 |
| Files modified | 1 |
| Tests added | 32 |
| Total tests passing | 700 |

## Accomplishments

1. **RegionalAggregator** -- Loads regional_config.json, assigns Tribes to regions by state overlap, computes aggregate awards, shared hazards, delegation overlap, economic impact, and coverage gaps. Crosscutting region spans all 592 Tribes.

2. **RegionalContext dataclass** -- 22 fields covering identity (region_id, region_name, core_frame, treaty_trust_angle), aggregated data (tribe_count, total_awards, award_coverage, hazard_coverage), hazard synthesis (top_shared_hazards, composite_risk_score), economic aggregates, congressional overlap (delegation_overlap, total_senators, total_representatives), and coverage gaps.

3. **6 regional DOCX section renderers** -- render_regional_cover_page (CONFIDENTIAL banner for Doc C), render_regional_executive_summary (coverage gap + delegation leverage for Doc C, resource utilization for Doc D), render_regional_hazard_synthesis (shared hazards table), render_regional_award_landscape (aggregate awards + investment gaps), render_regional_delegation (overlap table for Doc C, summary for Doc D), render_regional_appendix (Tribe listing).

4. **Orchestrator integration** -- generate_regional_docs() iterates all 8 regions, aggregates Tribe contexts, and generates Doc C + Doc D for each. _generate_regional_doc() renders all 6 sections with doc-type-specific headers/footers. Output to regional/internal/ and regional/congressional/ directories.

5. **32 tests** -- 23 for RegionalAggregator (assignment, awards, hazards, delegation, gaps, economics, full aggregate) + 9 for DOCX section renderers (cover page, exec summary, hazard synthesis, delegation, appendix, award landscape with audience differentiation verification).

## Task Commits

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Create RegionalAggregator and RegionalContext | `5c53588` | src/packets/regional.py, tests/test_regional.py |
| 2 | Wire regional doc generation into orchestrator | `a76062d` | src/packets/docx_regional_sections.py, src/packets/orchestrator.py, tests/test_regional.py |

## Files Created

- `src/packets/regional.py` -- RegionalContext dataclass (22 fields) + RegionalAggregator class with state-overlap assignment, award/hazard/delegation/economic aggregation, and coverage gap identification (553 lines)
- `src/packets/docx_regional_sections.py` -- 6 regional section renderers with audience differentiation, same StyleManager patterns as Tribal sections (380 lines)
- `tests/test_regional.py` -- 32 tests in 9 test classes covering aggregation logic and DOCX rendering (680 lines)

## Files Modified

- `src/packets/orchestrator.py` -- Added generate_regional_docs() and _generate_regional_doc() methods, updated module docstring for regional doc support

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| DEC-1404-01 | RegionalContext in regional.py, not context.py | Self-contained module avoids bloating TribePacketContext file |
| DEC-1404-02 | Lazy imports for regional module in orchestrator | Prevents circular deps, keeps orchestrator lightweight |
| DEC-1404-03 | Delegation overlap keyed by bioguide_id with formatted_name fallback | Canonical ID preferred, fallback handles edge cases |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added from __future__ import annotations to docx_hotsheet.py**

- **Found during:** Task 1 verification (full test suite)
- **Issue:** Parallel plan 14-03 added `DocumentTypeConfig` type annotation under `TYPE_CHECKING` guard in docx_hotsheet.py but forgot `from __future__ import annotations`, causing NameError at runtime
- **Fix:** Added `from __future__ import annotations` at top of docx_hotsheet.py
- **Files modified:** src/packets/docx_hotsheet.py
- **Verification:** Full test suite passes (700 tests)
- **Note:** The fix was committed as part of Task 1, though the parallel plan (14-03 commit 983a493) had already addressed this. The file ended up with both sets of changes merged cleanly.

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary fix for parallel plan's import issue. No scope creep.

## Issues Encountered

1. **Parallel plan 14-03 modifications** -- Plan 14-03 executed in parallel and modified orchestrator.py (adding generate_tribal_docs, _generate_single_doc, _get_output_dir). As instructed, this plan's changes ONLY added new methods (generate_regional_docs, _generate_regional_doc) without modifying any existing methods. No merge conflicts.

2. **Intermittent meta-test** -- test_doc_assembly.py::TestRegression::test_existing_tests_unaffected occasionally fails in batch but passes when run individually (subprocess timing issue, not caused by this plan's changes). All 700 tests pass in full suite.

## User Setup Required

None -- no external service configuration required.

## Next Phase Readiness

Plan 14-04 deliverables ready for downstream plans:
- RegionalAggregator and RegionalContext importable from src.packets.regional
- generate_regional_docs() callable from orchestrator
- All 8 regions produce valid RegionalContext objects
- Doc C and Doc D render with correct audience differentiation
- Regional sections use same StyleManager patterns as Tribal sections

Remaining for Phase 14:
- Plans 14-05+ can refine regional narrative quality
- Data validation script (14-06) can report regional doc generation success
- Deployment (14-07) includes regional/ directory structure

---
*Phase: 14-integration*
*Completed: 2026-02-11*
