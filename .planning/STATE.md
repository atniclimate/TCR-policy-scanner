# State: TCR Policy Scanner

## Project Reference

**Core Value:** Tribal Leaders get timely, accurate, machine-scored policy intelligence that surfaces federal developments relevant to their climate resilience programs.

**Current Focus:** Phase 1 -- validate the existing pipeline works against live APIs before building new capabilities on top.

**Project Type:** Brownfield -- working Python pipeline with 4 scrapers, relevance scorer, knowledge graph, and report generator already implemented.

## Current Position

**Milestone:** v1
**Phase:** 1 - Pipeline Validation
**Plan:** Not started
**Status:** NOT STARTED

**Progress:**
```
Phase 1 [..........] 0%  Pipeline Validation
Phase 2 [..........] 0%  Data Model and Graph
Phase 3 [..........] 0%  Monitoring and Logic
Phase 4 [..........] 0%  Report Enhancements
Overall [..........] 0%  0/31 requirements
```

## Performance Metrics

| Metric | Value |
|--------|-------|
| Requirements completed | 0/31 |
| Phases completed | 0/4 |
| Plans completed | 0/8 |
| Session count | 0 |

## Accumulated Context

### Key Decisions

| Decision | Phase | Rationale |
|----------|-------|-----------|
| Phase 1 validates before building | Roadmap | Brownfield project -- must confirm existing pipeline works with live APIs before adding features |
| Data model before monitoring | Roadmap | Monitors need enriched graph and updated statuses to function correctly |
| Reports last | Roadmap | Reports surface monitoring/logic output -- build the data pipeline first |

### Architecture Notes

- **Pipeline flow:** Ingest (4 async scrapers) -> Normalize -> Graph Construction -> Analysis -> Reporting
- **Data files:** scanner_config.json, program_inventory.json, policy_tracking.json, graph_schema.json
- **Stack:** Python 3.12, aiohttp, python-dateutil, jinja2
- **Deployment:** GitHub Actions daily-scan.yml (weekday 6 AM Pacific)
- **Dual workspace:** F:\tcr-policy-scanner (Windows dev), GitHub Actions (Linux deploy)

### Todos

_None yet._

### Blockers

_None yet._

## Session Continuity

### Last Session

_No sessions yet._

### Resume Instructions

Start with Phase 1, Plan 1.1 (Scraper Validation and Pipeline Run). Run `python src/main.py` and verify each scraper returns data from live APIs. Check that LATEST-BRIEFING.md and LATEST-RESULTS.json are generated. API keys needed: CONGRESS_API_KEY, SAM_API_KEY.

---
*State initialized: 2026-02-09*
*Last updated: 2026-02-09*
