# State: TCR Policy Scanner

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-11)

**Core value:** Tribal Leaders get timely, accurate, machine-scored policy intelligence that surfaces federal developments relevant to their climate resilience programs.
**Current focus:** v1.2 Tech Debt Cleanup + Data Foundation

**Project Type:** Brownfield -- working Python pipeline with 4 scrapers, relevance scorer, knowledge graph, 5 monitors, decision engine, report generator, and per-Tribe DOCX advocacy packet generation.

## Current Position

**Milestone:** v1.2 Tech Debt Cleanup + Data Foundation
**Phase:** 14 - Integration & Validation
**Plan:** 6 of 7 (14-01 + 14-02 + 14-03 + 14-04 + 14-05 + 14-06 complete)
**Status:** In progress
**Last activity:** 2026-02-11 -- Completed 14-05-PLAN.md (Batch Generation + Quality Review)

**Progress:**
```
v1.0 MVP [##########] 100% SHIPPED (4 phases, 9 plans, 30 requirements)
v1.1     [##########] 100% SHIPPED (4 phases, 17 plans, 22 requirements)
v1.2     [#########~]  95% IN PROGRESS (6 phases, 17 plans, 24 requirements)
  Phase  9: Config Hardening     [##########] 100%  2/2 plans complete  DONE
  Phase 10: Code Quality         [##########] 100%  2/2 plans complete  DONE
  Phase 11: API Resilience       [##########] 100%  2/2 plans complete  DONE
  Phase 12: Award Population     [##########] 100%  4/4 plans complete  DONE (gap closure)
  Phase 13: Hazard Population    [##########] 100%  3/3 plans complete  DONE
  Phase 14: Integration          [########~~]  86%  6/7 plans complete  IN PROGRESS
```

## Performance Metrics

| Metric | Value |
|--------|-------|
| v1.0 shipped | 2026-02-09 (4 phases, 9 plans, 30 requirements, 52 tests) |
| v1.1 shipped | 2026-02-10 (4 phases, 17 plans, 22 requirements, 287 tests) |
| v1.2 research | 2026-02-11 (4 agents, 4 code fixes, 96 new tests, 15 Pydantic models) |
| v1.2 roadmap | 2026-02-11 (6 phases, 15 plans, 24 requirements) |
| Total phases | 8 completed + 6 planned = 14 |
| Total plans | 40 completed + 1 planned = 41 |
| Total requirements | 63 completed + 13 planned = 76 |
| Total tests | 738 |
| Source files | 71 (+1: quality_review.py) |
| Total LOC | ~25,000 Python (est. +1,300 scripts + tests + HA aliases) |
| Source files | 70 (+6: generate_ha_aliases.py, test_housing_authority_aliases.py, etc.) |

## Accumulated Context

### Architecture Notes

- **Pipeline flow:** Ingest (4 async scrapers) -> Normalize -> Graph Construction -> Monitors -> Decision Engine -> Reporting
- **Packet flow:** CLI (--prep-packets) -> PacketOrchestrator -> Registry + Congressional + Awards + Hazards + Economic -> DocxEngine -> DOCX
- **Stack:** Python 3.12, aiohttp, python-dateutil, jinja2, pytest, python-docx, rapidfuzz, openpyxl
- **Deployment:** GitHub Actions daily-scan.yml (weekday 6 AM Pacific)
- **Dual workspace:** F:\tcr-policy-scanner (Windows dev), GitHub Actions (Linux deploy)

### Research Team Findings (2026-02-11)

**Sovereignty Scout** (801-line report):
- 3 of 4 scrapers don't paginate (silently truncating results)
- Congress.gov never fetches bill details (missing sponsors, committees, summaries)
- USASpending has hardcoded FY26 dates (now fixed by Fire Keeper)
- Missing UEI field for deterministic entity linking
- 13 improvements across 4 priority tiers

**Fire Keeper** (4 fixes, 0 regressions):
- Logger naming: 14 files fixed to `__name__`
- FY26 hardcoding: new `src/config.py` with dynamic fiscal year
- format_dollars: new `src/utils.py` as single source of truth
- graph_schema paths: `PROJECT_ROOT` via pathlib

**River Runner** (96 tests, 15 Pydantic models):
- Overall data completeness: 67.2%
- Award cache: 0% populated (592 placeholder files)
- Hazard profiles: 0% populated (592 placeholder files)
- Populating both sources: 67.2% -> ~91% completeness
- 239 Tribes missing BIA codes, 91 unmapped to districts

