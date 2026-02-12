# TCR Policy Scanner

## What This Is

Automated policy intelligence pipeline for Tribal Climate Resilience advocacy. Scans 4 federal policy sources (Federal Register, Grants.gov, Congress.gov, USASpending), scores relevance against 16 tracked programs, runs 5 threat/signal monitors, classifies advocacy goals via a 5-rule decision engine, and produces advocacy intelligence products for Tribal Leaders advocating for FY26 climate resilience funding. Generates 4 document types — Tribal internal strategy (Doc A), Tribal congressional overview (Doc B), regional InterTribal strategy (Doc C), and regional congressional overview (Doc D) — for all 592 federally recognized Tribes across 8 regions, backed by real USASpending award data and FEMA NRI hazard profiles.

Built for the Tribal Climate Resilience program, serving 592 federally recognized Tribal Nations.

## Core Value

Tribal Leaders get timely, accurate, machine-scored policy intelligence that surfaces federal developments relevant to their climate resilience programs — so they know what changed and what to do about it.

## Requirements

### Validated

- ✓ 4 async scrapers (Federal Register, Grants.gov, Congress.gov, USASpending) with BaseScraper pattern, exponential backoff, 403/429 resilience — v1.0
- ✓ 5-factor weighted relevance scorer (program_match 0.35, tribal_keyword_density 0.20, recency 0.10, source_authority 0.15, action_relevance 0.20) with critical boost and Tribal eligibility override — v1.0
- ✓ Scan-to-scan change detection — v1.0
- ✓ Knowledge graph builder with typed dataclass schema (ProgramNode, AuthorityNode, FundingVehicleNode, BarrierNode, AdvocacyLeverNode, ObligationNode, TrustSuperNode) — v1.0
- ✓ Markdown briefing (14 sections) and JSON report generation with CI Dashboard — v1.0
- ✓ 16 tracked programs with CI scores, Hot Sheets alignment, and 7 status categories (SECURE, STABLE, STABLE_BUT_VULNERABLE, AT_RISK, UNCERTAIN, FLAGGED, TERMINATED) — v1.0
- ✓ Config-driven architecture with domain adaptability — v1.0
- ✓ GitHub Actions daily scan workflow (weekday 6 AM Pacific) — v1.0
- ✓ Strategic Framework bridging scanner to FY26 Hot Sheets — v1.0
- ✓ Pipeline validation — all 4 scrapers validated against live APIs, CI workflow runs on schedule — v1.0
- ✓ Five Structural Asks as AdvocacyLeverNodes with ADVANCES edges — v1.0
- ✓ Trust Super-Node (FEDERAL_TRUST_RESPONSIBILITY) with TRUST_OBLIGATION edges — v1.0
- ✓ 5 active monitors (IIJA sunset, reconciliation, DHS funding cliff, Tribal consultation, Hot Sheets sync) — v1.0
- ✓ 5-rule advocacy decision engine (52 TDD tests) — v1.0
- ✓ 14-section briefing with Reconciliation Watch, IIJA Countdown, Advocacy Goals, Structural Asks, Hot Sheets sync, CI Score Trends — v1.0
- ✓ Historical CI trend tracking with 90-entry cap — v1.0
- ✓ 592-Tribe registry from EPA API with BIA codes, states, ecoregion classification — v1.1
- ✓ Many-to-many congressional delegation mapping (Census CD119-AIANNH + Congress.gov API) — v1.1
- ✓ Per-Tribe USASpending award matching with two-tier system (3,751 aliases + rapidfuzz >= 85) — v1.1
- ✓ Multi-source hazard profiling (FEMA NRI 18 types + USFS wildfire risk) for all 592 Tribes — v1.1
- ✓ District-level economic impact framing with published multipliers + FEMA 4:1 BCR — v1.1
- ✓ Professional DOCX generation engine (DocxEngine + StyleManager + HotSheetRenderer) — v1.1
- ✓ Document 1: per-Tribe DOCX (592 variants) with 8-section assembly — v1.1
- ✓ Document 2: shared strategic overview DOCX with 7 sections — v1.1
- ✓ Batch (all 592 Tribes) and ad-hoc (single Tribe) CLI generation modes — v1.1
- ✓ Change tracking ("Since Last Packet" diffs between generations) — v1.1
- ✓ GitHub Pages search widget (15KB) with Tribe autocomplete and DOCX download — v1.1
- ✓ Config-driven fiscal year (`src/config.py` with dynamic FY) — v1.2
- ✓ Config-driven `graph_schema.json` path (PROJECT_ROOT via pathlib) — v1.2
- ✓ Deduplicated `format_dollars` (`src/utils.py` single source of truth) — v1.2
- ✓ Logger naming fixed to `__name__` across 14 files — v1.2
- ✓ Centralized path constants module (`src/paths.py`) with 25 constants, 47 files migrated — v1.2
- ✓ All 16 programs have complete metadata (cfda, access_type, funding_type) — v1.2
- ✓ Ruff-clean codebase (pyproject.toml, zero violations) — v1.2
- ✓ Circuit breaker pattern (CLOSED/OPEN/HALF_OPEN) wrapping all 4 scrapers — v1.2
- ✓ Configurable retry/backoff + cache fallback for API resilience — v1.2
- ✓ Health check CLI (--health-check) reports API availability — v1.2
- ✓ Batch USASpending award population (14 CFDAs x 5 FYs, 451/592 Tribes matched) — v1.2
- ✓ Two-tier award matching with 18,776 aliases (including housing authority mappings) — v1.2
- ✓ FEMA NRI county-level hazard data with area-weighted Tribe-to-county crosswalk — v1.2
- ✓ USFS wildfire risk override for fire-prone Tribes — v1.2
- ✓ 592 hazard profiles populated with real NRI + USFS data — v1.2
- ✓ 4 document types: Doc A (Tribal internal), Doc B (congressional), Doc C (regional internal), Doc D (regional congressional) — v1.2
- ✓ Audience differentiation with air gap enforcement (no strategy/leverage in congressional docs) — v1.2
- ✓ Regional aggregation across 8 regions with Doc C/D generation — v1.2
- ✓ Quality review automation (audience leakage, air gap, placeholder detection) — v1.2
- ✓ Data validation script with coverage reporting across all cache types — v1.2
- ✓ GitHub Pages deployment with production URLs (atniclimate.github.io) — v1.2

