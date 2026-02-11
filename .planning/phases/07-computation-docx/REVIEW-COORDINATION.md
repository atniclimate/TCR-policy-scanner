# Phase 7 Review Coordination

## Section A: Organization Name Removal (Agent 1)

**Status:** COMPLETE
**Date:** 2026-02-10

### Files Modified (12 files)

1. `src/analysis/relevance.py`
2. `README.md`
3. `FY26_TCR_PolicyScanner_Reference.md`
4. `docs/CLAUDE-CODE-PROMPT.md`
5. `docs/STRATEGIC-FRAMEWORK.md`
6. `.planning/v1.1-session-prompt.md`
7. `.planning/MILESTONES.md`
8. `.planning/PROJECT.md`
9. `.planning/research/FEATURES.md`
10. `.planning/research/ARCHITECTURE.md`
11. `.planning/phases/05-foundation/TEAM1-epa-tribes-api.md`
12. `.planning/phases/07-computation-docx/07-RESEARCH.md`
13. `.github/workflows/daily-scan.yml` (found during sweep -- not in original 12)
14. `.planning/phases/02-data-model-graph/02-CONTEXT.md` (found during sweep -- not in original 12)

### Changes Made

| File | Line(s) | Old Text | New Text |
|------|---------|----------|----------|
| `src/analysis/relevance.py` | 3 | "against the [org] program inventory" | "against the tracked program inventory" |
| `README.md` | 10 | "16 programs tracked by a regional Tribal organization's climate resilience committee" | "16 programs tracked for Tribal Climate Resilience advocacy" |
| `README.md` | 17 | "against the [org] program inventory" | "against the tracked program inventory" |
| `README.md` | 50 | "github.com/[org-handle]/TCR-policy-scanner.git" | "<private repository URL>" |
| `README.md` | 84 | "Push this repo to `github.com/[org-handle]/TCR-policy-scanner`" | "Push this repo to your private repository" |
| `README.md` | 259 | "Tribal climate resilience committee" | "Project contributors" |
| `FY26_TCR_PolicyScanner_Reference.md` | 3 | "A regional Tribal organization \| Climate Resilience Committee" | "Tribal Climate Resilience \| Policy Scanner Reference" |
| `FY26_TCR_PolicyScanner_Reference.md` | 6 | "Repository: `github.com/[org-handle]/tcr-policy-scanner`" | "Repository: private repository" |
| `FY26_TCR_PolicyScanner_Reference.md` | 49 | "Prepared by Tribal climate resilience committee" | "Prepared by project contributors" |
| `docs/CLAUDE-CODE-PROMPT.md` | 10-12 | "[org] TCR Policy Scanner...a regional Tribal organization's climate resilience committee" | "TCR Policy Scanner...Tribal Climate Resilience program" |
| `docs/CLAUDE-CODE-PROMPT.md` | 14 | "github.com/[org-handle]/TCR-policy-scanner" | "private repository" |
| `docs/STRATEGIC-FRAMEWORK.md` | 1 | "# [org] TCR Policy Scanner" | "# TCR Policy Scanner" |
| `.planning/v1.1-session-prompt.md` | 12 | "organization conventions, organization sessions" | "policy conventions, advocacy sessions" |
| `.planning/v1.1-session-prompt.md` | 20 | "ECWS 2026, [org] Mid-Year" | "ECWS 2026, a policy convention" |
| `.planning/v1.1-session-prompt.md` | 40 | "event templates ([org], [org], ECWS" | "event templates (policy convention, advocacy session, ECWS" |
| `.planning/v1.1-session-prompt.md` | 46 | "Since [org] 2025 Mid-Year" | "Since the 2025 mid-year advocacy event" |
| `.planning/v1.1-session-prompt.md` | 52 | "from [org]/[org]" | "from Tribal advocacy organizations" |
| `.planning/v1.1-session-prompt.md` | 63 | "[org] produces" | "Tribal advocacy organizations produce" |
| `.planning/v1.1-session-prompt.md` | 106 | "since last [org]/[org] event" | "since last advocacy event" |
| `.planning/MILESTONES.md` | 28 | "attending [org], [org], ECWS" | "attending policy conventions, advocacy sessions, ECWS" |
| `.planning/PROJECT.md` | 7 | "Built for the Tribal climate resilience program" | "Built for the Tribal Climate Resilience program" |
| `.planning/PROJECT.md` | 58 | "Tribal climate resilience program (expanded from [org] in v1.1)" | "Tribal Climate Resilience program" |
| `.planning/PROJECT.md` | 59 | "github.com/[org-handle]/TCR-policy-scanner (private)" | "private repository" |
| `.planning/PROJECT.md` | 126 | "All 574 Tribes (not just [org]) \| program scope serves all" | "All 574 Tribes \| Program scope serves all" |
| `.planning/research/FEATURES.md` | 28 | "from [org]/[org] conventions" | "from Tribal advocacy conventions" |
| `.planning/research/FEATURES.md` | 89 | "Before [org] Mid-Year" | "Before a mid-year advocacy event" |
| `.planning/research/FEATURES.md` | 125 | "Since your [org] Mid-Year packet" | "Since your mid-year advocacy packet" |
| `.planning/research/FEATURES.md` | 325 | "[org] Tribal Unity Impact Days ([org].org URL)" | "Tribal advocacy organization impact days" |
| `.planning/research/ARCHITECTURE.md` | 520 | "Prepared for [Tribe] by [org]" | "Prepared for [Tribe]" |
| `.planning/phases/05-foundation/TEAM1-epa-tribes-api.md` | 301 | "Source 4: [org] Tribal Directory ([org].org URL)" | "Source 4: Tribal Advocacy Organization Directory" |
| `.planning/phases/05-foundation/TEAM1-epa-tribes-api.md` | 451 | "[org] Tribal Directory ([org].org URL)" | "Tribal advocacy organization directory" |
| `.planning/phases/07-computation-docx/07-RESEARCH.md` | 446 | "[org] 'Honor the Promises' framework" | "Tribal advocacy frameworks" |
| `.github/workflows/daily-scan.yml` | 37 | "scanner@[org-domain].org" | "scanner@tcr-policy-scanner.local" |
| `.planning/phases/02-data-model-graph/02-CONTEXT.md` | 10 | "github.com/[org-handle]/TCR-policy-scanner (private)" | "private repository" |

