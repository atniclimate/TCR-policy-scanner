# Phase 10: Code Quality - Research

**Researched:** 2026-02-11
**Domain:** Python linting (ruff), data completeness, dead code removal
**Confidence:** HIGH

## Summary

Phase 10 addresses two requirements: completing program_inventory.json field coverage (QUAL-01) and achieving a ruff-clean codebase with no dead code (QUAL-02). Research investigated the current state of both and found the scope is well-bounded.

For QUAL-01, the inventory has **5 programs with null CFDA numbers** out of 16 total. All 16 already have non-null `access_type` and `funding_type` fields, so only `cfda` needs attention. The 5 null-CFDA programs are: `irs_elective_pay`, `fema_tribal_mitigation`, `noaa_tribal`, `usbr_tap`, and `epa_tribal_air`. Some of these may legitimately lack a single CFDA number (e.g., IRS Elective Pay is a tax provision, not a grant program), so the plan must decide between populating actual CFDA numbers, using "N/A" sentinel values, or documenting why null is intentional.

For QUAL-02, ruff check currently reports **70 violations across 27 files**, broken down as: 35 unused imports (F401), 19 f-strings without placeholders (F541), 8 module-import-not-at-top (E402), 7 unused variables (F841), and 1 ambiguous variable name (E741). Of the 70, **54 are auto-fixable** via `ruff check --fix`. The remaining 16 require manual intervention (7 unused variables need `--unsafe-fixes`, 8 E402 violations in scripts/ need `per-file-ignores` config, 1 E741 needs variable rename).

**Primary recommendation:** Create a `pyproject.toml` with ruff configuration (target Python 3.12, per-file-ignores for scripts/), run `ruff check --fix` for the 54 auto-fixable violations, manually fix the remaining 16, then verify all 383 tests still pass.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| ruff | 0.15.0 | Python linter and formatter | Installed on this system; replaces flake8/pylint/isort with 10-100x speed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | (existing) | Test runner | Verify no regressions after cleanup |
| pyproject.toml | N/A | Ruff configuration home | Standard Python project config location |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pyproject.toml | ruff.toml | ruff.toml uses `[lint]` syntax without `[tool.ruff]` prefix; pyproject.toml is more standard for Python projects and can hold future tool configs |

**Installation:**
```bash
pip install ruff  # Already installed (v0.15.0)
```

## Architecture Patterns

### Recommended ruff Configuration

The project currently has **no ruff configuration file**. Default rules (`E4`, `E7`, `E9`, `F`) are being applied. A `pyproject.toml` should be created with:

```toml
[tool.ruff]
target-version = "py312"
line-length = 120

[tool.ruff.lint]
select = ["E4", "E7", "E9", "F"]

[tool.ruff.lint.per-file-ignores]
"scripts/*.py" = ["E402"]
```

**Key design decisions:**

1. **`target-version = "py312"`** - Project uses Python 3.12+ (confirmed by `list[str]` type hints in source, Python 3.13 on system)
2. **`line-length = 120`** - Existing code exceeds 88 chars frequently; 120 is pragmatic
3. **`per-file-ignores` for `scripts/`** - All 4 scripts use the `sys.path.insert()` pattern (DEC-0902-01) which requires imports after `sys.path` manipulation. Ruff's E402 exception only works for bare `sys.path.insert()` at module level, not inside `if` blocks. The scripts wrap it in `if str(_PROJECT_ROOT) not in sys.path:` which triggers E402
4. **Default rule set (`E4`, `E7`, `E9`, `F`)** - Matches ruff defaults; no need to add extra rules for this phase

### Pattern: Auto-fix then Manual Fix

```
Step 1: ruff check --fix .           # Auto-fixes 54 violations (F401, F541)
Step 2: Manual fixes for F841 (7)    # Remove unused variable assignments
Step 3: Manual fix for E741 (1)      # Rename ambiguous variable 'l' -> 'line'
Step 4: python -m pytest tests/ -q   # Verify 383 tests still pass
Step 5: ruff check .                 # Verify zero violations
```

