"""Tests for Phase 7 economic impact calculator and program relevance filter.

Covers requirements:
  ECON-01: EconomicImpactCalculator (multiplier ranges, BCR, district allocation)
  DOC-02: ProgramRelevanceFilter (hazard-based filtering, 8-12 programs)

All tests use mock data -- no file I/O or network access required.
"""

import pytest


# ---------------------------------------------------------------------------
# Mock data factories
# ---------------------------------------------------------------------------

def _make_programs(count: int = 16) -> dict[str, dict]:
    """Create a mock programs dict with the given number of programs."""
    program_defs = [
        ("bia_tcr", "BIA Tribal Climate Resilience", "critical"),
        ("fema_bric", "FEMA BRIC", "critical"),
        ("irs_elective_pay", "IRS Elective Pay", "critical"),
        ("epa_stag", "EPA STAG", "high"),
        ("epa_gap", "EPA GAP", "high"),
        ("fema_tribal_mitigation", "FEMA Tribal Mitigation", "high"),
        ("dot_protect", "DOT PROTECT", "high"),
        ("usda_wildfire", "USDA Wildfire", "high"),
        ("doe_indian_energy", "DOE Indian Energy", "high"),
        ("hud_ihbg", "HUD IHBG", "high"),
        ("noaa_tribal", "NOAA Tribal", "high"),
        ("fhwa_ttp_safety", "FHWA TTP Safety", "medium"),
        ("usbr_watersmart", "USBR WaterSMART", "medium"),
        ("usbr_tap", "USBR TAP", "medium"),
        ("bia_tcr_awards", "BIA TCR Awards", "high"),
        ("epa_tribal_air", "EPA Tribal Air", "high"),
    ]
    programs = {}
    for pid, name, priority in program_defs[:count]:
        programs[pid] = {
            "id": pid,
            "name": name,
            "priority": priority,
        }
    return programs


def _make_hazard_profile(top_hazards: list[dict] | None = None) -> dict:
    """Create a mock hazard profile with optional top hazards."""
    if top_hazards is None:
        top_hazards = [
            {"type": "Wildfire", "code": "WFIR", "risk_score": 92.0,
             "risk_rating": "Very High", "eal_total": 500000.0},
            {"type": "Drought", "code": "DRGT", "risk_score": 60.0,
             "risk_rating": "Relatively Moderate", "eal_total": 180000.0},
            {"type": "Hurricane", "code": "HRCN", "risk_score": 15.0,
             "risk_rating": "Very Low", "eal_total": 13000.0},
        ]
    return {
        "fema_nri": {
            "composite": {
                "risk_score": 85.5,
                "risk_rating": "Very High",
            },
            "top_hazards": top_hazards,
            "all_hazards": {},
        },
    }


# ===========================================================================
# ECON-01: TestEconomicImpactCalculator
# ===========================================================================