### Verification

```
grep -ri "NCAI\|ATNI" F:\tcr-policy-scanner --include="*.py" --include="*.md" --include="*.json"
```

**Result:** Zero matches in all 14 modified files (12 originally identified + 2 found during comprehensive sweep). Only 2 files still contain references:
- `REVIEW-COORDINATION.md` -- this coordination document (expected, as it describes the removal task)
- `PHASE7-SYSTEMIC-REVIEW-PROMPT.md` -- the task prompt itself (expected, as it defines the removal task)

All source code, documentation, planning, research, and CI/CD files are clean. No functional code behavior was changed -- only organization names in strings, comments, docstrings, documentation, and git config were replaced with neutral equivalents.

**Comprehensive sweep performed:** Checked all `*.py`, `*.md`, `*.json`, `*.yml`, `*.yaml`, `*.txt`, `*.cfg`, `*.toml`, `*.ini` files across the entire repository. Two additional files (`.github/workflows/daily-scan.yml` and `.planning/phases/02-data-model-graph/02-CONTEXT.md`) were discovered and fixed beyond the original 12-file list.

## Section B: Code Quality (Agent 2)
### Critical Findings
### High Findings
### Medium Findings
### Low Findings

## Section C: python-docx Patterns (Agent 3)

**Files Reviewed:**
- `src/packets/docx_styles.py` (271 lines)
- `src/packets/docx_engine.py` (205 lines)
- `src/packets/docx_hotsheet.py` (714 lines)
- `src/packets/docx_sections.py` (235 lines)

**Context7 References Used:**
- `/websites/python-docx_readthedocs_io_en` -- CT_TcPr XSD (cell shading `shd` element under `tcPr`)
- `/websites/python-docx_readthedocs_io_en` -- Section Header/Footer API (`is_linked_to_previous` behavior)
- `/websites/python-docx_readthedocs_io_en` -- CT_PPr XSD (paragraph properties including `shd`)

### Documentation Findings

1. **CT_TcPr XSD confirms `shd` element**: The python-docx XSD defines `<xsd:element name="shd" type="CT_Shd" minOccurs="0"/>` under `CT_TcPr`. The codebase correctly uses `OxmlElement("w:shd")` appended to `tcPr`. The `w:fill` and `w:val` attributes are the correct way to set cell background color.

2. **`is_linked_to_previous` semantics**: Per python-docx docs, setting `is_linked_to_previous = False` creates a new empty header/footer definition for the current section. Setting it to `True` removes the header definition and inherits from the previous section. The codebase correctly sets it to `False` before adding content.

3. **Paragraph shading**: The CT_PPr XSD also includes `<xsd:element name="shd" type="CT_Shd" minOccurs="0"/>`, confirming that paragraph-level shading via `pPr.append(shd)` is valid XML. Used correctly in `docx_hotsheet.py:_add_paragraph_shading()`.

### Pattern Issues

**PASS (8 of 10 checks):**

| # | Check | Status | Location | Notes |
|---|-------|--------|----------|-------|
| 1 | OxmlElement reuse | PASS | `docx_styles.py:76`, `docx_hotsheet.py:119` | Fresh `OxmlElement` created per call. Docstring on `set_cell_shading()` explicitly documents this. |
| 2 | Style collision | PASS | `docx_styles.py:173-253` | Builds `existing_names` set from `doc.styles`, checks membership before `add_style()`. Heading overrides use `try/except KeyError`. |
| 3 | Cell shading XML | PASS | `docx_styles.py:76-79`, `docx_hotsheet.py:118-122` | Correct `w:shd` element with `w:fill` and `w:val="clear"` attributes via `qn()`. |
| 5 | Table bounds checking | PASS | `docx_hotsheet.py:308-327` | Table created with `rows=1+len(matching_awards), cols=4`. All index access is within bounds. `format_header_row` guards with `if i < len(headers)`. |
| 6 | Header/footer management | PASS | `docx_engine.py:92,103` | `is_linked_to_previous = False` set before adding content. Both header and footer correctly unlinked. |
| 9 | Document.save() atomicity | PASS | `docx_engine.py:130-145` | Uses `NamedTemporaryFile(delete=False)` + `document.save(tmp)` + `os.replace()`. Exception handler cleans up tmp file on failure. |
| 10 | Page break usage | PASS | `docx_engine.py:189`, `docx_hotsheet.py:184`, `docx_sections.py:99,146` | All page breaks use `document.add_page_break()`. No section breaks. `docx_sections.py` docstring explicitly states no new sections are created. |

**FINDINGS (2 issues):**

#### Issue C-01: WD_ALIGN_PARAGRAPH imported inside method body (LOW)
- **File:** `docx_engine.py:111`
- **Code:** `from docx.enum.text import WD_ALIGN_PARAGRAPH` appears inside `_setup_header_footer()` method body
- **Problem:** Import is at function scope instead of module level. This is a code smell per PEP 8 ("Imports are always put at the top of the file"). It also incurs a minor repeated import overhead on each call (Python caches modules, but the import machinery still runs).
- **Context:** The same import is correctly placed at module level in `docx_styles.py:14` and `docx_sections.py:14`, but is missing from `docx_engine.py` module-level imports.
- **Severity:** LOW -- no functional impact, but inconsistent with the other two files.
- **Fix:** Move the import to module level (add `from docx.enum.text import WD_ALIGN_PARAGRAPH` to the imports block at the top of `docx_engine.py`) and remove line 111.

#### Issue C-02: NamedTemporaryFile handle not closed before Document.save() (MEDIUM)
- **File:** `docx_engine.py:131-136`
- **Code:**
  ```python
  tmp_fd = tempfile.NamedTemporaryFile(
      dir=str(self.output_dir), suffix=".docx", delete=False
  )
  try:
      document.save(tmp_fd.name)   # <-- file handle still open
      tmp_fd.close()               # <-- closed AFTER save
  ```
