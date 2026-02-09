# State: TCR Policy Scanner

## Project Reference

**Core Value:** Tribal Leaders get timely, accurate, machine-scored policy intelligence that surfaces federal developments relevant to their climate resilience programs.

**Current Focus:** Phase 2 in progress -- data model enrichment. Plan 01 complete (data file gaps), Plan 02 next (graph schema/builder).

**Project Type:** Brownfield -- working Python pipeline with 4 scrapers, relevance scorer, knowledge graph, and report generator already implemented.

## Current Position

**Milestone:** v1
**Phase:** 2 of 4 (Data Model and Graph)
**Plan:** 1 of 2 complete
**Status:** In progress
**Last activity:** 2026-02-09 - Completed 02-01-PLAN.md

**Progress:**
```
Phase 1 [##########] 100% Pipeline Validation (2/2 plans) COMPLETE
Phase 2 [#####.....] 50%  Data Model and Graph (1/2 plans)
Phase 3 [..........] 0%   Monitoring and Logic
Phase 4 [..........] 0%   Report Enhancements
Overall [###.......] 37%  3/8 plans complete
```

## Performance Metrics

| Metric | Value |
|--------|-------|
| Requirements completed | 7/31 (PIPE-01, PIPE-02, PIPE-03, PIPE-04, DATA-02, DATA-04, DATA-05) |
| Phases completed | 1/4 |
| Plans completed | 3/8 |
| Session count | 3 |

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

### Todos

_None._

### Blockers

_None._

## Session Continuity

### Last Session

**Date:** 2026-02-09
**Stopped at:** Completed 02-01-PLAN.md (Data File Gaps) -- Phase 2 Plan 1 complete
**Resume file:** `.planning/phases/02-data-model-graph/02-02-PLAN.md`

### Resume Instructions

Phase 2 Plan 1 (Data File Gaps) is complete. DATA-02, DATA-04, DATA-05 requirements addressed. Continue with Phase 2 Plan 2 (Graph Schema and Builder Enhancements).

---
*State initialized: 2026-02-09*
*Last updated: 2026-02-09*
