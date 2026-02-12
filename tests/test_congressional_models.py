"""Tests for congressional intelligence Pydantic models (Plan 15-01).

Validates BillAction, BillIntelligence, VoteRecord, Legislator, and
CongressionalIntelReport model construction, field validation, defaults,
serialization, and edge cases.

50+ tests covering all congressional models added in Phase 15.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.schemas.models import (
    BILL_TYPE_CODES,
    BillAction,
    BillIntelligence,
    CongressionalIntelReport,
    Legislator,
    VoteRecord,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _valid_bill_action(**overrides) -> dict:
    """Return a valid BillAction dict with optional overrides."""
    data = {
        "action_date": "2025-03-15",
        "text": "Referred to the Committee on Natural Resources.",
        "action_type": "IntroReferral",
        "chamber": "House",
    }
    data.update(overrides)
    return data


def _valid_bill_intelligence(**overrides) -> dict:
    """Return a valid BillIntelligence dict with optional overrides."""
    data = {
        "bill_id": "119-HR-1234",
        "congress": 119,
        "bill_type": "HR",
        "bill_number": 1234,
        "title": "Tribal Climate Resilience Act of 2025",
        "relevance_score": 0.85,
    }
    data.update(overrides)
    return data


def _valid_vote_record(**overrides) -> dict:
    """Return a valid VoteRecord dict with optional overrides."""
    data = {
        "vote_id": "119-H-42",
    }
    data.update(overrides)
    return data


def _valid_legislator(**overrides) -> dict:
    """Return a valid Legislator dict with optional overrides."""
    data = {
        "bioguide_id": "M001153",
        "name": "Lisa Murkowski",
    }
    data.update(overrides)
    return data


def _valid_intel_report(**overrides) -> dict:
    """Return a valid CongressionalIntelReport dict with optional overrides."""
    data = {
        "tribe_id": "epa_100000001",
        "generated_at": "2026-02-12T08:00:00+00:00",
    }
    data.update(overrides)
    return data


# ===========================================================================
# BillAction Tests (~8 tests)
# ===========================================================================


class TestBillAction:
    """Validate BillAction model construction and defaults."""

    def test_valid_construction(self):
        """BillAction with all fields constructs successfully."""
        ba = BillAction(**_valid_bill_action())
        assert ba.action_date == "2025-03-15"
        assert ba.text == "Referred to the Committee on Natural Resources."
        assert ba.action_type == "IntroReferral"
        assert ba.chamber == "House"

    def test_defaults_for_optional_fields(self):
        """BillAction with only required fields uses defaults."""
        ba = BillAction(action_date="2025-06-01", text="Introduced in House.")
        assert ba.action_type == ""
        assert ba.chamber == ""

    def test_missing_action_date_raises(self):
        """BillAction without action_date raises ValidationError."""
        with pytest.raises(ValidationError, match="action_date"):
            BillAction(text="Some action.")

    def test_missing_text_raises(self):
        """BillAction without text raises ValidationError."""
        with pytest.raises(ValidationError, match="text"):
            BillAction(action_date="2025-01-01")

    def test_serialization_roundtrip(self):
        """BillAction serializes to dict and reconstructs."""
        ba = BillAction(**_valid_bill_action())
        d = ba.model_dump()
        ba2 = BillAction(**d)
        assert ba == ba2

    def test_empty_chamber_accepted(self):
        """BillAction with empty chamber string is valid."""
        ba = BillAction(action_date="2025-01-01", text="Action.", chamber="")
        assert ba.chamber == ""

    def test_senate_chamber(self):
        """BillAction with Senate chamber is valid."""
        ba = BillAction(
            action_date="2025-02-20",
            text="Passed Senate.",
            chamber="Senate",
        )
        assert ba.chamber == "Senate"

    def test_floor_action_type(self):
        """BillAction accepts Floor action type."""
        ba = BillAction(
            action_date="2025-05-10",
            text="Passed by recorded vote.",
            action_type="Floor",
            chamber="House",
        )
        assert ba.action_type == "Floor"


# ===========================================================================
# BillIntelligence Tests (~25 tests)
# ===========================================================================


class TestBillIntelligence:
    """Validate BillIntelligence model construction, validators, and edges."""

    def test_valid_construction(self):
        """BillIntelligence with required fields constructs."""
        bi = BillIntelligence(**_valid_bill_intelligence())
        assert bi.bill_id == "119-HR-1234"
        assert bi.congress == 119
        assert bi.bill_type == "HR"
        assert bi.bill_number == 1234
        assert bi.title == "Tribal Climate Resilience Act of 2025"
        assert bi.relevance_score == 0.85

    def test_all_defaults(self):
        """BillIntelligence defaults are applied correctly."""
        bi = BillIntelligence(**_valid_bill_intelligence())
        assert bi.sponsor is None
        assert bi.cosponsors == []
        assert bi.cosponsor_count == 0
        assert bi.actions == []
        assert bi.latest_action is None
        assert bi.committees == []
        assert bi.subjects == []
        assert bi.policy_area == ""
        assert bi.text_url == ""
        assert bi.congress_url == ""
        assert bi.matched_programs == []
        assert bi.update_date == ""
        assert bi.introduced_date == ""

    def test_bill_type_hr_valid(self):
        """HR bill type is accepted."""
        bi = BillIntelligence(**_valid_bill_intelligence(bill_type="HR"))
        assert bi.bill_type == "HR"

    def test_bill_type_s_valid(self):
        """S (Senate) bill type is accepted."""
        bi = BillIntelligence(**_valid_bill_intelligence(bill_type="S"))
        assert bi.bill_type == "S"

    def test_bill_type_hjres_valid(self):
        """HJRES bill type is accepted."""
        bi = BillIntelligence(**_valid_bill_intelligence(bill_type="HJRES"))
        assert bi.bill_type == "HJRES"

    def test_bill_type_sjres_valid(self):
        """SJRES bill type is accepted."""
        bi = BillIntelligence(**_valid_bill_intelligence(bill_type="SJRES"))
        assert bi.bill_type == "SJRES"

    def test_bill_type_hconres_valid(self):
        """HCONRES bill type is accepted."""
        bi = BillIntelligence(**_valid_bill_intelligence(bill_type="HCONRES"))
        assert bi.bill_type == "HCONRES"

    def test_bill_type_sconres_valid(self):
        """SCONRES bill type is accepted."""
        bi = BillIntelligence(**_valid_bill_intelligence(bill_type="SCONRES"))
        assert bi.bill_type == "SCONRES"

    def test_bill_type_hres_valid(self):
        """HRES bill type is accepted."""
        bi = BillIntelligence(**_valid_bill_intelligence(bill_type="HRES"))
        assert bi.bill_type == "HRES"

    def test_bill_type_sres_valid(self):
        """SRES bill type is accepted."""
        bi = BillIntelligence(**_valid_bill_intelligence(bill_type="SRES"))
        assert bi.bill_type == "SRES"

    @pytest.mark.parametrize(
        "bad_type",
        ["hr", "s", "HJ", "CONCURRENT", "EXECUTIVE", "AMENDMENT", ""],
    )
    def test_bill_type_invalid_rejected(self, bad_type):
        """Invalid bill types are rejected."""
        with pytest.raises(ValidationError, match="bill_type"):
            BillIntelligence(**_valid_bill_intelligence(bill_type=bad_type))

    def test_all_valid_bill_types_accepted(self):
        """Every type code in BILL_TYPE_CODES is accepted."""
        for code in BILL_TYPE_CODES:
            bi = BillIntelligence(**_valid_bill_intelligence(bill_type=code))
            assert bi.bill_type == code

    def test_relevance_score_zero(self):
        """Relevance score of 0.0 is valid."""
        bi = BillIntelligence(**_valid_bill_intelligence(relevance_score=0.0))
        assert bi.relevance_score == 0.0

    def test_relevance_score_one(self):
        """Relevance score of 1.0 is valid."""
        bi = BillIntelligence(**_valid_bill_intelligence(relevance_score=1.0))
        assert bi.relevance_score == 1.0

    def test_relevance_score_above_one_rejected(self):
        """Relevance score > 1.0 is rejected."""
        with pytest.raises(ValidationError):
            BillIntelligence(**_valid_bill_intelligence(relevance_score=1.5))

    def test_relevance_score_negative_rejected(self):
        """Negative relevance score is rejected."""
        with pytest.raises(ValidationError):
            BillIntelligence(**_valid_bill_intelligence(relevance_score=-0.1))

    def test_cosponsor_count_nonnegative(self):
        """Cosponsor count must be non-negative."""
        bi = BillIntelligence(
            **_valid_bill_intelligence(cosponsor_count=42)
        )
        assert bi.cosponsor_count == 42

    def test_cosponsor_count_negative_rejected(self):
        """Negative cosponsor count is rejected."""
        with pytest.raises(ValidationError):
            BillIntelligence(
                **_valid_bill_intelligence(cosponsor_count=-1)
            )

    def test_nested_bill_actions(self):
        """BillIntelligence with nested BillAction list validates."""
        actions = [
            _valid_bill_action(text="Introduced."),
            _valid_bill_action(text="Referred to committee."),
        ]
        bi = BillIntelligence(**_valid_bill_intelligence(actions=actions))
        assert len(bi.actions) == 2
        assert all(isinstance(a, BillAction) for a in bi.actions)

    def test_latest_action_as_dict(self):
        """BillIntelligence accepts latest_action as a dict."""
        la = _valid_bill_action(text="Placed on calendar.")
        bi = BillIntelligence(**_valid_bill_intelligence(latest_action=la))
        assert isinstance(bi.latest_action, BillAction)
        assert bi.latest_action.text == "Placed on calendar."

    def test_sponsor_as_dict(self):
        """BillIntelligence accepts sponsor as a dict."""
        sponsor = {
            "bioguide_id": "C001120",
            "name": "Dan Crenshaw",
            "party": "Republican",
            "state": "TX",
        }
        bi = BillIntelligence(**_valid_bill_intelligence(sponsor=sponsor))
        assert bi.sponsor["name"] == "Dan Crenshaw"

    def test_matched_programs_list(self):
        """matched_programs list is stored correctly."""
        programs = ["bia_tcr", "fema_bric", "epa_gap"]
        bi = BillIntelligence(
            **_valid_bill_intelligence(matched_programs=programs)
        )
        assert bi.matched_programs == programs

    def test_serialization_roundtrip(self):
        """BillIntelligence serializes and reconstructs."""
        bi = BillIntelligence(
            **_valid_bill_intelligence(
                actions=[_valid_bill_action()],
                subjects=["Native Americans", "Climate Change"],
                matched_programs=["bia_tcr"],
            )
        )
        d = bi.model_dump()
        bi2 = BillIntelligence(**d)
        assert bi == bi2

    def test_real_world_data_sample(self):
        """Realistic bill data validates correctly."""
        bi = BillIntelligence(
            bill_id="119-HR-5678",
            congress=119,
            bill_type="HR",
            bill_number=5678,
            title="Native American Climate Adaptation and Resilience Act",
            sponsor={
                "bioguide_id": "C001120",
                "name": "Dan Crenshaw",
                "party": "Republican",
                "state": "TX",
            },
            cosponsors=[
                {"bioguide_id": "M001153", "name": "Lisa Murkowski"},
            ],
            cosponsor_count=15,
            actions=[
                BillAction(
                    action_date="2025-01-15",
                    text="Introduced in House.",
                    action_type="IntroReferral",
                    chamber="House",
                ),
                BillAction(
                    action_date="2025-02-20",
                    text="Referred to House Natural Resources Committee.",
                    action_type="Committee",
                    chamber="House",
                ),
            ],
            committees=[
                {"name": "House Committee on Natural Resources"},
            ],
            subjects=["Native Americans", "Environmental Protection"],
            policy_area="Native Americans",
            relevance_score=0.92,
            matched_programs=["bia_tcr", "fema_bric"],
            update_date="2025-02-20",
            introduced_date="2025-01-15",
            congress_url="https://www.congress.gov/bill/119th-congress/house-bill/5678",
        )
        assert bi.congress == 119
        assert len(bi.actions) == 2
        assert bi.matched_programs == ["bia_tcr", "fema_bric"]

    def test_missing_required_bill_id_raises(self):
        """Missing bill_id raises ValidationError."""
        with pytest.raises(ValidationError, match="bill_id"):
            BillIntelligence(
                congress=119,
                bill_type="HR",
                bill_number=100,
                title="Test",
            )

    def test_missing_required_title_raises(self):
        """Missing title raises ValidationError."""
        with pytest.raises(ValidationError, match="title"):
            BillIntelligence(
                bill_id="119-HR-100",
                congress=119,
                bill_type="HR",
                bill_number=100,
            )


# ===========================================================================
# VoteRecord Tests (~5 tests)
# ===========================================================================


class TestVoteRecord:
    """Validate VoteRecord model construction and defaults."""

    def test_valid_construction(self):
        """VoteRecord with all fields constructs."""
        vr = VoteRecord(
            vote_id="119-H-42",
            bill_id="119-HR-1234",
            chamber="House",
            vote_date="2025-05-10",
            result="Passed",
            yea_count=225,
            nay_count=200,
        )
        assert vr.vote_id == "119-H-42"
        assert vr.yea_count == 225

    def test_defaults(self):
        """VoteRecord with only vote_id uses defaults."""
        vr = VoteRecord(**_valid_vote_record())
        assert vr.bill_id == ""
        assert vr.chamber == ""
        assert vr.vote_date == ""
        assert vr.result == ""
        assert vr.yea_count == 0
        assert vr.nay_count == 0

    def test_missing_vote_id_raises(self):
        """VoteRecord without vote_id raises ValidationError."""
        with pytest.raises(ValidationError, match="vote_id"):
            VoteRecord()

    def test_senate_vote(self):
        """VoteRecord for a Senate vote constructs correctly."""
        vr = VoteRecord(
            vote_id="119-S-15",
            bill_id="119-S-567",
            chamber="Senate",
            result="Agreed to",
            yea_count=60,
            nay_count=38,
        )
        assert vr.chamber == "Senate"
        assert vr.result == "Agreed to"

    def test_serialization(self):
        """VoteRecord serializes and reconstructs."""
        vr = VoteRecord(
            vote_id="119-H-99",
            bill_id="119-HR-999",
            chamber="House",
            vote_date="2025-07-04",
            result="Failed",
            yea_count=100,
            nay_count=320,
        )
        d = vr.model_dump()
        vr2 = VoteRecord(**d)
        assert vr == vr2


# ===========================================================================
# Legislator Tests (~5 tests)
# ===========================================================================


class TestLegislator:
    """Validate Legislator model construction and defaults."""

    def test_valid_construction(self):
        """Legislator with all fields constructs."""
        leg = Legislator(
            bioguide_id="M001153",
            name="Lisa Murkowski",
            state="AK",
            party="Republican",
            chamber="Senate",
            committees=[{"name": "Appropriations"}],
            sponsored_bills=["119-S-100"],
            cosponsored_bills=["119-HR-200", "119-S-300"],
        )
        assert leg.bioguide_id == "M001153"
        assert len(leg.cosponsored_bills) == 2

    def test_defaults(self):
        """Legislator with only required fields uses defaults."""
        leg = Legislator(**_valid_legislator())
        assert leg.state == ""
        assert leg.district == ""
        assert leg.party == ""
        assert leg.chamber == ""
        assert leg.committees == []
        assert leg.sponsored_bills == []
        assert leg.cosponsored_bills == []

    def test_missing_bioguide_raises(self):
        """Legislator without bioguide_id raises ValidationError."""
        with pytest.raises(ValidationError, match="bioguide_id"):
            Legislator(name="Test Person")

    def test_missing_name_raises(self):
        """Legislator without name raises ValidationError."""
        with pytest.raises(ValidationError, match="name"):
            Legislator(bioguide_id="T001234")

    def test_committee_list(self):
        """Legislator committee list stores correctly."""
        committees = [
            {"name": "Appropriations", "role": "member"},
            {"name": "Indian Affairs", "role": "chair"},
        ]
        leg = Legislator(
            **_valid_legislator(committees=committees)
        )
        assert len(leg.committees) == 2
        assert leg.committees[1]["role"] == "chair"


# ===========================================================================
# CongressionalIntelReport Tests (~8 tests)
# ===========================================================================


class TestCongressionalIntelReport:
    """Validate CongressionalIntelReport construction and nesting."""

    def test_valid_construction(self):
        """CongressionalIntelReport with required fields constructs."""
        report = CongressionalIntelReport(**_valid_intel_report())
        assert report.tribe_id == "epa_100000001"
        assert report.generated_at == "2026-02-12T08:00:00+00:00"

    def test_defaults(self):
        """CongressionalIntelReport defaults are applied."""
        report = CongressionalIntelReport(**_valid_intel_report())
        assert report.bills == []
        assert report.delegation_enhanced is False
        assert report.confidence == {}
        assert report.scan_date == ""

    def test_with_bills_list(self):
        """CongressionalIntelReport with nested bills validates."""
        bills = [
            _valid_bill_intelligence(bill_id="119-HR-100"),
            _valid_bill_intelligence(bill_id="119-S-200", bill_type="S"),
        ]
        report = CongressionalIntelReport(
            **_valid_intel_report(bills=bills)
        )
        assert len(report.bills) == 2
        assert all(isinstance(b, BillIntelligence) for b in report.bills)

    def test_empty_bills_list(self):
        """CongressionalIntelReport with empty bills list is valid."""
        report = CongressionalIntelReport(
            **_valid_intel_report(bills=[])
        )
        assert report.bills == []

    def test_nested_bill_validation(self):
        """CongressionalIntelReport rejects invalid nested bills."""
        bad_bill = {
            "bill_id": "119-HR-100",
            "congress": 119,
            "bill_type": "INVALID",  # Invalid type
            "bill_number": 100,
            "title": "Test",
        }
        with pytest.raises(ValidationError, match="bill_type"):
            CongressionalIntelReport(
                **_valid_intel_report(bills=[bad_bill])
            )

    def test_confidence_dict(self):
        """CongressionalIntelReport accepts confidence dict."""
        confidence = {
            "congress_gov": {"score": 0.78, "level": "HIGH"},
            "federal_register": {"score": 0.65, "level": "MEDIUM"},
        }
        report = CongressionalIntelReport(
            **_valid_intel_report(confidence=confidence)
        )
        assert report.confidence["congress_gov"]["score"] == 0.78

    def test_tribe_id_validation(self):
        """CongressionalIntelReport rejects non-epa_ tribe_id."""
        with pytest.raises(ValidationError, match="tribe_id"):
            CongressionalIntelReport(
                tribe_id="bad_id",
                generated_at="2026-01-01T00:00:00+00:00",
            )

    def test_delegation_enhanced_flag(self):
        """delegation_enhanced flag stores correctly."""
        report = CongressionalIntelReport(
            **_valid_intel_report(delegation_enhanced=True)
        )
        assert report.delegation_enhanced is True