class TestEconomicImpactCalculator:
    """Tests for EconomicImpactCalculator (ECON-01)."""

    def test_compute_with_awards(self) -> None:
        """Known awards produce correct impact ranges."""
        from src.packets.economic import EconomicImpactCalculator

        calc = EconomicImpactCalculator()
        awards = [
            {"obligation": 500_000, "program_id": "bia_tcr", "cfda": "15.156"},
            {"obligation": 250_000, "program_id": "fema_bric", "cfda": "97.047"},
        ]
        programs = _make_programs(4)
        summary = calc.compute(
            tribe_id="epa_001",
            tribe_name="Alpha Tribe",
            awards=awards,
            districts=[],
            programs=programs,
        )

        # Total includes actual awards (750k) + benchmarks for remaining programs
        # Check actual-award programs specifically
        actual_programs = [p for p in summary.by_program if not p.is_benchmark]
        assert len(actual_programs) == 2

        bia = next(p for p in actual_programs if p.program_id == "bia_tcr")
        assert bia.total_obligation == 500_000
        assert bia.estimated_impact_low == 500_000 * 1.8
        assert bia.estimated_impact_high == 500_000 * 2.4
        assert bia.is_benchmark is False

    def test_compute_zero_awards(self) -> None:
        """Empty awards list returns benchmark-based summary."""
        from src.packets.economic import EconomicImpactCalculator

        calc = EconomicImpactCalculator()
        programs = _make_programs(4)
        summary = calc.compute(
            tribe_id="epa_002",
            tribe_name="Beta Tribe",
            awards=[],
            districts=[],
            programs=programs,
        )

        # All should be benchmarks
        assert len(summary.by_program) == 4
        assert all(p.is_benchmark for p in summary.by_program)
        assert summary.total_obligation > 0

    def test_bcr_mitigation_programs(self) -> None:
        """BCR=4.0 for mitigation programs, None for non-mitigation."""
        from src.packets.economic import EconomicImpactCalculator

        calc = EconomicImpactCalculator()
        awards = [
            {"obligation": 500_000, "program_id": "fema_bric"},
            {"obligation": 100_000, "program_id": "epa_gap"},
        ]
        programs = {"fema_bric": _make_programs()["fema_bric"],
                     "epa_gap": _make_programs()["epa_gap"]}
        summary = calc.compute(
            tribe_id="epa_001",
            tribe_name="Alpha Tribe",
            awards=awards,
            districts=[],
            programs=programs,
        )

        bric = next(p for p in summary.by_program if p.program_id == "fema_bric")
        gap = next(p for p in summary.by_program if p.program_id == "epa_gap")
        assert bric.fema_bcr == 4.0
        assert gap.fema_bcr is None

    def test_district_allocation(self) -> None:
        """Multi-district proportional split by overlap_pct."""
        from src.packets.economic import EconomicImpactCalculator

        calc = EconomicImpactCalculator()
        awards = [
            {"obligation": 1_000_000, "program_id": "bia_tcr"},
        ]
        districts = [
            {"district": "OK-02", "overlap_pct": 60.0},
            {"district": "TX-01", "overlap_pct": 40.0},
        ]
        programs = {"bia_tcr": _make_programs()["bia_tcr"]}
        summary = calc.compute(
            tribe_id="epa_003",
            tribe_name="Gamma Tribe",
            awards=awards,
            districts=districts,
            programs=programs,
        )

        assert "OK-02" in summary.by_district
        assert "TX-01" in summary.by_district

        # OK-02 gets 60% of impact
        ok = summary.by_district["OK-02"]
        assert ok["overlap_pct"] == 60.0
        assert ok["obligation"] == pytest.approx(600_000.0)
        assert ok["impact_low"] == pytest.approx(1_000_000 * 1.8 * 0.6)
        assert ok["impact_high"] == pytest.approx(1_000_000 * 2.4 * 0.6)

        # TX-01 gets 40%
        tx = summary.by_district["TX-01"]
        assert tx["obligation"] == pytest.approx(400_000.0)

    def test_jobs_estimate_range(self) -> None:
        """Known obligation produces correct job range."""
        from src.packets.economic import EconomicImpactCalculator

        calc = EconomicImpactCalculator()
        awards = [{"obligation": 2_000_000, "program_id": "bia_tcr"}]
        programs = {"bia_tcr": _make_programs()["bia_tcr"]}
        summary = calc.compute(
            tribe_id="epa_001",
            tribe_name="Alpha Tribe",
            awards=awards,
            districts=[],
            programs=programs,
        )

        bia = next(p for p in summary.by_program if p.program_id == "bia_tcr")
        # $2M: jobs_low = 2 * 8 = 16, jobs_high = 2 * 15 = 30
        assert bia.jobs_estimate_low == pytest.approx(16.0)
        assert bia.jobs_estimate_high == pytest.approx(30.0)

    def test_format_impact_narrative(self) -> None:
        """Narrative includes tribe name and dollar ranges."""
        from src.packets.economic import (
            EconomicImpactCalculator, ProgramEconomicImpact,
        )

        calc = EconomicImpactCalculator()
        impact = ProgramEconomicImpact(
            program_id="bia_tcr",
            total_obligation=500_000,
            estimated_impact_low=900_000,
            estimated_impact_high=1_200_000,
            jobs_estimate_low=4.0,
            jobs_estimate_high=7.5,
            is_benchmark=False,
        )
        narrative = calc.format_impact_narrative(
            impact, "Alpha Tribe", "BIA Tribal Climate Resilience"
        )
        assert "Alpha Tribe" in narrative
        assert "$900,000" in narrative
        assert "$1,200,000" in narrative
        assert "BEA RIMS II" in narrative
        assert "1.8-2.4x" in narrative
        assert "BLS employment" in narrative

    def test_format_impact_narrative_benchmark(self) -> None:
        """Benchmark narrative uses 'could generate' framing."""
        from src.packets.economic import (
            EconomicImpactCalculator, ProgramEconomicImpact,
        )

        calc = EconomicImpactCalculator()
        impact = ProgramEconomicImpact(
            program_id="bia_tcr",
            total_obligation=150_000,
            estimated_impact_low=270_000,
            estimated_impact_high=360_000,
            jobs_estimate_low=1.2,
            jobs_estimate_high=2.25,
            is_benchmark=True,
        )
        narrative = calc.format_impact_narrative(
            impact, "Beta Tribe", "BIA Tribal Climate Resilience"
        )
        assert "Based on program averages" in narrative
        assert "could generate" in narrative
        # Benchmark does not mention tribe name directly
        assert "Beta Tribe" not in narrative

    def test_format_bcr_narrative(self) -> None:
        """Returns string for mitigation, None for non-mitigation."""
        from src.packets.economic import (
            EconomicImpactCalculator, ProgramEconomicImpact,
        )

        calc = EconomicImpactCalculator()

        # Mitigation program
        mit = ProgramEconomicImpact(
            program_id="fema_bric",
            total_obligation=500_000,
            fema_bcr=4.0,
        )
        bcr_text = calc.format_bcr_narrative(mit)
        assert bcr_text is not None
        assert "$4" in bcr_text
        assert "MitSaves" in bcr_text

        # Non-mitigation
        non_mit = ProgramEconomicImpact(
            program_id="epa_gap",
            total_obligation=100_000,
            fema_bcr=None,
        )
        assert calc.format_bcr_narrative(non_mit) is None

    def test_negative_obligation_skipped(self) -> None:
        """Awards with negative or zero amounts are excluded."""
        from src.packets.economic import EconomicImpactCalculator

        calc = EconomicImpactCalculator()
        awards = [
            {"obligation": -50_000, "program_id": "bia_tcr"},
            {"obligation": 0, "program_id": "fema_bric"},
            {"obligation": 100_000, "program_id": "epa_gap"},
        ]
        programs = {"bia_tcr": _make_programs()["bia_tcr"],
                     "fema_bric": _make_programs()["fema_bric"],
                     "epa_gap": _make_programs()["epa_gap"]}
        summary = calc.compute(
            tribe_id="epa_001",
            tribe_name="Alpha Tribe",
            awards=awards,
            districts=[],
            programs=programs,
        )

        # Only epa_gap award counted (100k); others are benchmark
        actual = [p for p in summary.by_program if not p.is_benchmark]
        assert len(actual) == 1
        assert actual[0].program_id == "epa_gap"
        assert actual[0].total_obligation == 100_000

    def test_methodology_citation(self) -> None:
        """Citation string present in every ProgramEconomicImpact."""
        from src.packets.economic import (
            EconomicImpactCalculator, METHODOLOGY_CITATION,
        )

        calc = EconomicImpactCalculator()
        awards = [{"obligation": 100_000, "program_id": "bia_tcr"}]
        programs = {"bia_tcr": _make_programs()["bia_tcr"]}
        summary = calc.compute(
            tribe_id="epa_001",
            tribe_name="Alpha Tribe",
            awards=awards,
            districts=[],
            programs=programs,
        )

        for impact in summary.by_program:
            assert impact.methodology_citation == METHODOLOGY_CITATION
            assert "BEA" in impact.methodology_citation
            assert "BLS" in impact.methodology_citation
            assert "MitSaves" in impact.methodology_citation

    def test_district_allocation_skips_none_overlap(self) -> None:
        """Districts with overlap_pct=None or 0 are skipped."""
        from src.packets.economic import EconomicImpactCalculator

        calc = EconomicImpactCalculator()
        awards = [{"obligation": 1_000_000, "program_id": "bia_tcr"}]
        districts = [
            {"district": "AZ-02", "overlap_pct": 95.0},
            {"district": "AZ-05", "overlap_pct": None},
            {"district": "AZ-07", "overlap_pct": 0},
        ]
        programs = {"bia_tcr": _make_programs()["bia_tcr"]}
        summary = calc.compute(
            tribe_id="epa_001",
            tribe_name="Alpha Tribe",
            awards=awards,
            districts=districts,
            programs=programs,
        )

        assert "AZ-02" in summary.by_district
        assert "AZ-05" not in summary.by_district
        assert "AZ-07" not in summary.by_district

    def test_cfda_fallback_when_no_program_id(self) -> None:
        """Awards without program_id fall back to CFDA field."""
        from src.packets.economic import EconomicImpactCalculator

        calc = EconomicImpactCalculator()
        awards = [
            {"obligation": 100_000, "cfda": "15.156"},
            {"obligation": 200_000, "cfda": ["97.047", "97.048"]},
        ]
        programs = {"bia_tcr": _make_programs()["bia_tcr"]}
        summary = calc.compute(
            tribe_id="epa_001",
            tribe_name="Alpha Tribe",
            awards=awards,
            districts=[],
            programs=programs,
        )

        # Both should be in by_program (even though cfda keys won't match program dict)
        actual = [p for p in summary.by_program if not p.is_benchmark]
        assert len(actual) == 2

    def test_string_obligation_converted(self) -> None:
        """String-typed obligation is converted to float."""
        from src.packets.economic import EconomicImpactCalculator

        calc = EconomicImpactCalculator()
        awards = [{"obligation": "500000", "program_id": "bia_tcr"}]
        programs = {"bia_tcr": _make_programs()["bia_tcr"]}
        summary = calc.compute(
            tribe_id="epa_001",
            tribe_name="Alpha Tribe",
            awards=awards,
            districts=[],
            programs=programs,
        )

        actual = [p for p in summary.by_program if not p.is_benchmark]
        assert actual[0].total_obligation == 500_000.0

    def test_actual_awards_sorted_before_benchmarks(self) -> None:
        """Actual awards appear before benchmark estimates in by_program."""
        from src.packets.economic import EconomicImpactCalculator

        calc = EconomicImpactCalculator()
        awards = [{"obligation": 100_000, "program_id": "epa_gap"}]
        programs = _make_programs(4)
        summary = calc.compute(
            tribe_id="epa_001",
            tribe_name="Alpha Tribe",
            awards=awards,
            districts=[],
            programs=programs,
        )

        # First item should be the actual award
        assert summary.by_program[0].program_id == "epa_gap"
        assert summary.by_program[0].is_benchmark is False

        # Remaining should be benchmarks
        for p in summary.by_program[1:]:
            assert p.is_benchmark is True


