# Phase 2: Data Model and Graph Enhancements - Research

**Researched:** 2026-02-09
**Domain:** Brownfield Python codebase -- JSON data files + graph builder modifications
**Confidence:** HIGH

## Summary

This research thoroughly examines the existing TCR Policy Scanner codebase to understand exactly how JSON data files are structured, how the graph builder consumes them, and how downstream components (analysis, reporting) depend on the graph output. The goal is to give the planner precise knowledge of what files to modify, what patterns to follow, and what downstream dependencies to verify.

The codebase follows a clean pattern: four JSON data files (`program_inventory.json`, `policy_tracking.json`, `graph_schema.json`, `scanner_config.json`) are loaded by Python modules (`main.py`, `builder.py`, `relevance.py`, `generator.py`) that build an in-memory knowledge graph, score items, and generate reports. Phase 2 work is primarily JSON data editing with targeted Python code changes to `src/graph/schema.py` and `src/graph/builder.py` to handle new node types (Trust Super-Node) and edge types (ADVANCES, TRUST_OBLIGATION).

**Primary recommendation:** Split work into two plans: (1) data file updates (program_inventory, policy_tracking, scanner_config) which require zero Python changes, and (2) graph schema/builder enhancements (Five Structural Asks loading, Trust Super-Node, ADVANCES/TRUST_OBLIGATION edges) which require Python changes to `schema.py` and `builder.py`.

## Standard Stack

This is a brownfield project. The "standard stack" is the existing codebase, not external libraries.

### Core Files to Modify

| File | Purpose | What Changes |
|------|---------|-------------|
| `data/program_inventory.json` | 16 programs with CI, keywords, advocacy levers | Add 2 programs, update CI/status for all, add trigger keywords |
| `data/policy_tracking.json` | FY26 positions with CI thresholds | Add TERMINATED tier, verify all 16 positions match inventory |
| `data/graph_schema.json` | Authorities, barriers, funding vehicles, structural asks | Add authorities/barriers, verify structural asks are complete |
| `config/scanner_config.json` | Sources, scoring weights, keywords | Add reconciliation/repeal trigger keywords to search_queries |
| `src/graph/schema.py` | Dataclass definitions for node/edge types | Add TrustSuperNode dataclass, ADVANCES/TRUST_OBLIGATION edge docs |
| `src/graph/builder.py` | Graph construction from schema + scraped data | Add `_seed_structural_asks()`, `_seed_trust_node()` methods |

### Files That Must NOT Break (Downstream Consumers)

| File | What It Reads | Risk |
|------|--------------|------|
| `src/main.py` | `program_inventory.json` via `load_programs()` -- expects `{"programs": [...]}` | Shape change breaks pipeline |
| `src/analysis/relevance.py` | Programs list -- uses `keywords`, `scanner_trigger_keywords`, `priority`, `ci_status` | Missing fields cause KeyError |
| `src/reports/generator.py` | Programs dict + graph_data dict -- reads `_type`, node fields, edge types | New node types need serialization |
| `src/scrapers/grants_gov.py` | `CFDA_NUMBERS` hardcoded dict -- new programs with CFDA need entries here | Missing CFDA = no targeted scraping |

### No New Dependencies

No new Python packages are needed. All changes use `json`, `dataclasses`, `pathlib`, and `logging` -- already in the codebase.

## Architecture Patterns

### Existing Project Structure
```
F:\tcr-policy-scanner\
  config/
    scanner_config.json      # Source configs, scoring weights, keywords
  data/
    program_inventory.json   # Program definitions (CI, keywords, advocacy)
    policy_tracking.json     # FY26 positions with CI thresholds
    graph_schema.json        # Static graph data (authorities, barriers, asks)
  src/
    main.py                  # Pipeline orchestrator
    graph/
      schema.py              # Node/Edge dataclasses
      builder.py             # KnowledgeGraph + GraphBuilder classes
    analysis/
      relevance.py           # Multi-factor scoring
      change_detector.py     # Scan-to-scan diff
    reports/
      generator.py           # Markdown + JSON output
    scrapers/
      base.py                # Shared resilience patterns
      federal_register.py    # Federal Register API
      grants_gov.py          # Grants.gov API (has CFDA_NUMBERS dict)
      congress_gov.py        # Congress.gov API
      usaspending.py         # USASpending API
  outputs/
    LATEST-BRIEFING.md       # Generated report
    LATEST-RESULTS.json      # Generated data
    LATEST-GRAPH.json        # Generated graph
```

