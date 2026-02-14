# Roadmap: TCR Policy Scanner

## Milestones

- v1.0 MVP - Phases 1-4 (shipped 2026-02-09)
- v1.1 Tribe-Specific Advocacy Packets - Phases 5-8 (shipped 2026-02-10)
- v1.2 Tech Debt Cleanup + Data Foundation - Phases 9-14 (shipped 2026-02-11)
- **v1.3 Production Launch** - Phases 15-18 (in progress)

## Phases

<details>
<summary>v1.0 MVP (Phases 1-4) - SHIPPED 2026-02-09</summary>

See `.planning/milestones/v1.0-ROADMAP.md` for phase details.
4 phases, 9 plans, 30 requirements validated.

</details>

<details>
<summary>v1.1 Tribe-Specific Advocacy Packets (Phases 5-8) - SHIPPED 2026-02-10</summary>

See `.planning/milestones/v1.1-ROADMAP.md` for phase details.
4 phases, 17 plans, 22 requirements validated.

</details>

<details>
<summary>v1.2 Tech Debt Cleanup + Data Foundation (Phases 9-14) - SHIPPED 2026-02-11</summary>

See `.planning/milestones/v1.2-ROADMAP.md` for phase details.
6 phases, 20 plans, 24 requirements validated.

</details>

---

## v1.3 Production Launch

**Milestone Goal:** Ship a production-ready website delivering real DOCX advocacy packets to 592 Tribal Nations, backed by reliable scrapers, congressional intelligence, and trustworthy document quality. Target: 100-200 concurrent users over 48-hour launch window.

**Depth:** Quick (4 phases)
**Requirements:** 39 across 5 categories (INTEL, DOCX, WEB, HARD, XCUT)
**Architecture:** 4-phase agent swarm pipeline -- each phase uses parallel agents with defined territories

**Critical path:** Congressional intelligence pipeline (Phase 15) --> Document quality assurance (Phase 16) --> Website deployment (Phase 17) --> Production hardening (Phase 18)

---

### Phase 15: Congressional Intelligence Pipeline

**Goal**: Tribal Leaders receive advocacy packets enriched with complete congressional intelligence -- bill tracking, delegation data, committee activity, and confidence-scored sections -- backed by scrapers that paginate to completion with zero silent data loss

**Depends on**: Phase 14 (v1.2 shipped)

**Requirements**: INTEL-01, INTEL-02, INTEL-03, INTEL-04, INTEL-05, INTEL-06, INTEL-07, INTEL-08, INTEL-09, INTEL-10, INTEL-11, INTEL-12, INTEL-13, INTEL-14, INTEL-15, XCUT-01, XCUT-02, XCUT-03

**Agent Swarm:** Sovereignty Scout, Fire Keeper, River Runner, Horizon Walker
**Swarm trigger:** `F:\tcr-policy-scanner\.planning\TRIGGER-PROMPT-V1.3.md`

| Agent | File | Territory |
|-------|------|-----------|
| Sovereignty Scout | `F:\tcr-policy-scanner\.planning\sovereignty-scout.md` | `src/scrapers/`, `data/`, `config/`, `scripts/` |
| Fire Keeper | `F:\tcr-policy-scanner\.planning\fire-keeper.md` | `src/` (non-scraper), `src/packets/`, `src/models/` |
| River Runner | `F:\tcr-policy-scanner\.planning\river-runner.md` | `tests/`, `validate_data_integrity.py`, `.github/workflows/` |
| Horizon Walker | `F:\tcr-policy-scanner\.planning\horizon-walker.md` | `docs/`, `.planning/` |

**Coordination rule:** Scout and Fire Keeper must agree on data model BEFORE either builds.

**Success Criteria** (what must be TRUE):
  1. All 4 scrapers (Federal Register, Grants.gov, Congress.gov, USASpending) paginate to completion -- running a scan logs `fetched == total` for every source, or an explicit WARNING with gap count; zero silent truncation
  2. A Tribal Leader's DOCX packet contains congressional intelligence sections (delegation, relevant bills, committee activity) in all 4 doc types, with Doc A including strategy/talking points and Doc B containing facts only
  3. Every DOCX section displays a confidence indicator (HIGH/MEDIUM/LOW) derived from source weights and freshness decay, and zero numeric confidence scores appear in any rendered document
  4. The test suite exceeds 900 total tests, including pagination tests for all 4 scrapers, congressional model validation, and an end-to-end trace from `congressional_intel.json` through DOCX rendering
  5. Air gap compliance passes (`grep -rn` returns zero hits for ATNI, NCAI, or tool name references), zero third-party tracking exists, and v1.2 Four Fixes remain clean

