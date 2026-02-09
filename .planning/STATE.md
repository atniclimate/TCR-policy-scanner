# State: TCR Policy Scanner

## Project Reference

**Core Value:** Tribal Leaders get timely, accurate, machine-scored policy intelligence that surfaces federal developments relevant to their climate resilience programs.

**Current Focus:** Phase 4 in progress. Report sections and pipeline wiring complete (Plan 1). CI trend history remains (Plan 2).

**Project Type:** Brownfield -- working Python pipeline with 4 scrapers, relevance scorer, knowledge graph, 5 monitors, decision engine, and report generator.

## Current Position

**Milestone:** v1
**Phase:** 4 of 4 (Report Enhancements) -- In progress
**Plan:** 1 of 2 complete
**Status:** In progress
**Last activity:** 2026-02-09 - Completed 04-01-PLAN.md

**Progress:**
```
Phase 1 [##########] 100% Pipeline Validation (2/2 plans) COMPLETE
Phase 2 [##########] 100% Data Model and Graph (2/2 plans) COMPLETE
Phase 3 [##########] 100% Monitoring and Logic (3/3 plans) COMPLETE
Phase 4 [#####.....] 50%  Report Enhancements (1/2 plans)
Overall [#########.] 89%  8/9 plans complete
```

## Performance Metrics

| Metric | Value |
|--------|-------|
| Requirements completed | 33/37 (PIPE-01..04, DATA-02, DATA-04, DATA-05, GRAPH-01, GRAPH-02, GRAPH-05, MON-01..05, LOGIC-01..05, RPT-01, RPT-02, RPT-03, RPT-05, RPT-06) |
| Phases completed | 3/4 |
| Plans completed | 8/9 |
| Session count | 8 |

## Accumulated Context

### Key Decisions

| Decision | Phase | Rationale |
|----------|-------|-----------|
| Phase 1 validates before building | Roadmap | Brownfield project -- must confirm existing pipeline works with live APIs before adding features |
| Data model before monitoring | Roadmap | Monitors need enriched graph and updated statuses to function correctly |
| Reports last | Roadmap | Reports surface monitoring/logic output -- build the data pipeline first |
| Grants.gov search2 response wraps in data object | 01-01 | search2 endpoint returns `{data: {oppHits: [...]}}` not `{oppHits: [...]}` |
| Federal Register uses slug agency IDs | 01-01 | API requires strings like `interior-department`, not numeric IDs |
| USASpending requires explicit fields param | 01-01 | POST body without `fields` returns 422 |
| Congress.gov graceful skip without API key | 01-01 | Scraper logs warning and returns 0 items rather than crashing pipeline |
| SAM_API_KEY stored in GitHub Secrets | 01-02 | Added for future SAM.gov scraper use; prevents revisiting secrets config later |
| CI validation via workflow_dispatch | 01-02 | Manual trigger exercises same code path as cron schedule; sufficient for PIPE-03 validation |
| flagged_floor raised to 0.10 | 02-01 | FEMA BRIC at CI 0.12 stays FLAGGED; gap 0.10-0.0 reserved for TERMINATED only |
| terminated_floor at 0.0 | 02-01 | Absolute floor for confirmed-dead programs |
| Reconciliation keywords as shared scanner terms | 02-01 | Added to global action_keywords/search_queries so all scrapers benefit |
| Structural asks reuse AdvocacyLeverNode | 02-02 | ask_ prefix distinguishes from per-program lever_ nodes; avoids new type per RESEARCH.md |
| Trust Super-Node connects to 5 BIA/EPA programs | 02-02 | bia_tcr, bia_tcr_awards, epa_gap, epa_stag, epa_tribal_air carry direct trust responsibility implications |
| ADVANCES/TRUST_OBLIGATION edge direction | 02-02 | ADVANCES: ask -> program (advocacy direction); TRUST_OBLIGATION: trust node -> program (obligation direction) |
| THREATENS edges are ephemeral (regenerated each scan) | 03-01 | Days_remaining changes daily; persisting would create stale data |
| Fund-exhaustion programs get INFO alerts, no THREATENS edge | 03-01 | No calendar deadline means no days_remaining for urgency calculation |
| Reconciliation uses urgency_threshold_days for days_remaining | 03-01 | Reconciliation timelines are unpredictable; setting to threshold ensures LOGIC-05 triggers |
| Enacted laws filtered by config list + latest_action status | 03-01 | Double filtering prevents OBBBA false positives and any future enacted bills |
| Rule evaluation as explicit list, not data-driven | 03-02 | 5 rules is too few to justify dispatch table; explicit list is clearer |
| FLAGGED treated as near-TERMINATED for LOGIC-01 | 03-02 | FEMA BRIC at CI 0.12 needs Restore/Replace classification |
| AT_RISK/UNCERTAIN with discretionary = threat signal for LOGIC-02 | 03-02 | Status itself indicates risk; combined with discretionary funding confirms Protect Base |
| access_type required for LOGIC-03 and LOGIC-04 | 03-02 | Programs without explicit access_type fall through to default classification |
| HotSheetsValidator runs first in monitor order | 03-03 | CI overrides must be applied before decision engine classifies programs |
| Hot Sheets status aligned at baseline | 03-03 | Clean starting point; user updates inventory manually when Hot Sheets positions change |
| Tribal consultation signals are INFO severity | 03-03 | Consultations are informational signals, not threats -- no THREATENS edges created |
| Monitor data saved to separate JSON file | 03-03 | ReportGenerator modification is Phase 4 scope; separate file provides clean data interface |
| Section ordering: urgent above fold, analytical middle, reference at end | 04-01 | Tribal leaders see time-sensitive items (reconciliation/IIJA) first, then strategic context, then reference data |
| Always-render pattern for Reconciliation Watch and IIJA Countdown | 04-01 | "No active threats" is valuable information for Tribal leaders preparing for meetings |
| Classified/unclassified split in Advocacy Goals | 04-01 | Prevents 14 "No match" rows from obscuring 2 classified programs |
| CI Dashboard Determination truncated 80 -> 70 chars | 04-01 | Accommodates 5th column (Hot Sheets) without excessive table width |
| All Items section moved to near-end position | 04-01 | Reference data goes after structural analysis sections |

