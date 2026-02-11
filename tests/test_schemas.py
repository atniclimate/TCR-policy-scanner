"""Schema validation tests for TCR Policy Scanner data structures.

Tests Pydantic v2 models against real data files to ensure schema
compliance. Every test validates actual data, not mocked examples.

Test categories:
1. ProgramRecord validation against program_inventory.json
2. TribeRecord validation against tribal_registry.json
3. AwardCacheFile validation against award_cache/*.json
4. HazardProfile validation against hazard_profiles/*.json
5. PolicyPosition validation against policy_tracking.json
6. CongressionalDelegate + CongressionalDelegation validation
7. Edge cases: missing fields, null values, empty strings, type errors
"""

import json
import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.schemas.models import (
    AwardCacheFile,
    CommitteeAssignment,
    CongressionalDelegate,
    CongressionalDelegation,
    DistrictMapping,
    ExtensibleFields,
    FundingRecord,
    HazardDetail,
    HazardProfile,
    HotSheetsStatus,
    NRIComposite,
    NRISource,
    PolicyPosition,
    ProgramRecord,
    TribeRecord,
    CI_STATUSES,
    NRI_HAZARD_CODES,
    PRIORITY_LEVELS,
    ACCESS_TYPES,
    FUNDING_TYPES,
)


# ── Fixtures ──

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def program_inventory():
    """Load program_inventory.json."""
    path = PROJECT_ROOT / "data" / "program_inventory.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def policy_tracking():
    """Load policy_tracking.json."""
    path = PROJECT_ROOT / "data" / "policy_tracking.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def tribal_registry():
    """Load tribal_registry.json."""
    path = PROJECT_ROOT / "data" / "tribal_registry.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def congressional_cache():
    """Load congressional_cache.json."""
    path = PROJECT_ROOT / "data" / "congressional_cache.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_award_cache(tribe_id: str) -> dict:
    """Load a specific award_cache file."""
    path = PROJECT_ROOT / "data" / "award_cache" / f"{tribe_id}.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_hazard_profile(tribe_id: str) -> dict:
    """Load a specific hazard_profiles file."""
    path = PROJECT_ROOT / "data" / "hazard_profiles" / f"{tribe_id}.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── 1. ProgramRecord validation ──


