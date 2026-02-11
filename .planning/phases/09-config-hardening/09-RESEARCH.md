# Phase 9: Config Hardening - Research

**Researched:** 2026-02-11
**Domain:** Python pathlib centralization, cross-platform path resolution
**Confidence:** HIGH

## Summary

Phase 9 is a pure code refactoring task that creates a centralized `src/paths.py` module replacing all scattered path construction across the codebase. The project currently uses 5 distinct path patterns (some good, some problematic), and the refactoring consolidates them into a single import source.

Research investigated every source file, test file, and script to catalog the exact path construction patterns in use today. The codebase has 52 Python source files across `src/` and 14 test files, with path-related code appearing in ~20 source files and ~6 test files. No external libraries are needed -- this is pure Python stdlib `pathlib` work.

**Primary recommendation:** Create `src/paths.py` as a flat module with `PROJECT_ROOT` at the top, directory constants grouped by domain, and helper functions for parameterized paths (cache files keyed by tribe_id). Every source and test file that constructs paths gets updated to import from `src.paths`. Verify with grep-based regression checks.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pathlib` | stdlib (3.12+) | Path construction, resolution, joining | Python standard library, cross-platform by design |
| `Path.__file__` | stdlib | Anchor project root to physical file location | Only reliable way to find project root regardless of cwd |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `os.replace()` | stdlib | Atomic file replacement | Already used in codebase for atomic writes; stays unchanged |
| `tempfile` | stdlib | Temporary files for atomic writes | Already used in codebase; stays unchanged |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `Path(__file__).resolve().parent.parent` | `.git` marker search | Fragile, fails in archives without `.git`; current approach is simpler and proven |
| Flat constants | Class-based `ProjectPaths` | Over-engineering for a project with one root; flat module is simpler and more Pythonic |
| Module-level constants | Env var `TCR_ROOT` override | Explicitly deferred per user decision; pure pathlib-relative only |

**Installation:** No new packages needed. Pure stdlib refactoring.

## Architecture Patterns

### Recommended paths.py Structure
```
src/
├── paths.py             # NEW: All path constants + helpers
├── config.py            # MODIFIED: imports PROJECT_ROOT from paths.py
├── main.py              # MODIFIED: imports paths from src.paths
├── ...                  # All other files: import from src.paths
```

### Pattern 1: Flat Constants Module
**What:** A single `src/paths.py` file defining `PROJECT_ROOT` and all derived path constants as module-level `Path` objects, organized by domain.
**When to use:** Always -- this is the only pattern for this phase.
**Example:**
```python
# src/paths.py
"""Centralized path constants for TCR Policy Scanner.

All file paths in the codebase resolve through this module.
Changing a data directory here propagates to all consumers.

No import-time validation -- callers get FileNotFoundError at usage time.
"""

from pathlib import Path

# ── Project Root ──
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
"""Absolute path to the project root directory (one level above src/)."""

# ── Config Paths ──
CONFIG_DIR: Path = PROJECT_ROOT / "config"
SCANNER_CONFIG_PATH: Path = CONFIG_DIR / "scanner_config.json"

# ── Data Paths ──
DATA_DIR: Path = PROJECT_ROOT / "data"
PROGRAM_INVENTORY_PATH: Path = DATA_DIR / "program_inventory.json"
POLICY_TRACKING_PATH: Path = DATA_DIR / "policy_tracking.json"
GRAPH_SCHEMA_PATH: Path = DATA_DIR / "graph_schema.json"
TRIBAL_REGISTRY_PATH: Path = DATA_DIR / "tribal_registry.json"
TRIBAL_ALIASES_PATH: Path = DATA_DIR / "tribal_aliases.json"
CONGRESSIONAL_CACHE_PATH: Path = DATA_DIR / "congressional_cache.json"
ECOREGION_CONFIG_PATH: Path = DATA_DIR / "ecoregion_config.json"
AIANNH_CROSSWALK_PATH: Path = DATA_DIR / "aiannh_tribe_crosswalk.json"
NRI_DIR: Path = DATA_DIR / "nri"
USFS_DIR: Path = DATA_DIR / "usfs"
AWARD_CACHE_DIR: Path = DATA_DIR / "award_cache"
HAZARD_PROFILES_DIR: Path = DATA_DIR / "hazard_profiles"
PACKET_STATE_DIR: Path = DATA_DIR / "packet_state"
CENSUS_DATA_PATH: Path = DATA_DIR / "census" / "tab20_cd11920_aiannh20_natl.txt"