# ===========================================================================
# DOC-02: TestProgramRelevanceFilter
# ===========================================================================

class TestProgramRelevanceFilter:
    """Tests for ProgramRelevanceFilter (DOC-02)."""

    def test_filter_critical_always_included(self) -> None:
        """Critical programs always appear in the filtered result."""
        from src.packets.relevance import ProgramRelevanceFilter

        programs = _make_programs()
        filt = ProgramRelevanceFilter(programs)
        result = filt.filter_for_tribe(
            hazard_profile=_make_hazard_profile(),
            ecoregions=["southwest"],
        )

        result_ids = {p["id"] for p in result}
        assert "bia_tcr" in result_ids
        assert "fema_bric" in result_ids
        assert "irs_elective_pay" in result_ids

    def test_filter_hazard_match(self) -> None:
        """Wildfire hazard includes usda_wildfire in results."""
        from src.packets.relevance import ProgramRelevanceFilter

        programs = _make_programs()
        filt = ProgramRelevanceFilter(programs)
        result = filt.filter_for_tribe(
            hazard_profile=_make_hazard_profile([
                {"type": "Wildfire", "code": "WFIR", "risk_score": 95.0},
            ]),
            ecoregions=[],
        )

        result_ids = {p["id"] for p in result}
        assert "usda_wildfire" in result_ids
        assert "fema_bric" in result_ids  # Also mapped to WFIR

    def test_filter_empty_hazard_fallback(self) -> None:
        """Empty hazard profile still returns programs via priority/ecoregion."""
        from src.packets.relevance import ProgramRelevanceFilter

        programs = _make_programs()
        filt = ProgramRelevanceFilter(
            programs, ecoregion_priority=["bia_tcr", "fema_bric"]
        )
        result = filt.filter_for_tribe(
            hazard_profile={},
            ecoregions=[],
        )

        # Should still get MIN_PROGRAMS items
        assert len(result) >= 8
        # Critical programs always present
        result_ids = {p["id"] for p in result}
        assert "bia_tcr" in result_ids

    def test_filter_min_programs(self) -> None:
        """Result has at least MIN_PROGRAMS items when enough programs exist."""
        from src.packets.relevance import ProgramRelevanceFilter

        programs = _make_programs()
        filt = ProgramRelevanceFilter(programs)
        result = filt.filter_for_tribe(
            hazard_profile={},
            ecoregions=[],
        )

        assert len(result) >= 8

    def test_filter_max_programs(self) -> None:
        """Result capped at MAX_PROGRAMS."""
        from src.packets.relevance import ProgramRelevanceFilter

        programs = _make_programs()
        filt = ProgramRelevanceFilter(programs)
        # Give many hazards to boost many programs
        profile = _make_hazard_profile([
            {"code": "WFIR", "type": "Wildfire", "risk_score": 95.0},
            {"code": "CFLD", "type": "Coastal Flooding", "risk_score": 90.0},
            {"code": "DRGT", "type": "Drought", "risk_score": 85.0},
            {"code": "HRCN", "type": "Hurricane", "risk_score": 80.0},
            {"code": "ERQK", "type": "Earthquake", "risk_score": 75.0},
            {"code": "HWAV", "type": "Heat Wave", "risk_score": 70.0},
        ])
        result = filt.filter_for_tribe(
            hazard_profile=profile,
            ecoregions=["southwest"],
        )

        assert len(result) <= 12

    def test_omitted_programs(self) -> None:
        """Programs not in filtered list returned by get_omitted_programs()."""
        from src.packets.relevance import ProgramRelevanceFilter

        programs = _make_programs()
        filt = ProgramRelevanceFilter(programs)
        result = filt.filter_for_tribe(
            hazard_profile=_make_hazard_profile(),
            ecoregions=[],
        )

        omitted = filt.get_omitted_programs(result)
        result_ids = {p["id"] for p in result}
        omitted_ids = {p["id"] for p in omitted}

        # No overlap between included and omitted
        assert len(result_ids & omitted_ids) == 0
        # Together they cover all programs
        assert result_ids | omitted_ids == set(programs.keys())

    def test_relevance_score_ordering(self) -> None:
        """Results sorted by relevance score descending."""
        from src.packets.relevance import ProgramRelevanceFilter

        programs = _make_programs()
        filt = ProgramRelevanceFilter(programs)
        result = filt.filter_for_tribe(
            hazard_profile=_make_hazard_profile(),
            ecoregions=["southwest"],
        )

        scores = [p["_relevance_score"] for p in result]
        assert scores == sorted(scores, reverse=True)

    def test_filter_with_ecoregion_mapper(self) -> None:
        """Ecoregion mapper integration boosts matching programs."""
        from src.packets.relevance import ProgramRelevanceFilter

        programs = _make_programs()

        # Mock ecoregion mapper
        class MockMapper:
            def get_priority_programs(self, eco):
                if eco == "southwest":
                    return ["bia_tcr", "usda_wildfire"]
                return []

        filt = ProgramRelevanceFilter(programs)
        result = filt.filter_for_tribe(
            hazard_profile=_make_hazard_profile(),
            ecoregions=["southwest"],
            ecoregion_mapper=MockMapper(),
        )

        result_ids = {p["id"] for p in result}
        assert "bia_tcr" in result_ids
        assert "usda_wildfire" in result_ids

    def test_filter_hazard_name_resolution(self) -> None:
        """Hazard type field (human name) resolves correctly."""
        from src.packets.relevance import ProgramRelevanceFilter

        programs = _make_programs()
        filt = ProgramRelevanceFilter(programs)
        result = filt.filter_for_tribe(
            hazard_profile=_make_hazard_profile([
                {"type": "Drought", "risk_score": 80.0},  # No code field
            ]),
            ecoregions=[],
        )

        result_ids = {p["id"] for p in result}
        # Drought maps to usbr_watersmart, usbr_tap, bia_tcr
        assert "usbr_watersmart" in result_ids or "bia_tcr" in result_ids

    def test_filter_small_program_inventory(self) -> None:
        """Filter works with fewer than MIN_PROGRAMS in inventory."""
        from src.packets.relevance import ProgramRelevanceFilter

        programs = _make_programs(4)  # Only 4 programs
        filt = ProgramRelevanceFilter(programs)
        result = filt.filter_for_tribe(
            hazard_profile=_make_hazard_profile(),
            ecoregions=[],
        )

        # Should return all 4 (can't reach MIN_PROGRAMS=8)
        assert len(result) == 4

    def test_hazard_program_map_has_18_entries(self) -> None:
        """HAZARD_PROGRAM_MAP covers all 18 NRI hazard types."""
        from src.packets.relevance import HAZARD_PROGRAM_MAP
        assert len(HAZARD_PROGRAM_MAP) == 18

    def test_critical_survives_max_trimming(self) -> None:
        """Critical programs are never removed when trimming to MAX_PROGRAMS."""
        from src.packets.relevance import ProgramRelevanceFilter

        programs = _make_programs()
        filt = ProgramRelevanceFilter(programs)
        # Many hazards to exceed MAX
        profile = _make_hazard_profile([
            {"code": "WFIR", "type": "Wildfire", "risk_score": 95.0},
            {"code": "CFLD", "type": "Coastal Flooding", "risk_score": 90.0},
            {"code": "DRGT", "type": "Drought", "risk_score": 85.0},
            {"code": "HRCN", "type": "Hurricane", "risk_score": 80.0},
            {"code": "ERQK", "type": "Earthquake", "risk_score": 75.0},
        ])
        result = filt.filter_for_tribe(
            hazard_profile=profile,
            ecoregions=["southwest", "great_plains_south"],
        )

        result_ids = {p["id"] for p in result}
        # All 3 critical programs must survive
        assert "bia_tcr" in result_ids
        assert "fema_bric" in result_ids
        assert "irs_elective_pay" in result_ids