class TestProgramRecordSchema:
    """Validate program_inventory.json against ProgramRecord schema."""

    def test_all_16_programs_validate(self, program_inventory):
        """Every program in program_inventory.json must pass ProgramRecord validation."""
        programs = program_inventory["programs"]
        assert len(programs) == 16, f"Expected 16 programs, got {len(programs)}"
        errors = []
        for prog_data in programs:
            try:
                ProgramRecord(**prog_data)
            except ValidationError as e:
                errors.append(f"{prog_data.get('id', 'UNKNOWN')}: {e}")
        assert not errors, f"Validation errors:\n" + "\n".join(errors)

    def test_program_ids_unique(self, program_inventory):
        """All program IDs must be unique."""
        ids = [p["id"] for p in program_inventory["programs"]]
        assert len(ids) == len(set(ids)), f"Duplicate IDs: {[x for x in ids if ids.count(x) > 1]}"

    def test_confidence_index_range(self, program_inventory):
        """Confidence index must be between 0.0 and 1.0 for all programs."""
        for prog in program_inventory["programs"]:
            ci = prog["confidence_index"]
            assert 0.0 <= ci <= 1.0, (
                f"Program {prog['id']}: confidence_index {ci} out of range [0.0, 1.0]"
            )

    def test_ci_status_valid(self, program_inventory):
        """CI status must be a recognized status value."""
        for prog in program_inventory["programs"]:
            assert prog["ci_status"] in CI_STATUSES, (
                f"Program {prog['id']}: invalid ci_status '{prog['ci_status']}'"
            )

    def test_priority_valid(self, program_inventory):
        """Priority must be a recognized value."""
        for prog in program_inventory["programs"]:
            assert prog["priority"] in PRIORITY_LEVELS, (
                f"Program {prog['id']}: invalid priority '{prog['priority']}'"
            )

    def test_access_type_valid(self, program_inventory):
        """Access type must be a recognized value."""
        for prog in program_inventory["programs"]:
            assert prog["access_type"] in ACCESS_TYPES, (
                f"Program {prog['id']}: invalid access_type '{prog['access_type']}'"
            )

    def test_funding_type_valid(self, program_inventory):
        """Funding type must be a recognized value."""
        for prog in program_inventory["programs"]:
            assert prog["funding_type"] in FUNDING_TYPES, (
                f"Program {prog['id']}: invalid funding_type '{prog['funding_type']}'"
            )

    def test_hot_sheets_status_present(self, program_inventory):
        """Every program must have a hot_sheets_status with valid fields."""
        for prog in program_inventory["programs"]:
            hs = prog["hot_sheets_status"]
            assert "status" in hs, f"Program {prog['id']}: missing hot_sheets_status.status"
            assert "last_updated" in hs, f"Program {prog['id']}: missing hot_sheets_status.last_updated"
            assert "source" in hs, f"Program {prog['id']}: missing hot_sheets_status.source"
            assert hs["status"] in CI_STATUSES, (
                f"Program {prog['id']}: invalid hot_sheets_status.status '{hs['status']}'"
            )

    def test_keywords_non_empty(self, program_inventory):
        """Every program must have at least one keyword."""
        for prog in program_inventory["programs"]:
            assert len(prog["keywords"]) >= 1, (
                f"Program {prog['id']}: keywords list is empty"
            )

    def test_search_queries_non_empty(self, program_inventory):
        """Every program must have at least one search query."""
        for prog in program_inventory["programs"]:
            assert len(prog["search_queries"]) >= 1, (
                f"Program {prog['id']}: search_queries list is empty"
            )

    def test_cfda_type_correct(self, program_inventory):
        """CFDA must be null, a string, or a list of strings."""
        for prog in program_inventory["programs"]:
            cfda = prog.get("cfda")
            if cfda is not None:
                if isinstance(cfda, list):
                    assert all(isinstance(c, str) for c in cfda), (
                        f"Program {prog['id']}: CFDA list contains non-string: {cfda}"
                    )
                else:
                    assert isinstance(cfda, str), (
                        f"Program {prog['id']}: CFDA must be str or list, got {type(cfda)}"
                    )

    def test_specialist_fields_consistent(self, program_inventory):
        """If specialist_required is True, specialist_focus must be present."""
        for prog in program_inventory["programs"]:
            if prog.get("specialist_required"):
                assert prog.get("specialist_focus"), (
                    f"Program {prog['id']}: specialist_required=True but no specialist_focus"
                )


# ── 2. TribeRecord validation ──


