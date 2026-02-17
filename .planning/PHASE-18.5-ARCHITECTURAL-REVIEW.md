# Phase 18.5: Architectural Review and Scaffolding
## TCR Policy Scanner v1.4 Pre-Phase

**Prepared:** 2026-02-17
**Classification:** T0 (Open)
**Position:** Before Phase 19 (Schema and Core Data Foundation), after v1.3 closeout
**Duration:** 1 session (agent team, parallel execution)
**Depends on:** v1.3 Production Launch COMPLETE, .planning/ documentation harmonized

---

## Purpose

Phase 18.5 is an architectural review conducted by the Research Team agent ecosystem before any v1.4 code is written. The team uses MCP servers for GitHub (live codebase inspection) and Context7 (library documentation and best practices lookup) to ground-truth the proposed architecture against what actually exists, what the most current tooling can do, and whether the 6-phase plan (Phases 19 through 24) is structured to produce the clearest, most usable intelligence for Tribal Leaders.

This is not a planning phase. It is a reckoning phase. The agents look backward over 18 phases of construction, forward through 6 phases of proposed expansion, and ask: does this serve the people it is meant to serve? Is the story clear? Is the pipeline honest about what it knows and what it does not? Are we using the best available techniques to harmonize federal datasets into information that Tribal Leaders can act on, not just data that technicians can read?

---

## Why This Phase Exists

v1.3 shipped 992 documents across 592 Tribal Nations. It works. But v1.4 adds three entirely new data domains (CDC SVI, USGS LOCA2 climate projections, expanded FEMA NRI) and introduces a composite vulnerability score that synthesizes them. That is a fundamentally different kind of output: not "here is what federal programs exist" but "here is how vulnerable your community is and why." The stakes of getting that wrong, of presenting it too technically, of losing critical nuance in the harmonization, of framing it in ways that diminish rather than strengthen sovereignty, are higher than anything in v1.3.

The agents review the architecture before Phase 19 begins so that scaffolding decisions, schema designs, narrative framing choices, and library selections are made with full awareness of:

1. How the existing codebase actually works (not how the docs say it works)
2. What the most current versions of key libraries support
3. Where the proposed architecture makes assumptions that need validation
4. How the output documents will read to a Tribal Leader who is not a data scientist
5. Whether critical information gets lost in the harmonization pipeline

---

## MCP Server Requirements

### GitHub MCP (Required)

The GitHub MCP server provides live read access to `atniclimate/TCR-policy-scanner`. Agents use this to inspect the actual codebase state rather than relying on architecture documents that may have drifted from implementation.

**Key inspection targets:**

- `src/packets/hazards.py` lines 360-577: Current NRI field extraction and area-weighting logic (the pattern all v1.4 data sources must follow)
- `src/packets/orchestrator.py` lines 305-400: `_load_tribe_cache()` and `_build_context()` (the integration seam for vulnerability data)
- `src/packets/context.py`: TribePacketContext dataclass (the contract between data pipeline and document renderer)
- `src/packets/docx_sections.py`: Current section renderer signatures (the pattern vulnerability renderers must follow)
- `src/packets/doc_types.py`: DocumentTypeConfig frozen dataclass (constraints on Doc E definition)
- `src/paths.py`: 35 path constants (naming conventions and organization patterns)
- `data/hazard_profiles/epa_100000001.json`: Actual hazard profile schema (ground truth vs architecture doc)
- `tests/`: Test patterns and coverage expectations (what the bar is for v1.4 tests)
- `.planning/STATE.md`: Current project state and decision inventory

### Context7 MCP (Required)

Context7 provides documentation lookup for libraries and frameworks. Agents use this to verify that the proposed architecture uses the most current and capable versions of key dependencies.

**Key documentation targets:**

