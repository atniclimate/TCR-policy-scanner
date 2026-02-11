# Enhancement Proposal: Interactive Knowledge Graph Visualization

**Author:** Horizon Walker, TCR Policy Scanner Research Team
**Date:** 2026-02-11
**Status:** Proposed
**Effort:** 18 story points across 3 sprints

---

## Problem

The TCR Policy Scanner builds a knowledge graph with 9 node types and 10 edge types
that encodes the full landscape of Tribal climate resilience policy: which programs
exist, what authorizes them, how they are funded, what blocks them, and what advocacy
levers can unblock them. This graph is a powerful analytical structure -- but today
it exists only as JSON files and Python dataclasses.

The current graph schema (`src/graph/schema.py`) defines:

**9 Node Types:**
1. `ProgramNode` -- Central unit of advocacy (16 programs)
2. `AuthorityNode` -- Legal basis (20 authorities in `graph_schema.json`)
3. `FundingVehicleNode` -- Money pipeline (8 funding vehicles)
4. `BarrierNode` -- Obstacles (13 barriers)
5. `AdvocacyLeverNode` / Structural Asks (5 structural asks)
6. `ObligationNode` -- Actual spending records from USASpending
7. `TrustSuperNode` -- Federal trust responsibility meta-node (1)
8. `TribeNode` -- Federally recognized Tribal Nation (592)
9. `CongressionalDistrictNode` -- U.S. Congressional District

**10 Edge Types:**
1. `AUTHORIZED_BY` (Program -> Authority)
2. `FUNDED_BY` (Program -> FundingVehicle)
3. `BLOCKED_BY` (Program -> Barrier)
4. `MITIGATED_BY` (Barrier -> AdvocacyLever)
5. `OBLIGATED_BY` (Program -> ObligationNode)
6. `ADVANCES` (StructuralAsk -> Program)
7. `TRUST_OBLIGATION` (TrustSuperNode -> Program)
8. `THREATENS` (ThreatNode -> Program)
9. `REPRESENTED_BY` (TribeNode -> CongressionalDistrictNode)
10. `IN_ECOREGION` (TribeNode -> ecoregion)

A Tribal Leader who could explore this graph interactively -- clicking on their
programs, seeing the connections between funding, barriers, and advocacy levers,
understanding at a glance which programs are secure and which are threatened --
would gain an intuitive understanding of their policy landscape that no static
document can provide.

Today, that graph is locked inside JSON. Let us unlock it.

## Vision

An interactive, browser-based knowledge graph visualization embedded in the existing
GitHub Pages widget (`docs/web/`) where:

- A Tribal Leader types their Tribe's name and the graph renders their specific
  policy landscape: their relevant programs (8-12 via `ProgramRelevanceFilter`),
  connected authorities, funding vehicles, barriers, and advocacy levers
- Node colors indicate CI status at a glance: green (SECURE) through red (TERMINATED)
- Edge thickness indicates relationship strength or urgency
- Clicking a node opens a data card with full details
- The graph updates automatically when new scan data is published
- The visualization runs entirely client-side (no server needed, aligns with static
  GitHub Pages deployment)

A Tribal climate coordinator in Oklahoma opens the widget, types "Absentee-Shawnee,"
and sees a force-directed graph centered on their 10 relevant programs. BIA TCR glows
green (STABLE). FEMA BRIC pulses red (FLAGGED). She clicks on FEMA BRIC and sees:
"FEMA announced termination of BRIC on April 4, 2025. Advocacy must pivot to the
replacement mechanism." She follows the MITIGATED_BY edge to the "Restore/Replace
with Tribal Set-Aside" lever and reads the specific action. She understands her
landscape in 30 seconds.

That is the power of making data visual.

## Technical Approach

### Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Graph Rendering | **D3.js v7** (force-directed layout) | Industry standard, no dependencies, runs client-side, fine-grained control |
| Data Format | **Pre-computed JSON per Tribe** | Static files on GitHub Pages, no API needed |
| Embedding | **iframe or direct integration** | Same pattern as existing search widget |
| Styling | **CSS variables** | Align with existing `style.css` color palette |
| Interaction | **Vanilla JS** | Keep bundle small (target <50KB added to existing 15KB) |

**Why D3.js over alternatives:**
- **vis.js / vis-network**: Heavier bundle (~300KB), less control over styling
- **Cytoscape.js**: Better for bioinformatics, overkill for our graph size
- **Three.js / WebGL**: 3D is unnecessary complexity for policy relationships
- **Sigma.js**: Good for very large graphs (10K+ nodes), but our per-Tribe graphs
  are small (20-50 nodes)

D3 force-directed layout handles our graph size (20-50 nodes per Tribe view,
~100 nodes in the full 16-program overview) with excellent performance and
complete styling control.

