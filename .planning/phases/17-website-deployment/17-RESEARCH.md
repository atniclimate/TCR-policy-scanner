# Phase 17: Website Deployment - Research

**Researched:** 2026-02-12
**Domain:** Static website (vanilla HTML/JS/CSS), fuzzy search, accessibility, GitHub Pages deployment
**Confidence:** HIGH

## Summary

Phase 17 enhances the existing static website at `docs/web/` to serve as the public distribution point for 992 DOCX advocacy packets across 592 Tribal Nations and 8 regions. The site uses enhanced vanilla HTML/JS/CSS with Fuse.js for fuzzy search -- no build step, no framework.

The existing codebase provides a solid foundation: `index.html` (51 lines), `app.js` (125 lines), and `style.css` (48 lines) with Awesomplete for search. The key transformation is replacing Awesomplete with a custom ARIA combobox powered by Fuse.js, adding state filtering, data freshness badges, dark mode, and the deployment pipeline.

Critical sizing discovery: The full 18,776 alias set is 1.2MB raw / 83KB gzipped. However, filtering to the 10 most distinctive aliases per Tribe (excluding housing authority variants) yields 258KB raw / **28KB gzipped** -- well within the 500KB total budget. This is the recommended approach: embed aliases directly in `tribes.json` and let Fuse.js search `name` + `aliases` keys with weighted scoring.

**Primary recommendation:** Replace Awesomplete with a custom ARIA combobox (W3C APG pattern) powered by Fuse.js v7.1.0 (`fuse.min.js` at 25.8KB). Embed 10 filtered aliases per Tribe in `tribes.json`. Build a GitHub Actions workflow to generate `tribes.json`, copy DOCX files, and deploy to GitHub Pages on merge to main.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Fuse.js | 7.1.0 | Fuzzy search with typo tolerance | Zero-dependency, ~6KB gzipped (basic) or ~8KB (full), weighted multi-key search, client-side |
| Vanilla JS | ES2020+ | Application logic | Decision: no framework, no build step |
| CSS Custom Properties | N/A | Theming, dark mode | Already used (`--tcr-primary`, etc.), extend for dark mode |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| None | N/A | N/A | Zero external dependencies beyond Fuse.js |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom ARIA combobox | Awesomplete + Fuse.js overlay | Awesomplete last released 2019, ARIA 1.0 era, poor screen reader alignment with modern ARIA 1.2 combobox spec. Custom is more work but delivers correct accessibility. |
| Fuse.js | FlexSearch, Lunr.js | FlexSearch is faster for large datasets but heavier. Lunr.js is index-based but ~8KB and less ergonomic for fuzzy search. Fuse.js is the standard for client-side fuzzy search at this scale. |
| Full 18,776 aliases | Top 10 per Tribe | Full set is 83KB gzipped, still within budget but wastes bandwidth on housing authority variants users won't search for. 10 per Tribe (28KB gz) is sufficient for typo tolerance + self-designation names. |

### Installation
```html
<!-- CDN (no npm/build step) -->
<script src="https://cdn.jsdelivr.net/npm/fuse.js@7.1.0/dist/fuse.min.js"></script>

<!-- Or self-host for zero external dependencies -->
<script src="js/fuse.min.js"></script>
```

**Recommendation: Self-host** `fuse.min.js` (25.8KB) in `docs/web/js/` to avoid CDN dependency and comply with indigenous data sovereignty (XCUT-02: zero third-party requests).

### Fuse.js Distribution Files (v7.1.0)
| File | Size | Use |
|------|------|-----|
| `fuse.min.js` | 25.8 KB | Full feature set, UMD bundle -- **use this** |
| `fuse.basic.min.js` | 17.4 KB | Basic search only (no extended search) |
| `fuse.min.mjs` | 17.8 KB | ES module variant |

## Architecture Patterns

### Recommended Project Structure
```
docs/web/
  index.html              # Single-page application entry
  404.html                # SPA routing fallback for GitHub Pages
  css/
    style.css             # Main styles (light + dark mode)
  js/
    fuse.min.js           # Fuse.js 7.1.0 (self-hosted, 25.8KB)
    app.js                # Application logic (search, cards, downloads)
    combobox.js           # Custom ARIA combobox component
  data/
    tribes.json           # Generated: 592 Tribes + aliases + doc metadata
    manifest.json         # Generated: deployment metadata (timestamp, counts)
  tribes/
    internal/             # Doc A DOCX files (384 files)
    congressional/        # Doc B DOCX files (592 files)
    regional/
      internal/           # Doc C DOCX files (8 files)
      congressional/      # Doc D DOCX files (8 files)
```

