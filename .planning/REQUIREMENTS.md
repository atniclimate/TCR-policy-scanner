# v1.3 Production Launch — Requirements

## Overview

39 requirements across 5 categories, organized by the 4-phase agent swarm architecture.
Phase numbering continues from 14 (v1.2 ended at phase 14; v1.3 starts at phase 15).

**Milestone goal:** Ship a production-ready website delivering real DOCX advocacy packets
to 592 Tribal Nations, backed by reliable scrapers, congressional intelligence, and
trustworthy document quality. Target: 100-200 concurrent users over 48-hour launch window.

---

## v1 Requirements

### Congressional Intelligence (INTEL)

**Agent swarm:** Sovereignty Scout, Fire Keeper, River Runner, Horizon Walker
**Swarm trigger:** `F:\tcr-policy-scanner\.planning\TRIGGER-PROMPT-V1.3.md`
**Agent definitions:**
| Agent | File | Territory |
|-------|------|-----------|
| Sovereignty Scout | `F:\tcr-policy-scanner\.planning\sovereignty-scout.md` | `src/scrapers/`, `data/`, `config/`, `scripts/` |
| Fire Keeper | `F:\tcr-policy-scanner\.planning\fire-keeper.md` | `src/` (non-scraper), `src/packets/`, `src/models/` |
| River Runner | `F:\tcr-policy-scanner\.planning\river-runner.md` | `tests/`, `validate_data_integrity.py`, `.github/workflows/` |
| Horizon Walker | `F:\tcr-policy-scanner\.planning\horizon-walker.md` | `docs/`, `.planning/` |

**Coordination rule:** Scout and Fire Keeper must agree on data model BEFORE either builds.

- [x] **INTEL-01**: Congress.gov bill detail fetcher returns complete records with sponsors, committees, actions, subjects, and text URLs for Tribal-relevant legislation in the 119th Congress
- [x] **INTEL-02**: All 4 scrapers (Federal Register, Grants.gov, Congress.gov, USASpending) paginate to completion with zero silent truncation — `fetched == total` or explicit WARNING logged with gap count
- [x] **INTEL-03**: Congressional-to-program mapping links bills to tracked program ALNs with relevance scores (0.0-1.0), action types, and urgency ratings, output as `congressional_intel.json`
- [x] **INTEL-04**: Delegation data enhanced with live committee assignments, voting records on Tribal-relevant legislation, and co-sponsorship of tracked bills
- [x] **INTEL-05**: Congressional Pydantic models (Legislator, VoteRecord, BillIntelligence, BillAction, CongressionalIntelReport) validate all Scout output as the contract between ingestion and rendering
- [x] **INTEL-06**: TribePacketContext extended with CongressionalContext (delegation, relevant_bills, committee_activity, appropriations_status, scan_date, confidence)
- [x] **INTEL-07**: DOCX section renderers produce congressional content for all 4 doc types: Doc A (delegation + bills + talking points + timing), Doc B (delegation + bills, facts only, zero strategy), Doc C/D (regional aggregation)
- [x] **INTEL-08**: Confidence scoring system produces per-section scores using source weights (congress_gov_api: 1.0 down to inferred: 0.50) and freshness decay (today: 1.0 down to 365 days: 0.30)
- [x] **INTEL-09**: Pagination tests for all 4 scrapers and congressional model validation tests against real API response shapes reach 900+ total test count (from 743)
- [x] **INTEL-10**: End-to-end pipeline test traces congressional data from `congressional_intel.json` through context building through DOCX rendering through structural validation for all 4 doc types
- [x] **INTEL-11**: CI pipeline extended with congressional intelligence scan and DOCX validation in GitHub Actions workflows
- [x] **INTEL-12**: Congressional alert system architecture fully specified in ENH-001 with change detection engine, alert classification (CRITICAL/HIGH/MEDIUM/LOW), per-Tribe routing, and 21 story points decomposed across 3 sprints
- [x] **INTEL-13**: v1.3 Phase Integration Map documents every handoff from Congress.gov API through DOCX agents through website agents through bug hunters to Tribal Leader's hands
- [x] **INTEL-14**: Knowledge graph schema extended with congressional nodes (Bill, Legislator, Committee, Vote) and edges (AFFECTS_PROGRAM, SPONSORED_BY, REFERRED_TO, REPRESENTS, VOTED_ON, MEMBER_OF) with query examples in ENH-002
- [x] **INTEL-15**: Data completeness roadmap updated with congressional sources, confidence scores per program, and gap prioritization across all 8 data sources

