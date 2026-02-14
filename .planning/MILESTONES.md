# Project Milestones: TCR Policy Scanner

## v1.3 Production Launch (Complete: 2026-02-14)

**Delivered:** Congressional intelligence pipeline with bill tracking, CFDA-to-program mapping, committee activity monitoring, and confidence scoring; 5-agent document quality assurance audit with 992-document structural validation; production website with Fuse.js fuzzy search, ARIA combobox, dark mode, mobile responsive layout, and SquareSpace iframe embedding; 4-agent adversarial hardening with 2-round audit cycle (initial NO-GO, full P2/P3 remediation, re-audit confirming GO). Trust 9/10, Joy 9/10, zero P0/P1/P2 remaining.

**Phases completed:** 15-18 (20 plans total)

**Key accomplishments:**

- Built congressional intelligence pipeline: Congress.gov bill detail fetcher (5 sub-endpoints), 4-component relevance scoring (subject 0.30, CFDA 0.25, committee 0.20, keyword 0.25), confidence scoring with exponential freshness decay (~69-day half-life), audience-differentiated rendering across all 4 doc types
- Hardened all 4 scrapers for full pagination with safety caps (Congress.gov 2500, Federal Register 20 pages, Grants.gov 1000, USASpending 5000) and zero silent truncation
- Ran 5-agent document quality audit on 992 DOCX corpus: 40 findings (0 P0, 6 P1 all fixed), structural validation at ~208ms/doc, WCAG contrast fix (amber #B45309, 4.6:1), quality gate default enabled
- Deployed production website: vanilla HTML/JS/CSS + Fuse.js 7.1.0 (65KB gzipped), ARIA combobox, state filtering, freshness badges, hash-based deep linking, CSP + SRI security, privacy footer, SquareSpace iframe embedding
- Executed 4-agent adversarial hardening (Cyclops, Dale Gribble, Mr. Magoo, Marie Kondo) across 6 waves: 70 findings, 38 fixed, 23 confirmed safe, NO-GO decision followed by full remediation and re-audit to GO
- Achieved CARE/OCAP/UNDRIP sovereignty compliance with zero third-party tracking, zero cookies, zero external CDN dependencies

**Stats:**

- 102 Python files (54 src + 33 tests + 14 scripts + 1 root), ~38,300 lines of Python (src + tests)
- 4 phases, 20 plans, 39 requirements (38 satisfied + 1 conditional)
- 964 tests (221 new: congressional models, pagination, confidence, rendering, E2E, XCUT compliance)
- 36 key decisions documented (DEC-1501-01 through DEC-1806-01)
- 4 agent swarms deployed (17 total agent roles across territory, audit, review, and adversarial modes)
- Trust score 9/10, Joy score 9/10, Sovereignty assessment COMPLIANT + IMPROVED
- 3 days from v1.2 ship to v1.3 completion (2026-02-12 to 2026-02-14)

**Git range:** `8f96850` (v1.2 end) -> `e8a4aba` (v1.3 end)

**What's next:** Planning next milestone. Candidates: DOCX layout/presentation redesign, extreme weather vulnerability data, climate risk/impact/vulnerability assessments per Tribe.

---

## v1.2 Tech Debt Cleanup + Data Foundation (Shipped: 2026-02-11)

**Delivered:** Eliminated tech debt, added API resilience with circuit breakers and cache fallback, populated real USASpending award data (451/592 Tribes) and FEMA NRI hazard profiles (592/592 Tribes), built 4-document-type system with audience differentiation and air gap enforcement, regional aggregation across 8 regions, quality review automation, and GitHub Pages deployment — producing 992 data-backed advocacy documents.

**Phases completed:** 9-14 (20 plans total)

**Key accomplishments:**

- Centralized all file paths in src/paths.py (25 constants, 47 files migrated) and achieved ruff-clean codebase
- Built circuit breaker pattern (CLOSED/OPEN/HALF_OPEN) with configurable retry/backoff and cache fallback for API resilience across all 4 scrapers
- Populated award caches for 451/592 Tribes (76.2%) via batch CFDA queries and 6-round housing authority alias curation (18,776 total aliases)
- Populated hazard profiles for all 592 Tribes with area-weighted FEMA NRI data (dual-CRS crosswalk) and USFS wildfire risk override
- Built 4-document-type system (Doc A/B/C/D) with audience differentiation, air gap enforcement, and quality review automation
- Deployed regional aggregation (8 NCA5 regions), data validation, and GitHub Pages with production URLs

**Stats:**

- 95 Python source files, ~37,900 lines of Python (src + tests)
- 6 phases, 20 plans, 24 requirements
- 743 tests (456 new: circuit breaker, hazard aggregation, audience filtering, regional, quality review, etc.)
- 97 commits, 1,368 files changed (+194,056 / -57,448 lines, includes 1,184+ regenerated data cache files)
- 1 day from v1.1 ship to v1.2 ship (2026-02-11)
- 4 research agents deployed (Sovereignty Scout, Fire Keeper, River Runner, Horizon Walker)

**Git range:** `bcd6635` (v1.1 end) -> `8f96850` (v1.2 end)

**What's next:** Planning v1.3 (congressional alerts, confidence scoring, scraper pagination)

---

## v1.0 MVP (Shipped: 2026-02-09)

**Delivered:** Automated policy intelligence pipeline scanning 4 federal APIs, scoring relevance against 16 Tribal climate resilience programs, running 5 threat/signal monitors, classifying advocacy goals, and producing a 14-section advocacy intelligence briefing for Tribal Leaders.

**Phases completed:** 1-4 (9 plans total)

**Key accomplishments:**

- Validated 4 live federal API scrapers (Federal Register, Grants.gov, Congress.gov, USASpending) with graceful degradation
- Built enriched knowledge graph with 79 static nodes (programs, authorities, barriers, structural asks, trust super-node) and 118 typed edges
- Deployed 5 active monitors: IIJA sunset, reconciliation, DHS funding cliff, Tribal consultation, Hot Sheets sync validation
- Implemented 5-rule priority-ordered advocacy decision engine with 52 TDD tests
- Delivered 14-section advocacy intelligence briefing with CI trends, structural asks, IIJA countdown, reconciliation watch, and advocacy goal classifications
- Automated daily scans via GitHub Actions (weekday 6 AM Pacific)

**Stats:**

- 46 source files created/modified
- 4,074 lines of Python (src + tests)
- 4 phases, 9 plans, 30 requirements
- 2 days from start to ship (2026-02-08 to 2026-02-09)
- 3 code review passes applied (structural, domain, documentation)

**Git range:** `38f3821` (initial upload) -> `8491e66` (pass 3 docs)

**What's next:** v1.1 Tribe-Specific Advocacy Packets (shipped 2026-02-10)

---

## v1.1 Tribe-Specific Advocacy Packets (Shipped: 2026-02-10)

**Delivered:** Per-Tribe congressional advocacy DOCX packet generation for all 592 federally recognized Tribes, with localized USASpending award history, FEMA/USFS hazard profiling, economic impact framing, congressional delegation mapping, and a GitHub Pages search widget for distribution.

**Phases completed:** 5-8 (17 plans total)

**Key accomplishments:**

- Built 592-Tribe registry from EPA API with ecoregion classification and many-to-many congressional delegation mapping (Census CD119-AIANNH + Congress.gov API)
- Implemented two-tier USASpending award matching (3,751-entry alias table + rapidfuzz >= 85 with state-overlap validation) with per-Tribe JSON caches
- Created multi-source hazard profiling (FEMA NRI 18 hazard types + USFS wildfire risk) cached for all 592 Tribes
- Built professional DOCX generation engine (DocxEngine + StyleManager + HotSheetRenderer) with programmatic python-docx construction and economic impact synthesis
- Assembled complete Document 1 (per-Tribe, 592 variants with 8-section layout) and Document 2 (strategic overview with 7 sections) with batch + ad-hoc CLI modes
- Deployed 15KB GitHub Pages search widget with Tribe autocomplete and DOCX download, embeddable via SquareSpace iframe

**Stats:**

- 52 Python source files, 18,546 lines of Python (src + tests)
- 4 phases, 17 plans, 22 requirements
- 287 tests (31 + 23 + 108 + 73 + 52 baseline)
- 87 commits, 1,314 files changed (includes 1,184+ data cache files)
- 2 days from v1.0 ship to v1.1 ship (2026-02-09 to 2026-02-10)
- 1 systemic review (9-agent, 3-wave, 40 findings triaged, 10 fixes applied)

**Git range:** `8491e66` (v1.0 end) -> `bcd6635` (v1.1 end)

**What's next:** Planning next milestone.

---
