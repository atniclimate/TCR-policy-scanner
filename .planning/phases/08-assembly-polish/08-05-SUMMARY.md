# Phase 8 Plan 5: Web Widget + CI Workflow (WEB-01/WEB-02/WEB-03) Summary

**One-liner:** Self-contained GitHub Pages search widget with Awesomplete autocomplete, tribes.json builder, weekly CI workflow, and SquareSpace embed docs -- all under 15KB

## Metadata

- **Phase:** 08-assembly-polish
- **Plan:** 05
- **Subsystem:** docs/web, scripts, CI
- **Tags:** web-widget, github-pages, awesomplete, autocomplete, ci, github-actions, squarespace
- **Requirements:** WEB-01, WEB-02, WEB-03

## Dependency Graph

- **Requires:** 08-03 (batch generation for packet files), 05-02 (tribal_registry.json)
- **Provides:** Static search widget, tribes.json index builder, weekly packet generation workflow
- **Affects:** 08-06 (final polish may reference widget), GitHub Pages deployment

## Tech Stack

- **Added:** Awesomplete 1.1.7 (vendored, MIT license) for autocomplete
- **Patterns:** No-framework vanilla JS widget, atomic JSON writes, GitHub Actions cron + dispatch

## Key Files

### Created

| File | Purpose |
|------|---------|
| `docs/web/index.html` | Semantic HTML5 search page with WCAG 2.1 AA accessibility |
| `docs/web/css/style.css` | Mobile-first responsive styles with TCR brand colors |
| `docs/web/css/awesomplete.css` | Vendored Awesomplete dropdown styles |
| `docs/web/js/app.js` | Widget logic: fetch, autocomplete init, card display, download |
| `docs/web/js/awesomplete.min.js` | Vendored Awesomplete library (MIT) |
| `scripts/build_web_index.py` | CLI to generate tribes.json from registry + packet directory |
| `.github/workflows/generate-packets.yml` | Weekly CI: generate packets, build index, deploy to Pages |
| `tests/test_web_index.py` | 7 tests for build_index() function |

## Tasks Completed

| Task | Name | Commit | Key Changes |
|------|------|--------|-------------|
| 1 | Create docs/web/ static widget | fc25ea2 | HTML, CSS, JS, vendored Awesomplete |
| 2 | Create scripts/build_web_index.py | 5d8302e | Index builder with atomic write, 10MB guard |
| 3 | Create generate-packets.yml | c3a917a | Weekly cron + manual dispatch workflow |
| 4 | Create tests/test_web_index.py | 588cecf | 7 tests, 279/279 total passing |
| 5 | Document SquareSpace embed | (in fc25ea2) | HTML comment with iframe code |
| - | CSS size optimization | 07101d0 | Trim to meet 15KB bundle target |

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Bundle CSS variables consolidated (--tcr-focus merged into --tcr-accent) | --tcr-focus and --tcr-primary-light were identical (#2980b9); saves bytes |
| tribe_id as primary key in build_index() | Registry uses tribe_id, not epa_id; matches actual tribal_registry.json schema |
| DEFAULT_PACKETS = outputs/packets (no /tribes subdirectory) | DocxEngine.save() writes to outputs/packets/{tribe_id}.docx per 08-03 deviation |
| Awesomplete vendored as minified JS (not CDN) | No external dependencies; self-contained widget requirement |
| Module export code removed from Awesomplete | AMD/CommonJS exports not needed for browser-only use; saves ~130 bytes |
| SquareSpace embed uses generic URL placeholder | User must update src URL to match their GitHub Pages deployment |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Corrected DEFAULT_PACKETS path**
- **Found during:** Task 2
- **Issue:** Plan specified `outputs/packets/tribes` but DocxEngine writes to `outputs/packets/`
- **Fix:** Set `DEFAULT_PACKETS = Path("outputs/packets")` per critical deviation instructions
- **Files modified:** `scripts/build_web_index.py`

**2. [Rule 3 - Blocking] Corrected workflow DOCX copy path**
- **Found during:** Task 3
- **Issue:** Plan specified `outputs/packets/tribes/*.docx` but files are at `outputs/packets/*.docx`
- **Fix:** `cp outputs/packets/*.docx docs/web/tribes/` per critical deviation instructions
- **Files modified:** `.github/workflows/generate-packets.yml`

**3. [Rule 1 - Bug] Registry uses tribe_id not epa_id**
- **Found during:** Task 2
- **Issue:** Plan mock used `epa_id` but actual tribal_registry.json uses `tribe_id` as primary key
- **Fix:** build_index() checks `tribe_id` first, then falls back to `epa_id` and `id`
- **Files modified:** `scripts/build_web_index.py`, `tests/test_web_index.py`

**4. [Rule 3 - Blocking] Bundle size exceeded 15KB target**
- **Found during:** Task 1 verification
- **Issue:** Initial widget was 19.3 KB with verbose CSS/JS/HTML
- **Fix:** Compacted CSS (minified selectors, merged variables), trimmed HTML whitespace, removed Awesomplete module exports
- **Files modified:** All docs/web/ files
- **Commits:** fc25ea2, 07101d0

## Verification Results

| Check | Result |
|-------|--------|
| `pytest tests/test_web_index.py -v` | 7/7 passed |
| `python scripts/build_web_index.py --help` | CLI displays correctly |
| YAML syntax validation | Valid |
| `pytest tests/ --tb=short` | 279/279 passed |
| SquareSpace embed in index.html | Present (line 44) |
| Widget bundle size | 15,330 bytes (14.97 KB) -- under 15KB |

## Test Coverage

- **New tests:** 7 (test_web_index.py)
- **Total tests:** 279 (272 existing + 7 new)
- **All passing:** Yes

## Metrics

- **Duration:** ~10 minutes
- **Completed:** 2026-02-10
- **Commits:** 5 task commits

## Next Phase Readiness

- Widget is ready for GitHub Pages deployment once repository is configured
- CI workflow requires CONGRESS_API_KEY and SAM_API_KEY secrets in repository settings
- 08-06 (final polish) can proceed independently