- **Pydantic v2**: Schema definition patterns, validators, model inheritance (for `src/schemas/vulnerability.py`)
- **xarray**: NetCDF reading, coordinate selection, multi-file datasets, lazy loading (for LOCA2 climate data extraction)
- **netCDF4**: Low-level NetCDF access as xarray backend (format compatibility, chunking)
- **geopandas**: Current overlay and spatial join capabilities (verify crosswalk approach is still optimal)
- **python-docx**: Table rendering, style management, conditional formatting (for vulnerability section rendering)
- **Chart.js**: Radar charts, bar charts, responsive config (for website vulnerability visualizations)
- **Fuse.js**: Search index structure (impact of adding vulnerability fields to tribes.json)

---

## Agent Assignments

### Sovereignty Scout: Data Source Validation

**Mission:** Verify that every proposed data source is accessible, current, and structured as the architecture assumes.

**Tasks:**

1. **NRI CSV field audit**: Use GitHub MCP to read the actual `_load_nri_county_data()` implementation. Confirm which fields are already extracted. Cross-reference with the architecture document's list of "NOT yet captured" fields. Verify that `EAL_VALB`, `EAL_VALP`, `EAL_VALA`, `RISK_NPCTL`, `POPULATION`, `BUILDVALUE` exist in the current NRI CSV by checking the download script.

2. **CDC SVI endpoint validation**: Verify the SVI 2022 download URL at svi.cdc.gov is still active. Check whether SVI 2024 (based on 2020-2024 ACS) has been released, which would supersede 2022 data. Confirm the CSV column names match what the architecture assumes (`FIPS`, `RPL_THEMES`, `RPL_THEME1` through `RPL_THEME4`).

3. **USGS LOCA2 format verification**: Examine the ScienceBase catalog entry for CMIP6-LOCA2 county summaries. Confirm NetCDF availability, GEOID keying, variable names. Check for any pre-processed CSV or JSON alternatives that would eliminate the xarray/netCDF4 dependency entirely. Research whether USGS has released county-level summary CSVs since the architecture was written.

4. **Alaska coverage gap assessment**: Quantify exactly how many of the 592 tracked Tribal Nations are in Alaska. Identify which LOCA2 alternatives exist for Alaska boroughs (e.g., SNAP climate data from UAF, NOAA Arctic climate projections). Recommend a concrete fallback strategy rather than "accept partial coverage."

5. **FEMA FRI status check**: Confirm the Future Risk Index remains removed from FEMA's website. Check whether any restored or replacement dataset has appeared. Validate the architecture's decision to derive future risk signals from LOCA2 instead.

**Deliverable:** Data source validation report with status (CONFIRMED/CHANGED/UNAVAILABLE) for each source, plus specific corrections to the architecture document where reality diverges from assumptions.

---

### Fire Keeper: Codebase Pattern Analysis

**Mission:** Read the living codebase and identify the exact patterns that v1.4 must follow, plus any technical debt that should be resolved before new code is layered on top.

**Tasks:**

1. **Pattern extraction via GitHub MCP**: Read `HazardProfileBuilder` end to end. Document the exact sequence: CSV load, field extraction, county-to-Tribe crosswalk, area weighting, atomic JSON write. This is the template `VulnerabilityProfileBuilder` must replicate. Note any undocumented quirks (e.g., handling of -999 sentinel values, NaN propagation, weight normalization edge cases).

2. **Context dataclass expansion analysis**: Read `TribePacketContext` and identify all existing dict-typed fields. Check whether adding `vulnerability_profile: dict` creates any naming collisions, serialization issues, or memory concerns for the 592-Tribe batch run.

3. **Renderer pattern catalog**: Read every function in `docx_sections.py`. Catalog the exact function signatures, parameter patterns, style manager usage, and conditional rendering logic. Create a specification sheet that `docx_vulnerability_sections.py` must conform to.

4. **Technical debt inventory**: Use GitHub MCP to grep for any remaining instances of the four v1.3 fixes (hardcoded loggers, FY literals, format_dollars duplication, graph_schema paths). Report whether these are fully resolved or whether v1.4 would inherit drift.

5. **Library version audit via Context7**: Look up current stable versions of Pydantic, xarray, netCDF4, python-docx. Compare against what is in `requirements.txt`. Identify any breaking changes between current and proposed versions. Flag if Pydantic v2 migration patterns apply (v1 to v2 migration is a known pain point).

