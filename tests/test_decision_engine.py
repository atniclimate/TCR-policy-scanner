"""Tests for the advocacy goal decision engine.

Covers all 5 decision rules (LOGIC-01 through LOGIC-05), priority ordering,
default/no-match fallback, and secondary_rules transparency.

Uses synthetic graph_data and program dicts to isolate each rule.
"""

import pytest

from src.analysis.decision_engine import DecisionEngine, ADVOCACY_GOALS


# ---------------------------------------------------------------------------
# Fixtures: minimal config, programs, and graph helpers
# ---------------------------------------------------------------------------

def _default_config(urgency_days=30):
    """Config with decision_engine section."""
    return {
        "monitors": {
            "decision_engine": {
                "urgency_threshold_days": urgency_days,
            }
        }
    }


def _make_graph(nodes=None, edges=None):
    """Build a minimal graph_data dict."""
    return {
        "nodes": nodes or {},
        "edges": edges or [],
    }


def _threatens_edge(target_pid, days_remaining, description="threat"):
    """Create a THREATENS edge targeting a program."""
    return {
        "source": f"threat_{target_pid}",
        "target": target_pid,
        "type": "THREATENS",
        "metadata": {
            "threat_type": "test_threat",
            "deadline": "2026-03-01",
            "days_remaining": days_remaining,
            "description": description,
        },
    }


def _authority_node(auth_id, durability="Permanent", citation="Test Act"):
    """Create an authority node dict."""
    return {
        "id": auth_id,
        "_type": "AuthorityNode",
        "citation": citation,
        "durability": durability,
    }


def _funding_node(fv_id, funding_type="Discretionary", name="Test Fund"):
    """Create a funding vehicle node dict."""
    return {
        "id": fv_id,
        "_type": "FundingVehicleNode",
        "name": name,
        "funding_type": funding_type,
    }


def _barrier_node(bar_id, barrier_type="Administrative", severity="High"):
    """Create a barrier node dict."""
    return {
        "id": bar_id,
        "_type": "BarrierNode",
        "description": "Test barrier",
        "barrier_type": barrier_type,
        "severity": severity,
    }


def _authorized_by_edge(pid, auth_id):
    return {"source": pid, "target": auth_id, "type": "AUTHORIZED_BY", "metadata": {}}


def _funded_by_edge(pid, fv_id):
    return {"source": pid, "target": fv_id, "type": "FUNDED_BY", "metadata": {}}


def _blocked_by_edge(pid, bar_id):
    return {"source": pid, "target": bar_id, "type": "BLOCKED_BY", "metadata": {}}


# ---------------------------------------------------------------------------
# ADVOCACY_GOALS constant
# ---------------------------------------------------------------------------

class TestAdvocacyGoals:
    """Verify the ADVOCACY_GOALS constant has all 5 goals."""

    def test_has_five_goals(self):
        assert len(ADVOCACY_GOALS) == 5

    def test_keys(self):
        expected = {
            "URGENT_STABILIZATION",
            "RESTORE_REPLACE",
            "PROTECT_BASE",
            "DIRECT_ACCESS_PARITY",
            "EXPAND_STRENGTHEN",
        }
        assert set(ADVOCACY_GOALS.keys()) == expected

    def test_values_are_human_readable(self):
        for key, val in ADVOCACY_GOALS.items():
            assert isinstance(val, str)
            assert len(val) > 0


# ---------------------------------------------------------------------------
# LOGIC-05: Urgent Stabilization
# ---------------------------------------------------------------------------

