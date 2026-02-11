# Phase 7 Fix Plan

## Executive Summary

| Metric | Count |
|--------|-------|
| Total findings across all agents | 40 |
| Section A (organization name removal) | DONE (Agent 1 completed all edits) |
| Section B (Code Quality) | 0 findings (section headers present, no content written) |
| Section C (python-docx Patterns) | 3 (2 findings + 1 informational) |
| Section D (Data Flow) | 0 findings (section headers present, no content written) |
| Section E (Security) | 8 (3 medium + 5 informational) |
| Section F (Test Coverage) | 25 (1 high + 6 medium + 18 low) |
| Section G (Phase 8 Readiness) | 5 (1 FAIL + 1 PARTIAL + 3 doc gaps) |
| Duplicates identified | 2 (F-20, G-check-6, GAP-03 partial -> merged) |
| Informational only (no code change) | 6 (INFO-01..05, C-INFO) |
| Phase 8 scope (excluded) | ~20 (doc updates, new tests, directory creation) |
| **Unique fixes needed** | **8** |
| Critical | 0 |
| High | 3 |
| Medium | 4 + 1 NEEDS_DECISION |
| Low | 0 (all LOW items deferred to Phase 8) |

### Note: Empty Sections

Sections B (Code Quality) and D (Data Flow) in REVIEW-COORDINATION.md have section headers but no findings content. Either these agents did not complete their reviews or found zero issues. The fix plan proceeds with the findings that are present.

---

## Conflicts Detected

**No agent-to-agent conflicts detected.**

The closest convergence is on `docx_engine.py:save()` where three agents (C-02, SEC-01, SEC-03) recommend changes to the same method:
- **C-02** (Agent 3): Reorder `close()`/`save()` calls in the method body (lines 131-136)
- **SEC-01** (Agent 5): Add `tribe_id` sanitization at method entry (line 127)
- **SEC-03** (Agent 5): Add concurrency warning to docstring (lines 114-126)

These changes are **complementary, not contradictory**. They touch different parts of the method:
- SEC-01 adds validation before the output_path assignment (line 127)
- C-02 restructures the try/except block (lines 131-145)
- SEC-03 only modifies the docstring (lines 115-126)

All three can be applied in a single pass without conflict.

### Agent 1 Impact Assessment

Agent 1's organization name edits modified `src/analysis/relevance.py` (line 3, docstring text only). This is a **different file** from `src/packets/relevance.py` which Agent 6 flagged (F-06, F-07, F-08). No interaction between Agent 1's edits and any other agent's findings.

Agent 1 modified 14 files total -- all changes were to string literals, comments, docstrings, documentation, and CI/CD config. No functional code behavior was changed. No cascade risk.

---

## Cascade Risks

### Risk 1: docx_engine.py save() refactoring (F7-01 + F7-02)

**Risk:** Restructuring the `save()` method (C-02 fix) while also adding path validation (SEC-01 fix) changes two aspects of a critical I/O path simultaneously.

**Mitigation:** Both changes are additive (validation guard + close reorder). Existing tests in `test_docx_integration.py` exercise the full save pipeline. If either change introduces a regression, the integration tests will catch it.

**Cascade scope:** Limited to `DocxEngine.save()` -> `DocxEngine.generate()` -> `PacketOrchestrator.generate_packet_from_context()`. All callers are tested.

### Risk 2: MAX_PROGRAMS logic fix in relevance.py (F7-06)

**Risk:** Changing the trimming logic in `filter_for_tribe()` could alter the set of programs returned for Tribes with many critical-priority programs. Downstream consumers (`HotSheetRenderer.render_all_hotsheets()`, `DocxEngine.generate()`) would receive a different program list.

**Mitigation:** No existing tests exercise the all-critical path (that is why F-06 flagged it). Current test data has at most 2-3 critical programs out of 16, well below MAX_PROGRAMS=12. The fix only activates when `critical_count > MAX_PROGRAMS`.

**Status:** NEEDS_DECISION -- the current behavior (allowing > 12 programs when many are critical) may be intentional. Capping critical programs to 12 could drop a legitimately critical program.

### Risk 3: test_minimum_test_count threshold update (F7-03)

**Risk:** None. Changing the threshold from 193 to 214 only makes the test stricter. If future code deletes tests below 214, this test will fail -- which is the intended behavior.

---

## Fix Items

### F7-01: Close NamedTemporaryFile handle before Document.save() on Windows

