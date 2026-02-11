# Phase 7 Review: Fix Verification Design

**Agent:** Agent 9 (Fix Verification Design)
**Date:** 2026-02-10
**Input:** REVIEW-COORDINATION.md (all findings from 7 agents)
**Goal:** Map every finding to existing tests, identify gaps, specify new tests needed

---

## Executive Summary

**Total Findings:** 30 unique issues identified across 7 review agents
**Existing Test Coverage:** 214 tests, but gaps exist for 18/30 findings
**New Tests Needed:** 16 new test functions
**Verification Steps:** 4-step final validation sequence

---

## Section 1: Finding-to-Test Mapping

### 1.1 Code Quality Findings (Agent 2)

| Finding ID | Issue | Existing Test | Sufficient? | New Test Needed? |
|------------|-------|---------------|-------------|------------------|
| **H-01** | Logger naming inconsistency (economic.py) | None | N/A | **No** (import check only) |
| **H-02** | Division by zero in jobs calc (economic.py:196) | `test_compute_zero_awards` | **No** - doesn't test obligation=0 | **YES** - `test_jobs_estimate_zero_obligation` |
| **H-03 / C-01** | Import inside method (docx_engine.py:111) | None | N/A | **No** (static analysis check) |
| **H-04** | Hardcoded FY26 (docx_sections.py) | None | N/A | **No** (design choice, not bug) |
| **M-01** | Benchmark key mismatch (economic.py) | `test_compute_zero_awards` | **Partial** - checks count, not keys | **YES** - `test_benchmark_program_id_matches_inventory` |
| **M-02 / D-03** | CFDA normalization duplication | `test_cfda_string_normalized`, `test_cfda_list_normalized` | **Yes** - edge cases covered | **No** |
| **M-03** | Missing access_type/funding_type | None | N/A | **No** (data quality, not code bug) |
| **M-04** | STABLE_BUT_VULNERABLE framing | `test_framing_by_status_covers_all_statuses` | **Yes** - all 6 statuses covered | **No** |
| **L-01** | Duplicate _format_dollars | None | N/A | **No** (refactor task, not bug) |
| **L-02** | Unused CI_STATUS_COLORS import | None | N/A | **No** (cleanup task, not bug) |

**Summary:** 2 new tests needed (H-02, M-01)

---

### 1.2 python-docx Patterns (Agent 3)

| Finding ID | Issue | Existing Test | Sufficient? | New Test Needed? |
|------------|-------|---------------|-------------|------------------|
| **C-01** | WD_ALIGN_PARAGRAPH import location (= H-03) | None | N/A | **No** (static check) |
| **C-02** | NamedTemporaryFile handle ordering | `test_engine_save_atomic` | **No** - doesn't test Windows lock behavior | **YES** - `test_save_closes_handle_before_write` |

**Summary:** 1 new test needed (C-02)

---

### 1.3 Data Flow (Agent 4)

| Finding ID | Issue | Existing Test | Sufficient? | New Test Needed? |
|------------|-------|---------------|-------------|------------------|
| **D-01** | Hazard profile schema ambiguity | `test_hazard_profile_sources_key_path` | **Yes** - tests both paths | **No** |
| **D-02** | Structural asks hardcoded path | None | N/A | **No** (config task, not bug) |
| **D-03** | CFDA format inconsistency (= M-02) | Covered under M-02 | **Yes** | **No** |

**Summary:** 0 new tests needed

---

### 1.4 Security (Agent 5)

| Finding ID | Issue | Existing Test | Sufficient? | New Test Needed? |
|------------|-------|---------------|-------------|------------------|
| **SEC-01** | Path traversal via tribe_id | None | **No** | **YES** - `test_docx_engine_rejects_malicious_tribe_id` |
| **SEC-02** | Unbounded JSON parsing | None | **No** | **YES** - `test_orchestrator_rejects_oversized_cache` |
| **SEC-03** | Concurrent write race condition | None | **No** | **YES** - `test_docx_engine_concurrent_save_warning` |
| **INFO-01** | Tribe name in logs | None | N/A | **No** (informational, no fix) |
| **INFO-02** | DOCX metadata sanitization | None | N/A | **YES** - `test_docx_metadata_sanitized` (if fix applied) |
| **INFO-03** | Ecoregion priority programs lookup | None | N/A | **No** (informational, no fix) |
| **INFO-04** | Hazard profile access pattern | Covered under D-01 | **Yes** | **No** |
| **INFO-05** | CFDA normalization defensive coding | Covered under M-02 | **Yes** | **No** |