# ── Output Paths ──
OUTPUTS_DIR: Path = PROJECT_ROOT / "outputs"
LATEST_RESULTS_PATH: Path = OUTPUTS_DIR / "LATEST-RESULTS.json"
LATEST_GRAPH_PATH: Path = OUTPUTS_DIR / "LATEST-GRAPH.json"
LATEST_MONITOR_DATA_PATH: Path = OUTPUTS_DIR / "LATEST-MONITOR-DATA.json"
CI_HISTORY_PATH: Path = OUTPUTS_DIR / ".ci_history.json"
CFDA_TRACKER_PATH: Path = OUTPUTS_DIR / ".cfda_tracker.json"
MONITOR_STATE_PATH: Path = OUTPUTS_DIR / ".monitor_state.json"
ARCHIVE_DIR: Path = OUTPUTS_DIR / "archive"
PACKETS_OUTPUT_DIR: Path = OUTPUTS_DIR / "packets"

# ── Docs Paths ──
DOCS_DIR: Path = PROJECT_ROOT / "docs"
WEB_DIR: Path = DOCS_DIR / "web"
WEB_DATA_DIR: Path = WEB_DIR / "data"
TRIBES_INDEX_PATH: Path = WEB_DATA_DIR / "tribes.json"

# ── Scripts Paths ──
SCRIPTS_DIR: Path = PROJECT_ROOT / "scripts"


# ── Helper Functions ──
# Encode naming conventions so callers don't construct ad-hoc paths.

def award_cache_path(tribe_id: str) -> Path:
    """Return the award cache JSON path for a specific Tribe."""
    return AWARD_CACHE_DIR / f"{tribe_id}.json"


def hazard_profile_path(tribe_id: str) -> Path:
    """Return the hazard profile JSON path for a specific Tribe."""
    return HAZARD_PROFILES_DIR / f"{tribe_id}.json"


def packet_state_path(tribe_id: str) -> Path:
    """Return the packet state JSON path for a specific Tribe."""
    return PACKET_STATE_DIR / f"{tribe_id}.json"
```

### Pattern 2: Config-Overridable Paths via scanner_config.json
**What:** Some modules (packets subsystem) allow paths to be overridden via `scanner_config.json`. After this refactoring, the _default_ values in the config fallback chain should reference `src.paths` constants, not hardcoded strings.
**When to use:** When a module reads a path from config with a fallback default.
**Example:**
```python
# BEFORE (current pattern in packets/awards.py):
_DEFAULT_ALIAS_PATH = "data/tribal_aliases.json"
alias_path = Path(awards_cfg.get("alias_path", _DEFAULT_ALIAS_PATH))

# AFTER (using paths.py):
from src.paths import TRIBAL_ALIASES_PATH
alias_path = Path(awards_cfg.get("alias_path", str(TRIBAL_ALIASES_PATH)))
# OR if config not present:
alias_path = TRIBAL_ALIASES_PATH  # default, no config lookup needed
```

**Decision point:** The config.json file itself still contains relative path strings like `"data/tribal_registry.json"` -- these are user-facing configuration values that stay as-is. The refactoring targets the _Python source code defaults_, not the JSON config schema. When config provides a path, the module uses it. When config doesn't, the module falls back to the `src.paths` constant instead of a hardcoded string.

### Pattern 3: Path Resolution for Config-Provided Strings
**What:** Some modules receive path strings from config that may be relative. These need resolution relative to `PROJECT_ROOT`.
**When to use:** When a path from config might be relative or absolute.
**Example:**
```python
# BEFORE (hazards.py _resolve_path):
def _resolve_path(raw_path: str) -> Path:
    p = Path(raw_path)
    if not p.is_absolute():
        p = Path(__file__).resolve().parent.parent.parent / p
    return p

# AFTER (using paths.py PROJECT_ROOT):
from src.paths import PROJECT_ROOT

def _resolve_path(raw_path: str) -> Path:
    p = Path(raw_path)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return p