### Pattern 1: Program Inventory Entry Structure
**What:** Each program in `program_inventory.json` follows an exact schema.
**When to use:** Adding BIA TCR Awards and EPA Tribal Air Quality programs.
**Existing example (from `program_inventory.json`):**
```json
{
  "id": "bia_tcr_awards",
  "name": "Tribal Community Resilience Annual Awards",
  "agency": "BIA",
  "federal_home": "Bureau of Indian Affairs",
  "priority": "high",
  "keywords": ["community resilience", "annual awards", "BIA resilience", "tribal community resilience", "TCR awards"],
  "search_queries": ["BIA tribal community resilience annual awards", "tribal community resilience awards"],
  "advocacy_lever": "Protect award program; ensure multi-year planning capacity",
  "description": "BIA annual awards program for Tribal community resilience projects.",
  "confidence_index": 0.85,
  "ci_status": "STABLE",
  "ci_determination": "Established BIA program tied to TCR appropriations line.",
  "cfda": "15.124"
}
```

**Required fields (every program must have these):** `id`, `name`, `agency`, `federal_home`, `priority`, `keywords`, `search_queries`, `advocacy_lever`, `description`, `confidence_index`, `ci_status`, `ci_determination`

**Optional fields:** `cfda`, `tightened_language`, `specialist_required`, `specialist_focus`, `proposed_fix`, `scanner_trigger_keywords`

### Pattern 2: Policy Tracking Position Structure
**What:** Each position in `policy_tracking.json` mirrors a program with advocacy-specific fields.
**Existing example:**
```json
{
  "program_id": "dot_protect",
  "program_name": "DOT PROTECT Grants",
  "agency": "DOT",
  "confidence_index": 0.93,
  "status": "SECURE",
  "reasoning": "Tribal set-aside (2%) is statutorily protected under IIJA S11405.",
  "extensible_fields": {
    "advocacy_priority": "High",
    "tribal_set_aside": "2%",
    "scanner_trigger_keywords": ["PROTECT grant", "transportation resilience"]
  }
}
```

**Required fields:** `program_id`, `program_name`, `agency`, `confidence_index`, `status`, `reasoning`

**The `extensible_fields` object** is freeform -- different programs have different fields. Common ones: `advocacy_priority`, `scanner_trigger_keywords`, `tightened_language`, `proposed_fix`.

### Pattern 3: Graph Schema Authority/Barrier Structure
**What:** Authorities and barriers in `graph_schema.json` link to programs by ID array.
**Existing authority example:**
```json
{
  "id": "auth_ira_48e",
  "citation": "IRA S 48(e) (Low-Income Community Solar)",
  "type": "Statute",
  "durability": "Expires 2032",
  "programs": ["irs_elective_pay"]
}
```

**Existing barrier example:**
```json
{
  "id": "bar_reconciliation_repeal",
  "description": "IRA provisions (S6417 Elective Pay) subject to budget reconciliation repeal",
  "type": "Statutory",
  "severity": "High",
  "programs": ["irs_elective_pay"],
  "mitigated_by": ["lever_irs_elective_pay"]
}
```

**Key:** Barriers have a `mitigated_by` array referencing lever IDs. Levers are created automatically by the builder from `program_inventory.json` advocacy_lever fields (pattern: `lever_{program_id}`).

### Pattern 4: Structural Asks (Already Partially in Schema)
**What:** The `structural_asks` array already exists in `graph_schema.json` with 5 entries.
**Existing example:**
```json
{
  "id": "ask_multi_year",
  "name": "Multi-Year Funding Stability",
  "description": "Shift from annual discretionary to multi-year or permanent authorization",
  "target": "Congress",
  "urgency": "FY26",
  "mitigates": ["bar_appropriations_volatility", "bar_iija_sunset", "bar_reauthorization_gap"],
  "programs": ["bia_tcr", "epa_gap", "doe_indian_energy", ...]
}
```

**CRITICAL FINDING:** The structural asks data is already IN `graph_schema.json` but the `GraphBuilder._seed_from_schema()` method does NOT load them. It only processes `authorities`, `funding_vehicles`, and `barriers`. The builder must be extended to also process `structural_asks`.

