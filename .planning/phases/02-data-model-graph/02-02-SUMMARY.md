---
phase: 02-data-model-graph
plan: 02
subsystem: graph
tags: [knowledge-graph, structural-asks, trust-responsibility, advances-edges, trust-obligation, advocacy-levers]

# Dependency graph
requires:
  - phase: 02-data-model-graph/plan-01
    provides: "Plan 01 enriched data model files; Plan 02 extends graph builder to consume structural_asks already in graph_schema.json"
provides:
  - "5 AdvocacyLeverNodes for Five Structural Asks with 26 ADVANCES edges"
  - "TrustSuperNode (FEDERAL_TRUST_RESPONSIBILITY) with 5 TRUST_OBLIGATION edges to BIA/EPA programs"
  - "9 MITIGATED_BY edges from structural asks to barriers"
  - "TrustSuperNode dataclass in schema.py"
affects: [03-monitoring-logic, 04-report-enhancements]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Structural asks reuse AdvocacyLeverNode with ask_ prefix to distinguish from per-program lever_ nodes"
    - "Trust Super-Node pattern: single meta-node with TRUST_OBLIGATION edges to multiple programs"
    - "Schema-driven seeding: new _seed_structural_asks and _seed_trust_node methods follow same pattern as existing barrier/authority seeding"

key-files:
  created: []
  modified:
    - src/graph/schema.py
    - src/graph/builder.py
    - data/graph_schema.json

key-decisions:
  - "Structural asks use AdvocacyLeverNode (not new type) per RESEARCH.md recommendation, distinguished by ask_ ID prefix"
  - "Trust Super-Node connects to 5 BIA/EPA programs that carry direct trust responsibility implications"
  - "ADVANCES edge type: structural ask -> program (advocacy direction); TRUST_OBLIGATION: trust node -> program (obligation direction)"

patterns-established:
  - "New edge types added to Edge docstring as canonical reference for graph relationship types"
  - "Graph builder seed methods accept schema dict parameter for testability and composition"

# Metrics
duration: 2min
completed: 2026-02-09
---

# Phase 2 Plan 2: Graph Schema & Builder Enhancements Summary

**TrustSuperNode dataclass and trust_super_node JSON data added; GraphBuilder extended with _seed_structural_asks (5 nodes, 26 ADVANCES + 9 MITIGATED_BY edges) and _seed_trust_node (1 node, 5 TRUST_OBLIGATION edges) methods wired into _seed_from_schema pipeline**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-02-09
- **Completed:** 2026-02-09
- **Tasks:** 2/2 (all auto)
- **Files modified:** 3

## Accomplishments

- Added TrustSuperNode dataclass to schema.py with id, name, description, legal_basis fields
- Added trust_super_node object to graph_schema.json with FEDERAL_TRUST_RESPONSIBILITY connecting to 5 BIA/EPA programs (bia_tcr, bia_tcr_awards, epa_gap, epa_stag, epa_tribal_air)
- Updated Edge class docstring to document ADVANCES and TRUST_OBLIGATION edge types
- Added _seed_structural_asks method loading 5 structural asks as AdvocacyLeverNodes
- Created 26 ADVANCES edges from structural asks to their connected programs
- Created 9 MITIGATED_BY edges from structural asks to their connected barriers
- Added _seed_trust_node method creating FEDERAL_TRUST_RESPONSIBILITY TrustSuperNode
- Created 5 TRUST_OBLIGATION edges from trust node to BIA/EPA Tribal programs
- Wired both methods into _seed_from_schema pipeline (called after barriers loop)
- Graph now produces 79 nodes (up from 73) and 118 edges (up from 78) in static seeding mode
- TrustSuperNode appears in graph serialization node_types

## Task Commits

1. **Task 1: Add TrustSuperNode class and Trust Super-Node JSON data** - `eee35e2`
2. **Task 2: Extend GraphBuilder to load Structural Asks and Trust Super-Node** - `d74c603`

## Files Created/Modified

- `src/graph/schema.py` - Added TrustSuperNode dataclass; updated Edge docstring with ADVANCES and TRUST_OBLIGATION edge types
- `src/graph/builder.py` - Added _seed_structural_asks and _seed_trust_node methods; imported TrustSuperNode; wired into _seed_from_schema
- `data/graph_schema.json` - Added trust_super_node object with FEDERAL_TRUST_RESPONSIBILITY and 5 connected programs

## Decisions Made

- **Structural asks reuse AdvocacyLeverNode:** Per RESEARCH.md recommendation, structural asks use the existing AdvocacyLeverNode type with `ask_` ID prefix to distinguish from per-program `lever_` nodes. This avoids a new node type while maintaining clear separation.
- **Trust Super-Node connects to 5 specific programs:** BIA TCR, BIA TCR Awards, EPA GAP, EPA STAG, and EPA Tribal Air were selected as programs carrying direct trust responsibility implications for environmental protection on Tribal lands.
- **Edge direction conventions:** ADVANCES edges flow from structural ask to program (advocacy direction); TRUST_OBLIGATION edges flow from trust node to program (obligation direction).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

- GRAPH-01 (structural asks as AdvocacyLeverNodes), GRAPH-02 (Trust Super-Node), GRAPH-05 (ADVANCES and TRUST_OBLIGATION edges) requirements addressed
- Phase 2 (Data Model and Graph) is now complete (2/2 plans)
- Ready for Phase 3 (Monitoring and Logic)
- No blockers or concerns

---
*Phase: 02-data-model-graph*
*Completed: 2026-02-09*
