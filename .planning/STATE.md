# State: TCR Policy Scanner

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-17)

**Core value:** Tribal Leaders get timely, accurate, machine-scored policy intelligence that surfaces federal developments relevant to their climate resilience programs.
**Current focus:** v1.4 Climate Vulnerability Intelligence -- 12+ federal data sources, composite vulnerability profiles, Doc E standalone reports, website visualizations

**Project Type:** Brownfield -- working Python pipeline with 4 scrapers, relevance scorer, knowledge graph, 5 monitors, decision engine, report generator, 4-document-type DOCX advocacy packet generation, regional aggregation, and GitHub Pages deployment.

## Current Position

**Milestone:** v1.4 Climate Vulnerability Intelligence
**Phase:** 20 - Flood & Water Data - PLANNED (ready for execution)
**Plan:** 7 plans created (20-01 through 20-07), 3 waves. Spec swarm complete (30 files).
**Status:** Phase 20 PLANNED -- 7 plans + 30-file specification suite ready. Next: `/gsd:execute-phase 20`
**Last activity:** 2026-02-18 -- Phase 20 agent swarm complete (4 phases, 4 agents, 30 spec files)

**Progress:**
```
v1.0 MVP [##########] 100% SHIPPED (4 phases, 9 plans, 30 requirements)
v1.1     [##########] 100% SHIPPED (4 phases, 17 plans, 22 requirements)
v1.2     [##########] 100% SHIPPED (6 phases, 20 plans, 24 requirements)
v1.3     [##########] 100% SHIPPED (4 phases, 20 plans, 39 requirements)
v1.4     [####------]  33% Phase 19 COMPLETE, Phase 20 PLANNED (7 phases, 28 requirements)
```

## Performance Metrics

| Metric | Value |
|--------|-------|
| v1.0 shipped | 2026-02-09 (4 phases, 9 plans, 30 requirements, 52 tests) |
| v1.1 shipped | 2026-02-10 (4 phases, 17 plans, 22 requirements, 287 tests) |
| v1.2 shipped | 2026-02-11 (6 phases, 20 plans, 24 requirements, 743 tests) |
| v1.3 shipped | 2026-02-14 (4 phases, 20 plans, 39 requirements, 964 tests) |
| Total phases | 19 completed, 1 planned (20), 4 pending (21-24) |
| Total plans | 72 completed (66 prior + 6 Phase 19), 7 planned (Phase 20) |
| Total requirements | 121 completed + 28 planned = 149 |
| Total tests | 1257 (all passing, 1 skipped) |
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
| 19 | Schema & Core Data Foundation | REG-03, REG-04, VULN-01, VULN-02, XCUT-03, XCUT-04 | **COMPLETE** (6/6 done) |
| 20 | Flood & Water Data | FLOOD-01 to FLOOD-06 | **PLANNED** (7 plans, spec swarm done) |
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
- [19-05-DEC-01] Import _safe_float from hazards.py (DRY, battle-tested sentinel handling).
- [19-05-DEC-02] SVI profiles output to data/svi/profiles/ (intermediate, consumed by composite builder).
- [19-05-DEC-03] Skip counties where ALL 3 included themes are 0.0 (suppressed data, not real zeros).
- [19-05-DEC-04] Store RPL_THEMES for reference but never use in composite (includes excluded Theme 3).
- [19-06-DEC-01] Only check Doc B/D headings for FORBIDDEN_DOC_B_TERMS (internal Doc A/C/E headings intentionally use strategy terms).

### Todos

- ~~Fix 22 hardcoded FY26 strings (pre-Phase 19 tech debt cleanup)~~ DONE (19-01)
- ~~Add `vulnerability_profile: dict` to TribePacketContext (zero-risk)~~ DONE (19-01)
- ~~Add 6 path constants to `src/paths.py` (zero-risk)~~ DONE (19-01)
- ~~Build SVI 2022 builder with theme exclusion~~ DONE (19-05)
- ~~Build NRI expanded builder with version pinning~~ DONE (19-04)
- ~~Integration & XCUT-04 compliance tests~~ DONE (19-06)
- ~~Phase 20 planning: 7 PLAN.md files created~~ DONE
- ~~Phase 20 spec swarm: 4-phase agent swarm (30 files)~~ DONE
- ~~Fix 4 P1 audit findings (NIBS ROI, HMGP frozen, date range, BRIC/HMGP split)~~ DONE
- Execute Phase 20: `/gsd:execute-phase 20` (7 plans, 3 waves)

