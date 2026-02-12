"""Cross-cutting compliance tests for TCR Policy Scanner.

Verifies three compliance categories programmatically:

  XCUT-01: Air gap compliance -- no organizational names in source code
  XCUT-02: Indigenous data sovereignty -- no third-party tracking
  XCUT-03: v1.2 fix verification -- logger naming, FY hardcoding, format_dollars

All tests use pathlib for file discovery (no subprocess/shell commands).
"""

import ast
import re
from pathlib import Path

import pytest

# Project root for file scanning
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
DOCS_WEB_DIR = PROJECT_ROOT / "docs" / "web"


def _collect_py_files(directory: Path) -> list[Path]:
    """Collect all .py files in directory recursively."""
    return sorted(directory.rglob("*.py"))


def _read_file_text(path: Path) -> str:
    """Read file content as UTF-8 text, returning empty string on error."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _collect_web_files() -> list[Path]:
    """Collect HTML, JS, and CSS files from docs/web/."""
    if not DOCS_WEB_DIR.exists():
        return []
    patterns = ["*.html", "*.js", "*.css"]
    files = []
    for pattern in patterns:
        files.extend(DOCS_WEB_DIR.rglob(pattern))
    return sorted(files)


# ===========================================================================
# XCUT-01: Air Gap Compliance
# ===========================================================================


class TestXCUT01AirGap:
    """Air gap compliance: no organizational names leak into source code.

    Source .py files in src/ must not contain organizational identifiers
    except in legitimate enforcement patterns (quality_review.py defines
    the air-gap violation list, doc_types.py references it in docstring).
    """

    # Files that legitimately reference org names for enforcement purposes
    EXEMPT_FILES = {
        "quality_review.py",  # Defines AIR_GAP_VIOLATIONS list
        "doc_types.py",       # Docstring reference to air gap enforcement
        "main.py",            # CLI description uses tool name (not in DOCX output)
        "generator.py",       # Internal report header (not DOCX/web output)
    }

    def _scan_src_py_for_pattern(
        self, pattern: str, case_insensitive: bool = False
    ) -> list[tuple[Path, int, str]]:
        """Scan src/ .py files for a pattern, returning violations.

        Skips exempt files and comment-only lines.

        Returns:
            List of (file_path, line_number, line_text) tuples.
        """
        flags = re.IGNORECASE if case_insensitive else 0
        regex = re.compile(pattern, flags)
        violations = []

        for py_file in _collect_py_files(SRC_DIR):
            if py_file.name in self.EXEMPT_FILES:
                continue

            text = _read_file_text(py_file)
            for i, line in enumerate(text.splitlines(), 1):
                stripped = line.strip()
                # Skip pure comments
                if stripped.startswith("#"):
                    continue
                # Skip docstring lines (heuristic: inside triple-quoted blocks)
                # We check for the pattern in actual code, not docs
                if regex.search(line):
                    violations.append((py_file, i, stripped))

        return violations

    def test_no_atni_in_src_code(self):
        """No 'ATNI' references in src/ Python code (excluding exempt files)."""
        violations = self._scan_src_py_for_pattern(r"\bATNI\b")
        assert not violations, (
            f"ATNI found in {len(violations)} location(s):\n"
            + "\n".join(
                f"  {v[0].relative_to(PROJECT_ROOT)}:{v[1]}: {v[2]}"
                for v in violations
            )
        )

    def test_no_ncai_in_src_code(self):
        """No 'NCAI' references in src/ Python code (excluding exempt files)."""
        violations = self._scan_src_py_for_pattern(r"\bNCAI\b")
        assert not violations, (
            f"NCAI found in {len(violations)} location(s):\n"
            + "\n".join(
                f"  {v[0].relative_to(PROJECT_ROOT)}:{v[1]}: {v[2]}"
                for v in violations
            )
        )

    def test_no_affiliated_tribes_in_src_code(self):
        """No 'Affiliated Tribes of Northwest Indians' in src/ code."""
        violations = self._scan_src_py_for_pattern(
            r"Affiliated Tribes of Northwest Indians", case_insensitive=True
        )
        assert not violations, (
            f"Organization name found in {len(violations)} location(s)"
        )

    def test_no_tcr_policy_scanner_in_src_code(self):
        """No 'TCR Policy Scanner' tool attribution in src/ code."""
        violations = self._scan_src_py_for_pattern(
            r"TCR Policy Scanner", case_insensitive=True
        )
        # Filter out docstring/comment references that describe the project
        real_violations = [
            v for v in violations
            if not v[2].startswith('"""') and not v[2].startswith("'''")
        ]
        assert not real_violations, (
            f"Tool name found in {len(real_violations)} location(s):\n"
            + "\n".join(
                f"  {v[0].relative_to(PROJECT_ROOT)}:{v[1]}: {v[2]}"
                for v in real_violations
            )
        )

    def test_no_atni_in_web_files(self):
        """No ATNI references in docs/web/ HTML/JS/CSS files."""
        regex = re.compile(r"\bATNI\b")
        violations = []
        for web_file in _collect_web_files():
            text = _read_file_text(web_file)
            for i, line in enumerate(text.splitlines(), 1):
                if regex.search(line):
                    violations.append((web_file, i, line.strip()))

        assert not violations, (
            f"ATNI found in web files:\n"
            + "\n".join(
                f"  {v[0].relative_to(PROJECT_ROOT)}:{v[1]}: {v[2][:80]}"
                for v in violations
            )
        )

    def test_no_ncai_in_web_files(self):
        """No NCAI references in docs/web/ HTML/JS/CSS files."""
        regex = re.compile(r"\bNCAI\b")
        violations = []
        for web_file in _collect_web_files():
            text = _read_file_text(web_file)
            for i, line in enumerate(text.splitlines(), 1):
                if regex.search(line):
                    violations.append((web_file, i, line.strip()))

        assert not violations, (
            f"NCAI found in web files:\n"
            + "\n".join(
                f"  {v[0].relative_to(PROJECT_ROOT)}:{v[1]}: {v[2][:80]}"
                for v in violations
            )
        )

    def test_no_generated_by_in_web_files(self):
        """No 'Generated by' attribution in web-facing files."""
        regex = re.compile(r"Generated by", re.IGNORECASE)
        violations = []
        for web_file in _collect_web_files():
            text = _read_file_text(web_file)
            for i, line in enumerate(text.splitlines(), 1):
                if regex.search(line):
                    violations.append((web_file, i, line.strip()))

        assert not violations, (
            f"'Generated by' attribution found in web files:\n"
            + "\n".join(
                f"  {v[0].relative_to(PROJECT_ROOT)}:{v[1]}: {v[2][:80]}"
                for v in violations
            )
        )

    def test_no_indigenous_access_in_src_code(self):
        """No 'IndigenousACCESS' tool name in src/ code."""
        violations = self._scan_src_py_for_pattern(
            r"IndigenousACCESS", case_insensitive=True
        )
        assert not violations, (
            f"IndigenousACCESS found in {len(violations)} location(s)"
        )