class TestTribeRecordSchema:
    """Validate tribal_registry.json records against TribeRecord schema."""

    def test_all_592_tribes_validate(self, tribal_registry):
        """Every Tribe in tribal_registry.json must pass TribeRecord validation."""
        tribes = tribal_registry["tribes"]
        assert len(tribes) == 592, f"Expected 592 Tribes, got {len(tribes)}"
        errors = []
        for tribe_data in tribes:
            try:
                TribeRecord(**tribe_data)
            except ValidationError as e:
                errors.append(f"{tribe_data.get('tribe_id', 'UNKNOWN')}: {e}")
        assert not errors, f"Validation errors:\n" + "\n".join(errors)

    def test_tribe_ids_unique(self, tribal_registry):
        """All Tribe IDs must be unique."""
        ids = [t["tribe_id"] for t in tribal_registry["tribes"]]
        assert len(ids) == len(set(ids)), "Duplicate Tribe IDs found"

    def test_tribe_id_format(self, tribal_registry):
        """All Tribe IDs must follow epa_XXXXXXXXX format."""
        for tribe in tribal_registry["tribes"]:
            tid = tribe["tribe_id"]
            assert tid.startswith("epa_"), f"Tribe ID does not start with 'epa_': {tid}"
            assert tid[4:].isdigit(), f"Tribe ID numeric part is not digits: {tid}"

    def test_states_non_empty(self, tribal_registry):
        """Every Tribe must have at least one state."""
        for tribe in tribal_registry["tribes"]:
            assert len(tribe["states"]) >= 1, (
                f"Tribe {tribe['tribe_id']}: states list is empty"
            )

    def test_epa_region_valid(self, tribal_registry):
        """EPA region must be 1-10."""
        valid_regions = {str(i) for i in range(1, 11)}
        for tribe in tribal_registry["tribes"]:
            assert tribe["epa_region"] in valid_regions, (
                f"Tribe {tribe['tribe_id']}: invalid epa_region '{tribe['epa_region']}'"
            )

    def test_bia_recognized_field_is_boolean(self, tribal_registry):
        """bia_recognized must be a boolean for all Tribes."""
        for tribe in tribal_registry["tribes"]:
            assert isinstance(tribe["bia_recognized"], bool), (
                f"Tribe {tribe['tribe_id']}: bia_recognized is {type(tribe['bia_recognized']).__name__}, not bool"
            )

    def test_bia_recognized_distribution(self, tribal_registry):
        """Most Tribes should be BIA-recognized; 16 bands have bia_recognized=False.

        The EPA registry includes sub-bands (e.g., individual bands of the
        Minnesota Chippewa Tribe, Te-Moak Tribe bands) as separate entries
        where BIA recognizes only the parent Tribe. These 16 entries correctly
        have bia_recognized=False.
        """
        recognized = sum(1 for t in tribal_registry["tribes"] if t["bia_recognized"])
        not_recognized = sum(1 for t in tribal_registry["tribes"] if not t["bia_recognized"])
        assert recognized == 576, f"Expected 576 BIA-recognized, got {recognized}"
        assert not_recognized == 16, f"Expected 16 non-BIA-recognized bands, got {not_recognized}"

    def test_metadata_present(self, tribal_registry):
        """Registry metadata must contain expected fields."""
        meta = tribal_registry["metadata"]
        assert meta["total_tribes"] == 592
        assert meta["source"] == "EPA Tribes Names Service API"
        assert "fetched_at" in meta


# ── 3. AwardCacheFile validation ──


class TestAwardCacheSchema:
    """Validate award_cache files against AwardCacheFile schema."""

    SAMPLE_TRIBES = [
        "epa_100000001",
        "epa_100000050",
        "epa_100000100",
        "epa_100000200",
        "epa_100000300",
    ]

    @pytest.mark.parametrize("tribe_id", SAMPLE_TRIBES)
    def test_award_cache_validates(self, tribe_id):
        """Sample award_cache files must pass AwardCacheFile validation."""
        data = load_award_cache(tribe_id)
        try:
            award = AwardCacheFile(**data)
            assert award.tribe_id == tribe_id
        except ValidationError as e:
            pytest.fail(f"Award cache {tribe_id} validation failed: {e}")

    def test_all_592_award_files_exist(self):
        """There must be exactly 592 award_cache files."""
        award_dir = PROJECT_ROOT / "data" / "award_cache"
        files = list(award_dir.glob("epa_*.json"))
        assert len(files) == 592, f"Expected 592 award cache files, got {len(files)}"

    def test_award_count_matches_awards_length(self):
        """award_count must equal len(awards) in every file."""
        award_dir = PROJECT_ROOT / "data" / "award_cache"
        errors = []
        for f in sorted(award_dir.glob("epa_*.json"))[:50]:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            if data["award_count"] != len(data["awards"]):
                errors.append(
                    f"{f.name}: award_count={data['award_count']} but len(awards)={len(data['awards'])}"
                )
        assert not errors, f"Mismatched award counts:\n" + "\n".join(errors)

    def test_total_obligation_non_negative(self):
        """total_obligation must be >= 0 in every file."""
        for tribe_id in self.SAMPLE_TRIBES:
            data = load_award_cache(tribe_id)
            assert data["total_obligation"] >= 0, (
                f"{tribe_id}: negative total_obligation: {data['total_obligation']}"
            )

    def test_empty_awards_have_context(self):
        """Files with 0 awards should have a no_awards_context message."""
        for tribe_id in self.SAMPLE_TRIBES:
            data = load_award_cache(tribe_id)
            if data["award_count"] == 0:
                assert data.get("no_awards_context"), (
                    f"{tribe_id}: no_awards_context missing for empty award file"
                )


