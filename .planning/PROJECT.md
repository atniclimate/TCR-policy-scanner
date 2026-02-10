# TCR Policy Scanner

## What This Is

Automated policy intelligence pipeline for Tribal Climate Resilience advocacy. Scans 4 federal policy sources (Federal Register, Grants.gov, Congress.gov, USASpending), scores relevance against 16 tracked programs, runs 5 threat/signal monitors, classifies advocacy goals via a 5-rule decision engine, and produces a 14-section advocacy intelligence briefing for Tribal Leaders advocating for FY26 climate resilience funding.

Built for the Affiliated Tribes of Northwest Indians (ATNI) Climate Resilience Committee.

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

- [ ] Meeting Prep Packet generator — event-specific advocacy intelligence packets for Tribal leaders
- [ ] Tribe-specific framing — map programs to impacted Tribes/regions using public data
- [ ] Per-program briefs with advocacy talking points templates
- [ ] "Since last meeting" change summaries

### Out of Scope

- Tribal-specific or sensitive data collection — T0 (Open) data only, public federal sources
- Real-time streaming — batch scan architecture, not live feeds
- Non-climate Tribal policy domains — v1 focused on TCR; config-driven design supports future expansion
- Frontend dashboard — CLI and markdown/JSON output for now

## Context

**Organization:** ATNI Climate Resilience Committee
**Repository:** github.com/atniclimate/TCR-policy-scanner (private)
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

**Test suite:** 52 tests (decision engine), 8 data validation checks

## Constraints

- **TSDF T0**: No Tribal-specific data — public federal sources only
- **API keys**: Congress.gov key via CONGRESS_API_KEY env var; SAM key via SAM_API_KEY; no keys in repo
- **Stack**: Python 3.12, async (aiohttp) — maintain existing patterns
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

---
*Last updated: 2026-02-09 after v1.0 milestone*