### Architecture Notes

- **Pipeline flow:** Ingest (4 async scrapers) -> Normalize -> Graph Construction -> Monitors -> Decision Engine -> Reporting
- **Data files:** scanner_config.json, program_inventory.json, policy_tracking.json, graph_schema.json
- **Stack:** Python 3.12, aiohttp, python-dateutil, jinja2
- **Deployment:** GitHub Actions daily-scan.yml (weekday 6 AM Pacific, cron `0 13 * * 1-5`)
- **Dual workspace:** F:\tcr-policy-scanner (Windows dev), GitHub Actions (Linux deploy)
- **Live API results (01-01):** Federal Register: 93 items, Grants.gov: 83 items, USASpending: 103 items, Congress.gov: needs API key
- **CI results (01-02):** All 4 scrapers ran in CI with API keys from GitHub Secrets; outputs committed at 6178fc3
- **Pipeline throughput:** 279 raw -> 164 scored above threshold -> 182 graph nodes, 196 graph edges
- **GitHub Secrets configured:** CONGRESS_API_KEY, SAM_API_KEY
- **CI thresholds:** 7-tier model (secure/stable/stable_but_vulnerable/at_risk/uncertain/flagged/terminated)
- **Scanner keywords:** 42 action keywords, 16 search queries (includes reconciliation/repeal terms)
- **CFDA mappings:** 12 entries in grants_gov.py (includes 15.124 for BIA TCR Awards)
- **Graph stats (static seed):** 79 nodes (16 ProgramNode, 21 AdvocacyLeverNode, 20 AuthorityNode, 8 FundingVehicleNode, 13 BarrierNode, 1 TrustSuperNode), 118 edges
- **Graph stats (with scan data):** 188 nodes, 236 edges
- **Graph edge types:** AUTHORIZED_BY, FUNDED_BY, BLOCKED_BY, MITIGATED_BY, OBLIGATED_BY, ADVANCES, TRUST_OBLIGATION, THREATENS
- **Structural asks:** 5 asks (multi_year, match_waivers, direct_access, consultation, data_sovereignty) with 26 ADVANCES edges and 9 MITIGATED_BY edges
- **Trust Super-Node:** FEDERAL_TRUST_RESPONSIBILITY with 5 TRUST_OBLIGATION edges
- **Monitor framework:** BaseMonitor ABC, MonitorAlert dataclass, MonitorRunner orchestrator in src/monitors/
- **Active monitors (5):** HotSheetsValidator (MON-04, runs first), IIJASunsetMonitor (MON-01), ReconciliationMonitor (MON-02), DHSFundingCliffMonitor (MON-05), TribalConsultationMonitor (MON-03)
- **Monitor output (cached scan, Feb 9):** 5 alerts (2 DHS WARNING, 2 IIJA INFO, 1 IIJA fund-exhaustion INFO), 4 THREATENS edges
- **Monitor config:** 6 sub-keys in scanner_config.json monitors section
- **Monitor state:** outputs/.monitor_state.json tracks known Hot Sheets divergences between runs
- **Monitor data output:** outputs/LATEST-MONITOR-DATA.json with alerts, classifications, and summary
- **Decision engine:** DecisionEngine in src/analysis/decision_engine.py with 5 rules, ADVOCACY_GOALS constant, classify_all() method
- **Decision rules:** LOGIC-05 > 01 > 02 > 03 > 04 priority order; secondary_rules for transparency
- **Test infrastructure:** pytest installed, tests/ package with 45 test cases for decision engine
- **Hot Sheets baseline:** All 16 programs have hot_sheets_status field aligned with scanner CI status
- **Pipeline integration:** run_monitors_and_classify() in src/main.py runs stages 3.5-3.6
- **Report generator:** 11 sections in LATEST-BRIEFING.md (5 new from 04-01: Reconciliation Watch, IIJA Countdown, Advocacy Goals, Structural Asks, Hot Sheets column)
- **Report data flow:** monitor_data and classifications passed from run_monitors_and_classify() -> reporter.generate() -> _build_markdown()/_build_json()
- **Briefing sections (04-01):** Executive Summary -> Reconciliation Watch -> IIJA Countdown -> New Developments -> Critical Updates -> CI Dashboard (w/ Hot Sheets) -> FLAGGED -> Advocacy Goals -> Structural Asks -> Barriers -> Authorities -> Advocacy Levers -> All Items

### Todos

_None._

### Blockers

_None._

## Session Continuity

### Last Session

**Date:** 2026-02-09
**Stopped at:** Completed 04-01-PLAN.md (Report Sections and Pipeline Wiring)
**Resume file:** 04-02-PLAN.md (CI Trend History)

### Resume Instructions

Plan 04-01 complete. ReportGenerator has 5 new sections and pipeline wiring is done. Proceed with 04-02-PLAN.md for CI trend history tracking (RPT-04). The _build_markdown() method has clear insertion points for the CI Trends section near the end (before All Items).

---
*State initialized: 2026-02-09*
*Last updated: 2026-02-09*