### Document Quality (DOCX)

**Agent swarm:** 5 parallel READ-ONLY audit agents
**Agent definitions:**
| Agent | File | Audits |
|-------|------|--------|
| Design Aficionado | `F:\tcr-policy-scanner\.planning\design-aficionado.md` | `docx_styles.py` (269 LOC), `docx_template.py` (572 LOC), `hot_sheet_template.docx` |
| Accuracy Agent | `F:\tcr-policy-scanner\.planning\accuracy-agent.md` | `docx_hotsheet.py` (803 LOC), `docx_sections.py` (973 LOC), `docx_regional_sections.py` (494 LOC) |
| Pipeline Surgeon | `F:\tcr-policy-scanner\.planning\pipeline-surgeon.md` | `orchestrator.py` (1,071 LOC), `context.py` (74 LOC), `economic.py` (382 LOC), `relevance.py` (330 LOC) |
| Gatekeeper | `F:\tcr-policy-scanner\.planning\gatekeeper.md` | `agent_review.py` (434 LOC), `quality_review.py` (473 LOC), `doc_types.py` (198 LOC) |
| Gap Finder | `F:\tcr-policy-scanner\.planning\gap-finder.md` | All test files + source coverage mapping |

**Priority hierarchy:** accuracy > audience > political > design > copy
**Output:** `outputs/docx_review/{agent}_findings.json` per agent

- [x] **DOCX-01**: DOCX structural validation script (`scripts/validate_docx_structure.py`) checks heading hierarchy, table population, page count ranges, Tribe name in header, placeholder text absence, font consistency, and broken images across all 992 documents (208s at ~208ms/doc; DEC-1601-01 relaxed 60s budget)
- [x] **DOCX-02**: Design & layout audit identifies color/contrast issues, font size hierarchy violations, style system integrity gaps, and template pre-baking problems across all 4 doc types
- [x] **DOCX-03**: Content accuracy verification confirms dollar amounts trace to source data, Tribe names match federal register spelling, program names match inventory, and congressional data freshness matches scan_date
- [x] **DOCX-04**: Pipeline integrity audit verifies TribePacketContext completeness, cache/file loading safety, economic calculation correctness, relevance filtering accuracy, and concurrency handling
- [x] **DOCX-05**: Quality gate enforcement audit verifies priority hierarchy (accuracy > audience > political > design > copy), MAX_PAGES enforcement, air gap regex patterns, and audience leakage detection between Doc A/B and Doc C/D
- [x] **DOCX-06**: Test coverage gap analysis maps function-level coverage, identifies untested edge cases, verifies doc type coverage for all 4 types, and assesses assertion depth beyond surface-level checks

### Website (WEB)

**Agent swarm:** 4 parallel review agents
**Swarm trigger:** `F:\tcr-policy-scanner\.planning\LAUNCH-SWARM.md`
**Agent definitions:**
| Agent | File | Focus |
|-------|------|-------|
| Web Wizard | via `F:\tcr-policy-scanner\.planning\LAUNCH-SWARM.md` | Performance, build optimization, SquareSpace compatibility |
| Mind Reader | via `F:\tcr-policy-scanner\.planning\LAUNCH-SWARM.md` | UX/UI, accessibility, WCAG 2.1 AA |
| Keen Kerner | via `F:\tcr-policy-scanner\.planning\LAUNCH-SWARM.md` | Typography, type scale, letter-spacing, readability |
| Pipeline Professor | via `F:\tcr-policy-scanner\.planning\LAUNCH-SWARM.md` | Data pipeline, deployment, SquareSpace integration |

**Known issues:** 47 across P0-P3 in `.planning/website/`
**Stack:** React 18 + Vite 6 + Tailwind CSS v4 + shadcn/ui
**Output:** `outputs/website_review/{agent}_findings.json`, synthesized into `SYNTHESIS.md`