### Data Format

Each Tribe gets a pre-computed graph JSON file alongside their existing data caches:

```
data/graph_cache/
  epa_100000001.json    # Absentee-Shawnee Tribe
  epa_100000002.json    # Agua Caliente Band
  ...
  overview.json         # Full 16-program system view
```

**Per-Tribe graph JSON structure:**

```json
{
  "tribe_id": "epa_100000001",
  "tribe_name": "Absentee-Shawnee Tribe of Indians of Oklahoma",
  "generated_at": "2026-02-10T17:35:21Z",
  "nodes": [
    {
      "id": "bia_tcr",
      "type": "ProgramNode",
      "label": "BIA TCR",
      "name": "BIA Tribal Climate Resilience",
      "ci_status": "STABLE",
      "ci_score": 0.88,
      "priority": "critical",
      "agency": "BIA",
      "relevance_score": 95,
      "detail": {
        "funding_type": "Discretionary",
        "access_type": "direct",
        "advocacy_lever": "Protect/expand the line; waived match, multi-year stability",
        "ci_determination": "FY26 funded at $34.291M..."
      }
    },
    {
      "id": "auth_snyder_act",
      "type": "AuthorityNode",
      "label": "Snyder Act",
      "citation": "25 U.S.C. 13",
      "durability": "Permanent",
      "detail": {}
    },
    {
      "id": "bar_appropriations_volatility",
      "type": "BarrierNode",
      "label": "Appropriations Volatility",
      "severity": "High",
      "barrier_type": "Statutory",
      "detail": {
        "description": "Annual appropriations volatility creates year-to-year uncertainty..."
      }
    },
    {
      "id": "ask_multi_year",
      "type": "AdvocacyLeverNode",
      "label": "Multi-Year Funding",
      "target": "Congress",
      "urgency": "FY26",
      "detail": {
        "description": "Shift from annual discretionary to multi-year or permanent authorization..."
      }
    },
    {
      "id": "FEDERAL_TRUST_RESPONSIBILITY",
      "type": "TrustSuperNode",
      "label": "Federal Trust Responsibility",
      "detail": {
        "legal_basis": "Cherokee Nation v. Georgia (1831)..."
      }
    }
  ],
  "edges": [
    {"source": "bia_tcr", "target": "auth_snyder_act", "type": "AUTHORIZED_BY", "strength": 1.0},
    {"source": "bia_tcr", "target": "bar_appropriations_volatility", "type": "BLOCKED_BY", "strength": 0.8},
    {"source": "bar_appropriations_volatility", "target": "ask_multi_year", "type": "MITIGATED_BY", "strength": 0.9},
    {"source": "FEDERAL_TRUST_RESPONSIBILITY", "target": "bia_tcr", "type": "TRUST_OBLIGATION", "strength": 1.0}
  ]
}
```

### Visual Design

#### Node Styling by Type

