# TCR Policy Scanner

## What This Is

Automated policy intelligence pipeline for Tribal Climate Resilience advocacy. Scans federal policy sources (Federal Register, Grants.gov, Congress.gov, USASpending), scores relevance against the ATNI program inventory of 16 tracked programs, and generates actionable briefings for Tribal Leaders advocating for FY26 climate resilience funding.

Built for the Affiliated Tribes of Northwest Indians (ATNI) Climate Resilience Committee.

## Core Value

Tribal Leaders get timely, accurate, machine-scored policy intelligence that surfaces federal developments relevant to their climate resilience programs — so they know what changed and what to do about it.

## Requirements

### Validated

- ✓ 4 async scrapers (Federal Register, Grants.gov, Congress.gov, USASpending) with BaseScraper pattern, exponential backoff, 403/429 resilience — existing
- ✓ 5-factor weighted relevance scorer (program_match, tribal_keyword_density, recency, source_authority, action_relevance) with critical boost and Tribal eligibility override — existing
- ✓ Scan-to-scan change detection — existing
- ✓ Knowledge graph builder with typed dataclass schema (ProgramNode, AuthorityNode, FundingVehicleNode, BarrierNode, AdvocacyLeverNode, ObligationNode) — existing
- ✓ Markdown briefing and JSON report generation with CI Dashboard — existing
- ✓ 16 tracked programs with CI scores, Hot Sheets alignment, and 6 status categories (SECURE, STABLE, STABLE_BUT_VULNERABLE, AT_RISK, UNCERTAIN, FLAGGED) — existing
- ✓ Config-driven architecture with domain adaptability — existing
- ✓ GitHub Actions daily scan workflow (weekday 6 AM Pacific) — existing
- ✓ Strategic Framework bridging scanner to FY26 Hot Sheets — existing

### Active

- [x] Pipeline validation — all 4 scrapers validated against live APIs, full pipeline produces real output, CI workflow runs on schedule (Phase 1 complete)
- [ ] Graph builder loads Five Structural Asks from graph_schema.json as AdvocacyLeverNodes with ADVANCES edges
- [ ] IIJA sunset tracker — flag programs approaching FY26 expiration with no reauthorization bill
- [ ] Reconciliation monitor — track House/Senate bills for IRA section 6417 repeal
- [ ] Report enhancements — Five Structural Asks section, Hot Sheets sync indicator, IIJA countdown
- [ ] Tribal consultation tracker — detect DTLLs, consultation notices, EO 13175 signals
- [ ] Hot Sheets sync validation — automated CI vs Hot Sheets comparison after each scan
- [ ] Historical CI trend tracking — score trajectories over time
- [ ] Test suite — unit tests for scorer, graph builder, each scraper normalizer
- [ ] Add 2 new programs (BIA TCR Awards, EPA Tribal Air Quality) to inventory if not already present
- [ ] Reconcile CI statuses per Strategic Framework reclassifications
- [ ] Add reconciliation/repeal trigger keywords to scanner config

### Out of Scope

- Tribal-specific or sensitive data collection — T0 (Open) data only, public federal sources
- Real-time streaming — batch scan architecture, not live feeds
- Non-climate Tribal policy domains — v1 focused on TCR; config-driven design supports future expansion
- Frontend dashboard — CLI and markdown/JSON output for v1

## Context

**Organization:** ATNI Climate Resilience Committee
**Repository:** github.com/atniclimate/TCR-policy-scanner (private)
**TSDF Classification:** T0 (Open) — all data from public federal documents
**Stack:** Python 3.12, aiohttp, python-dateutil, jinja2 — all async
**Server:** GitHub-hosted with Claude Code at /root/.claude/projects/-home-user-TCR-policy-scanner/
**Local workspace:** F:\tcr-policy-scanner

**Pipeline architecture:**
```
Ingest → Normalize → Graph Construction → Analysis → Reporting
```

**Data files:**
- `config/scanner_config.json` — sources, scoring weights, 28 Tribal keywords, 30 action keywords
- `data/program_inventory.json` — 16 programs with CI, advocacy levers, tightened language
- `data/policy_tracking.json` — FY26 positions with 6-tier CI thresholds
- `data/graph_schema.json` — 21 authorities, 14 barriers, 8 funding vehicles, Five Structural Asks

**Strategic reference:** `docs/STRATEGIC-FRAMEWORK.md` — 15-item implementation checklist bridging scanner to Hot Sheets

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
| 6-tier CI status model | Hot Sheets alignment adds SECURE, UNCERTAIN, TERMINATED categories | — Pending |
| Five Structural Asks framework | Cross-cutting advocacy levers from Hot Sheets | — Pending |
| F:\ local workspace | Consolidate development on external drive with full access | ✓ Good |
| Pipeline validates before building | Brownfield project — confirm existing pipeline works with live APIs before adding features | ✓ Phase 1 |
| Grants.gov search2 + aln param | API migrated from /opportunities/search to /api/search2 with aln param | ✓ Phase 1 |
| Federal Register slug agency IDs | API requires string slugs, not numeric IDs | ✓ Phase 1 |

---
*Last updated: 2026-02-09 after Phase 1 completion*