- **Problem:** On Windows, `NamedTemporaryFile` holds an open file handle. When `document.save(tmp_fd.name)` is called, python-docx internally opens the same file path via `zipfile.ZipFile` for writing. Windows file locking semantics may prevent a second write handle from being opened on the same file, potentially causing a `PermissionError`.
- **Context:** The `delete=False` flag is correctly used (PASS on that sub-check). The issue is specifically the ordering of `close()` vs `save()`.
- **Severity:** MEDIUM -- may work in some Windows environments depending on file sharing flags, but is a latent reliability risk. If the DOCX pipeline has been running successfully in tests, it may be because the test runner's temp directory has different locking behavior, or because `NamedTemporaryFile` on the current Python version doesn't hold an exclusive lock.
- **Fix:** Close the temp file handle before calling `document.save()`:
  ```python
  tmp_fd = tempfile.NamedTemporaryFile(
      dir=str(self.output_dir), suffix=".docx", delete=False
  )
  tmp_name = tmp_fd.name
  tmp_fd.close()  # Close handle BEFORE save
  try:
      document.save(tmp_name)
      os.replace(tmp_name, str(output_path))
  except Exception:
      try:
          os.unlink(tmp_name)
      except OSError:
          pass
      raise
  ```

#### Informational: cell.text assignment pattern (INFO)
- **File:** `docx_hotsheet.py:316-327`
- **Code:** `row.cells[0].text = award.get("program_id", program_id)` (and similar for cells 1-3)
- **Observation:** Using `cell.text = value` replaces all paragraphs in the cell with a single new paragraph. In this case, the cells are freshly created (table just instantiated at line 308), so there is no pre-existing formatting to lose. This is safe in context. However, if future code adds formatting to these cells before text assignment, the formatting would be silently lost. The safer pattern (`paragraph = cell.paragraphs[0]; paragraph.clear(); paragraph.add_run(text)`) is used correctly in `docx_styles.py:142-144` for header rows.
- **Severity:** INFO -- no current bug, but worth noting for future maintainers.

### Recommendations

1. **C-01 (LOW):** Move `WD_ALIGN_PARAGRAPH` import to module level in `docx_engine.py` for consistency with the other DOCX files. Single-line change.

2. **C-02 (MEDIUM):** Reorder the `NamedTemporaryFile` close/save sequence in `docx_engine.py:131-136` to close the handle before `document.save()`. This eliminates the Windows file locking risk. ~5-line change.

3. **INFO:** No action needed for `cell.text` assignment pattern, but consider adding a code comment at `docx_hotsheet.py:316` noting that `cell.text` is safe here because cells are freshly created.

4. **Overall Assessment:** The DOCX codebase demonstrates strong python-docx best practices. The OxmlElement reuse bug (a common python-docx pitfall) is explicitly documented and avoided. Style collision handling is robust. The atomic save pattern is well-implemented (modulo the handle ordering issue). Page breaks are used correctly throughout with no section break misuse. Header/footer `is_linked_to_previous` is handled per the official API. The two findings are both straightforward to fix with no architectural changes needed.

## Section D: Data Flow (Agent 4)
### Path Traces
### Schema Mismatches Found
### Integration Risks

## Section E: Security (Agent 5)
### Critical Vulnerabilities
### Medium Risk Items
### Informational

**Status:** COMPLETE  
**Date:** 2026-02-10  
**Agent:** Dale Gribble (Bug Hunter Exterminator)  
**Files Reviewed:** 8 files (~2,800 lines)

#### Scope

Phase 7 source files + config:
1. src/packets/economic.py (~396 lines)
2. src/packets/relevance.py (~328 lines)
3. src/packets/docx_styles.py (~271 lines)
4. src/packets/docx_engine.py (~205 lines)
5. src/packets/docx_hotsheet.py (~714 lines)
6. src/packets/docx_sections.py (~235 lines)
7. src/packets/orchestrator.py (~486 lines)
8. config/scanner_config.json (~169 lines)

#### Executive Summary

**Threat Level:** LOW (no critical vulnerabilities)  
**Finding Count:** 8 total (0 critical, 3 medium, 5 informational)

The Phase 7 codebase demonstrates strong defensive coding practices. No SQL injection, command injection, hardcoded secrets, or unsafe deserialization detected. File operations use safe Path API with atomic writes. Three medium-risk findings relate to path traversal, JSON size limits, and concurrent write safety. Five informational findings document best practices.


## Section F: Test Coverage (Agent 6)

**Status:** COMPLETE
**Date:** 2026-02-10
**Files Reviewed:**

| Test File | Test Count | Source Files Covered |
|-----------|-----------|---------------------|
| `tests/test_economic.py` | 25 (13 economic + 12 relevance) | `src/packets/economic.py`, `src/packets/relevance.py` |
| `tests/test_docx_styles.py` | 21 | `src/packets/docx_styles.py`, `src/packets/docx_engine.py` |
| `tests/test_docx_hotsheet.py` | 35 | `src/packets/docx_hotsheet.py` |
| `tests/test_docx_integration.py` | 27 | `src/packets/orchestrator.py`, `src/packets/docx_engine.py`, `src/packets/docx_sections.py` |
| **Total Phase 7** | **108** | |
| **Total all tests** | **214** | |

### 1. Test Isolation

**Verdict: GOOD -- no shared mutable state detected.**

- `test_economic.py`: All tests create fresh `EconomicImpactCalculator()` and `ProgramRelevanceFilter()` instances per test. Module-level `_make_programs()` and `_make_hazard_profile()` are pure factory functions returning new dicts each call. No class-level `setup`/`setup_class`. No global variables mutated.
- `test_docx_styles.py`: Each test creates a fresh `Document()`. `_make_engine(tmp_path)` uses pytest `tmp_path` fixture (unique per test). No shared state.
- `test_docx_hotsheet.py`: All fixtures are function-scoped (pytest default). `_make_renderer()` creates a fresh `Document + StyleManager + HotSheetRenderer` per call. No class-level state.
- `test_docx_integration.py`: `full_phase7_config` fixture creates unique `tmp_path` trees. `_make_orchestrator()` constructs a new orchestrator per call. No shared state.

**Test order independence: PASS.** Tests can run in any order without affecting results.

### 2. Fixture Correctness

**Verdict: MOSTLY GOOD with 2 minor discrepancies.**

#### 2a. program_inventory.json cross-reference