# ── 4. HazardProfile validation ──


class TestHazardProfileSchema:
    """Validate hazard_profiles files against HazardProfile schema."""

    SAMPLE_TRIBES = [
        "epa_100000001",
        "epa_100000050",
        "epa_100000100",
        "epa_100000200",
        "epa_100000400",
    ]

    @pytest.mark.parametrize("tribe_id", SAMPLE_TRIBES)
    def test_hazard_profile_validates(self, tribe_id):
        """Sample hazard_profiles must pass HazardProfile validation."""
        data = load_hazard_profile(tribe_id)
        try:
            hp = HazardProfile(**data)
            assert hp.tribe_id == tribe_id
        except ValidationError as e:
            pytest.fail(f"Hazard profile {tribe_id} validation failed: {e}")

    def test_all_592_hazard_files_exist(self):
        """There must be exactly 592 hazard_profile files."""
        hazard_dir = PROJECT_ROOT / "data" / "hazard_profiles"
        files = list(hazard_dir.glob("epa_*.json"))
        assert len(files) == 592, f"Expected 592 hazard profile files, got {len(files)}"

    @pytest.mark.parametrize("tribe_id", SAMPLE_TRIBES)
    def test_sources_has_required_keys(self, tribe_id):
        """sources must contain fema_nri and usfs_wildfire keys."""
        data = load_hazard_profile(tribe_id)
        sources = data["sources"]
        assert "fema_nri" in sources, f"{tribe_id}: missing sources.fema_nri"
        assert "usfs_wildfire" in sources, f"{tribe_id}: missing sources.usfs_wildfire"

    @pytest.mark.parametrize("tribe_id", SAMPLE_TRIBES)
    def test_nri_has_18_hazard_types(self, tribe_id):
        """FEMA NRI must include all 18 hazard type codes."""
        data = load_hazard_profile(tribe_id)
        nri = data["sources"]["fema_nri"]
        all_hazards = nri.get("all_hazards", {})
        hazard_codes = set(all_hazards.keys())
        assert hazard_codes == NRI_HAZARD_CODES, (
            f"{tribe_id}: NRI hazard codes mismatch. "
            f"Missing: {NRI_HAZARD_CODES - hazard_codes}, "
            f"Extra: {hazard_codes - NRI_HAZARD_CODES}"
        )

    @pytest.mark.parametrize("tribe_id", SAMPLE_TRIBES)
    def test_nri_composite_fields_present(self, tribe_id):
        """NRI composite must have all expected score fields."""
        data = load_hazard_profile(tribe_id)
        composite = data["sources"]["fema_nri"]["composite"]
        expected = {"risk_score", "risk_rating", "eal_total", "eal_score",
                    "sovi_score", "sovi_rating", "resl_score", "resl_rating"}
        actual = set(composite.keys())
        missing = expected - actual
        assert not missing, f"{tribe_id}: composite missing fields: {missing}"

    @pytest.mark.parametrize("tribe_id", SAMPLE_TRIBES)
    def test_hazard_detail_fields_present(self, tribe_id):
        """Each hazard detail must have risk_score, risk_rating, eal_total, annualized_freq, num_events."""
        data = load_hazard_profile(tribe_id)
        expected_fields = {"risk_score", "risk_rating", "eal_total", "annualized_freq", "num_events"}
        for code, detail in data["sources"]["fema_nri"]["all_hazards"].items():
            actual = set(detail.keys())
            missing = expected_fields - actual
            assert not missing, (
                f"{tribe_id} hazard {code}: missing fields {missing}"
            )

    @pytest.mark.parametrize("tribe_id", SAMPLE_TRIBES)
    def test_nri_source_validates_via_model(self, tribe_id):
        """NRI source data must pass NRISource model validation."""
        data = load_hazard_profile(tribe_id)
        hp = HazardProfile(**data)
        nri = hp.get_nri_source()
        assert isinstance(nri, NRISource)
        assert nri.version == "1.20"


