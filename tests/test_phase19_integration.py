"""Phase 19 cross-plan integration tests for TCR Policy Scanner v1.4.

Verifies that all Phase 19 artifacts (schemas, builders, vocabulary, paths,
doc_types, context) work together correctly:

1. TestSchemaImports - All vulnerability models importable, no circular imports
2. TestSchemaToBuilderContract - Builder output validates against Pydantic models
3. TestTierMapping - Boundary score classification favors Tribal Nations
4. TestVocabularyIntegrity - Gap messages, tier displays, and framing compliance
5. TestDynamicFiscalYear - No hardcoded FY26 in src/packets/ Python files
6. TestPathConstants - Vulnerability path constants and helper functions
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# -- Test fixtures --
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_nri_dict():
    """Minimal valid NRI expanded profile dict."""
    return {
        "tribe_id": "epa_100000001",
        "risk_score": 25.5,
        "risk_percentile": 72.3,
        "eal_total": 150000.0,
        "eal_buildings": 80000.0,
        "eal_population": 40000.0,
        "eal_agriculture": 20000.0,
        "eal_population_equivalence": 10000.0,
        "community_resilience": 55.2,
        "social_vulnerability_nri": 62.1,
        "hazard_count": 3,
        "top_hazards": [
            {"type": "Riverine Flooding", "code": "RFLD", "eal_total": 80000.0},
            {"type": "Wildfire", "code": "WFIR", "eal_total": 50000.0},
        ],
        "coverage_pct": 0.85,
    }


@pytest.fixture()
def sample_svi_dict():
    """Minimal valid SVI profile dict."""
    from src.schemas.vulnerability import SVITheme

    themes = [
        SVITheme(
            theme_id="theme1",
            name="Socioeconomic Status",
            percentile=0.72,
            flag_count=3,
        ),
        SVITheme(
            theme_id="theme2",
            name="Household Characteristics & Disability",
            percentile=0.65,
            flag_count=2,
        ),
        SVITheme(
            theme_id="theme4",
            name="Housing Type & Transportation",
            percentile=0.58,
            flag_count=1,
        ),
    ]
    composite = round((0.72 + 0.65 + 0.58) / 3, 4)
    return {
        "tribe_id": "epa_100000001",
        "themes": themes,
        "composite": composite,
        "coverage_pct": 0.9,
        "source_year": 2022,
        "data_gaps": [],
    }


@pytest.fixture()
def sample_composite_dict():
    """Minimal valid composite score dict (score=0.55 -> ELEVATED)."""
    return {
        "score": 0.55,
        "tier": "ELEVATED",
        "data_completeness": 1.0,
        "components": [
            {
                "component": "hazard_exposure",
                "raw_score": 0.6,
                "base_weight": 0.40,
                "weight": 0.40,
                "weighted_score": 0.24,
                "available": True,
            },
            {
                "component": "social_vulnerability",
                "raw_score": 0.65,
                "base_weight": 0.35,
                "weight": 0.35,
                "weighted_score": 0.2275,
                "available": True,
            },
            {
                "component": "adaptive_capacity_deficit",
                "raw_score": 0.33,
                "base_weight": 0.25,
                "weight": 0.25,
                "weighted_score": 0.0825,
                "available": True,
            },
        ],
    }


# ---------------------------------------------------------------------------
# -- TestSchemaImports --
# ---------------------------------------------------------------------------


class TestSchemaImports:
    """All vulnerability models importable from expected locations."""

    def test_all_models_importable_from_vulnerability_module(self):
        """All 8 models importable from src.schemas.vulnerability."""
        from src.schemas.vulnerability import (
            CompositeComponent,
            CompositeScore,
            DataGapType,
            InvestmentPriorityTier,
            NRIExpanded,
            SVIProfile,
            SVITheme,
            VulnerabilityProfile,
        )

        # Verify they are actual types, not None
        assert CompositeComponent is not None
        assert CompositeScore is not None
        assert DataGapType is not None
        assert InvestmentPriorityTier is not None
        assert NRIExpanded is not None
        assert SVIProfile is not None
        assert SVITheme is not None
        assert VulnerabilityProfile is not None

    def test_models_reexported_from_schemas_package(self):
        """All vulnerability models re-exported from src.schemas."""
        from src.schemas import (
            CompositeComponent,
            CompositeScore,
            DataGapType,
            InvestmentPriorityTier,
            NRIExpanded,
            SVIProfile,
            SVITheme,
            VulnerabilityProfile,
        )

        # Verify they are the same objects as direct imports
        from src.schemas.vulnerability import (
            CompositeComponent as CC,
            CompositeScore as CS,
            DataGapType as DG,
            InvestmentPriorityTier as IPT,
            NRIExpanded as NE,
            SVIProfile as SP,
            SVITheme as ST,
            VulnerabilityProfile as VP,
        )

        assert CompositeComponent is CC
        assert CompositeScore is CS
        assert DataGapType is DG
        assert InvestmentPriorityTier is IPT
        assert NRIExpanded is NE
        assert SVIProfile is SP
        assert SVITheme is ST
        assert VulnerabilityProfile is VP

    def test_no_circular_imports(self):
        """Import schemas, vocabulary, nri_expanded, svi_builder in sequence without error."""
        # This test would raise ImportError on circular dependency
        import src.schemas.vulnerability  # noqa: F401
        import src.packets.vocabulary  # noqa: F401
        import src.packets.nri_expanded  # noqa: F401
        import src.packets.svi_builder  # noqa: F401

        # If we reach here, no circular import
        assert True


# ---------------------------------------------------------------------------
# -- TestSchemaToBuilderContract --
# ---------------------------------------------------------------------------


class TestSchemaToBuilderContract:
    """Builder output dicts validate against Pydantic models."""

    def test_nri_builder_output_validates(self, sample_nri_dict):
        """NRI builder output dict validates against NRIExpanded model."""
        from src.schemas.vulnerability import NRIExpanded

        profile = NRIExpanded(**sample_nri_dict)
        assert profile.tribe_id == "epa_100000001"
        assert profile.risk_score == 25.5
        assert profile.risk_percentile == 72.3
        assert profile.coverage_pct == 0.85
        assert len(profile.top_hazards) == 2

    def test_svi_builder_output_validates(self, sample_svi_dict):
        """SVI builder output dict validates against SVIProfile model."""
        from src.schemas.vulnerability import SVIProfile

        profile = SVIProfile(**sample_svi_dict)
        assert profile.tribe_id == "epa_100000001"
        assert len(profile.themes) == 3
        assert profile.source_year == 2022
        assert profile.data_gaps == []

    def test_composite_score_from_components_validates(self, sample_composite_dict):
        """Composite score from components validates against CompositeScore model."""
        from src.schemas.vulnerability import CompositeScore

        score = CompositeScore(**sample_composite_dict)
        assert score.score == 0.55
        assert score.tier == "ELEVATED"
        assert len(score.components) == 3

    def test_vulnerability_profile_assembles_with_subprofiles(
        self, sample_nri_dict, sample_svi_dict, sample_composite_dict
    ):
        """VulnerabilityProfile assembles with NRI + SVI + Composite sub-profiles."""
        from src.schemas.vulnerability import (
            CompositeScore,
            NRIExpanded,
            SVIProfile,
            VulnerabilityProfile,
        )

        nri = NRIExpanded(**sample_nri_dict)
        svi = SVIProfile(**sample_svi_dict)
        composite = CompositeScore(**sample_composite_dict)

        profile = VulnerabilityProfile(
            tribe_id="epa_100000001",
            tribe_name="Test Tribal Nation",
            nri=nri,
            svi=svi,
            composite=composite,
            is_coastal=False,
            data_gaps=[],
            generated_at="2026-02-17T12:00:00+00:00",
            nri_version="1.20",
            svi_version="2022",
        )

        assert profile.tribe_id == "epa_100000001"
        assert profile.nri is not None
        assert profile.svi is not None
        assert profile.composite is not None
        assert profile.nri.risk_score == 25.5
        assert profile.svi.composite == sample_svi_dict["composite"]
        assert profile.composite.tier == "ELEVATED"

    def test_vulnerability_profile_optional_subprofiles(self):
        """VulnerabilityProfile works with None subprofiles (incremental population)."""
        from src.schemas.vulnerability import VulnerabilityProfile

        profile = VulnerabilityProfile(
            tribe_id="epa_100000001",
            tribe_name="Test Tribal Nation",
            nri=None,
            svi=None,
            composite=None,
            generated_at="2026-02-17T12:00:00+00:00",
            nri_version="1.20",
            svi_version="2022",
        )

        assert profile.nri is None
        assert profile.svi is None
        assert profile.composite is None


# ---------------------------------------------------------------------------
# -- TestTierMapping --
# ---------------------------------------------------------------------------


class TestTierMapping:
    """Investment priority tier boundary classification tests."""

    @pytest.mark.parametrize(
        "score, expected_tier",
        [
            (0.00, "LOW"),
            (0.19, "LOW"),
            (0.20, "MODERATE"),
            (0.39, "MODERATE"),
            (0.40, "ELEVATED"),
            (0.59, "ELEVATED"),
            (0.60, "HIGH"),
            (0.79, "HIGH"),
            (0.80, "CRITICAL"),
            (1.00, "CRITICAL"),
        ],
    )
    def test_boundary_scores(self, score, expected_tier):
        """Boundary score maps to expected tier."""
        from src.schemas.vulnerability import InvestmentPriorityTier

        tier = InvestmentPriorityTier.from_score(score)
        assert tier.value == expected_tier, (
            f"Score {score} should be {expected_tier}, got {tier.value}"
        )

    def test_boundary_favors_tribe_at_080(self):
        """Score 0.80 classifies as CRITICAL (>=), not HIGH.

        Boundary rule: >= 0.80 is CRITICAL. This favors Tribal Nations by
        ensuring borderline scores receive the higher priority classification,
        supporting stronger advocacy positioning.
        """
        from src.schemas.vulnerability import InvestmentPriorityTier

        tier = InvestmentPriorityTier.from_score(0.80)
        assert tier == InvestmentPriorityTier.CRITICAL
        assert tier.value != "HIGH"

    def test_all_five_tiers_reachable(self):
        """All five tiers are reachable via from_score()."""
        from src.schemas.vulnerability import InvestmentPriorityTier

        tiers_reached = set()
        for score in [0.0, 0.2, 0.4, 0.6, 0.8]:
            tiers_reached.add(InvestmentPriorityTier.from_score(score).value)

        expected = {"LOW", "MODERATE", "ELEVATED", "HIGH", "CRITICAL"}
        assert tiers_reached == expected


# ---------------------------------------------------------------------------
# -- TestVocabularyIntegrity --
# ---------------------------------------------------------------------------


class TestVocabularyIntegrity:
    """Vocabulary constants aligned with schema enums and framing requirements."""

    def test_gap_messages_keys_match_enum(self):
        """GAP_MESSAGES keys match DataGapType enum values exactly."""
        from src.packets.vocabulary import GAP_MESSAGES
        from src.schemas.vulnerability import DataGapType

        enum_values = {member.value for member in DataGapType}
        message_keys = set(GAP_MESSAGES.keys())
        assert message_keys == enum_values, (
            f"GAP_MESSAGES keys mismatch:\n"
            f"  In enum, missing from messages: {enum_values - message_keys}\n"
            f"  In messages, missing from enum: {message_keys - enum_values}"
        )

    def test_tier_displays_keys_match_tier_values(self):
        """TIER_DISPLAYS keys match InvestmentPriorityTier values (title-cased)."""
        from src.packets.vocabulary import TIER_DISPLAYS
        from src.schemas.vulnerability import InvestmentPriorityTier

        # Tier enum values are uppercase (CRITICAL, HIGH, etc.)
        # TIER_DISPLAYS keys are title-case (Critical, High, etc.)
        tier_values = {member.value.title() for member in InvestmentPriorityTier}
        display_keys = set(TIER_DISPLAYS.keys())
        assert display_keys == tier_values, (
            f"TIER_DISPLAYS keys mismatch:\n"
            f"  Expected (from enum): {tier_values}\n"
            f"  Actual (display keys): {display_keys}"
        )

    def test_section_headings_no_raw_vulnerability(self):
        """Section headings contain no raw 'vulnerability' (case-insensitive).

        Per DEC-05: headings use 'Climate Resilience Investment' framing.
        'vulnerability' is only allowed inside federal proper noun contexts.
        """
        from src.packets.vocabulary import SECTION_HEADINGS

        headings = [
            SECTION_HEADINGS.doc_a_main,
            SECTION_HEADINGS.doc_b_main,
            SECTION_HEADINGS.doc_c_main,
            SECTION_HEADINGS.doc_d_main,
            SECTION_HEADINGS.doc_e_main,
        ]
        for heading in headings:
            assert "vulnerability" not in heading.lower(), (
                f"Heading contains forbidden 'vulnerability': {heading}"
            )

    def test_no_forbidden_doc_b_terms_in_congressional_headings(self):
        """Doc B/D headings contain no FORBIDDEN_DOC_B_TERMS.

        Only congressional-facing section headings (doc_b_main, doc_d_main) are
        checked. Internal headings (doc_a_main, doc_c_main, doc_e_main) may
        intentionally use strategy terms like 'investment profile' since they
        target internal audiences. EXPOSURE_CONTEXT and RATING_LABEL are
        similarly used in internal docs and are not checked here.
        """
        from src.packets.vocabulary import (
            FORBIDDEN_DOC_B_TERMS,
            SECTION_HEADINGS,
        )

        # Only check congressional-audience headings (Doc B, Doc D)
        texts_to_check = {
            "SECTION_HEADINGS.doc_b_main": SECTION_HEADINGS.doc_b_main,
            "SECTION_HEADINGS.doc_d_main": SECTION_HEADINGS.doc_d_main,
        }

        violations = []
        for label, text in texts_to_check.items():
            text_lower = text.lower()
            for term in FORBIDDEN_DOC_B_TERMS:
                if term.lower() in text_lower:
                    violations.append(f"{label} contains forbidden term '{term}'")

        assert not violations, (
            f"Congressional headings contain Doc B forbidden terms:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )


# ---------------------------------------------------------------------------
# -- TestDynamicFiscalYear --
# ---------------------------------------------------------------------------


class TestDynamicFiscalYear:
    """Dynamic fiscal year compliance -- no hardcoded FY26."""

    def test_doc_a_title_uses_fiscal_year_short(self):
        """DOC_A title_template contains FISCAL_YEAR_SHORT, not literal 'FY26'."""
        from src.config import FISCAL_YEAR_SHORT
        from src.packets.doc_types import DOC_A

        assert FISCAL_YEAR_SHORT in DOC_A.title_template, (
            f"DOC_A title_template should contain '{FISCAL_YEAR_SHORT}', "
            f"got: {DOC_A.title_template}"
        )

    def test_doc_b_title_uses_fiscal_year_short(self):
        """DOC_B title_template contains FISCAL_YEAR_SHORT."""
        from src.config import FISCAL_YEAR_SHORT
        from src.packets.doc_types import DOC_B

        assert FISCAL_YEAR_SHORT in DOC_B.title_template

    def test_doc_c_title_uses_fiscal_year_short(self):
        """DOC_C title_template contains FISCAL_YEAR_SHORT."""
        from src.config import FISCAL_YEAR_SHORT
        from src.packets.doc_types import DOC_C

        assert FISCAL_YEAR_SHORT in DOC_C.title_template

    def test_doc_d_title_uses_fiscal_year_short(self):
        """DOC_D title_template contains FISCAL_YEAR_SHORT."""
        from src.config import FISCAL_YEAR_SHORT
        from src.packets.doc_types import DOC_D

        assert FISCAL_YEAR_SHORT in DOC_D.title_template

    def test_format_filename_uses_fiscal_year_short(self):
        """format_filename() uses FISCAL_YEAR_SHORT.lower() in output."""
        from src.config import FISCAL_YEAR_SHORT
        from src.packets.doc_types import DOC_A

        filename = DOC_A.format_filename("test_tribe")
        assert FISCAL_YEAR_SHORT.lower() in filename, (
            f"format_filename should contain '{FISCAL_YEAR_SHORT.lower()}', "
            f"got: {filename}"
        )

    def test_no_hardcoded_fy26_in_packets_source(self):
        """No 'FY26' literal in src/packets/ Python files (regression guard).

        Scans all .py files under src/packets/ for the string 'FY26'.
        The only allowed exception is iija_sunset.py which is in src/monitors/
        (not in src/packets/), so no exclusions needed here.
        """
        from src.paths import PROJECT_ROOT

        packets_dir = PROJECT_ROOT / "src" / "packets"
        violations = []

        for py_file in sorted(packets_dir.glob("*.py")):
            source = py_file.read_text(encoding="utf-8")
            for lineno, line in enumerate(source.splitlines(), start=1):
                # Skip comments that document the FY26 fix itself
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if "FY26" in line:
                    violations.append(f"{py_file.name}:{lineno}: {stripped}")

        assert not violations, (
            f"Hardcoded 'FY26' found in src/packets/ Python files:\n"
            + "\n".join(f"  {v}" for v in violations)
        )


# ---------------------------------------------------------------------------
# -- TestPathConstants --
# ---------------------------------------------------------------------------


class TestPathConstants:
    """Vulnerability path constants under DATA_DIR."""

    def test_svi_dir_under_data(self):
        """SVI_DIR is under DATA_DIR."""
        from src.paths import DATA_DIR, SVI_DIR

        assert SVI_DIR.parent == DATA_DIR

    def test_svi_county_path_under_svi_dir(self):
        """SVI_COUNTY_PATH is under SVI_DIR."""
        from src.paths import SVI_COUNTY_PATH, SVI_DIR

        assert SVI_COUNTY_PATH.parent == SVI_DIR

    def test_climate_dir_under_data(self):
        """CLIMATE_DIR is under DATA_DIR."""
        from src.paths import CLIMATE_DIR, DATA_DIR

        assert CLIMATE_DIR.parent == DATA_DIR

    def test_climate_summary_under_climate_dir(self):
        """CLIMATE_SUMMARY_PATH is under CLIMATE_DIR."""
        from src.paths import CLIMATE_DIR, CLIMATE_SUMMARY_PATH

        assert CLIMATE_SUMMARY_PATH.parent == CLIMATE_DIR

    def test_vulnerability_profiles_dir_under_data(self):
        """VULNERABILITY_PROFILES_DIR is under DATA_DIR."""
        from src.paths import DATA_DIR, VULNERABILITY_PROFILES_DIR

        assert VULNERABILITY_PROFILES_DIR.parent == DATA_DIR

    def test_climate_raw_dir_under_climate_dir(self):
        """CLIMATE_RAW_DIR is under CLIMATE_DIR."""
        from src.paths import CLIMATE_DIR, CLIMATE_RAW_DIR

        assert CLIMATE_RAW_DIR.parent == CLIMATE_DIR

    def test_all_six_vulnerability_paths_exist_as_constants(self):
        """All 6 new vulnerability paths are importable."""
        from src.paths import (
            CLIMATE_DIR,
            CLIMATE_RAW_DIR,
            CLIMATE_SUMMARY_PATH,
            SVI_COUNTY_PATH,
            SVI_DIR,
            VULNERABILITY_PROFILES_DIR,
        )

        paths = [
            SVI_DIR,
            SVI_COUNTY_PATH,
            CLIMATE_DIR,
            CLIMATE_SUMMARY_PATH,
            VULNERABILITY_PROFILES_DIR,
            CLIMATE_RAW_DIR,
        ]
        for p in paths:
            assert isinstance(p, Path), f"Expected Path, got {type(p)}: {p}"

    def test_vulnerability_profile_path_helper(self):
        """vulnerability_profile_path() returns expected path."""
        from src.paths import VULNERABILITY_PROFILES_DIR, vulnerability_profile_path

        result = vulnerability_profile_path("epa_100000001")
        expected = VULNERABILITY_PROFILES_DIR / "epa_100000001.json"
        assert result == expected

    def test_tribe_packet_context_default_vulnerability_profile(self):
        """TribePacketContext().vulnerability_profile defaults to empty dict."""
        from src.packets.context import TribePacketContext

        ctx = TribePacketContext(tribe_id="epa_100000001", tribe_name="Test")
        assert ctx.vulnerability_profile == {}
        assert isinstance(ctx.vulnerability_profile, dict)

    def test_paths_module_no_existence_checks_at_import(self):
        """src/paths.py does not call .exists() or .mkdir() at import time.

        Path constants module must be pure constants with no side effects.
        """
        from src.paths import PROJECT_ROOT

        paths_file = PROJECT_ROOT / "src" / "paths.py"
        source = paths_file.read_text(encoding="utf-8")
        tree = ast.parse(source)

        # Walk AST looking for method calls to .exists() or .mkdir()
        violations = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute):
                    if func.attr in ("exists", "mkdir"):
                        # Check if it's at module level (not inside a function)
                        # Since ast.walk doesn't give parent context easily,
                        # we check by line: if it's outside def/class bodies
                        violations.append(
                            f"Line {node.lineno}: .{func.attr}() call found"
                        )

        # Filter: only flag module-level calls (outside function defs)
        # Parse to find all function definition line ranges
        func_ranges = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_ranges.append((node.lineno, node.end_lineno or node.lineno))

        module_level_violations = []
        for v in violations:
            lineno = int(v.split(":")[0].replace("Line ", ""))
            in_func = any(start <= lineno <= end for start, end in func_ranges)
            if not in_func:
                module_level_violations.append(v)

        assert not module_level_violations, (
            f"src/paths.py has module-level side effects:\n"
            + "\n".join(f"  {v}" for v in module_level_violations)
        )