**Plans:** 7 plans in 4 waves

Plans:
- [x] 15-01-PLAN.md -- Data model contract: Pydantic models, context extension, confidence scoring, KG schema (Wave 1, Fire Keeper)
- [x] 15-02-PLAN.md -- Scraper pagination hardening: all 4 scrapers paginate to completion (Wave 1, Sovereignty Scout)
- [x] 15-03-PLAN.md -- Documentation: alert system spec, integration map, KG spec, data roadmap (Wave 1, Horizon Walker)
- [x] 15-04-PLAN.md -- Bill detail fetcher + bill-to-program mapping + config (Wave 2, Sovereignty Scout)
- [x] 15-05-PLAN.md -- DOCX renderers + orchestrator wiring + regional sections (Wave 3, Fire Keeper)
- [x] 15-06-PLAN.md -- Test suite: models, pagination, confidence, rendering (Wave 4, River Runner)
- [x] 15-07-PLAN.md -- E2E test + CI pipeline + XCUT compliance verification (Wave 4, River Runner)

---

### Phase 16: Document Quality Assurance

**Goal**: Every document in the 992-document corpus is structurally valid, content-accurate, and pipeline-verified -- confirmed by 5 independent audit agents whose findings are machine-readable and traceable to specific quality dimensions

**Depends on**: Phase 15 (congressional content must exist before auditing documents)

**Requirements**: DOCX-01, DOCX-02, DOCX-03, DOCX-04, DOCX-05, DOCX-06

**Agent Swarm:** 5 parallel READ-ONLY audit agents

| Agent | File | Audits |
|-------|------|--------|
| Design Aficionado | `F:\tcr-policy-scanner\.planning\design-aficionado.md` | `docx_styles.py` (269 LOC), `docx_template.py` (572 LOC), `hot_sheet_template.docx` |
| Accuracy Agent | `F:\tcr-policy-scanner\.planning\accuracy-agent.md` | `docx_hotsheet.py` (803 LOC), `docx_sections.py` (973 LOC), `docx_regional_sections.py` (494 LOC) |
| Pipeline Surgeon | `F:\tcr-policy-scanner\.planning\pipeline-surgeon.md` | `orchestrator.py` (1,071 LOC), `context.py` (74 LOC), `economic.py` (382 LOC), `relevance.py` (330 LOC) |
| Gatekeeper | `F:\tcr-policy-scanner\.planning\gatekeeper.md` | `agent_review.py` (434 LOC), `quality_review.py` (473 LOC), `doc_types.py` (198 LOC) |
| Gap Finder | `F:\tcr-policy-scanner\.planning\gap-finder.md` | All test files + source coverage mapping |

**Priority hierarchy:** accuracy > audience > political > design > copy
**Output:** `outputs/docx_review/{agent}_findings.json` per agent

**Success Criteria** (what must be TRUE):
  1. The structural validation script checks all 992 documents in under 60 seconds and reports heading hierarchy, table population, page count ranges, placeholder absence, font consistency, and broken image status per document
  2. Dollar amounts in rendered DOCX trace to source data files (award cache, economic calculations), Tribe names match federal register spelling, and program names match the inventory
  3. Quality gates enforce priority hierarchy (accuracy > audience > political > design > copy), MAX_PAGES limits, air gap regex patterns, and zero audience leakage between internal (Doc A/C) and congressional (Doc B/D) documents
  4. A test coverage gap analysis maps function-level coverage, identifies untested edge cases across all 4 doc types, and produces actionable findings in machine-readable JSON

**Plans:** 2 plans in 2 waves

Plans:
- [x] 16-01-PLAN.md -- Wave 1 Audit: structural validation script + 5 parallel audit agents (DOCX-01 through DOCX-06)
- [x] 16-02-PLAN.md -- Wave 2 Fix + Verify: fix P0/P1 defects, add critical tests, re-validate, produce SYNTHESIS.md quality certificate

---

### Phase 17: Website Deployment