### Active

*No active requirements — next milestone not yet defined.*

See `.planning/milestones/` for archived milestone requirements.

### Out of Scope

- Tribal-specific or sensitive data collection -- T0 (Open) data only, public federal sources
- Real-time streaming -- batch scan architecture, not live feeds
- Non-climate Tribal policy domains -- focused on TCR; config-driven design supports future expansion
- Interactive web dashboard -- AF-05 superseded by static search+download widget (shipped v1.1); not a dashboard or editing UI
- EPA EJScreen integration -- removed from EPA Feb 2025; FEMA NRI + USFS cover core hazard needs
- NOAA climate projections -- valuable but deferred; adds significant integration complexity beyond NRI
- BEA RIMS II multipliers -- cost-prohibitive ($500/region); published multipliers + FEMA BCR sufficient
- Scraper pagination fixes -- important but separate concern; v1.3 candidate
- Congress.gov bill detail fetching -- v1.3 candidate

## Context

**Organization:** Tribal Climate Resilience program
**Repository:** private repository
**TSDF Classification:** T0 (Open) — all data from public federal documents
**Stack:** Python 3.12, aiohttp, python-dateutil, jinja2, pytest, python-docx, rapidfuzz, openpyxl — async pipeline + DOCX generation
**Server:** GitHub-hosted, developed locally at F:\tcr-policy-scanner
**Local workspace:** F:\tcr-policy-scanner

**Shipped v1.2 with ~37,900 LOC Python across 95 source files.**

**Pipeline architecture:**
```
Ingest (4 scrapers) -> Normalize -> Graph Construction -> Monitors (5) -> Decision Engine -> Reporting (14 sections)
```

**Packet architecture:**
```
CLI (--prep-packets) -> PacketOrchestrator -> Registry + Congressional + Awards + Hazards + Economic -> DocxEngine -> DOCX
```