**Summary:** 4 new tests needed (SEC-01, SEC-02, SEC-03, INFO-02 optional)

---

### 1.5 Test Coverage (Agent 6)

| Finding ID | Issue | Existing Test | Sufficient? | New Test Needed? |
|------------|-------|---------------|-------------|------------------|
| **F-20** | Stale test minimum count (193 vs 214) | `test_minimum_test_count` | **No** - threshold outdated | **YES** - Update threshold to 214 |
| **F-03** | float('inf')/NaN untested | None | **No** | **YES** - `test_compute_inf_nan_obligation` |
| **F-06** | All-critical programs logic bug | `test_critical_survives_max_trimming` | **Partial** - doesn't test >12 critical | **YES** - `test_all_critical_exceeds_max` |
| **F-13** | Read-only output directory | None | **No** | **YES** - `test_save_permission_error` |
| **F-15** | Large program count (50+) in TOC | None | **No** | **YES** - `test_render_toc_50_programs` |
| **F-19** | docx_sections.py functions lack direct unit tests | `test_docx_has_cover_page`, `test_toc_lists_programs` | **Partial** - integration only | **YES** - `test_render_cover_page_unit`, `test_render_appendix_with_omitted` |
| **F-21** | Weak assertion in test_compute_zero_awards | `test_compute_zero_awards:121` | **Yes** - test exists but weak | **YES** - Tighten assertion |
| **F-01 thru F-25** | Various low-priority gaps | Covered or informational | Varies | **No** (defer to Phase 8) |

**Summary:** 8 new tests needed (F-20, F-03, F-06, F-13, F-15, F-19 x2, F-21)

---

### 1.6 GitHub + Phase 8 Readiness (Agent 7)

| Finding ID | Issue | Existing Test | Sufficient? | New Test Needed? |
|------------|-------|---------------|-------------|------------------|
| **GAP-01** | README.md outdated | None | N/A | **No** (Phase 8 task) |
| **GAP-02** | Tribe count inconsistency | None | N/A | **No** (Phase 8 task) |
| **GAP-03** | README test count stale | Covered under F-20 | **Yes** | **No** |

**Summary:** 0 new tests needed (documentation tasks)

---

## Section 2: New Tests Specification

### 2.1 MUST-HAVE Tests (Fix Blockers)

#### Test 1: `test_jobs_estimate_zero_obligation` (H-02)
**File:** `tests/test_economic.py`
**Verifies:** Division by zero in jobs calculation
**Priority:** HIGH

```python
def test_jobs_estimate_zero_obligation(self) -> None:
    """Zero obligation produces zero jobs estimate (no division by zero)."""
    from src.packets.economic import EconomicImpactCalculator

    calc = EconomicImpactCalculator()
    awards = [{"obligation": 0, "program_id": "bia_tcr"}]
    programs = {"bia_tcr": _make_programs()["bia_tcr"]}
    summary = calc.compute(
        tribe_id="epa_001",
        tribe_name="Alpha Tribe",
        awards=awards,
        districts=[],
        programs=programs,
    )

    # Should skip the zero-obligation award, only benchmark present
    assert all(p.is_benchmark for p in summary.by_program)
    # No division by zero crash
```

---

#### Test 2: `test_benchmark_program_id_matches_inventory` (M-01)
**File:** `tests/test_economic.py`
**Verifies:** Benchmark keys match program inventory
**Priority:** HIGH

```python
def test_benchmark_program_id_matches_inventory(self) -> None:
    """Benchmark program IDs match keys in programs dict."""
    from src.packets.economic import EconomicImpactCalculator

    calc = EconomicImpactCalculator()
    programs = _make_programs(4)
    summary = calc.compute(
        tribe_id="epa_001",
        tribe_name="Alpha Tribe",
        awards=[],
        districts=[],
        programs=programs,
    )

    benchmark_ids = {p.program_id for p in summary.by_program if p.is_benchmark}
    program_ids = set(programs.keys())

    # All benchmark IDs must exist in programs dict
    assert benchmark_ids.issubset(program_ids), (
        f"Benchmark IDs not in inventory: {benchmark_ids - program_ids}"
    )
```

