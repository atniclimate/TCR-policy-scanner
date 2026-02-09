# Claude Code CLI Prompt — TCR Policy Scanner

Use the following prompt when starting a Claude Code CLI session to resume work
on this project. Copy everything between the `---` delimiters.

---

## Prompt

I am working on the **ATNI TCR Policy Scanner** — an automated policy intelligence
pipeline for Tribal Climate Resilience (TCR) FY26 advocacy, used by the Affiliated
Tribes of Northwest Indians (ATNI) Climate Resilience Committee.

**Repository:** `github.com/atniclimate/TCR-policy-scanner`
**Branch:** `main`

### Project Architecture

This is a Python-based DAG pipeline with five stages:

```
Ingest → Normalize → Graph Construction → Analysis → Reporting
```

**Pipeline components:**
- **4 Scrapers** (`src/scrapers/`): Federal Register API, Grants.gov API, Congress.gov API, USASpending.gov API — all inherit from `BaseScraper` with exponential backoff, User-Agent compliance, and 403/429 resilience
- **Relevance Scorer** (`src/analysis/relevance.py`): 5-factor weighted scoring (program_match 0.35, tribal_keyword_density 0.20, recency 0.10, source_authority 0.15, action_relevance 0.20) with critical boost, Tribal eligibility override, and document subtype boost
- **Change Detector** (`src/analysis/change_detector.py`): Scan-to-scan diff detection
- **Knowledge Graph** (`src/graph/`): Typed dataclass schema (ProgramNode, AuthorityNode, FundingVehicleNode, BarrierNode, AdvocacyLeverNode, ObligationNode) with edges (AUTHORIZED_BY, FUNDED_BY, BLOCKED_BY, MITIGATED_BY, OBLIGATED_BY). Two-phase builder: static seed from `data/graph_schema.json` + dynamic enrichment from scraped items via regex pattern matching
- **Report Generator** (`src/reports/generator.py`): 14-section Markdown briefings and JSON output (Executive Summary, Reconciliation Watch, IIJA Countdown, New Developments, Critical Updates, CI Dashboard, FLAGGED, Advocacy Goals, Structural Asks, Barriers, Authorities, Advocacy Levers, CI Score Trends, All Items)
- **Decision Engine** (`src/analysis/decision_engine.py`): 6 advocacy goal classifications (URGENT_STABILIZATION, RESTORE_REPLACE, PROTECT_BASE, DIRECT_ACCESS_PARITY, EXPAND_STRENGTHEN, MONITOR_ENGAGE) via 5 prioritized logic rules with MONITOR_ENGAGE as default fallback
- **5 Monitors** (`src/monitors/`): IIJA sunset, reconciliation, consultation, Hot Sheets, DHS funding cliff
- **GitHub Actions** (`.github/workflows/daily-scan.yml`): Weekday 6 AM Pacific automated scans

### Key Data Files

- `config/scanner_config.json` — Sources, scoring weights, keywords (46 tribal, 42 action), 23 search queries
- `data/program_inventory.json` — **16 tracked programs** with CI scores, statuses, keywords, advocacy levers, access_type, funding_type, and CFDA mappings
- `data/policy_tracking.json` — FY26 positions with CI thresholds (6 statuses: SECURE, STABLE, STABLE_BUT_VULNERABLE, AT_RISK, UNCERTAIN, FLAGGED)
- `data/graph_schema.json` — Static authorities (21), funding vehicles (8), barriers (14), and Five Structural Asks (cross-cutting advocacy levers)
- `docs/STRATEGIC-FRAMEWORK.md` — Framework bridging scanner architecture to FY26 Hot Sheets congressional advocacy brief

### Current State (as of Feb 2026)

**Programs (16):**
- 3 Critical: BIA TCR (STABLE, CI:88%), FEMA BRIC (FLAGGED, CI:12%), IRS Elective Pay (AT_RISK, CI:55%)
- 11 High: EPA STAG (STABLE, 90%), EPA GAP (STABLE, 80%), Tribal Air Quality (STABLE, 82%), BIA TCR Awards (STABLE, 85%), FEMA Mitigation Plans (AT_RISK, 65%), DOT PROTECT (SECURE, 93%), USDA Wildfire (VULNERABLE, 78%), DOE Indian Energy (UNCERTAIN, 55%), HUD IHBG (STABLE, 85%), NOAA Tribal (UNCERTAIN, 50%), FHWA TTP (STABLE, 85%)
- 2 Medium: WaterSMART (UNCERTAIN, 60%), TAP (STABLE, 75%)

**Scraper strategies:**
- Federal Register: Term search + agency ID sweep (11 agency IDs) + document subtype detection (ICR, guidance, RFI, ANPRM)
- Grants.gov: 12 CFDA-targeted queries (incl. 10.720 USDA Wildfire, 20.284 DOT PROTECT) + keyword broad sweep + Tribal eligibility override (codes 06, 07, 11) + zombie CFDA detection
- Congress.gov: 11 legislative queries for 119th Congress (HR/S bill types)
- USASpending: CFDA-based obligation tracking for FY26

**Graph schema features:**
- Five Structural Asks (cross-cutting AdvocacyLeverNodes): Multi-Year Funding, Match Waivers, Direct Tribal Access, Consultation Compliance, Data Sovereignty
- IIJA sunset barrier tracking (4+ programs affected)
- Reconciliation repeal barrier for IRS Elective Pay

**Recent Hot Sheets sync:**
- Added 2 new programs: BIA TCR Awards, EPA Tribal Air Quality
- Reclassified IRS Elective Pay from STABLE to AT_RISK (reconciliation threat)
- Reclassified DOT PROTECT from STABLE to SECURE (statutory set-aside)
- Introduced SECURE, UNCERTAIN status categories
- Added CI scores for all 16 programs (no gaps)

### Priority Next Steps

**Completed in v1:**
- ~~Graph builder enhancement~~ (structural asks, ADVANCES edges) -- Phase 2
- ~~IIJA sunset tracker~~ -- Phase 3
- ~~Reconciliation monitor~~ -- Phase 3
- ~~Tribal consultation tracker~~ -- Phase 3
- ~~Report enhancements~~ (14-section briefings, Hot Sheets sync, IIJA Countdown) -- Phase 4
- ~~Historical CI trends~~ -- Phase 4
- ~~Test suite~~ (52 tests) -- all phases

**Remaining v2 priorities:**
1. **Hot Sheets sync validation**: Automated comparison between scanner CI and Hot Sheets positions after each scan
2. **Cross-program correlation analysis**: Identify funding/policy linkages across programs
3. **Repository restructure and packaging**: Clean up for distribution and deployment
4. **SAM.gov scraper implementation**: Add contract opportunity tracking

### Key Constraints

- **TSDF: T0 (Open)** — All data is public federal data; no Tribal-specific or sensitive data
- **No API keys in repo** — Congress.gov key via `CONGRESS_API_KEY` env var; SAM key via `SAM_API_KEY`
- **Config-driven design** — Architecture supports domain adaptability via `domain`/`domain_name` config fields
- Python 3.13, dependencies: aiohttp, python-dateutil, jinja2
- All scrapers are async (aiohttp)

Please read `docs/STRATEGIC-FRAMEWORK.md` and the `data/` files first to understand the full context before making changes. The framework document contains a detailed implementation checklist.

---

*Copy the prompt above into your Claude Code CLI session to resume work on this project.*
