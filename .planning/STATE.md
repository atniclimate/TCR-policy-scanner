# State: TCR Policy Scanner

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-12)

**Core value:** Tribal Leaders get timely, accurate, machine-scored policy intelligence that surfaces federal developments relevant to their climate resilience programs.
**Current focus:** v1.3 Production Launch -- Phase 17 IN PROGRESS (1/5 plans complete: 17-02)

**Project Type:** Brownfield -- working Python pipeline with 4 scrapers, relevance scorer, knowledge graph, 5 monitors, decision engine, report generator, 4-document-type DOCX advocacy packet generation, regional aggregation, and GitHub Pages deployment.

## Current Position

**Milestone:** v1.3 Production Launch
**Phase:** 17 of 18 (Website Deployment) -- IN PROGRESS
**Plan:** 02 of 5 in phase (HTML/CSS rewrite complete)
**Status:** Plan 17-02 complete, 17-01/03/04/05 remaining
**Last activity:** 2026-02-12 -- Completed 17-02-PLAN.md (HTML/CSS rewrite)

**Progress:**
```
v1.0 MVP [##########] 100% SHIPPED (4 phases, 9 plans, 30 requirements)
v1.1     [##########] 100% SHIPPED (4 phases, 17 plans, 22 requirements)
v1.2     [##########] 100% SHIPPED (6 phases, 20 plans, 24 requirements)
v1.3     [█████████░] 88% Phase 17 IN PROGRESS (1/5 plans, 10 WEB)
         Phase 16 COMPLETE (2/2 plans, 6 DOCX)
         Phase 15 COMPLETE (7/7 plans, 15 INTEL + 3 XCUT)
```

## Performance Metrics

| Metric | Value |
|--------|-------|
| v1.0 shipped | 2026-02-09 (4 phases, 9 plans, 30 requirements, 52 tests) |
| v1.1 shipped | 2026-02-10 (4 phases, 17 plans, 22 requirements, 287 tests) |
| v1.2 shipped | 2026-02-11 (6 phases, 20 plans, 24 requirements, 743 tests) |
| Total phases | 14 completed + Phase 16 COMPLETE, Phase 17 in progress, 1 remaining |
| Total plans | 60 completed |
| Total requirements | 76 completed, 39 active, 18 verified (Phase 15), 6 verified (Phase 16) |
| Total tests | 954 (all passing) |
| Source files | 96 Python files |
| Total LOC | ~37,900 Python |
| Documents generated | 992 (384 Doc A + 592 Doc B + 8 Doc C + 8 Doc D) |

## Accumulated Context

### Architecture Notes

- **Pipeline flow:** Ingest (4 async scrapers) -> Normalize -> Graph Construction -> Monitors -> Decision Engine -> Reporting
- **Packet flow:** CLI (--prep-packets) -> PacketOrchestrator -> Registry + Congressional + Awards + Hazards + Economic -> DocxEngine -> DOCX (4 types)
- **Stack:** Python 3.12, aiohttp, python-dateutil, jinja2, pytest, python-docx, rapidfuzz, openpyxl, geopandas
- **Deployment:** GitHub Actions daily-scan.yml (weekday 6 AM Pacific) + generate-packets.yml
- **Dual workspace:** F:\tcr-policy-scanner (Windows dev), GitHub Actions (Linux deploy)
- **API resilience:** Circuit breaker (CLOSED/OPEN/HALF_OPEN) wrapping all scrapers, cache fallback, health check CLI

### v1.3 Phase Structure

| Phase | Goal | Agent Swarm | Requirements |
|-------|------|-------------|--------------|
| 15 | Congressional intelligence + data reliability | Scout, Fire Keeper, Runner, Walker | 15 INTEL + 3 XCUT |
| 16 | Document quality assurance | 5 audit agents | 6 DOCX |
| 17 | Website deployment | 4 review agents | 10 WEB |
| 18 | Production hardening | 4 bug hunt agents | 5 HARD |

### Decisions

