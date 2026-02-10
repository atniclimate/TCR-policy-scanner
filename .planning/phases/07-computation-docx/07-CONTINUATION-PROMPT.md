# Phase 7 Continuation Prompt

Copy everything below the `---` line into a fresh `/clear` context window.

---

## Project Anchor (READ THIS FIRST)

**Project:** TCR Policy Scanner v1.1 — Tribe-Specific Advocacy Packets
**Path:** `F:\tcr-policy-scanner` (NOT F:\ root — that's WSDOT)
**Planning:** `F:\tcr-policy-scanner\.planning`
**Phase:** 7 of 8 — Computation + DOCX Generation
**Context:** `F:\tcr-policy-scanner\.planning\phases\07-computation-docx\07-CONTEXT.md`

Before running any GSD command, `cd F:\tcr-policy-scanner` and verify `.planning/ROADMAP.md` mentions "Tribe-Specific Advocacy Packets" — if it says "WSDOT Agent Ecosystem", you loaded the wrong project.

## What to do

```
/gsd:plan-phase 7
```

Plan Phase 7: Computation + DOCX Generation for the TCR Policy Scanner at `F:\tcr-policy-scanner\.planning`.

## Pre-loaded Research Context

Phase 7 delivers 5 requirements: ECON-01 (economic impact calculator), DOC-01 (DOCX engine), DOC-02 (Hot Sheet renderer), DOC-03 (advocacy language assembly), DOC-04 (structural asks integration).

### Codebase Architecture (verified 2026-02-10)

**Entry point:** `src/main.py` — `--prep-packets --tribe <name>` or `--all-tribes`
**Orchestrator:** `src/packets/orchestrator.py` — `PacketOrchestrator` class with `run_single_tribe()`, `run_all_tribes()`, `_build_context()` methods
**Context dataclass:** `src/packets/context.py` — `TribePacketContext` with fields: tribe_id, tribe_name, states, ecoregions, bia_code, epa_id, districts, senators, representatives, awards, hazard_profile, economic_impact (stub), generated_at, congress_session

**Phase 5-6 modules (data inputs — DO NOT MODIFY):**
- `src/packets/registry.py` — `TribalRegistry` (592 Tribes, 3-tier name resolution)
- `src/packets/ecoregion.py` — `EcoregionMapper` (7 NCA5 ecoregions, `get_priority_programs()`)
- `src/packets/congress.py` — `CongressionalMapper` (119th Congress, districts/senators/reps/committees)
- `src/packets/awards.py` — `TribalAwardMatcher` (per-Tribe award cache in `data/award_cache/{tribe_id}.json`)
- `src/packets/hazards.py` — `HazardProfileBuilder` (per-Tribe hazard cache in `data/hazard_profiles/{tribe_id}.json`)

**v1.0 modules (decision engine + graph — READ ONLY for Phase 7):**
- `src/analysis/decision_engine.py` — `DecisionEngine` with 5 advocacy goals (LOGIC-01..05), `classify_all(graph_data, alerts)`
- `src/graph/builder.py` — `KnowledgeGraph` with program/authority/barrier/lever nodes
- `src/monitors/hot_sheets.py` — CI status overrides from external hot sheets data
- `src/reports/generator.py` — existing Markdown report generator (reference for patterns)

### Key Data Schemas (actual field names)

**program_inventory.json** (16 programs):
```
programs[].id, .name, .agency, .ci_status, .confidence_index,
.tightened_language, .advocacy_lever, .access_type, .funding_type,
.cfda, .hot_sheets_status.status, .specialist_focus, .proposed_fix
```

**graph_schema.json** (structural asks — DOC-04):
```
structural_asks[].id, .name, .description, .target, .urgency, .mitigates[], .programs[]
barriers[].id, .description, .type, .severity, .programs[], .mitigated_by[]
authorities[].id, .citation, .type, .durability, .programs[]
```

**award_cache/{tribe_id}.json**:
```
.tribe_id, .tribe_name, .awards[], .total_obligation, .award_count,
.cfda_summary.{cfda}.count/.total, .no_awards_context (zero-award Tribes)
```

**hazard_profiles/{tribe_id}.json**:
```
.sources.fema_nri.composite.risk_score/.risk_rating/.eal_total/.sovi_score
.sources.fema_nri.top_hazards[] (ranked by risk_score)
.sources.fema_nri.all_hazards.{WFIR,IFLD,DRGT,...}.risk_score/.eal_total
.sources.usfs_wildfire.risk_to_homes/.wildfire_likelihood
```

**congressional_cache.json** (per tribe_id):
```
.districts[].state/.district/.overlap_pct
.senators[].name/.party/.state/.committees[]
.representatives[].name/.party/.district/.committees[]
```

**ecoregion_config.json**:
```
.ecoregions.{region}.name/.states[]/.priority_programs[]
```

### Implementation Decisions (from 07-CONTEXT.md)

**Hot Sheets:**
- 1-page target, overflow OK; fixed section order, hide empty
- Traffic light CI status (red/yellow/green) + text label via Word-native formatting + inline shapes
- Only hazard-relevant programs (8-12 per Tribe), omitted programs in appendix with brief paragraphs
- Ordered by priority/risk; prominent 3-line Key Ask callout (ASK/WHY/IMPACT)
- Zero-award Tribes get "First-Time Applicant Advantage" pivot framing

**Economic Impact (ECON-01):**
- Range with citation: "estimated $X-$Y (BEA methodology range: 1.8-2.4x)"
- Job estimates via BLS jobs-per-million-output ratios
- Dual FEMA BCR framing: future savings + ROI language
- Multi-district Tribes: total + per-district breakdown using Census area overlap
- Program average benchmarks; methodology footnote per Hot Sheet

**Document Styling (DOC-01):**
- Professional modern (Brookings/McKinsey style), Arial/Helvetica
- Status-driven palette: At Risk=red, Watch=amber, Stable=green
- Zebra-striped tables, cover page with state/region map
- Style reference created programmatically from scratch

**Advocacy Language (DOC-03 + DOC-04):**
- Direct insertion of `tightened_language` and `advocacy_lever` from program inventory
- Framing shifts by CI status: defensive (At Risk) / protective (Watch) / growth (Stable)
- Committee-match flags when delegation sits on relevant committee
- Office-specific "What You Can Do" action items
- Legislative references from v1.0 pipeline data

### Existing Patterns to Follow

- **Lazy loading:** All Phase 5-6 modules lazy-load data on first access
- **Atomic writes:** tmp file + `os.replace()` for all JSON output (Windows-safe)
- **UTF-8 everywhere:** `encoding="utf-8"` on every `open()` and `Path.write_text()`
- **Per-Tribe caching:** O(1) lookup from `data/{cache_dir}/{tribe_id}.json`
- **Config-driven paths:** All file paths read from `scanner_config.json` packets section
- **Test pattern:** pytest with `tmp_path` fixtures, mock data, no network access
- **Module location:** New modules go in `src/packets/` (not src/ root)

### Expected New Modules (Phase 7)

```
src/packets/economic.py      — EconomicImpactCalculator (ECON-01)
src/packets/docx_styles.py   — StyleManager, programmatic style definitions (DOC-01)
src/packets/docx_hotsheet.py — HotSheetRenderer, per-program section builder (DOC-02)
src/packets/docx_sections.py — Section generators: cover page, appendix (DOC-02 support)
src/packets/docx_engine.py   — DocxEngine, core document construction (DOC-01)
src/packets/relevance.py     — ProgramRelevanceFilter, hazard-to-program mapping (DOC-02)
```

### Stack & Dependencies

- Python 3.12, python-docx >= 1.1.0 (already in requirements.txt)
- pytest for tests, tmp_path fixtures
- No new dependencies expected (python-docx handles DOCX, Pillow for map images if needed)
- 106 tests currently passing — no regressions allowed

## Research Directives for Agents

When `/gsd:plan-phase 7` spawns research agents, they should use these tools:

**Context7:** Resolve `python-docx` library ID and query for:
- Programmatic style creation (heading styles, table styles, paragraph styles)
- Table cell shading and alternating row colors
- Inline shapes / drawing ML for status badges
- Header/footer configuration with section-level control
- Page break insertion and section management
- Image embedding for cover page map

**Ref:** Search for:
- python-docx advanced table formatting patterns
- DOCX style inheritance and style reference documents
- Word-compatible color codes for traffic light status
- BEA economic multiplier methodology and published ranges
- BLS jobs-per-million-output ratios by sector
- FEMA benefit-cost ratio documentation

**Code Review:** After plans are written, validate:
- All file paths reference real existing modules
- Data field names match actual JSON schemas listed above
- No modifications to Phase 5-6 modules (except TribePacketContext.economic_impact)
- Test coverage for each new module
- UTF-8 encoding on all file operations
- Atomic write pattern for any new cache files

## Anti-Patterns to Prevent

1. **DO NOT** load `.planning/ROADMAP.md` from `F:\` — always use `F:\tcr-policy-scanner\.planning/`
2. **DO NOT** modify Phase 5-6 modules (registry, congress, ecoregion, awards, hazards) except to consume their output
3. **DO NOT** add AI-generated advocacy text — use existing `tightened_language` and `advocacy_lever` fields
4. **DO NOT** make API calls during DOCX generation — all data is pre-cached
5. **DO NOT** use `datetime.utcnow()` — use `datetime.now(timezone.utc)` (Python 3.12)
6. **DO NOT** use bare `open()` — always pass `encoding="utf-8"` on Windows
7. **DO NOT** create template .docx files — all styles are programmatic
8. **DO NOT** hardcode the 16-program count — relevance filtering reduces to 8-12 per Tribe