### Pattern 5: Graph Builder Seeding Pattern
**What:** The builder loads each schema section in `_seed_from_schema()` by iterating the JSON array, creating nodes, then creating edges linking to program IDs.
**Existing pattern (from `builder.py` lines 183-237):**
```python
def _seed_from_schema(self) -> None:
    with open(self.schema_path) as f:
        schema = json.load(f)

    # Authorities
    for auth in schema.get("authorities", []):
        node = AuthorityNode(id=auth["id"], citation=auth["citation"], ...)
        self.graph.add_node(node)
        for pid in auth.get("programs", []):
            self.graph.add_edge(Edge(source_id=pid, target_id=auth["id"],
                                     edge_type="AUTHORIZED_BY"))

    # Funding vehicles (same pattern)
    # Barriers (same pattern + mitigated_by edges)
```

**To add structural asks:** Follow the identical pattern -- iterate `schema.get("structural_asks", [])`, create `AdvocacyLeverNode` for each, add `ADVANCES` edges from ask to each program.

### Pattern 6: Node Type Serialization
**What:** `node_to_dict()` in `schema.py` adds a `_type` field equal to the class name. The report generator filters nodes by `_type` string.
**Implication:** Any new node class (e.g., `TrustSuperNode`) will automatically get `_type: "TrustSuperNode"` in serialization. The report generator can use this to format Trust Super-Node sections.

### Anti-Patterns to Avoid
- **Modifying `_seed_from_programs()` for structural asks:** The asks are cross-cutting (not per-program). They belong in `_seed_from_schema()`, loaded from `graph_schema.json`.
- **Duplicating lever nodes:** The builder already creates `lever_{program_id}` nodes from each program's advocacy_lever field. Structural asks are DIFFERENT from per-program levers -- they are top-level cross-cutting advocacy positions. Use a different ID prefix (`ask_` is already used in the schema).
- **Breaking the `mitigated_by` reference chain:** Barriers reference levers by ID. If structural asks mitigate barriers, barriers should reference ask IDs (e.g., `ask_multi_year`) in their `mitigated_by` arrays. This is ALREADY done in the existing schema data.
- **Adding TERMINATED as a status without updating ci_thresholds:** The thresholds object maps status names to floor values. TERMINATED needs a floor (could be same as FLAGGED at 0.0, or a separate negative sentinel).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Node serialization | Custom JSON conversion per node type | Existing `node_to_dict()` in `schema.py` | Already handles all dataclasses generically via `__dict__` |
| Edge type validation | Edge type enum or validation layer | Existing string-based edge types | Codebase uses string edge types throughout; changing to enum would break downstream |
| CI score computation | Complex formula engine | Hardcoded values from Strategic Framework | CONTEXT.md gives Claude discretion; the Framework has specific values; formula adds complexity for 16 programs that change infrequently |
| Program-to-position sync | Automated sync validator | Manual alignment during this phase | Phase 3 adds Hot Sheets sync; for now, just ensure consistency during editing |

**Key insight:** This phase is primarily about editing JSON data files and adding 2 small methods to `builder.py`. The existing architecture handles new node/edge types automatically through dataclass serialization and string-based edge typing. Do not over-engineer.

## Common Pitfalls

### Pitfall 1: Program ID Mismatch Between Files
**What goes wrong:** A program ID in `program_inventory.json` does not exactly match the corresponding `program_id` in `policy_tracking.json` or the `programs` arrays in `graph_schema.json`.
**Why it happens:** Four files reference the same program IDs independently. A typo in one file silently breaks graph edges.
**How to avoid:** After editing, verify that every program ID in `program_inventory.json` appears in `policy_tracking.json` positions and has at least one reference in `graph_schema.json` (authority, barrier, or structural ask).
**Warning signs:** Graph builder logs show fewer edges than expected; report generator shows missing programs in tables.

### Pitfall 2: Structural Asks Already Exist But Are Not Loaded
**What goes wrong:** The planner assumes structural asks need to be added to `graph_schema.json`, wasting time adding data that already exists.
**Why it happens:** The `structural_asks` array (5 entries) is ALREADY in `graph_schema.json`. What is missing is the Python code in `builder.py` to load them into the graph.
**How to avoid:** Plan 2.1 should verify/update the structural asks DATA in the JSON. Plan 2.2 should add the Python code to LOAD them.
**Warning signs:** Duplicate structural ask entries in `graph_schema.json`.