class TestLogic05UrgentStabilization:
    """LOGIC-05: THREATENS edge within urgency window overrides all rules."""

    def test_threatens_within_30_days_triggers(self):
        programs = {"prog_a": {"id": "prog_a", "ci_status": "STABLE"}}
        graph = _make_graph(edges=[_threatens_edge("prog_a", days_remaining=15)])
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])

        assert result["prog_a"]["advocacy_goal"] == "URGENT_STABILIZATION"
        assert result["prog_a"]["rule"] == "LOGIC-05"
        assert result["prog_a"]["confidence"] == "HIGH"

    def test_threatens_at_exactly_30_days_triggers(self):
        programs = {"prog_a": {"id": "prog_a", "ci_status": "STABLE"}}
        graph = _make_graph(edges=[_threatens_edge("prog_a", days_remaining=30)])
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])

        assert result["prog_a"]["advocacy_goal"] == "URGENT_STABILIZATION"

    def test_threatens_at_31_days_does_not_trigger(self):
        programs = {"prog_a": {"id": "prog_a", "ci_status": "STABLE"}}
        graph = _make_graph(edges=[_threatens_edge("prog_a", days_remaining=31)])
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])

        assert result["prog_a"]["advocacy_goal"] != "URGENT_STABILIZATION"

    def test_custom_urgency_threshold(self):
        """Urgency threshold is configurable."""
        programs = {"prog_a": {"id": "prog_a", "ci_status": "STABLE"}}
        graph = _make_graph(edges=[_threatens_edge("prog_a", days_remaining=45)])
        engine = DecisionEngine(_default_config(urgency_days=60), programs)
        result = engine.classify_all(graph, [])

        assert result["prog_a"]["advocacy_goal"] == "URGENT_STABILIZATION"

    def test_overrides_logic01(self):
        """LOGIC-05 overrides LOGIC-01 when both match."""
        programs = {"prog_a": {"id": "prog_a", "ci_status": "TERMINATED"}}
        graph = _make_graph(
            nodes={"auth_1": _authority_node("auth_1", durability="Permanent")},
            edges=[
                _threatens_edge("prog_a", days_remaining=10),
                _authorized_by_edge("prog_a", "auth_1"),
            ],
        )
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])

        assert result["prog_a"]["advocacy_goal"] == "URGENT_STABILIZATION"
        assert result["prog_a"]["rule"] == "LOGIC-05"

    def test_reason_includes_days(self):
        programs = {"prog_a": {"id": "prog_a", "ci_status": "STABLE"}}
        graph = _make_graph(edges=[_threatens_edge("prog_a", days_remaining=5, description="IIJA sunset")])
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])

        assert "5" in result["prog_a"]["reason"]


# ---------------------------------------------------------------------------
# LOGIC-01: Restore/Replace
# ---------------------------------------------------------------------------

class TestLogic01RestoreReplace:
    """LOGIC-01: TERMINATED/FLAGGED program with active permanent authority."""

    def test_terminated_with_permanent_authority(self):
        programs = {"prog_a": {"id": "prog_a", "ci_status": "TERMINATED"}}
        graph = _make_graph(
            nodes={"auth_1": _authority_node("auth_1", durability="Permanent")},
            edges=[_authorized_by_edge("prog_a", "auth_1")],
        )
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])

        assert result["prog_a"]["advocacy_goal"] == "RESTORE_REPLACE"
        assert result["prog_a"]["rule"] == "LOGIC-01"
        assert result["prog_a"]["confidence"] == "HIGH"

    def test_flagged_treated_as_near_terminated(self):
        programs = {"prog_a": {"id": "prog_a", "ci_status": "FLAGGED"}}
        graph = _make_graph(
            nodes={"auth_1": _authority_node("auth_1", durability="Permanent")},
            edges=[_authorized_by_edge("prog_a", "auth_1")],
        )
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])

        assert result["prog_a"]["advocacy_goal"] == "RESTORE_REPLACE"

    def test_stable_does_not_trigger(self):
        programs = {"prog_a": {"id": "prog_a", "ci_status": "STABLE"}}
        graph = _make_graph(
            nodes={"auth_1": _authority_node("auth_1", durability="Permanent")},
            edges=[_authorized_by_edge("prog_a", "auth_1")],
        )
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])

        assert result["prog_a"]["advocacy_goal"] != "RESTORE_REPLACE"

    def test_terminated_without_permanent_authority_does_not_trigger(self):
        """TERMINATED but authority is expiring -- no restore/replace."""
        programs = {"prog_a": {"id": "prog_a", "ci_status": "TERMINATED"}}
        graph = _make_graph(
            nodes={"auth_1": _authority_node("auth_1", durability="Expires FY26")},
            edges=[_authorized_by_edge("prog_a", "auth_1")],
        )
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])

        assert result["prog_a"]["advocacy_goal"] != "RESTORE_REPLACE"

    def test_reason_includes_authority_citation(self):
        programs = {"prog_a": {"id": "prog_a", "ci_status": "TERMINATED"}}
        graph = _make_graph(
            nodes={"auth_1": _authority_node("auth_1", durability="Permanent", citation="Stafford Act")},
            edges=[_authorized_by_edge("prog_a", "auth_1")],
        )
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])

        assert "Stafford Act" in result["prog_a"]["reason"]


