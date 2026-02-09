# Roadmap: TCR Policy Scanner

**Created:** 2026-02-09
**Depth:** Quick
**Phases:** 4
**Coverage:** 31/31 v1 requirements mapped

## Overview

The TCR Policy Scanner is a brownfield Python project with working scrapers, scoring, graph building, and report generation. This roadmap validates the existing pipeline first, then enriches the data model, adds monitoring and decision logic capabilities, and finally enhances report output to surface all new intelligence. Each phase builds on the previous -- you cannot monitor what you have not modeled, and you cannot report what you have not monitored.

---

## Phase 1: Pipeline Validation

**Goal:** The existing pipeline runs end-to-end against live federal APIs and produces correct output on schedule.

**Dependencies:** None (this is the foundation -- verify before building on top)

**Requirements:** PIPE-01, PIPE-02, PIPE-03, PIPE-04

**Plans:** 2 plans

Plans:
- [x] 01-01-PLAN.md -- Fix Grants.gov endpoint, validate all 4 scrapers, full pipeline run, change detection
- [x] 01-02-PLAN.md -- Verify GitHub Actions CI workflow via manual trigger

**Success Criteria:**

1. Running `python src/main.py` against live APIs produces a LATEST-BRIEFING.md and LATEST-RESULTS.json with real scan data from all 4 sources (Federal Register, Grants.gov, Congress.gov, USASpending)
2. Each scraper handles API errors gracefully -- a single source failure does not crash the pipeline, and partial results are still reported
3. The GitHub Actions daily-scan.yml workflow completes successfully on a manual trigger, producing committed output files
4. Running two consecutive scans with a known change between them produces a change detection summary that correctly identifies the new/modified/removed items

---

## Phase 2: Data Model and Graph Enhancements

**Goal:** The knowledge graph and program inventory reflect the full Strategic Framework -- all programs scored, statuses aligned to Hot Sheets, Five Structural Asks modeled, and expanded authorities/barriers captured.

**Dependencies:** Phase 1 (pipeline must be verified working before modifying the data it consumes)

**Requirements:** DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, GRAPH-01, GRAPH-02, GRAPH-03, GRAPH-04, GRAPH-05

**Plans:** 2 plans

Plans:
- [x] 02-01-PLAN.md -- Add TERMINATED status tier, reconciliation keywords, BIA TCR Awards CFDA
- [x] 02-02-PLAN.md -- Five Structural Asks loading, Trust Super-Node, ADVANCES/TRUST_OBLIGATION edges

**Success Criteria:**

1. Loading program_inventory.json shows 18 programs (16 original + BIA TCR Awards + EPA Tribal Air Quality), each with a CI score and Hot Sheets-aligned status from the 6-tier model (SECURE, STABLE, STABLE_BUT_VULNERABLE, AT_RISK, UNCERTAIN, FLAGGED)
2. Running the graph builder produces a knowledge graph containing Five Structural Asks as AdvocacyLeverNodes with ADVANCES edges connecting them to relevant program nodes
3. The graph contains the Trust Super-Node (FEDERAL_TRUST_RESPONSIBILITY) with TRUST_OBLIGATION edges to BIA and EPA programs
4. Graph schema includes 10 new statutory authorities and 6 new barriers from the Strategic Framework, and scanner_config.json contains reconciliation/repeal trigger keywords
5. IRS Elective Pay shows AT_RISK status (CI: 0.55) and DOT PROTECT shows SECURE status (CI: 0.93) in policy_tracking.json

---

## Phase 3: Monitoring Capabilities and Decision Logic

**Goal:** The scanner detects legislative threats (IIJA sunsets, reconciliation bills, funding cliffs), Tribal consultation signals, and classifies each program into an advocacy goal using 5 decision rules.

**Dependencies:** Phase 2 (monitoring needs the enriched data model; decision logic needs updated statuses and graph edges)

**Requirements:** MON-01, MON-02, MON-03, MON-04, MON-05, LOGIC-01, LOGIC-02, LOGIC-03, LOGIC-04, LOGIC-05

**Plans:** 3 plans

