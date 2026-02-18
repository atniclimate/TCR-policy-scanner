# State: TCR Policy Scanner

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-17)

**Core value:** Tribal Leaders get timely, accurate, machine-scored policy intelligence that surfaces federal developments relevant to their climate resilience programs.
**Current focus:** v1.4 Climate Vulnerability Intelligence -- 12+ federal data sources, composite vulnerability profiles, Doc E standalone reports, website visualizations

**Project Type:** Brownfield -- working Python pipeline with 4 scrapers, relevance scorer, knowledge graph, 5 monitors, decision engine, report generator, 4-document-type DOCX advocacy packet generation, regional aggregation, and GitHub Pages deployment.

## Current Position

**Milestone:** v1.4 Climate Vulnerability Intelligence
**Phase:** 19 - Schema & Core Data Foundation - IN PROGRESS
**Plan:** 03 of 6 complete (19-01 through 19-06), Wave 1 complete
**Status:** Phase 19 IN PROGRESS -- 19-01, 19-02, 19-03 complete (Wave 1 done)
**Last activity:** 2026-02-18 -- Completed 19-01-PLAN.md (FY26 tech debt + path constants + context field)

**Progress:**
```
v1.0 MVP [##########] 100% SHIPPED (4 phases, 9 plans, 30 requirements)
v1.1     [##########] 100% SHIPPED (4 phases, 17 plans, 22 requirements)
v1.2     [##########] 100% SHIPPED (6 phases, 20 plans, 24 requirements)
v1.3     [##########] 100% SHIPPED (4 phases, 20 plans, 39 requirements)
v1.4     [##--------]  18% Phase 19 in progress (7 phases, 28 requirements)
```

## Performance Metrics

| Metric | Value |
|--------|-------|
| v1.0 shipped | 2026-02-09 (4 phases, 9 plans, 30 requirements, 52 tests) |
| v1.1 shipped | 2026-02-10 (4 phases, 17 plans, 22 requirements, 287 tests) |
| v1.2 shipped | 2026-02-11 (6 phases, 20 plans, 24 requirements, 743 tests) |
| v1.3 shipped | 2026-02-14 (4 phases, 20 plans, 39 requirements, 964 tests) |
| Total phases | 18 completed, 7 planned (18.5 + 19-24) |
| Total plans | 66 completed |
| Total requirements | 115 completed + 28 planned = 143 |
| Total tests | 1103 (all passing) |
| Source files | 102 Python files (54 src + 33 tests + 14 scripts + 1 root) |
| Total LOC | ~38,300 Python (src + tests) |
| Documents generated | 992 (384 Doc A + 592 Doc B + 8 Doc C + 8 Doc D) |

## Accumulated Context

### Architecture Notes

- **Pipeline flow:** Ingest (4 async scrapers) -> Normalize -> Graph Construction -> Monitors -> Decision Engine -> Reporting
- **Packet flow:** CLI (--prep-packets) -> PacketOrchestrator -> Registry + Congressional + Awards + Hazards + Economic -> DocxEngine -> DOCX (4 types)
- **Stack:** Python 3.12, aiohttp, python-dateutil, jinja2, pytest, python-docx, rapidfuzz, openpyxl, geopandas
- **Deployment:** GitHub Actions daily-scan.yml (weekday 6 AM Pacific) + generate-packets.yml + deploy-website.yml
- **Dual workspace:** F:\tcr-policy-scanner (Windows dev), GitHub Actions (Linux deploy)
- **API resilience:** Circuit breaker (CLOSED/OPEN/HALF_OPEN) wrapping all scrapers, cache fallback, health check CLI

### v1.4 Phase Plan

| Phase | Name | Requirements | Status |
|-------|------|-------------|--------|
| 18.5 | Architectural Review & Scaffolding | — (pre-phase) | **COMPLETE** |
| 19 | Schema & Core Data Foundation | REG-03, REG-04, VULN-01, VULN-02, XCUT-03, XCUT-04 | **IN PROGRESS** (19-03 done) |
| 20 | Flood & Water Data | FLOOD-01 to FLOOD-06 | Pending |
| 21 | Climate, Geologic & Infrastructure Data | CLIM-01 to CLIM-03, GEO-01, GEO-02, INFRA-01 | Pending |
| 22 | Vulnerability Profiles & Pipeline Integration | VULN-03, VULN-04, REG-01, REG-02, XCUT-01 to XCUT-03, XCUT-05 | Pending |
| 23 | Document Rendering | DOC-01, DOC-02, DOC-03 | Pending |
| 24 | Website & Delivery | WEB-01, WEB-02, WEB-03 | Pending |

