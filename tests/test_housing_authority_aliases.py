"""Tests for housing authority alias mapping and integration.

Covers:
  - Housing authority alias file validity
  - Tribe ID validation against registry
  - Known housing authority mappings
  - Regional authority exclusion
  - Integration with main alias table
  - TribalAwardMatcher resolution of housing authority names
"""

import json
from pathlib import Path

import pytest

from src.packets.awards import TribalAwardMatcher

# Paths to data files
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_HA_ALIASES_PATH = _DATA_DIR / "housing_authority_aliases.json"
_TRIBAL_ALIASES_PATH = _DATA_DIR / "tribal_aliases.json"
_REGISTRY_PATH = _DATA_DIR / "tribal_registry.json"


# ── Fixtures ──


def _load_ha_aliases() -> dict:
    """Load the housing authority aliases file."""
    with open(_HA_ALIASES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_tribal_aliases() -> dict:
    """Load the main tribal aliases file."""
    with open(_TRIBAL_ALIASES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_registry() -> dict:
    """Load the tribal registry."""
    with open(_REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _build_registry_file(tmp_path, tribes):
    """Write a minimal tribal_registry.json for testing."""
    registry_path = tmp_path / "tribal_registry.json"
    registry_path.write_text(
        json.dumps({"tribes": tribes, "metadata": {"placeholder": False}}),
        encoding="utf-8",
    )
    return registry_path


def _build_alias_file(tmp_path, aliases=None):
    """Write a minimal tribal_aliases.json for testing."""
    alias_path = tmp_path / "tribal_aliases.json"
    alias_path.write_text(
        json.dumps({"aliases": aliases or {}}),
        encoding="utf-8",
    )
    return alias_path


def _make_matcher(tmp_path, tribes, aliases=None):
    """Create a TribalAwardMatcher with temp files and custom cache dir."""
    registry_path = _build_registry_file(tmp_path, tribes)
    alias_path = _build_alias_file(tmp_path, aliases or {})
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


# ── Housing authority alias file validity ──


class TestHousingAuthorityAliasesFileValidity:
    """Test that the housing authority aliases file is valid and well-structured."""

    def test_housing_authority_aliases_file_valid_json(self):
        """File exists, is valid JSON, and has an aliases dict."""
        assert _HA_ALIASES_PATH.exists(), (
            f"Housing authority aliases file not found: {_HA_ALIASES_PATH}"
        )
        data = _load_ha_aliases()
        assert isinstance(data, dict)
        assert "aliases" in data
        assert isinstance(data["aliases"], dict)
        assert len(data["aliases"]) > 0

    def test_housing_authority_aliases_have_metadata(self):
        """File has _metadata section with expected keys."""
        data = _load_ha_aliases()
        assert "_metadata" in data
        metadata = data["_metadata"]
        assert "description" in metadata
        assert "version" in metadata
        assert "last_updated" in metadata

    def test_housing_authority_aliases_all_lowercase(self):
        """All alias keys should be lowercase."""
        data = _load_ha_aliases()
        for key in data["aliases"]:
            assert key == key.lower(), f"Alias key not lowercase: {key}"


# ── Tribe ID validation ──


class TestHousingAuthorityTribeIds:
    """Test that all tribe_ids in the HA aliases exist in the registry."""

    def test_housing_authority_aliases_have_valid_tribe_ids(self):
        """Every tribe_id in the HA aliases exists in tribal_registry.json."""
        ha_data = _load_ha_aliases()
        registry = _load_registry()
        valid_ids = {t["tribe_id"] for t in registry["tribes"]}

        invalid = []
        for alias_name, tribe_id in ha_data["aliases"].items():
            if tribe_id not in valid_ids:
                invalid.append((alias_name, tribe_id))

        assert not invalid, (
            f"Found {len(invalid)} aliases with invalid tribe_ids: "
            f"{invalid[:5]}..."
        )


# ── Known housing authority mappings ──


class TestKnownHousingAuthoritiesMapped:
    """Test that specific known housing authority names are mapped correctly."""

    @pytest.mark.parametrize(
        "alias_name,expected_tribe_id",
        [
            ("navajo housing authority", "epa_100000171"),
            ("housing authority of choctaw nations", "epa_100000045"),
            ("oglala lakota housing authority", "epa_100000179"),
            ("tohono o'odham ki ki association", "epa_100000302"),
            ("white mountain apache housing authority", "epa_100000324"),
            ("hopi tribal housing authority", "epa_100000104"),
            ("turtle mountain housing authority", "epa_100000311"),
            ("sicangu wicoti awayankape corporation", "epa_100000244"),
            ("blackfeet housing program", "epa_100000020"),
            ("san carlos housing authority", "epa_100000254"),
            ("yakama nation housing authority", "epa_100000062"),
            ("cheyenne river housing authority", "epa_100000040"),
            ("standing rock housing local development", "epa_100000289"),
        ],
    )
    def test_known_housing_authorities_mapped(self, alias_name, expected_tribe_id):
        """Verify specific known housing authority -> tribe_id mappings."""
        data = _load_ha_aliases()
        aliases = data["aliases"]
        assert alias_name in aliases, (
            f"Known housing authority alias not found: {alias_name}"
        )
        assert aliases[alias_name] == expected_tribe_id, (
            f"Wrong tribe_id for {alias_name}: "
            f"expected {expected_tribe_id}, got {aliases[alias_name]}"
        )

    def test_at_least_15_curated_mappings(self):
        """Housing authority aliases file has at least 15 curated mappings."""
        data = _load_ha_aliases()
        # The curated count is in metadata
        curated = data["_metadata"].get("curated_count", 0)
        assert curated >= 15, (
            f"Expected at least 15 curated mappings, got {curated}"
        )


# ── Regional authority exclusion ──


class TestRegionalAuthoritiesExcluded:
    """Test that multi-Tribe regional housing authorities are excluded."""

    @pytest.mark.parametrize(
        "regional_name",
        [
            "interior regional housing authority",
            "bering straits regional housing authority",
        ],
    )
    def test_regional_authorities_excluded(self, regional_name):
        """Regional housing authorities serving multiple Tribes must NOT be in aliases."""
        data = _load_ha_aliases()
        aliases = data["aliases"]
        assert regional_name not in aliases, (
            f"Regional authority should be excluded: {regional_name}"
        )

    def test_skipped_regional_documented(self):
        """Skipped regional authorities are documented in metadata."""
        data = _load_ha_aliases()
        skipped = data["_metadata"].get("skipped_regional", [])
        assert len(skipped) > 0, "Skipped regional authorities should be documented"
        # Check that interior regional is in the skipped list
        skipped_lower = [s.lower() for s in skipped]
        assert any("interior regional" in s for s in skipped_lower)


# ── Main alias table integration ──


class TestAliasTableIncludesHousingAuthorities:
    """Test that the rebuilt main alias table contains housing authority entries."""

    def test_alias_table_includes_housing_authorities(self):
        """After rebuild, tribal_aliases.json contains housing authority entries."""
        aliases_data = _load_tribal_aliases()
        aliases = aliases_data["aliases"]

        # Check that known housing authority names are in the main table
        assert "navajo housing authority" in aliases
        assert "hopi tribal housing authority" in aliases
        assert "blackfeet housing program" in aliases

    def test_alias_table_count_increased(self):
        """Main alias table should have more than 3,751 aliases after merge."""
        aliases_data = _load_tribal_aliases()
        count = aliases_data["_metadata"]["total_aliases"]
        assert count > 3751, (
            f"Expected alias count > 3,751 after merge, got {count}"
        )


# ── TribalAwardMatcher resolution ──


class TestMatcherResolvesHousingAuthority:
    """Test that TribalAwardMatcher resolves housing authority names to Tribes."""

    def test_matcher_resolves_housing_authority(self, tmp_path):
        """Matcher resolves 'NAVAJO HOUSING AUTHORITY' to Navajo Nation."""
        tribes = [
            {
                "tribe_id": "epa_100000171",
                "name": "Navajo Nation",
                "states": ["AZ", "NM", "UT"],
                "alternate_names": [],
            },
        ]
        aliases = {
            "navajo nation": "epa_100000171",
            "navajo housing authority": "epa_100000171",
        }
        matcher = _make_matcher(tmp_path, tribes, aliases=aliases)

        result = matcher.match_recipient_to_tribe("NAVAJO HOUSING AUTHORITY")
        assert result is not None
        assert result["tribe_id"] == "epa_100000171"
        assert result["name"] == "Navajo Nation"

    def test_matcher_resolves_housing_program(self, tmp_path):
        """Matcher resolves housing program variant names."""
        tribes = [
            {
                "tribe_id": "epa_100000020",
                "name": "Blackfeet Tribe",
                "states": ["MT"],
                "alternate_names": [],
            },
        ]
        aliases = {
            "blackfeet tribe": "epa_100000020",
            "blackfeet housing program": "epa_100000020",
        }
        matcher = _make_matcher(tmp_path, tribes, aliases=aliases)

        result = matcher.match_recipient_to_tribe("BLACKFEET HOUSING PROGRAM")
        assert result is not None
        assert result["tribe_id"] == "epa_100000020"

    def test_matcher_does_not_resolve_unrelated_name(self, tmp_path):
        """Matcher returns None for names not in aliases or registry."""
        tribes = [
            {
                "tribe_id": "epa_100000171",
                "name": "Navajo Nation",
                "states": ["AZ", "NM", "UT"],
                "alternate_names": [],
            },
        ]
        aliases = {
            "navajo nation": "epa_100000171",
            "navajo housing authority": "epa_100000171",
        }
        matcher = _make_matcher(tmp_path, tribes, aliases=aliases)

        result = matcher.match_recipient_to_tribe("ACME CORPORATION")
        assert result is None

    def test_matcher_uses_full_alias_table(self):
        """Using the real alias table, matcher resolves housing authorities."""
        # Use the actual project data files
        config = {
            "packets": {
                "tribal_registry": {"data_path": str(_REGISTRY_PATH)},
                "awards": {
                    "alias_path": str(_TRIBAL_ALIASES_PATH),
                    "cache_dir": str(_DATA_DIR / "award_cache"),
                },
            },
        }
        matcher = TribalAwardMatcher(config)

        # Test several housing authority names
        result = matcher.match_recipient_to_tribe("NAVAJO HOUSING AUTHORITY")
        assert result is not None
        assert result["tribe_id"] == "epa_100000171"

        result = matcher.match_recipient_to_tribe("HOPI TRIBAL HOUSING AUTHORITY")
        assert result is not None
        assert result["tribe_id"] == "epa_100000104"

        result = matcher.match_recipient_to_tribe("STANDING ROCK HOUSING LOCAL DEVELOPMENT")
        assert result is not None
        assert result["tribe_id"] == "epa_100000289"