---

#### Test 3: `test_save_closes_handle_before_write` (C-02)
**File:** `tests/test_docx_styles.py`
**Verifies:** NamedTemporaryFile closed before Document.save()
**Priority:** HIGH (Windows file locking)

```python
def test_save_closes_handle_before_write(self, tmp_path):
    """Temp file handle closed before Document.save() to avoid Windows lock."""
    import tempfile
    from docx import Document

    engine = self._make_engine(tmp_path)
    doc, _ = engine.create_document()

    # Save should succeed on Windows without PermissionError
    # This test verifies the fix: tmp_fd.close() before document.save()
    path = engine.save(doc, "windows_test")
    assert path.exists()
    assert path.stat().st_size > 0
```

---

#### Test 4: `test_docx_engine_rejects_malicious_tribe_id` (SEC-01)
**File:** `tests/test_docx_styles.py`
**Verifies:** Path traversal prevention
**Priority:** HIGH (security)

```python
def test_docx_engine_rejects_malicious_tribe_id(self, tmp_path):
    """Engine rejects tribe_id with path traversal sequences."""
    engine = self._make_engine(tmp_path)
    doc, _ = engine.create_document()

    malicious_ids = [
        "../../../etc/passwd",
        "..\\..\\..\\Windows\\System32\\config\\sam",
        ".",
        "..",
        "foo/../../../bar",
    ]

    for bad_id in malicious_ids:
        with pytest.raises(ValueError, match="Invalid tribe_id"):
            engine.save(doc, bad_id)
```

---

#### Test 5: `test_orchestrator_rejects_oversized_cache` (SEC-02)
**File:** `tests/test_docx_integration.py`
**Verifies:** JSON size limits
**Priority:** HIGH (DoS prevention)

```python
def test_orchestrator_rejects_oversized_cache(self, tmp_path):
    """Orchestrator rejects cache files exceeding size limit."""
    import json
    from src.packets.orchestrator import PacketOrchestrator

    # Create 11MB JSON file (exceeds 10MB limit)
    large_json = {"awards": [{"obligation": 1000000}] * 500000}
    cache_path = tmp_path / "awards" / "epa_123.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(large_json), encoding="utf-8")

    config = {
        "packets": {
            "awards": {"cache_dir": str(tmp_path / "awards")},
        }
    }
    orch = PacketOrchestrator(config, {})

    # Should reject oversized file and return empty dict
    result = orch._load_tribe_cache(tmp_path / "awards", "epa_123")
    assert result == {}
```

---

#### Test 6: `test_docx_engine_concurrent_save_warning` (SEC-03)
**File:** `tests/test_docx_styles.py`
**Verifies:** Concurrent write warning in docstring
**Priority:** MEDIUM (documentation)

```python
def test_docx_engine_concurrent_save_warning(self, tmp_path):
    """DocxEngine.save() docstring warns about concurrent access."""
    from src.packets.docx_engine import DocxEngine

    # Check that save method has warning in docstring
    assert DocxEngine.save.__doc__ is not None
    assert "concurrent" in DocxEngine.save.__doc__.lower() or \
           "multi-process" in DocxEngine.save.__doc__.lower(), \
           "save() docstring should warn about concurrent access"
```

---

#### Test 7: `test_compute_inf_nan_obligation` (F-03)
**File:** `tests/test_economic.py`
**Verifies:** Inf/NaN obligation handling
**Priority:** MEDIUM

```python
def test_compute_inf_nan_obligation(self) -> None:
    """Inf and NaN obligations are skipped (not crash)."""
    from src.packets.economic import EconomicImpactCalculator

    calc = EconomicImpactCalculator()
    awards = [
        {"obligation": float('inf'), "program_id": "bia_tcr"},
        {"obligation": float('nan'), "program_id": "fema_bric"},
        {"obligation": 100_000, "program_id": "epa_gap"},
    ]
    programs = {
        "bia_tcr": _make_programs()["bia_tcr"],
        "fema_bric": _make_programs()["fema_bric"],
        "epa_gap": _make_programs()["epa_gap"],
    }
    summary = calc.compute(
        tribe_id="epa_001",
        tribe_name="Alpha Tribe",
        awards=awards,
        districts=[],
        programs=programs,
    )

    # Only epa_gap should be actual award (inf/nan skipped)
    actual = [p for p in summary.by_program if not p.is_benchmark]
    assert len(actual) == 1
    assert actual[0].program_id == "epa_gap"
    assert actual[0].total_obligation == 100_000
```