### Decisions

v1.3 decisions (33 total) archived to `milestones/v1.3-ROADMAP.md`. Full cumulative log in `PROJECT.md` Key Decisions table.

**Phase 18.5 decisions:**
- [18.5-DEC-01] `RISK_NPCTL` does not exist in NRI v1.20. Compute national percentile from `RISK_SCORE` rank at build time.
- [18.5-DEC-02] SVI `RPL_THEMES` includes excluded Theme 3. Compute custom Tribal SVI from Themes 1+2+4 average.
- [18.5-DEC-03] LOCA2 deferral to v1.5+ validated. CSV Thresholds path eliminates xarray/netCDF4 dependency when ready.
- [18.5-DEC-04] Composite score: 3-component formula (0.40 hazard + 0.35 social + 0.25 adaptive capacity deficit) for v1.4.
- [18.5-DEC-05] Framing: Option D (Hybrid) -- "Climate Resilience Investment Priority" headings, "disproportionate exposure" context, "vulnerability" only in federal proper nouns.
- [18.5-DEC-06] Alaska (229 Tribes): 3-tier narrative strategy. Data gaps framed as federal infrastructure failures.
- [18.5-DEC-07] USGS Water Services: build against NEW API (`api.waterdata.usgs.gov`), not legacy endpoint.
- [18.5-DEC-08] NOAA NCEI: use new endpoint (`ncei.noaa.gov/access/services/data/v1`), not deprecated CDO v2.
- [18.5-DEC-09] GEO-02 (3DEP): defer to v1.5+ (requires research-grade geospatial processing).
- [18.5-DEC-10] Fix 22 hardcoded FY26 strings BEFORE defining DOC_E (pre-Phase 19 tech debt).

**Phase 19 decisions:**
- [19-01-DEC-01] Use f-strings at module init time for doc_types constants (frozen dataclass values evaluated once at import).
- [19-01-DEC-02] Double-brace escape for .replace() placeholders in f-strings (DOC_B/DOC_D header_template).
- [19-01-DEC-03] Preserve FY26 example value in schemas/models.py line 96 (documentation, not functional code).
- [19-01-DEC-04] Leave test mock filenames in test_quality_review.py as literal fy26 (mock data, not generated).

### Todos

- ~~Fix 22 hardcoded FY26 strings (pre-Phase 19 tech debt cleanup)~~ DONE (19-01)
- ~~Add `vulnerability_profile: dict` to TribePacketContext (zero-risk)~~ DONE (19-01)
- ~~Add 6 path constants to `src/paths.py` (zero-risk)~~ DONE (19-01)
- Execute Phase 19: Schema & Core Data Foundation -- Wave 2 next (19-04, 19-05)

### Blockers

_None._

## Session Continuity

### Last Session

**Date:** 2026-02-18
**Stopped at:** Completed 19-01-PLAN.md (FY26 tech debt + path constants + context field)
**Next step:** Continue Phase 19 Wave 2 execution (19-04, 19-05)
**Resume file:** .planning/phases/19-schema-core-data-foundation/19-01-SUMMARY.md
**Quality gate:** 1103 tests passing. Trust 9/10.

## Phase 18.5 Summary

**Completed:** 2026-02-17

**Execution:** 2 waves, 4 research agents
- Wave 1: Sovereignty Scout (data validation) + Fire Keeper (codebase analysis)
- Wave 2: River Runner (schema design) + Horizon Walker (narrative framing)
- Synthesis: Architecture Delta Report

**Deliverables:**
- `.planning/phases/18.5-architectural-review/sovereignty-scout-report.md` (405 lines)
- `.planning/phases/18.5-architectural-review/fire-keeper-report.md` (917 lines)
- `.planning/phases/18.5-architectural-review/river-runner-report.md` (~2,258 lines)
- `.planning/phases/18.5-architectural-review/horizon-walker-report.md` (~1,080 lines)
- `.planning/phases/18.5-architectural-review/ARCHITECTURE-DELTA-REPORT.md` (synthesis)

**Key findings:** 8 architecture corrections, 37 Pydantic v2 models drafted, 4 framing options evaluated (Option D Hybrid recommended), 229 Alaska Tribes require 3-tier narrative strategy, 22 FY26 tech debt instances to fix before Phase 19.

**Decision:** GO with corrections.

---
*State initialized: 2026-02-09*
*Last updated: 2026-02-18 after 19-01 completion*