6. **Dependency isolation review**: Evaluate the architecture's suggestion to make xarray/netCDF4 optional (`pip install tcr-policy-scanner[climate]`). Use Context7 to check setuptools/pyproject.toml patterns for optional dependency groups. Confirm this does not break the GitHub Actions pipeline.

**Deliverable:** Pattern conformance specification for v1.4 code, technical debt report, dependency compatibility matrix.

---

### River Runner: Schema and Validation Architecture

**Mission:** Design the Pydantic schema architecture for vulnerability profiles before Phase 19 implements them, ensuring type safety, validation rules, and the composite score formula are formally specified.

**Tasks:**

1. **Existing schema audit via GitHub MCP**: Check whether `src/schemas/` already exists. If so, read all existing Pydantic models and understand the validation patterns in use. If not, identify where data validation currently happens (inline checks, assert statements, try/except blocks) and catalog what Phase 19's schema migration must cover.

2. **Vulnerability profile schema draft**: Using the architecture document's `TribePacketContext.vulnerability_profile` example structure, draft the full Pydantic model hierarchy:
   - `SVIProfile` (overall + 4 theme rankings, source version)
   - `ClimateProjectionProfile` (scenario, period, baseline, 7+ metrics)
   - `NRIExpandedProfile` (EAL components, national percentile, demographics)
   - `CompositeVulnerability` (score, rating, 4 component weights)
   - `VulnerabilityProfile` (composing all of the above + metadata)

3. **Composite score formula validation**: Examine the proposed weighted average (0.30 hazard + 0.25 social + 0.25 climate + 0.20 adaptive capacity deficit). Test edge cases: What happens when a Tribe has no LOCA2 coverage (Alaska)? When SVI data is missing for a county? When NRI reports -999 for a field? Define explicit handling for partial data, including whether the composite score should be computed at all when major components are missing.

4. **Coverage reporting specification**: Define what the `vulnerability_coverage_report.json` must contain. Per-Tribe: which components have data, which are missing, what percentage of the composite is based on actual data vs imputed/default values. Aggregate: how many of 592 Tribes have full coverage, partial, none. This report becomes the honesty layer, the truth about what the data can and cannot tell us.

5. **Test architecture**: Propose the test structure for Phase 19 through 24. How many tests should each phase add? What fixtures are needed (sample NRI CSV rows, sample SVI records, synthetic climate projections)? What integration tests validate the full pipeline? Estimate the test count target for v1.4 completion (v1.3 ended at 964).

**Deliverable:** Draft Pydantic schema models, composite score edge case matrix, coverage report specification, test architecture proposal.

---

### Horizon Walker: Narrative and Framing Review

**Mission:** Ensure that the v1.4 output documents tell a clear, actionable story for Tribal Leaders, not a technical report for data scientists. Review every point where data becomes narrative and ask: does this serve advocacy?

**Tasks:**

1. **Document audience analysis**: Review the existing Doc A (internal strategy) and Doc B (congressional briefing) via GitHub MCP. Understand the current narrative voice, reading level, information density, and advocacy framing. Assess whether the proposed vulnerability sections match that voice or risk creating a jarring tonal shift.

2. **Vulnerability framing review**: The architecture proposes a composite vulnerability score with ratings from "Very Low" to "Very High." Evaluate this framing through a sovereignty lens:
   - Does labeling a Tribal Nation as "Very High" vulnerability risk reinforcing deficit narratives?
   - Should the framing be reoriented toward resilience capacity and investment need rather than vulnerability ranking?
   - How does the caveat language ("based on available federal datasets") actually read in a document? Is it buried in a footnote or integrated into the narrative flow?
   - Propose alternative framing options that honor both data transparency and sovereignty.

3. **Narrative format inventory**: The architecture produces four document types (Doc A internal, Doc B congressional, Doc C/D regional, Doc E standalone vulnerability). For each, outline:
   - What story does the vulnerability data tell in this context?
   - What is the reader's decision point? (Internal strategy vs congressional ask vs regional coordination)
   - What level of technical detail serves that decision?
   - What must be simplified, and what must be preserved at full fidelity?