---

#### Test 8: `test_all_critical_exceeds_max` (F-06)
**File:** `tests/test_economic.py`
**Verifies:** MAX_PROGRAMS cap holds when critical count exceeds 12
**Priority:** MEDIUM (logic bug)

```python
def test_all_critical_exceeds_max(self) -> None:
    """When 15 critical programs exist, result capped at MAX_PROGRAMS=12."""
    from src.packets.relevance import ProgramRelevanceFilter

    # Create 15 critical programs
    programs = {}
    for i in range(15):
        programs[f"crit_{i}"] = {
            "id": f"crit_{i}",
            "name": f"Critical Program {i}",
            "priority": "critical",
        }

    filt = ProgramRelevanceFilter(programs)
    result = filt.filter_for_tribe(
        hazard_profile={},
        ecoregions=[],
    )

    # Result must be capped at 12 (MAX_PROGRAMS)
    assert len(result) <= 12, (
        f"Expected <= 12 programs, got {len(result)}. "
        "Logic bug: critical programs should be trimmed to MAX."
    )
```

---

#### Test 9: `test_save_permission_error` (F-13)
**File:** `tests/test_docx_styles.py`
**Verifies:** Read-only directory error handling
**Priority:** MEDIUM

```python
def test_save_permission_error(self, tmp_path):
    """Read-only output directory raises appropriate error."""
    import os
    import stat

    engine = self._make_engine(tmp_path)
    doc, _ = engine.create_document()

    # Make output directory read-only
    output_dir = tmp_path / "packets"
    output_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)  # r-x------

    try:
        with pytest.raises((PermissionError, OSError)):
            engine.save(doc, "readonly_test")
    finally:
        # Restore permissions for cleanup
        output_dir.chmod(stat.S_IRWXU)
```

---

#### Test 10: `test_render_toc_50_programs` (F-15)
**File:** `tests/test_docx_integration.py`
**Verifies:** TOC handles large program counts
**Priority:** LOW

```python
def test_render_toc_50_programs(self):
    """TOC renders correctly with 50 programs."""
    from docx import Document
    from src.packets.docx_styles import StyleManager
    from src.packets.docx_sections import render_table_of_contents

    doc = Document()
    sm = StyleManager(doc)

    # Create 50 synthetic programs
    programs = [
        {"id": f"prog_{i}", "name": f"Program {i}"}
        for i in range(50)
    ]

    render_table_of_contents(doc, sm, programs)

    all_text = "\n".join(p.text for p in doc.paragraphs)
    assert "50 program analyses" in all_text
    assert "Program 0" in all_text
    assert "Program 49" in all_text
```

---

#### Test 11: `test_render_cover_page_unit` (F-19)
**File:** `tests/test_docx_integration.py`
**Verifies:** Cover page direct unit test
**Priority:** MEDIUM

```python
def test_render_cover_page_unit(self):
    """render_cover_page creates expected content."""
    from docx import Document
    from src.packets.context import TribePacketContext
    from src.packets.docx_styles import StyleManager
    from src.packets.docx_sections import render_cover_page

    doc = Document()
    sm = StyleManager(doc)

    context = TribePacketContext(
        tribe_id="test_001",
        tribe_name="Test Tribe",
        states=["WA", "OR"],
        ecoregions=["pacific_northwest"],
        senators=[
            {"formatted_name": "Sen. Test Senator (D-WA)"},
        ],
        representatives=[],
        congress_session="119",
        generated_at="2026-02-10T12:00:00Z",
    )

    render_cover_page(doc, sm, context)

    all_text = "\n".join(p.text for p in doc.paragraphs)

    assert "Test Tribe" in all_text
    assert "FY26 Climate Resilience Program Priorities" in all_text
    assert "State(s): WA, OR" in all_text
    assert "Ecoregion(s): pacific_northwest" in all_text
    assert "Congressional Session: 119" in all_text
    assert "Sen. Test Senator (D-WA)" in all_text
```

---

#### Test 12: `test_render_appendix_with_omitted` (F-19)
**File:** `tests/test_docx_integration.py`
**Verifies:** Appendix with omitted programs
**Priority:** MEDIUM