| Node Type | Shape | Size | Default Color |
|-----------|-------|------|--------------|
| ProgramNode | Circle | Large (radius 30) | CI status color (see below) |
| AuthorityNode | Rounded rectangle | Medium (20x40) | Steel blue (#4682B4) |
| FundingVehicleNode | Diamond | Medium (25) | Gold (#DAA520) |
| BarrierNode | Octagon (stop sign) | Medium (22) | Crimson (#DC143C) |
| AdvocacyLeverNode | Star | Medium (25) | Forest green (#228B22) |
| TrustSuperNode | Double circle | Extra large (40) | Deep purple (#4A148C) |
| ObligationNode | Small circle | Small (12) | Teal (#008080) |
| TribeNode | Hexagon | Large (35) | Warm brown (#795548) |
| CongressionalDistrictNode | Rectangle | Small (15x30) | Slate gray (#708090) |

#### CI Status Colors (ProgramNode fills)

| CI Status | Color | Hex |
|-----------|-------|-----|
| SECURE | Deep green | #2E7D32 |
| STABLE | Green | #43A047 |
| STABLE_BUT_VULNERABLE | Yellow-green | #9E9D24 |
| AT_RISK | Amber | #F57F17 |
| UNCERTAIN | Orange | #EF6C00 |
| FLAGGED | Red-orange | #E65100 |
| TERMINATED | Red | #C62828 |

These colors align with the existing DOCX packet color palette in
`src/packets/docx_styles.py`, ensuring visual consistency across all outputs.

#### Edge Styling by Type

| Edge Type | Line Style | Color | Thickness Logic |
|-----------|-----------|-------|----------------|
| AUTHORIZED_BY | Solid | Steel blue | Uniform (2px) |
| FUNDED_BY | Solid, thick | Gold | Amount-proportional (2-6px) |
| BLOCKED_BY | Dashed | Red | Severity-proportional |
| MITIGATED_BY | Dotted-dash | Green | Confidence of mitigation |
| OBLIGATED_BY | Solid | Teal | Amount-proportional |
| ADVANCES | Solid arrow | Forest green | Number of programs advanced |
| TRUST_OBLIGATION | Double line | Purple | Uniform (3px) |
| THREATENS | Pulsing dashed | Red | Days-remaining inversely proportional |
| REPRESENTED_BY | Thin solid | Gray | Uniform (1px) |
| IN_ECOREGION | Thin dotted | Brown | Uniform (1px) |

#### Interaction Design

**Hover:** Node enlarges 1.3x, connected edges highlight, tooltip shows label
and one-line summary.

**Click:** Opens a data card panel (right side or bottom) with full details:

```
┌──────────────────────────────────────────┐
│  BIA Tribal Climate Resilience           │
│  ─────────────────────────────────────── │
│  Agency: Bureau of Indian Affairs        │
│  CI Status: STABLE (0.88)               │
│  FY26 Status: Funded at $34.291M        │
│  Priority: Critical                      │
│  Access: Direct                          │
│                                          │
│  Advocacy Lever:                         │
│  Protect/expand the line; waived match,  │
│  multi-year stability                    │
│                                          │
│  Connected To:                           │
│  ● Snyder Act (AUTHORIZED_BY)           │
│  ● ISDEAA (AUTHORIZED_BY)               │
│  ● FY26 Interior Approps (FUNDED_BY)    │
│  ● Appropriations Volatility (BLOCKED)  │
│  ● Federal Trust (TRUST_OBLIGATION)     │
│                                          │
│  [View Full Program Details]             │
└──────────────────────────────────────────┘
```

**Double-click:** Expand/collapse a node's neighborhood (show/hide connected
nodes that are not yet visible).

**Search:** Typing a program name, authority, or barrier highlights matching
nodes with a pulsing border.

**Filter toggles:** Buttons to show/hide node types:
```
[Programs] [Authorities] [Funding] [Barriers] [Levers] [Trust]
```

### Layout Algorithms

Three layout options, user-selectable:

1. **Force-directed** (default): D3 force simulation with:
   - Center force on ProgramNodes
   - Link distance proportional to relationship strength
   - Collision detection to prevent overlap
   - TrustSuperNode anchored at top center

2. **Hierarchical**: Top-down layout showing:
   ```
   Trust Responsibility
        │
   Programs (sorted by CI)
      │         │
   Authorities  Funding
      │
   Barriers
      │
   Advocacy Levers
   ```

3. **Radial**: Tribe at center, programs in inner ring, everything else in
   outer rings by hop distance.

### Graph Data Generation

A new module `src/graph/export.py` generates the per-Tribe graph JSON:

```python
class GraphExporter:
    """Exports per-Tribe interactive graph data.

    Reads from:
    - data/program_inventory.json (16 programs)
    - data/graph_schema.json (authorities, barriers, levers, trust)
    - src/packets/relevance.py (ProgramRelevanceFilter for per-Tribe filtering)

    Writes to:
    - data/graph_cache/{tribe_id}.json (per-Tribe graph)
    - data/graph_cache/overview.json (system-wide graph)
    """

    def export_tribe(self, tribe_id: str, context: TribePacketContext) -> dict:
        """Generate graph JSON for a single Tribe."""
        # 1. Filter to relevant programs (8-12)
        # 2. Collect connected authorities, barriers, levers
        # 3. Build node list with CI status colors
        # 4. Build edge list with strength metadata
        # 5. Return serializable dict
        ...

    def export_overview(self) -> dict:
        """Generate system-wide overview graph (all 16 programs)."""
        ...
```

This integrates into the existing `PacketOrchestrator` pipeline so graph data
is regenerated alongside DOCX packets.

### Embedding Strategy

The interactive graph lives alongside the existing search widget:

```
docs/web/
  index.html          # Existing search widget (enhanced with graph tab)
  css/
    style.css         # Existing styles (extended)
    graph.css         # Graph-specific styles (NEW, ~3KB)
  js/
    app.js            # Existing search logic (extended)
    graph.js          # Graph rendering (NEW, ~25KB)
    d3.min.js         # D3.js v7 (NEW, ~30KB gzipped)
  data/
    graph/            # Pre-computed graph JSON files
      overview.json
      epa_100000001.json
      ...
```

**Integration with existing widget:**

The `index.html` gains a tabbed interface:

```html
<nav class="tcr-tabs" role="tablist">
  <button role="tab" aria-selected="true" data-tab="search">Search Packets</button>
  <button role="tab" data-tab="graph">Explore Graph</button>
</nav>

<div id="tab-search" class="tcr-tab-panel">
  <!-- Existing search widget -->
</div>

<div id="tab-graph" class="tcr-tab-panel" hidden>
  <div id="graph-search">
    <input type="text" placeholder="Type a Tribe name..." />
  </div>
  <div id="graph-container">
    <!-- D3 renders here -->
  </div>
  <div id="graph-detail-panel">
    <!-- Node data card renders here -->
  </div>
</div>
```

**Total bundle size increase:** ~58KB (25KB graph.js + 30KB d3.min.js + 3KB graph.css),
bringing the total widget from 15KB to ~73KB -- still lightweight enough for
SquareSpace iframe embedding.

### Live Update Strategy

The graph updates when new scan data is published:

1. `daily-scan.yml` runs the pipeline (existing)
2. Pipeline generates new graph cache JSON files (new step)
3. GitHub Actions commits updated graph JSON to `docs/web/data/graph/` (new step)
4. GitHub Pages serves the updated files (existing)
5. Client-side JS checks `generated_at` timestamp and refreshes if stale (new)

Since the graph JSON is pre-computed (not generated client-side), the update is
a file replacement, not a computation. Load time for a per-Tribe graph (~5KB JSON)
is negligible.

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| `src/graph/schema.py` | Exists (v1.0) | Node/edge type definitions |
| `data/graph_schema.json` | Exists (v1.0) | 20 authorities, 13 barriers, 5 asks |
| `data/program_inventory.json` | Exists (v1.0) | 16 programs with CI scores |
| `src/packets/relevance.py` | Exists (v1.1) | ProgramRelevanceFilter for per-Tribe filtering |
| `docs/web/index.html` | Exists (v1.1) | Extend with graph tab |
| `docs/web/js/app.js` | Exists (v1.1) | Extend with tab management |
| D3.js v7 | New dependency | CDN or vendored (~30KB gzipped) |
| Graph cache population | New | Requires pipeline integration |
| Data cache population | v1.2 tech debt | Graph quality depends on data quality |

## Effort Estimate

### Phase 1: Graph Export and Data Format (5 SP, Sprint 1)

- Implement `src/graph/export.py` (GraphExporter)
- Generate per-Tribe graph JSON from existing data
- Generate overview graph JSON
- Integrate export into PacketOrchestrator pipeline
- Tests: 10-15 new tests

### Phase 2: D3 Visualization Core (8 SP, Sprint 2)

- Build `docs/web/js/graph.js` with D3 force-directed layout
- Implement node styling by type (shapes, colors, sizes)
- Implement edge styling by type (line styles, thickness)
- Implement CI status color mapping
- Add hover tooltips and click-to-select
- Build data card panel for node details
- Integrate with existing search widget (tabbed interface)

### Phase 3: Polish and Interaction (5 SP, Sprint 3)

- Add layout toggle (force-directed / hierarchical / radial)
- Add node type filter toggles
- Add search highlighting
- Add double-click neighborhood expansion
- Add live update detection (timestamp check)
- Accessibility: keyboard navigation, screen reader labels, WCAG 2.1 AA
- Performance testing with 592-Tribe dataset
- Mobile responsive layout

**Total: 18 story points across 3 sprints (~6 weeks)**

## Impact Statement: How This Serves Tribal Sovereignty

Policy is relationships. A program exists because a statute authorizes it. It survives
because an appropriation funds it. It falters because a barrier blocks it. It recovers
because an advocacy lever unlocks it. These relationships are not obvious from a
flat document. They are obvious from a graph.

When a Tribal Leader sees their policy landscape as an interconnected network, they
gain something that no briefing document can provide: intuition. They see that FEMA
BRIC is red (FLAGGED) and connected to a barrier ("BRIC program terminated") and
connected to a lever ("Restore/Replace with Tribal Set-Aside"). The path from
problem to action is visible. They see that the Trust Super-Node connects to 5
programs, reinforcing that these are not discretionary gifts but legal obligations.

For the 592 Tribal Nations we serve, an interactive knowledge graph transforms the
scanner from a document generator into a decision support system. A Tribal climate
coordinator exploring connections in the graph will discover relationships between
programs that a static document obscures. She might see that three of her Tribe's
priority programs all share the same barrier (cost-share requirements) and the same
mitigation lever (match waivers) -- and realize that one advocacy action could
unlock three programs simultaneously.

That kind of strategic insight is what happens when data becomes visible. When policy
relationships become navigable. When a Tribal Leader can explore the full landscape
of federal obligations to their community and trace the path from where they are to
where they need to be.

The graph already exists in the data. This proposal makes it exist for the people
it serves.

---

*Proposed by Horizon Walker. The connections are already there. We just need to draw them.*
