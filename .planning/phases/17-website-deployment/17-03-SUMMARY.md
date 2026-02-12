---
phase: 17-website-deployment
plan: 03
subsystem: web-frontend
tags: [javascript, fuse-js, aria-combobox, fuzzy-search, accessibility, dom-safe]
completed: 2026-02-12
duration: ~1min
requires:
  - 17-01 (Fuse.js 7.1.0 self-hosted, alias embedding in tribes.json)
  - 17-02 (ARIA 1.2 combobox HTML markup, CSS styles, freshness badge containers)
provides:
  - W3C APG ARIA combobox with keyboard navigation and Fuse.js integration
  - Main application controller with state filter, card rendering, downloads
  - Fuzzy search across 592 Tribe names + 18,776 aliases
  - Data freshness badges (green/yellow/red)
  - Descriptive download filenames
  - Download Both sequential trigger
  - Regional document cards
affects:
  - 17-04 (data pipeline integration, tribes.json population)
  - 17-05 (deployment and end-to-end verification)
tech-stack:
  added: []
  patterns: [iife, prototype-methods, var-only, dom-safe-rendering, aria-combobox-pattern]
key-files:
  created:
    - docs/web/js/combobox.js
  modified:
    - docs/web/js/app.js
decisions: []
metrics:
  tasks: 2/2
  commits: 2
  files-created: 1
  files-modified: 1
  total-lines: 804 (309 combobox.js + 495 app.js)
---

# Phase 17 Plan 03: JavaScript Application Logic Summary

**One-liner:** W3C APG ARIA combobox with Fuse.js fuzzy search, state filter, freshness badges, descriptive downloads, and DOM-safe rendering

## What Was Done

### Task 1: Create combobox.js -- W3C APG ARIA combobox component
**Commit:** `29b4554`

Created a self-contained IIFE exposing `window.TribeCombobox` implementing the W3C ARIA Authoring Practices Guide "Editable Combobox with List Autocomplete" pattern:

- **Constructor** accepts input, listbox, status, and Fuse.js instance
- **Keyboard navigation**: ArrowDown/Up with wrapping, Enter to select, Escape to close/clear
- **Focus management**: `aria-activedescendant` on input, `aria-selected` on options, `scrollIntoView` for visibility
- **Search integration**: Runs `fuse.search()` on input, caps at 15 results, announces count via live region
- **Alias display**: Detects alias matches from Fuse.js `result.matches` and shows "Also known as: {alias}"
- **Click handling**: Delegated click on listbox walks up to `[role="option"]`, finds index, selects
- **Blur delay**: 200ms timeout before close allows click events to register first
- **Prototype methods**: 11 methods on `TribeCombobox.prototype` for broad browser compatibility
- **XSS prevention**: All DOM via `createElement`/`textContent`, zero `innerHTML`

### Task 2: Rewrite app.js -- main application with Fuse.js, state filter, cards, downloads
**Commit:** `fa2e952`

Complete rewrite of app.js from Awesomplete-based to Fuse.js-powered application:

- **Fuse.js initialization**: Weighted keys (name:3, aliases:1, states:0.5), threshold 0.4, ignoreLocation, includeMatches
- **TribeCombobox integration**: `new TribeCombobox(input, listbox, status, fuse)` with `onTribeSelected = showCard`
- **State filter**: Builds sorted unique state list from all tribes, populates `<select>`, filters and renders clickable results
- **State browse results**: Clickable div items with keyboard support (Enter/Space), sorted alphabetically
- **showCard()**: Sets name, states, ecoregion, freshness badge, builds download buttons with descriptive filenames
- **Freshness badges**: `getFreshnessBadge()` returns class/text/label -- green (<7d), yellow (<30d), red (30d+), gray (unknown)
- **Descriptive filenames**: `sanitizeFilename()` strips special chars, replaces spaces with underscores, applied to all downloads
- **Download Both**: Creates temporary anchor elements, clicks first, 300ms delay, clicks second
- **Regional documents**: Renders region cards with name, states, Internal Strategy and Congressional Overview buttons
- **Card animation**: Uses `data-visible` attribute with forced reflow for CSS opacity transition
- **Error handling**: fetch failure shows error message, empty tribes shows "No Tribe data available"
- **Bootstrap**: `DOMContentLoaded` handler with readyState check for script timing

## Verification Results

| Check | Status |
|-------|--------|
| combobox.js contains TribeCombobox | PASS (15 occurrences) |
| combobox.js uses prototype methods | PASS (11 methods) |
| combobox.js zero innerHTML | PASS |
| combobox.js zero let/const | PASS (var only) |
| app.js contains Fuse initialization | PASS |
| app.js zero innerHTML | PASS |
| app.js zero let/const | PASS (var only) |
| app.js zero Awesomplete references | PASS |
| XCUT-01 compliance (no ATNI/NCAI/TCR Policy Scanner) | PASS |
| XCUT-02 compliance (zero CDN dependencies) | PASS |

## Deviations from Plan

None -- plan executed exactly as written.

## Key Artifacts

### combobox.js (309 lines)
```javascript
// Key API surface:
window.TribeCombobox = function(inputEl, listboxEl, statusEl, fuseInstance) { ... }
TribeCombobox.prototype.onInput     // Fuse.js search + render
TribeCombobox.prototype.onKeyDown   // ArrowDown/Up/Enter/Escape
TribeCombobox.prototype.moveFocus   // aria-activedescendant management
TribeCombobox.prototype.renderOptions // DOM-safe option rendering
TribeCombobox.prototype.selectOption  // Selection + callback
TribeCombobox.prototype.open/close/isOpen // Listbox visibility
```

### app.js (495 lines)
```javascript
// Key functions:
init()              // Fetch tribes.json, build Fuse index, wire UI
populateStateFilter()  // Build sorted state dropdown
onStateFilterChange()  // Filter and render state results
showCard(tribe)     // Render tribe card with badges and downloads
getFreshnessBadge() // Green/yellow/red based on timestamp age
sanitizeFilename()  // Safe download filenames
downloadBoth()      // Sequential 300ms-delayed dual download
renderRegions()     // Regional document cards
```

## Next Phase Readiness

Plan 17-04 (data pipeline) and 17-05 (deployment) can now proceed. All JavaScript logic is in place:
- Combobox binds to HTML elements from Plan 17-02
- Fuse.js search indexes data from Plan 17-01
- State filter, cards, and downloads ready for tribes.json data
- Regional documents render from regions array in tribes.json