### Pattern 1: Custom ARIA Combobox (W3C APG Pattern)

**What:** Hand-built combobox following the W3C ARIA Authoring Practices Guide "Editable Combobox with List Autocomplete" pattern.

**When to use:** When Awesomplete or similar libraries don't fully implement ARIA 1.2 combobox semantics.

**Why replace Awesomplete:** Awesomplete was last released in 2019 (v1.1.5). It implements ARIA 1.0 combobox patterns. Modern screen readers (JAWS 2024+, NVDA 2024+, VoiceOver on iOS 17+) expect ARIA 1.2 combobox semantics: `role="combobox"` on the input, `aria-controls` pointing to the listbox, `aria-activedescendant` for visual focus management, `aria-expanded`, and `aria-autocomplete="list"`.

**Required ARIA attributes:**
```html
<!-- Input (combobox) -->
<input type="text"
  role="combobox"
  aria-autocomplete="list"
  aria-controls="tribe-listbox"
  aria-expanded="false"
  aria-activedescendant=""
  id="tribe-search"
  autocomplete="off">

<!-- Listbox (dropdown) -->
<ul role="listbox"
  id="tribe-listbox"
  aria-label="Tribal Nations"
  hidden>
  <li role="option" id="opt-0" aria-selected="false">Navajo Nation</li>
  <li role="option" id="opt-1" aria-selected="false">Cherokee Nation</li>
</ul>
```

**Required keyboard interactions:**
| Key | Textbox Focused | Listbox Focused |
|-----|-----------------|-----------------|
| Down Arrow | Open listbox, move to first option | Next option (wrap) |
| Up Arrow | Open listbox, move to last option | Previous option (wrap) |
| Enter | Select current option, close | Select current option, close |
| Escape | Clear if open, close listbox | Close listbox, return to textbox |
| Home/End | Move cursor in text | Return to textbox, move cursor |
| Printable chars | Type in textbox, filter results | Return to textbox, type |

**Focus management:** DOM focus stays on the `<input>`. Visual focus on listbox options is managed via `aria-activedescendant` pointing to the currently highlighted `<li id>`. JavaScript must scroll the highlighted option into view.

Source: [W3C APG Combobox Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/combobox/examples/combobox-autocomplete-list/)

### Pattern 2: Fuse.js Weighted Multi-Key Search

**What:** Configure Fuse.js to search across Tribe `name` (highest weight) and `aliases` (lower weight), with `ignoreLocation: true` and a threshold tuned for typo tolerance.

**Configuration:**
```javascript
// Source: https://www.fusejs.io/api/options.html + Context7 /websites/fusejs_io
const fuse = new Fuse(tribesData, {
  keys: [
    { name: 'name', weight: 3 },
    { name: 'aliases', weight: 1 },
    { name: 'states', weight: 0.5 }
  ],
  threshold: 0.4,          // 0=exact, 1=match anything; 0.4 = good typo tolerance
  ignoreLocation: true,     // Match anywhere in string, not just first 60 chars
  includeScore: true,       // For ranking display
  includeMatches: true,     // For highlighting matched text
  minMatchCharLength: 2,    // Don't match single chars
  shouldSort: true,         // Sort by score
  findAllMatches: false,    // Stop at first good match per key
});

// Search returns scored results
const results = fuse.search("navjo"); // typo for "Navajo"
// results[0] = { item: {name: "Navajo Nation", ...}, score: 0.15, matches: [...] }
```

**Pre-indexing for performance (optional):**
```javascript
// Source: https://www.fusejs.io/api/indexing.html
const index = Fuse.createIndex(
  ['name', 'aliases', 'states'],
  tribesData
);
const fuse = new Fuse(tribesData, options, index);
```

**Critical: `ignoreLocation: true`** is essential. Tribal Nation names like "Absentee-Shawnee Tribe of Indians of Oklahoma" are 50+ chars. Default Fuse.js only searches first 60 chars from position 0. With aliases embedded, the match may appear deep in the aliases array.

### Pattern 3: Two-Tier Data Loading

**What:** Load `tribes.json` on page load (single fetch, ~28KB gzipped), initialize Fuse.js index, enable search. No secondary fetches needed.