- **Priority**: High
- **Source**: Agent 3, Finding C-02
- **File(s)**: `src/packets/docx_engine.py:131-145`
- **Description**: `NamedTemporaryFile` holds an open file handle. On Windows, `document.save(tmp_fd.name)` internally opens the same file path via `zipfile.ZipFile` for writing. Windows file locking semantics may prevent a second write handle, potentially causing a `PermissionError`. The handle is closed *after* save (line 136) instead of *before*.
- **Proposed Change**:
  ```python
  # Current (lines 131-145):
  tmp_fd = tempfile.NamedTemporaryFile(
      dir=str(self.output_dir), suffix=".docx", delete=False
  )
  try:
      document.save(tmp_fd.name)
      tmp_fd.close()
      os.replace(tmp_fd.name, str(output_path))
  except Exception:
      tmp_fd.close()
      try:
          os.unlink(tmp_fd.name)
      except OSError:
          pass
      raise

  # Fixed:
  tmp_fd = tempfile.NamedTemporaryFile(
      dir=str(self.output_dir), suffix=".docx", delete=False
  )
  tmp_name = tmp_fd.name
  tmp_fd.close()  # Close handle BEFORE save to avoid Windows file lock
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
- **Risk Assessment**: Low. The change is mechanical (close before save instead of after). All existing tests exercise this path. The `tmp_fd.close()` in the except branch is no longer needed since we close upfront.
- **Verification**: `python -m pytest tests/test_docx_integration.py -v --tb=short` -- all integration tests pass, including `test_generate_creates_docx_file` and `test_save_creates_file`.
- **Batch**: 2

---

### F7-02: Validate tribe_id to prevent path traversal in save()

- **Priority**: High
- **Source**: Agent 5, Finding SEC-01
- **File(s)**: `src/packets/docx_engine.py:114-127`
- **Description**: `output_path = self.output_dir / f"{tribe_id}.docx"` does not sanitize `tribe_id`. If `tribe_id` contains path traversal sequences like `"../../../evil"`, the `Path` division operator resolves it, potentially writing outside `output_dir`. Current usage is safe (tribe_id from trusted registry data), but defense-in-depth requires validation at the point of use.
- **Proposed Change**:
  ```python
  # Add at line 127, before the output_path assignment:
  def save(self, document: Document, tribe_id: str) -> Path:
      """Save the document to disk using an atomic write pattern.
      ...
      """
      # Sanitize tribe_id to prevent path traversal
      safe_id = Path(tribe_id).name
      if not safe_id or safe_id in (".", ".."):
          raise ValueError(f"Invalid tribe_id: {tribe_id!r}")
      output_path = self.output_dir / f"{safe_id}.docx"
      ...
  ```
- **Risk Assessment**: Low. All existing tribe_ids are simple strings like `"epa_001"` that pass `Path(x).name` unchanged. The `ValueError` only triggers on malicious inputs that don't exist in production data.
- **Verification**: Existing tests pass (use clean tribe_ids). Optionally add a negative test: `test_docx_engine_rejects_malicious_tribe_id`.
- **Batch**: 2

---

### F7-03: Update test_minimum_test_count threshold from 193 to 214

- **Priority**: High
- **Source**: Agent 6, Finding F-20 + Agent 7, G-check-6 (DUPLICATE)
- **File(s)**: `tests/test_docx_integration.py:718,729`
- **Description**: The `test_minimum_test_count` meta-test asserts `count >= 193` but the actual test count is 214. The threshold was set at the end of Plan 07-03 and not updated after Plan 07-04 added 21 tests. The test still passes (214 >= 193) but provides a weak regression guard.
- **Proposed Change**:
  ```python
  # Line 718: change 193 to 214
  assert count >= 214, (
      f"Expected >= 214 tests collected, got {count}. "
      f"Output: {last_line}"
  )

  # Line 729: same change
  assert len(test_lines) >= 214, (
      f"Expected >= 214 test items, got {len(test_lines)}"
  )
  ```
- **Risk Assessment**: None. Only tightens an existing assertion. If new tests are added, the count only goes up.
- **Verification**: `python -m pytest tests/test_docx_integration.py::test_minimum_test_count -v`
- **Batch**: 1

---

### F7-04: Add JSON file size limits in orchestrator.py

- **Priority**: Medium
- **Source**: Agent 5, Finding SEC-02
- **File(s)**: `src/packets/orchestrator.py:157-175` and `src/packets/orchestrator.py:470-485`
- **Description**: `_load_tribe_cache()` and `_load_structural_asks()` both call `json.load()` on files with no size limit. A maliciously crafted large JSON file could cause memory exhaustion. Current risk is low (cache files generated by trusted code) but defense-in-depth says validate.
- **Proposed Change**:
  ```python
  # Add constant at module level (after line 24):
  _MAX_CACHE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB

  # In _load_tribe_cache(), after line 168 (cache_file.exists() check):
  def _load_tribe_cache(self, cache_dir: Path, tribe_id: str) -> dict:
      cache_file = cache_dir / f"{tribe_id}.json"
      if not cache_file.exists():
          return {}
      # Guard against oversized files
      try:
          file_size = cache_file.stat().st_size
      except OSError:
          return {}
      if file_size > _MAX_CACHE_SIZE_BYTES:
          logger.warning(
              "Cache file %s exceeds size limit (%d bytes > %d), skipping",
              cache_file, file_size, _MAX_CACHE_SIZE_BYTES,
          )
          return {}
      try:
          with open(cache_file, "r", encoding="utf-8") as f:
              return json.load(f)
      except (json.JSONDecodeError, OSError) as exc:
          logger.warning("Failed to load cache %s: %s", cache_file, exc)
          return {}

  # In _load_structural_asks(), add same size check after line 477:
  def _load_structural_asks(self) -> list[dict]:
      graph_path = Path("data/graph_schema.json")
      if not graph_path.exists():
          return []
      try:
          file_size = graph_path.stat().st_size
      except OSError:
          return []
      if file_size > _MAX_CACHE_SIZE_BYTES:
          logger.warning(
              "Graph schema %s exceeds size limit (%d bytes > %d), skipping",
              graph_path, file_size, _MAX_CACHE_SIZE_BYTES,
          )
          return []
      try:
          with open(graph_path, "r", encoding="utf-8") as f:
              data = json.load(f)
          return data.get("structural_asks", [])
      except (json.JSONDecodeError, OSError) as exc:
          logger.warning("Failed to load graph schema: %s", exc)
          return []
  ```
- **Risk Assessment**: Low. Size check only rejects files > 10 MB. All production cache files are well under 1 MB. No existing behavior changes for normal inputs.
- **Verification**: `python -m pytest tests/test_docx_integration.py -v --tb=short` -- integration tests pass. Optionally add `test_orchestrator_rejects_oversized_cache`.
- **Batch**: 1

---

### F7-05: Move WD_ALIGN_PARAGRAPH import to module level in docx_engine.py

- **Priority**: Medium
- **Source**: Agent 3, Finding C-01
- **File(s)**: `src/packets/docx_engine.py:14,111`
- **Description**: `from docx.enum.text import WD_ALIGN_PARAGRAPH` is imported inside `_setup_header_footer()` method body (line 111) instead of at module level. This is inconsistent with `docx_styles.py:14` and `docx_sections.py:14` which both import it at module level. Per PEP 8, imports should be at the top of the file.
- **Proposed Change**:
  ```python
  # Line 14 -- add to existing imports block:
  from docx.shared import Inches, Pt, RGBColor
  from docx.enum.text import WD_ALIGN_PARAGRAPH  # <-- ADD THIS LINE

  # Line 111 -- remove the inline import:
  # DELETE: from docx.enum.text import WD_ALIGN_PARAGRAPH
  # KEEP:   footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
  ```
- **Risk Assessment**: None. Python caches module imports, so behavior is identical. The import was already used successfully at function scope.
- **Verification**: `python -c "from src.packets.docx_engine import DocxEngine"` -- import chain works.
- **Batch**: 2

---

### F7-06: Cap critical programs at MAX_PROGRAMS in relevance filter

- **Priority**: Medium -- **NEEDS_DECISION**
- **Source**: Agent 6, Finding F-06
- **File(s)**: `src/packets/relevance.py:218-228`
- **Description**: If all programs have `priority="critical"`, the trimming logic first adds ALL critical programs to `kept`, then fills remaining up to `MAX_PROGRAMS`. If `len(critical_ids) > MAX_PROGRAMS`, the `kept` list exceeds `MAX_PROGRAMS=12`. This is an untested edge case that may be a logic bug or intentional design.
- **Current Code** (lines 218-228):
  ```python
  if len(result) > MAX_PROGRAMS:
      kept: list[dict] = []
      for prog in result:
          if prog["id"] in critical_ids:
              kept.append(prog)  # Could add > MAX items
      for prog in result:
          if prog["id"] not in critical_ids:
              if len(kept) < MAX_PROGRAMS:
                  kept.append(prog)
      result = kept
  ```
- **Proposed Fix (if decision is "cap")**:
  ```python
  if len(result) > MAX_PROGRAMS:
      kept: list[dict] = []
      for prog in result:
          if prog["id"] in critical_ids:
              kept.append(prog)
              if len(kept) >= MAX_PROGRAMS:
                  break  # Cap even critical programs at MAX
      for prog in result:
          if prog["id"] not in critical_ids:
              if len(kept) < MAX_PROGRAMS:
                  kept.append(prog)
      result = kept
  ```
- **Alternative (if decision is "allow overflow")**: Add a docstring comment explaining the intentional behavior and add a test that verifies the current behavior.
- **Risk Assessment**: If capped, a legitimately critical program could be dropped from a Tribe's packet. If not capped, the Hot Sheet could have more than 12 pages. In practice, the current program inventory has only 2-3 critical programs, so this edge case never activates.
- **Verification**: Add `test_all_critical_exceeds_max` to verify whichever behavior is chosen.
- **Batch**: 3 (pending decision)

---

### F7-07: Tighten test_compute_zero_awards assertion

- **Priority**: Medium
- **Source**: Agent 6, Finding F-21
- **File(s)**: `tests/test_economic.py:121`
- **Description**: `assert len(summary.by_program) > 0` is too weak. The test provides 4 programs (`bia_tcr`, `fema_bric`, `epa_gap`, `hud_ihbg`), all present in `PROGRAM_BENCHMARK_AVERAGES`. With zero awards, all 4 should get benchmark entries. The assertion should verify the exact count.
- **Proposed Change**:
  ```python
  # Line 121: change from
  assert len(summary.by_program) > 0
  # to
  assert len(summary.by_program) == 4
  ```
- **Risk Assessment**: None. The test already passes with exactly 4 programs. This only makes the assertion more precise.
- **Verification**: `python -m pytest tests/test_economic.py::TestEconomicImpactCalculator::test_compute_zero_awards -v`
- **Batch**: 1

---

### F7-08: Document single-process assumption in docx_engine.py save()

- **Priority**: Medium
- **Source**: Agent 5, Finding SEC-03
- **File(s)**: `src/packets/docx_engine.py:114-126`
- **Description**: If two processes call `engine.save(document, "epa_123")` simultaneously, both create temp files, then both call `os.replace()` on the same output path. Last writer wins silently. The method should document this limitation.
- **Proposed Change**:
  ```python
  def save(self, document: Document, tribe_id: str) -> Path:
      """Save the document to disk using an atomic write pattern.

      Writes to a temporary file first, then atomically replaces the
      target path. This prevents partial/corrupt files on crash.

      Warning:
          Not safe for concurrent execution by multiple processes
          targeting the same tribe_id. If parallel packet generation
          is needed, use external locking or a task queue with
          single-worker concurrency per tribe_id.

      Args:
          document: The completed python-docx Document.
          tribe_id: Tribe identifier used as filename stem.

      Returns:
          Path to the saved .docx file.
      """
  ```
- **Risk Assessment**: None. Documentation-only change, no functional impact.
- **Verification**: Visual inspection.
- **Batch**: 2

---

## Execution Batches

### Batch 1 (Parallel -- no file overlaps)

| Fix ID | File | Description |
|--------|------|-------------|
| F7-03 | `tests/test_docx_integration.py` | Update test_minimum_test_count threshold: 193 -> 214 |
| F7-04 | `src/packets/orchestrator.py` | Add JSON file size limits (10 MB cap) |
| F7-07 | `tests/test_economic.py` | Tighten assertion: `> 0` -> `== 4` |

These three fixes touch different files with no dependencies. All can be implemented by separate agents simultaneously.

### Batch 2 (Sequential -- all touch docx_engine.py)

| Fix ID | Lines | Description |
|--------|-------|-------------|
| F7-05 | 14, 111 | Move WD_ALIGN_PARAGRAPH import to module level |
| F7-02 | 127 | Add tribe_id path traversal validation |
| F7-08 | 114-126 | Add concurrency warning to save() docstring |
| F7-01 | 131-145 | Close NamedTemporaryFile handle before save |

All four changes target `src/packets/docx_engine.py`. They should be applied by a single agent in one pass to avoid merge conflicts. The recommended order is top-to-bottom: imports (F7-05), then docstring (F7-08), then validation (F7-02), then body (F7-01).

### Batch 3 (Pending Decision)

| Fix ID | File | Description |
|--------|------|-------------|
| F7-06 | `src/packets/relevance.py` | MAX_PROGRAMS cap for critical programs (**NEEDS_DECISION**) |

This fix requires a domain decision: should critical programs be hard-capped at MAX_PROGRAMS=12, or should the overflow be intentional? The decision should come from the project owner. If decided, this fix can run independently (no file overlap with Batches 1 or 2).

---

## Deduplication Log

| Duplicate Group | Agents | Merged Into |
|----------------|--------|-------------|
| Stale test_minimum_test_count threshold | F-20 (Agent 6), G-check-6 (Agent 7), GAP-03 partial (Agent 7) | **F7-03** |
| WD_ALIGN_PARAGRAPH import | C-01 (Agent 3), MEMORY.md note | **F7-05** |

---

## Items Excluded from Fix Plan

### Already Done (Agent 1)
All 14 files in Section A -- organization name removal complete and verified.

### Informational Only (no code change needed)
| ID | Agent | Description |
|----|-------|-------------|
| INFO-01 | 5 | Tribe name/financial data in logs -- appropriate log levels already used |
| INFO-02 | 5 | DOCX metadata not sanitized -- low risk, CONFIDENTIAL document |
| INFO-03 | 5 | Unknown program ID in ecoregion lookup -- minor UX, no crash |
| INFO-04 | 5 | Hazard profile fallback branches -- may be dead code if schema stable |
| INFO-05 | 5 | CFDA normalization defensive coding -- architecturally correct |
| C-INFO | 3 | cell.text assignment safe on freshly created cells |

### Phase 8 Scope (excluded -- new features/tests, not fixes to existing code)
| ID | Description |
|----|-------------|
| GAP-01 | README.md update for Phase 7 features |
| GAP-02 | Tribe count inconsistency across planning docs (575/592) |
| GAP-03 | README test count stale ("52 tests") |
| G-check-5 | Create Phase 8 directory |
| G-check-7 | Define Phase 8 plans |
| G-finding-6 | Create project-level CLAUDE.md |
| G-optional | Tighten `__init__.py` with `__all__` |
| F-03 | New test: float('inf')/NaN obligation handling |
| F-13 | New test: read-only output directory error path |
| F-15 | New test: large program count (50+) in TOC |
| F-19 | New tests: docx_sections.py direct unit tests |
| F-01..F-02 | Test fixture realism improvements (CFDA mismatches) |
| F-04..F-12 | New edge case tests (various) |
| F-14..F-18 | New edge case tests (various) |
| F-22..F-25 | Weak assertion improvements |

### Empty Sections (no findings to process)
| Section | Agent | Status |
|---------|-------|--------|
| B: Code Quality | Agent 2 | Headers present, no content written |
| D: Data Flow | Agent 4 | Headers present, no content written |

---

## Final Verification Sequence

After all batches are complete, run in order:

```bash
# 1. Full test suite -- all 214+ tests must pass
python -m pytest tests/ -v --tb=short

# 2. Organization name removal verification -- zero results expected
python -c "import subprocess, sys; r = subprocess.run(['python', '-m', 'grep', '-ri', 'NCAI|ATNI', '.', '--include=*.py', '--include=*.md', '--include=*.json'], capture_output=True, text=True); print(r.stdout or 'Clean'); sys.exit(1 if 'NCAI' in r.stdout or 'ATNI' in r.stdout else 0)"

# 3. Import chain verification -- no ImportError
python -c "from src.packets.orchestrator import PacketOrchestrator; print('Import OK')"

# 4. docx_engine import verification -- WD_ALIGN_PARAGRAPH at module level
python -c "from src.packets.docx_engine import DocxEngine; print('DocxEngine import OK')"

# 5. Verify test count meta-test with new threshold
python -m pytest tests/test_docx_integration.py -k test_minimum_test_count -v
```

---

*Generated by Agent 8 (Conflict Detection + Fix Plan Orchestrator) | 2026-02-10*
*Input: REVIEW-COORDINATION.md (7 agent sections, 40 total findings)*
*Output: 8 unique fix items across 3 execution batches*