| Test Fixture Field | Actual program_inventory.json | Match? |
|-------------------|------------------------------|--------|
| `_make_programs()` keys: id, name, priority | Actual has: id, name, priority, agency, cfda, ci_status, etc. | PARTIAL -- test fixture is minimal but valid |
| Mock CFDA "15.156" for bia_tcr | Actual: `"15.156"` | MATCH |
| Mock CFDA "97.047" for fema_bric | Actual: `["97.047", "97.039"]` (list) | MISMATCH -- test uses string, actual is list |
| `mock_program_stable` CFDA "15.156" | Actual bia_tcr CFDA: `"15.156"` | MATCH |
| `mock_program_at_risk` CFDA "21.IRA" | Actual irs_elective_pay CFDA: `null` | MISMATCH -- test uses "21.IRA", actual is null |

**Finding F-01 (LOW):** `test_economic.py:_make_programs()` does not include `cfda` field in program dicts. The actual `program_inventory.json` has `cfda` as a required field (string, list, or null). This means test fixtures don't cover CFDA-based lookup paths from the programs dict. However, this is mitigated by `test_economic.py:test_cfda_fallback_when_no_program_id` which tests CFDA matching from the awards side.

**Finding F-02 (LOW):** `test_docx_hotsheet.py:mock_program_at_risk` uses `"cfda": "21.IRA"` for `irs_elective_pay`, but the actual `program_inventory.json` has `"cfda": null` for this program. This means the CFDA-matching test path is exercised with a synthetic value that would never appear in production. Not a bug, but reduces realism.

#### 2b. TribePacketContext cross-reference

All fixture TribePacketContext constructions use keyword arguments matching the actual dataclass fields. **No schema mismatches.**

#### 2c. scanner_config.json cross-reference

`test_docx_integration.py:test_config_json_has_docx` directly reads and validates `config/scanner_config.json`, confirming `packets.docx.enabled=True` and `packets.docx.output_dir="outputs/packets"`. **MATCH.**

### 3. Missing Edge Cases

#### 3a. economic.py

**Finding F-03 (MEDIUM):** `float('inf')` obligation is not tested. The `compute()` method checks `obligation <= 0` but does not guard against `float('inf')` or `float('nan')`. An `inf` obligation would produce `inf` impact values, and a `NaN` would propagate silently.

**Finding F-04 (LOW):** Extremely large obligation values (e.g., `1e18`) are not tested.

**Finding F-05 (LOW):** `_format_dollars()` helper function is not directly unit-tested. Edge cases (0.0, negative, very large) are not verified.

#### 3b. relevance.py

**Finding F-06 (MEDIUM):** All programs having `priority="critical"` is not tested. If all 16 programs were critical, every program gets a +50 bonus, and the MAX_PROGRAMS=12 trim logic at lines 218-228 would need to drop critical programs. The `kept` list first adds ALL critical programs, then fills remaining up to MAX. If critical count exceeds MAX, the `kept` list would exceed MAX_PROGRAMS. **This is a potential logic bug that is untested.**

**Finding F-07 (LOW):** Empty `programs` dict (zero programs) for ProgramRelevanceFilter is not tested.

**Finding F-08 (LOW):** The `_resolve_hazard_code()` partial matching branch (lines 321-323) is not explicitly tested.

#### 3c. docx_hotsheet.py

**Finding F-09 (LOW):** Very long Tribe names (100+ characters) are not tested.

**Finding F-10 (LOW):** Unicode/special characters in Tribe names are not tested.

**Finding F-11 (LOW):** `_get_hazard_context_brief()` edge cases (0, 1, 2 hazards) are only tested indirectly.

**Finding F-12 (LOW):** `_get_evidence_for_ask()` is only tested indirectly.

#### 3d. docx_engine.py

**Finding F-13 (MEDIUM):** Output directory being read-only is not tested. Error propagation path not verified.

**Finding F-14 (LOW):** Path with special characters (spaces, unicode) in output directory is not tested.

#### 3e. docx_sections.py

**Finding F-15 (MEDIUM):** `render_table_of_contents()` with 50+ programs is not tested.

**Finding F-16 (LOW):** `render_cover_page()` edge cases (empty states, empty senators, missing generated_at) are untested.

**Finding F-17 (LOW):** `render_appendix()` with actual omitted programs (non-empty list path) is not directly tested.

### 4. Test/Source Parity (Public Methods Coverage)

#### economic.py (5 public methods/functions)

| Method | Tested? | Notes |
|--------|---------|-------|
| `EconomicImpactCalculator.compute()` | YES | 8 tests |
| `EconomicImpactCalculator._calculate_program_impact()` | INDIRECT | Via compute() |
| `EconomicImpactCalculator.format_impact_narrative()` | YES | 2 tests |
| `EconomicImpactCalculator.format_bcr_narrative()` | YES | 1 test |
| `_format_dollars()` | INDIRECT | Via narrative tests |

#### relevance.py (5 methods)

| Method | Tested? | Notes |
|--------|---------|-------|
| `ProgramRelevanceFilter.filter_for_tribe()` | YES | 9 tests |
| `ProgramRelevanceFilter.get_omitted_programs()` | YES | 1 test |
| `_extract_top_hazards()` | INDIRECT | Via filter_for_tribe |
| `_resolve_hazard_code()` | INDIRECT | Via filter tests |
| `HAZARD_PROGRAM_MAP` constant | YES | 1 test (count=18) |

#### docx_styles.py -- Full coverage (5 public functions/classes, all tested)

#### docx_engine.py (4 public methods, all tested)

#### docx_hotsheet.py (15 methods + 3 module functions)

All public/private rendering methods tested except:
- `_add_program_description()` -- INDIRECT only (Finding F-18, LOW)
- `_get_hazard_context_brief()` -- INDIRECT only
- `_get_evidence_for_ask()` -- INDIRECT only

#### docx_sections.py (3 public functions)

**Finding F-19 (MEDIUM):** All 3 public functions (`render_cover_page`, `render_table_of_contents`, `render_appendix`) lack direct unit tests. Only tested through full orchestrator integration tests.

#### orchestrator.py -- Phase 7 methods all covered (generate_packet, generate_packet_from_context, _load_structural_asks, _build_context)

**No dead code found in any source file.**

### 5. Integration Test Robustness