**Data flow:**
```
Page load -> fetch('data/tribes.json')
          -> Parse JSON (592 Tribes + aliases + doc metadata + 8 regions)
          -> Initialize Fuse.js index
          -> Enable search input
          -> Enable state dropdown
```

**tribes.json schema (enhanced from build_web_index.py):**
```json
{
  "generated_at": "2026-02-12T00:00:00Z",
  "total_tribes": 592,
  "tribes": [
    {
      "id": "epa_100000001",
      "name": "Absentee-Shawnee Tribe of Indians of Oklahoma",
      "states": ["OK"],
      "ecoregion": "Plains",
      "aliases": [
        "absentee-shawnee tribe",
        "absentee-shawnee tribe of oklahoma",
        "absentee-shawnee tribe of indians"
      ],
      "documents": {
        "internal_strategy": "internal/epa_100000001.docx",
        "congressional_overview": "congressional/epa_100000001.docx"
      },
      "has_complete_data": true,
      "generated_at": "2026-02-12T00:00:00Z"
    }
  ],
  "regions": [
    {
      "region_id": "pnw",
      "region_name": "Pacific Northwest / Columbia River Basin",
      "states": ["WA", "OR", "ID", "MT"],
      "documents": {
        "internal_strategy": "regional/internal/pnw.docx",
        "congressional_overview": "regional/congressional/pnw.docx"
      }
    }
  ],
  "metadata": {
    "doc_a_count": 384,
    "doc_b_count": 592,
    "doc_c_count": 8,
    "doc_d_count": 8
  }
}
```

### Pattern 4: State Filter Dropdown

**What:** A `<select>` element listing 37 US states that have Tribes. Selecting a state filters the visible Tribe list below the search. Works independently of and alongside fuzzy search.

**Implementation:**
```javascript
// Build state list from tribes data
const allStates = [...new Set(tribesData.flatMap(t => t.states))].sort();
// Populate <select> with <option> elements

// Filter: when state selected, show all Tribes in that state
function filterByState(stateCode) {
  const matches = tribesData.filter(t => t.states.includes(stateCode));
  renderTribeList(matches);
}
```

**37 states** have federally recognized Tribes (from analysis): AK, AL, AZ, CA, CO, CT, FL, IA, ID, IN, KS, LA, MA, ME, MI, MN, MO, MS, MT, NC, ND, NE, NM, NV, NY, OK, OR, RI, SC, SD, TN, TX, UT, VA, WA, WI, WY.

### Pattern 5: Dark Mode via CSS Custom Properties

**What:** Auto dark mode using `prefers-color-scheme` media query. Override CSS custom properties in the dark mode block. No JavaScript toggle needed.

```css
/* Light mode (default) */
:root {
  --tcr-primary: #1a5276;
  --tcr-accent: #2980b9;
  --tcr-bg: #f8f9fa;
  --tcr-text: #2c3e50;
  --tcr-card: #fff;
  --tcr-border: #dee2e6;
}

/* Dark mode (auto from OS preference) */
@media (prefers-color-scheme: dark) {
  :root {
    --tcr-primary: #5dade2;
    --tcr-accent: #85c1e9;
    --tcr-bg: #1a1a2e;
    --tcr-text: #e0e0e0;
    --tcr-card: #16213e;
    --tcr-border: #2c3e50;
  }
}
```

### Pattern 6: CRT Scan-Line Effect (CSS Only)

**What:** A purely decorative scan-line overlay using CSS `repeating-linear-gradient`. No canvas, no JavaScript, no animation frames.

```css
body::after {
  content: '';
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 9999;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(0, 0, 0, 0.03) 2px,
    rgba(0, 0, 0, 0.03) 4px
  );
}

@media (prefers-reduced-motion: reduce) {
  body::after {
    display: none;
  }
}
```

The React prototype used `opacity: 0.03` with cyan-colored lines. For the production site, use black semi-transparent lines at very low opacity (0.02-0.04) which works in both light and dark mode.

### Pattern 7: Descriptive Download Filenames

**What:** Use the `download` attribute on `<a>` tags with a human-readable filename. GitHub Pages serves static `.docx` files; the browser uses the `download` attribute to rename.