### Anti-Patterns to Avoid
- **Blanket `# noqa` comments:** Do not suppress violations with inline comments. Fix them.
- **Adding `--unsafe-fixes` to auto-fix F841:** These need human review because removing an assignment could have side effects (e.g., function call for side effect). Review each F841 manually.
- **Ignoring E402 globally:** Only ignore in `scripts/` directory where the pattern is intentional.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Finding unused imports | Manual grep | `ruff check --select F401` | Ruff handles re-exports, `__all__`, conditional imports |
| Auto-removing imports | Manual editing | `ruff check --fix` | Handles comma cleanup, blank lines |
| CFDA number lookup | Web scraping | SAM.gov Assistance Listings | Official federal source of CFDA/ALN numbers |

**Key insight:** Ruff's `--fix` handles 77% of violations automatically and correctly. Manual intervention is only needed for unused variables and the E741 rename.

## Common Pitfalls

### Pitfall 1: Auto-fixing F401 breaks re-exports
**What goes wrong:** `ruff check --fix` removes an import that is used by downstream modules via re-export
**Why it happens:** Ruff may not detect all re-export patterns (especially those not listed in `__all__`)
**How to avoid:** The project already uses `__all__` in `src/schemas/__init__.py` and `src/config.py`, which ruff respects. Run tests after fix to catch any breakage.
**Warning signs:** ImportError in test suite after auto-fix

### Pitfall 2: Removing unused variable that has side effects
**What goes wrong:** Code like `engine = DocxEngine(config, programs)` assigns to unused variable, but the constructor has side effects (creates output directory)
**Why it happens:** F841 flags the variable as unused, but the RHS call matters
**How to avoid:** Review each F841 violation manually. For side-effect-only calls, either use `_` prefix (`_engine = ...`) or remove the assignment and keep just the call
**Warning signs:** Test `test_docx_styles.py:373` creates DocxEngine for its side effect (output dir creation). Removing the assignment is fine; removing the call breaks the test.

### Pitfall 3: CFDA numbers that legitimately don't exist
**What goes wrong:** Filling in a CFDA for a program that doesn't have one (e.g., IRS Elective Pay is a tax provision under IRC Section 6417, not a grant with a CFDA)
**Why it happens:** Requirement says "non-null" but some programs genuinely lack CFDAs
**How to avoid:** Use "N/A" string for programs without CFDAs, with a comment in the JSON explaining why. Or use a sentinel like "N/A - Tax Provision" to be self-documenting.
**Warning signs:** Downstream code that parses CFDA as numeric will break on "N/A"

### Pitfall 4: E402 in scripts cannot be auto-fixed
**What goes wrong:** Attempting to restructure script imports to be at top of file
**Why it happens:** Scripts need `sys.path.insert()` BEFORE importing `src.*` modules. This is by design (DEC-0902-01).
**How to avoid:** Use `per-file-ignores` in pyproject.toml config rather than restructuring scripts
**Warning signs:** ImportError when running scripts directly if imports are moved above sys.path manipulation

### Pitfall 5: validate_data_integrity.py at project root
**What goes wrong:** Forgetting to include this file in cleanup scope
**Why it happens:** It's at the project root, not in `src/` or `tests/`
**How to avoid:** Include it explicitly in the cleanup scope. It has 7 violations (4 unused typing imports, 2 f-string, 1 unused variable)
**Warning signs:** `ruff check .` still reports violations after "fixing everything in src/"

## Code Examples

### Creating pyproject.toml with ruff config
```toml
# pyproject.toml - Ruff linter configuration for TCR Policy Scanner
[tool.ruff]
target-version = "py312"
line-length = 120

[tool.ruff.lint]
# Default rule set: pycodestyle errors + pyflakes
select = ["E4", "E7", "E9", "F"]

[tool.ruff.lint.per-file-ignores]
# Scripts use sys.path.insert() pattern (DEC-0902-01) requiring imports after path manipulation
"scripts/*.py" = ["E402"]
```

### Fixing F541 (f-string without placeholders)
```python
# Before (violation):
print(f"\nSources to scan:")

# After (fixed):
print("\nSources to scan:")
```

### Fixing F841 (unused variable) - side effect case
```python
# Before (violation):
engine = DocxEngine(config, programs)  # F841: unused

# After (fixed - keep call, discard assignment):
DocxEngine(config, programs)  # Side effect: creates output dir
# OR use underscore prefix:
_engine = DocxEngine(config, programs)
```

### Fixing E741 (ambiguous variable name)
```python
# Before (violation):
test_lines = [l for l in output.split("\n") if "::" in l and "test_" in l]

# After (fixed):
test_lines = [line for line in output.split("\n") if "::" in line and "test_" in line]
```

