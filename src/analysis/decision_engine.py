"""Advocacy Goal Decision Engine.

Classifies each tracked program into one of five advocacy goals based on
its knowledge graph state, CI status, and monitor alerts. The five goals
(in priority order) are:

  LOGIC-05  Urgent Stabilization  -- THREATENS edge within urgency window
  LOGIC-01  Restore/Replace       -- TERMINATED/FLAGGED + active authority
  LOGIC-02  Protect Base          -- discretionary funding + eliminate/reduce signals
  LOGIC-03  Direct Access Parity  -- state pass-through + high admin burden
  LOGIC-04  Expand and Strengthen -- STABLE/SECURE + direct/set-aside access

Every program receives a classification dict or an explicit 'no match'
with reason. The primary match wins; all other matching rules are
collected into secondary_rules for transparency.

Exports:
    ADVOCACY_GOALS  -- constant mapping goal keys to human labels
    DecisionEngine  -- classifier class with classify_all() method
"""

import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ADVOCACY_GOALS = {
    "URGENT_STABILIZATION": "Urgent Stabilization",
    "RESTORE_REPLACE": "Restore/Replace",
    "PROTECT_BASE": "Protect Base",
    "DIRECT_ACCESS_PARITY": "Direct Access Parity",
    "EXPAND_STRENGTHEN": "Expand and Strengthen",
}

# ---------------------------------------------------------------------------
# DecisionEngine
# ---------------------------------------------------------------------------