# ---------------------------------------------------------------------------
# LOGIC-02: Protect Base
# ---------------------------------------------------------------------------

class TestLogic02ProtectBase:
    """LOGIC-02: Discretionary-funded program facing eliminate/reduce signals."""

    def test_discretionary_with_eliminate_alert(self):
        programs = {"prog_a": {"id": "prog_a", "ci_status": "STABLE"}}
        graph = _make_graph(
            nodes={"fv_1": _funding_node("fv_1", funding_type="Discretionary")},
            edges=[_funded_by_edge("prog_a", "fv_1")],
        )
        alerts = [
            type("Alert", (), {
                "monitor": "test",
                "severity": "WARNING",
                "program_ids": ["prog_a"],
                "title": "eliminate funding",
                "detail": "eliminate",
                "metadata": {"signal": "eliminate"},
            })()
        ]
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, alerts)

        assert result["prog_a"]["advocacy_goal"] == "PROTECT_BASE"
        assert result["prog_a"]["rule"] == "LOGIC-02"

    def test_discretionary_with_reduce_alert(self):
        programs = {"prog_a": {"id": "prog_a", "ci_status": "STABLE"}}
        graph = _make_graph(
            nodes={"fv_1": _funding_node("fv_1", funding_type="Discretionary")},
            edges=[_funded_by_edge("prog_a", "fv_1")],
        )
        alerts = [
            type("Alert", (), {
                "monitor": "test",
                "severity": "WARNING",
                "program_ids": ["prog_a"],
                "title": "reduce funding",
                "detail": "reduce",
                "metadata": {"signal": "reduce"},
            })()
        ]
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, alerts)

        assert result["prog_a"]["advocacy_goal"] == "PROTECT_BASE"

    def test_at_risk_with_discretionary_funding(self):
        """AT_RISK status with discretionary funding triggers PROTECT_BASE."""
        programs = {"prog_a": {"id": "prog_a", "ci_status": "AT_RISK"}}
        graph = _make_graph(
            nodes={"fv_1": _funding_node("fv_1", funding_type="Discretionary")},
            edges=[_funded_by_edge("prog_a", "fv_1")],
        )
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])

        assert result["prog_a"]["advocacy_goal"] == "PROTECT_BASE"

    def test_uncertain_with_discretionary_funding(self):
        """UNCERTAIN status with discretionary funding triggers PROTECT_BASE."""
        programs = {"prog_a": {"id": "prog_a", "ci_status": "UNCERTAIN"}}
        graph = _make_graph(
            nodes={"fv_1": _funding_node("fv_1", funding_type="Discretionary")},
            edges=[_funded_by_edge("prog_a", "fv_1")],
        )
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])

        assert result["prog_a"]["advocacy_goal"] == "PROTECT_BASE"

    def test_mandatory_funding_does_not_trigger(self):
        programs = {"prog_a": {"id": "prog_a", "ci_status": "AT_RISK"}}
        graph = _make_graph(
            nodes={"fv_1": _funding_node("fv_1", funding_type="Mandatory")},
            edges=[_funded_by_edge("prog_a", "fv_1")],
        )
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])

        assert result["prog_a"]["advocacy_goal"] != "PROTECT_BASE"

    def test_no_funding_edges_checks_program_field(self):
        """Falls back to program-level funding_type field if no edges."""
        programs = {"prog_a": {"id": "prog_a", "ci_status": "AT_RISK", "funding_type": "Discretionary"}}
        graph = _make_graph()
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])

        assert result["prog_a"]["advocacy_goal"] == "PROTECT_BASE"