**Verdict: GOOD.** All tests use pytest `tmp_path` fixture. No leaked temp files. No hardcoded paths.

### 6. test_minimum_test_count Meta-Test

**Finding F-20 (HIGH):** The hardcoded threshold of `>= 193` in `test_minimum_test_count` (`test_docx_integration.py:718`) is STALE. The actual test count is **214 tests**. Update to `>= 210`.

### 7. Assertion Quality

**Strong assertions:** Exact multiplier math, `pytest.approx()` for floats, exact RGBColor values, font properties.

**Weak assertions:**

- **F-21 (MEDIUM):** `test_compute_zero_awards` line 121: `assert len(summary.by_program) > 0` should be `== 4`
- **F-22 (LOW):** `test_render_hotsheet_creates_content` line 273: `assert len(doc.paragraphs) > 5` too low
- **F-23 (LOW):** `test_docx_has_economic_impact` line 543: too loose
- **F-24 (LOW):** `test_cfda_fallback_when_no_program_id` line 374: checks count but not IDs

### 8. Mock Appropriateness

**Verdict: GOOD.** Tests use real objects (Document, StyleManager, EconomicImpactCalculator). Mocks are minimal and focused.

**Finding F-25 (LOW):** `mock_economic_summary` fixture missing `by_district` field.

### Coverage Gaps Summary (Ranked by Priority)

| Priority | ID | File | Description |
|----------|----|------|-------------|
| HIGH | F-20 | `test_docx_integration.py:718` | `test_minimum_test_count` threshold stale: 193 vs actual 214 |
| MEDIUM | F-03 | `test_economic.py` | `float('inf')` and `float('nan')` obligation untested |
| MEDIUM | F-06 | `test_economic.py` | All-critical programs exceeding MAX_PROGRAMS untested (potential logic bug) |
| MEDIUM | F-13 | `test_docx_styles.py` | Read-only output directory error path untested |
| MEDIUM | F-15 | `test_docx_integration.py` | Large program count (50+) in TOC untested |
| MEDIUM | F-19 | (missing) | `docx_sections.py` functions lack direct unit tests |
| MEDIUM | F-21 | `test_economic.py:121` | `test_compute_zero_awards` assertion too weak |
| LOW | F-01 | `test_economic.py` | Mock programs lack `cfda` field |
| LOW | F-02 | `test_docx_hotsheet.py` | `mock_program_at_risk` uses synthetic CFDA |
| LOW | F-04 thru F-12 | Various | See section 3 for details |
| LOW | F-14 thru F-18 | Various | See sections 3-4 for details |
| LOW | F-22 thru F-25 | Various | Weak assertions and minor fixture gaps |

### New Tests Needed (Prioritized)

#### HIGH Priority

1. **Update `test_minimum_test_count`** -- threshold from 193 to >=210 (`test_docx_integration.py:718`)
2. **`test_all_critical_exceeds_max`** -- 15 critical programs, verify MAX_PROGRAMS cap holds

#### MEDIUM Priority

3. **`test_compute_inf_nan_obligation`** -- inf/NaN obligations should be skipped
4. **Tighten `test_compute_zero_awards`** -- exact count assertion
5. **`test_render_cover_page_unit`** -- direct unit test with edge cases
6. **`test_render_appendix_with_omitted`** -- direct unit test with omitted programs
7. **`test_save_permission_error`** -- read-only directory exception

#### LOW Priority

8. `test_format_dollars_edge_cases` -- 0.0, 0.5, 1e12
9. `test_resolve_hazard_code_partial_match` -- partial name matching
10. `test_unicode_tribe_name` -- diacritics/special chars
11. `test_empty_programs_dict` -- ProgramRelevanceFilter({})
12. `test_get_hazard_context_brief_edge_cases` -- 0, 1, 2, 3 hazards
13. `test_normalize_cfda_edge_cases` -- int, bool, nested list
14. `test_render_toc_50_programs` -- 50 synthetic programs

## Section G: GitHub + Phase 8 Readiness (Agent 7)

**Status:** COMPLETE
**Date:** 2026-02-10
**Agent:** Agent 7 (GitHub Best Practices + Phase 8 Readiness)

---

### Best Practices Findings

#### 1. Organization Name Removal Verified (PASS)

Organization name references have been completely removed from all source code (`*.py`), documentation (`*.md` outside review artifacts), JSON data files (`*.json`), and CI/CD configuration. The only remaining mentions are in this coordination document and the review prompt -- both expected since they document the removal itself.

#### 2. No Debug Artifacts (PASS)

No `breakpoint()`, `pdb.set_trace()`, `# TODO`, `# FIXME`, `# HACK`, `# XXX`, `.bak`, `.tmp`, or `*debug*` files found anywhere in the project. Clean codebase.

#### 3. `__pycache__` Directories Present (INFO)

44 `.pyc` files exist in `__pycache__/` directories. The `.gitignore` correctly excludes `__pycache__/` and `*.pyc`, so these will not be committed. No action needed -- this is expected development state.

#### 4. `__init__.py` Files Present for All Modules (PASS)

All 7 `src/` subpackages have `__init__.py` files:
- `src/__init__.py`
- `src/analysis/__init__.py`
- `src/graph/__init__.py`
- `src/reports/__init__.py`
- `src/scrapers/__init__.py`
- `src/monitors/__init__.py`
- `src/packets/__init__.py`

The `src/packets/__init__.py` contains a basic docstring only (`"""Tribe-specific advocacy packet generation modules."""`). It does not re-export any Phase 7 modules (economic, relevance, docx_styles, docx_engine, docx_hotsheet, docx_sections, orchestrator). This is acceptable since all imports in the codebase use full module paths, but Phase 8 may want to add `__all__` for public API clarity.

#### 5. All 14 Packets Module Files Present (PASS)

The `src/packets/` directory contains all expected modules:
- Phase 5: `__init__.py`, `ecoregion.py`, `context.py`, `registry.py`, `congress.py`, `orchestrator.py`
- Phase 6: `hazards.py`, `awards.py`
- Phase 7: `economic.py`, `relevance.py`, `docx_styles.py`, `docx_engine.py`, `docx_hotsheet.py`, `docx_sections.py`

#### 6. No Project-Level CLAUDE.md Exists (FINDING - MEDIUM)