```javascript
function makeDownloadLink(docPath, tribeName, docType) {
  var a = document.createElement('a');
  a.href = 'tribes/' + docPath;
  // Sanitize tribe name for filesystem safety
  var safeName = tribeName.replace(/[^a-zA-Z0-9 _-]/g, '').replace(/\s+/g, '_');
  var typeLabel = docType === 'internal_strategy'
    ? 'Internal_Strategy'
    : 'Congressional_Overview';
  a.download = safeName + '_' + typeLabel + '.docx';
  return a;
}
```

**Important:** The `download` attribute works for same-origin files on GitHub Pages. Cross-origin downloads require `Content-Disposition` headers which GitHub Pages doesn't set, but since all files are served from the same origin (`atniclimate.github.io`), the `download` attribute works correctly.

### Pattern 8: Data Freshness Badges

**What:** Color-coded badges showing document age based on `generated_at` timestamp.

```javascript
function getFreshnessBadge(generatedAt) {
  if (!generatedAt) return { cls: 'badge-unknown', text: 'Unknown' };
  var days = (Date.now() - new Date(generatedAt).getTime()) / 86400000;
  if (days < 7)  return { cls: 'badge-fresh', text: 'Current' };
  if (days < 30) return { cls: 'badge-aging', text: 'Recent' };
  return { cls: 'badge-stale', text: 'Needs Update' };
}
```

```css
.badge-fresh  { background: #2c6e49; color: #fff; } /* Green */
.badge-aging  { background: #b45309; color: #fff; } /* Amber (WCAG AA: #B45309 verified in Phase 16) */
.badge-stale  { background: #c0392b; color: #fff; } /* Red */
```

### Anti-Patterns to Avoid

- **Loading full 1.6MB tribal_aliases.json in the browser:** The 18,776-alias file is for the Python pipeline, not the web client. The web client uses the pre-filtered aliases embedded in `tribes.json`.
- **Using string-based DOM insertion for dynamic content:** Always use DOM methods (`createElement`, `textContent`) to prevent XSS. The existing `app.js` already follows this pattern correctly.
- **CDN dependencies:** No external CDN requests. Self-host Fuse.js to comply with XCUT-02 (indigenous data sovereignty, zero third-party tracking).
- **SPA routing complexity:** This is a single-page app with no routes. The `404.html` is only needed if GitHub Pages is configured for a custom domain and someone navigates to a subpath directly. For `docs/web/` deployment, a simple redirect from 404 back to index is sufficient.
- **Canvas particle system:** The React prototype had an `AnimatedBackground.tsx` with particle effects. The decision explicitly removes this: "the little particles can go."

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fuzzy search | Custom Levenshtein distance | Fuse.js | Scoring theory, weighted keys, threshold tuning, 7+ years of edge cases handled |
| ARIA combobox | None - must hand-build | W3C APG reference implementation | No vanilla JS library does this right. Follow the W3C pattern exactly. |
| Dark mode toggle | JavaScript theme switcher | `prefers-color-scheme` media query | Decision: auto dark mode, no manual toggle. Pure CSS. |
| File downloads | Blob URL generation | `<a download>` attribute | Same-origin DOCX files on GitHub Pages work with `download` attr. No Blob needed for static file serving. |
| Gzip compression | Manual compression | GitHub Pages serves gzipped automatically | GitHub Pages applies gzip/brotli to all text assets automatically. |
| Search index generation | Runtime index building | `Fuse.createIndex()` at build time or `build_web_index.py` | Pre-filter aliases in Python, embed in tribes.json, let Fuse index at runtime (592 items is fast enough). |

**Key insight:** The only library needed is Fuse.js. Everything else is vanilla HTML/CSS/JS following established web standards. The ARIA combobox must be hand-built because no lightweight vanilla JS library implements the full W3C APG combobox pattern correctly.

## Common Pitfalls

### Pitfall 1: Fuse.js Default Location/Distance Limits
**What goes wrong:** Search for "Navajo" works, but search for "Apsaalooke" (alias for Crow Nation) returns nothing because it appears in an alias field, not at string position 0.
**Why it happens:** Fuse.js defaults: `location: 0`, `distance: 100`. Pattern must appear within `threshold * distance` characters of position 0.
**How to avoid:** Set `ignoreLocation: true` in Fuse.js options.
**Warning signs:** Aliases in search results always rank below direct name matches.

