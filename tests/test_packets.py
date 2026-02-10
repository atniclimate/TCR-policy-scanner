"""Test suite for Phase 5 packet modules.

Covers all five Phase 5 requirements:
  REG-01: TribalRegistry (name resolution, fuzzy search)
  REG-02: EcoregionMapper (state-to-ecoregion classification)
  REG-03: TribePacketContext (dataclass, serialization)
  CONG-01: CongressionalMapper districts
  CONG-02: CongressionalMapper members and committees

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
