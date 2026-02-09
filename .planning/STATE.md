# State: TCR Policy Scanner

## Project Reference

**Core Value:** Tribal Leaders get timely, accurate, machine-scored policy intelligence that surfaces federal developments relevant to their climate resilience programs.

**Current Focus:** Phase 3 in progress -- monitor framework and threat monitors complete. Decision engine and signal monitors next.

**Project Type:** Brownfield -- working Python pipeline with 4 scrapers, relevance scorer, knowledge graph, and report generator already implemented.

## Current Position

**Milestone:** v1
**Phase:** 3 of 4 (Monitoring and Logic) -- IN PROGRESS
**Plan:** 1 of 3 complete
**Status:** In progress
**Last activity:** 2026-02-09 - Completed 03-01-PLAN.md

**Progress:**
```
Phase 1 [##########] 100% Pipeline Validation (2/2 plans) COMPLETE
Phase 2 [##########] 100% Data Model and Graph (2/2 plans) COMPLETE
Phase 3 [###.......] 33%  Monitoring and Logic (1/3 plans)
Phase 4 [..........] 0%   Report Enhancements
Overall [######....] 63%  5/8 plans complete
```

## Performance Metrics

| Metric | Value |
|--------|-------|
| Requirements completed | 13/31 (PIPE-01..04, DATA-02, DATA-04, DATA-05, GRAPH-01, GRAPH-02, GRAPH-05, MON-01, MON-02, MON-05) |
| Phases completed | 2/4 |
| Plans completed | 5/8 |
| Session count | 5 |

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

### Architecture Notes

- **Pipeline flow:** Ingest (4 async scrapers) -> Normalize -> Graph Construction -> Analysis -> Reporting
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
- **Graph edge types:** AUTHORIZED_BY, FUNDED_BY, BLOCKED_BY, MITIGATED_BY, OBLIGATED_BY, ADVANCES, TRUST_OBLIGATION, THREATENS
- **Structural asks:** 5 asks (multi_year, match_waivers, direct_access, consultation, data_sovereignty) with 26 ADVANCES edges and 9 MITIGATED_BY edges
- **Trust Super-Node:** FEDERAL_TRUST_RESPONSIBILITY with 5 TRUST_OBLIGATION edges
- **Monitor framework:** BaseMonitor ABC, MonitorAlert dataclass, MonitorRunner orchestrator in src/monitors/
- **Active monitors:** IIJASunsetMonitor (MON-01), ReconciliationMonitor (MON-02), DHSFundingCliffMonitor (MON-05)
- **Monitor output (empty scan, Feb 9):** 6 alerts (3 IIJA sunset INFO, 1 IIJA fund-exhaustion INFO, 2 DHS funding WARNING), 5 THREATENS edges
- **Monitor config:** 6 sub-keys in scanner_config.json monitors section

### Todos

_None._

### Blockers

_None._

## Session Continuity

### Last Session

**Date:** 2026-02-09
**Stopped at:** Completed 03-01-PLAN.md (Monitor Framework and Threat Monitors)
**Resume file:** `.planning/phases/03-monitoring-logic/03-02-PLAN.md` (Decision Engine)

### Resume Instructions

Phase 3 Plan 1 (Monitor Framework) is complete. Three threat monitors producing THREATENS edges. Begin Plan 03-02 (Decision Engine with 5 classification rules, TDD).

---
*State initialized: 2026-02-09*
*Last updated: 2026-02-09*