# ---------------------------------------------------------------------------
# LOGIC-03: Direct Access Parity
# ---------------------------------------------------------------------------

class TestLogic03DirectAccessParity:
    """LOGIC-03: State pass-through programs with high administrative burden."""

    def test_state_pass_through_with_high_admin_barrier(self):
        programs = {"prog_a": {"id": "prog_a", "ci_status": "STABLE", "access_type": "state_pass_through"}}
        graph = _make_graph(
            nodes={"bar_1": _barrier_node("bar_1", barrier_type="Administrative", severity="High")},
            edges=[_blocked_by_edge("prog_a", "bar_1")],
        )
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])

        assert result["prog_a"]["advocacy_goal"] == "DIRECT_ACCESS_PARITY"
        assert result["prog_a"]["rule"] == "LOGIC-03"

    def test_direct_access_does_not_trigger(self):
        programs = {"prog_a": {"id": "prog_a", "ci_status": "STABLE", "access_type": "direct"}}
        graph = _make_graph(
            nodes={"bar_1": _barrier_node("bar_1", barrier_type="Administrative", severity="High")},
            edges=[_blocked_by_edge("prog_a", "bar_1")],
        )
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])

        assert result["prog_a"]["advocacy_goal"] != "DIRECT_ACCESS_PARITY"

    def test_state_pass_through_without_high_barrier_does_not_trigger(self):
        """State pass-through but only low severity barriers -- does not trigger."""
        programs = {"prog_a": {"id": "prog_a", "ci_status": "STABLE", "access_type": "state_pass_through"}}
        graph = _make_graph(
            nodes={"bar_1": _barrier_node("bar_1", barrier_type="Administrative", severity="Low")},
            edges=[_blocked_by_edge("prog_a", "bar_1")],
        )
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])

        assert result["prog_a"]["advocacy_goal"] != "DIRECT_ACCESS_PARITY"


# ---------------------------------------------------------------------------
# LOGIC-04: Expand and Strengthen
# ---------------------------------------------------------------------------

class TestLogic04ExpandStrengthen:
    """LOGIC-04: STABLE/SECURE programs with direct or set-aside access."""

    def test_stable_with_direct_access(self):
        programs = {"prog_a": {"id": "prog_a", "ci_status": "STABLE", "access_type": "direct"}}
        graph = _make_graph()
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])

        assert result["prog_a"]["advocacy_goal"] == "EXPAND_STRENGTHEN"
        assert result["prog_a"]["rule"] == "LOGIC-04"

    def test_secure_with_set_aside(self):
        programs = {"prog_a": {"id": "prog_a", "ci_status": "SECURE", "access_type": "set_aside"}}
        graph = _make_graph()
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])

        assert result["prog_a"]["advocacy_goal"] == "EXPAND_STRENGTHEN"

    def test_stable_but_vulnerable_with_tribal_set_aside(self):
        programs = {"prog_a": {"id": "prog_a", "ci_status": "STABLE_BUT_VULNERABLE", "access_type": "tribal_set_aside"}}
        graph = _make_graph()
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])

        assert result["prog_a"]["advocacy_goal"] == "EXPAND_STRENGTHEN"

    def test_at_risk_does_not_trigger(self):
        programs = {"prog_a": {"id": "prog_a", "ci_status": "AT_RISK", "access_type": "direct"}}
        graph = _make_graph()
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])

        assert result["prog_a"]["advocacy_goal"] != "EXPAND_STRENGTHEN"

    def test_stable_without_access_type_does_not_trigger(self):
        """STABLE but no access_type field -- falls through."""
        programs = {"prog_a": {"id": "prog_a", "ci_status": "STABLE"}}
        graph = _make_graph()
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])

        assert result["prog_a"]["advocacy_goal"] != "EXPAND_STRENGTHEN"