class DecisionEngine:
    """Classifies programs into advocacy goals using 5 decision rules.

    Constructor args:
        config:   Full scanner_config.json dict (reads monitors.decision_engine section)
        programs: Dict mapping program_id -> program dict from inventory
    """

    def __init__(self, config: dict, programs: dict):
        self.config = config
        self.programs = programs
        self.urgency_threshold_days = (
            config
            .get("monitors", {})
            .get("decision_engine", {})
            .get("urgency_threshold_days", 30)
        )

    # -- Public API ---------------------------------------------------------

    def classify_all(
        self, graph_data: dict, alerts: list
    ) -> dict[str, dict]:
        """Classify every program. Returns {program_id: classification_dict}.

        Args:
            graph_data: Serialized knowledge graph dict with nodes/edges
            alerts:     List of MonitorAlert objects from monitors

        Returns:
            Dict mapping each program_id to its classification dict.
        """
        results: dict[str, dict] = {}
        for pid, program in self.programs.items():
            classification = self._classify_program(pid, program, graph_data, alerts)
            results[pid] = classification
            logger.debug(
                "Classified %s -> %s (%s) confidence=%s",
                pid,
                classification.get("advocacy_goal"),
                classification.get("rule"),
                classification.get("confidence"),
            )
        return results

    # -- Core classification ------------------------------------------------

    def _classify_program(
        self, pid: str, program: dict, graph_data: dict, alerts: list
    ) -> dict:
        """Apply all 5 rules, collect matches, return highest-priority as primary."""

        # Evaluate every rule and collect (rule_id, classification) pairs
        rule_checks = [
            ("LOGIC-05", self._check_urgent_stabilization(pid, graph_data, alerts)),
            ("LOGIC-01", self._check_restore_replace(pid, program, graph_data)),
            ("LOGIC-02", self._check_protect_base(pid, program, graph_data, alerts)),
            ("LOGIC-03", self._check_direct_access_parity(pid, program, graph_data)),
            ("LOGIC-04", self._check_expand_strengthen(pid, program, graph_data)),
        ]

        # Separate matches from non-matches
        matches: list[tuple[str, dict]] = [
            (rule_id, result)
            for rule_id, result in rule_checks
            if result is not None
        ]

        if not matches:
            return {
                "advocacy_goal": None,
                "goal_label": None,
                "rule": None,
                "confidence": "LOW",
                "reason": "No decision rule matched for this program",
                "secondary_rules": [],
            }

        # First match is the primary (list is already in priority order)
        primary_rule_id, primary_result = matches[0]
        secondary_rules = [rule_id for rule_id, _ in matches[1:]]

        primary_result["secondary_rules"] = secondary_rules
        return primary_result

    # -- Rule implementations -----------------------------------------------

    def _check_urgent_stabilization(
        self, pid: str, graph_data: dict, alerts: list
    ) -> dict | None:
        """LOGIC-05: THREATENS edge within urgency_threshold_days overrides all.

        Queries graph_data edges for THREATENS edges targeting this program
        where days_remaining <= threshold.
        """
        threatens_edges = _get_edges_for_program(
            graph_data, pid, "THREATENS", direction="target"
        )

        for edge in threatens_edges:
            days = edge.get("metadata", {}).get("days_remaining", 999)
            if days <= self.urgency_threshold_days:
                description = edge.get("metadata", {}).get("description", "")
                return {
                    "advocacy_goal": "URGENT_STABILIZATION",
                    "goal_label": ADVOCACY_GOALS["URGENT_STABILIZATION"],
                    "rule": "LOGIC-05",
                    "confidence": "HIGH",
                    "reason": (
                        f"THREATENS edge: {description} "
                        f"({days} days remaining, threshold {self.urgency_threshold_days})"
                    ),
                }
        return None

    def _check_restore_replace(
        self, pid: str, program: dict, graph_data: dict
    ) -> dict | None:
        """LOGIC-01: TERMINATED or FLAGGED program with active/permanent authority.

        FLAGGED is treated as near-terminated. Checks AUTHORIZED_BY edges
        to authorities with 'permanent' or 'active' in durability field.
        """
        ci_status = program.get("ci_status", "")
        if ci_status not in ("TERMINATED", "FLAGGED"):
            return None

        auth_edges = _get_edges_for_program(
            graph_data, pid, "AUTHORIZED_BY", direction="source"
        )

        for edge in auth_edges:
            auth_id = edge.get("target", "")
            auth_node = graph_data.get("nodes", {}).get(auth_id, {})
            durability = auth_node.get("durability", "").lower()

            if "permanent" in durability or "active" in durability:
                return {
                    "advocacy_goal": "RESTORE_REPLACE",
                    "goal_label": ADVOCACY_GOALS["RESTORE_REPLACE"],
                    "rule": "LOGIC-01",
                    "confidence": "HIGH",
                    "reason": (
                        f"Program is {ci_status} but authorized under "
                        f"{auth_node.get('citation', 'unknown')} "
                        f"(durability: {auth_node.get('durability', 'unknown')})"
                    ),
                }
        return None

    def _check_protect_base(
        self, pid: str, program: dict, graph_data: dict, alerts: list
    ) -> dict | None:
        """LOGIC-02: Discretionary-funded program facing eliminate/reduce signals.

        Triggers when:
        - Program has discretionary funding (FUNDED_BY edge to FundingVehicleNode
          with funding_type containing 'discretionary', or program dict field)
        - AND has eliminate/reduce signals in alerts, or ci_status is AT_RISK/UNCERTAIN
        """
        has_discretionary = self._has_discretionary_funding(pid, program, graph_data)
        if not has_discretionary:
            return None

        # Check for eliminate/reduce signals
        has_threat_signal = self._has_eliminate_reduce_signal(pid, program, graph_data, alerts)

        if has_threat_signal:
            return {
                "advocacy_goal": "PROTECT_BASE",
                "goal_label": ADVOCACY_GOALS["PROTECT_BASE"],
                "rule": "LOGIC-02",
                "confidence": "HIGH" if program.get("ci_status") in ("AT_RISK", "FLAGGED") else "MEDIUM",
                "reason": (
                    f"Discretionary-funded program with threat signals "
                    f"(ci_status: {program.get('ci_status', 'unknown')})"
                ),
            }
        return None

    def _check_direct_access_parity(
        self, pid: str, program: dict, graph_data: dict
    ) -> dict | None:
        """LOGIC-03: State pass-through program with high administrative barriers.

        Checks program access_type for 'state_pass_through' and BLOCKED_BY edges
        to barriers with severity='High' and barrier_type='Administrative'.
        """
        access_type = program.get("access_type", "")
        if access_type != "state_pass_through":
            return None

        # Check for high-severity administrative barriers
        barrier_edges = _get_edges_for_program(
            graph_data, pid, "BLOCKED_BY", direction="source"
        )

        for edge in barrier_edges:
            bar_id = edge.get("target", "")
            bar_node = graph_data.get("nodes", {}).get(bar_id, {})
            severity = bar_node.get("severity", "").lower()
            barrier_type = bar_node.get("barrier_type", "").lower()

            if severity == "high" and barrier_type == "administrative":
                return {
                    "advocacy_goal": "DIRECT_ACCESS_PARITY",
                    "goal_label": ADVOCACY_GOALS["DIRECT_ACCESS_PARITY"],
                    "rule": "LOGIC-03",
                    "confidence": "MEDIUM",
                    "reason": (
                        f"State pass-through program with high administrative "
                        f"barrier: {bar_node.get('description', 'unknown')}"
                    ),
                }
        return None

    def _check_expand_strengthen(
        self, pid: str, program: dict, graph_data: dict
    ) -> dict | None:
        """LOGIC-04: STABLE/SECURE program with direct or set-aside access.

        ci_status must be STABLE, SECURE, or STABLE_BUT_VULNERABLE.
        access_type must be 'direct', 'set_aside', or 'tribal_set_aside'.
        """
        eligible_statuses = ("STABLE", "SECURE", "STABLE_BUT_VULNERABLE")
        eligible_access = ("direct", "set_aside", "tribal_set_aside")

        ci_status = program.get("ci_status", "")
        access_type = program.get("access_type", "")

        if ci_status not in eligible_statuses:
            return None
        if access_type not in eligible_access:
            return None

        return {
            "advocacy_goal": "EXPAND_STRENGTHEN",
            "goal_label": ADVOCACY_GOALS["EXPAND_STRENGTHEN"],
            "rule": "LOGIC-04",
            "confidence": "MEDIUM",
            "reason": (
                f"Program is {ci_status} with {access_type} access -- "
                f"positioned for expansion and strengthening"
            ),
        }

    # -- Helper methods -----------------------------------------------------

    def _has_discretionary_funding(
        self, pid: str, program: dict, graph_data: dict
    ) -> bool:
        """Check if program has discretionary funding via edges or program field."""
        # Check FUNDED_BY edges
        funding_edges = _get_edges_for_program(
            graph_data, pid, "FUNDED_BY", direction="source"
        )
        for edge in funding_edges:
            fv_id = edge.get("target", "")
            fv_node = graph_data.get("nodes", {}).get(fv_id, {})
            funding_type = fv_node.get("funding_type", "").lower()
            if "discretionary" in funding_type:
                return True

        # Fall back to program-level field
        program_funding = program.get("funding_type", "").lower()
        if "discretionary" in program_funding:
            return True

        return False

    def _has_eliminate_reduce_signal(
        self, pid: str, program: dict, graph_data: dict, alerts: list
    ) -> bool:
        """Check for eliminate/reduce threat signals.

        Signals come from:
        1. Alerts with program_id matching this program and eliminate/reduce in title/detail
        2. THREATENS edges in graph
        3. ci_status is AT_RISK or UNCERTAIN (with discretionary funding already confirmed)
        """
        # Check alerts for eliminate/reduce signals
        for alert in alerts:
            alert_pids = getattr(alert, "program_ids", [])
            if pid in alert_pids:
                alert_text = (
                    f"{getattr(alert, 'title', '')} {getattr(alert, 'detail', '')}"
                ).lower()
                if "eliminate" in alert_text or "reduce" in alert_text:
                    return True

        # Check for THREATENS edges
        threatens = _get_edges_for_program(
            graph_data, pid, "THREATENS", direction="target"
        )
        if threatens:
            return True

        # ci_status AT_RISK or UNCERTAIN with discretionary funding is a signal
        ci_status = program.get("ci_status", "")
        if ci_status in ("AT_RISK", "UNCERTAIN"):
            return True

        return False


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _get_edges_for_program(
    graph_data: dict,
    program_id: str,
    edge_type: str,
    direction: str = "any",
) -> list[dict]:
    """Filter graph_data edges for a program by type and direction.

    Args:
        graph_data:  Serialized graph dict with 'edges' list
        program_id:  The program node ID
        edge_type:   Edge type string (e.g. 'THREATENS', 'AUTHORIZED_BY')
        direction:   'source' (pid is source), 'target' (pid is target), or 'any'

    Returns:
        List of matching edge dicts.
    """
    edges = graph_data.get("edges", [])
    results = []
    for e in edges:
        if e.get("type") != edge_type:
            continue
        if direction == "source" and e.get("source") == program_id:
            results.append(e)
        elif direction == "target" and e.get("target") == program_id:
            results.append(e)
        elif direction == "any" and (
            e.get("source") == program_id or e.get("target") == program_id
        ):
            results.append(e)
    return results