- [x] **WEB-01**: Real DOCX download infrastructure replaces fake text blob generation with actual packet files served from GitHub Pages, with manifest.json listing all available packets and metadata
- [x] **WEB-02**: Full 592-Tribe coverage replaces 46-Tribe hardcoded mock list with EPA registry data, with accurate state and ecoregion mapping and fuzzy search autocomplete
- [x] **WEB-03**: SquareSpace iframe embedding tested and documented with `sandbox="allow-scripts allow-same-origin allow-downloads allow-popups"`, including cross-origin download verification on actual SquareSpace environment
- [x] **WEB-04**: Performance optimization achieves <500KB gzipped bundle, Core Web Vitals targets (LCP <2.5s, CLS <0.1), canvas particle system <5ms/frame, and non-render-blocking font loading
- [x] **WEB-05**: WCAG 2.1 AA accessibility compliance with keyboard navigation, screen reader ARIA roles (combobox, listbox, dialog), color contrast 4.5:1 minimum, focus management, and `prefers-reduced-motion` support
- [x] **WEB-06**: Typography rationalized with consistent type scale (CSS custom properties), letter-spacing reduced from 0.15em to 0.06em for titles, line-height documented, and line length limited to 45-75 characters
- [x] **WEB-07**: Data freshness indicators display packet generation date and underlying data currency date, with visual badges (green/yellow/red) for data age and accessible tooltips
- [x] **WEB-08**: Mobile browser compatibility verified on iOS Safari (375px) and Android Chrome (360px) with 44px minimum touch targets, no horizontal scroll, and functional download dialogs
- [x] **WEB-09**: GitHub Pages deployment pipeline automates Vite build, asset deployment, manifest generation, and SPA routing via 404.html redirect, triggered on merge to main
- [x] **WEB-10**: Website review synthesis document (`outputs/website_review/SYNTHESIS.md`) aggregates all 4 agents' findings into priority matrix (P0/P1/P2/P3), cross-agent themes, and implementation roadmap

### Production Hardening (HARD)

**Agent swarm:** 4 bug hunt agents
**Agent definitions:**
| Agent | File | Method | Checklist |
|-------|------|--------|-----------|
| Cyclops | `F:\tcr-policy-scanner\.planning\cyclops.md` | Deep code inspection (reads source) | 15 items |
| Dale Gribble | `F:\tcr-policy-scanner\.planning\dale-gribble.md` | Security & sovereignty audit (reads source + web) | 18 items |
| Mr. Magoo | `F:\tcr-policy-scanner\.planning\mr-magoo.md` | Experiential testing (does NOT read source) | 12 items |
| Marie Kondo | `F:\tcr-policy-scanner\.planning\marie-kondo.md` | Code hygiene & minimization (reads source) | TBD |

**Gate:** Go/no-go launch decision based on combined findings
**Output:** `outputs/bug_hunt/{agent}_findings.json`

- [ ] **HARD-01**: Deep code inspection (Cyclops) verifies boundary handling, race conditions, error recovery paths, resource leaks, and the 15-item checklist including GitHub Pages fallback, special characters in Tribe names, manifest staleness, and search race conditions
- [ ] **HARD-02**: Security & data sovereignty audit (Dale Gribble) verifies CSP headers, zero third-party tracking (no Google Analytics/Fonts CDN/cookies), TSDF compliance, referrer leakage prevention, source map exclusion, and the 18-item UNDRIP/OCAP/CARE checklist with paranoia_level assessment
- [ ] **HARD-03**: Experiential user testing (Mr. Magoo) navigates as a non-technical Tribal staff member without reading source code, testing misspellings, mobile friction, download flow, and reporting trust_score (1-10) across the 12-item user experience checklist
- [ ] **HARD-04**: Code hygiene sweep (Marie Kondo) identifies dead code, unused imports, redundant abstractions, oversized modules, and opportunities for simplification across the full codebase without changing behavior
- [ ] **HARD-05**: Go/no-go launch decision synthesizes all 4 agents' findings — zero P0 critical issues, all P1 issues have documented workarounds, and combined trust assessment supports 100-200 concurrent user launch

