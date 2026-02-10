# State: TCR Policy Scanner

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-10)

**Core value:** Tribal Leaders get timely, accurate, machine-scored policy intelligence that surfaces federal developments relevant to their climate resilience programs.
**Current focus:** v1.1 Tribe-Specific Advocacy Intelligence Packets

**Project Type:** Brownfield -- working Python pipeline with 4 scrapers, relevance scorer, knowledge graph, 5 monitors, decision engine, and report generator.

## Current Position

**Milestone:** v1.1 Tribe-Specific Advocacy Packets
**Phase:** Not started (defining requirements)
**Status:** Defining requirements
**Last activity:** 2026-02-10 -- Milestone v1.1 started

**Progress:**
```
v1.0 MVP [##########] 100% SHIPPED (4 phases, 9 plans, 30 requirements)
v1.1      [          ]   0% Defining requirements
```

## Performance Metrics

| Metric | Value |
|--------|-------|
| v1.0 Requirements completed | 30/30 |
| v1.0 Phases completed | 4/4 |
| v1.0 Plans completed | 9/9 |
| v1.0 Tests passing | 52/52 |
| v1.0 Code review passes | 3 |

## Accumulated Context

### Architecture Notes

- **Pipeline flow:** Ingest (4 async scrapers) -> Normalize -> Graph Construction -> Monitors -> Decision Engine -> Reporting
- **Data files:** scanner_config.json, program_inventory.json, policy_tracking.json, graph_schema.json
- **Stack:** Python 3.12, aiohttp, python-dateutil, jinja2, pytest, python-docx (new for v1.1)
- **Deployment:** GitHub Actions daily-scan.yml (weekday 6 AM Pacific, cron `0 13 * * 1-5`)
- **Dual workspace:** F:\tcr-policy-scanner (Windows dev), GitHub Actions (Linux deploy)

### v1.1 Design Decisions

- Output as DOCX (Word) for congressional office distribution
- Programmatic DOCX generation (python-docx), no template files
- All 574 federally recognized Tribes (NCAI scope, not just ATNI)
- Two output documents: per-Tribe Program Priorities + shared Federal Funding Overview
- Multi-source hazard profiling: FEMA NRI + EPA EJScreen + USFS wildfire + NOAA
- Economic impact: USASpending obligations x BEA multipliers + FEMA BCR avoided cost
- Congressional mapping: Census TIGER districts + Congress.gov API members/committees
- Batch (all 574) and ad-hoc (single Tribe) generation modes
- Change tracking between packet generations

### Todos

_None._

### Blockers

_None._

## Session Continuity

### Last Session

**Date:** 2026-02-10
**Stopped at:** v1.1 milestone initialization, defining requirements
**Resume file:** None

---
*State initialized: 2026-02-09*
*Last updated: 2026-02-10 after v1.1 milestone start*