# ---------------------------------------------------------------------------
# Default / No Match
# ---------------------------------------------------------------------------

class TestDefaultNoMatch:
    """Programs matching no rules get a default classification."""

    def test_no_match_returns_none_goal(self):
        programs = {"prog_a": {"id": "prog_a", "ci_status": "STABLE"}}
        graph = _make_graph()
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])

        assert result["prog_a"]["advocacy_goal"] is None
        assert result["prog_a"]["rule"] is None
        assert result["prog_a"]["confidence"] == "LOW"

    def test_no_match_has_reason(self):
        programs = {"prog_a": {"id": "prog_a", "ci_status": "STABLE"}}
        graph = _make_graph()
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])

        assert len(result["prog_a"]["reason"]) > 0

    def test_every_program_gets_classification(self):
        """classify_all must return a result for every program in inventory."""
        programs = {
            "p1": {"id": "p1", "ci_status": "STABLE"},
            "p2": {"id": "p2", "ci_status": "AT_RISK"},
            "p3": {"id": "p3", "ci_status": "TERMINATED"},
        }
        graph = _make_graph()
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])

        assert set(result.keys()) == {"p1", "p2", "p3"}


# ---------------------------------------------------------------------------
# Classification dict shape
# ---------------------------------------------------------------------------

class TestClassificationShape:
    """All classifications must have required fields."""

    def test_matched_classification_has_all_fields(self):
        programs = {"prog_a": {"id": "prog_a", "ci_status": "STABLE"}}
        graph = _make_graph(edges=[_threatens_edge("prog_a", days_remaining=5)])
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])
        c = result["prog_a"]

        assert "advocacy_goal" in c
        assert "goal_label" in c
        assert "rule" in c
        assert "confidence" in c
        assert "reason" in c
        assert "secondary_rules" in c

    def test_default_classification_has_all_fields(self):
        programs = {"prog_a": {"id": "prog_a", "ci_status": "STABLE"}}
        graph = _make_graph()
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])
        c = result["prog_a"]

        assert "advocacy_goal" in c
        assert "goal_label" in c
        assert "rule" in c
        assert "confidence" in c
        assert "reason" in c
        assert "secondary_rules" in c

    def test_goal_label_matches_advocacy_goals(self):
        """When advocacy_goal is set, goal_label must be the human-readable label."""
        programs = {"prog_a": {"id": "prog_a", "ci_status": "STABLE"}}
        graph = _make_graph(edges=[_threatens_edge("prog_a", days_remaining=5)])
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])
        c = result["prog_a"]

        assert c["goal_label"] == ADVOCACY_GOALS[c["advocacy_goal"]]


# ---------------------------------------------------------------------------
# Priority Ordering
# ---------------------------------------------------------------------------