### Pitfall 2: ARIA Combobox Version Mismatch
**What goes wrong:** Screen readers announce options incorrectly or don't announce the combobox role.
**Why it happens:** ARIA 1.0 put `role="combobox"` on a wrapper `<div>`. ARIA 1.2 puts `role="combobox"` directly on the `<input>`. Screen readers vary in which version they support.
**How to avoid:** Follow ARIA 1.2 pattern (role on input). Test with NVDA + Chrome and VoiceOver + Safari. The existing `index.html` already has `role="combobox"` on the input, which is the correct ARIA 1.2 placement.
**Warning signs:** Automated accessibility checkers (axe-core) report "required ARIA attributes missing" on the combobox.

### Pitfall 3: GitHub Pages Path Resolution
**What goes wrong:** Download links break because paths are relative to the repo root, not the `docs/web/` directory.
**Why it happens:** GitHub Pages can serve from `/docs` directory. Links like `tribes/internal/epa_100000001.docx` resolve relative to the HTML file location.
**How to avoid:** Use relative paths from `index.html` location: `tribes/internal/epa_100000001.docx`. Verify in the GitHub Actions workflow that files are copied to `docs/web/tribes/`.
**Warning signs:** 404 errors on download links in production but not in local testing.

### Pitfall 4: SquareSpace iframe Sandbox Restrictions
**What goes wrong:** Downloads don't work inside the SquareSpace iframe.
**Why it happens:** SquareSpace may apply `sandbox` attribute to iframes which blocks downloads by default.
**How to avoid:** The iframe embed code must include `sandbox="allow-scripts allow-same-origin allow-downloads allow-popups"`. Document this in the embed instructions. The existing HTML already includes iframe embed instructions in a comment.
**Warning signs:** Clicking download buttons inside SquareSpace does nothing. Console shows sandbox violation.

### Pitfall 5: Mobile Touch Target Sizes
**What goes wrong:** Users can't tap buttons reliably on mobile.
**Why it happens:** Buttons or listbox options are smaller than 44x44px (WCAG 2.5.5).
**How to avoid:** Set `min-height: 44px` (already done in existing CSS), ensure combobox options have `padding: 0.75rem` minimum.
**Warning signs:** Difficulty tapping specific items in the dropdown list on mobile Safari.

### Pitfall 6: CLS from Dynamically Rendered Content
**What goes wrong:** Search results or Tribe cards appearing push content down, causing layout shift.
**Why it happens:** No space reserved for dynamic content.
**How to avoid:** Use `min-height` on the results container, or insert results below the fold. The existing design places the card below the search area, which is acceptable. Avoid inserting content between the search box and scroll position.
**Warning signs:** CLS > 0.1 in Lighthouse audit.

### Pitfall 7: tribal_aliases.json vs. tribes.json Confusion
**What goes wrong:** Build script loads the wrong file, or web client tries to load the 1.6MB Python alias file.
**Why it happens:** Two similar files exist: `data/tribal_aliases.json` (Python pipeline, 1.6MB, 18,776 aliases) and `docs/web/data/tribes.json` (web client, ~28KB gzipped, 10 aliases per Tribe).
**How to avoid:** The `build_web_index.py` script must be enhanced to read `tribal_aliases.json`, filter to top 10 per Tribe, and embed them in `tribes.json`. The web client only ever fetches `data/tribes.json`.
**Warning signs:** Page load takes >2s on slow connections; network tab shows large JSON fetch.

## Code Examples

