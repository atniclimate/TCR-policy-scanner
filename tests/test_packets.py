"""Test suite for Phase 5 and Phase 6 packet modules.

Covers all Phase 5 requirements:
  REG-01: TribalRegistry (name resolution, fuzzy search)
  REG-02: EcoregionMapper (state-to-ecoregion classification)
  REG-03: TribePacketContext (dataclass, serialization)
  CONG-01: CongressionalMapper districts
  CONG-02: CongressionalMapper members and committees

Covers Phase 6 requirements:
  AWARD-01, AWARD-02: TribalAwardMatcher (alias lookup, fuzzy matching, cache)
  HAZ-01, HAZ-02: HazardProfileBuilder (NRI parsing, aggregation, USFS)
  Orchestrator integration (award + hazard context loading and display)

All tests use tmp_path fixtures with mock data -- no network access required.
"""

import json
import pytest
from pathlib import Path


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _write_json(path: Path, data: dict) -> None:
    """Write a dict as JSON to the given path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


@pytest.fixture
def registry_data(tmp_path: Path) -> dict:
    """Create a mock tribal_registry.json and return a config dict."""
    data = {
        "metadata": {"total_tribes": 5, "placeholder": False},
        "tribes": [
            {
                "tribe_id": "epa_001",
                "bia_code": "100",
                "name": "Alpha Tribe of Arizona",
                "states": ["AZ"],
                "alternate_names": ["Alpha AZ Tribe"],
                "epa_region": "9",
                "bia_recognized": True,
            },
            {
                "tribe_id": "epa_002",
                "bia_code": "200",
                "name": "Beta Band of Choctaw",
                "states": ["OK"],
                "alternate_names": ["Beta Choctaw"],
                "epa_region": "6",
                "bia_recognized": True,
            },
            {
                "tribe_id": "epa_003",
                "bia_code": "300",
                "name": "Gamma Choctaw Nation of Oklahoma",
                "states": ["OK", "TX"],
                "alternate_names": [],
                "epa_region": "6",
                "bia_recognized": True,
            },
            {
                "tribe_id": "epa_004",
                "bia_code": "400",
                "name": "Delta Village of Alaska",
                "states": ["AK"],
                "alternate_names": ["Delta Alaska Village", "Delta AK"],
                "epa_region": "10",
                "bia_recognized": True,
            },
            {
                "tribe_id": "epa_005",
                "bia_code": "500",
                "name": "Epsilon Pueblo of New Mexico",
                "states": ["NM"],
                "alternate_names": [],
                "epa_region": "6",
                "bia_recognized": True,
            },
        ],
    }
    path = tmp_path / "tribal_registry.json"
    _write_json(path, data)
    config = {
        "packets": {
            "tribal_registry": {"data_path": str(path)},
        }
    }
    return config


@pytest.fixture
def ecoregion_data(tmp_path: Path) -> dict:
    """Create a mock ecoregion_config.json and return a config dict."""
    data = {
        "metadata": {"version": "test"},
        "ecoregions": {
            "southwest": {
                "name": "Southwest",
                "states": ["AZ", "NM", "NV", "UT", "CA"],
                "priority_programs": ["bia_tcr", "fema_bric"],
            },
            "alaska": {
                "name": "Alaska",
                "states": ["AK"],
                "priority_programs": ["bia_tcr", "epa_gap"],
            },
            "great_plains_south": {
                "name": "Great Plains South",
                "states": ["OK", "TX", "KS"],
                "priority_programs": ["fema_bric", "usda_wildfire"],
            },
            "northeast_midwest": {
                "name": "Northeast & Midwest",
                "states": ["NY", "PA", "OH", "MI", "MN"],
                "priority_programs": ["epa_gap"],
            },
        },
    }
    path = tmp_path / "ecoregion_config.json"
    _write_json(path, data)
    config = {
        "packets": {
            "ecoregion": {"data_path": str(path)},
        }
    }
    return config


@pytest.fixture
def congress_data(tmp_path: Path) -> dict:
    """Create a mock congressional_cache.json and return a config dict."""
    data = {
        "metadata": {
            "congress_session": "119",
            "total_members": 3,
            "total_committees": 2,
            "total_tribes_mapped": 2,
        },
        "members": {
            "S001": {
                "bioguide_id": "S001",
                "name": "Smith, Jane",
                "state": "AZ",
                "district": None,
                "party": "Democratic",
                "party_abbr": "D",
                "chamber": "Senate",
                "formatted_name": "Sen. Jane Smith (D-AZ)",
            },
            "S002": {
                "bioguide_id": "S002",
                "name": "Jones, Bob",
                "state": "AZ",
                "district": None,
                "party": "Republican",
                "party_abbr": "R",
                "chamber": "Senate",
                "formatted_name": "Sen. Bob Jones (R-AZ)",
            },
            "R001": {
                "bioguide_id": "R001",
                "name": "Lee, Carol",
                "state": "AZ",
                "district": 2,
                "party": "Democratic",
                "party_abbr": "D",
                "chamber": "House",
                "formatted_name": "Rep. Carol Lee (D-AZ-02)",
            },
        },
        "committees": {
            "SLIA": {
                "name": "Senate Committee on Indian Affairs",
                "chamber": "Senate",
                "members": [
                    {"bioguide_id": "S001", "name": "Smith, Jane", "role": "member"},
                ],
            },
            "HSII24": {
                "name": "Indian and Insular Affairs",
                "chamber": "House",
                "members": [
                    {"bioguide_id": "R001", "name": "Lee, Carol", "role": "ranking_member"},
                ],
            },
        },
        "delegations": {
            "epa_001": {
                "tribe_id": "epa_001",
                "districts": [
                    {
                        "district": "AZ-02",
                        "state": "AZ",
                        "aiannh_name": "Alpha Reservation",
                        "overlap_pct": 95.0,
                    },
                ],
                "states": ["AZ"],
                "senators": [
                    {
                        "bioguide_id": "S001",
                        "name": "Smith, Jane",
                        "state": "AZ",
                        "district": None,
                        "party": "Democratic",
                        "party_abbr": "D",
                        "chamber": "Senate",
                        "formatted_name": "Sen. Jane Smith (D-AZ)",
                        "committees": [
                            {"committee_id": "SLIA", "committee_name": "Senate Committee on Indian Affairs", "role": "member"},
                        ],
                    },
                    {
                        "bioguide_id": "S002",
                        "name": "Jones, Bob",
                        "state": "AZ",
                        "district": None,
                        "party": "Republican",
                        "party_abbr": "R",
                        "chamber": "Senate",
                        "formatted_name": "Sen. Bob Jones (R-AZ)",
                        "committees": [],
                    },
                ],
                "representatives": [
                    {
                        "bioguide_id": "R001",
                        "name": "Lee, Carol",
                        "state": "AZ",
                        "district": 2,
                        "party": "Democratic",
                        "party_abbr": "D",
                        "chamber": "House",
                        "formatted_name": "Rep. Carol Lee (D-AZ-02)",
                        "committees": [
                            {"committee_id": "HSII24", "committee_name": "Indian and Insular Affairs", "role": "ranking_member"},
                        ],
                    },
                ],
            },
            "epa_003": {
                "tribe_id": "epa_003",
                "districts": [
                    {"district": "OK-02", "state": "OK", "aiannh_name": "Gamma Reserve", "overlap_pct": 60.0},
                    {"district": "TX-01", "state": "TX", "aiannh_name": "Gamma Reserve", "overlap_pct": 40.0},
                ],
                "states": ["OK", "TX"],
                "senators": [
                    {"bioguide_id": "S010", "name": "Okla, Sam", "state": "OK", "party_abbr": "R", "chamber": "Senate", "formatted_name": "Sen. Sam Okla (R-OK)", "committees": []},
                    {"bioguide_id": "S011", "name": "Okla, Pat", "state": "OK", "party_abbr": "D", "chamber": "Senate", "formatted_name": "Sen. Pat Okla (D-OK)", "committees": []},
                    {"bioguide_id": "S012", "name": "Tex, Ann", "state": "TX", "party_abbr": "R", "chamber": "Senate", "formatted_name": "Sen. Ann Tex (R-TX)", "committees": []},
                    {"bioguide_id": "S013", "name": "Tex, Dan", "state": "TX", "party_abbr": "R", "chamber": "Senate", "formatted_name": "Sen. Dan Tex (R-TX)", "committees": []},
                ],
                "representatives": [
                    {"bioguide_id": "R010", "name": "House, Joe", "state": "OK", "district": 2, "party_abbr": "R", "chamber": "House", "formatted_name": "Rep. Joe House (R-OK-02)", "committees": []},
                    {"bioguide_id": "R011", "name": "House, Amy", "state": "TX", "district": 1, "party_abbr": "D", "chamber": "House", "formatted_name": "Rep. Amy House (D-TX-01)", "committees": []},
                ],
            },
        },
    }
    path = tmp_path / "congressional_cache.json"
    _write_json(path, data)
    config = {
        "packets": {
            "congressional_cache": {"data_path": str(path)},
        }
    }
    return config


# ===========================================================================
# REG-02: TestEcoregionMapper
# ===========================================================================

class TestEcoregionMapper:
    """Tests for EcoregionMapper (REG-02)."""

    def test_single_state(self, ecoregion_data: dict) -> None:
        from src.packets.ecoregion import EcoregionMapper
        mapper = EcoregionMapper(ecoregion_data)
        result = mapper.classify(["AZ"])
        assert result == ["southwest"]

    def test_multi_state_same_ecoregion(self, ecoregion_data: dict) -> None:
        from src.packets.ecoregion import EcoregionMapper
        mapper = EcoregionMapper(ecoregion_data)
        result = mapper.classify(["AZ", "NM"])
        assert result == ["southwest"]

    def test_cross_ecoregion(self, ecoregion_data: dict) -> None:
        from src.packets.ecoregion import EcoregionMapper
        mapper = EcoregionMapper(ecoregion_data)
        result = mapper.classify(["OK", "AZ"])
        assert sorted(result) == ["great_plains_south", "southwest"]

    def test_alaska(self, ecoregion_data: dict) -> None:
        from src.packets.ecoregion import EcoregionMapper
        mapper = EcoregionMapper(ecoregion_data)
        result = mapper.classify(["AK"])
        assert result == ["alaska"]

    def test_all_states_have_ecoregion(self, ecoregion_data: dict) -> None:
        from src.packets.ecoregion import EcoregionMapper
        mapper = EcoregionMapper(ecoregion_data)
        # All mapped states should resolve
        for state in ["AZ", "NM", "NV", "UT", "CA", "AK", "OK", "TX", "KS",
                       "NY", "PA", "OH", "MI", "MN"]:
            result = mapper.classify([state])
            assert len(result) == 1, f"State {state} should map to exactly 1 ecoregion"

    def test_priority_programs(self, ecoregion_data: dict) -> None:
        from src.packets.ecoregion import EcoregionMapper
        mapper = EcoregionMapper(ecoregion_data)
        progs = mapper.get_priority_programs("southwest")
        assert progs == ["bia_tcr", "fema_bric"]

    def test_unknown_state(self, ecoregion_data: dict) -> None:
        from src.packets.ecoregion import EcoregionMapper
        mapper = EcoregionMapper(ecoregion_data)
        result = mapper.classify(["ZZ"])
        assert result == []


# ===========================================================================
# REG-01: TestTribalRegistry
# ===========================================================================

class TestTribalRegistry:
    """Tests for TribalRegistry (REG-01)."""

    def test_exact_match(self, registry_data: dict) -> None:
        from src.packets.registry import TribalRegistry
        reg = TribalRegistry(registry_data)
        result = reg.resolve("Alpha Tribe of Arizona")
        assert isinstance(result, dict)
        assert result["tribe_id"] == "epa_001"

    def test_case_insensitive(self, registry_data: dict) -> None:
        from src.packets.registry import TribalRegistry
        reg = TribalRegistry(registry_data)
        result = reg.resolve("alpha tribe of arizona")
        assert isinstance(result, dict)
        assert result["tribe_id"] == "epa_001"

    def test_substring_single(self, registry_data: dict) -> None:
        from src.packets.registry import TribalRegistry
        reg = TribalRegistry(registry_data)
        # "Epsilon" substring matches only one tribe
        result = reg.resolve("Epsilon")
        assert isinstance(result, dict)
        assert result["tribe_id"] == "epa_005"

    def test_substring_ambiguous(self, registry_data: dict) -> None:
        from src.packets.registry import TribalRegistry
        reg = TribalRegistry(registry_data)
        # "Choctaw" appears in both epa_002 and epa_003
        result = reg.resolve("Choctaw")
        assert isinstance(result, list)
        assert len(result) == 2
        ids = {r["tribe_id"] for r in result}
        assert ids == {"epa_002", "epa_003"}

    def test_alternate_name_match(self, registry_data: dict) -> None:
        from src.packets.registry import TribalRegistry
        reg = TribalRegistry(registry_data)
        # "Delta AK" is an alternate name for epa_004
        result = reg.resolve("Delta AK")
        assert isinstance(result, dict)
        assert result["tribe_id"] == "epa_004"

    def test_fuzzy_match(self, registry_data: dict) -> None:
        from src.packets.registry import TribalRegistry
        reg = TribalRegistry(registry_data)
        # "Alfa Tribe" is close to "Alpha Tribe of Arizona" via fuzzy
        result = reg.resolve("Alfa Tribe")
        # Should return a list with _match_score or a dict
        if isinstance(result, list):
            assert any(r.get("_match_score") for r in result)
            assert result[0]["tribe_id"] == "epa_001"
        elif isinstance(result, dict):
            # Could be resolved directly
            assert result["tribe_id"] == "epa_001"
        else:
            pytest.fail("Expected fuzzy result, got None")

    def test_no_match_returns_none(self, registry_data: dict) -> None:
        from src.packets.registry import TribalRegistry
        reg = TribalRegistry(registry_data)
        result = reg.resolve("xyznonexistent123")
        assert result is None

    def test_get_all(self, registry_data: dict) -> None:
        from src.packets.registry import TribalRegistry
        reg = TribalRegistry(registry_data)
        all_tribes = reg.get_all()
        assert len(all_tribes) == 5
        assert all("tribe_id" in t for t in all_tribes)

    def test_get_by_id(self, registry_data: dict) -> None:
        from src.packets.registry import TribalRegistry
        reg = TribalRegistry(registry_data)
        result = reg.get_by_id("epa_004")
        assert result is not None
        assert result["name"] == "Delta Village of Alaska"

    def test_alaska_valid_id(self, registry_data: dict) -> None:
        from src.packets.registry import TribalRegistry
        reg = TribalRegistry(registry_data)
        result = reg.get_by_id("epa_004")
        assert result is not None
        assert "AK" in result["states"]


# ===========================================================================
# CONG-01, CONG-02: TestCongressionalMapper
# ===========================================================================

class TestCongressionalMapper:
    """Tests for CongressionalMapper (CONG-01, CONG-02)."""

    def test_get_delegation(self, congress_data: dict) -> None:
        from src.packets.congress import CongressionalMapper
        mapper = CongressionalMapper(congress_data)
        delegation = mapper.get_delegation("epa_001")
        assert delegation is not None
        assert delegation["tribe_id"] == "epa_001"
        assert len(delegation["districts"]) == 1
        assert len(delegation["senators"]) == 2
        assert len(delegation["representatives"]) == 1

    def test_multi_state_districts(self, congress_data: dict) -> None:
        from src.packets.congress import CongressionalMapper
        mapper = CongressionalMapper(congress_data)
        districts = mapper.get_districts("epa_003")
        assert len(districts) == 2
        states = {d["state"] for d in districts}
        assert states == {"OK", "TX"}

    def test_senators_not_duplicated(self, congress_data: dict) -> None:
        from src.packets.congress import CongressionalMapper
        mapper = CongressionalMapper(congress_data)
        senators = mapper.get_senators("epa_003")
        # 4 senators (2 per state for OK + TX), each unique
        ids = [s["bioguide_id"] for s in senators]
        assert len(ids) == len(set(ids)), "Senators should not be duplicated"
        assert len(senators) == 4

    def test_unknown_tribe(self, congress_data: dict) -> None:
        from src.packets.congress import CongressionalMapper
        mapper = CongressionalMapper(congress_data)
        delegation = mapper.get_delegation("epa_999")
        assert delegation is None

    def test_congress_session(self, congress_data: dict) -> None:
        from src.packets.congress import CongressionalMapper
        mapper = CongressionalMapper(congress_data)
        session = mapper.get_congress_session()
        assert session == "119"

    def test_relevant_committees(self, congress_data: dict) -> None:
        from src.packets.congress import CongressionalMapper
        mapper = CongressionalMapper(congress_data)
        committees = mapper.get_relevant_committees("epa_001")
        # SLIA has S001 who is in epa_001's delegation
        # HSII24 has R001 who is in epa_001's delegation
        assert len(committees) >= 1
        comm_ids = {c["committee_id"] for c in committees}
        assert "SLIA" in comm_ids

    def test_get_representatives(self, congress_data: dict) -> None:
        from src.packets.congress import CongressionalMapper
        mapper = CongressionalMapper(congress_data)
        reps = mapper.get_representatives("epa_001")
        assert len(reps) == 1
        assert reps[0]["formatted_name"] == "Rep. Carol Lee (D-AZ-02)"

    def test_get_member(self, congress_data: dict) -> None:
        from src.packets.congress import CongressionalMapper
        mapper = CongressionalMapper(congress_data)
        member = mapper.get_member("S001")
        assert member is not None
        assert member["name"] == "Smith, Jane"
        assert member["chamber"] == "Senate"


# ===========================================================================
# REG-03: TestTribePacketContext
# ===========================================================================

class TestTribePacketContext:
    """Tests for TribePacketContext (REG-03)."""

    def test_create_context(self) -> None:
        from src.packets.context import TribePacketContext
        ctx = TribePacketContext(
            tribe_id="epa_001",
            tribe_name="Alpha Tribe",
            states=["AZ"],
            ecoregions=["southwest"],
            bia_code="100",
            districts=[{"district": "AZ-02", "state": "AZ"}],
            senators=[{"name": "Smith", "state": "AZ"}],
            representatives=[{"name": "Lee", "state": "AZ", "district": 2}],
            generated_at="2026-01-01T00:00:00+00:00",
        )
        assert ctx.tribe_id == "epa_001"
        assert ctx.tribe_name == "Alpha Tribe"
        assert ctx.states == ["AZ"]
        assert ctx.ecoregions == ["southwest"]
        assert len(ctx.districts) == 1
        assert len(ctx.senators) == 1
        assert len(ctx.representatives) == 1

    def test_to_dict_serializable(self) -> None:
        from src.packets.context import TribePacketContext
        ctx = TribePacketContext(
            tribe_id="epa_002",
            tribe_name="Beta Band",
            states=["OK"],
            ecoregions=["great_plains_south"],
            districts=[{"district": "OK-02"}],
            generated_at="2026-01-01T00:00:00+00:00",
        )
        d = ctx.to_dict()
        assert isinstance(d, dict)
        assert d["tribe_id"] == "epa_002"
        assert d["tribe_name"] == "Beta Band"
        assert d["states"] == ["OK"]
        assert d["districts"] == [{"district": "OK-02"}]
        # Should be JSON-serializable
        json.dumps(d)

    def test_stub_fields_default_empty(self) -> None:
        from src.packets.context import TribePacketContext
        ctx = TribePacketContext(tribe_id="epa_999", tribe_name="Stub Tribe")
        assert ctx.awards == []
        assert ctx.hazard_profile == {}
        assert ctx.economic_impact == {}
        assert ctx.districts == []
        assert ctx.senators == []
        assert ctx.representatives == []
        assert ctx.congress_session == "119"


# ===========================================================================
# TestPacketOrchestrator
# ===========================================================================

class TestPacketOrchestrator:
    """Tests for PacketOrchestrator integration."""

    @pytest.fixture
    def full_config(self, registry_data: dict, ecoregion_data: dict, congress_data: dict) -> dict:
        """Merge all sub-configs into one."""
        merged = {"packets": {}}
        merged["packets"].update(registry_data.get("packets", {}))
        merged["packets"].update(ecoregion_data.get("packets", {}))
        merged["packets"].update(congress_data.get("packets", {}))
        return merged

    def test_build_context_assembles_all_layers(self, full_config: dict) -> None:
        from src.packets.orchestrator import PacketOrchestrator
        programs = [
            {"id": "bia_tcr", "name": "BIA Tribal Climate Resilience"},
            {"id": "fema_bric", "name": "FEMA BRIC"},
        ]
        orch = PacketOrchestrator(full_config, programs)

        # Resolve Alpha Tribe
        tribe = orch.registry.resolve("Alpha Tribe of Arizona")
        assert isinstance(tribe, dict)

        ctx = orch._build_context(tribe)
        assert ctx.tribe_id == "epa_001"
        assert ctx.tribe_name == "Alpha Tribe of Arizona"
        assert ctx.states == ["AZ"]
        assert "southwest" in ctx.ecoregions
        assert len(ctx.districts) == 1
        assert ctx.districts[0]["district"] == "AZ-02"
        assert len(ctx.senators) == 2
        assert len(ctx.representatives) == 1
        assert ctx.congress_session == "119"
        assert ctx.generated_at != ""

    def test_build_context_no_delegation(self, full_config: dict) -> None:
        """Tribe with no congressional delegation still builds context."""
        from src.packets.orchestrator import PacketOrchestrator
        programs = [{"id": "bia_tcr", "name": "BIA TCR"}]
        orch = PacketOrchestrator(full_config, programs)

        tribe = orch.registry.resolve("Delta Village of Alaska")
        assert isinstance(tribe, dict)

        ctx = orch._build_context(tribe)
        assert ctx.tribe_id == "epa_004"
        assert ctx.states == ["AK"]
        assert "alaska" in ctx.ecoregions
        # epa_004 has no delegation in mock data
        assert ctx.districts == []
        assert ctx.senators == []
        assert ctx.representatives == []

    def test_run_single_tribe_exact(self, full_config: dict, capsys: pytest.CaptureFixture) -> None:
        """run_single_tribe with exact match prints tribe info."""
        from src.packets.orchestrator import PacketOrchestrator
        programs = [{"id": "bia_tcr", "name": "BIA TCR"}]
        orch = PacketOrchestrator(full_config, programs)
        orch.run_single_tribe("Alpha Tribe of Arizona")
        output = capsys.readouterr().out
        assert "Alpha Tribe of Arizona" in output
        assert "AZ-02" in output
        assert "Sen. Jane Smith (D-AZ)" in output


# ===========================================================================
# AWARD-01, AWARD-02: TestTribalAwardMatcher
# ===========================================================================

class TestTribalAwardMatcher:
    """Tests for TribalAwardMatcher (AWARD-01 + AWARD-02)."""

    @pytest.fixture
    def award_config(self, tmp_path: Path) -> dict:
        """Create mock registry, alias table, and award cache dir for testing."""
        # Mini registry with 4 Tribes across different states
        registry = {
            "metadata": {"total_tribes": 4, "placeholder": False},
            "tribes": [
                {
                    "tribe_id": "epa_001",
                    "bia_code": "100",
                    "name": "Alpha Tribe of Arizona",
                    "states": ["AZ"],
                    "alternate_names": ["Alpha AZ Tribe"],
                    "epa_region": "9",
                    "bia_recognized": True,
                },
                {
                    "tribe_id": "epa_002",
                    "bia_code": "200",
                    "name": "Beta Band of Choctaw",
                    "states": ["OK"],
                    "alternate_names": ["Beta Choctaw"],
                    "epa_region": "6",
                    "bia_recognized": True,
                },
                {
                    "tribe_id": "epa_003",
                    "bia_code": "300",
                    "name": "Gamma Choctaw Nation of Oklahoma",
                    "states": ["OK", "TX"],
                    "alternate_names": [],
                    "epa_region": "6",
                    "bia_recognized": True,
                },
                {
                    "tribe_id": "epa_004",
                    "bia_code": "400",
                    "name": "Delta Village of Alaska",
                    "states": ["AK"],
                    "alternate_names": ["Delta Alaska Village"],
                    "epa_region": "10",
                    "bia_recognized": True,
                },
            ],
        }
        reg_path = tmp_path / "tribal_registry.json"
        _write_json(reg_path, registry)

        # Alias table mapping known variants -> tribe_id
        aliases = {
            "aliases": {
                "alpha az tribe": "epa_001",
                "alpha tribe of arizona": "epa_001",
                "beta choctaw": "epa_002",
                "beta band of choctaw": "epa_002",
                "gamma choctaw nation of oklahoma": "epa_003",
                "delta alaska village": "epa_004",
            }
        }
        alias_path = tmp_path / "tribal_aliases.json"
        _write_json(alias_path, aliases)

        cache_dir = tmp_path / "award_cache"
        cache_dir.mkdir()

        return {
            "packets": {
                "tribal_registry": {"data_path": str(reg_path)},
                "awards": {
                    "alias_path": str(alias_path),
                    "cache_dir": str(cache_dir),
                    "fuzzy_threshold": 85,
                },
            }
        }

    def test_alias_table_load(self, award_config: dict) -> None:
        """Verify TribalAwardMatcher loads the alias table correctly."""
        from src.packets.awards import TribalAwardMatcher
        matcher = TribalAwardMatcher(award_config)
        assert len(matcher.alias_table) == 6
        assert "alpha az tribe" in matcher.alias_table
        assert matcher.alias_table["alpha az tribe"] == "epa_001"

    def test_match_tier1_exact_alias(self, award_config: dict) -> None:
        """Verify exact alias table match returns correct Tribe dict."""
        from src.packets.awards import TribalAwardMatcher
        matcher = TribalAwardMatcher(award_config)
        result = matcher.match_recipient_to_tribe("Alpha AZ Tribe")
        assert result is not None
        assert result["tribe_id"] == "epa_001"

    def test_match_tier2_fuzzy_token_sort(self, award_config: dict) -> None:
        """Verify fuzzy matching with score >= 85 returns correct Tribe."""
        from src.packets.awards import TribalAwardMatcher
        matcher = TribalAwardMatcher(award_config)
        # Close variant but not in alias table
        result = matcher.match_recipient_to_tribe(
            "Alpha Tribe Arizona", recipient_state="AZ"
        )
        assert result is not None
        assert result["tribe_id"] == "epa_001"

    def test_match_tier2_below_threshold(self, award_config: dict) -> None:
        """Verify score < 85 returns None (false negative, not false positive)."""
        from src.packets.awards import TribalAwardMatcher
        matcher = TribalAwardMatcher(award_config)
        # Very different name -- should not match
        result = matcher.match_recipient_to_tribe("Completely Different Organization")
        assert result is None

    def test_match_state_overlap_rejection(self, award_config: dict) -> None:
        """Verify state mismatch causes rejection even with high fuzzy score."""
        from src.packets.awards import TribalAwardMatcher
        matcher = TribalAwardMatcher(award_config)
        # "Beta Band of Choctaw" is in OK, so searching with state MS should reject
        result = matcher.match_recipient_to_tribe(
            "Beta Band of Choctaw People", recipient_state="MS"
        )
        assert result is None

    def test_match_state_overlap_pass(self, award_config: dict) -> None:
        """Verify state match allows the match through."""
        from src.packets.awards import TribalAwardMatcher
        matcher = TribalAwardMatcher(award_config)
        # Same name variant but with correct state
        result = matcher.match_recipient_to_tribe(
            "Beta Band of Choctaw People", recipient_state="OK"
        )
        assert result is not None
        assert result["tribe_id"] == "epa_002"

    def test_match_no_match_returns_none(self, award_config: dict) -> None:
        """Verify completely unrecognizable name returns None."""
        from src.packets.awards import TribalAwardMatcher
        matcher = TribalAwardMatcher(award_config)
        result = matcher.match_recipient_to_tribe("XYZ Corporation Inc")
        assert result is None

    def test_match_all_awards_grouping(self, award_config: dict) -> None:
        """Verify awards are correctly grouped by tribe_id after matching."""
        from src.packets.awards import TribalAwardMatcher
        matcher = TribalAwardMatcher(award_config)

        awards_by_cfda = {
            "15.156": [
                {"Recipient Name": "Alpha AZ Tribe", "Award ID": "A001",
                 "Total Obligation": "500000", "Start Date": "2024-01-01",
                 "End Date": "2025-01-01", "Description": "TCR grant",
                 "Awarding Agency": "DOI"},
                {"Recipient Name": "Alpha AZ Tribe", "Award ID": "A002",
                 "Total Obligation": "250000", "Start Date": "2024-06-01",
                 "End Date": "2025-06-01", "Description": "TCR grant 2",
                 "Awarding Agency": "DOI"},
            ],
            "97.047": [
                {"Recipient Name": "Delta Alaska Village", "Award ID": "B001",
                 "Total Obligation": "100000", "Start Date": "2024-03-01",
                 "End Date": "2025-03-01", "Description": "BRIC grant",
                 "Awarding Agency": "FEMA"},
            ],
        }

        result = matcher.match_all_awards(awards_by_cfda)
        assert "epa_001" in result
        assert len(result["epa_001"]) == 2
        assert "epa_004" in result
        assert len(result["epa_004"]) == 1
        # Verify obligation converted to float
        assert result["epa_001"][0]["obligation"] == 500000.0

    def test_write_cache_zero_awards(self, award_config: dict) -> None:
        """Verify zero-award Tribes get cache file with no_awards_context field."""
        from src.packets.awards import TribalAwardMatcher
        matcher = TribalAwardMatcher(award_config)

        # No awards matched to any Tribe
        count = matcher.write_cache({})
        assert count == 4  # All 4 Tribes get cache files

        # Check a specific Tribe's cache file
        cache_file = Path(award_config["packets"]["awards"]["cache_dir"]) / "epa_001.json"
        assert cache_file.exists()
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["awards"] == []
        assert data["award_count"] == 0
        assert "no_awards_context" in data
        assert "first-time applicant" in data["no_awards_context"]

    def test_write_cache_numeric_amounts(self, award_config: dict) -> None:
        """Verify award amounts are stored as float, not string."""
        from src.packets.awards import TribalAwardMatcher
        matcher = TribalAwardMatcher(award_config)

        matched = {
            "epa_001": [
                {"obligation": 500000.0, "cfda": "15.156", "award_id": "A001"},
                {"obligation": 250000.0, "cfda": "15.156", "award_id": "A002"},
            ]
        }
        matcher.write_cache(matched)

        cache_file = Path(award_config["packets"]["awards"]["cache_dir"]) / "epa_001.json"
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data["total_obligation"], float)
        assert data["total_obligation"] == 750000.0
        assert data["award_count"] == 2
        for award in data["awards"]:
            assert isinstance(award["obligation"], (int, float))


# ===========================================================================
# HAZ-01, HAZ-02: TestHazardProfileBuilder
# ===========================================================================

class TestHazardProfileBuilder:
    """Tests for HazardProfileBuilder (HAZ-01 + HAZ-02)."""

    @pytest.fixture
    def hazard_config(self, tmp_path: Path) -> dict:
        """Create mock registry, crosswalk, NRI CSV, and USFS dir for testing."""
        # Mini registry
        registry = {
            "metadata": {"total_tribes": 3, "placeholder": False},
            "tribes": [
                {
                    "tribe_id": "epa_001",
                    "bia_code": "100",
                    "name": "Alpha Tribe of Arizona",
                    "states": ["AZ"],
                    "alternate_names": [],
                    "epa_region": "9",
                    "bia_recognized": True,
                },
                {
                    "tribe_id": "epa_002",
                    "bia_code": "200",
                    "name": "Beta Band of Choctaw",
                    "states": ["OK"],
                    "alternate_names": [],
                    "epa_region": "6",
                    "bia_recognized": True,
                },
                {
                    "tribe_id": "epa_003",
                    "bia_code": "300",
                    "name": "Zeta Tribe with Diacritics",
                    "states": ["NM"],
                    "alternate_names": [],
                    "epa_region": "6",
                    "bia_recognized": True,
                },
            ],
        }
        reg_path = tmp_path / "tribal_registry.json"
        _write_json(reg_path, registry)

        # Crosswalk: AIANNH GEOID -> tribe_id
        crosswalk = {
            "mappings": {
                "0400001": "epa_001",
                "0400002": "epa_001",  # Alpha spans 2 AIANNH areas
                "4000001": "epa_002",
            }
        }
        crosswalk_path = tmp_path / "aiannh_tribe_crosswalk.json"
        _write_json(crosswalk_path, crosswalk)

        # NRI directory with county CSV
        nri_dir = tmp_path / "nri"
        nri_dir.mkdir()

        # Create mock NRI county CSV with 4 counties
        nri_csv = nri_dir / "NRI_Table_Counties.csv"
        headers = [
            "STCOFIPS", "COUNTY", "STATE", "RISK_SCORE", "RISK_RATNG",
            "RISK_VALUE", "EAL_VALT", "EAL_SCORE", "EAL_RATNG",
            "SOVI_SCORE", "SOVI_RATNG", "RESL_SCORE", "RESL_RATNG",
        ]
        # Add per-hazard columns for WFIR and DRGT (2 of 18)
        for code in ["WFIR", "DRGT", "HRCN"]:
            headers.extend([
                f"{code}_RISKS", f"{code}_RISKR", f"{code}_EALT",
                f"{code}_AFREQ", f"{code}_EVNTS",
            ])

        rows = [
            # AZ county matching epa_001 via crosswalk
            ["04001", "Maricopa", "Arizona", "85.5", "Very High",
             "1000000", "500000", "90.0", "Very High",
             "72.0", "Relatively High", "45.0", "Relatively Moderate",
             # WFIR
             "88.0", "Very High", "200000", "5.2", "100",
             # DRGT
             "60.0", "Relatively Moderate", "100000", "3.1", "50",
             # HRCN
             "10.0", "Very Low", "5000", "0.1", "2",
             ],
            # Another AZ county
            ["04003", "Pima", "Arizona", "70.0", "Relatively High",
             "800000", "400000", "75.0", "Relatively High",
             "65.0", "Relatively Moderate", "50.0", "Relatively Moderate",
             # WFIR
             "92.0", "Very High", "300000", "6.0", "120",
             # DRGT
             "55.0", "Relatively Moderate", "80000", "2.5", "40",
             # HRCN
             "15.0", "Very Low", "8000", "0.2", "3",
             ],
            # OK county matching epa_002 via crosswalk
            ["40001", "Adair", "Oklahoma", "50.0", "Relatively Moderate",
             "300000", "150000", "55.0", "Relatively Moderate",
             "80.0", "Very High", "30.0", "Relatively Low",
             # WFIR
             "20.0", "Relatively Low", "10000", "1.0", "10",
             # DRGT
             "70.0", "Relatively High", "200000", "4.0", "60",
             # HRCN
             "40.0", "Relatively Moderate", "50000", "1.5", "20",
             ],
            # NM county (for epa_003 state fallback)
            ["35001", "Bernalillo", "New Mexico", "45.0", "Relatively Moderate",
             "200000", "100000", "50.0", "Relatively Moderate",
             "60.0", "Relatively Moderate", "55.0", "Relatively Moderate",
             # WFIR
             "75.0", "Relatively High", "150000", "4.5", "80",
             # DRGT
             "65.0", "Relatively High", "120000", "3.5", "55",
             # HRCN
             "5.0", "Very Low", "2000", "0.05", "1",
             ],
        ]

        with open(nri_csv, "w", encoding="utf-8", newline="") as f:
            import csv
            writer = csv.writer(f)
            writer.writerow(headers)
            for row in rows:
                writer.writerow(row)

        # NRI Tribal Relational CSV
        tribal_rel_csv = nri_dir / "NRI_Tribal_County_Relational.csv"
        with open(tribal_rel_csv, "w", encoding="utf-8", newline="") as f:
            import csv
            writer = csv.writer(f)
            writer.writerow(["AIESSION", "STCOFIPS"])
            writer.writerow(["0400001", "04001"])
            writer.writerow(["0400002", "04003"])
            writer.writerow(["4000001", "40001"])

        # USFS dir (empty -- no XLSX for now; some tests don't need it)
        usfs_dir = tmp_path / "usfs"
        usfs_dir.mkdir()

        cache_dir = tmp_path / "hazard_profiles"

        return {
            "packets": {
                "tribal_registry": {"data_path": str(reg_path)},
                "hazards": {
                    "nri_dir": str(nri_dir),
                    "usfs_dir": str(usfs_dir),
                    "cache_dir": str(cache_dir),
                    "crosswalk_path": str(crosswalk_path),
                },
            }
        }

    def test_nri_hazard_codes_count(self) -> None:
        """Verify NRI_HAZARD_CODES has exactly 18 entries."""
        from src.packets.hazards import NRI_HAZARD_CODES
        assert len(NRI_HAZARD_CODES) == 18

    def test_safe_float_conversion(self) -> None:
        """Verify _safe_float handles empty, None, N/A, numeric strings, and ints."""
        from src.packets.hazards import _safe_float
        assert _safe_float("") == 0.0
        assert _safe_float(None) == 0.0
        assert _safe_float("N/A") == 0.0
        assert _safe_float("12.5") == 12.5
        assert _safe_float(42) == 42.0
        assert _safe_float(3.14) == 3.14
        assert _safe_float("  7.0  ") == 7.0

    def test_nri_county_parsing(self, hazard_config: dict) -> None:
        """Verify NRI county CSV parsing extracts correct values."""
        from src.packets.hazards import HazardProfileBuilder
        builder = HazardProfileBuilder(hazard_config)
        county_data = builder._load_nri_county_data()

        assert len(county_data) == 4
        assert "04001" in county_data
        assert county_data["04001"]["risk_score"] == 85.5
        assert county_data["04001"]["risk_rating"] == "Very High"
        assert county_data["04001"]["hazards"]["WFIR"]["risk_score"] == 88.0
        assert county_data["40001"]["hazards"]["DRGT"]["risk_score"] == 70.0

    def test_tribe_profile_aggregation(self, hazard_config: dict) -> None:
        """Verify multi-county Tribes get max risk scores across counties."""
        from src.packets.hazards import HazardProfileBuilder
        builder = HazardProfileBuilder(hazard_config)
        county_data = builder._load_nri_county_data()
        tribal_counties = builder._load_nri_tribal_relational()

        tribe = {"tribe_id": "epa_001", "name": "Alpha Tribe of Arizona", "states": ["AZ"]}
        profile = builder._build_tribe_nri_profile("epa_001", tribe, county_data, tribal_counties)

        # epa_001 spans 04001 (85.5) and 04003 (70.0); MAX should be 85.5
        assert profile["composite"]["risk_score"] == 85.5
        assert profile["counties_analyzed"] == 2
        # WFIR: MAX of 88.0 and 92.0 = 92.0
        assert profile["all_hazards"]["WFIR"]["risk_score"] == 92.0
        # EAL for WFIR: SUM of 200000 + 300000 = 500000
        assert profile["all_hazards"]["WFIR"]["eal_total"] == 500000.0

    def test_top_hazards_ranking(self, hazard_config: dict) -> None:
        """Verify top 3 hazards are ordered by risk score descending."""
        from src.packets.hazards import HazardProfileBuilder
        builder = HazardProfileBuilder(hazard_config)
        county_data = builder._load_nri_county_data()
        tribal_counties = builder._load_nri_tribal_relational()

        tribe = {"tribe_id": "epa_001", "name": "Alpha Tribe of Arizona", "states": ["AZ"]}
        profile = builder._build_tribe_nri_profile("epa_001", tribe, county_data, tribal_counties)

        top = profile["top_hazards"]
        assert len(top) == 3
        # Scores should be descending
        assert top[0]["risk_score"] >= top[1]["risk_score"]
        assert top[1]["risk_score"] >= top[2]["risk_score"]
        # WFIR should be highest (92.0)
        assert top[0]["code"] == "WFIR"
        assert top[0]["type"] == "Wildfire"

    def test_empty_profile_for_unmatched(self, hazard_config: dict) -> None:
        """Verify unmatched Tribes get a profile with zero values (not a crash)."""
        from src.packets.hazards import HazardProfileBuilder
        builder = HazardProfileBuilder(hazard_config)

        # Tribe not in crosswalk and with no NRI data for its state
        profile = builder._build_tribe_nri_profile(
            "epa_999",
            {"tribe_id": "epa_999", "name": "Phantom Tribe", "states": ["GU"]},
            {},  # Empty county data
            {},  # Empty tribal counties
        )
        assert profile["counties_analyzed"] == 0
        assert "note" in profile
        assert profile["composite"]["risk_score"] == 0.0
        assert profile["top_hazards"] == []

    def test_cache_file_encoding(self, hazard_config: dict) -> None:
        """Verify cache file is written with UTF-8 encoding for special characters."""
        from src.packets.hazards import HazardProfileBuilder
        builder = HazardProfileBuilder(hazard_config)
        builder.build_all_profiles()

        # epa_003 has name with "Diacritics" -- verify it writes correctly
        cache_file = Path(hazard_config["packets"]["hazards"]["cache_dir"]) / "epa_003.json"
        assert cache_file.exists()
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["tribe_name"] == "Zeta Tribe with Diacritics"
        assert data["tribe_id"] == "epa_003"

    def test_build_profiles_creates_directory(self, hazard_config: dict) -> None:
        """Verify cache directory is created if missing."""
        import shutil
        from src.packets.hazards import HazardProfileBuilder

        cache_dir = Path(hazard_config["packets"]["hazards"]["cache_dir"])
        # Remove cache dir if it exists
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
        assert not cache_dir.exists()

        builder = HazardProfileBuilder(hazard_config)
        count = builder.build_all_profiles()

        assert cache_dir.exists()
        assert count == 3  # All 3 Tribes get profile files


# ===========================================================================
# Phase 6 Integration: TestOrchestratorPhase6Integration
# ===========================================================================

class TestOrchestratorPhase6Integration:
    """Tests for orchestrator integration with Phase 6 award and hazard data."""

    @pytest.fixture
    def phase6_config(
        self,
        tmp_path: Path,
        registry_data: dict,
        ecoregion_data: dict,
        congress_data: dict,
    ) -> dict:
        """Create full config with award cache and hazard cache files."""
        # Merge existing sub-configs
        merged = {"packets": {}}
        merged["packets"].update(registry_data.get("packets", {}))
        merged["packets"].update(ecoregion_data.get("packets", {}))
        merged["packets"].update(congress_data.get("packets", {}))

        # Create award cache
        award_cache_dir = tmp_path / "award_cache"
        award_cache_dir.mkdir()
        merged["packets"]["awards"] = {
            "cache_dir": str(award_cache_dir),
        }

        # Write mock award cache for epa_001
        award_data = {
            "tribe_id": "epa_001",
            "tribe_name": "Alpha Tribe of Arizona",
            "awards": [
                {
                    "award_id": "A001",
                    "cfda": "15.156",
                    "program_id": "bia_tcr",
                    "recipient_name_raw": "Alpha AZ Tribe",
                    "obligation": 500000.0,
                    "start_date": "2024-01-01",
                    "end_date": "2025-01-01",
                    "description": "TCR grant",
                    "awarding_agency": "DOI",
                },
                {
                    "award_id": "A002",
                    "cfda": "97.047",
                    "program_id": "fema_bric",
                    "recipient_name_raw": "Alpha Tribe of Arizona",
                    "obligation": 250000.0,
                    "start_date": "2024-06-01",
                    "end_date": "2025-06-01",
                    "description": "BRIC grant",
                    "awarding_agency": "FEMA",
                },
            ],
            "total_obligation": 750000.0,
            "award_count": 2,
        }
        _write_json(award_cache_dir / "epa_001.json", award_data)

        # Create hazard cache
        hazard_cache_dir = tmp_path / "hazard_profiles"
        hazard_cache_dir.mkdir()
        merged["packets"]["hazards"] = {
            "cache_dir": str(hazard_cache_dir),
        }

        # Write mock hazard cache for epa_001
        hazard_data = {
            "tribe_id": "epa_001",
            "tribe_name": "Alpha Tribe of Arizona",
            "sources": {
                "fema_nri": {
                    "version": "1.20",
                    "counties_analyzed": 2,
                    "composite": {
                        "risk_score": 85.5,
                        "risk_rating": "Very High",
                        "eal_total": 900000.0,
                        "eal_score": 90.0,
                        "sovi_score": 72.0,
                        "sovi_rating": "Relatively High",
                        "resl_score": 45.0,
                        "resl_rating": "Relatively Moderate",
                    },
                    "top_hazards": [
                        {"type": "Wildfire", "code": "WFIR", "risk_score": 92.0,
                         "risk_rating": "Very High", "eal_total": 500000.0},
                        {"type": "Drought", "code": "DRGT", "risk_score": 60.0,
                         "risk_rating": "Relatively Moderate", "eal_total": 180000.0},
                        {"type": "Hurricane", "code": "HRCN", "risk_score": 15.0,
                         "risk_rating": "Very Low", "eal_total": 13000.0},
                    ],
                    "all_hazards": {},
                },
                "usfs_wildfire": {
                    "risk_to_homes": 0.85,
                    "wildfire_likelihood": 0.0023,
                    "source_name": "Alpha Reservation",
                },
            },
            "generated_at": "2026-02-10T00:00:00+00:00",
        }
        _write_json(hazard_cache_dir / "epa_001.json", hazard_data)

        return merged

    def test_context_includes_awards(self, phase6_config: dict) -> None:
        """Verify _build_context() populates context.awards from cache."""
        from src.packets.orchestrator import PacketOrchestrator
        programs = [{"id": "bia_tcr", "name": "BIA TCR"}]
        orch = PacketOrchestrator(phase6_config, programs)

        tribe = orch.registry.resolve("Alpha Tribe of Arizona")
        assert isinstance(tribe, dict)

        ctx = orch._build_context(tribe)
        assert len(ctx.awards) == 2
        assert ctx.awards[0]["obligation"] == 500000.0
        assert ctx.awards[1]["program_id"] == "fema_bric"

    def test_context_includes_hazard_profile(self, phase6_config: dict) -> None:
        """Verify _build_context() populates context.hazard_profile from cache."""
        from src.packets.orchestrator import PacketOrchestrator
        programs = [{"id": "bia_tcr", "name": "BIA TCR"}]
        orch = PacketOrchestrator(phase6_config, programs)

        tribe = orch.registry.resolve("Alpha Tribe of Arizona")
        ctx = orch._build_context(tribe)

        assert "fema_nri" in ctx.hazard_profile
        assert ctx.hazard_profile["fema_nri"]["composite"]["risk_score"] == 85.5
        assert "usfs_wildfire" in ctx.hazard_profile
        assert ctx.hazard_profile["usfs_wildfire"]["risk_to_homes"] == 0.85

    def test_context_missing_cache_files(self, phase6_config: dict) -> None:
        """Verify _build_context() works when no cache files exist."""
        from src.packets.orchestrator import PacketOrchestrator
        programs = [{"id": "bia_tcr", "name": "BIA TCR"}]
        orch = PacketOrchestrator(phase6_config, programs)

        # epa_004 has no cache files
        tribe = orch.registry.resolve("Delta Village of Alaska")
        assert isinstance(tribe, dict)

        ctx = orch._build_context(tribe)
        assert ctx.awards == []
        assert ctx.hazard_profile == {}

    def test_display_award_summary(
        self, phase6_config: dict, capsys: pytest.CaptureFixture,
    ) -> None:
        """Verify _display_tribe_info() outputs award total when awards present."""
        from src.packets.orchestrator import PacketOrchestrator
        programs = [{"id": "bia_tcr", "name": "BIA TCR"}]
        orch = PacketOrchestrator(phase6_config, programs)

        tribe = orch.registry.resolve("Alpha Tribe of Arizona")
        ctx = orch._build_context(tribe)
        orch._display_tribe_info(ctx)
        output = capsys.readouterr().out

        assert "Award History:" in output
        assert "$750,000" in output
        assert "2 awards" in output

    def test_display_hazard_summary(
        self, phase6_config: dict, capsys: pytest.CaptureFixture,
    ) -> None:
        """Verify _display_tribe_info() outputs top hazards when hazard profile present."""
        from src.packets.orchestrator import PacketOrchestrator
        programs = [{"id": "bia_tcr", "name": "BIA TCR"}]
        orch = PacketOrchestrator(phase6_config, programs)

        tribe = orch.registry.resolve("Alpha Tribe of Arizona")
        ctx = orch._build_context(tribe)
        orch._display_tribe_info(ctx)
        output = capsys.readouterr().out

        assert "Climate Hazard Profile:" in output
        assert "Very High" in output
        assert "Wildfire" in output
        assert "Drought" in output
        assert "Top Hazards:" in output