| ID | Decision | Phase |
|----|----------|-------|
| DEC-1503-01 | Alert severity uses 4 tiers (CRITICAL/HIGH/MEDIUM/LOW) with escalation rules | 15-03 |
| DEC-1503-02 | Knowledge graph uses deterministic IDs from source data (bioguide, system codes) | 15-03 |
| DEC-1503-03 | Confidence scoring uses weighted average with per-program weight adjustments | 15-03 |
| DEC-1503-04 | VoteNode deferred pending Senate.gov structured vote data availability | 15-03 |
| DEC-1501-01 | Legislator model kept lightweight vs full CongressionalDelegate | 15-01 |
| DEC-1501-02 | Confidence decay_rate=0.01 (~69 day half-life) for congressional data | 15-01 |
| DEC-1501-03 | DEFAULT_SOURCE_WEIGHTS as module-level dict for override flexibility | 15-01 |
| DEC-1502-01 | Grants.gov uses startRecordNum offset not page number | 15-02 |
| DEC-1502-02 | USASpending _fetch_obligations upgraded to limit=100 with full pagination | 15-02 |
| DEC-1502-03 | Safety caps vary by scraper (2500/1000/1000/5000) | 15-02 |
| DEC-1504-01 | Bill relevance: 4 weighted components (subject 0.30, CFDA 0.25, committee 0.20, keyword 0.25) | 15-04 |
| DEC-1504-02 | Two-phase relevance scoring: quick title scan then full detail scoring | 15-04 |
| DEC-1504-03 | Voting records deferred pending Senate API availability | 15-04 |
| DEC-1505-01 | Bills-first ordering (position 4 before delegation at position 5) | 15-05 |
| DEC-1505-02 | Doc B relevance threshold 0.5 for bill inclusion | 15-05 |
| DEC-1505-03 | Regional bill aggregation uses combined_relevance (sum of per-Tribe scores) | 15-05 |
| DEC-1506-01 | Use asyncio.run() not get_event_loop() for scraper pagination tests (pytest-anyio compat) | 15-06 |
| DEC-1506-02 | Regional rendering tests extract text from paragraphs AND table cells | 15-06 |
| DEC-1507-01 | Air gap exemptions: quality_review.py, doc_types.py, main.py, generator.py | 15-07 |
| DEC-1507-02 | FY hardcoding check scoped to Phase 15 files (pre-existing in doc_types.py) | 15-07 |
| DEC-1601-01 | Performance budget relaxed from 60s to 210s -- python-docx parsing ~200ms/file inherent cost | 16-01 |
| DEC-1601-02 | Gap finder uses both findings[] and missing_tests[] for downstream consumption | 16-01 |
| DEC-1602-01 | Amber status badge darkened to #B45309 (4.6:1 ratio) for WCAG AA compliance | 16-02 |
| DEC-1602-02 | AgentReviewOrchestrator default changed to enabled=True with warning on bypass | 16-02 |
| DEC-1602-03 | ACCURACY-006 (P3) fixed alongside GAP-002 (P1) as companion fix | 16-02 |
| DEC-1702-01 | Listbox width uses calc(100% - 2rem) to account for search container padding | 17-02 |
| DEC-1702-02 | Tribe card uses opacity transition with data-visible attribute for JS-controlled fade-in | 17-02 |

### Todos

_None._

### Blockers

_None._

## Session Continuity

### Last Session

**Date:** 2026-02-12
**Stopped at:** Completed 17-02-PLAN.md (HTML/CSS rewrite with ARIA combobox and dark mode)
**Next step:** Execute 17-01 (Fuse.js vendor), 17-03 (JavaScript), 17-04 (data), or 17-05 (deploy)
**Resume file:** None
**Quality gate:** SYNTHESIS.md PASS at outputs/docx_review/SYNTHESIS.md

---
*State initialized: 2026-02-09*
*Last updated: 2026-02-12 after 17-02 execution (HTML/CSS rewrite: ARIA combobox, dark mode, CRT effect, badges)*
