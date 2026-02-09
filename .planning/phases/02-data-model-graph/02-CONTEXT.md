# Phase 2: Data Model and Graph Enhancements - Context

**Gathered:** 2026-02-09
**Status:** Ready for planning

<project>
## Project Reference

**Project:** TCR Policy Scanner (Tribal Climate Resilience)
**Repo:** github.com/atniclimate/TCR-policy-scanner (private)
**Local workspace:** `F:\tcr-policy-scanner`
**Planning root:** `F:\tcr-policy-scanner\.planning\`

**Key data files (all relative to project root):**
- `config/scanner_config.json` — sources, scoring weights, 28 Tribal keywords, 30 action keywords
- `data/program_inventory.json` — 16 programs with CI, advocacy levers, tightened language
- `data/policy_tracking.json` — FY26 positions with 6-tier CI thresholds
- `data/graph_schema.json` — 21 authorities, 14 barriers, 8 funding vehicles, Five Structural Asks

**Strategic reference:** `docs/STRATEGIC-FRAMEWORK.md` — 15-item implementation checklist bridging scanner to Hot Sheets

**Stack:** Python 3.12, aiohttp, python-dateutil, jinja2 — all async
**Pipeline:** Ingest (4 async scrapers) -> Normalize -> Graph Construction -> Analysis -> Reporting

**IMPORTANT:** This is NOT the WSDOT project at `F:\`. All file operations must target `F:\tcr-policy-scanner\`.

</project>

<domain>
## Phase Boundary

Enrich the knowledge graph and program inventory to reflect the full Strategic Framework. This includes: adding 2 new programs to the inventory, reconciling all CI scores and statuses to align with Hot Sheets positions, modeling Five Structural Asks as graph nodes with ADVANCES edges, expanding statutory authorities and barriers, and adding the Trust Super-Node. The pipeline (Phase 1) is verified working; this phase modifies the data it consumes. Monitoring, decision logic, and report output belong to Phases 3-4.

</domain>

<decisions>
## Implementation Decisions

### CI scores and status alignment
- CI values for IRS Elective Pay (0.55 AT_RISK) and DOT PROTECT (0.93 SECURE) are specified in requirements but Claude has discretion on whether to hardcode from the Strategic Framework or derive via formula
- TERMINATED added as a 7th status tier — distinct from FLAGGED or AT_RISK, represents actively terminated programs
- Full reconciliation across all 16 programs (not just the 2 explicitly called out) — every program's CI score and status aligned to the Strategic Framework
- Reconciliation/repeal trigger keywords scoped broadly — cover general reconciliation language ("budget reconciliation", "reconciliation bill", "revenue offsets") in addition to IRA section 6417-specific terms

### Claude's Discretion
- Whether CI values are hardcoded from Strategic Framework or derived from a formula (user said "you decide")
- Exact threshold boundaries between the 7 status tiers in policy_tracking.json
- New program metadata structure for BIA TCR Awards and EPA Tribal Air Quality (CI scores, advocacy levers, funding vehicles, linked authorities)
- Five Structural Asks graph modeling — how ADVANCES edges connect Asks to programs, cardinality, barrier mitigation pathways
- Trust Super-Node (FEDERAL_TRUST_RESPONSIBILITY) design — what it connects to, TRUST_OBLIGATION edge semantics
- How to structure the 10 new statutory authorities and 6 new barriers from the Strategic Framework

</decisions>

<specifics>
## Specific Ideas

No specific requirements beyond what the Strategic Framework document provides — open to standard approaches informed by the existing codebase patterns.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-data-model-graph*
*Context gathered: 2026-02-09*