class TestPriorityOrdering:
    """Rules are evaluated in strict priority order: 05 > 01 > 02 > 03 > 04."""

    def test_logic05_beats_logic01(self):
        """Already tested above, but explicit priority test."""
        programs = {"prog_a": {"id": "prog_a", "ci_status": "TERMINATED"}}
        graph = _make_graph(
            nodes={"auth_1": _authority_node("auth_1", durability="Permanent")},
            edges=[
                _threatens_edge("prog_a", days_remaining=10),
                _authorized_by_edge("prog_a", "auth_1"),
            ],
        )
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])

        assert result["prog_a"]["rule"] == "LOGIC-05"

    def test_logic01_beats_logic02(self):
        """TERMINATED + discretionary + permanent authority -> LOGIC-01 wins."""
        programs = {"prog_a": {"id": "prog_a", "ci_status": "TERMINATED"}}
        graph = _make_graph(
            nodes={
                "auth_1": _authority_node("auth_1", durability="Permanent"),
                "fv_1": _funding_node("fv_1", funding_type="Discretionary"),
            },
            edges=[
                _authorized_by_edge("prog_a", "auth_1"),
                _funded_by_edge("prog_a", "fv_1"),
            ],
        )
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])

        assert result["prog_a"]["rule"] == "LOGIC-01"

    def test_logic02_beats_logic04(self):
        """AT_RISK + discretionary + direct access -> LOGIC-02 over LOGIC-04."""
        programs = {"prog_a": {"id": "prog_a", "ci_status": "AT_RISK", "access_type": "direct"}}
        graph = _make_graph(
            nodes={"fv_1": _funding_node("fv_1", funding_type="Discretionary")},
            edges=[_funded_by_edge("prog_a", "fv_1")],
        )
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])

        # AT_RISK triggers LOGIC-02 (protect base), not LOGIC-04 (expand/strengthen)
        assert result["prog_a"]["rule"] == "LOGIC-02"


# ---------------------------------------------------------------------------
# Secondary Rules
# ---------------------------------------------------------------------------

class TestSecondaryRules:
    """secondary_rules collects other matching rules for transparency."""

    def test_urgent_with_restore_replace_secondary(self):
        """LOGIC-05 primary, LOGIC-01 in secondary."""
        programs = {"prog_a": {"id": "prog_a", "ci_status": "TERMINATED"}}
        graph = _make_graph(
            nodes={"auth_1": _authority_node("auth_1", durability="Permanent")},
            edges=[
                _threatens_edge("prog_a", days_remaining=10),
                _authorized_by_edge("prog_a", "auth_1"),
            ],
        )
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])

        assert result["prog_a"]["rule"] == "LOGIC-05"
        assert "LOGIC-01" in result["prog_a"]["secondary_rules"]

    def test_no_secondary_when_single_match(self):
        """Only one rule matches -- secondary_rules should be empty."""
        programs = {"prog_a": {"id": "prog_a", "ci_status": "STABLE"}}
        graph = _make_graph(edges=[_threatens_edge("prog_a", days_remaining=5)])
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])

        assert result["prog_a"]["secondary_rules"] == []

    def test_default_has_empty_secondary(self):
        programs = {"prog_a": {"id": "prog_a", "ci_status": "STABLE"}}
        graph = _make_graph()
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])

        assert result["prog_a"]["secondary_rules"] == []


# ---------------------------------------------------------------------------
# Edge Case: Graph data robustness
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Robustness: missing data, empty graphs, missing fields."""

    def test_empty_graph(self):
        programs = {"prog_a": {"id": "prog_a", "ci_status": "STABLE"}}
        graph = _make_graph()
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])

        assert result["prog_a"]["advocacy_goal"] is None

    def test_empty_programs(self):
        programs = {}
        graph = _make_graph()
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])

        assert result == {}

    def test_missing_ci_status(self):
        """Program without ci_status should not crash."""
        programs = {"prog_a": {"id": "prog_a"}}
        graph = _make_graph()
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])

        # Should get default -- no crash
        assert "prog_a" in result

    def test_graph_with_no_edges_key(self):
        """graph_data missing 'edges' entirely should not crash."""
        programs = {"prog_a": {"id": "prog_a", "ci_status": "STABLE"}}
        graph = {"nodes": {}}
        engine = DecisionEngine(_default_config(), programs)
        result = engine.classify_all(graph, [])

        assert "prog_a" in result

    def test_default_config_uses_30_days(self):
        """Config without decision_engine section defaults to 30 days."""
        programs = {"prog_a": {"id": "prog_a", "ci_status": "STABLE"}}
        graph = _make_graph(edges=[_threatens_edge("prog_a", days_remaining=25)])
        engine = DecisionEngine({}, programs)
        result = engine.classify_all(graph, [])

        assert result["prog_a"]["advocacy_goal"] == "URGENT_STABILIZATION"
