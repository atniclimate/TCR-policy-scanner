# State: TCR Policy Scanner

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-10)

**Core value:** Tribal Leaders get timely, accurate, machine-scored policy intelligence that surfaces federal developments relevant to their climate resilience programs.
**Current focus:** v1.1 Tribe-Specific Advocacy Intelligence Packets

**Project Type:** Brownfield -- working Python pipeline with 4 scrapers, relevance scorer, knowledge graph, 5 monitors, decision engine, and report generator.

## Current Position

**Milestone:** v1.1 Tribe-Specific Advocacy Packets
**Phase:** 8 (Assembly, Polish, Web Distribution) -- IN PROGRESS
**Plan:** 3 of 6 complete in Phase 8
**Status:** Phase 8 Wave 2 in progress (08-03 complete, 08-04 in parallel)
**Last activity:** 2026-02-10 -- Completed 08-03-PLAN.md (batch generation OPS-02/OPS-03)

**Progress:**
```
v1.0 MVP [##########] 100% SHIPPED (4 phases, 9 plans, 30 requirements)
v1.1     [##########]  90% Phase 7 complete, Phase 8 planned
  Phase 5: Foundation       [##########] 100% (4/4 plans complete)
  Phase 6: Data Acquisition [##########] 100% (3/3 plans complete)
  Phase 7: Computation+DOCX [##########] 100% (4/4 plans complete)
  Phase 8: Assembly+Polish  [#####     ] 50%  (3/6 plans, Wave 2 in progress)
```

## Performance Metrics

| Metric | Value |
|--------|-------|
| v1.0 Requirements completed | 30/30 |
| v1.0 Phases completed | 4/4 |
| v1.0 Plans completed | 9/9 |
| v1.0 Tests passing | 52/52 |
| v1.0 Code review passes | 3 |
| v1.1 Requirements total | 22 |
| v1.1 Phases planned | 4 (Phases 5-8) |
| v1.1 Requirements mapped | 19/19 |
| v1.1 Phase 5 plans completed | 4/4 |
| v1.1 Phase 5 tests added | 31 |
| v1.1 Total tests passing | 256/256 |
| v1.1 Phase 6 plans completed | 3/3 |
| v1.1 Phase 6 tests added | 23 |
| v1.1 Phase 7 plans completed | 4/4 |
| v1.1 Phase 7 tests added | 108 |
| v1.1 Systemic review | 9-agent, 40 findings triaged, 10 fixes applied |
| v1.1 Requirements complete | 18/22 (REG-01..03, CONG-01..02, AWARD-01..02, HAZ-01..02, ECON-01, DOC-01..06, OPS-02, OPS-03) |
| v1.1 Phase 8 tests added | 42 |
| v1.1 Phase 8 plans | 6 (08-01..06, 3 waves) |
| v1.1 Phase 8 requirements | 8 (DOC-05, DOC-06, OPS-01..03, WEB-01..03) |

## Accumulated Context

### Architecture Notes