**Data files:**
- `config/scanner_config.json` — sources, scoring weights, 46 Tribal keywords, 42 action keywords, monitor config
- `data/program_inventory.json` — 16 programs with CI, advocacy levers, hot_sheets_status, access_type, funding_type
- `data/policy_tracking.json` — FY26 positions with 7-tier CI thresholds
- `data/graph_schema.json` — 20 authorities, 13 barriers, 8 funding vehicles, Five Structural Asks, Trust Super-Node
- `data/ecoregion_config.json` — 7 NCA5 ecoregion definitions with program priority mappings
- `data/tribal_registry.json` — 592 Tribes with BIA codes, states, name variants
- `data/congressional_cache.json` — 538 members with committee assignments per Tribe
- `data/tribal_aliases.json` — 18,776 USASpending name aliases for two-tier matching (including housing authority mappings)
- `data/housing_authority_aliases.json` — 15,027 housing authority aliases for award matching
- `data/award_cache/*.json` — per-Tribe USASpending award histories (592 files, 451 with real data)
- `data/hazard_profiles/*.json` — per-Tribe FEMA NRI + USFS hazard profiles (592 files, all with real data)
- `data/regional_config.json` — 8 NCA5-based regional definitions with Tribe-to-region mapping

**Test suite:** 743 tests across 20+ modules (circuit breaker, hazard aggregation, USFS override, housing authority aliases, document types, audience filtering, regional aggregation, quality review, coverage validation, plus all v1.0/v1.1 modules)

**Known tech debt (8 items, 0 critical):**
- 4 circuit breaker behaviors need human E2E verification (network manipulation tests)
- Non-atomic write_text() for award cache files (re-runnable, low risk)
- 141 Tribes with zero awards (remaining housing authority gaps)
- 91 placeholder warnings in docs (TBD where data fields empty)
- Doc A coverage limited to 384/592 (data completeness constraint)

## Constraints