4. **Information loss analysis**: Trace a single data point through the entire pipeline. For example: CDC SVI Theme 3 (Racial and Ethnic Minority Status) RPL_THEME3 = 0.81 for County X. Follow it through area-weighting, composite scoring, section rendering, and final document text. At each stage, ask: what context is preserved? What is lost? Does the Tribal Leader reading the final document understand what 0.81 means for their community, or is it an opaque number?

5. **Multiple narrative format readiness**: Evaluate whether the architecture supports future output formats beyond DOCX: presentation slides for Tribal Council meetings, one-page fact sheets for congressional visits, dashboard views for ongoing monitoring. Identify any schema or pipeline design decisions in Phases 19 through 24 that would make or break these future formats.

6. **Visualization specification for website**: The architecture proposes Chart.js for vulnerability visualization. Draft specifications for what charts would most effectively communicate vulnerability data to non-technical audiences: radar charts for multi-dimensional profiles? Bar charts for comparison? Color-coded summary badges? Reference best practices in public health data communication.

**Deliverable:** Narrative framing recommendations with specific language proposals, information loss audit, multi-format readiness assessment, visualization specifications.

---

## Orchestrator Coordination Protocol

The team lead coordinates the four agents in a single session:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Phase 18.5 Execution Flow                     │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │ Sovereignty Scout │  │   Fire Keeper    │                     │
│  │ Data Source       │  │ Codebase Pattern │  PARALLEL           │
│  │ Validation        │  │ Analysis         │  (MCP-intensive)    │
│  └────────┬─────────┘  └────────┬─────────┘                     │
│           │                      │                               │
│  ┌────────┴─────────┐  ┌────────┴─────────┐                     │
│  │  River Runner     │  │  Horizon Walker  │                     │
│  │  Schema Design    │  │  Narrative Review│  PARALLEL           │
│  │  (needs FK output)│  │  (needs SS data) │  (depends on above) │
│  └────────┬─────────┘  └────────┬─────────┘                     │
│           │                      │                               │
│           └──────────┬───────────┘                               │
│                      │                                           │
│           ┌──────────┴───────────┐                               │
│           │   SYNTHESIS REPORT   │                               │
│           │  Architecture Delta  │                               │
│           │  Go/Revise Decision  │                               │
│           └──────────────────────┘                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Wave 1 (Parallel):** Sovereignty Scout and Fire Keeper execute simultaneously. Both are primarily read operations against GitHub MCP and Context7. No file ownership conflicts.

**Wave 2 (Parallel, dependent):** River Runner needs Fire Keeper's pattern analysis to design conformant schemas. Horizon Walker needs Sovereignty Scout's data validation to assess what information is actually available for narrative. Both execute in parallel once Wave 1 deliverables are shared.

**Synthesis:** The orchestrator compiles all four deliverables into a single Architecture Delta Report that identifies every place where the proposed v1.4 architecture (ARCHITECTURE.md) needs revision before Phase 19 begins.

---

## Success Criteria

Phase 18.5 is complete when:

1. Every data source in the architecture has a verified status (CONFIRMED/CHANGED/UNAVAILABLE) with evidence from live endpoint checks
2. The codebase pattern specification exists, grounded in actual code inspection via GitHub MCP, not architecture assumptions
3. Draft Pydantic schemas for vulnerability profiles are written with explicit edge case handling for missing data
4. The composite vulnerability score has been evaluated through a sovereignty lens with alternative framing options proposed
5. An information loss audit traces at least one data point from source to rendered document and identifies preservation/loss at each stage
6. The Architecture Delta Report identifies all changes needed to ARCHITECTURE.md before Phase 19 execution
7. A GO/REVISE decision is made: either the 6-phase plan proceeds as designed, or specific modifications are documented

---

## Architecture Delta Report Template

The synthesis output follows this structure:

```
ARCHITECTURE DELTA REPORT
Phase 18.5 | TCR Policy Scanner v1.4

SECTION 1: DATA SOURCE STATUS
  [source]: [CONFIRMED|CHANGED|UNAVAILABLE]
  [specific findings and corrections]

SECTION 2: CODEBASE PATTERN CONFORMANCE
  [pattern]: [MATCHES|DRIFT|NEEDS UPDATE]
  [specific code references and line numbers]

SECTION 3: SCHEMA RECOMMENDATIONS
  [model]: [APPROVED|NEEDS REVISION]
  [edge cases identified and handling proposed]

SECTION 4: NARRATIVE FRAMING DECISIONS
  [decision point]: [RECOMMENDATION]
  [sovereignty implications and alternative options]

SECTION 5: PHASE 19-24 MODIFICATIONS
  [phase]: [NO CHANGE|MODIFY]
  [specific changes to phase requirements or success criteria]

SECTION 6: GO/REVISE DECISION
  [GO]: Architecture confirmed, proceed to Phase 19
  [REVISE]: Specific changes required before Phase 19
```

---

## Trigger Prompt

> Paste this into Claude Code to launch the Phase 18.5 review.

```
I need you to lead the TCR Policy Scanner Research Team through Phase 18.5:
Architectural Review and Scaffolding for the v1.4 Vulnerability Data milestone.

## Context

v1.3 is COMPLETE (18 phases, 964 tests, 992 documents for 592 Tribal Nations).
v1.4 adds climate vulnerability intelligence: CDC SVI social vulnerability,
USGS LOCA2 climate projections, expanded FEMA NRI metrics, and a composite
vulnerability score. This data becomes advocacy ammunition for Tribal Leaders.

The proposed architecture is in .planning/ARCHITECTURE.md. The 6-phase build
plan covers Phases 19-24. BEFORE any code is written, the Research Team reviews
the architecture against the actual codebase and current data sources.

Read CLAUDE.md and .claude/agents/ before proceeding.

## MCP Servers Required

- GitHub MCP: live inspection of atniclimate/TCR-policy-scanner
- Context7 MCP: library documentation lookup (Pydantic, xarray, python-docx,
  Chart.js, geopandas, netCDF4, Fuse.js)

## Agent Assignments

### Sovereignty Scout (sovereignty-scout)
Spawn: "You are Sovereignty Scout. Read .claude/agents/sovereignty-scout.md.
Your Phase 18.5 mission: validate every v1.4 data source. Use GitHub MCP to
inspect download scripts and data schemas. Check CDC SVI endpoint status (has
SVI 2024 dropped?). Verify USGS LOCA2 NetCDF format and availability. Quantify
Alaska coverage gap with exact Tribe count. Confirm FEMA FRI remains archived.
Deliver a data source validation report with CONFIRMED/CHANGED/UNAVAILABLE for
each source. Frame findings in terms of what they mean for Tribal advocacy."

### Fire Keeper (fire-keeper)
Spawn: "You are Fire Keeper. Read .claude/agents/fire-keeper.md. Your Phase
18.5 mission: read the living codebase via GitHub MCP and extract the exact
patterns v1.4 must follow. Document HazardProfileBuilder end-to-end as the
template for VulnerabilityProfileBuilder. Catalog docx_sections.py renderer
signatures. Audit requirements.txt versions against current stable releases
using Context7. Check for residual technical debt from the four v1.3 fixes.
Deliver a pattern conformance specification and dependency compatibility matrix."

### River Runner (river-runner)
Spawn: "You are River Runner. Read .claude/agents/river-runner.md. Your Phase
18.5 mission: design the Pydantic schema architecture for vulnerability profiles
BEFORE Phase 19 implements them. Use Fire Keeper's pattern analysis to ensure
conformance. Draft SVIProfile, ClimateProjectionProfile, NRIExpandedProfile,
CompositeVulnerability, and VulnerabilityProfile models. Test composite score
edge cases: missing LOCA2 (Alaska), missing SVI, NRI sentinel values. Define
the coverage report specification. Propose the test architecture for Phases
19-24. Deliver draft schemas, edge case matrix, and test plan."

### Horizon Walker (horizon-walker)
Spawn: "You are Horizon Walker. Read .claude/agents/horizon-walker.md. Your
Phase 18.5 mission: ensure v1.4 tells a clear story, not a technical report.
Review existing Doc A/B narrative voice via GitHub MCP. Evaluate 'Very High
vulnerability' framing through a sovereignty lens: does it reinforce deficit
narratives? Propose alternative framings. Trace one data point (SVI Theme 3
RPL_THEME3=0.81) from source through pipeline to rendered document and audit
information loss at each stage. Assess multi-format readiness (slides, fact
sheets, dashboards). Draft visualization specs for Chart.js on the website.
Deliver narrative framing recommendations and information loss audit."

## Coordination

Wave 1: Sovereignty Scout + Fire Keeper run in parallel (read-intensive)
Wave 2: River Runner + Horizon Walker run in parallel (dependent on Wave 1)
Synthesis: Compile all findings into an Architecture Delta Report

## Success Criteria

The review succeeds when:
- Every data source has a verified status with evidence
- Codebase patterns are documented from actual code, not architecture assumptions
- Draft Pydantic schemas exist with edge case handling
- Vulnerability framing has been evaluated through a sovereignty lens
- At least one data point has been traced source-to-document for information loss
- An Architecture Delta Report identifies all changes needed before Phase 19
- A GO/REVISE decision is made

Every finding must answer: does this serve the Tribal Leaders who will read
these documents? Sovereignty is the innovation. Relatives, not resources.

Begin by reading CLAUDE.md and agent definitions, then create the team.
```