### Pitfall 3: Authorities and Barriers Already Partially Present
**What goes wrong:** Adding "new" authorities/barriers that already exist, creating duplicates.
**Why it happens:** The current `graph_schema.json` already has 19 authorities and 13 barriers. Some of the "10 new authorities" and "6 new barriers" from the Strategic Framework may overlap with existing entries.
**How to avoid:** Before adding, check existing IDs. Current authority IDs: `auth_stafford_act`, `auth_snyder_act`, `auth_ira_6417`, `auth_iija`, `auth_nahasda`, `auth_isdeaa`, `auth_clean_water_act`, `auth_energy_policy_act`, `auth_protect_formula`, `auth_iija_wildfire`, `auth_eo14225`, `auth_magnuson_stevens`, `auth_ttp_statute`, `auth_reclamation_act`, `auth_ira_48e`, `auth_ira_45_48`, `auth_caa_105`, `auth_indian_environmental_gap`, `auth_iija_watersmart`. Current barrier IDs: `bar_bric_terminated`, `bar_cost_share`, `bar_plan_requirement`, `bar_instrumentality_ambiguity`, `bar_competitive_only`, `bar_eo14225_reform`, `bar_appropriations_volatility`, `bar_reconciliation_repeal`, `bar_iija_sunset`, `bar_agency_capacity`, `bar_reauthorization_gap`, `bar_data_sovereignty`, `bar_match_burden`.
**Warning signs:** JSON validation shows duplicate IDs; graph node count higher than expected.

### Pitfall 4: New Programs Missing from BIA TCR Awards and EPA Tribal Air
**What goes wrong:** New programs are added to inventory but not to policy_tracking, graph_schema authorities, grants_gov CFDA_NUMBERS, or scanner_config search queries.
**Why it happens:** Multiple files reference programs; forgetting one leaves gaps.
**How to avoid:** Checklist for each new program:
  1. `program_inventory.json` -- program entry
  2. `policy_tracking.json` -- position entry
  3. `graph_schema.json` -- at least one authority links to program ID
  4. `graph_schema.json` -- at least one structural ask includes program in `programs` array
  5. `src/scrapers/grants_gov.py` CFDA_NUMBERS -- if program has a CFDA number
  6. `config/scanner_config.json` search_queries -- any new queries needed

**CRITICAL FINDING ON EXISTING STATE:** Both `bia_tcr_awards` and `epa_tribal_air` already exist in `program_inventory.json` (16 programs total) and `policy_tracking.json` (16 positions). The "add 2 new programs" work appears to have been done during Phase 1 setup. Authority entries for both also exist in `graph_schema.json` (`auth_snyder_act_tcr_awards` for BIA TCR Awards, `auth_caa_105` for EPA Tribal Air). The CFDA number for `bia_tcr_awards` (15.124) is present in inventory but NOT in `grants_gov.py` CFDA_NUMBERS dict.

### Pitfall 5: TERMINATED Status Tier vs FLAGGED Confusion
**What goes wrong:** Adding TERMINATED but not clearly distinguishing it from FLAGGED in thresholds and code.
**Why it happens:** The Strategic Framework describes FEMA BRIC as "TERMINATED -> REPLACEMENT" but the current system uses FLAGGED for terminated programs.
**How to avoid:** Define clear semantics: FLAGGED = active crisis requiring intervention (could be a funding cut, zeroed out, crisis). TERMINATED = program is dead, advocacy pivots to replacement. Add TERMINATED to `ci_thresholds` and `status_definitions`. Decide threshold: could share the 0.0 floor with FLAGGED, or use a separate range (e.g., TERMINATED below FLAGGED).
**Warning signs:** Report generator has special handling for `FLAGGED` status (shows specialist warning). Similar handling may be needed for `TERMINATED`.

### Pitfall 6: Edge Direction Inconsistency
**What goes wrong:** Creating ADVANCES edges in the wrong direction.
**Why it happens:** Existing edges go from PROGRAM -> TARGET (e.g., program AUTHORIZED_BY authority). The ADVANCES edge has different semantics: a structural ask ADVANCES a program's interests.
**How to avoid:** Be explicit about direction. Recommendation: `ADVANCES` edges go from `ask_*` -> `program_*` (ask advances program). This matches the reporting pattern where you ask "what does this structural ask advance?" Alternative: program -> ask ("program is advanced by ask") would match the AUTHORIZED_BY pattern. Choose one and document it in the Edge docstring.
**Warning signs:** Report generator queries edges by source/target and gets wrong results.