### Fixing F401 in src/scrapers/base.py (import used elsewhere)
```python
# Before:
from datetime import datetime, timedelta, timezone  # timedelta unused HERE
from src.paths import CFDA_TRACKER_PATH  # unused HERE but re-exported

# After:
from datetime import datetime, timezone
# CFDA_TRACKER_PATH import removed (callers import directly from src.paths)
```
Note: Verify `src/scrapers/grants_gov.py` imports `CFDA_TRACKER_PATH` from `src.scrapers.base` -- if so, that import chain needs updating. Current code: `from src.scrapers.base import BaseScraper, check_zombie_cfda, CFDA_TRACKER_PATH` -- this imports it from base, so removing from base.py would break grants_gov.py. **Action:** Update grants_gov.py to import CFDA_TRACKER_PATH directly from src.paths instead.

## Current State Inventory

### Violation Breakdown by File (27 files)

| Count | File | Violations |
|-------|------|------------|
| 13 | tests/test_schemas.py | F541 (13) |
| 7 | validate_data_integrity.py | F401 (4), F541 (2), F841 (1) |
| 4 | scripts/build_congress_cache.py | E402 (3), F841 (1) |
| 4 | src/main.py | F541 (4) |
| 4 | src/packets/docx_hotsheet.py | F401 (4) |
| 4 | src/packets/orchestrator.py | F541 (4) |
| 3 | src/packets/docx_engine.py | F401 (3) |
| 3 | tests/test_e2e_phase8.py | F401 (2), F841 (1) |
| 2 | scripts/build_registry.py | E402 (2) |
| 2 | src/packets/docx_sections.py | F401 (2) |
| 2 | src/packets/hazards.py | F401 (2) |
| 2 | src/scrapers/base.py | F401 (2) |
| 2 | tests/test_batch_generation.py | F401 (2) |
| 2 | tests/test_docx_hotsheet.py | F401 (2) |
| 2 | tests/test_docx_integration.py | E741 (1), F841 (1) |
| 2 | tests/test_docx_styles.py | F401 (1), F841 (1) |
| 2 | tests/test_strategic_overview.py | F401 (1), F841 (1) |
| 1 | scripts/build_tribal_aliases.py | E402 (1) |
| 1 | scripts/build_web_index.py | E402 (1) |
| 1 | src/packets/docx_styles.py | F401 (1) |
| 1 | src/reports/generator.py | F541 (1) |
| 1 | src/scrapers/grants_gov.py | F401 (1) |
| 1 | tests/test_change_tracking.py | F401 (1) |
| 1 | tests/test_decision_engine.py | F401 (1) |
| 1 | tests/test_doc_assembly.py | F401 (1) |
| 1 | tests/test_packets.py | F841 (1) |
| 1 | tests/test_web_index.py | F401 (1) |

### Violation Summary by Rule

| Rule | Count | Auto-fixable | Description |
|------|-------|-------------|-------------|
| F401 | 35 | Yes (--fix) | Unused imports |
| F541 | 19 | Yes (--fix) | f-string without placeholders |
| E402 | 8 | No (per-file-ignores) | Module import not at top |
| F841 | 7 | No (manual) | Unused local variable |
| E741 | 1 | No (manual) | Ambiguous variable name |
| **Total** | **70** | **54 auto / 16 manual** | |

### Program Inventory Field Status

| Program ID | cfda | access_type | funding_type |
|-----------|------|-------------|--------------|
| bia_tcr | 15.156 | direct | Discretionary |
| fema_bric | ["97.047","97.039"] | competitive | One-Time |
| **irs_elective_pay** | **null** | direct | Mandatory |
| epa_stag | 66.468 | direct | Discretionary |
| epa_gap | 66.926 | direct | Discretionary |
| **fema_tribal_mitigation** | **null** | direct | Discretionary |
| dot_protect | 20.284 | tribal_set_aside | Discretionary |
| usda_wildfire | 10.720 | competitive | One-Time |
| doe_indian_energy | 81.087 | direct | Discretionary |
| hud_ihbg | 14.867 | direct | Discretionary |
| **noaa_tribal** | **null** | competitive | Discretionary |
| fhwa_ttp_safety | 20.205 | direct | Discretionary |
| usbr_watersmart | 15.507 | competitive | Discretionary |
| **usbr_tap** | **null** | direct | Discretionary |
| bia_tcr_awards | 15.124 | direct | Discretionary |
| **epa_tribal_air** | **null** | direct | Discretionary |