**Horizon Walker** (5 proposals, ~87KB):
- Congressional alert system: 21 story points, 3 sprints
- Confidence scoring: current system confidence 0.36
- Interactive knowledge graph: D3.js, +58KB to widget
- Data completeness roadmap: 8 sources prioritized, 39% -> 91%
- MILESTONE-NEXT.md: 6 phases, 29 story points

### Key Decisions

- Phase numbering continues from v1.1 (Phase 9 onward)
- Wave parallelization: Phases 9+10 (Wave 1), 11+12 (Wave 2), 13+14 (Wave 3)
- 24 v1.2 requirements (original count of 22 was undercounted; INTG-05 and INTG-06 were missed)
- Quick depth: 2-3 plans per phase, 15 total plans
- DEC-0901-01: src/paths.py imports only pathlib.Path (zero project imports) to prevent circular dependencies
- DEC-0901-02: src/config.py re-exports PROJECT_ROOT via __all__ for backward compatibility
- DEC-0902-01: Scripts use sys.path insertion pattern for src.paths access (standalone entry points)
- DEC-0902-02: Config-overridable paths use `Path(raw) if raw else CONSTANT` pattern (backward compat)
- DEC-0902-03: Docstring path references left as-is (documentation, not executable)
- DEC-1001-01: IRS elective pay uses "N/A - ..." sentinel string (not a grant program, no CFDA exists)
- DEC-1001-02: usbr_tap shares ALN 15.507 with usbr_watersmart (same WaterSMART umbrella)
- DEC-1002-01: E402 suppressed via per-file-ignores for scripts/*.py only (sys.path pattern)
- DEC-1002-02: CFDA_TRACKER_PATH import redirected from base.py re-export to direct src.paths import
- DEC-1002-03: Unused variables removed or kept based on side-effect analysis
- DEC-1002-04: hazards.py E402 fixed by moving import above constant definitions
- DEC-1101-01: Circuit breaker wraps entire retry loop, not individual attempts (trips only when ALL retries exhausted)
- DEC-1101-02: Injectable clock parameter defaults to time.monotonic, enabling zero-sleep deterministic tests
- DEC-1101-03: Module-level constants (MAX_RETRIES, BACKOFF_BASE, DEFAULT_TIMEOUT) preserved as defaults for backward compatibility
- DEC-1101-04: retries parameter in _request_with_retry changed to None default (falls through to self.max_retries)
- DEC-1102-01: Cache files use dotfile convention (.cache_{source}.json) in OUTPUTS_DIR for gitignore compatibility
- DEC-1102-02: 10MB file size cap on cache load prevents memory exhaustion from corrupted/bloated cache files
- DEC-1102-03: Health probes use aiohttp directly (not BaseScraper) to avoid circuit breaker interference with diagnostics
- DEC-1102-04: Async tests use asyncio.run() instead of pytest-asyncio to avoid adding a test dependency
- DEC-1201-01: TRIBAL_AWARD_TYPE_CODES includes 06+10 (direct payments) alongside 02-05 (grants)
- DEC-1201-02: Sequential not parallel querying to respect USASpending rate limits
- DEC-1201-03: Page-100 safety break prevents infinite loop on large result sets
- DEC-1202-01: Consortium patterns are case-insensitive substring matches; 'association of' requires 'of' suffix to avoid false positives
- DEC-1202-02: Task 1 code bundled in 12-01 commit during parallel execution; Task 2 tests committed separately
- DEC-1203-01: USASpending API requires award_type_codes from single group per request; split into TRIBAL_AWARD_TYPE_CODE_GROUPS
- DEC-1203-02: 418/592 coverage (70.6%) accepted below 450 target; housing authority names dominate unmatched
- DEC-1203-03: Data files (award_cache/*.json, outputs/*.json) NOT committed to git
- DEC-1301-01: data/nri/ added to .gitignore since it contains large downloaded data files (shapefiles, CSVs)
- DEC-1301-02: requests library added to requirements.txt for download script (aiohttp not needed for sync downloads)
- DEC-1301-03: Shapefile ZIPs extract to subdirectories (aiannh/, county/) to keep data/nri/ organized
- DEC-1302-01: EAL dollar amounts use weighted SUM (not average) to reflect proportional exposure
- DEC-1302-02: Ratings re-derived from weighted scores via quintile breakpoints (not MAX of source ratings)
- DEC-1302-03: Version string changed from '1.20' to 'NRI_v1.20' to document data source
- DEC-1302-04: Empty profiles use empty all_hazards dict instead of 18-entry zero dict
- DEC-1303-01: USFS conditional-risk-to-structures overrides NRI WFIR only when both NRI WFIR > 0 and USFS risk_to_homes > 0
- DEC-1303-02: Original NRI WFIR score preserved in usfs_wildfire.nri_wfir_original for audit trail
- DEC-1303-03: data/usfs/ and data/hazard_profiles/ added to .gitignore (large downloaded/generated files)
- DEC-1303-04: NRI version detected dynamically from sibling ZIP filenames; falls back to NRI_v1.20
- DEC-1303-05: Coverage report tracks per-state breakdown and unmatched Tribes list
- DEC-1303-06: populate_hazards.py requires NRI county CSV as hard prerequisite; crosswalk and USFS are soft (warnings)
- DEC-1204-01: Housing authority aliases generated programmatically (suffix stripping) + curated overrides (5 rounds)
- DEC-1204-02: Regional Alaska HAs (Cook Inlet, Bering Straits, Interior, etc.) excluded — serve multiple Nations
- DEC-1204-03: BIA-prefixed names (e.g., "DOI TRB WA UPPER SKAGIT") added as curated overrides
- DEC-1204-04: Self-designation names (Apsaalooke = Crow, Sicangu Wicoti = Rosebud) included in curated overrides
- DEC-1204-05: MN Chippewa component bands (Bois Forte, White Earth, Mille Lacs, Fond du Lac, Leech Lake) mapped to parent epa_100000161
- DEC-1401-01: All 18 NRI hazard types always present in all_hazards dict (zeros for non-applicable) for schema consistency
- DEC-1401-02: regional_config.json is separate from ecoregion_config.json -- complementary configs serving different purposes
- DEC-1401-03: Crosscutting region has empty states list; spans all 592 Tribes for Doc C/D aggregation
- DEC-1401-04: USFS XLSX first sheet is README; USFS wildfire override unavailable this run (soft prerequisite per DEC-1303-06)
- DEC-1402-01: Default doc_type_config is None (not DOC_B) for full backward compatibility
- DEC-1402-02: Air gap covers all src/packets/ files including strategic_overview and docx_template
- DEC-1402-03: Cover page shows "For Congressional Office Use" as default classification
- DEC-1403-01: Section renderers use keyword argument doc_type_config=None for backward compatibility
- DEC-1403-02: Congressional Key Ask uses program description instead of advocacy_lever for ASK line
- DEC-1403-03: Orchestrator _has_complete_data checks awards AND hazards AND delegation
- DEC-1403-04: Hazard alignment paragraph in economic impact for all doc types (factual, safe for congressional)
- DEC-1403-05: Change tracking excluded from congressional docs (is_internal gate)
- DEC-1404-01: RegionalContext in regional.py (not context.py) to avoid bloating TribePacketContext file
- DEC-1404-02: Orchestrator regional methods use lazy imports for regional module
- DEC-1404-03: Delegation overlap keyed by bioguide_id with formatted_name fallback
- DEC-1406-01: Congressional coverage denominator uses registry universe (592) not cache entries (501)
- DEC-1406-02: Cross-source completeness six-way classification: complete / partial(award+deleg) / award-only / deleg-only / hazard-only / none
- DEC-1405-01: 384 Tribes get Doc A (not 400+) due to data completeness constraints (awards + hazards + delegation intersection)
- DEC-1405-02: Placeholder warnings (91) are non-critical; TBD text exists in docs where specific data fields are empty

### Todos

_None._

### Blockers

_None._

## Session Continuity

### Last Session

**Date:** 2026-02-11
**Stopped at:** Completed 14-05-PLAN.md (Batch Generation + Quality Review)
**Next step:** Execute 14-07-PLAN.md (GitHub Pages Deployment)
**Resume file:** None
**Resume command:** `/gsd:execute-phase 14`

---
*State initialized: 2026-02-09*
*Last updated: 2026-02-11 after 14-05 completion (Phase 14 in progress, 6/7 plans: 14-01 + 14-02 + 14-03 + 14-04 + 14-05 + 14-06)*