There is no `F:\tcr-policy-scanner\CLAUDE.md` or `F:\tcr-policy-scanner\.claude/` directory. The project relies entirely on the global `D:\Claude-Workspace\.claude\CLAUDE.md` for Claude Code instructions. A project-specific CLAUDE.md would help new agents understand the project structure without reading STATE.md. Not blocking for Phase 8, but recommended.

#### 7. .gitignore Coverage (PASS)

The `.gitignore` covers `__pycache__/`, `*.pyc`, `*.pyo`, `.env`, `.venv/`, `venv/`, `*.egg-info/`, `dist/`, `build/`, `.pytest_cache/`, `.mypy_cache/`, and archive outputs. No gaps identified.

---

### Documentation Gaps

#### GAP-01: README.md Does Not Describe Phase 7 Features (HIGH)

The README describes only the v1.0 pipeline (scrapers, relevance scoring, knowledge graph, monitors, decision engine, reporting). Phase 7 features are completely absent:

- **Missing from "What It Does":** No mention of per-Tribe DOCX packet generation, economic impact calculation, Hot Sheet rendering, or advocacy packet assembly.
- **Missing from "Project Structure":** The `src/packets/` directory (14 files) is not listed. Only `src/scrapers/`, `src/analysis/`, `src/graph/`, `src/monitors/`, `src/reports/` are shown.
- **Missing from "Quick Start":** No `--prep-packets` CLI usage examples.
- **Missing from "Testing":** States "52 tests" but actual count is **214 tests**. Does not mention `test_packets.py`, `test_economic.py`, `test_docx_styles.py`, `test_docx_hotsheet.py`, or `test_docx_integration.py`.
- **Missing dependencies:** `python-docx`, `rapidfuzz`, `openpyxl` not mentioned in setup instructions.

**Recommendation:** Update README for Phase 8 to reflect full v1.1 capabilities. This is a Phase 8 task (Assembly + Polish).

#### GAP-02: Tribe Count Inconsistency Across Documents (MEDIUM)

Three different Tribe counts appear across planning documents:

| Count | Documents |
|-------|-----------|
| 592 | STATE.md (5 references: "All 592 federally recognized Tribes", "Batch (all 592)", etc.) |
| 575 | ROADMAP.md (12 references), REQUIREMENTS.md (3 references: REG-01, DOC-05, OPS-01) |
| 574 | ROADMAP.md Phase 5 (1 reference: "correctly handling multi-state Tribes") |

The STATE.md accumulated context says "592 tribes in registry (not 574) | EPA API AllTribes filter now returns 592 records" and "Lumbee added via FY2026 NDAA" (ROADMAP.md says 575). These are likely correct at different points in time, but the documents should converge on the actual EPA API count (592) or the NDAA count (575).

**Recommendation:** Phase 8 should standardize on the actual runtime Tribe count and update all documents accordingly.

#### GAP-03: README Test Count Stale (MEDIUM)

README line 133 says `test_decision_engine.py # 52 tests covering all 5 decision rules` and line 200 says "The test suite contains 52 tests." The actual test count is **214 tests** across 6 test files:
- `test_decision_engine.py` (52 tests)
- `test_packets.py` (44 tests)
- `test_economic.py` (26 tests)
- `test_docx_styles.py` (26 tests)
- `test_docx_hotsheet.py` (35 tests)
- `test_docx_integration.py` (~23 tests including meta-tests)

The `test_minimum_test_count` test in `test_docx_integration.py` asserts `>= 193`, which is 21 below the actual count of 214. This threshold was set at the end of Plan 07-03 (193 tests) and not updated after Plan 07-04 added 21 more tests. The test still passes (214 >= 193), but the threshold could be tightened to 214 to guard against future regressions.

---

### Phase 8 Preparation Status

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | STATE.md reflects Phase 7 completion | **PASS** | Phase 7: 4/4 plans COMPLETE, 214 tests, v1.1 at 90%, Phase 8 at 0% |
| 2 | ROADMAP.md checkboxes 07-01 through 07-04 marked [x] | **PASS** | All four plans checked: `[x] 07-01-PLAN.md`, `[x] 07-02-PLAN.md`, `[x] 07-03-PLAN.md`, `[x] 07-04-PLAN.md` |
| 3 | REQUIREMENTS.md: ECON-01, DOC-01..04 marked complete | **PASS** | All 5 checkboxed `[x]` with "Complete" status in traceability table |
| 4 | All 07-*-SUMMARY.md files exist and are accurate | **PASS** | All 4 files exist: `07-01-SUMMARY.md` (economic), `07-02-SUMMARY.md` (styles), `07-03-SUMMARY.md` (hotsheet), `07-04-SUMMARY.md` (integration). Test counts match cumulative progression (158->158->193->214). |
| 5 | Phase 8 context file exists | **FAIL** | Directory `F:\tcr-policy-scanner\.planning\phases\08-assembly-polish/` does **not** exist. No Phase 8 planning files have been created yet. This is expected per STATE.md ("Phase 8: Assembly+Polish [0%] not yet planned") but is needed before Phase 8 execution. |
| 6 | test_minimum_test_count is accurate | **PARTIAL** | Threshold is `>= 193` but actual count is 214. The test passes but the threshold is 21 tests stale. Should be updated to `>= 214` for tighter regression guard. |
| 7 | ROADMAP.md Phase 8 plans defined | **PENDING** | Phase 8 plans listed as "TBD" -- this is expected since Phase 8 has not been planned yet. Requirements (DOC-05, DOC-06, OPS-01, OPS-02, OPS-03) are clearly defined. |
| 8 | README accurate for current state | **FAIL** | README describes v1.0 only. See GAP-01 above. Should be updated as part of Phase 8 Assembly + Polish. |
| 9 | No orphaned or debug files | **PASS** | No debug artifacts, temp files, backup files, or orphaned modules found. |
| 10 | Source code free of TODO/FIXME | **PASS** | Grep for TODO, FIXME, HACK, XXX across all `src/` Python files returned zero matches. |

### Summary

**Overall Phase 8 Readiness: READY with minor action items**