### Complete ARIA Combobox Skeleton
```javascript
// Source: W3C APG Combobox Pattern
// https://www.w3.org/WAI/ARIA/apg/patterns/combobox/examples/combobox-autocomplete-list/
function TribeCombobox(inputEl, listboxEl, fuseInstance) {
  this.input = inputEl;
  this.listbox = listboxEl;
  this.fuse = fuseInstance;
  this.options = [];
  this.activeIndex = -1;
  this._lastQuery = '';

  var self = this;
  this.input.addEventListener('input', function() { self.onInput(); });
  this.input.addEventListener('keydown', function(e) { self.onKeyDown(e); });
  this.input.addEventListener('blur', function() { self.onBlur(); });
  this.listbox.addEventListener('click', function(e) { self.onOptionClick(e); });
}

TribeCombobox.prototype.onInput = function() {
  var query = this.input.value.trim();
  if (query.length < 2) {
    this.close();
    return;
  }
  this._lastQuery = query;
  var results = this.fuse.search(query).slice(0, 15);
  this.renderOptions(results);
  this.open();
};

TribeCombobox.prototype.onKeyDown = function(e) {
  switch (e.key) {
    case 'ArrowDown':
      e.preventDefault();
      if (!this.isOpen()) this.onInput();
      else this.moveFocus(1);
      break;
    case 'ArrowUp':
      e.preventDefault();
      if (!this.isOpen()) this.onInput();
      else this.moveFocus(-1);
      break;
    case 'Enter':
      e.preventDefault();
      if (this.activeIndex >= 0) this.selectOption(this.activeIndex);
      break;
    case 'Escape':
      this.close();
      if (this.input.value) { this.input.value = ''; }
      break;
  }
};

TribeCombobox.prototype.moveFocus = function(delta) {
  var len = this.options.length;
  if (len === 0) return;
  // Clear previous
  if (this.activeIndex >= 0) {
    this.options[this.activeIndex].setAttribute('aria-selected', 'false');
  }
  // Calculate new index with wrapping
  this.activeIndex = (this.activeIndex + delta + len) % len;
  var opt = this.options[this.activeIndex];
  opt.setAttribute('aria-selected', 'true');
  this.input.setAttribute('aria-activedescendant', opt.id);
  opt.scrollIntoView({ block: 'nearest' });
};

TribeCombobox.prototype.renderOptions = function(results) {
  // Clear existing options using DOM methods
  while (this.listbox.firstChild) {
    this.listbox.removeChild(this.listbox.firstChild);
  }
  this.options = [];
  this.activeIndex = -1;

  var self = this;
  results.forEach(function(r, i) {
    var li = document.createElement('li');
    li.setAttribute('role', 'option');
    li.id = 'opt-' + i;
    li.setAttribute('aria-selected', 'false');
    li.textContent = r.item.name;
    // Show state(s) as secondary text
    if (r.item.states && r.item.states.length) {
      var span = document.createElement('span');
      span.className = 'option-state';
      span.textContent = r.item.states.join(', ');
      li.appendChild(span);
    }
    self.listbox.appendChild(li);
    self.options.push(li);
  });
  this.input.setAttribute('aria-activedescendant', '');
};

TribeCombobox.prototype.selectOption = function(index) {
  var results = this.fuse.search(this._lastQuery);
  var item = results[index];
  if (item) {
    this.input.value = item.item.name;
    this.close();
    this.onTribeSelected(item.item);
  }
};

TribeCombobox.prototype.open = function() {
  this.listbox.hidden = false;
  this.input.setAttribute('aria-expanded', 'true');
};

TribeCombobox.prototype.close = function() {
  this.listbox.hidden = true;
  this.input.setAttribute('aria-expanded', 'false');
  this.activeIndex = -1;
  this.input.setAttribute('aria-activedescendant', '');
};

TribeCombobox.prototype.isOpen = function() {
  return !this.listbox.hidden;
};

TribeCombobox.prototype.onBlur = function() {
  // Delay to allow option click to register
  var self = this;
  setTimeout(function() { self.close(); }, 200);
};

TribeCombobox.prototype.onOptionClick = function(e) {
  var li = e.target.closest('[role="option"]');
  if (li) {
    var idx = this.options.indexOf(li);
    if (idx >= 0) this.selectOption(idx);
  }
};

TribeCombobox.prototype.onTribeSelected = function(tribe) {
  // Override in main app to show card
};
```

### Download Both Documents Pattern
```javascript
// Trigger sequential downloads with delay to avoid browser blocking
function downloadBoth(docA_path, docB_path, tribeName) {
  var safeName = tribeName.replace(/[^a-zA-Z0-9 _-]/g, '').replace(/\s+/g, '_');

  var a1 = document.createElement('a');
  a1.href = 'tribes/' + docA_path;
  a1.download = safeName + '_Internal_Strategy.docx';
  document.body.appendChild(a1);
  a1.click();
  document.body.removeChild(a1);

  setTimeout(function() {
    var a2 = document.createElement('a');
    a2.href = 'tribes/' + docB_path;
    a2.download = safeName + '_Congressional_Overview.docx';
    document.body.appendChild(a2);
    a2.click();
    document.body.removeChild(a2);
  }, 300);
}
```