## Code Examples

### Example 1: Adding Structural Ask Loading to GraphBuilder

Follow the exact pattern of existing `_seed_from_schema()` sections. This code would be added inside `_seed_from_schema()` in `builder.py`:

```python
# Structural Asks (Five Structural Asks as AdvocacyLeverNodes)
for ask in schema.get("structural_asks", []):
    node = AdvocacyLeverNode(
        id=ask["id"],
        description=ask["description"],
        target=ask.get("target", ""),
        urgency=ask.get("urgency", ""),
    )
    self.graph.add_node(node)
    # ADVANCES edges: Ask -> Program
    for pid in ask.get("programs", []):
        self.graph.add_edge(Edge(
            source_id=ask["id"],
            target_id=pid,
            edge_type="ADVANCES",
        ))
    # Structural ask mitigates barriers
    for bar_id in ask.get("mitigates", []):
        self.graph.add_edge(Edge(
            source_id=ask["id"],
            target_id=bar_id,
            edge_type="MITIGATED_BY",
        ))
```

### Example 2: Trust Super-Node Implementation

New dataclass in `schema.py`:

```python
@dataclass
class TrustSuperNode:
    """Federal trust responsibility meta-node connecting to BIA/EPA Tribal programs."""
    id: str
    name: str
    description: str = ""
    legal_basis: str = ""
```

Loading in `builder.py` (could be in `_seed_from_schema()` or a new `_seed_trust_node()` method):

```python
# Trust Super-Node
trust_data = schema.get("trust_super_node")
if trust_data:
    node = TrustSuperNode(
        id=trust_data["id"],
        name=trust_data["name"],
        description=trust_data.get("description", ""),
        legal_basis=trust_data.get("legal_basis", ""),
    )
    self.graph.add_node(node)
    for pid in trust_data.get("programs", []):
        self.graph.add_edge(Edge(
            source_id=trust_data["id"],
            target_id=pid,
            edge_type="TRUST_OBLIGATION",
        ))
```

JSON in `graph_schema.json`:

```json
{
  "trust_super_node": {
    "id": "FEDERAL_TRUST_RESPONSIBILITY",
    "name": "Federal Trust Responsibility",
    "description": "The federal government's trust obligation to Tribal Nations",
    "legal_basis": "Cherokee Nation v. Georgia (1831); Snyder Act; ISDEAA",
    "programs": ["bia_tcr", "bia_tcr_awards", "epa_gap", "epa_stag", "epa_tribal_air"]
  }
}
```

### Example 3: Adding TERMINATED to Policy Tracking Thresholds

Current `ci_thresholds` in `policy_tracking.json`:
```json
{
  "secure": 0.90,
  "stable": 0.75,
  "stable_but_vulnerable": 0.65,
  "at_risk_floor": 0.40,
  "uncertain_floor": 0.25,
  "flagged_floor": 0.0
}
```

Updated with TERMINATED:
```json
{
  "secure": 0.90,
  "stable": 0.75,
  "stable_but_vulnerable": 0.65,
  "at_risk_floor": 0.40,
  "uncertain_floor": 0.25,
  "flagged_floor": 0.10,
  "terminated_floor": 0.0
}
```

And add to `status_definitions`:
```json
{
  "TERMINATED": "Program confirmed terminated; advocacy pivots to replacement mechanism"
}
```

### Example 4: Adding Reconciliation Keywords to scanner_config.json

Add to the `search_queries` array:
```json
[
  "budget reconciliation tribal",
  "IRA repeal tribal",
  "reconciliation bill energy",
  "section 6417 repeal"
]
```

And ensure the following are in `action_keywords`:
```json
[
  "reconciliation", "reconciliation bill", "revenue offsets",
  "repeal", "section 6417", "elective pay repeal"
]
```

## State of the Art