### Cross-Cutting (XCUT)

These requirements apply across ALL phases and are verified at each gate.

- [x] **XCUT-01**: Air gap compliance — zero references to ATNI, ATNI Climate Resilience Committee, NCAI, NCAI Climate Action Task Force, or "TCR Policy Scanner" in any rendered DOCX content or website-facing text; `grep -rn` audit returns zero hits
- [x] **XCUT-02**: Indigenous data sovereignty — zero third-party tracking scripts, zero external analytics, zero non-essential cookies, zero PII in URLs; CARE Principles and TSDF T0 classification maintained throughout
- [x] **XCUT-03**: v1.2 fix verification — all Four Fixes confirmed clean: logger naming (zero hardcoded strings), FY hardcoding (zero string literals), format_dollars (one canonical function), graph_schema paths (all pathlib)

---

## Future Requirements (Deferred Beyond v1.3)

- **DF-01**: Confidence scoring dashboard (visual confidence indicators in web UI) — deferred; confidence scoring embedded in INTEL-08 for DOCX, web display deferred
- **DF-03**: Action Center (interactive next-steps for Tribal Leaders) — deferred to v1.4
- **DF-05**: Download analytics (first-party only, for capacity planning) — deferred; requires opt-in infrastructure
- **ENH-003**: Interactive knowledge graph visualization (D3.js, SquareSpace-safe) — spec may be written in v1.3 by Horizon Walker, implementation deferred to v1.4+

## Out of Scope

- **AF-01**: No Tribal-specific data collection (T1+ classified) — only federal public data (T0)
- **AF-02**: No user accounts or authentication — static document delivery
- **AF-03**: No real-time WebSocket notifications — alert system is architecture spec only
- **AF-04**: No CMS or admin interface — pipeline runs via CLI and CI
- **AF-05**: No mobile native app — responsive web only
- **AF-06**: No React 19 or Vite 7 upgrades — stay on React 18 + Vite 6 for stability
- **AF-07**: No server-side rendering — static SPA on GitHub Pages
- **AF-08**: No external CDN dependencies — self-host all assets for sovereignty compliance

---

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| INTEL-01 | Phase 15 | Complete |
| INTEL-02 | Phase 15 | Complete |
| INTEL-03 | Phase 15 | Complete |
| INTEL-04 | Phase 15 | Complete |
| INTEL-05 | Phase 15 | Complete |
| INTEL-06 | Phase 15 | Complete |
| INTEL-07 | Phase 15 | Complete |
| INTEL-08 | Phase 15 | Complete |
| INTEL-09 | Phase 15 | Complete |
| INTEL-10 | Phase 15 | Complete |
| INTEL-11 | Phase 15 | Complete |
| INTEL-12 | Phase 15 | Complete |
| INTEL-13 | Phase 15 | Complete |
| INTEL-14 | Phase 15 | Complete |
| INTEL-15 | Phase 15 | Complete |
| DOCX-01 | Phase 16 | Complete |
| DOCX-02 | Phase 16 | Complete |
| DOCX-03 | Phase 16 | Complete |
| DOCX-04 | Phase 16 | Complete |
| DOCX-05 | Phase 16 | Complete |
| DOCX-06 | Phase 16 | Complete |
| WEB-01 | Phase 17 | Complete |
| WEB-02 | Phase 17 | Complete |
| WEB-03 | Phase 17 | Complete |
| WEB-04 | Phase 17 | Complete |
| WEB-05 | Phase 17 | Complete |
| WEB-06 | Phase 17 | Complete |
| WEB-07 | Phase 17 | Complete |
| WEB-08 | Phase 17 | Complete |
| WEB-09 | Phase 17 | Complete |
| WEB-10 | Phase 17 | Complete |
| HARD-01 | Phase 18 | Pending |
| HARD-02 | Phase 18 | Pending |
| HARD-03 | Phase 18 | Pending |
| HARD-04 | Phase 18 | Pending |
| HARD-05 | Phase 18 | Pending |
| XCUT-01 | Phase 15 | Complete |
| XCUT-02 | Phase 15 | Complete |
| XCUT-03 | Phase 15 | Complete |