```

### Anti-Patterns to Avoid
- **Ad-hoc `Path(__file__).resolve().parent.parent.parent`**: Every module computing its own project root is fragile and violates DRY. Currently found in `ecoregion.py` and `hazards.py`.
- **Bare `Path("outputs/...")` without anchoring**: Found in `change_detector.py`, `hot_sheets.py`, `base.py`, `generator.py`. These resolve relative to cwd, not project root -- they work when cwd is the project root but break otherwise.
- **Module-level path constants duplicating paths.py**: After migration, no file except `src/paths.py` should define `GRAPH_SCHEMA_PATH`, `OUTPUTS_DIR`, etc.
- **String-based path defaults in source code**: Strings like `"data/award_cache"` as Python-level defaults should be replaced by `src.paths` constant imports.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cross-platform path joining | String concatenation with `/` | `pathlib.Path / "child"` | Already used everywhere; just centralize |
| Project root detection | Marker file search (`.git`) | `Path(__file__).resolve().parent.parent` | Already working in `config.py`; proven pattern |
| Path validation at import time | Eager `.exists()` checks in paths.py | Let callers get `FileNotFoundError` | Per user decision; keeps paths.py pure |

**Key insight:** This phase is NOT building anything new -- it's consolidating existing proven patterns into a single module and removing duplicates.

## Common Pitfalls

### Pitfall 1: Circular Import Between config.py and paths.py
**What goes wrong:** If `paths.py` imports from `config.py` or vice versa in a cycle, Python raises `ImportError`.
**Why it happens:** Both modules are foundational; careless import ordering creates cycles.
**How to avoid:** `paths.py` imports NOTHING from the project (only `pathlib`). `config.py` imports `PROJECT_ROOT` from `paths.py`. All other modules import from whichever they need. The dependency graph is: `paths.py` <- `config.py` <- everything else. `paths.py` has zero internal imports.
**Warning signs:** `ImportError: cannot import name 'PROJECT_ROOT' from partially initialized module`.

### Pitfall 2: Bare Path("relative/...") Resolves from cwd, Not Project Root
**What goes wrong:** `Path("outputs/LATEST-RESULTS.json")` resolves relative to the current working directory, which varies (IDE, pytest, CI, scripts/).
**Why it happens:** Several existing modules use this pattern (change_detector.py, hot_sheets.py, base.py, generator.py). It works in practice because the project always runs from its root, but it's fragile.
**How to avoid:** Always anchor to `PROJECT_ROOT`: `OUTPUTS_DIR / "LATEST-RESULTS.json"` where `OUTPUTS_DIR = PROJECT_ROOT / "outputs"`.
**Warning signs:** `FileNotFoundError` when running tests from a subdirectory or when cwd differs.

### Pitfall 3: Tests Defining Their Own PROJECT_ROOT
**What goes wrong:** `tests/test_schemas.py` line 49 defines `PROJECT_ROOT = Path(__file__).resolve().parent.parent` independently of `src.paths`.
**Why it happens:** Test was written before paths.py existed.
**How to avoid:** After creating `src/paths.py`, update tests to `from src.paths import PROJECT_ROOT`. Test schemas that access real data files should use the same root.
**Warning signs:** Divergent PROJECT_ROOT values if file moves or project structure changes.

### Pitfall 4: Config JSON Paths vs Python Source Defaults
**What goes wrong:** Confusing which paths to migrate. The `scanner_config.json` file contains path strings like `"data/tribal_registry.json"` -- these are _user configuration_ and should NOT be changed. Only the _Python source code_ defaults (fallback values when config doesn't specify a path) should reference `src.paths`.
**Why it happens:** The boundary between "config schema values" and "Python code defaults" is subtle.
**How to avoid:** Rule: `scanner_config.json` is unchanged. Python source `_DEFAULT_*` string constants are replaced by `src.paths` imports. When a module reads from config and falls back, the fallback uses `src.paths`.
**Warning signs:** Accidentally changing the JSON schema or breaking config-driven path overrides.

### Pitfall 5: Grep Verification Missing Edge Cases
**What goes wrong:** Grep patterns for regression checking miss some hardcoded paths.
**Why it happens:** Path strings appear in many forms: `"data/"`, `'outputs/'`, `Path("config/")`, string literals in docstrings/comments.
**How to avoid:** Use multiple grep patterns and exclude known safe locations (comments, docstrings, test assertions that verify config values, scanner_config.json). Suggested patterns:
```bash
# Hardcoded directory path strings in source (excluding tests, config JSON, docs)
rg '"data/' src/ --glob '!__pycache__'
rg "'data/" src/ --glob '!__pycache__'
rg '"outputs/' src/ --glob '!__pycache__'
rg "'outputs/" src/ --glob '!__pycache__'
rg '"config/' src/ --glob '!__pycache__'
rg "'config/" src/ --glob '!__pycache__'
rg '"docs/' src/ --glob '!__pycache__'