| Aspect | Current State | Phase 2 Target | What Changes |
|--------|--------------|----------------|-------------|
| Programs | 16 in inventory (includes BIA TCR Awards + EPA Tribal Air) | 16 verified, all with CI | Verify CI scores, add missing trigger keywords |
| Status tiers | 6 tiers (SECURE through FLAGGED) | 7 tiers (add TERMINATED) | Add tier to thresholds + definitions |
| CI scores | Some programs have CI, some need reconciliation | All 16 have Hot Sheets-aligned CI | Update ~5 programs per Strategic Framework |
| Authorities | 19 in graph_schema | 19 + verify completeness | May add a few if Strategic Framework specifies more not yet present |
| Barriers | 13 in graph_schema | 13 + verify completeness | May add a few if Strategic Framework specifies more not yet present |
| Structural asks | 5 in graph_schema JSON but NOT loaded by builder | 5 loaded as AdvocacyLeverNodes with ADVANCES edges | Add Python code to builder |
| Trust Super-Node | Does not exist | FEDERAL_TRUST_RESPONSIBILITY with TRUST_OBLIGATION edges | Add JSON data + Python code |
| Edge types | AUTHORIZED_BY, FUNDED_BY, BLOCKED_BY, MITIGATED_BY, OBLIGATED_BY | Add ADVANCES, TRUST_OBLIGATION | String-based; no enum to update |
| Scanner keywords | 12 search queries, 28 tribal keywords, 30 action keywords | Add reconciliation/repeal terms | JSON edits only |

**Already done (from Phase 1 setup):**
- BIA TCR Awards and EPA Tribal Air are already in `program_inventory.json` and `policy_tracking.json`
- IRS Elective Pay already shows CI: 0.55, AT_RISK
- DOT PROTECT already shows CI: 0.93, SECURE
- 6 new barriers from Strategic Framework are already in `graph_schema.json`
- 10 new authorities from Strategic Framework are already in `graph_schema.json`
- Five Structural Asks data is already in `graph_schema.json`
- Reconciliation/repeal keywords already in IRS Elective Pay's `scanner_trigger_keywords`

## Critical Discovery: Much Data Already Aligned

**HIGH confidence finding from reading the actual files:**

Comparing the Strategic Framework requirements against actual file contents reveals that significant data alignment work was already completed during the project setup phase (before Phase 1). Specifically:

1. **DATA-05 (BIA TCR Awards + EPA Tribal Air):** Both programs already exist in `program_inventory.json` (entries at positions 15-16) and `policy_tracking.json` (entries at positions 2 and 7). Their CI scores, statuses, authorities, and structural ask references are present.

2. **DATA-03 (IRS reclassification + DOT reclassification):** IRS Elective Pay already shows `confidence_index: 0.55`, `ci_status: "AT_RISK"`. DOT PROTECT already shows `confidence_index: 0.93`, `ci_status: "SECURE"`.

3. **DATA-02 (SECURE, UNCERTAIN status categories):** Already present in `policy_tracking.json` `ci_thresholds` and `status_definitions`. TERMINATED is NOT yet present.

4. **DATA-01 (All 16 programs have CI scores):** All 16 programs in `program_inventory.json` have `confidence_index` and `ci_status` values. No gaps.

5. **GRAPH-03 + GRAPH-04 (Authorities and barriers):** The 10 authorities and 6 barriers from the Strategic Framework are already in `graph_schema.json`.

6. **DATA-04 (Reconciliation keywords):** `scanner_trigger_keywords` are on IRS Elective Pay in both inventory and policy tracking. The broader reconciliation terms ("budget reconciliation", "reconciliation bill", "revenue offsets") are NOT yet in `scanner_config.json` `action_keywords` or `search_queries`.

**What is NOT done (the actual Phase 2 work):**

| Requirement | Status | What Remains |
|-------------|--------|-------------|
| DATA-02 (TERMINATED status) | Partial | Add TERMINATED tier to thresholds + definitions |
| DATA-04 (broad reconciliation keywords) | Partial | Add broad terms to `scanner_config.json` action_keywords + search_queries |
| DATA-05 (CFDA in grants_gov.py) | Partial | Add BIA TCR Awards CFDA 15.124 to `grants_gov.py` CFDA_NUMBERS |
| GRAPH-01 (Structural Asks loaded) | NOT DONE | Builder does not process `structural_asks` from schema |
| GRAPH-02 (ADVANCES edges) | NOT DONE | No code creates ADVANCES edges |
| GRAPH-05 (Trust Super-Node) | NOT DONE | No trust_super_node in schema JSON, no TrustSuperNode class, no builder code |
| Verification | NOT DONE | Need tests/validation that all data is consistent across files |

## Open Questions

