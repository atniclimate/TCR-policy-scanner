# Project Milestones: TCR Policy Scanner

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