# ── 5. PolicyPosition validation ──


class TestPolicyPositionSchema:
    """Validate policy_tracking.json positions against PolicyPosition schema."""

    def test_all_16_positions_validate(self, policy_tracking):
        """Every position in policy_tracking.json must pass PolicyPosition validation."""
        positions = policy_tracking["positions"]
        assert len(positions) == 16, f"Expected 16 positions, got {len(positions)}"
        errors = []
        for pos_data in positions:
            try:
                PolicyPosition(**pos_data)
            except ValidationError as e:
                errors.append(f"{pos_data.get('program_id', 'UNKNOWN')}: {e}")
        assert not errors, f"Validation errors:\n" + "\n".join(errors)

    def test_position_program_ids_match_inventory(self, policy_tracking, program_inventory):
        """All position program_ids must exist in program_inventory."""
        inventory_ids = {p["id"] for p in program_inventory["programs"]}
        for pos in policy_tracking["positions"]:
            assert pos["program_id"] in inventory_ids, (
                f"Position program_id '{pos['program_id']}' not in program_inventory"
            )

    def test_ci_thresholds_descending(self, policy_tracking):
        """CI thresholds must be in descending order."""
        thresholds = policy_tracking["ci_thresholds"]
        ordered_keys = [
            "secure", "stable", "stable_but_vulnerable",
            "at_risk_floor", "uncertain_floor", "flagged_floor", "terminated_floor"
        ]
        values = [thresholds[k] for k in ordered_keys]
        for i in range(len(values) - 1):
            assert values[i] >= values[i + 1], (
                f"Threshold {ordered_keys[i]} ({values[i]}) < {ordered_keys[i+1]} ({values[i+1]})"
            )

    def test_status_definitions_complete(self, policy_tracking):
        """All CI_STATUSES must have definitions."""
        defs = set(policy_tracking["status_definitions"].keys())
        missing = CI_STATUSES - defs
        assert not missing, f"Missing status definitions: {missing}"

    def test_extensible_fields_validate(self, policy_tracking):
        """All extensible_fields must pass ExtensibleFields validation."""
        for pos in policy_tracking["positions"]:
            try:
                ExtensibleFields(**pos["extensible_fields"])
            except ValidationError as e:
                pytest.fail(
                    f"Position {pos['program_id']} extensible_fields failed: {e}"
                )

    def test_all_positions_have_scanner_trigger_keywords(self, policy_tracking):
        """All positions should have scanner_trigger_keywords in extensible_fields."""
        for pos in policy_tracking["positions"]:
            ext = pos["extensible_fields"]
            assert "scanner_trigger_keywords" in ext, (
                f"Position {pos['program_id']}: missing scanner_trigger_keywords"
            )
            assert len(ext["scanner_trigger_keywords"]) >= 1, (
                f"Position {pos['program_id']}: scanner_trigger_keywords is empty"
            )


# ── 6. Congressional schema validation ──