1. **TERMINATED threshold semantics**
   - What we know: 6 status tiers exist with clear floor values. TERMINATED needs to be added as 7th.
   - What's unclear: Should TERMINATED share floor 0.0 with FLAGGED, or should FLAGGED be raised (e.g., to 0.10) to make room? Currently only FEMA BRIC (CI: 0.12) is FLAGGED.
   - Recommendation: Raise FLAGGED floor to 0.10, add TERMINATED at 0.0. FEMA BRIC stays FLAGGED (0.12 > 0.10). If a program is actually terminated with CI below 0.10, it gets TERMINATED status. This maintains backward compatibility.

2. **ADVANCES edge direction**
   - What we know: Existing edges flow Program -> Target. ADVANCES is semantically different (Ask advances Program).
   - What's unclear: Should edge direction be Ask -> Program (natural language) or Program -> Ask (consistent with other patterns)?
   - Recommendation: Ask -> Program (`source_id=ask_id, target_id=program_id`). This reads naturally: "Multi-Year Funding ADVANCES BIA TCR". The report generator can query "what programs does this ask advance?" by filtering edges where source is the ask.

3. **Report generator impact**
   - What we know: The report generator (`generator.py`) reads `_type` fields and specific edge types to format barriers and authorities sections.
   - What's unclear: Does the report generator need updates in Phase 2, or is that Phase 4 work?
   - Recommendation: Phase 2 focuses on data and graph changes. The report generator will continue to work (it gracefully handles unknown node types via `_type` filtering). Report enhancements (Five Structural Asks section, Trust Responsibility section) belong in Phase 4. However, verify the report does not crash with new node/edge types.

4. **Structural asks as AdvocacyLeverNode vs new type**
   - What we know: The schema has `AdvocacyLeverNode` for per-program levers. Structural asks are cross-cutting.
   - What's unclear: Should structural asks use `AdvocacyLeverNode` (reusing existing type) or a new `StructuralAskNode` type?
   - Recommendation: Reuse `AdvocacyLeverNode`. The existing class has all needed fields (`id`, `description`, `target`, `urgency`). The structural asks data already fits this shape. The `_type` will be "AdvocacyLeverNode" in serialization, which is fine -- the `id` prefix `ask_` distinguishes them from per-program `lever_` nodes. If the report generator needs to distinguish them, it can filter by ID prefix.

## Sources

### Primary (HIGH confidence)
- `F:\tcr-policy-scanner\data\program_inventory.json` -- read in full, 16 programs verified
- `F:\tcr-policy-scanner\data\policy_tracking.json` -- read in full, 16 positions verified
- `F:\tcr-policy-scanner\data\graph_schema.json` -- read in full, 19 authorities, 13 barriers, 5 structural asks, 8 funding vehicles
- `F:\tcr-policy-scanner\config\scanner_config.json` -- read in full, 4 sources, scoring config, keyword lists
- `F:\tcr-policy-scanner\src\graph\builder.py` -- read in full, 349 lines, GraphBuilder class analyzed
- `F:\tcr-policy-scanner\src\graph\schema.py` -- read in full, 110 lines, 6 node types + Edge class
- `F:\tcr-policy-scanner\src\reports\generator.py` -- read in full, 288 lines, report generation analyzed
- `F:\tcr-policy-scanner\src\main.py` -- read in full, 240 lines, pipeline flow traced
- `F:\tcr-policy-scanner\src\analysis\relevance.py` -- read in full, 171 lines, scoring logic analyzed
- `F:\tcr-policy-scanner\src\analysis\change_detector.py` -- read in full, 91 lines
- `F:\tcr-policy-scanner\src\scrapers\grants_gov.py` -- read in full, CFDA_NUMBERS dict analyzed
- `F:\tcr-policy-scanner\docs\STRATEGIC-FRAMEWORK.md` -- read in full, all requirements mapped
- `F:\tcr-policy-scanner\.planning\phases\02-data-model-graph\02-CONTEXT.md` -- read in full, decisions parsed

## Metadata

**Confidence breakdown:**
- Data file structures: HIGH -- read all 4 JSON files directly, schemas are clear
- Graph builder patterns: HIGH -- read full source code, patterns are explicit and consistent
- Downstream dependencies: HIGH -- read all consuming modules, identified exact fields/types used
- What remains to do: HIGH -- compared Strategic Framework against actual file contents line by line
- Open questions: MEDIUM -- recommendations are informed but involve design decisions left to Claude's discretion

**Research date:** 2026-02-09
**Valid until:** 2026-03-09 (stable codebase, no external dependency changes expected)