**5 programs need CFDA resolution:**
1. `irs_elective_pay` - IRC Section 6417 tax provision (may not have traditional CFDA)
2. `fema_tribal_mitigation` - FEMA hazard mitigation planning (likely 97.039 or 97.047, same as BRIC)
3. `noaa_tribal` - Umbrella for multiple NOAA programs (may need multiple CFDAs or primary one)
4. `usbr_tap` - Bureau of Reclamation Technical Assistance (may be sub-program of WaterSMART 15.507)
5. `epa_tribal_air` - Clean Air Act Section 105 Tribal grants (likely 66.038)

### Test Baseline
- **383 tests collected, 383 passed** (as of research date)
- Test time: ~32 seconds
- All tests must still pass after cleanup

### Source File Count
- `src/` directory: 43 Python files (including `__init__.py` files)
- `tests/` directory: 14 Python files
- `scripts/` directory: 4 Python files
- Project root: 1 Python file (`validate_data_integrity.py`)
- **Total: 62 Python files**

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| flake8 + isort + pylint | ruff (single tool) | 2023+ | 10-100x faster, single config |
| setup.cfg for tool config | pyproject.toml | PEP 518 (2017) | Standard Python project config |
| CFDA numbers (5-digit) | ALN (Assistance Listing Numbers) | 2022 | Same format, different name; CFDA still widely used |

**Note:** The federal government renamed CFDA to "Assistance Listing Number" (ALN) in 2022, but the format remains the same (XX.XXX). The field name `cfda` in program_inventory.json is fine -- it's universally understood.

## Open Questions

1. **Should null CFDAs be "N/A" or actual numbers?**
   - What we know: 5 programs have null cfda. Some may genuinely lack a CFDA (IRS tax provision). Others likely have one we can look up.
   - What's unclear: Whether downstream code (relevance scoring, USASpending scraper CFDA matching) will handle "N/A" strings correctly
   - Recommendation: Research actual CFDA/ALN numbers for the 4 grant programs. Use "N/A" only for `irs_elective_pay` (tax provision, not a grant). Check `src/scrapers/usaspending.py` for how it uses CFDA numbers to ensure compatibility.

2. **Should E402 violations be suppressed via per-file-ignores or restructured?**
   - What we know: 8 E402 violations in 4 scripts, all caused by the `sys.path.insert()` pattern inside `if` blocks
   - What's unclear: Whether moving the `if` guard to a bare `sys.path.insert()` would satisfy ruff (it documents this as an exception)
   - Recommendation: Use `per-file-ignores` in pyproject.toml. The `if str(_PROJECT_ROOT) not in sys.path:` guard is defensive programming and should not be simplified just to satisfy the linter.

3. **CFDA_TRACKER_PATH import chain**
   - What we know: `src/scrapers/base.py` imports `CFDA_TRACKER_PATH` from `src.paths` but doesn't use it. `src/scrapers/grants_gov.py` imports it from `src.scrapers.base`.
   - What's unclear: Whether this is an intentional re-export or accidental
   - Recommendation: Update `grants_gov.py` to import directly from `src.paths`, then remove unused import from `base.py`. Verify with tests.

## Sources

### Primary (HIGH confidence)
- Context7 `/websites/astral_sh_ruff` - Configuration, per-file-ignores, E402 behavior, default rules
- Direct codebase analysis - All violation counts, file inventories, program_inventory.json field status
- `ruff --version` output: 0.15.0
- `python -m pytest tests/ --co -q`: 383 tests collected
- `python -m pytest tests/ -q`: 383 passed

### Secondary (MEDIUM confidence)
- Ruff default configuration documentation (Context7) - Default rule selection `["E4", "E7", "E9", "F"]`
- Ruff E402 exception for `sys.path` modifications - documented but the `if`-wrapped variant still triggers

### Tertiary (LOW confidence)
- CFDA/ALN numbers for the 5 null-CFDA programs - Need verification against SAM.gov Assistance Listings

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - ruff 0.15.0 installed and tested, all violations catalogued
- Architecture: HIGH - pyproject.toml config pattern well-documented by ruff
- Pitfalls: HIGH - Each pitfall verified against actual codebase violations
- CFDA research: MEDIUM - Likely numbers identified but need SAM.gov verification

**Research date:** 2026-02-11
**Valid until:** 2026-03-11 (stable domain, ruff config unlikely to change)
