---
phase: 18-production-hardening
plan: 01
subsystem: web-hardening
tags: [wcag, dark-mode, contrast, adversarial-audit, security, sovereignty, ux, code-hygiene]
completed: 2026-02-13
duration: ~17min
requires:
  - 17-05 (SYNTHESIS.md with P1/P2/P3 findings)
  - 17-02 (HTML/CSS with ARIA combobox)
  - 17-03 (JavaScript with Fuse.js search)
  - 17-04 (CI/CD pipeline)
provides:
  - 11 inherited defect fixes (3 P1, 5 P2, 3 P3) for clean audit baseline
  - 4-agent adversarial audit findings for Wave 2 fix cycle
  - Complete defect inventory across code, security, UX, and hygiene
affects:
  - 18-02 (fix wave consumes agent findings JSON files)
  - 18-03 (final verification uses clean baseline)
tech-stack:
  added: []
  patterns: [4-agent-adversarial-audit, pre-flight-defect-fix, wcag-aa-verification]
key-files:
  created:
    - outputs/bug_hunt/cyclops_findings.json
    - outputs/bug_hunt/cyclops_summary.md
    - outputs/bug_hunt/dale-gribble_findings.json
    - outputs/bug_hunt/dale-gribble_summary.md
    - outputs/bug_hunt/mr-magoo_findings.json
    - outputs/bug_hunt/mr-magoo_summary.md
    - outputs/bug_hunt/marie-kondo_findings.json
    - outputs/bug_hunt/marie-kondo_summary.md
  modified:
    - docs/web/css/style.css
    - docs/web/js/app.js
    - docs/web/index.html
decisions: []
metrics:
  tasks: 2/2
  commits: 2
  files-created: 8
  files-modified: 3
---

# Phase 18 Plan 01: Pre-flight Fixes + Adversarial Audit Summary

Fixed 11 inherited defects from Phase 17 to establish a clean baseline, then executed 4 independent adversarial agents covering deep code inspection (15 items), security/sovereignty (18 items), experiential UX (12 items), and code hygiene (3-pass inventory).

## Task 1: Pre-flight Defect Fixes

Fixed all 11 inherited issues from Phase 17's SYNTHESIS.md across 3 files:

### P1 Fixes (3 items -- all in style.css dark mode block)
- **P1-01:** Button contrast -- `.btn-download`/`.btn-congressional` background `#1a5276` (8.36:1 on white)
- **P1-02:** Badge contrast -- `.badge-fresh` `#1e7a3d`, `.badge-aging` `#b45309`, `.badge-stale` `#a93226`, `.badge-unknown` `#5a6268` (all 4.5:1+)
- **P1-03:** Selected option contrast -- `#1a5276` background with `#fff` text (8.36:1)

### P2 Fixes (5 items)
- **P2-01:** `--tcr-muted` darkened from `#6c757d` to `#636b73` (4.78:1 on `#f8f9fa`)
- **P2-02:** `.option-alias` CSS class added (was referenced in JS, missing in CSS)
- **P2-03:** Duplicate `max-width` removed from `.section-desc`
- **P2-04:** `scrollIntoView` now checks `prefers-reduced-motion` via JS `matchMedia`
- **P2-05:** Light mode selected option changed from `--tcr-accent` to `--tcr-primary` (8.36:1)

### P3 Fixes (3 items)
- **P3-02:** Replaced `atniclimate.github.io` URL with generic `YOUR-ORG` in HTML comment
- **P3-03:** Added `rel="noopener"` to all 6 download anchor elements in app.js
- **P3-04:** Removed `opacity: 0.7` from `.footer-credit` to maintain contrast
- **P3-06:** Added `<noscript>` fallback message in index.html

## Task 2: Adversarial Agent Audit

### Agent 1: Cyclops (Deep Code Inspection)
- **Findings:** 15 (1 important, 14 cosmetic)
- **Key finding:** CYCLOPS-001 -- fetch() has no timeout/AbortController. If server hangs, user sees permanent loading state.
- **Assessment:** Architecture fundamentally sound. XSS-safe DOM manipulation throughout. Efficient 592-item handling. One substantive timeout issue.
- **Traces completed:** 8 end-to-end data paths

### Agent 2: Dale Gribble (Security and Data Sovereignty)
- **Findings:** 18 (2 important, 16 cosmetic)
- **Key findings:**
  - DALE-001 -- No SRI hash on bundled fuse.min.js (supply chain risk)
  - DALE-002 -- Public manifest enables monitoring of Tribal advocacy activity
- **Sovereignty assessment:** Substantially honors UNDRIP/OCAP/CARE principles. Zero tracking, system fonts, no cookies, T0 classification enforced.
- **Third-party inventory:** 5 domains (1 hosting + 4 federal APIs, all server-side)

### Agent 3: Mr. Magoo (Experiential User Testing)
- **Findings:** 12 (0 important, 12 cosmetic)
- **Trust score:** 8/10
- **Highlights:** Search works beautifully, performance is excellent, mobile layout is solid, design is professional and respectful.
- **Key suggestions:** Add document type descriptions, add privacy statement, consider shareable URLs.

### Agent 4: Marie Kondo (Code Hygiene Sweep)
- **Joy score:** 8/10 (potential: 9/10)
- **Dependencies:** 13 packages, 0 unused, 2 replaceable with stdlib (low priority)
- **Dead code:** 4 one-time alias migration scripts (safe to remove)
- **Consolidation:** CFDA mapping duplicated between 2 scrapers
- **Assessment:** Clean architecture, every module serves the mission, minimal clutter.

## Aggregate Findings for Wave 2

| Agent | Critical (P0) | Important (P1) | Cosmetic (P2/P3) | Total |
|-------|:---:|:---:|:---:|:---:|
| Cyclops | 0 | 1 | 14 | 15 |
| Dale Gribble | 0 | 2 | 16 | 18 |
| Mr. Magoo | 0 | 0 | 12 | 12 |
| Marie Kondo | 0 | 0 | 12 | 12 |
| **Total** | **0** | **3** | **54** | **57** |

### Important (P1) findings requiring Wave 2 action:
1. **CYCLOPS-001:** Add fetch timeout with AbortController
2. **DALE-001:** Add SRI hash on fuse.min.js
3. **DALE-002:** Document manifest exposure in TSDF assessment (or remove manifest)

## Deviations from Plan

None -- plan executed exactly as written.

## Verification

- [x] All 3 P1 dark mode contrast issues fixed with WCAG AA-compliant colors
- [x] All P2/P3 issues from Phase 17 fixed
- [x] All 4 agent findings JSON files exist and are valid JSON
- [x] All 4 agent markdown summaries exist
- [x] Each agent covered every item on their checklist
- [x] No source files modified during agent audits
- [x] All 964 tests pass (no regressions)

## Commits

| Hash | Description |
|------|-------------|
| `b58203e` | fix(18-01): resolve 11 inherited P1/P2/P3 defects from Phase 17 |
| `de424b2` | feat(18-01): execute 4-agent adversarial audit and collect findings |

## Next Phase Readiness

Wave 2 (18-02) is ready to begin. The 3 important findings from the adversarial audit (fetch timeout, SRI hash, manifest documentation) should be prioritized. The 54 cosmetic findings can be triaged for inclusion or deferral.