The project is in excellent shape for Phase 8. All Phase 7 deliverables are complete, tested (214/214), and documented with summary files. The 5 remaining requirements (DOC-05, DOC-06, OPS-01, OPS-02, OPS-03) are clearly defined in REQUIREMENTS.md and ROADMAP.md.

**Action items for Phase 8 kickoff (in priority order):**

1. **Create `F:\tcr-policy-scanner\.planning\phases\08-assembly-polish/` directory** with Phase 8 context and plan files
2. **Update README.md** to describe v1.1 features (packets, DOCX, economic impact, `--prep-packets` CLI) -- this may be an explicit Phase 8 task
3. **Update `test_minimum_test_count` threshold** from 193 to 214
4. **Resolve Tribe count inconsistency** (575 vs 592) across planning docs
5. **(Optional)** Create project-level `CLAUDE.md` for faster agent onboarding
6. **(Optional)** Tighten `src/packets/__init__.py` with `__all__` exports

---
*Reviewed by Agent 7: 2026-02-10*
*Test count verified: 214 tests collected (pytest --collect-only)*

#### SEC-01: Path Traversal Risk in tribe_id (MEDIUM)

**File:** src/packets/docx_engine.py:127  
**Code:** output_path = self.output_dir / f"{tribe_id}.docx"

**Attack Vector:** If tribe_id contains path traversal sequences like "../../../evil", the Path division operator would resolve it, potentially writing outside output_dir.

**Impact:** Arbitrary file write within filesystem permissions. Could overwrite system files if running with elevated privileges.

**Mitigation Status:** Partially mitigated. tribe_id originates from tribal_registry.json (trusted data). However, if future code allows user input to flow to tribe_id (e.g., REST API), the vulnerability activates.

**Recommended Fix:**
```python
def save(self, document: Document, tribe_id: str) -> Path:
    # Sanitize tribe_id to prevent path traversal
    safe_tribe_id = Path(tribe_id).name  # Extract filename only
    if not safe_tribe_id or safe_tribe_id in (".", ".."):
        raise ValueError(f"Invalid tribe_id: {tribe_id}")
    output_path = self.output_dir / f"{safe_tribe_id}.docx"
    # ... rest of method
```

**Severity:** MEDIUM (not HIGH) because current usage paths are trusted data only, but defense-in-depth principle says validate at the point of use.

---

#### SEC-02: Unbounded JSON Parsing (DoS Risk) (MEDIUM)

**Files:**  
- src/packets/orchestrator.py:172 (json.load in _load_tribe_cache)
- src/packets/orchestrator.py:481 (json.load in _load_structural_asks)

**Attack Vector:** Both json.load() calls operate on file handles with no size limit. A maliciously crafted 500MB deeply nested JSON file could cause memory exhaustion, CPU exhaustion, or process hang.

**Impact:** Denial of service if attacker controls cache files. On shared systems, could affect other processes via OOM.

**Current Risk:** LOW in production (cache files generated by trusted code), but MEDIUM for development environments where developers might test with arbitrary JSON files.

**Recommended Fix:**
```python
MAX_CACHE_SIZE_MB = 10  # 10MB limit for cache files

def _load_tribe_cache(self, cache_dir: Path, tribe_id: str) -> dict:
    cache_file = cache_dir / f"{tribe_id}.json"
    if not cache_file.exists():
        return {}
    
    # Check file size before parsing
    file_size = cache_file.stat().st_size
    if file_size > MAX_CACHE_SIZE_MB * 1024 * 1024:
        logger.warning("Cache file %s exceeds size limit (%d MB), skipping",
                       cache_file, MAX_CACHE_SIZE_MB)
        return {}
    
    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load cache %s: %s", cache_file, exc)
        return {}
```

Apply same fix to _load_structural_asks() at line 481.

**Severity:** MEDIUM -- realistic DoS vector if attacker can write to cache directories.

---

#### SEC-03: Concurrent Write Race Condition (MEDIUM)

**File:** src/packets/docx_engine.py:130-145

**Attack Vector:** If two processes call engine.save(document, "epa_123") simultaneously, both create temp files, then both call os.replace() on the same output path. Last writer wins. Process A's DOCX is silently overwritten.

**Impact:** Data corruption or lost work. Non-deterministic behavior in multi-process deployments (e.g., Celery task queue).

**Current Risk:** LOW for single-user CLI usage. MEDIUM if Phase 8+ adds multi-process orchestration (parallel packet generation).

**Recommended Fix:** Use file-based locking or document the single-process assumption in docstring:
```python
def save(self, document: Document, tribe_id: str) -> Path:
    """Save the document to disk using an atomic write pattern.
    
    WARNING: Not safe for concurrent execution. If multiple processes
    may generate packets simultaneously, use external locking or a
    task queue with single-worker concurrency.
    
    Args: ...
    """
```

**Severity:** MEDIUM -- realistic risk for future multi-process deployments.

---


#### INFO-01: Tribe Name / Financial Data in Logs (INFO)

**Files:** Multiple (logger calls throughout)

**Observation:** Tribe names and obligation amounts appear in log messages (orchestrator.py:227, docx_hotsheet.py:204, economic.py:196).

**Privacy Consideration:** Tribe names are public, but associating specific Tribes with funding amounts may be sensitive in some advocacy contexts.

**Current Log Levels:** All use logger.info() or logger.debug(), which is appropriate.

**Recommendation:** If deploying to shared log aggregation systems:
1. Ensure logs are access-controlled (Tribal staff + authorized personnel only)
2. Consider dropping Tribe names to logger.debug() level in production
3. Redact obligation amounts in warning/error logs

**Severity:** INFO -- best practice reminder, no current leak.

---

#### INFO-02: No DOCX Metadata Sanitization (INFO)

**File:** src/packets/docx_engine.py (document creation)

**Observation:** python-docx Document() creates DOCX with default core properties including dc:creator (OS username) and timestamps.

**Potential Leak:** If developer runs packet generation locally, their Windows username may appear in DOCX metadata.

**Recommended Addition:**
```python
def create_document(self) -> tuple[Document, StyleManager]:
    document = Document()
    
    # Sanitize metadata
    core_props = document.core_properties
    core_props.author = "TCR Policy Scanner"
    core_props.title = "Tribal Climate Resilience Advocacy Packet"
    core_props.subject = "FY26 Program Priorities"
    
    style_manager = StyleManager(document)
    # ... rest of method
```