- **Pipeline flow:** Ingest (4 async scrapers) -> Normalize -> Graph Construction -> Monitors -> Decision Engine -> Reporting
- **Packet flow:** CLI (--prep-packets) -> PacketOrchestrator -> TribalRegistry + EcoregionMapper + CongressionalMapper + AwardCache + HazardCache -> TribePacketContext -> Display
- **Data files:** scanner_config.json, program_inventory.json, policy_tracking.json, graph_schema.json, ecoregion_config.json, tribal_registry.json, congressional_cache.json, aiannh_tribe_crosswalk.json, tribal_aliases.json, hazard_profiles/*.json, award_cache/*.json
- **Stack:** Python 3.12, aiohttp, python-dateutil, jinja2, pytest, python-docx (v1.1), rapidfuzz (v1.1), openpyxl (v1.1)
- **Deployment:** GitHub Actions daily-scan.yml (weekday 6 AM Pacific, cron `0 13 * * 1-5`)
- **Dual workspace:** F:\tcr-policy-scanner (Windows dev), GitHub Actions (Linux deploy)

### v1.1 Design Decisions

- Output as DOCX (Word) for congressional office distribution
- Programmatic DOCX generation (python-docx), no template files
- All 592 federally recognized Tribes (EPA API scope, updated from 574/575 estimate)
- Two output documents: per-Tribe Program Priorities + shared Federal Funding Overview
- Multi-source hazard profiling: FEMA NRI + USFS wildfire (EJScreen deferred, NOAA deferred)
- Economic impact: USASpending obligations x published multipliers + FEMA BCR (not RIMS II)
- Congressional mapping: Census CD119-AIANNH + Congress.gov API members/committees
- Many-to-many Tribe-to-district model from day one
- Separate CLI command (`--prep-packets`), not daily pipeline integration
- Pre-cache all data layers before DOCX generation (zero API calls during doc construction)
- Batch (all 592) and ad-hoc (single Tribe) generation modes
- Change tracking between packet generations

### Decisions (Phase 5)

| Decision | Plan | Rationale |
|----------|------|-----------|
| Ecoregion program IDs mapped to actual inventory | 05-01 | Plan referenced 5 non-existent program IDs; substituted with verified inventory matches |
| DC mapped to southeast ecoregion | 05-01 | Geographically appropriate; ensures 50-state + DC coverage |
| Lazy-loaded ecoregion config | 05-01 | Faster import time; JSON only loaded on first classify() call |
| WRatio scorer for fuzzy matching | 05-02 | token_sort_ratio gives ~20% for short queries vs long names; WRatio auto-selects partial matching |
| EPA API text/plain response handling | 05-02 | EPA returns JSON with text/plain content type; parse as text + json.loads() |
| 592 tribes in registry (not 574) | 05-02 | EPA API AllTribes filter now returns 592 records; more complete than research estimate |
| Census CD119-AIANNH over CRS R48107 | 05-03 | Machine-readable, 119th Congress (current), has area overlap data; CRS report is 118th Congress PDF |
| Four-tier crosswalk matching | 05-03 | Single-pass normalization matched only 60/577; added variant generation + substring + fuzzy = 550/577 (95.3%) |
| 538 Congress members (not 541) | 05-03 | API returned 538 current members; difference from research estimate likely vacancies |
| Auto-select first fuzzy match | 05-04 | Orchestrator auto-selects best match from ambiguous results, shows alternatives as warning |
| Lazy import for packets module | 05-04 | PacketOrchestrator only imported when --prep-packets is set; avoids rapidfuzz overhead for existing pipeline |
| Graceful no-delegation display | 05-04 | Tribes without congressional data get informative message instead of crash |

### Decisions (Phase 6)

| Decision | Plan | Rationale |
|----------|------|-----------|
| MAX risk / SUM EAL aggregation for multi-county Tribes | 06-02 | Conservative: highlights worst-case risk exposure; SUM reflects total expected annual loss |
| State-level county fallback for unmatched Tribes | 06-02 | Less precise but ensures every Tribe gets some hazard data when tribal relational CSV unavailable |
| Schema discovery for USFS/NRI columns | 06-02 | Column names uncertain from research; dynamic header inspection avoids hardcoded assumptions |
| Empty profiles for all 592 Tribes | 06-02 | Downstream DOCX generation never crashes on missing cache; note field explains data gaps |
| token_sort_ratio (not WRatio) for award matching | 06-01 | WRatio is for interactive registry resolve(); award matching needs strict, word-order-invariant scoring |
| 85 threshold for fuzzy award matching | 06-01 | Prevents false positives; alias table (3751 entries) handles known names at Tier 1 |
| Per-Tribe cache files (not single file) | 06-01 | O(1) per-Tribe lookup during DOCX generation; avoids loading all 592 Tribes' data |
| Zero-award Tribes get advocacy framing | 06-01 | First-time applicant status is a competitive advantage, not a data gap |
| Read-only cache loading in orchestrator | 06-03 | Orchestrator displays pre-built data, never generates; keeps --prep-packets fast |
| Generic _load_tribe_cache helper | 06-03 | Reused for both award and hazard cache directories; DRY pattern |
| Awards grouped by program_id in display | 06-03 | Shows which specific programs funded the Tribe for advocacy context |

### Decisions (Phase 7)

| Decision | Plan | Rationale |
|----------|------|-----------|
| Zero-award Tribes use PROGRAM_BENCHMARK_AVERAGES | 07-01 | Primary path since all current caches have empty awards; is_benchmark=True enables distinct framing |
| Total obligation includes benchmarks | 07-01 | Complete economic picture for Tribes even without award history |
| Actual awards sorted before benchmarks | 07-01 | Most impactful data shown first in by_program list |
| 18 NRI hazard types mapped to programs | 07-01 | Full coverage; unmapped hazards fall back to bia_tcr + fema_bric |
| Dual hazard code resolution (code + type) | 07-01 | Handles both NRI code field and human-readable type field from cached profiles |
| paragraph.clear() not cell.text="" for headers | 07-02 | cell.text="" creates ghost empty run at runs[0]; clear() properly removes all runs |
| _ColorNamespace class for COLORS | 07-02 | Attribute access (COLORS.primary_dark) more readable than dict access |
| docx.document.Document for isinstance | 07-02 | Top-level Document import is a factory function, not a type |
| Page breaks (not section breaks) between Hot Sheets | 07-03 | Section breaks disrupt header/footer; page breaks are cosmetic only |
| Paragraph-level shading for Key Ask callout | 07-03 | OxmlElement w:shd on pPr simpler than table-based callout |
| USFS wildfire data only for _WILDFIRE_PROGRAM_IDS | 07-03 | Only wildfire-related programs benefit from USFS risk data |
| Evidence lines derived dynamically from context | 07-03 | Structural ask evidence assembled at render time from award/hazard data |
| Always render appendix section even when empty | 07-04 | Better document structure; shows reader all programs were considered |
| dataclasses.asdict() for economic_summary serialization | 07-04 | TribeEconomicSummary lacks to_dict(); asdict() provides deep conversion |
| Shared generate_packet_from_context() helper | 07-04 | Avoids duplicate code between generate_packet() and run_single_tribe() flows |
| NCAI/ATNI references removed from all files | review | Organizations did not authorize name use; replaced with generic terms |
| Allow critical program overflow past MAX_PROGRAMS | review | In practice only 2-3 critical programs exist; capping could drop a legitimately critical program |
| Path traversal validation on tribe_id | review | Defense-in-depth: sanitize tribe_id in DocxEngine.save() |
| 10MB JSON cache size limit | review | Defense-in-depth: prevents memory exhaustion from oversized files |
| NamedTemporaryFile closed before save | review | Prevents Windows file locking conflicts |
| Program relevance filtering supersedes AF-04 | review | ProgramRelevanceFilter returns 8-12 programs per Tribe; omitted programs go to appendix |

### Decisions (Phase 8)

| Decision | Plan | Rationale |
|----------|------|-----------|
| Structural asks count hardcoded to 5 | 08-01 | Per project design; dynamic count would require cross-section coordination |
| Senators shown as "At-Large" in district column | 08-01 | Senators represent entire state, not specific districts |
| EAL formatted as $X,XXX (no decimals) | 08-01 | Consistent with _format_dollars pattern in docx_hotsheet.py |
| Evidence line uses program_id match (not CFDA) | 08-01 | Direct match sufficient for standalone section |
| Policy tracking lookup via extensible_fields with reasoning fallback | 08-02 | policy_tracking.json uses 'positions' key; authorization_status in extensible_fields |
| Monitor data tries multiple key names for alerts | 08-02 | Cascading lookup (alerts/findings/threats/monitors) handles different output formats |
| _FEMA_PROGRAM_IDS includes 5 IDs (only 2 in current inventory) | 08-02 | Future-proof for when fema_hmgp/fma/pdm are added |
| gc and time imported inside run_all_tribes() | 08-03 | Lazy import avoids module-level overhead; only needed during batch runs |
| gc.collect() in finally block (every 25 Tribes) | 08-03 | Runs even if Tribe fails; prevents memory buildup across 592 Tribes |
| time.monotonic() for elapsed time | 08-03 | Immune to system clock adjustments; better for measuring durations |
| run_all_tribes() returns dict (not None) | 08-03 | Enables programmatic checking in tests and CI pipelines |
| Error list capped at 10 in output | 08-03 | Prevents wall of text for mass failures; full list in logs |

### Todos

_None._

### Blockers

_None._

## Session Continuity

### Last Session

**Date:** 2026-02-10
**Stopped at:** Completed 08-03-PLAN.md (batch generation OPS-02/OPS-03)
**Next step:** Verify 08-04 completion, then execute Wave 3 (08-05 + 08-06)
**Resume file:** .planning/phases/08-assembly-polish/08-MASTER-PROMPT.md
**Resume command:** Execute Wave 3: Plans 08-05 and 08-06

---
*State initialized: 2026-02-09*
*Last updated: 2026-02-10 after 08-03 completion (256 tests, 18/22 requirements)*