---

## Relationship to Phase 19-24 Plan

Phase 18.5 does not add requirements or change the scope of Phases 19 through 24. It produces an Architecture Delta Report that may modify HOW those phases execute, not WHAT they deliver. The 6-phase plan remains:

| Phase | Goal | Relationship to 18.5 |
|-------|------|----------------------|
| 19 | Schema and Core Data Foundation | 18.5 delivers draft schemas and pattern specs that 19 implements |
| 20 | Flood and Water Data | 18.5 validates data source accessibility and format assumptions |
| 21 | Climate, Geologic, and Infrastructure | 18.5 validates LOCA2 format and Alaska gap strategy |
| 22 | Vulnerability Profiles and Pipeline | 18.5 delivers composite score edge case handling and framing decisions |
| 23 | Document Rendering | 18.5 delivers narrative framing recommendations and renderer pattern catalog |
| 24 | Website and Delivery | 18.5 delivers visualization specifications and search index impact assessment |

The Architecture Delta Report becomes a companion document to ARCHITECTURE.md. Where the architecture describes the design, the delta describes the ground truth. Together they give Phase 19 a foundation of verified assumptions rather than hopeful ones.

---

## Values Alignment

This phase exists because the data in v1.4 carries weight that v1.3 did not. When a document says a Tribal Nation has "Very High" climate vulnerability, that statement enters the advocacy record. It gets cited in grant applications, referenced in congressional testimony, used in government-to-government consultation. If the underlying data harmonization lost critical context, if the composite score obscured more than it revealed, if the framing diminished rather than strengthened the Tribal Leader's position, the tool has failed regardless of how elegant the code is.

Phase 18.5 is the moment where the team pauses, looks at what they are about to build, and asks: will this actually help? Not in the abstract. For the specific Tribal Leader sitting across from a congressional staffer, holding a document that says their community faces escalating climate risk. Will the data be clear? Will the framing be honest? Will the story be one they can tell with confidence?

That is the question this phase answers.

Honor, Pride, and Respect.
Sovereignty is the innovation.
Relatives, not resources.

---

*Prepared: 2026-02-17*
*For: TCR Policy Scanner v1.4 Vulnerability Data Milestone*
*Scope: Architectural review, scaffolding verification, narrative framing*
*Position: Phase 18.5 (between v1.3 closeout and Phase 19)*
