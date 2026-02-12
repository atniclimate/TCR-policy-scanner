---
phase: 17-website-deployment
verified: 2026-02-12T23:58:00Z
status: gaps_found
score: 4/5 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 4/5
  gaps_closed: []
  gaps_remaining:
    - "Dark mode button contrast (#5dade2 + white = 2.46:1, needs 4.5:1)"
    - "Dark mode badge contrast (2.19-3.82:1, needs 4.5:1)"
    - "Dark mode selected option contrast (#85c1e9 + white = 1.94:1, needs 4.5:1)"
  regressions: []
gaps:
  - truth: "WCAG 2.1 AA compliance is verified: keyboard-only search-to-download flow works, ARIA combobox roles are present, color contrast meets 4.5:1, and prefers-reduced-motion is respected"
    status: partial
    reason: "Keyboard navigation and ARIA roles are complete, but 3 P1 dark mode color contrast failures drop below WCAG AA 4.5:1 threshold"
    artifacts:
      - path: "docs/web/css/style.css"
        issue: "Dark mode @media block (lines 36-51) only sets CSS variables. No component-specific overrides for buttons/badges/selected options that keep white text with lightened backgrounds"
    missing:
      - "Dark mode override: .btn-download { background: #1a5276; } for 4.5:1 with white"
      - "Dark mode override: .btn-download:hover { background: #1f6d9b; } for 4.5:1 with white"
      - "Dark mode overrides: .badge-* with darker backgrounds or dark text on light backgrounds"
      - "Dark mode override: .listbox li[aria-selected=true] { background: #1a5276; } for 4.5:1 with white"
context:
  conditional_pass: true
  user_accepted: "2026-02-12 (Plan 17-05)"
  deferred_to: "Future milestone"
  rationale: "CSS-only fixes, no architectural changes required. Site is functionally complete and accessible in light mode."
---

# Phase 17: Website Deployment Verification Report (Re-Verification)

**Phase Goal:** Any of 592 Tribal Nations can visit the website, search for their Nation by name (with typo tolerance), and download real DOCX advocacy packets -- served from GitHub Pages, embeddable in SquareSpace, accessible via keyboard and screen reader, and performant on mobile devices

**Verified:** 2026-02-12T23:58:00Z
**Status:** gaps_found
**Re-verification:** Yes — after conditional pass acceptance

## Re-Verification Context

**Previous verification:** 2026-02-12T23:45:00Z (initial)
**Previous status:** gaps_found (3 P1 dark mode contrast issues)
**User decision:** CONDITIONAL PASS accepted with design improvements deferred to future milestone

This re-verification confirms the gaps are **still present** but notes the user accepted conditional pass.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Tribal staff can type misspelled name, find Nation via fuzzy match (592 tribes), download real DOCX | ✓ VERIFIED | tribes.json line 2: 592 tribes. Fuse.js 7.1.0 threshold 0.4 (app.js 70-76). Download anchors with .download attribute (267-282). Human verified. |
| 2 | Renders in SquareSpace iframe with sandbox permissions, downloads work | ✓ VERIFIED | index.html line 69 documents sandbox attrs. Vanilla JS compatible. Download via anchor works. |
| 3 | Bundle <500KB gzipped, Core Web Vitals pass, mobile responsive 44px targets | ✓ VERIFIED | 438KB raw (~65KB gzipped). 44px baseline, 48px mobile. CLS none. LCP <1s. |
| 4 | WCAG 2.1 AA: keyboard nav, ARIA combobox, 4.5:1 contrast, reduced-motion | ⚠️ PARTIAL | PASS: ARIA complete, keyboard nav works, reduced-motion. FAIL: 3 P1 dark mode contrast (2.46:1, 2.19-3.82:1, 1.94:1). |
| 5 | GitHub Pages pipeline automates build, asset deploy, manifest, SPA routing | ✓ VERIFIED | deploy-website.yml triggers on main. generate-packets.yml weekly. 404.html SPA routing. |

**Score:** 4/5 truths verified

### Required Artifacts

| Artifact | Status | Notes |
|----------|--------|-------|
| docs/web/index.html | ✓ VERIFIED | 3.5KB, ARIA combobox markup |
| docs/web/css/style.css | ⚠️ PARTIAL | 11KB, 481 lines. Dark mode contrast gaps. |
| docs/web/js/app.js | ✓ VERIFIED | 16KB, search + downloads + state filter |
| docs/web/js/combobox.js | ✓ VERIFIED | 9KB, W3C APG pattern |
| docs/web/js/fuse.min.js | ✓ VERIFIED | 26KB, self-hosted 7.1.0 |
| docs/web/data/tribes.json | ✓ VERIFIED | 372KB, 592 tribes with aliases |
| scripts/build_web_index.py | ✓ VERIFIED | Generates tribes.json |
| .github/workflows/deploy-website.yml | ✓ VERIFIED | GitHub Pages CI/CD |
| .github/workflows/generate-packets.yml | ✓ VERIFIED | Weekly generation |
| docs/web/404.html | ✓ VERIFIED | SPA routing |

### Key Link Verification

All key links verified:
- app.js → tribes.json (fetch)
- app.js → Fuse.js (instantiation)  
- Buttons → DOCX files (download anchors)
- Workflows → scripts (python calls)

### Anti-Patterns Found

None. No TODOs, FIXMEs, or stub implementations.

### Re-Verification Analysis

**Gaps closed:** 0
**Gaps remaining:** 3 P1 issues (dark mode CSS variable contrast)
**Regressions:** 0

**Root cause:** Dark mode @media block (CSS 36-51) only sets CSS variables. Components using these variables with white text drop below 4.5:1 contrast.

**Fix:** Add component-specific dark mode overrides for .btn-download, .badge-*, and .listbox li[aria-selected=true].

### Gaps Summary

Truth 4 (WCAG 2.1 AA) partially verified. Keyboard nav and ARIA complete, but dark mode has 3 contrast failures:

1. Buttons: #5dade2 + white = 2.46:1 (needs 4.5:1)
2. Badges: 2.19-3.82:1 (needs 4.5:1)
3. Selected options: #85c1e9 + white = 1.94:1 (needs 4.5:1)

Website is **functionally complete and accessible in light mode**. User accepted CONDITIONAL PASS (17-05-SUMMARY) with CSS fixes deferred to future milestone.

**Phase goal:** 4/5 truths verified. Production-ready with dark mode WCAG AA caveat.

---

_Verified: 2026-02-12T23:58:00Z_
_Verifier: Claude (gsd-verifier)_
_Re-verification: Yes (gaps remain, conditional pass accepted)_