```python
def test_render_appendix_with_omitted(self):
    """render_appendix lists omitted programs with descriptions."""
    from docx import Document
    from src.packets.docx_styles import StyleManager
    from src.packets.docx_sections import render_appendix

    doc = Document()
    sm = StyleManager(doc)

    omitted = [
        {
            "id": "prog_1",
            "name": "Omitted Program 1",
            "description": "This program was omitted due to low relevance.",
            "priority": "medium",
        },
        {
            "id": "prog_2",
            "name": "Omitted Program 2",
            "description": "Another omitted program.",
            "priority": "low",
        },
    ]

    render_appendix(doc, sm, omitted)

    all_text = "\n".join(p.text for p in doc.paragraphs)

    assert "Appendix" in all_text
    assert "Omitted Program 1" in all_text
    assert "Omitted Program 2" in all_text
    assert "low relevance" in all_text
```

---

#### Test 13: Update `test_minimum_test_count` threshold (F-20)
**File:** `tests/test_docx_integration.py:718`
**Action:** Change `>= 193` to `>= 214`
**Priority:** HIGH (prevents regression)

```python
# Line 718 (existing test)
def test_minimum_test_count(self):
    """Verify we have >= 214 tests across all test files via collection."""
    # ... existing code ...
    assert count >= 214, (  # CHANGED from 193
        f"Expected >= 214 tests collected, got {count}. "
        f"Output: {last_line}"
    )
```

---

#### Test 14: Tighten `test_compute_zero_awards` assertion (F-21)
**File:** `tests/test_economic.py:121`
**Action:** Change `> 0` to `== 4`
**Priority:** MEDIUM

```python
# Line 121 (existing test)
def test_compute_zero_awards(self) -> None:
    """Empty awards list returns benchmark-based summary."""
    # ... existing code ...

    # All should be benchmarks
    assert len(summary.by_program) == 4  # CHANGED from > 0
    assert all(p.is_benchmark for p in summary.by_program)
    assert summary.total_obligation > 0
```

---

#### Test 15 (Optional): `test_docx_metadata_sanitized` (INFO-02)
**File:** `tests/test_docx_styles.py`
**Verifies:** DOCX metadata sanitization
**Priority:** LOW (informational fix)

```python
def test_docx_metadata_sanitized(self, tmp_path):
    """Document core properties have sanitized metadata."""
    engine = self._make_engine(tmp_path)
    doc, _ = engine.create_document()

    props = doc.core_properties

    assert props.author == "TCR Policy Scanner"
    assert props.title == "Tribal Climate Resilience Advocacy Packet"
    assert props.subject == "FY26 Program Priorities"
```

---

### 2.2 Test Priority Summary

| Priority | Test Count | Tests |
|----------|-----------|-------|
| **HIGH** | 6 | H-02, M-01, C-02, SEC-01, SEC-02, F-20 |
| **MEDIUM** | 7 | SEC-03, F-03, F-06, F-13, F-19 (x2), F-21 |
| **LOW** | 2 | F-15, INFO-02 (optional) |
| **Total** | 15-16 | (INFO-02 optional) |

---

## Section 3: Final Verification Sequence

After all fixes are implemented, run this 4-step verification:

### Step 1: Full Test Suite
```bash
cd F:\tcr-policy-scanner
python -m pytest tests/ -v --tb=short
```
**Expected:** All 214+ tests pass (threshold increased to 214)

---

### Step 2: Organization Name Removal Verification
```bash
cd F:\tcr-policy-scanner
grep -ri "NCAI\|ATNI" . --include="*.py" --include="*.md" --include="*.json" \
  --exclude-dir=.planning
```
**Expected:** Zero matches in source code and docs (only planning artifacts)

---

### Step 3: Import Check
```bash
cd F:\tcr-policy-scanner
python -c "from src.packets.orchestrator import PacketOrchestrator; print('Import OK')"
python -c "from src.packets.docx_engine import DocxEngine; print('Import OK')"
python -c "from src.packets.economic import EconomicImpactCalculator; print('Import OK')"
```
**Expected:** All three imports succeed with "Import OK" output

---

