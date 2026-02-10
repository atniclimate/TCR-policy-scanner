# TCR Policy Scanner

## What This Is

Automated policy intelligence pipeline for Tribal Climate Resilience advocacy. Scans 4 federal policy sources (Federal Register, Grants.gov, Congress.gov, USASpending), scores relevance against 16 tracked programs, runs 5 threat/signal monitors, classifies advocacy goals via a 5-rule decision engine, and produces advocacy intelligence products for Tribal Leaders advocating for FY26 climate resilience funding. v1.1 adds Tribe-specific congressional advocacy packet generation for all 574 federally recognized Tribes, with per-program award history, hazard profiling, economic impact framing, and congressional delegation mapping — output as print-ready DOCX documents.

Built for the Tribal Climate Resilience program, serving 574+ federally recognized Tribal Nations.

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

### Active

**v1.1 — Tribe-Specific Advocacy Intelligence Packets:**

- [ ] Tribal Registry — 574 federally recognized Tribes with state, location, ecoregion classification (BIA Federal Register data)
- [ ] Congressional Mapping — senators, House representatives, and committee assignments per Tribe (Census TIGER districts + Congress.gov)
- [ ] USASpending Award Matching — per-Tribe per-program funding history from existing scraper (fuzzy Tribal name matching)
- [ ] Hazard Profiling — multi-source Tribe-specific hazard data (FEMA NRI, EPA EJScreen, USFS wildfire risk, NOAA climate projections)
- [ ] Economic Impact Synthesis — BEA regional multipliers, FEMA 4:1 benefit-cost ratios, avoided cost framing per Tribe per program
- [ ] Document 1: FY26 [Tribe Name] Climate Resilience Program Priorities — per-Tribe DOCX with 16 program Hot Sheets, each with Tribe-specific award history, local hazards, district economic impact, congressional delegation, and advocacy language
- [ ] Document 2: FY26 Federal Funding Overview & Strategy — shared DOCX with appropriations landscape, ecoregion strategic priorities, science infrastructure threats, FEMA analysis, cross-cutting framework
- [ ] DOCX Generation Engine — python-docx programmatic document construction (no template files)
- [ ] CLI triggers — batch (all 574 Tribes) and ad-hoc (single Tribe) generation modes
- [ ] Change Tracking — "since last packet" diffs showing what shifted between packet generations

### Out of Scope

- Tribal-specific or sensitive data collection — T0 (Open) data only, public federal sources
- Real-time streaming — batch scan architecture, not live feeds
- Non-climate Tribal policy domains — v1 focused on TCR; config-driven design supports future expansion
- Frontend dashboard — CLI and markdown/JSON output for now

## Context

**Organization:** Tribal Climate Resilience program
**Repository:** private repository
**TSDF Classification:** T0 (Open) — all data from public federal documents
**Stack:** Python 3.12, aiohttp, python-dateutil, jinja2, pytest — all async
**Server:** GitHub-hosted with Claude Code at /root/.claude/projects/-home-user-TCR-policy-scanner/
**Local workspace:** F:\tcr-policy-scanner

**Shipped v1.0 with 4,074 LOC Python across 46 source files.**

**Pipeline architecture:**
```
Ingest (4 scrapers) -> Normalize -> Graph Construction -> Monitors (5) -> Decision Engine -> Reporting (14 sections)
```

**Data files:**
- `config/scanner_config.json` — sources, scoring weights, 46 Tribal keywords, 42 action keywords, monitor config
- `data/program_inventory.json` — 16 programs with CI, advocacy levers, hot_sheets_status, access_type, funding_type
- `data/policy_tracking.json` — FY26 positions with 7-tier CI thresholds
- `data/graph_schema.json` — 20 authorities, 13 barriers, 8 funding vehicles, Five Structural Asks, Trust Super-Node

**Strategic reference:** `docs/STRATEGIC-FRAMEWORK.md` — 15-item implementation checklist bridging scanner to Hot Sheets

**v1.1 reference documents:**
- FY26 TCR Program Priorities — per-Tribe DOCX template with 16 program Hot Sheets (see `C:\Users\PatrickFreeland\Desktop\FY26_TCR_Program_Priorities.docx`)
- FY26 Federal Funding Overview & Strategy — inter-Tribal strategic landscape (see `C:\Users\PatrickFreeland\Desktop\FY26_Federal_Funding_Strategy.docx`)

**v1.1 data sources:**
- BIA Federal Register notice — list of 574 federally recognized Tribes
- Census TIGER — congressional district boundaries for Tribe-to-district mapping
- Congress.gov API — current members, committee assignments (already have API key)
- FEMA National Risk Index — county-level hazard scores for 18 natural hazard types
- EPA EJScreen — environmental justice indicators by geography
- USFS wildfire risk — community wildfire risk data
- NOAA climate projections — regional climate impact data
- BEA regional input-output models — economic multipliers for district-level impact framing
- FEMA benefit-cost ratios — pre-disaster mitigation returns (4:1 standard)

**Test suite:** 52 tests (decision engine), 8 data validation checks

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
| DOCX output (not Markdown) | Congressional offices need printable/shareable documents | — Pending |
| Programmatic DOCX (no template files) | Build document structure in code for full control; no external template dependency | — Pending |
| All 574 Tribes | Program scope serves all federally recognized Tribes nationally | — Pending |
| Multi-source hazard profiling | FEMA NRI + EPA EJScreen + USFS + NOAA gives comprehensive picture | — Pending |
| BEA multipliers for economic impact | Standard federal methodology makes framing defensible | — Pending |
| Scanner generates both documents | Document 1 (per-Tribe) and Document 2 (strategic overview) both auto-generated | — Pending |

## Current Milestone: v1.1 Tribe-Specific Advocacy Packets

**Goal:** Generate per-Tribe congressional advocacy DOCX packets for all 574 federally recognized Tribes, with localized funding data, hazard profiling, economic impact framing, and congressional delegation mapping.

**Target features:**
- Tribal Registry with 574 Tribes mapped to states, ecoregions, and congressional districts
- Per-Tribe DOCX (Document 1) with 16 program Hot Sheets populated with Tribe-specific data
- Shared strategic DOCX (Document 2) with appropriations landscape and ecoregion priorities
- Multi-source hazard profiling (FEMA NRI, EPA EJScreen, USFS, NOAA)
- Economic impact synthesis (USASpending obligations x BEA multipliers + FEMA BCR)
- Congressional delegation mapping with committee assignments
- Batch (all Tribes) and ad-hoc (single Tribe) generation modes
- Change tracking between packet generations

---
*Last updated: 2026-02-10 after v1.1 milestone initialization*
