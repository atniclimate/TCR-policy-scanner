# Deferred Items Inventory (All Milestones)

*Compiled: 2026-02-14 during v1.3 documentation closeout*
*Sources: Milestone audit reports, STATE.md decisions, bug hunt findings, ROADMAP verification reports*

## From v1.0 (Shipped 2026-02-09)

| Item | Origin | Current Status | Resolved By |
|------|--------|----------------|-------------|
| No live scraper integration tests | TEST-01-05 debt | Still deferred | Not addressed in v1.1-v1.3 |
| Hardcoded FY26 dates | Phase 2 debt | Resolved | v1.2 CONF-01 (src/config.py dynamic FY) |
| No retry logic on transient failures | Phase 3 debt | Resolved | v1.2 Phase 11 (circuit breaker pattern) |
| CI history 90-entry cap is arbitrary | Phase 4 design choice | Still deferred | Acceptable; ~3 months daily scans |

## From v1.1 (Shipped 2026-02-10)

| Item | Origin | Current Status | Resolved By |
|------|--------|----------------|-------------|
| Award/hazard caches empty (no real data) | Phase 6 debt | Resolved | v1.2 Phases 12-13 (451 awards, 592 hazards) |
| SquareSpace embed placeholder only | Phase 8 debt | Resolved | v1.2 INTG-06, v1.3 WEB-03 |
| FY26 hardcoded in docx_sections | H-04 tech debt | Resolved | v1.2 dynamic FY via config |
| Document 1/2 naming (pre-Doc A/B/C/D) | Phase 7 convention | Resolved | v1.2 Phase 14 (Doc A/B/C/D system) |
| Template-based DOCX (not programmatic) | Phase 7 consideration | Design decision | Programmatic python-docx chosen; templates not needed |

## From v1.2 (Shipped 2026-02-11)

| Item | Origin | Current Status | Resolved By |
|------|--------|----------------|-------------|
| 4 circuit breaker human E2E verifications | Phase 11 debt | Still deferred | Requires network manipulation testing |
| 141 Tribes with zero awards | Phase 12 coverage gap | Still deferred | Remaining housing authority name gaps |
| 91 placeholder warnings in docs | Phase 14 debt | Still deferred | TBD sections where data fields empty |
| Doc A coverage 384/592 | Phase 14 data constraint | Still deferred | Data completeness limits coverage |
| Non-atomic write_text() for award cache | Phase 12 minor debt | Resolved | v1.3 Phase 18 Marie Kondo hygiene fixes |
| Scraper pagination fixes | Phase 11 scope deferral | Resolved | v1.3 INTEL-02 (all 4 scrapers hardened) |
| Congress.gov bill detail fetching | Phase 11 scope deferral | Resolved | v1.3 INTEL-01 (5 sub-endpoints per bill) |

## From v1.3 (Complete 2026-02-14)

| Item | Origin | Current Status | Details |
|------|--------|----------------|---------|
| VoteNode data structure | DEC-1503-04 | Still deferred | Graph schema VoteNode defined but not populated. Senate.gov lacks structured vote data. Pending reliable Senate API. |
| Voting records integration | DEC-1504-03 | Still deferred | Related to VoteNode. No programmatic source for Senate roll call votes. |
| CYCLOPS-016 (P3) | Phase 18 Wave 2 re-audit | Accepted for launch | URIError on malformed percent-encoded hash fragment (e.g., #tribe=%E0%A4) in docs/web/js/app.js line 209. Console error only, page loads normally without pre-selecting a Tribe. Fix: wrap decodeURIComponent in try/catch. |
| DALE-019 (P3) | Phase 18 Wave 2 re-audit | Accepted for launch | daily-scan.yml uses version-tagged GitHub Actions (checkout@v4, setup-python@v5) while other workflows are SHA-pinned. Low risk since daily scan outputs are not public-facing. Fix: pin to same SHAs as deploy-website.yml. |
| Phase 16 P2/P3 findings (16 P2, 18 P3) | Document quality audit | Partially addressed | 6 P1 all fixed. P2/P3 items documented in outputs/docx_review/ agent JSON files and SYNTHESIS.md. Includes DOCX formatting, content density, visual hierarchy items. |
| Data dictionary | Documentation gap | Not started | 1,817 JSON files across 10 directories with no standalone schema documentation. Pydantic models exist for congressional data. |
| Deployment runbook | Documentation gap | Not started | No consolidated deploy-from-scratch guide for the 3 GitHub Actions workflows, API keys, and GitHub Pages configuration. |
| DOCX layout/presentation redesign | Future milestone candidate | Not started | Primary candidate for next milestone per STATE.md Todos. |
| Extreme weather vulnerability data | Future milestone candidate | Not started | Integration of additional hazard/climate data sources. |
| Climate risk/impact/vulnerability assessments | Future milestone candidate | Not started | Per-Tribe climate risk profiles beyond NRI county-level data. |

## Summary

| Category | Total | Resolved | Still Deferred |
|----------|-------|----------|----------------|
| v1.0 tech debt | 4 | 2 | 2 |
| v1.1 tech debt | 5 | 4 | 1 (design decision) |
| v1.2 tech debt | 7 | 3 | 4 |
| v1.3 accepted items | 4 | 0 | 4 |
| v1.3 documentation gaps | 2 | 0 | 2 |
| Future milestone candidates | 3 | 0 | 3 |
| **Total** | **25** | **9** | **16** |

Of the 16 still-deferred items, 4 are coverage/data constraints (141 zero-award Tribes, 384/592 Doc A, VoteNode, voting records), 2 are low-risk P3 bugs (CYCLOPS-016, DALE-019), 4 are process items (E2E circuit breaker testing, placeholder warnings, Phase 16 P2/P3s, live scraper tests), 3 are future milestone candidates, and 2 are documentation gaps (data dictionary, deployment runbook).

None of the deferred items block v1.3 milestone closure.