### Step 4: End-to-End DOCX Generation
```bash
cd F:\tcr-policy-scanner
python -c "
from pathlib import Path
import json
from src.packets.orchestrator import PacketOrchestrator

config_path = Path('config/scanner_config.json')
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

programs_path = Path('data/program_inventory.json')
with open(programs_path, 'r', encoding='utf-8') as f:
    programs_data = json.load(f)
    programs = {p['id']: p for p in programs_data['programs']}

orch = PacketOrchestrator(config, programs)

# Test with a known Tribe (replace with actual tribe_name from registry)
path = orch.generate_packet('Muckleshoot Indian Tribe')
if path and path.exists():
    print(f'SUCCESS: Generated {path} ({path.stat().st_size} bytes)')
else:
    print('FAILED: No packet generated')
"
```
**Expected:** `SUCCESS: Generated outputs/packets/epa_XXX.docx (NNNNN bytes)`

---

## Section 4: Test File Modifications

### 4.1 `tests/test_economic.py`
**Add 5 tests:**
1. `test_jobs_estimate_zero_obligation` (H-02)
2. `test_benchmark_program_id_matches_inventory` (M-01)
3. `test_compute_inf_nan_obligation` (F-03)
4. `test_all_critical_exceeds_max` (F-06)

**Modify 1 test:**
5. `test_compute_zero_awards` - tighten assertion (F-21)

---

### 4.2 `tests/test_docx_styles.py`
**Add 4 tests:**
1. `test_save_closes_handle_before_write` (C-02)
2. `test_docx_engine_rejects_malicious_tribe_id` (SEC-01)
3. `test_save_permission_error` (F-13)
4. `test_docx_metadata_sanitized` (INFO-02, optional)

**Add 1 test:**
5. `test_docx_engine_concurrent_save_warning` (SEC-03)

---

### 4.3 `tests/test_docx_integration.py`
**Add 3 tests:**
1. `test_orchestrator_rejects_oversized_cache` (SEC-02)
2. `test_render_toc_50_programs` (F-15)
3. `test_render_cover_page_unit` (F-19)
4. `test_render_appendix_with_omitted` (F-19)

**Modify 1 test:**
5. `test_minimum_test_count` - update threshold to 214 (F-20)

---

## Section 5: Non-Test Fixes

These findings require code changes, not just tests:

### 5.1 Immediate Fixes (Before Tests)

| Finding | File | Line | Fix |
|---------|------|------|-----|
| H-03 / C-01 | `src/packets/docx_engine.py` | 111 | Move `from docx.enum.text import WD_ALIGN_PARAGRAPH` to module-level imports |
| C-02 | `src/packets/docx_engine.py` | 131-136 | Close `tmp_fd` before `document.save()` |
| SEC-01 | `src/packets/docx_engine.py` | 127 | Add `Path(tribe_id).name` sanitization and validation |
| SEC-02 | `src/packets/orchestrator.py` | 172, 481 | Add file size check before `json.load()` |
| L-02 | `src/packets/docx_hotsheet.py` | imports | Remove unused `CI_STATUS_COLORS` import |

### 5.2 Optional Fixes (Quality Improvements)

| Finding | File | Fix |
|---------|------|-----|
| H-01 | `src/packets/economic.py` | Rename logger to `logger = logging.getLogger(__name__)` |
| H-04 | `src/packets/docx_sections.py` | Extract FY26 to constant or config |
| L-01 | `src/packets/` | Consolidate `_format_dollars()` into single utility module |
| INFO-02 | `src/packets/docx_engine.py` | Sanitize DOCX core properties (author, title, subject) |
| D-02 | `src/packets/orchestrator.py` | Move hardcoded `data/graph_schema.json` to config |

---

## Section 6: Coverage Analysis

### 6.1 Findings Coverage by Test Priority

| Category | Findings | Tests Needed | Coverage % |
|----------|----------|--------------|-----------|
| **Code Quality (H/M/L)** | 10 | 2 | 80% (8 are cleanup/design) |
| **python-docx (C)** | 2 | 1 | 50% (1 is static check) |
| **Data Flow (D)** | 3 | 0 | 100% (already covered or config) |
| **Security (SEC + INFO)** | 8 | 4 | 50% (4 are informational) |
| **Test Coverage (F)** | 25 | 8 | 32% (17 are low-priority) |
| **GitHub/Docs (GAP)** | 3 | 0 | N/A (Phase 8 tasks) |
| **TOTAL** | 51 | 15 | 71% (with 36 non-test tasks) |