# Independent PROJECT_ROOT definitions (should only be in paths.py)
rg 'Path\(__file__\).*parent.*parent' src/ --glob '!paths.py'

# Bare relative Path() without anchoring (fragile cwd-dependent)
rg 'Path\("(data|outputs|config|docs)/' src/ --glob '!paths.py'
```
**Warning signs:** New path strings introduced after migration go undetected.

### Pitfall 6: Windows vs Linux Path Separator in String Comparisons
**What goes wrong:** Tests or assertions comparing path strings with hardcoded `/` separators fail on Windows (or vice versa).
**Why it happens:** `str(Path("outputs/packets"))` produces `outputs\packets` on Windows.
**How to avoid:** Compare `Path` objects, not string representations. Where string comparison is needed, use `Path` normalization or `as_posix()`.
**Warning signs:** Test failures that only appear on one platform.

## Code Examples

### Example 1: Migration of main.py Path Constants
```python
# BEFORE (current src/main.py lines 31-38):
from src.config import PROJECT_ROOT
CONFIG_PATH = PROJECT_ROOT / "config" / "scanner_config.json"
INVENTORY_PATH = PROJECT_ROOT / "data" / "program_inventory.json"
GRAPH_OUTPUT_PATH = PROJECT_ROOT / "outputs" / "LATEST-GRAPH.json"
MONITOR_OUTPUT_PATH = PROJECT_ROOT / "outputs" / "LATEST-MONITOR-DATA.json"

# AFTER:
from src.paths import (
    SCANNER_CONFIG_PATH,
    PROGRAM_INVENTORY_PATH,
    LATEST_GRAPH_PATH,
    LATEST_MONITOR_DATA_PATH,
    PROJECT_ROOT,  # only if still needed directly
)
# ... use SCANNER_CONFIG_PATH etc. throughout the file
```

### Example 2: Migration of Bare Relative Paths
```python
# BEFORE (current src/analysis/change_detector.py line 13):
CACHE_FILE = Path("outputs/LATEST-RESULTS.json")

# AFTER:
from src.paths import LATEST_RESULTS_PATH
# Replace all uses of CACHE_FILE with LATEST_RESULTS_PATH
# Remove the CACHE_FILE definition
```

### Example 3: Migration of _resolve_path Pattern
```python
# BEFORE (current src/packets/hazards.py lines 96-109):
def _resolve_path(raw_path: str) -> Path:
    p = Path(raw_path)
    if not p.is_absolute():
        p = Path(__file__).resolve().parent.parent.parent / p
    return p

# AFTER:
from src.paths import PROJECT_ROOT

def _resolve_path(raw_path: str) -> Path:
    p = Path(raw_path)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return p
```

### Example 4: Migration of Config-Defaulted Paths
```python
# BEFORE (current src/packets/awards.py lines 30-31, 62-63):
_DEFAULT_ALIAS_PATH = "data/tribal_aliases.json"
_DEFAULT_CACHE_DIR = "data/award_cache"
# ...
alias_path = Path(awards_cfg.get("alias_path", _DEFAULT_ALIAS_PATH))
self.cache_dir = Path(awards_cfg.get("cache_dir", _DEFAULT_CACHE_DIR))

# AFTER:
from src.paths import TRIBAL_ALIASES_PATH, AWARD_CACHE_DIR

# Remove _DEFAULT_ALIAS_PATH, _DEFAULT_CACHE_DIR
# ...
alias_path = Path(awards_cfg.get("alias_path", str(TRIBAL_ALIASES_PATH)))
self.cache_dir = Path(awards_cfg.get("cache_dir", str(AWARD_CACHE_DIR)))
```

### Example 5: Migration of config.py
```python
# BEFORE (current src/config.py lines 16, 38):
from pathlib import Path
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