### GitHub Actions Deployment Workflow
```yaml
# .github/workflows/deploy-website.yml
name: Deploy Website

on:
  push:
    branches: [main]
    paths:
      - 'docs/web/**'
      - 'outputs/packets/**'
      - 'scripts/build_web_index.py'

permissions:
  contents: write
  pages: write
  id-token: write

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Build web index (tribes.json with aliases)
        run: python scripts/build_web_index.py

      - name: Copy DOCX files to docs/web/tribes/
        run: |
          mkdir -p docs/web/tribes/internal
          mkdir -p docs/web/tribes/congressional
          mkdir -p docs/web/tribes/regional/internal
          mkdir -p docs/web/tribes/regional/congressional
          cp outputs/packets/internal/*.docx docs/web/tribes/internal/ 2>/dev/null || true
          cp outputs/packets/congressional/*.docx docs/web/tribes/congressional/ 2>/dev/null || true
          cp outputs/packets/regional/internal/*.docx docs/web/tribes/regional/internal/ 2>/dev/null || true
          cp outputs/packets/regional/congressional/*.docx docs/web/tribes/regional/congressional/ 2>/dev/null || true

      - name: Commit and push
        run: |
          git config user.name "TCR Policy Scanner"
          git config user.email "scanner@tcr-policy-scanner.local"
          git add docs/web/
          if git diff --cached --quiet; then
            echo "No changes to commit"
          else
            git commit -m "chore: deploy website ($(date -u +%Y-%m-%d))"
            git push
          fi
```

### build_web_index.py Enhancement (Alias Embedding)
```python
# Add to build_web_index.py: embed top 10 filtered aliases per Tribe
from collections import defaultdict

def _load_filtered_aliases(aliases_path, max_per_tribe=10):
    """Load tribal_aliases.json and return top aliases per tribe_id.

    Filters out housing authority variants and keeps the shortest
    unique aliases (most likely to be searched by users).
    """
    if not aliases_path.is_file():
        return {}
    size = aliases_path.stat().st_size
    if size > 10 * 1024 * 1024:
        return {}
    with open(aliases_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    alias_dict = data.get("aliases", {})

    reverse = defaultdict(list)
    for alias_str, tid in alias_dict.items():
        if "housing" not in alias_str:
            reverse[tid].append(alias_str)

    result = {}
    for tid, aliases in reverse.items():
        aliases.sort(key=len)
        result[tid] = aliases[:max_per_tribe]
    return result
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| ARIA 1.0 combobox (role on wrapper div) | ARIA 1.2 combobox (role on input) | 2023+ | Must use ARIA 1.2 pattern for modern screen readers |
| Awesomplete (2019) | Custom ARIA combobox + Fuse.js | Decision for this phase | Better WCAG compliance, typo tolerance |
| Framework SPA (React) | Enhanced vanilla HTML/JS/CSS | Decision for this phase | Zero build step, <500KB total, simpler deployment |
| Manual dark mode toggle | `prefers-color-scheme` auto | 2024+ best practice | No JavaScript toggle code, respects OS preference |
| INP replaces FID | Core Web Vitals 2024+ | March 2024 | Interaction to Next Paint replaces First Input Delay. Static site with minimal JS should pass easily. |

**Deprecated/outdated:**
- **Awesomplete v1.1.5 (2019):** Unmaintained, ARIA 1.0 era. Replace.
- **Canvas particle effects:** Removed per user decision. CSS-only scan-line effect replaces it.
- **React/Vite prototype in `.planning/website/`:** Decision: do not use. Reference for UX patterns only.

## Size Budget Analysis

**Target:** <500KB gzipped total

| Asset | Raw Size | Gzipped (est.) | Notes |
|-------|----------|-----------------|-------|
| `index.html` | ~5 KB | ~2 KB | Single HTML file |
| `style.css` | ~8 KB | ~2 KB | Existing 48 lines + dark mode + badges |
| `fuse.min.js` | 25.8 KB | ~8 KB | Self-hosted Fuse.js 7.1.0 |
| `app.js` | ~15 KB | ~5 KB | Enhanced from 125 lines |
| `combobox.js` | ~5 KB | ~2 KB | Custom ARIA combobox |
| `tribes.json` | ~260 KB | ~28 KB | 592 Tribes + 10 aliases each + doc metadata |
| **Total JS/CSS/HTML/JSON** | **~319 KB** | **~47 KB** | Well within 500KB budget |
| DOCX files (992) | ~150 MB | N/A | Downloaded on demand, not counted in page load |

**Conclusion:** Total page weight estimated at ~47KB gzipped. This is **less than 10% of the 500KB budget**, leaving ample headroom.

## Open Questions

1. **GitHub Pages configuration method**
   - What we know: Repository uses `docs/` directory pattern. The existing `generate-packets.yml` workflow copies files to `docs/web/tribes/`.
   - What's unclear: Whether GitHub Pages is already enabled for this repo, and whether it's configured to serve from `docs/` root or `docs/web/` subdirectory. The default GitHub Pages URL would be `https://atniclimate.github.io/TCR-policy-scanner/`.
   - Recommendation: Verify in GitHub repo settings. If serving from `docs/`, then the site lives at `/TCR-policy-scanner/` and all paths need to be relative. If serving from `docs/web/`, base path may differ.