# ===========================================================================
# XCUT-02: Indigenous Data Sovereignty
# ===========================================================================


class TestXCUT02DataSovereignty:
    """Indigenous data sovereignty: no third-party tracking or analytics.

    Verifies that the web widget and source code do not include any
    external tracking scripts, analytics beacons, third-party fonts,
    or cookie-setting patterns.
    """

    def test_no_google_analytics_in_web(self):
        """No Google Analytics scripts in web files."""
        regex = re.compile(r"google-analytics|googleanalytics", re.IGNORECASE)
        violations = []
        for web_file in _collect_web_files():
            text = _read_file_text(web_file)
            if regex.search(text):
                violations.append(web_file)

        assert not violations, (
            f"Google Analytics found in: "
            f"{[str(v.relative_to(PROJECT_ROOT)) for v in violations]}"
        )

    def test_no_ga_function_calls_in_web(self):
        """No ga() function calls (Google Analytics) in web files."""
        regex = re.compile(r"\bga\s*\(")
        violations = []
        for web_file in _collect_web_files():
            text = _read_file_text(web_file)
            if regex.search(text):
                violations.append(web_file)

        assert not violations, (
            f"ga() calls found in: "
            f"{[str(v.relative_to(PROJECT_ROOT)) for v in violations]}"
        )

    def test_no_google_tag_manager_in_web(self):
        """No Google Tag Manager in web files."""
        regex = re.compile(r"googletagmanager", re.IGNORECASE)
        violations = []
        for web_file in _collect_web_files():
            text = _read_file_text(web_file)
            if regex.search(text):
                violations.append(web_file)

        assert not violations, (
            f"Google Tag Manager found in: "
            f"{[str(v.relative_to(PROJECT_ROOT)) for v in violations]}"
        )

    def test_no_google_fonts_cdn_in_web(self):
        """No Google Fonts CDN links in web files."""
        regex = re.compile(r"fonts\.googleapis\.com", re.IGNORECASE)
        violations = []
        for web_file in _collect_web_files():
            text = _read_file_text(web_file)
            if regex.search(text):
                violations.append(web_file)

        assert not violations, (
            f"Google Fonts CDN found in: "
            f"{[str(v.relative_to(PROJECT_ROOT)) for v in violations]}"
        )

    def test_no_cookie_setting_in_web(self):
        """No document.cookie usage in web files."""
        regex = re.compile(r"document\.cookie")
        violations = []
        for web_file in _collect_web_files():
            if web_file.suffix in (".js", ".html"):
                text = _read_file_text(web_file)
                if regex.search(text):
                    violations.append(web_file)

        assert not violations, (
            f"Cookie setting found in: "
            f"{[str(v.relative_to(PROJECT_ROOT)) for v in violations]}"
        )

    def test_no_pii_fields_in_data_models(self):
        """Data models in src/schemas/ do not contain PII field names."""
        pii_fields = [
            "social_security", "ssn", "date_of_birth", "dob",
            "email_address", "phone_number", "home_address",
            "password", "credit_card",
        ]
        regex = re.compile("|".join(pii_fields), re.IGNORECASE)

        schemas_dir = SRC_DIR / "schemas"
        if not schemas_dir.exists():
            return  # No schemas dir -> no violations

        violations = []
        for py_file in _collect_py_files(schemas_dir):
            text = _read_file_text(py_file)
            for i, line in enumerate(text.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if regex.search(line):
                    violations.append((py_file, i, stripped))

        assert not violations, (
            f"PII field patterns found in schemas:\n"
            + "\n".join(
                f"  {v[0].relative_to(PROJECT_ROOT)}:{v[1]}: {v[2]}"
                for v in violations
            )
        )


# ===========================================================================
# XCUT-03: v1.2 Fix Verification
# ===========================================================================


class TestXCUT03V12Fixes:
    """Verify v1.2 code quality fixes remain clean.

    Checks logger naming conventions, fiscal year handling,
    format_dollars centralization, and graph path resolution.
    """

    def test_logger_naming_uses_dunder_name(self):
        """All loggers in src/ use getLogger(__name__), not string literals.

        Scans for getLogger("...") patterns which indicate hardcoded
        logger names instead of the standard __name__ convention.
        """
        # Match getLogger("...") or getLogger('...')
        regex = re.compile(r'getLogger\s*\(\s*["\']')
        violations = []

        for py_file in _collect_py_files(SRC_DIR):
            text = _read_file_text(py_file)
            for i, line in enumerate(text.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if regex.search(line):
                    violations.append((py_file, i, stripped))

        assert not violations, (
            f"Hardcoded logger names found in {len(violations)} location(s):\n"
            + "\n".join(
                f"  {v[0].relative_to(PROJECT_ROOT)}:{v[1]}: {v[2]}"
                for v in violations
            )
        )

    def test_no_fy_hardcoding_in_congressional_intel(self):
        """Congressional intelligence code does not hardcode fiscal years.

        Scans Phase 15 files for string literals containing 'FY26' or
        'FY2026' which should use config.FISCAL_YEAR_SHORT instead.
        """
        # Match string literals containing FY26 or FY2026
        regex = re.compile(r"""(['"])[^'"]*(?:FY26|FY2026)[^'"]*\1""")

        phase15_files = [
            SRC_DIR / "packets" / "docx_sections.py",
            SRC_DIR / "packets" / "orchestrator.py",
            SRC_DIR / "packets" / "confidence.py",
            SRC_DIR / "packets" / "context.py",
        ]
        # Also check scripts
        scripts_dir = PROJECT_ROOT / "scripts"
        if scripts_dir.exists():
            build_intel = scripts_dir / "build_congressional_intel.py"
            if build_intel.exists():
                phase15_files.append(build_intel)

        violations = []
        for py_file in phase15_files:
            if not py_file.exists():
                continue
            text = _read_file_text(py_file)
            for i, line in enumerate(text.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    continue
                if regex.search(line):
                    violations.append((py_file, i, stripped))

        assert not violations, (
            f"FY hardcoding in Phase 15 files:\n"
            + "\n".join(
                f"  {v[0].relative_to(PROJECT_ROOT)}:{v[1]}: {v[2]}"
                for v in violations
            )
        )

    def test_format_dollars_single_definition(self):
        """format_dollars is defined exactly once in src/utils.py."""
        regex = re.compile(r"def\s+format_dollars\s*\(")
        definitions = []

        for py_file in _collect_py_files(SRC_DIR):
            text = _read_file_text(py_file)
            for i, line in enumerate(text.splitlines(), 1):
                if regex.search(line):
                    definitions.append((py_file, i))

        assert len(definitions) == 1, (
            f"Expected exactly 1 format_dollars definition, found {len(definitions)}:\n"
            + "\n".join(
                f"  {d[0].relative_to(PROJECT_ROOT)}:{d[1]}"
                for d in definitions
            )
        )
        # Verify it's in utils.py
        assert definitions[0][0].name == "utils.py", (
            f"format_dollars should be in utils.py, found in {definitions[0][0].name}"
        )

    def test_no_local_format_dollars_variants(self):
        """No _format_dollars or local dollar formatting functions exist."""
        regex = re.compile(r"def\s+_format_dollars\s*\(")
        violations = []

        for py_file in _collect_py_files(SRC_DIR):
            text = _read_file_text(py_file)
            for i, line in enumerate(text.splitlines(), 1):
                if regex.search(line):
                    violations.append((py_file, i, line.strip()))

        assert not violations, (
            f"Local _format_dollars variants found:\n"
            + "\n".join(
                f"  {v[0].relative_to(PROJECT_ROOT)}:{v[1]}: {v[2]}"
                for v in violations
            )
        )

    def test_no_hardcoded_graph_schema_paths(self):
        """No hardcoded file paths to graph_schema.json in src/ code.

        All references should use GRAPH_SCHEMA_PATH from src.paths.
        Excludes paths.py itself (where the constant is defined) and
        comments/docstrings.
        """
        # Match string literals containing "graph_schema.json" with path separators
        regex = re.compile(r"""(['"])[^'"]*[/\\]graph_schema\.json[^'"]*\1""")
        violations = []

        for py_file in _collect_py_files(SRC_DIR):
            if py_file.name == "paths.py":
                continue
            text = _read_file_text(py_file)
            for i, line in enumerate(text.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if regex.search(line):
                    violations.append((py_file, i, stripped))

        assert not violations, (
            f"Hardcoded graph_schema.json paths found:\n"
            + "\n".join(
                f"  {v[0].relative_to(PROJECT_ROOT)}:{v[1]}: {v[2]}"
                for v in violations
            )
        )

    def test_logger_naming_convention_consistent(self):
        """All modules with loggers use the standard pattern."""
        # Count modules that have logger = ... assignments
        logger_pattern = re.compile(r"^logger\s*=\s*logging\.getLogger\(")
        correct_pattern = re.compile(
            r"^logger\s*=\s*logging\.getLogger\(__name__\)"
        )

        incorrect = []
        for py_file in _collect_py_files(SRC_DIR):
            text = _read_file_text(py_file)
            for i, line in enumerate(text.splitlines(), 1):
                if logger_pattern.match(line):
                    if not correct_pattern.match(line):
                        incorrect.append((py_file, i, line.strip()))

        assert not incorrect, (
            f"Logger assignments not using __name__:\n"
            + "\n".join(
                f"  {v[0].relative_to(PROJECT_ROOT)}:{v[1]}: {v[2]}"
                for v in incorrect
            )
        )

    def test_encoding_utf8_on_open_calls(self):
        """Spot-check that new Phase 15 files use encoding='utf-8' on open().

        Scans congressional intel-related files for open() calls that
        are missing encoding parameter.
        """
        phase15_files = [
            SRC_DIR / "packets" / "orchestrator.py",
            SRC_DIR / "packets" / "confidence.py",
        ]
        build_intel = PROJECT_ROOT / "scripts" / "build_congressional_intel.py"
        if build_intel.exists():
            phase15_files.append(build_intel)

        # Match open(...) calls without encoding parameter
        open_pattern = re.compile(r'\bopen\s*\(')
        encoding_pattern = re.compile(r'encoding\s*=')

        violations = []
        for py_file in phase15_files:
            if not py_file.exists():
                continue
            text = _read_file_text(py_file)
            for i, line in enumerate(text.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if open_pattern.search(line) and not encoding_pattern.search(line):
                    # Skip lines that are clearly not file opens
                    # (e.g., "open_in_browser" function references)
                    if "open(" in line and "encoding" not in line:
                        # Only flag if it looks like a file open (has mode arg or path)
                        if any(
                            mode in line
                            for mode in ['"r"', "'r'", '"w"', "'w'", '"a"', "'a'"]
                        ):
                            violations.append((py_file, i, stripped))

        assert not violations, (
            f"open() calls missing encoding='utf-8':\n"
            + "\n".join(
                f"  {v[0].relative_to(PROJECT_ROOT)}:{v[1]}: {v[2]}"
                for v in violations
            )
        )

    def test_no_third_party_tracking_in_src(self):
        """No analytics or tracking SDK references in Python source."""
        tracking_patterns = [
            r"google.analytics",
            r"mixpanel",
            r"segment\.io",
            r"amplitude",
            r"hotjar",
        ]
        combined = re.compile("|".join(tracking_patterns), re.IGNORECASE)
        violations = []

        for py_file in _collect_py_files(SRC_DIR):
            text = _read_file_text(py_file)
            for i, line in enumerate(text.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if combined.search(line):
                    violations.append((py_file, i, stripped))

        assert not violations, (
            f"Third-party tracking found in src/:\n"
            + "\n".join(
                f"  {v[0].relative_to(PROJECT_ROOT)}:{v[1]}: {v[2]}"
                for v in violations
            )
        )
