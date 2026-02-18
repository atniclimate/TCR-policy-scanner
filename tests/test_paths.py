"""Tests for centralized path constants and helper functions.

Verifies all path constants are importable, have correct types,
point to expected locations, and that helper functions return
properly constructed per-Tribe paths.
"""

from pathlib import Path

import pytest


class TestVulnerabilityPathConstants:
    """Verify the 6 new vulnerability data path constants."""

    def test_svi_dir_importable_and_is_path(self):
        """SVI_DIR is importable and is a Path instance."""
        from src.paths import SVI_DIR
        assert isinstance(SVI_DIR, Path)

    def test_svi_dir_under_data(self):
        """SVI_DIR is a subdirectory of DATA_DIR."""
        from src.paths import DATA_DIR, SVI_DIR
        assert SVI_DIR.parent == DATA_DIR
        assert SVI_DIR.name == "svi"

    def test_svi_county_path_importable_and_is_path(self):
        """SVI_COUNTY_PATH is importable and is a Path instance."""
        from src.paths import SVI_COUNTY_PATH
        assert isinstance(SVI_COUNTY_PATH, Path)

    def test_svi_county_path_under_svi_dir(self):
        """SVI_COUNTY_PATH is under SVI_DIR with correct filename."""
        from src.paths import SVI_COUNTY_PATH, SVI_DIR
        assert SVI_COUNTY_PATH.parent == SVI_DIR
        assert SVI_COUNTY_PATH.name == "SVI2022_US_COUNTY.csv"

    def test_climate_dir_importable_and_is_path(self):
        """CLIMATE_DIR is importable and is a Path instance."""
        from src.paths import CLIMATE_DIR
        assert isinstance(CLIMATE_DIR, Path)

    def test_climate_dir_under_data(self):
        """CLIMATE_DIR is a subdirectory of DATA_DIR."""
        from src.paths import CLIMATE_DIR, DATA_DIR
        assert CLIMATE_DIR.parent == DATA_DIR
        assert CLIMATE_DIR.name == "climate"

    def test_climate_summary_path_importable_and_is_path(self):
        """CLIMATE_SUMMARY_PATH is importable and is a Path instance."""
        from src.paths import CLIMATE_SUMMARY_PATH
        assert isinstance(CLIMATE_SUMMARY_PATH, Path)

    def test_climate_summary_path_under_climate_dir(self):
        """CLIMATE_SUMMARY_PATH is under CLIMATE_DIR with correct filename."""
        from src.paths import CLIMATE_DIR, CLIMATE_SUMMARY_PATH
        assert CLIMATE_SUMMARY_PATH.parent == CLIMATE_DIR
        assert CLIMATE_SUMMARY_PATH.name == "climate_summary.json"

    def test_vulnerability_profiles_dir_importable_and_is_path(self):
        """VULNERABILITY_PROFILES_DIR is importable and is a Path instance."""
        from src.paths import VULNERABILITY_PROFILES_DIR
        assert isinstance(VULNERABILITY_PROFILES_DIR, Path)

    def test_vulnerability_profiles_dir_under_data(self):
        """VULNERABILITY_PROFILES_DIR is a subdirectory of DATA_DIR."""
        from src.paths import DATA_DIR, VULNERABILITY_PROFILES_DIR
        assert VULNERABILITY_PROFILES_DIR.parent == DATA_DIR
        assert VULNERABILITY_PROFILES_DIR.name == "vulnerability_profiles"

    def test_climate_raw_dir_importable_and_is_path(self):
        """CLIMATE_RAW_DIR is importable and is a Path instance."""
        from src.paths import CLIMATE_RAW_DIR
        assert isinstance(CLIMATE_RAW_DIR, Path)

    def test_climate_raw_dir_under_climate_dir(self):
        """CLIMATE_RAW_DIR is under CLIMATE_DIR."""
        from src.paths import CLIMATE_DIR, CLIMATE_RAW_DIR
        assert CLIMATE_RAW_DIR.parent == CLIMATE_DIR
        assert CLIMATE_RAW_DIR.name == "raw"


class TestVulnerabilityProfilePathHelper:
    """Verify vulnerability_profile_path() helper function."""

    def test_helper_importable(self):
        """vulnerability_profile_path is importable from src.paths."""
        from src.paths import vulnerability_profile_path
        assert callable(vulnerability_profile_path)

    def test_returns_path_instance(self):
        """Helper returns a Path instance."""
        from src.paths import vulnerability_profile_path
        result = vulnerability_profile_path("epa_100000001")
        assert isinstance(result, Path)

    def test_correct_directory(self):
        """Helper returns path under VULNERABILITY_PROFILES_DIR."""
        from src.paths import VULNERABILITY_PROFILES_DIR, vulnerability_profile_path
        result = vulnerability_profile_path("epa_100000001")
        assert result.parent == VULNERABILITY_PROFILES_DIR

    def test_correct_filename(self):
        """Helper constructs filename from tribe_id + .json."""
        from src.paths import vulnerability_profile_path
        result = vulnerability_profile_path("epa_100000342")
        assert result.name == "epa_100000342.json"

    def test_different_tribe_ids(self):
        """Helper returns unique paths for different tribe_ids."""
        from src.paths import vulnerability_profile_path
        path_a = vulnerability_profile_path("epa_100000001")
        path_b = vulnerability_profile_path("epa_100000002")
        assert path_a != path_b


class TestNoCircularImports:
    """Verify that importing path constants does not trigger circular imports."""

    def test_import_all_vulnerability_constants(self):
        """All 6 new constants importable in a single statement."""
        from src.paths import (
            CLIMATE_DIR,
            CLIMATE_RAW_DIR,
            CLIMATE_SUMMARY_PATH,
            SVI_COUNTY_PATH,
            SVI_DIR,
            VULNERABILITY_PROFILES_DIR,
        )
        # All should be Path instances
        for const in [SVI_DIR, SVI_COUNTY_PATH, CLIMATE_DIR,
                      CLIMATE_SUMMARY_PATH, VULNERABILITY_PROFILES_DIR,
                      CLIMATE_RAW_DIR]:
            assert isinstance(const, Path)

    def test_import_helper_with_constants(self):
        """Helper and constants importable together without circular issues."""
        from src.paths import (
            VULNERABILITY_PROFILES_DIR,
            vulnerability_profile_path,
        )
        result = vulnerability_profile_path("epa_test")
        assert result.parent == VULNERABILITY_PROFILES_DIR