**Goal**: Any of 592 Tribal Nations can visit the website, search for their Nation by name (with typo tolerance), and download real DOCX advocacy packets -- served from GitHub Pages, embeddable in SquareSpace, accessible via keyboard and screen reader, and performant on mobile devices

**Depends on**: Phase 16 (verified DOCX must exist before website distributes them)

**Requirements**: WEB-01, WEB-02, WEB-03, WEB-04, WEB-05, WEB-06, WEB-07, WEB-08, WEB-09, WEB-10

**Agent Swarm:** 4 parallel review agents
**Swarm trigger:** `F:\tcr-policy-scanner\.planning\LAUNCH-SWARM.md`

| Agent | File | Focus |
|-------|------|-------|
| Web Wizard | via `F:\tcr-policy-scanner\.planning\LAUNCH-SWARM.md` | Performance, build optimization, SquareSpace compatibility |
| Mind Reader | via `F:\tcr-policy-scanner\.planning\LAUNCH-SWARM.md` | UX/UI, accessibility, WCAG 2.1 AA |
| Keen Kerner | via `F:\tcr-policy-scanner\.planning\LAUNCH-SWARM.md` | Typography, type scale, letter-spacing, readability |
| Pipeline Professor | via `F:\tcr-policy-scanner\.planning\LAUNCH-SWARM.md` | Data pipeline, deployment, SquareSpace integration |

**Stack:** Enhanced vanilla HTML/JS/CSS + Fuse.js 7.1.0 (self-hosted)
**Output:** `outputs/website_review/SYNTHESIS.md`

**Success Criteria** (what must be TRUE):
  1. A Tribal staff member can type a misspelled Tribe name into the search box and find their Nation via fuzzy matching across all 592 federally recognized Tribes (not 46 hardcoded mocks), then download a real DOCX file that opens in Microsoft Word
  2. The website renders correctly in a SquareSpace iframe with `sandbox="allow-scripts allow-same-origin allow-downloads allow-popups"`, and downloads complete successfully from within the embedded context
  3. The deployed bundle is under 500KB gzipped, Core Web Vitals pass (LCP <2.5s, CLS <0.1), and the site loads correctly on iOS Safari (375px) and Android Chrome (360px) with 44px minimum touch targets
  4. WCAG 2.1 AA compliance is verified: keyboard-only search-to-download flow works, ARIA combobox roles are present, color contrast meets 4.5:1, and `prefers-reduced-motion` is respected
  5. GitHub Pages deployment pipeline automates build, asset deployment, manifest generation, and SPA routing, triggered on merge to main

**Plans:** 5 plans in 3 waves

Plans:
- [x] 17-01-PLAN.md -- Data pipeline: build_web_index.py alias embedding + Fuse.js self-hosting (Wave 1)
- [x] 17-02-PLAN.md -- HTML + CSS: ARIA combobox markup, dark mode, CRT effect, type scale, mobile (Wave 1)
- [x] 17-03-PLAN.md -- JavaScript: ARIA combobox + Fuse.js search + state filter + card rendering (Wave 2)
- [x] 17-04-PLAN.md -- Deployment: deploy-website.yml + generate-packets.yml update + manifest (Wave 2)
- [x] 17-05-PLAN.md -- Review: 4-agent website review synthesis + human verification (Wave 3)

---

### Phase 18: Production Hardening

**Goal**: The complete system -- scrapers, documents, website, and deployment -- passes a 4-agent adversarial review with zero P0 critical issues, confirming it is ready for 100-200 concurrent Tribal users during a 48-hour launch window

**Depends on**: Phase 17 (deployed website must exist before adversarial testing)

**Requirements**: HARD-01, HARD-02, HARD-03, HARD-04, HARD-05

**Agent Swarm:** 4 bug hunt agents

| Agent | File | Method | Checklist |
|-------|------|--------|-----------|
| Cyclops | `F:\tcr-policy-scanner\.planning\cyclops.md` | Deep code inspection (reads source) | 15 items |
| Dale Gribble | `F:\tcr-policy-scanner\.planning\dale-gribble.md` | Security & sovereignty audit (reads source + web) | 18 items |
| Mr. Magoo | `F:\tcr-policy-scanner\.planning\mr-magoo.md` | Experiential testing (does NOT read source) | 12 items |
| Marie Kondo | `F:\tcr-policy-scanner\.planning\marie-kondo.md` | Code hygiene & minimization (reads source) | TBD |

