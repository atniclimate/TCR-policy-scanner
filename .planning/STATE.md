# State: TCR Policy Scanner

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-10)

**Core value:** Tribal Leaders get timely, accurate, machine-scored policy intelligence that surfaces federal developments relevant to their climate resilience programs.
**Current focus:** v1.1 Tribe-Specific Advocacy Intelligence Packets

**Project Type:** Brownfield -- working Python pipeline with 4 scrapers, relevance scorer, knowledge graph, 5 monitors, decision engine, and report generator.

## Current Position

**Milestone:** v1.1 Tribe-Specific Advocacy Packets
**Phase:** 5 (Foundation) -- not yet started
**Plan:** None (roadmap created, awaiting phase planning)
**Status:** Roadmap created, ready for phase planning
**Last activity:** 2026-02-10 -- Roadmap created (4 phases, 19 requirements)

**Progress:**
```
v1.0 MVP [##########] 100% SHIPPED (4 phases, 9 plans, 30 requirements)
v1.1     [          ]   0% Roadmap created, planning Phase 5
  Phase 5: Foundation       [          ] 0%  (5 requirements)
  Phase 6: Data Acquisition [          ] 0%  (4 requirements)
  Phase 7: Computation+DOCX [          ] 0%  (5 requirements)
  Phase 8: Assembly+Polish  [          ] 0%  (5 requirements)
```

## Performance Metrics

| Metric | Value |
|--------|-------|
| v1.0 Requirements completed | 30/30 |
| v1.0 Phases completed | 4/4 |
| v1.0 Plans completed | 9/9 |
| v1.0 Tests passing | 52/52 |
| v1.0 Code review passes | 3 |
| v1.1 Requirements total | 19 |
| v1.1 Phases planned | 4 (Phases 5-8) |
| v1.1 Requirements mapped | 19/19 |

## Accumulated Context

### Architecture Notes

- **Pipeline flow:** Ingest (4 async scrapers) -> Normalize -> Graph Construction -> Monitors -> Decision Engine -> Reporting
- **Data files:** scanner_config.json, program_inventory.json, policy_tracking.json, graph_schema.json
- **Stack:** Python 3.12, aiohttp, python-dateutil, jinja2, pytest, python-docx (new for v1.1), rapidfuzz (new for v1.1)
- **Deployment:** GitHub Actions daily-scan.yml (weekday 6 AM Pacific, cron `0 13 * * 1-5`)
- **Dual workspace:** F:\tcr-policy-scanner (Windows dev), GitHub Actions (Linux deploy)

### v1.1 Design Decisions

- Output as DOCX (Word) for congressional office distribution
- Programmatic DOCX generation (python-docx), no template files
- All 575 federally recognized Tribes (NCAI scope, not just ATNI)
- Two output documents: per-Tribe Program Priorities + shared Federal Funding Overview
- Multi-source hazard profiling: FEMA NRI + USFS wildfire (EJScreen deferred, NOAA deferred)
- Economic impact: USASpending obligations x published multipliers + FEMA BCR (not RIMS II)
- Congressional mapping: CRS R48107 table + Congress.gov API members/committees
- Many-to-many Tribe-to-district model from day one
- Separate CLI command (`--prep-packets`), not daily pipeline integration
- Pre-cache all data layers before DOCX generation (zero API calls during doc construction)
- Batch (all 575) and ad-hoc (single Tribe) generation modes
- Change tracking between packet generations

### Todos

_None._

### Blockers

_None._

## Session Continuity

### Last Session

**Date:** 2026-02-10
**Stopped at:** Roadmap created for v1.1 (Phases 5-8, 19 requirements mapped)
**Next step:** `/gsd:plan-phase 5` to create plans for Phase 5 (Foundation)
**Resume file:** None

---
*State initialized: 2026-02-09*
*Last updated: 2026-02-10 after v1.1 roadmap creation*