# AFTER:
from src.paths import PROJECT_ROOT
# Remove the local PROJECT_ROOT definition
# Keep all fiscal year logic unchanged
```

### Example 6: Migration of Test Files
```python
# BEFORE (tests/test_schemas.py line 49):
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# AFTER:
from src.paths import PROJECT_ROOT
```

### Example 7: Helper Functions for Parameterized Paths
```python
# Used by orchestrator when loading award/hazard caches:
from src.paths import award_cache_path, hazard_profile_path

# BEFORE:
cache_file = self.award_cache_dir / f"{tribe_id}.json"

# AFTER:
cache_file = award_cache_path(tribe_id)
```

## Inventory of Files Requiring Changes

### Files with Path Definitions to Migrate (source -> import from paths.py)

| File | Current Path Pattern | Constants/Lines Affected |
|------|---------------------|--------------------------|
| `src/config.py` | Defines `PROJECT_ROOT` | Line 38: move to paths.py, import back |
| `src/main.py` | 4 constants via `PROJECT_ROOT /` | Lines 35-38: CONFIG_PATH, INVENTORY_PATH, GRAPH_OUTPUT_PATH, MONITOR_OUTPUT_PATH; Line 105: schema_path |
| `src/graph/builder.py` | 1 constant via `PROJECT_ROOT /` | Line 26: GRAPH_SCHEMA_PATH |
| `src/reports/generator.py` | 3 bare relative paths | Lines 16-18: OUTPUTS_DIR, ARCHIVE_DIR, CI_HISTORY_PATH |
| `src/analysis/change_detector.py` | 1 bare relative path | Line 13: CACHE_FILE |
| `src/scrapers/base.py` | 1 bare relative path | Line 107: CFDA_TRACKER_PATH |
| `src/monitors/hot_sheets.py` | 1 bare relative path | Line 29: MONITOR_STATE_PATH |
| `src/packets/ecoregion.py` | 1 default string + `__file__` resolve | Line 14: _DEFAULT_CONFIG_PATH; Line 46: Path(__file__) resolve |
| `src/packets/registry.py` | 1 default string | Line 26: _DEFAULT_DATA_PATH |
| `src/packets/congress.py` | 1 default string | Line 18: _DEFAULT_CACHE_PATH |
| `src/packets/awards.py` | 2 default strings | Lines 30-31: _DEFAULT_ALIAS_PATH, _DEFAULT_CACHE_DIR |
| `src/packets/hazards.py` | 4 default strings + _resolve_path | Lines 52-55: _DEFAULT_*; Lines 96-109: _resolve_path |
| `src/packets/docx_engine.py` | 1 config-default string | Line 60: "outputs/packets" |
| `src/packets/change_tracker.py` | 1 default string | Line 60: Path("data/packet_state") |
| `src/packets/orchestrator.py` | 4 config-default strings + PROJECT_ROOT usage | Lines 59, 62, 501, 538, 576 |
| `src/packets/strategic_overview.py` | 3 PROJECT_ROOT constructions | Lines 85, 88, 91 |

### Test Files Requiring Updates

| File | Current Pattern | Change Needed |
|------|----------------|---------------|
| `tests/test_schemas.py` | Own `PROJECT_ROOT` definition (line 49) + data path construction (lines 55-93, 304-365) | Import from `src.paths` |
| `tests/test_docx_integration.py` | Uses `Path("config/scanner_config.json")` (line 606), `Path(__file__).parent.parent` (line 706) | Import from `src.paths` |
| `tests/test_doc_assembly.py` | Uses `Path(__file__).parent.parent` (line 691) | Import from `src.paths` |
| `tests/test_strategic_overview.py` | String path references in test helpers | Review for hardcoded path strings |

### Script Files (In Scope)

| File | Current Pattern | Change Needed |
|------|----------------|---------------|
| `scripts/build_registry.py` | `Path("data/tribal_registry.json")` default | Import from `src.paths` |
| `scripts/build_congress_cache.py` | 3 `Path("data/...")` defaults + CENSUS_LOCAL_PATH | Import from `src.paths` |
| `scripts/build_tribal_aliases.py` | 2 `Path("data/...")` constants | Import from `src.paths` |
| `scripts/build_web_index.py` | 3 `Path(...)` defaults | Import from `src.paths` |

### Files NOT Changing
- `scanner_config.json` -- user-facing config, paths stay as relative strings
- `src/packets/relevance.py` -- stateless, no file I/O
- `src/packets/context.py` -- dataclass, no file I/O
- `src/packets/docx_styles.py` -- styling constants, no file I/O
- `src/packets/docx_sections.py` -- rendering, no path construction
- `src/packets/docx_hotsheet.py` -- rendering, no path construction
- `src/packets/economic.py` -- computation, no file I/O
- `src/graph/schema.py` -- dataclasses, no file I/O
- `src/utils.py` -- formatting utilities, no path construction
- `src/scrapers/federal_register.py` -- uses base class, no own paths
- `src/scrapers/congress_gov.py` -- uses base class, no own paths
- `src/scrapers/usaspending.py` -- imports config but no path construction
- `src/monitors/iija_sunset.py` -- imports config but no path construction
- `src/monitors/reconciliation.py` -- no path construction
- `src/monitors/tribal_consultation.py` -- no path construction
- `src/monitors/dhs_funding.py` -- no path construction
- All `__init__.py` files -- no path construction

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `os.path.join()` string ops | `pathlib.Path / "child"` | Python 3.4+ (2014) | Codebase already uses pathlib exclusively |
| Per-module `__file__` resolution | Centralized `paths.py` | Standard practice ~2020+ | This phase implements it |
| String path defaults | Named path constants | Standard practice | Eliminates magic strings |

**Deprecated/outdated:**
- `os.path` for path construction: The project already uses `pathlib` exclusively. No `os.path` calls found in source.

## Open Questions

1. **Scripts import path: `src.paths` from scripts/?**
   - What we know: Scripts in `scripts/` are standalone CLI tools. They currently use bare relative paths like `Path("data/tribal_registry.json")`.
   - What's unclear: Whether `scripts/` can cleanly `from src.paths import ...` depends on how scripts are invoked (as modules or as standalone scripts).
   - Recommendation: Scripts should use `sys.path` insertion or be run as `python -m scripts.build_registry` to ensure `src.paths` is importable. Alternatively, scripts can define their own `PROJECT_ROOT = Path(__file__).resolve().parent.parent` and import constants from `src.paths` since the project is always structured the same way. The planner should decide the approach. Since scripts already use argparse defaults, this is a low-risk decision.

2. **Config-driven path override: str() wrapping**
   - What we know: When config provides a string and the module falls back to a `Path` constant, the config `.get()` default needs to be `str(CONSTANT)` since config values are strings.
   - What's unclear: Whether to keep config string-based fallbacks or just use `Path` constants directly when config key is absent.
   - Recommendation: Use `Path(cfg.get("key")) if cfg.get("key") else CONSTANT` pattern, avoiding the `str()` round-trip. This is cleaner and type-safe.

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection of all 52 source files and 14 test files
- Python pathlib documentation via Context7 `/python/cpython` -- Path.resolve() API
- Python official documentation: https://docs.python.org/3/library/pathlib.html

### Secondary (MEDIUM confidence)
- Web search: Python pathlib centralized path constants patterns 2025-2026
  - Multiple sources agree on `Path(__file__).resolve().parent.parent` as standard project root pattern
  - Flat constants module preferred over class-based approaches for single-root projects
  - Sources: [Real Python](https://realpython.com/python-pathlib/), [Python Tutorials](https://www.pythontutorials.net/blog/python-get-path-of-root-project-structure/)

### Tertiary (LOW confidence)
- None. All findings verified via direct codebase inspection.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Pure Python stdlib, no external dependencies; verified via codebase inspection
- Architecture: HIGH - patterns.py design directly derived from analyzing existing codebase patterns
- Pitfalls: HIGH - all pitfalls identified from actual code patterns found in the codebase
- File inventory: HIGH - every file inspected via grep + read; counts verified

**Research date:** 2026-02-11
**Valid until:** Indefinite (stdlib pathlib is stable; codebase inventory valid until next milestone)