2. **DOCX files in Git**
   - What we know: The `generate-packets.yml` workflow commits DOCX files to `docs/web/tribes/`. This means ~150MB of binary files in Git history.
   - What's unclear: Whether this is acceptable long-term or if Git LFS should be used.
   - Recommendation: For now, the existing workflow pattern works. If repo size becomes problematic, consider Git LFS or an artifact-based deployment.

3. **Per-Tribe `generated_at` timestamp for freshness badges**
   - What we know: `build_web_index.py` includes a top-level `generated_at` but no per-Tribe timestamp.
   - What's unclear: Whether per-Tribe timestamps are available from the packet generation pipeline.
   - Recommendation: Enhance `build_web_index.py` to read each DOCX file's modification time and embed it as `generated_at` per Tribe entry. Alternatively, use the top-level `generated_at` for all Tribes (simpler but less granular).

4. **SPA routing necessity**
   - What we know: The site is a single page. No actual routes exist.
   - What's unclear: Whether a `404.html` is needed for GitHub Pages.
   - Recommendation: Create a minimal `404.html` that redirects to `index.html`. This handles any edge cases with direct URL navigation and is standard practice for GitHub Pages SPAs.

## Sources

### Primary (HIGH confidence)
- Context7 `/websites/fusejs_io` - Fuse.js API options, weighted search, scoring theory, indexing, nested keys
- [W3C APG Combobox Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/combobox/) - ARIA roles, keyboard interaction, DOM structure
- [W3C APG Combobox with List Autocomplete](https://www.w3.org/WAI/ARIA/apg/patterns/combobox/examples/combobox-autocomplete-list/) - Reference implementation
- [Fuse.js Official Docs](https://www.fusejs.io/) - Installation, options, CDN URLs
- [jsDelivr CDN File Listing](https://cdn.jsdelivr.net/npm/fuse.js/dist/) - Exact file sizes for Fuse.js 7.1.0 distribution
- Existing codebase analysis: `docs/web/`, `scripts/build_web_index.py`, `src/packets/doc_types.py`, `data/tribal_registry.json`, `data/tribal_aliases.json`, `.github/workflows/generate-packets.yml`

### Secondary (MEDIUM confidence)
- [GitHub Awesomplete Repository](https://github.com/LeaVerou/awesomplete) - Last release 2019, maintenance status
- [MDN prefers-color-scheme](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@media/prefers-color-scheme) - Dark mode media query
- [MDN Content-Security-Policy sandbox](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/sandbox) - iframe sandbox permissions
- [web.dev Core Web Vitals](https://web.dev/articles/top-cwv) - LCP, CLS, INP optimization
- [W3C ARIA 1.1 Combobox Issues](https://github.com/w3c/aria/wiki/Resolving-ARIA-1.1-Combobox-Issues) - ARIA version differences

### Tertiary (LOW confidence)
- [spa-github-pages](https://github.com/rafgraph/spa-github-pages) - 404.html SPA routing hack for GitHub Pages
- [CRT CSS Effect](https://aleclownes.com/2017/02/01/crt-display.html) - Scan-line CSS technique

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** - Fuse.js verified via Context7 + official docs. ARIA combobox pattern from W3C APG. All sizing calculations from actual data analysis.
- Architecture: **HIGH** - Builds on existing codebase (`build_web_index.py`, `app.js`, `generate-packets.yml`). Data sizing confirmed via Python analysis of actual tribal_aliases.json.
- Pitfalls: **HIGH** - Fuse.js `ignoreLocation` verified in Context7 docs. ARIA version issues documented by W3C. GitHub Pages behavior confirmed from existing workflow.

**Research date:** 2026-02-12
**Valid until:** 2026-03-12 (stable domain: vanilla JS, Fuse.js, ARIA standards)
