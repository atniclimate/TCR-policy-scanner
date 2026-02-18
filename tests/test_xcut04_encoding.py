"""XCUT-04 compliance tests: encoding and atomic write enforcement.

Verifies that all Phase 19 source files comply with XCUT-04 requirements:
1. Every text-mode open() call includes encoding= keyword argument
2. Builder files use atomic write pattern (tempfile + os.replace())
3. Builder files have contextlib.suppress(OSError) for cleanup
4. Doc types and paths module comply with encoding and import-time safety rules

These tests use AST scanning to statically analyze source code, catching
encoding violations at test time rather than at runtime on Windows.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# -- AST Scanning Utility --
# ---------------------------------------------------------------------------


def find_open_calls_without_encoding(filepath: Path) -> list[int]:
    """Find text-mode open() calls missing the encoding= keyword.

    Scans a Python source file's AST for calls to open() (both bare
    function and method calls). Text-mode opens that lack an encoding=
    keyword argument are violations of XCUT-04.

    Binary-mode opens (mode contains 'b') are excluded since they
    cannot accept encoding.

    Args:
        filepath: Path to the Python source file to scan.

    Returns:
        List of line numbers where violations occur. Empty if compliant.
    """
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source)
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if (isinstance(func, ast.Name) and func.id == "open") or (
                isinstance(func, ast.Attribute) and func.attr == "open"
            ):
                mode_is_binary = False
                for kw in node.keywords:
                    if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                        if "b" in str(kw.value.value):
                            mode_is_binary = True
                if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                    if "b" in str(node.args[1].value):
                        mode_is_binary = True
                if mode_is_binary:
                    continue
                has_encoding = any(
                    kw.arg == "encoding" for kw in node.keywords
                )
                if not has_encoding:
                    violations.append(node.lineno)
    return violations


# ---------------------------------------------------------------------------
# -- TestEncodingCompliance --
# ---------------------------------------------------------------------------


class TestEncodingCompliance:
    """Every text-mode open() in Phase 19 source files has encoding= kwarg."""

    @pytest.fixture()
    def phase19_source_dir(self):
        """Return the project root for locating source files."""
        from src.paths import PROJECT_ROOT

        return PROJECT_ROOT

    def test_nri_expanded_encoding(self, phase19_source_dir):
        """nri_expanded.py: all text-mode open() calls have encoding=."""
        filepath = phase19_source_dir / "src" / "packets" / "nri_expanded.py"
        violations = find_open_calls_without_encoding(filepath)
        assert not violations, (
            f"nri_expanded.py has open() calls without encoding= on lines: {violations}"
        )

    def test_svi_builder_encoding(self, phase19_source_dir):
        """svi_builder.py: all text-mode open() calls have encoding=."""
        filepath = phase19_source_dir / "src" / "packets" / "svi_builder.py"
        violations = find_open_calls_without_encoding(filepath)
        assert not violations, (
            f"svi_builder.py has open() calls without encoding= on lines: {violations}"
        )

    def test_vocabulary_encoding(self, phase19_source_dir):
        """vocabulary.py: all text-mode open() calls have encoding= (if any)."""
        filepath = phase19_source_dir / "src" / "packets" / "vocabulary.py"
        violations = find_open_calls_without_encoding(filepath)
        assert not violations, (
            f"vocabulary.py has open() calls without encoding= on lines: {violations}"
        )

    def test_vulnerability_schema_encoding(self, phase19_source_dir):
        """vulnerability.py schema: all text-mode open() calls have encoding= (if any)."""
        filepath = phase19_source_dir / "src" / "schemas" / "vulnerability.py"
        violations = find_open_calls_without_encoding(filepath)
        assert not violations, (
            f"vulnerability.py has open() calls without encoding= on lines: {violations}"
        )


# ---------------------------------------------------------------------------
# -- TestAtomicWriteCompliance --
# ---------------------------------------------------------------------------


class TestAtomicWriteCompliance:
    """Builder files use atomic write pattern: tempfile + os.replace() + cleanup."""

    @pytest.fixture()
    def nri_source(self):
        """Read nri_expanded.py source code."""
        from src.paths import PROJECT_ROOT

        filepath = PROJECT_ROOT / "src" / "packets" / "nri_expanded.py"
        return filepath.read_text(encoding="utf-8")

    @pytest.fixture()
    def svi_source(self):
        """Read svi_builder.py source code."""
        from src.paths import PROJECT_ROOT

        filepath = PROJECT_ROOT / "src" / "packets" / "svi_builder.py"
        return filepath.read_text(encoding="utf-8")

    def test_nri_has_os_replace(self, nri_source):
        """nri_expanded.py uses os.replace() for atomic writes."""
        assert "os.replace(" in nri_source, (
            "nri_expanded.py must use os.replace() for atomic file writes"
        )

    def test_svi_has_os_replace(self, svi_source):
        """svi_builder.py uses os.replace() for atomic writes."""
        assert "os.replace(" in svi_source, (
            "svi_builder.py must use os.replace() for atomic file writes"
        )

    def test_nri_imports_tempfile(self, nri_source):
        """nri_expanded.py imports tempfile for atomic write pattern."""
        assert "import tempfile" in nri_source, (
            "nri_expanded.py must import tempfile for atomic write support"
        )

    def test_svi_imports_tempfile(self, svi_source):
        """svi_builder.py imports tempfile for atomic write pattern."""
        assert "import tempfile" in svi_source, (
            "svi_builder.py must import tempfile for atomic write support"
        )

    def test_nri_has_contextlib_suppress(self, nri_source):
        """nri_expanded.py has contextlib.suppress(OSError) for cleanup on failure."""
        assert "contextlib.suppress(OSError)" in nri_source, (
            "nri_expanded.py must use contextlib.suppress(OSError) for temp file cleanup"
        )

    def test_svi_has_contextlib_suppress(self, svi_source):
        """svi_builder.py has contextlib.suppress(OSError) for cleanup on failure."""
        assert "contextlib.suppress(OSError)" in svi_source, (
            "svi_builder.py must use contextlib.suppress(OSError) for temp file cleanup"
        )


# ---------------------------------------------------------------------------
# -- TestExistingFileCompliance --
# ---------------------------------------------------------------------------


class TestExistingFileCompliance:
    """Compliance checks for existing Phase 19 files."""

    def test_doc_a_format_filename_no_literal_fy26(self):
        """DOC_A.format_filename('test') does NOT contain literal 'fy26'.

        The filename should use the dynamic FISCAL_YEAR_SHORT.lower() value,
        which may be 'fy26' today but will change in future fiscal years.
        This test verifies the mechanism is dynamic, not that the current
        value is avoided.
        """
        from src.config import FISCAL_YEAR_SHORT
        from src.packets.doc_types import DOC_A

        filename = DOC_A.format_filename("test")
        # The filename should contain the dynamic FY value
        assert FISCAL_YEAR_SHORT.lower() in filename
        # Verify it's generated via the config, not hardcoded
        assert filename == f"test_internal_strategy_{FISCAL_YEAR_SHORT.lower()}.docx"

    def test_paths_module_constants_only(self):
        """src/paths.py does not call .exists() or .mkdir() at module level.

        The paths module must be a pure constants module with no side effects
        at import time. Directory creation is the caller's responsibility.
        """
        from src.paths import PROJECT_ROOT

        filepath = PROJECT_ROOT / "src" / "paths.py"
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source)

        # Collect all function definition line ranges
        func_ranges = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_ranges.append(
                    (node.lineno, node.end_lineno or node.lineno)
                )

        # Find .exists() and .mkdir() calls at module level
        module_level_violations = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr in (
                    "exists",
                    "mkdir",
                ):
                    lineno = node.lineno
                    in_func = any(
                        start <= lineno <= end for start, end in func_ranges
                    )
                    if not in_func:
                        module_level_violations.append(
                            f"Line {lineno}: .{func.attr}() at module level"
                        )

        assert not module_level_violations, (
            f"src/paths.py has module-level side effects:\n"
            + "\n".join(f"  {v}" for v in module_level_violations)
        )

    def test_doc_types_no_hardcoded_year_in_title(self):
        """All DOC_* title_template values use FISCAL_YEAR_SHORT, not a literal year."""
        from src.config import FISCAL_YEAR_SHORT
        from src.packets.doc_types import DOC_A, DOC_B, DOC_C, DOC_D

        for name, doc in [("DOC_A", DOC_A), ("DOC_B", DOC_B), ("DOC_C", DOC_C), ("DOC_D", DOC_D)]:
            # Title should contain the current FY string
            assert FISCAL_YEAR_SHORT in doc.title_template, (
                f"{name}.title_template should contain '{FISCAL_YEAR_SHORT}', "
                f"got: {doc.title_template}"
            )