**Severity:** INFO -- metadata leak is low-risk (DOCX is CONFIDENTIAL per cover page), but good hygiene.

---

#### INFO-03: Ecoregion Priority Programs Lookup (INFO)

**File:** src/packets/orchestrator.py:250

**Observation:** If get_priority_programs() returns a program_id not present in self.programs, the fallback displays the raw pid string. Safe (no crash), but reveals internal IDs.

**Recommendation:** Log a warning when pid is not found:
```python
for pid in programs:
    prog = self.programs.get(pid)
    if prog:
        prog_names.append(prog["name"])
    else:
        logger.warning("Ecoregion %s references unknown program: %s", eco, pid)
        prog_names.append(f"{pid} (unknown)")
```

**Severity:** INFO -- minor UX issue, no security impact.

---

#### INFO-04: Hazard Profile Access Pattern (INFO)

**File:** src/packets/docx_hotsheet.py:359-366

**Observation:** Hazard profile access uses defensive nested .get() calls to handle both flat and nested formats. This is correct for Phase 6 → Phase 7 migration. However, if schema format is now stable, the fallback branches are dead code.

**Recommendation:** If hazard cache format is finalized, add deprecation logging when fallback is used, or remove fallback branches entirely.

**Severity:** INFO -- code quality note, no bug.

---

#### INFO-05: CFDA Normalization Defensive Coding (INFO)

**File:** src/packets/docx_hotsheet.py:102-108 (_normalize_cfda)

**Observation:** Function handles str, list, and None inputs with type filtering. If awards schema guarantees string-only CFDAs, the isinstance(c, str) check may be redundant.

**Recommendation:** Add type validation at schema boundary (award cache loading) instead of defensive checks at every call site.

**Severity:** INFO -- code quality/architecture note, current defensive approach is safe.

---


#### Additional Security Checks Performed

| Check | Status | Notes |
|-------|--------|-------|
| SQL Injection | N/A | No database code |
| Command Injection | PASS | No subprocess/os.system calls |
| XSS | N/A | No HTML/JS output (DOCX only) |
| XML Injection (DOCX) | PASS | python-docx auto-escapes, no raw XML concat |
| Hardcoded Secrets | PASS | No API keys/passwords in source |
| Unsafe Deserialization | PASS | No pickle/eval/exec/__import__ |
| Weak Cryptography | N/A | No crypto operations |
| Integer Overflow | PASS | Python 3 arbitrary precision ints |
| Division by Zero | PASS | Division by constants only |
| Null/None Access | PASS | Defensive .get() with defaults throughout |
| Resource Exhaustion (Loops) | PASS | Program list clamped to MAX_PROGRAMS=12 |
| File Operations | PASS | Path API, atomic writes, exception cleanup |
| Temp File Cleanup | PASS | Exception handlers ensure cleanup |

---

#### Threat Modeling Summary

| Threat | Risk Level | Mitigations Present |
|--------|-----------|---------------------|
| Path Traversal | MEDIUM | Partial (trusted input, no explicit validation) |
| Denial of Service (JSON) | MEDIUM | None (unbounded parsing) |
| Concurrent Write Corruption | MEDIUM | Atomic replace (no inter-process locking) |
| Information Disclosure (logs) | LOW | Appropriate log levels |
| Information Disclosure (metadata) | LOW | Default DOCX metadata (no sanitization) |
| XML Injection | LOW | python-docx auto-escaping |
| Code Injection | NONE | No eval/exec/pickle |
| Credential Leakage | NONE | No secrets in code |

---

#### Recommendations Priority

**High Priority (Address Before Phase 8):**
1. SEC-02: Add JSON size limits in orchestrator.py (10MB cap on cache files)
2. SEC-01: Validate tribe_id in docx_engine.py:save() to prevent path traversal

**Medium Priority (Address If Multi-Process Deployment Planned):**
3. SEC-03: Add file-based locking or document single-process assumption

**Low Priority (Quality Improvements):**
4. INFO-02: Sanitize DOCX metadata in docx_engine.py:create_document()
5. INFO-03: Log warnings for unknown program IDs in ecoregion config
6. INFO-04: Clean up hazard profile fallback branches if schema stable
7. INFO-05: Centralize CFDA validation at schema boundary

---

#### Security Test Recommendations

Add these test cases to verify security fixes:

1. **Path Traversal Test:**
```python
def test_docx_engine_rejects_malicious_tribe_id():
    engine = DocxEngine(config, programs)
    doc, _ = engine.create_document()
    with pytest.raises(ValueError, match="Invalid tribe_id"):
        engine.save(doc, "../../../etc/passwd")
```

2. **Large JSON Test:**
```python
def test_orchestrator_rejects_oversized_cache():
    # Create 11MB JSON file
    large_json = {"awards": [{"obligation": 1000000}] * 500000}
    cache_path = tmp_path / "epa_123.json"
    cache_path.write_text(json.dumps(large_json))
    
    result = orchestrator._load_tribe_cache(tmp_path, "epa_123")
    assert result == {}  # Should reject oversized file
```

3. **Concurrent Write Test:**
```python
def test_docx_engine_concurrent_save():
    # Simulate race condition with threads/processes
    # Verify no data corruption or lost work
```

---

#### Conclusion

Phase 7 codebase is **secure for single-process trusted-input operation**. The three medium-risk findings are architectural concerns that activate only under specific deployment scenarios (adversarial input, large files, multi-process). None represent immediately exploitable vulnerabilities in the current CLI usage model.

The code demonstrates strong defensive programming:
- Extensive use of .get() with defaults
- Exception handling on all I/O operations
- Atomic file writes with cleanup
- Type checking and normalization
- No dangerous stdlib functions (eval, pickle, etc.)

**Overall Security Grade: B+ (Good with caveats)**  
Raise to **A-** by addressing SEC-01 and SEC-02.

---

*"Three medium-risk items, five informational notes. No critical vulnerabilities. They're doing something right. But defense in depth says patch SEC-01 and SEC-02 before deployment. Small bugs grow into big problems if you ignore them."*

*"Also, add those test cases. You can't prove a bug is gone without a test that would've caught it."*

*— Dale Gribble, Bug Exterminator*