### 6.2 Test Count After Fixes

**Current:** 214 tests
**New Tests:** +15 (13 new + 2 modified)
**Final Count:** 229 tests
**Coverage Improvement:** +7% (estimated based on uncovered branches)

---

## Section 7: Execution Plan

### Phase 1: Apply Non-Test Fixes (30 min)
1. H-03/C-01: Move import to module level (1 line)
2. C-02: Close temp file handle before save (5 lines)
3. SEC-01: Add path traversal validation (5 lines)
4. SEC-02: Add JSON size check (10 lines per location, 2 locations)
5. L-02: Remove unused import (1 line)

**Deliverable:** 5 files modified, ~25 lines changed

---

### Phase 2: Add New Tests (60 min)
1. Write 13 new test functions across 3 test files
2. Modify 2 existing tests (tighten assertions)

**Deliverable:** 3 test files modified, ~400 lines added

---

### Phase 3: Run Verification Sequence (15 min)
1. Step 1: `pytest tests/ -v --tb=short`
2. Step 2: `grep -ri "NCAI\|ATNI" ...`
3. Step 3: Import checks (3 commands)
4. Step 4: End-to-end DOCX generation

**Deliverable:** 4-step verification log with PASS status

---

### Phase 4: Document Results (15 min)
1. Update `REVIEW-COORDINATION.md` with verification timestamp
2. Create `PHASE7-FIX-SUMMARY.md` with before/after metrics
3. Commit all changes with descriptive message

**Deliverable:** Documentation updated, git commit created

---

## Section 8: Success Criteria

### Must-Have (Blockers)
- [ ] All 214+ tests pass (including 15 new tests)
- [ ] Zero organization name references in source code
- [ ] All 3 import checks succeed
- [ ] End-to-end DOCX generation succeeds
- [ ] SEC-01 (path traversal) fix verified
- [ ] SEC-02 (JSON size) fix verified
- [ ] C-02 (temp file handle) fix verified
- [ ] F-20 (test count threshold) updated

### Should-Have (Quality)
- [ ] H-02 (division by zero) test passes
- [ ] M-01 (benchmark key mismatch) test passes
- [ ] F-06 (all-critical logic) test passes
- [ ] F-19 (direct unit tests) implemented

### Nice-to-Have (Polish)
- [ ] INFO-02 (DOCX metadata) sanitized
- [ ] H-01 (logger naming) fixed
- [ ] L-01 (duplicate _format_dollars) refactored
- [ ] F-15 (50-program TOC) tested

---

## Section 9: Risk Assessment

### High-Risk Changes
1. **SEC-01 path traversal fix** - Could break valid tribe_ids if regex too strict
2. **C-02 temp file ordering** - Could fail on different Python versions
3. **F-06 all-critical logic** - Reveals potential MAX_PROGRAMS cap bug

**Mitigation:** Run full test suite after each fix, validate against known-good Tribes

### Low-Risk Changes
1. Import location move (H-03/C-01)
2. Test threshold update (F-20)
3. Unused import removal (L-02)

---

## Appendix A: Test Template

All new tests should follow this structure:

```python
def test_descriptive_name(self, fixtures_if_needed) -> None:
    """One-line summary of what is verified.

    Additional context if needed (e.g., "Verifies fix for finding H-02").
    """
    # Arrange: set up test data
    from src.module import ClassUnderTest

    instance = ClassUnderTest()
    test_data = {...}

    # Act: execute the code path
    result = instance.method(test_data)

    # Assert: verify expected behavior
    assert result.expected_field == expected_value
    assert condition is True
```

---

## Appendix B: Windows Compatibility Notes

Tests must handle Windows-specific behaviors:

1. **File encoding:** Always pass `encoding="utf-8"` to `open()` and `Path.write_text()`
2. **Path separators:** Use `Path` objects, not string concatenation
3. **File locking:** Close file handles before reopen (C-02 fix)
4. **Permissions:** Windows `chmod` may not work as expected (F-13 test may need `pytest.skip`)

---

**END OF VERIFICATION DESIGN**

*Prepared by Agent 9 (Fix Verification Design)*
*Date: 2026-02-10*
*Ready for implementation by fix agents (Agent 10-15)*