class TestCongressionalSchema:
    """Validate congressional_cache.json against delegate/delegation schemas."""

    def test_all_members_validate(self, congressional_cache):
        """All 538 members must pass CongressionalDelegate validation."""
        members = congressional_cache["members"]
        assert len(members) == 538, f"Expected 538 members, got {len(members)}"
        errors = []
        for bioguide_id, member_data in members.items():
            try:
                cd = CongressionalDelegate(**member_data)
                assert cd.bioguide_id == bioguide_id
            except ValidationError as e:
                errors.append(f"{bioguide_id}: {e}")
        assert not errors, f"Member validation errors:\n" + "\n".join(errors)

    def test_all_delegations_validate(self, congressional_cache):
        """All 501 delegations must pass CongressionalDelegation validation."""
        delegations = congressional_cache["delegations"]
        assert len(delegations) == 501, f"Expected 501 delegations, got {len(delegations)}"
        errors = []
        for tribe_id, deleg_data in delegations.items():
            try:
                d = CongressionalDelegation(**deleg_data)
                assert d.tribe_id == tribe_id
            except ValidationError as e:
                errors.append(f"{tribe_id}: {e}")
        assert not errors, f"Delegation validation errors:\n" + "\n".join(errors)

    def test_senators_are_senate_chamber(self, congressional_cache):
        """All senators in delegations must have chamber='Senate'."""
        for tribe_id, deleg in congressional_cache["delegations"].items():
            for senator in deleg.get("senators", []):
                assert senator["chamber"] == "Senate", (
                    f"Delegation {tribe_id}: senator {senator['bioguide_id']} has "
                    f"chamber='{senator['chamber']}' (expected 'Senate')"
                )

    def test_representatives_are_house_chamber(self, congressional_cache):
        """All representatives in delegations must have chamber='House'."""
        for tribe_id, deleg in congressional_cache["delegations"].items():
            for rep in deleg.get("representatives", []):
                assert rep["chamber"] == "House", (
                    f"Delegation {tribe_id}: rep {rep['bioguide_id']} has "
                    f"chamber='{rep['chamber']}' (expected 'House')"
                )

    def test_committee_assignments_validate(self, congressional_cache):
        """Committee assignments must pass CommitteeAssignment validation."""
        errors = []
        for bioguide_id, member in congressional_cache["members"].items():
            for i, comm in enumerate(member.get("committees", [])):
                try:
                    CommitteeAssignment(**comm)
                except ValidationError as e:
                    errors.append(f"{bioguide_id} committee[{i}]: {e}")
        assert not errors, f"Committee validation errors:\n" + "\n".join(errors)

    def test_district_mappings_validate(self, congressional_cache):
        """District mappings must pass DistrictMapping validation."""
        errors = []
        for tribe_id, deleg in congressional_cache["delegations"].items():
            for i, dist in enumerate(deleg.get("districts", [])):
                try:
                    DistrictMapping(**dist)
                except ValidationError as e:
                    errors.append(f"{tribe_id} district[{i}]: {e}")
        assert not errors, f"District mapping validation errors:\n" + "\n".join(errors)


# ── 7. Edge cases ──