**Gate:** Go/no-go launch decision based on combined findings
**Output:** `outputs/bug_hunt/{agent}_findings.json`

**Success Criteria** (what must be TRUE):
  1. Cyclops deep code inspection finds zero unhandled boundary conditions, race conditions, or resource leaks across the 15-item checklist -- including GitHub Pages fallback, special characters in Tribe names, manifest staleness, and search race conditions
  2. Dale Gribble security audit confirms zero third-party tracking (no Google Analytics, no Google Fonts CDN, no cookies), CSP headers block external requests, source maps are excluded from production, and the full 18-item UNDRIP/OCAP/CARE checklist passes
  3. Mr. Magoo experiential testing (navigating as a non-technical Tribal staff member without reading source code) reports a trust_score of 7+ out of 10 across the 12-item user experience checklist, with zero download failures and zero confusing UI states
  4. Go/no-go launch decision confirms zero P0 critical issues, all P1 issues have documented workarounds, and the combined agent assessment supports a 100-200 concurrent user launch

**Plans:** 6 plans in 6 waves

Plans:
- [x] 18-01-PLAN.md -- Pre-flight fixes (inherited P1/P2/P3) + 4-agent adversarial audit (Wave 1)
- [x] 18-02-PLAN.md -- Fix P0/P1 findings + apply low-risk Marie Kondo hygiene + re-verify (Wave 2)
- [x] 18-03-PLAN.md -- Initial synthesis report + human go/no-go checkpoint (Wave 3) -- NO-GO, fix P2/P3
- [x] 18-04-PLAN.md -- Fix all actionable P2/P3 findings: UX, security, code hygiene (Wave 4)
- [x] 18-05-PLAN.md -- 4-agent re-audit validating P2/P3 fixes (Wave 5)
- [x] 18-06-PLAN.md -- Updated synthesis + final go/no-go launch decision (Wave 6)

---

## Progress

**Execution Order:** 15 --> 16 --> 17 --> 18

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-4 | v1.0 | 9/9 | Complete | 2026-02-09 |
| 5-8 | v1.1 | 17/17 | Complete | 2026-02-10 |
| 9-14 | v1.2 | 20/20 | Complete | 2026-02-11 |
| 15 - Congressional Intelligence | v1.3 | 7/7 | Complete | 2026-02-12 |
| 16 - Document Quality | v1.3 | 2/2 | Complete | 2026-02-12 |
| 17 - Website Deployment | v1.3 | 5/5 | Complete | 2026-02-12 |
| 18 - Production Hardening | v1.3 | 6/6 | Complete | 2026-02-14 |

## Coverage

```
INTEL-01 -> Phase 15
INTEL-02 -> Phase 15
INTEL-03 -> Phase 15
INTEL-04 -> Phase 15
INTEL-05 -> Phase 15
INTEL-06 -> Phase 15
INTEL-07 -> Phase 15
INTEL-08 -> Phase 15
INTEL-09 -> Phase 15
INTEL-10 -> Phase 15
INTEL-11 -> Phase 15
INTEL-12 -> Phase 15
INTEL-13 -> Phase 15
INTEL-14 -> Phase 15
INTEL-15 -> Phase 15
DOCX-01  -> Phase 16
DOCX-02  -> Phase 16
DOCX-03  -> Phase 16
DOCX-04  -> Phase 16
DOCX-05  -> Phase 16
DOCX-06  -> Phase 16
WEB-01   -> Phase 17
WEB-02   -> Phase 17
WEB-03   -> Phase 17
WEB-04   -> Phase 17
WEB-05   -> Phase 17
WEB-06   -> Phase 17
WEB-07   -> Phase 17
WEB-08   -> Phase 17
WEB-09   -> Phase 17
WEB-10   -> Phase 17
HARD-01  -> Phase 18
HARD-02  -> Phase 18
HARD-03  -> Phase 18
HARD-04  -> Phase 18
HARD-05  -> Phase 18
XCUT-01  -> Phase 15
XCUT-02  -> Phase 15
XCUT-03  -> Phase 15

Mapped: 39/39
Orphaned: 0
Duplicates: 0
```

---
*Created: 2026-02-12 for v1.3 Production Launch*