### Blockers

_None._

## Session Continuity

### Last Session

**Date:** 2026-02-18
**Stopped at:** Phase 20 agent swarm complete (all 4 phases). P1 audit fixes applied. ROADMAP + STATE updated.
**Next step:** `/gsd:execute-phase 20` (7 plans in 3 waves: Wave 1 = 20-01, Wave 2 = 20-02 through 20-06, Wave 3 = 20-07)
**Resume file:** .planning/flood-module/SWARM-COMPLETE.md
**Quality gate:** 1257 tests passing, 1 skipped. Trust 9/10. Phase 20 specs: ~618+ tests specified, 20 Pydantic models, 4 API clients.

## Phase 20 Planning Summary

**Planned:** 2026-02-18

**Planning artifacts:**
- 7 PLAN.md files in `.planning/phases/20-flood-water-data/` (20-01 through 20-07)
- 30 specification files in `.planning/flood-module/` produced by 4-phase agent swarm
- Research: `20-RESEARCH.md`, `20-RESEARCH-ADDENDUM.md`, `20-CONTEXT.md`

**Agent swarm (4 phases, 4 agents):**
- Phase 1: Watershed Walker + Accuracy Agent (architecture + research verification)
- Phase 2: Flood Scout + Current Runner (data models + test infrastructure)
- Phase 3: All 4 agents (implementation specs + final audit)
- Phase 4: Watershed Walker (final planning documents + cross-reference consistency)

**Key specs:**
- 20 Pydantic v2 models (2 enums + 18 models) in `FLOOD-DATA-MODELS.md`
- 4 API clients (OpenFEMA, USGS OGC, Atlas 14 PFDS, NOAA CO-OPS) in `API-CLIENT-SPECS.md`
- 13 endpoints verified (10 VERIFIED, 3 PROBABLE) in `ENDPOINT-VERIFICATION.md`
- 6 builder implementation specs (9-step template each) in `IMPL-FLOOD-BUILDERS.md`
- ~618+ tests specified across 10 test spec files
- 4 enhancement proposals (ENH-F01 through F04, 134 total story points, future milestones)

**Audit:** 15 findings (4 P1 FIXED, 6 P2 advisory, 5 P3 advisory). Verdict: PASS.

**Data impact:** `program_inventory.json` updated from 16 to 18 programs (added `fema_hmgp` ALN 97.039 and `fema_fma` ALN 97.029).

**Execution plan:** 3 waves
- Wave 1: 20-01 (schemas, shared infra, paths, reference data)
- Wave 2: 20-02, 20-03, 20-04, 20-05, 20-06 (6 builders, parallel)
- Wave 3: 20-07 (CLI orchestrator, combined profile, coverage report)

**Decisions:**
- [20-DEC-01] All 6 flood sources route through existing county FIPS crosswalk (no new geographic files)
- [20-DEC-02] Coastal classification: marine > lacustrine > inland priority hierarchy
- [20-DEC-03] Missing data: 2-category system (not_applicable vs monitoring_gap), never bare None
- [20-DEC-04] Claims-outside-zones %: THE single most important advocacy number, traced at every handoff
- [20-DEC-05] USGS OGC API at v0 (not v1); peak flows use `dataretrieval` library fallback
- [20-DEC-06] All dollar amounts use `Decimal` (not float) in Pydantic models
- [20-DEC-07] OpenFEMA countyCode confirmed 5-digit FIPS (not 3-digit)
- [20-DEC-08] Include ALL disaster types (no incidentType filter per 20-CONTEXT.md)
- [20-DEC-09] Store raw API responses alongside parsed data for streamflow
- [20-DEC-10] HMGP "severely constrained" (not "frozen"); BRIC/HMGP split into separate program entries

---

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
*Last updated: 2026-02-18 after Phase 20 planning complete (agent swarm done, P1 fixes applied)*