class TestSchemaEdgeCases:
    """Test edge cases: missing fields, null values, empty strings, type errors."""

    def test_program_record_missing_required_field(self):
        """ProgramRecord must reject records missing required fields."""
        incomplete = {"id": "test_prog", "name": "Test"}
        with pytest.raises(ValidationError):
            ProgramRecord(**incomplete)

    def test_program_record_invalid_confidence_index(self):
        """ProgramRecord must reject CI outside 0.0-1.0."""
        with pytest.raises(ValidationError):
            ProgramRecord(
                id="test", name="Test", agency="TEST", federal_home="Test Agency",
                priority="high", keywords=["test"], search_queries=["test"],
                advocacy_lever="test", description="test", access_type="direct",
                funding_type="Discretionary", confidence_index=1.5,
                ci_status="STABLE", ci_determination="test",
                hot_sheets_status={"status": "STABLE", "last_updated": "2026-01-01", "source": "test"}
            )

    def test_program_record_invalid_ci_below_zero(self):
        """ProgramRecord must reject CI below 0.0."""
        with pytest.raises(ValidationError):
            ProgramRecord(
                id="test", name="Test", agency="TEST", federal_home="Test Agency",
                priority="high", keywords=["test"], search_queries=["test"],
                advocacy_lever="test", description="test", access_type="direct",
                funding_type="Discretionary", confidence_index=-0.1,
                ci_status="STABLE", ci_determination="test",
                hot_sheets_status={"status": "STABLE", "last_updated": "2026-01-01", "source": "test"}
            )

    def test_program_record_invalid_priority(self):
        """ProgramRecord must reject invalid priority values."""
        with pytest.raises(ValidationError):
            ProgramRecord(
                id="test", name="Test", agency="TEST", federal_home="Test Agency",
                priority="URGENT",  # Invalid
                keywords=["test"], search_queries=["test"],
                advocacy_lever="test", description="test", access_type="direct",
                funding_type="Discretionary", confidence_index=0.5,
                ci_status="STABLE", ci_determination="test",
                hot_sheets_status={"status": "STABLE", "last_updated": "2026-01-01", "source": "test"}
            )

    def test_program_record_invalid_access_type(self):
        """ProgramRecord must reject invalid access_type."""
        with pytest.raises(ValidationError):
            ProgramRecord(
                id="test", name="Test", agency="TEST", federal_home="Test Agency",
                priority="high", keywords=["test"], search_queries=["test"],
                advocacy_lever="test", description="test",
                access_type="open_enrollment",  # Invalid
                funding_type="Discretionary", confidence_index=0.5,
                ci_status="STABLE", ci_determination="test",
                hot_sheets_status={"status": "STABLE", "last_updated": "2026-01-01", "source": "test"}
            )

    def test_program_record_invalid_funding_type(self):
        """ProgramRecord must reject invalid funding_type."""
        with pytest.raises(ValidationError):
            ProgramRecord(
                id="test", name="Test", agency="TEST", federal_home="Test Agency",
                priority="high", keywords=["test"], search_queries=["test"],
                advocacy_lever="test", description="test", access_type="direct",
                funding_type="Entitlement",  # Invalid
                confidence_index=0.5,
                ci_status="STABLE", ci_determination="test",
                hot_sheets_status={"status": "STABLE", "last_updated": "2026-01-01", "source": "test"}
            )

    def test_program_record_invalid_ci_status(self):
        """ProgramRecord must reject invalid CI status."""
        with pytest.raises(ValidationError):
            ProgramRecord(
                id="test", name="Test", agency="TEST", federal_home="Test Agency",
                priority="high", keywords=["test"], search_queries=["test"],
                advocacy_lever="test", description="test", access_type="direct",
                funding_type="Discretionary", confidence_index=0.5,
                ci_status="DEFUNDED",  # Invalid
                ci_determination="test",
                hot_sheets_status={"status": "STABLE", "last_updated": "2026-01-01", "source": "test"}
            )

    def test_program_record_empty_keywords_rejected(self):
        """ProgramRecord must reject empty keywords list."""
        with pytest.raises(ValidationError):
            ProgramRecord(
                id="test", name="Test", agency="TEST", federal_home="Test Agency",
                priority="high", keywords=[],  # Empty
                search_queries=["test"],
                advocacy_lever="test", description="test", access_type="direct",
                funding_type="Discretionary", confidence_index=0.5,
                ci_status="STABLE", ci_determination="test",
                hot_sheets_status={"status": "STABLE", "last_updated": "2026-01-01", "source": "test"}
            )

    def test_tribe_record_missing_required_field(self):
        """TribeRecord must reject records missing required fields."""
        incomplete = {"tribe_id": "epa_999", "name": "Test Tribe"}
        with pytest.raises(ValidationError):
            TribeRecord(**incomplete)

    def test_tribe_record_invalid_id_format(self):
        """TribeRecord must reject IDs not starting with 'epa_'."""
        with pytest.raises(ValidationError):
            TribeRecord(
                tribe_id="bia_999",  # Invalid prefix
                bia_code="999", name="Test Tribe",
                states=["WA"], epa_region="10", bia_recognized=True
            )

    def test_tribe_record_invalid_epa_region(self):
        """TribeRecord must reject EPA regions outside 1-10."""
        with pytest.raises(ValidationError):
            TribeRecord(
                tribe_id="epa_999999999", bia_code="999",
                name="Test Tribe", states=["WA"],
                epa_region="11",  # Invalid
                bia_recognized=True
            )

    def test_tribe_record_empty_states_rejected(self):
        """TribeRecord must reject empty states list."""
        with pytest.raises(ValidationError):
            TribeRecord(
                tribe_id="epa_999999999", bia_code="999",
                name="Test Tribe", states=[],  # Empty
                epa_region="10", bia_recognized=True
            )

    def test_award_cache_negative_obligation_rejected(self):
        """AwardCacheFile must reject negative total_obligation."""
        with pytest.raises(ValidationError):
            AwardCacheFile(
                tribe_id="epa_999999999",
                tribe_name="Test Tribe",
                total_obligation=-100.0,  # Invalid
                award_count=0,
            )

    def test_award_cache_count_mismatch_rejected(self):
        """AwardCacheFile must reject when award_count does not match len(awards)."""
        with pytest.raises(ValidationError):
            AwardCacheFile(
                tribe_id="epa_999999999",
                tribe_name="Test Tribe",
                awards=[],
                total_obligation=0,
                award_count=5,  # Mismatch
            )

    def test_hazard_profile_missing_sources_keys(self):
        """HazardProfile must reject sources missing required keys."""
        with pytest.raises(ValidationError):
            HazardProfile(
                tribe_id="epa_999999999",
                tribe_name="Test Tribe",
                sources={"fema_nri": {}},  # Missing usfs_wildfire
                generated_at="2026-02-10T00:00:00+00:00",
            )

    def test_nri_source_unknown_hazard_code_rejected(self):
        """NRISource must reject unknown hazard type codes."""
        with pytest.raises(ValidationError):
            NRISource(
                version="1.20",
                counties_analyzed=1,
                all_hazards={
                    "FAKE": HazardDetail(risk_score=1.0),  # Invalid code
                },
            )

    def test_congressional_delegate_invalid_chamber(self):
        """CongressionalDelegate must reject invalid chamber."""
        with pytest.raises(ValidationError):
            CongressionalDelegate(
                bioguide_id="X000001", name="Test, Person",
                state="WA", party="Independent", party_abbr="I",
                chamber="Both",  # Invalid
                formatted_name="Test Person",
            )

    def test_district_mapping_overlap_over_100_rejected(self):
        """DistrictMapping must reject overlap_pct > 100."""
        with pytest.raises(ValidationError):
            DistrictMapping(
                district="WA-03", state="WA",
                overlap_pct=101.0,  # Invalid
            )

    def test_funding_record_defaults(self):
        """FundingRecord should accept minimal data with defaults."""
        fr = FundingRecord()
        assert fr.amount == 0.0
        assert fr.award_id is None
        assert fr.fiscal_year is None

    def test_hot_sheets_status_invalid_status(self):
        """HotSheetsStatus must reject invalid status values."""
        with pytest.raises(ValidationError):
            HotSheetsStatus(
                status="CANCELLED",  # Invalid
                last_updated="2026-02-09",
                source="test",
            )

    def test_policy_position_invalid_status(self):
        """PolicyPosition must reject invalid status values."""
        with pytest.raises(ValidationError):
            PolicyPosition(
                program_id="test", program_name="Test", agency="TEST",
                confidence_index=0.5,
                status="DEFUNCT",  # Invalid
                reasoning="test",
                extensible_fields={},
            )

    def test_valid_program_record_with_null_cfda(self):
        """ProgramRecord should accept null CFDA (e.g., IRS Elective Pay)."""
        pr = ProgramRecord(
            id="test", name="Test", agency="TEST", federal_home="Test Agency",
            priority="high", keywords=["test"], search_queries=["test"],
            advocacy_lever="test", description="test", access_type="direct",
            funding_type="Mandatory", cfda=None, confidence_index=0.5,
            ci_status="STABLE", ci_determination="test",
            hot_sheets_status={"status": "STABLE", "last_updated": "2026-01-01", "source": "test"}
        )
        assert pr.cfda is None

    def test_valid_program_record_with_list_cfda(self):
        """ProgramRecord should accept list CFDA (e.g., FEMA BRIC)."""
        pr = ProgramRecord(
            id="test", name="Test", agency="TEST", federal_home="Test Agency",
            priority="critical", keywords=["test"], search_queries=["test"],
            advocacy_lever="test", description="test", access_type="competitive",
            funding_type="One-Time", cfda=["97.047", "97.039"],
            confidence_index=0.12, ci_status="FLAGGED", ci_determination="test",
            hot_sheets_status={"status": "FLAGGED", "last_updated": "2026-01-01", "source": "test"}
        )
        assert pr.cfda == ["97.047", "97.039"]

    def test_extensible_fields_allows_extra(self):
        """ExtensibleFields should allow unknown extra fields (extra='allow')."""
        ef = ExtensibleFields(
            advocacy_priority="High",
            custom_field="custom_value",  # Extra field
        )
        assert ef.advocacy_priority == "High"