Plans:
- [x] 03-01-PLAN.md -- Monitor framework + threat monitors (IIJA sunset, reconciliation, DHS funding cliff)
- [x] 03-02-PLAN.md -- Advocacy decision engine with 5 classification rules (TDD)
- [x] 03-03-PLAN.md -- Signal monitors (Tribal consultation, Hot Sheets) + pipeline integration

**Success Criteria:**

1. After a scan, any IIJA-funded program approaching FY26 expiration without a detected reauthorization bill is flagged in scan results with a sunset warning and days remaining
2. When scan results contain bills referencing IRA section 6417 repeal, the reconciliation monitor tags affected programs and surfaces the threat in output
3. Running a scan that encounters a Dear Tribal Leader Letter, consultation notice, or EO 13175 reference produces a Tribal consultation alert in results
4. After each scan, the Hot Sheets sync validator produces a comparison showing where scanner CI statuses agree or diverge from Hot Sheets positions
5. Each program in scan results carries an advocacy goal classification (Restore/Replace, Protect Base, Direct Access Parity, Expand and Strengthen, or Urgent Stabilization) derived from the 5 decision rules applied to its current graph state

---

## Phase 4: Report Enhancements

**Goal:** LATEST-BRIEFING.md delivers a complete advocacy intelligence product -- Five Structural Asks mapped to barriers, Hot Sheets alignment visible, sunset countdowns active, CI trends tracked, reconciliation watch surfaced, and advocacy goals classified per program.

**Dependencies:** Phase 3 (reports surface the monitoring and decision logic outputs from Phase 3)

**Requirements:** RPT-01, RPT-02, RPT-03, RPT-04, RPT-05, RPT-06

**Success Criteria:**

1. LATEST-BRIEFING.md contains a "Five Structural Asks" section that maps each Ask to its barrier mitigation pathways and connected programs
2. Each program entry in the briefing shows a Hot Sheets sync indicator (aligned/divergent) with explanation when divergent
3. IIJA-affected programs display a sunset countdown (days remaining) and reconciliation-affected programs appear in a "Reconciliation Watch" section when relevant bills are detected
4. The briefing includes historical CI trend data showing score trajectories over the last N scan cycles for each program
5. Each program entry displays its advocacy goal classification (from Phase 3 decision logic) with the rule that triggered it

**Plans:**

| Plan | Scope | Requirements |
|------|-------|--------------|
| 4.1 - Briefing Sections and Indicators | Five Structural Asks section, Hot Sheets sync indicator, IIJA countdown, Reconciliation Watch, advocacy goal display | RPT-01, RPT-02, RPT-03, RPT-05, RPT-06 |
| 4.2 - Historical CI Trends | Score trajectory tracking across scan cycles, trend visualization in briefing | RPT-04 |

---

## Coverage

| Category | Requirements | Phase | Count |
|----------|-------------|-------|-------|
| Pipeline Validation | PIPE-01, PIPE-02, PIPE-03, PIPE-04 | Phase 1 | 4 |
| Data Model Updates | DATA-01, DATA-02, DATA-03, DATA-04, DATA-05 | Phase 2 | 5 |
| Graph Enhancements | GRAPH-01, GRAPH-02, GRAPH-03, GRAPH-04, GRAPH-05 | Phase 2 | 5 |
| Monitoring Capabilities | MON-01, MON-02, MON-03, MON-04, MON-05 | Phase 3 | 5 |
| Scanner Decision Logic | LOGIC-01, LOGIC-02, LOGIC-03, LOGIC-04, LOGIC-05 | Phase 3 | 5 |
| Report Enhancements | RPT-01, RPT-02, RPT-03, RPT-04, RPT-05, RPT-06 | Phase 4 | 6 |
| **Total** | | | **31** |

Unmapped: 0

## Progress

| Phase | Status | Plans | Completed |
|-------|--------|-------|-----------|
| 1 - Pipeline Validation | Complete (2026-02-09) | 2/2 | 01-01, 01-02 |
| 2 - Data Model and Graph | Complete (2026-02-09) | 2/2 | 02-01, 02-02 |
| 3 - Monitoring and Logic | Complete (2026-02-09) | 3/3 | 03-01, 03-02, 03-03 |
| 4 - Report Enhancements | Not Started | 0/2 | |

---
*Roadmap created: 2026-02-09*
*Last updated: 2026-02-09 (Plan 03-03 complete -- Phase 3 COMPLETE)*
