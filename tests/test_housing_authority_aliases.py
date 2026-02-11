"""Tests for housing authority alias loading, merging, and matching.

Covers:
  - housing_authority_aliases.json file validity and structure
  - All tribe_ids in HA aliases exist in tribal_registry.json
  - Known housing authority mappings are present
  - Regional/multi-Tribe housing authorities are excluded
  - Main alias table includes housing authority entries after rebuild
  - TribalAwardMatcher resolves housing authority names to parent Tribes
"""

import json

import pytest

from src.packets.awards import TribalAwardMatcher
from src.paths import TRIBAL_ALIASES_PATH, TRIBAL_REGISTRY_PATH

# Path to the housing authority aliases file
_HA_ALIASES_PATH = TRIBAL_REGISTRY_PATH.parent / "housing_authority_aliases.json"


# -- Fixtures --


@pytest.fixture(scope="module")
def ha_data():
    """Load housing authority aliases data."""
    with open(_HA_ALIASES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def ha_aliases(ha_data):
    """Get the aliases dict from HA data."""
    return ha_data.get("aliases", {})


@pytest.fixture(scope="module")
def registry_tribe_ids():
    """Get all valid tribe_ids from the registry."""
    with open(TRIBAL_REGISTRY_PATH, "r", encoding="utf-8") as f:
        registry = json.load(f)
    return {t["tribe_id"] for t in registry.get("tribes", [])}


@pytest.fixture(scope="module")
def alias_table():
    """Load the main tribal aliases table."""
    with open(TRIBAL_ALIASES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# -- File validity --


class TestHousingAuthorityAliasesFile:
    """Test housing_authority_aliases.json file structure and validity."""

    def test_file_exists(self):
        assert _HA_ALIASES_PATH.exists()

    def test_valid_json(self, ha_data):
        assert isinstance(ha_data, dict)
        assert "aliases" in ha_data
        assert isinstance(ha_data["aliases"], dict)

    def test_has_metadata(self, ha_data):
        assert "_metadata" in ha_data
        meta = ha_data["_metadata"]
        assert "version" in meta
        assert "last_updated" in meta
        assert "total_aliases" in meta

    def test_minimum_alias_count(self, ha_aliases):
        assert len(ha_aliases) >= 15


# -- Tribe ID validation --


class TestHousingAuthorityTribeIds:
    """Test that all tribe_ids in HA aliases exist in tribal_registry.json."""

    def test_all_tribe_ids_valid(self, ha_aliases, registry_tribe_ids):
        invalid = []
        for key, tribe_id in ha_aliases.items():
            if tribe_id not in registry_tribe_ids:
                invalid.append((key, tribe_id))
        assert not invalid, (
            f"Found {len(invalid)} HA aliases with invalid tribe_ids: "
            f"{invalid[:5]}"
        )


# -- Known housing authority mappings --


class TestKnownHousingAuthorities:
    """Verify specific known mappings are present."""

    @pytest.mark.parametrize(
        "ha_name,expected_tribe_id",
        [
            ("crow tribe of indians", "epa_100000069"),
            ("united keetoowah band of cherokee", "epa_100000315"),
            ("orutsararmuit native council, incorporated", "epa_100000496"),
            ("tule river indian housing auth", "epa_100000307"),
            ("sac & fox housing authority inc", "epa_100000248"),
            ("navajo nation housing authority", "epa_100000171"),
            ("hopi tribe housing authority", "epa_100000104"),
            ("standing rock sioux tribe housing authority", "epa_100000289"),
            ("turtle mountain band housing authority", "epa_100000311"),
            ("blackfeet tribe housing authority", "epa_100000020"),
        ],
    )
    def test_known_mapping(self, ha_aliases, ha_name, expected_tribe_id):
        found_id = ha_aliases.get(ha_name)
        assert found_id == expected_tribe_id, (
            f"Expected {ha_name!r} -> {expected_tribe_id}, "
            f"got {found_id!r}"
        )


# -- Regional authorities excluded --


class TestRegionalAuthoritiesExcluded:
    """Verify regional/multi-Tribe housing authorities are NOT in aliases."""

    @pytest.mark.parametrize(
        "regional_name",
        [
            "interior regional housing authority",
            "bering straits regional housing authority",
            "cook inlet housing authority",
            "bristol bay housing authority",
            "all mission indian housing authority",
            "new york state thruway authority",
        ],
    )
    def test_regional_excluded(self, ha_aliases, regional_name):
        assert regional_name not in ha_aliases


# -- Alias table integration --


class TestAliasTableIncludesHA:
    """Test that the main tribal_aliases.json contains HA entries after rebuild."""

    def test_alias_table_has_ha_entries(self, alias_table):
        aliases = alias_table.get("aliases", {})
        ha_count = sum(1 for k in aliases if "housing" in k)
        assert ha_count >= 100

    def test_alias_table_count_increased(self, alias_table):
        total = alias_table.get("_metadata", {}).get("total_aliases", 0)
        assert total > 3751


# -- Matcher integration --


def _make_matcher(tmp_path, tribes, aliases=None):
    """Create a TribalAwardMatcher with temp files."""
    registry_path = tmp_path / "tribal_registry.json"
    registry_path.write_text(
        json.dumps({"tribes": tribes, "metadata": {"placeholder": False}}),
        encoding="utf-8",
    )
    alias_path = tmp_path / "tribal_aliases.json"
    alias_path.write_text(
        json.dumps({"aliases": aliases or {}}),
        encoding="utf-8",
    )
    cache_dir = tmp_path / "award_cache"
    config = {
        "packets": {
            "tribal_registry": {"data_path": str(registry_path)},
            "awards": {
                "alias_path": str(alias_path),
                "cache_dir": str(cache_dir),
            },
        },
    }
    return TribalAwardMatcher(config)


class TestMatcherResolvesHA:
    """Test that TribalAwardMatcher resolves housing authority names."""

    def test_navajo_housing_authority(self, tmp_path):
        tribes = [
            {
                "tribe_id": "epa_100000171",
                "name": "Navajo Nation",
                "states": ["AZ", "NM", "UT"],
                "alternate_names": [],
            },
        ]
        aliases = {"navajo housing authority": "epa_100000171"}
        matcher = _make_matcher(tmp_path, tribes, aliases)
        result = matcher.match_recipient_to_tribe("NAVAJO HOUSING AUTHORITY")
        assert result is not None
        assert result["tribe_id"] == "epa_100000171"

    def test_crow_tribe_of_indians(self, tmp_path):
        tribes = [
            {
                "tribe_id": "epa_100000069",
                "name": "Crow Tribe of Montana",
                "states": ["MT"],
                "alternate_names": [],
            },
        ]
        aliases = {"crow tribe of indians": "epa_100000069"}
        matcher = _make_matcher(tmp_path, tribes, aliases)
        result = matcher.match_recipient_to_tribe("CROW TRIBE OF INDIANS")
        assert result is not None
        assert result["tribe_id"] == "epa_100000069"

    def test_truncated_auth_name(self, tmp_path):
        tribes = [
            {
                "tribe_id": "epa_100000307",
                "name": "Tule River Indian Tribe",
                "states": ["CA"],
                "alternate_names": [],
            },
        ]
        aliases = {"tule river indian housing auth": "epa_100000307"}
        matcher = _make_matcher(tmp_path, tribes, aliases)
        result = matcher.match_recipient_to_tribe(
            "TULE RIVER INDIAN HOUSING AUTH",
        )
        assert result is not None
        assert result["tribe_id"] == "epa_100000307"
