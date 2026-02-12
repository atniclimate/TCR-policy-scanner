---
phase: 17-website-deployment
plan: 02
subsystem: web-frontend
tags: [html, css, aria, dark-mode, accessibility, responsive]
completed: 2026-02-12
duration: ~2min
requires: []
provides:
  - ARIA 1.2 combobox markup in index.html
  - State filter dropdown element
  - Freshness badge containers
  - Dark mode via prefers-color-scheme
  - CRT scan-line effect
  - Type scale via CSS custom properties
  - 44px touch targets
  - prefers-reduced-motion support
  - 404.html SPA routing for GitHub Pages
affects:
  - 17-03 (JavaScript combobox controller and app logic)
  - 17-04 (data pipeline and freshness badge population)
  - 17-05 (deployment and final verification)
tech-stack:
  added: []
  patterns: [css-custom-properties, prefers-color-scheme, aria-combobox, spa-routing]
key-files:
  created:
    - docs/web/404.html
  modified:
    - docs/web/index.html
    - docs/web/css/style.css
decisions:
  - id: DEC-1702-01
    decision: "Listbox width uses calc(100% - 2rem) to account for search container padding"
  - id: DEC-1702-02
    decision: "Tribe card uses opacity transition with data-visible attribute for JS-controlled fade-in"
metrics:
  tasks: 2/2
  commits: 2
  files-created: 1
  files-modified: 2
  total-lines: 593 (74 HTML + 496 CSS + 23 404.html)
---

# Phase 17 Plan 02: HTML/CSS Rewrite with ARIA Combobox and Dark Mode Summary

**One-liner:** Complete HTML/CSS rewrite with ARIA 1.2 combobox markup, auto dark mode, CRT scan-line effect, freshness badges, state filter, and mobile responsive layout.

## What Was Done

### Task 1: Rewrite index.html with ARIA combobox, state filter, and complete structure
**Commit:** `f6cb928`

Rewrote the HTML structure to replace the Awesomplete-dependent markup with a standards-based ARIA 1.2 combobox pattern. Key structural additions:

- **ARIA combobox input** with `role="combobox"`, `aria-controls="tribe-listbox"`, `aria-expanded`, `aria-autocomplete="list"`, and `aria-activedescendant` attributes
- **Listbox element** (`<ul role="listbox" id="tribe-listbox">`) for search results dropdown
- **Live region** (`role="status"`, `aria-live="polite"`) for screen reader result count announcements
- **State filter dropdown** (`<select id="state-filter">`) with "Or browse by state" label
- **State browse results section** for displaying filtered tribe lists
- **Freshness badge container** (`<span id="tribe-freshness" class="badge">`) inside card title
- **Script loading order** changed to: fuse.min.js -> combobox.js -> app.js (no defer)
- **404.html** created for GitHub Pages SPA routing with path segment preservation
- **SquareSpace embed** updated with sandbox attributes for security
- **Removed** all references to awesomplete.css and awesomplete.min.js
- **Added** `<meta name="color-scheme" content="light dark">` for dark mode browser hint

### Task 2: Rewrite style.css with dark mode, CRT effect, type scale, badges, and mobile
**Commit:** `4d5dae9`

Complete CSS rewrite expanding from 49 minified lines to 497 well-structured lines with full documentation:

- **CSS custom properties** for type scale (`--tcr-fs-xs` through `--tcr-fs-xl`, 1.2 minor third ratio) and colors
- **Auto dark mode** via `@media (prefers-color-scheme: dark)` with full color palette overrides
- **CRT scan-line effect** via `body::after` pseudo-element with `repeating-linear-gradient`
- **Freshness badge styles** (`.badge-fresh`, `.badge-aging`, `.badge-stale`, `.badge-unknown`) with pill shape
- **Listbox dropdown** with absolute positioning, scroll overflow, hover/selected states
- **State filter** with flex layout, focus/disabled states, proper touch targets
- **State browse results** grid layout with hover/focus states
- **44px minimum touch targets** on all interactive elements (search input, listbox options, select, buttons, tribe items)
- **48px touch targets on mobile** (<600px breakpoint) for enhanced touch accessibility
- **Card fade-in** transition via `opacity` + `data-visible` attribute
- **prefers-reduced-motion** disables ALL transitions, animations, and CRT effect
- **Print media** hides non-essential elements, forces card visibility
- **Letter-spacing** `0.06em` on h1, line-height 1.2 for headings
- **Max line length** `65ch` on paragraph text in cards for readability
- **WCAG AA amber** `#b45309` preserved from Phase 16 DEC-1602-01

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| DEC-1702-01 | Listbox width uses `calc(100% - 2rem)` | Accounts for search container padding so dropdown aligns with input edges |
| DEC-1702-02 | Card fade-in uses `opacity` + `data-visible` attribute | Allows JS to control visibility without layout thrash; `hidden` attribute handled separately |

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

All must_haves confirmed:

| Requirement | Status |
|-------------|--------|
| HTML contains ARIA 1.2 combobox markup | PASS - role=combobox, aria-controls, aria-expanded, aria-autocomplete=list |
| HTML contains state filter dropdown | PASS - select#state-filter with label |
| HTML contains freshness badge containers | PASS - span#tribe-freshness.badge |
| CSS implements auto dark mode via prefers-color-scheme | PASS - full color overrides |
| CSS implements CRT scan-line effect | PASS - body::after with repeating-linear-gradient |
| CSS defines type scale using CSS custom properties | PASS - 6 scale steps, 30 usages |
| CSS ensures 44px minimum touch targets | PASS - 5 elements with min-height: 44px |
| CSS respects prefers-reduced-motion | PASS - disables transitions, animations, and CRT |
| 404.html redirects for SPA routing | PASS - redirect script with path preservation |
| No awesomplete references in HTML | PASS - zero matches |
| XCUT-01 compliance | PASS - zero ATNI/NCAI/TCR Policy Scanner references |

## Next Phase Readiness

Plan 17-03 (JavaScript) can now implement:
- Combobox controller binding to `#tribe-search` input and `#tribe-listbox`
- Fuse.js integration for fuzzy search
- State filter population and change handler
- Freshness badge class assignment (`badge-fresh`, `badge-aging`, `badge-stale`, `badge-unknown`)
- Card visibility via `data-visible` attribute
- State browse results population into `#state-results-list`

All HTML IDs and CSS classes are in place. JavaScript files referenced (`fuse.min.js`, `combobox.js`, `app.js`) need to be created in Plan 17-01 and 17-03.
