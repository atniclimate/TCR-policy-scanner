# Marie Kondo Code Hygiene Sweep Summary

## Agent: Marie Kondo
**Date:** 2026-02-13
**Scope:** All Python source files (47 in src/), scripts (17 in scripts/), test files (32 in tests/), web files (docs/web/), config files, workflows

## Methodology

Three-pass inventory: (1) Python dependency audit against requirements.txt, (2) Code inventory for unused imports, dead functions, dead code paths, (3) Configuration inventory for unused keys and simplification opportunities.

## Joy Score

| Metric | Score |
|--------|-------|
| Current joy | 8/10 |
| Potential joy (after tidying) | 9/10 |

## Key Findings

### Pass 1: Python Dependencies (13 packages)

| Package | Status | Verdict |
|---------|--------|---------|
| aiohttp | Essential | Keep -- concurrent API scraping |
| pydantic | Essential | Keep -- congressional intel models |
| python-dateutil | Used | Keep -- date parsing across APIs |
| jinja2 | Used | Keep -- report templating |
| rapidfuzz | Essential | Keep -- Tribal name matching |
| pyyaml | Replaceable | Evaluate -- only 1 import site |
| python-docx | Essential | Keep -- DOCX generation core |
| openpyxl | Used | Keep -- Excel reports |
| requests | Replaceable | Evaluate -- only 2 download scripts |
| geopandas | Used | Keep -- build-time only |
| shapely | Used | Keep -- geopandas transitive |
| pyproj | Used | Keep -- geopandas transitive |
| pyogrio | Used | Keep -- geopandas I/O backend |

**Verdict:** 0 truly unused dependencies. 2 replaceable with stdlib (pyyaml, requests) but low priority.

### Pass 2: Python Code

**4 dead scripts identified** (safe to remove):
- `scripts/_add_curated_aliases_round3.py` -- one-time migration, applied
- `scripts/_add_curated_aliases_round4.py` -- one-time migration, applied
- `scripts/_add_curated_aliases_round5.py` -- one-time migration, applied
- `scripts/_add_curated_aliases_tmp.py` -- temporary script, completed

**1 consolidation opportunity:**
- CFDA_NUMBERS (grants_gov.py) and CFDA_TO_PROGRAM (usaspending.py) are near-duplicates. Consider extracting to a shared module.

**1 backward-compat alias:**
- `src/config.py` re-exports `PROJECT_ROOT` from `src/paths.py`. New code should import from paths directly.

**No unused imports found** in source files. All imports verified against usage.
**No dead functions found** -- all exported functions are imported or called.
**No TODO/FIXME comments for resolved issues** found in source code.

### Pass 3: Configuration

- Manifest generation code duplicated between two GitHub Actions workflows (~20 lines). Acceptable for CI readability.
- No unused config JSON keys found in scanner_config.json.
- No unused web files -- all HTML/CSS/JS files are referenced.

## Recommendations (Priority Order)

1. **Remove 4 dead alias scripts** -- safe, no dependencies, reduces scripts/ directory clutter
2. **Extract shared CFDA mapping** -- reduces duplication between scrapers
3. **Migrate PROJECT_ROOT imports** to use src.paths directly (gradual)
4. **Consider pyyaml/requests replacement** with stdlib (low priority)

## What Sparks Joy

- Clean module architecture: scrapers, analysis, graph, monitors, packets, reports
- 964 tests with 100% pass rate
- Atomic write patterns throughout
- Consistent logging with getLogger(__name__)
- Path constants centralized in src/paths.py
- Zero external dependencies in the web frontend (system fonts, bundled Fuse.js)
- 592 Tribal Nations served with exactly the documents they need

**A tidy codebase is a trustworthy codebase. This one is already close to perfect.**