- **TSDF T0**: No Tribal-specific data — public federal sources only
- **API keys**: Congress.gov key via CONGRESS_API_KEY env var; SAM key via SAM_API_KEY; no keys in repo
- **Stack**: Python 3.12, async (aiohttp), python-docx for DOCX generation — maintain existing patterns
- **CI/CD**: GitHub Actions for automated scans — must remain functional
- **Dual workspace**: Development on F:\tcr-policy-scanner (Windows), deployment via GitHub Actions (Linux)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| T0 (Open) classification | All source data is public federal policy — no Tribal data collected | ✓ Good |
| Config-driven architecture | Enables future domain expansion beyond TCR | ✓ Good |
| 5-factor weighted scoring | Balances program relevance, Tribal keywords, recency, authority, actionability | ✓ Good |
| 7-tier CI status model | Hot Sheets alignment with SECURE through TERMINATED tiers | ✓ Good — validated across 16 programs |
| Five Structural Asks framework | Cross-cutting advocacy levers from Hot Sheets | ✓ Good — 26 ADVANCES + 9 MITIGATED_BY edges |
| Trust Super-Node pattern | Models federal trust responsibility as single meta-node | ✓ Good — 5 TRUST_OBLIGATION edges |
| F:\ local workspace | Consolidate development on external drive with full access | ✓ Good |
| Pipeline validates before building | Brownfield project — verify before extending | ✓ Good — caught 3 API bugs |
| Grants.gov search2 + aln param | API migrated from /opportunities/search to /api/search2 | ✓ Good |
| Federal Register slug agency IDs | API requires string slugs, not numeric IDs | ✓ Good |
| THREATENS edges ephemeral | Days_remaining changes daily; persisting creates stale data | ✓ Good |
| Priority-ordered rule evaluation | 5 rules too few for dispatch table; explicit list clearer | ✓ Good |
| HotSheetsValidator runs first | CI overrides must apply before decision engine | ✓ Good |
| Always-render threat sections | "No threats" is valuable info for meeting prep | ✓ Good |
| CI history 90-entry cap | ~3 months daily scans; prevents unbounded growth | ✓ Good |
| DOCX output (not Markdown) | Congressional offices need printable/shareable documents | ✓ Good — DocxEngine + StyleManager operational |
| Programmatic DOCX (no template files) | Build document structure in code for full control; no external template dependency | ✓ Good — python-docx with _ColorNamespace styles |
| All 592 Tribes | Program scope serves all federally recognized Tribes nationally (EPA API returns 592) | ✓ Good — registry + caches for all 592 |
| Multi-source hazard profiling | FEMA NRI + USFS wildfire (EJScreen deferred, NOAA deferred) | ✓ Good — 18 NRI hazard types + USFS wildfire |
| Published multipliers for economic impact | Standard federal methodology makes framing defensible (not RIMS II at $500/region) | ✓ Good — FEMA BCR + published multipliers |
| Scanner generates both documents | Document 1 (per-Tribe) and Document 2 (strategic overview) both auto-generated | ✓ Good — DocxEngine + StrategicOverviewGenerator operational |
| Web distribution widget | Static search+download on GitHub Pages, iframe embed for SquareSpace | ✓ Good — 15KB bundle, autocomplete, WCAG 2.1 AA |
| AF-05 superseded | Lightweight widget is not a dashboard; supersedes "no web UI" constraint | ✓ Good — static file server, not interactive UI |
| Census CD119-AIANNH for district mapping | Machine-readable, 119th Congress, area overlap data (CRS R48107 was 118th PDF) | ✓ Good — 550/577 Tribes matched (95.3%) |
| Four-tier crosswalk matching | Normalization + variant generation + substring + fuzzy matching for Tribe-to-district | ✓ Good — overcame 60/577 initial match rate |
| Two-tier award matching | Curated alias table primary + rapidfuzz fallback; false negatives over false positives | ✓ Good — 3,751 aliases with state-overlap validation |
| Pre-cache all data before DOCX gen | Zero API calls during document construction | ✓ Good — 1,184+ cache files, fast render |
| ProgramRelevanceFilter (8-12 per Tribe) | Supersedes AF-04; omitted programs in appendix | ✓ Good — focused packets, complete coverage |
| Batch GC every 25 Tribes | Prevents memory buildup across 592 Tribe batch generation | ✓ Good — stable memory usage |
| Change tracking with state persistence | Per-Tribe JSON state enables "Since Last Packet" diff sections | ✓ Good — 5 change types detected |
| Centralized src/paths.py | Single source of truth for all file paths, imports only pathlib | ✓ Good — 25 constants, 47 consumers |
| Circuit breaker wraps retry loop | Trips only when ALL retries exhausted, not per-attempt | ✓ Good — injectable clock for testing |
| Batch CFDA queries (not per-Tribe) | 70 API calls vs 592; respects rate limits | ✓ Good — 14 CFDAs x 5 FYs |
| Housing authority alias curation | 6 rounds programmatic + curated overrides | ✓ Good — 418 → 451 coverage |
| Area-weighted hazard aggregation | Weighted avg for percentiles, weighted sum for EAL | ✓ Good — dual-CRS (EPSG:5070 + EPSG:3338) |
| 4 document types with air gap | Doc A/C internal, Doc B/D congressional; no strategy leakage | ✓ Good — quality review enforces |
| Regional aggregation (8 regions) | NCA5-based regions with crosscutting region for all 592 | ✓ Good — Doc C/D per region |
| DOM methods for web widget (not innerHTML) | XSS prevention in client-side JavaScript | ✓ Good — security best practice |

## Current State

**v1.0 MVP** shipped 2026-02-09 — policy intelligence pipeline with 4 scrapers, 5 monitors, decision engine, 14-section briefing.
**v1.1 Tribe-Specific Advocacy Packets** shipped 2026-02-10 — per-Tribe DOCX generation for 592 Tribes with award history, hazard profiling, economic impact, congressional delegation, and web distribution widget.
**v1.2 Tech Debt Cleanup + Data Foundation** shipped 2026-02-11 — API resilience, real award/hazard data population, 4 document types with audience differentiation, regional aggregation, quality review, and GitHub Pages deployment. 992 documents generated (384 Doc A + 592 Doc B + 8 Doc C + 8 Doc D). Data completeness: ~87% (up from ~39%).

**Next milestone:** Planning (v1.3 candidates in .planning/milestones/v1.2-REQUIREMENTS.md Future Requirements section)

---
*Last updated: 2026-02-11 after v1.2 milestone completion*
