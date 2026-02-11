"""Agent review orchestrator for DOCX Hot Sheet production.

Python-side coordinator for the 3-pass review cycle. Manages critique
collection from 5 specialist agents, applies conflict resolution using
the priority hierarchy (accuracy > audience > political > design > copy),
and tracks revisions for the orchestrator agent to apply.

This module provides the data structures and algorithms; the actual
review agents are Claude Code agent definitions that produce JSON
critique objects consumed here.

Usage::

    reviewer = AgentReviewOrchestrator()
    reviewer.register_critiques("accuracy-agent", [...])
    reviewer.register_critiques("audience-director", [...])
    conflicts = reviewer.resolve_conflicts()
    gate = reviewer.check_quality_gate()
    log = reviewer.get_resolution_log()
"""

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AGENT_PRIORITY: dict[str, int] = {
    "accuracy-agent": 1,
    "audience-director": 2,
    "political-translator": 3,
    "design-aficionado": 4,
    "copy-editor": 5,
}
"""Conflict resolution priority (lower number = higher priority)."""

VALID_SEVERITIES = frozenset({"critical", "major", "minor"})

REQUIRED_CRITIQUE_FIELDS = frozenset({"agent", "section", "severity"})

MIN_AGENTS_FOR_QUALITY_GATE = 3
"""Minimum number of agents that must complete for the review to pass."""

MAX_PAGES = 2
"""Non-negotiable page limit for Hot Sheet documents."""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Critique:
    """A single review critique from a specialist agent."""

    agent: str
    section: str
    severity: str
    raw: dict = field(repr=False)

    @classmethod
    def from_dict(cls, data: dict) -> "Critique":
        """Create a Critique from a raw JSON dict.

        Validates required fields and severity values.

        Args:
            data: Raw critique dict from an agent.

        Returns:
            Validated Critique instance.

        Raises:
            ValueError: If required fields are missing or severity is invalid.
        """
        missing = REQUIRED_CRITIQUE_FIELDS - set(data.keys())
        if missing:
            raise ValueError(
                f"Critique missing required fields: {sorted(missing)}"
            )
        severity = data["severity"].lower()
        if severity not in VALID_SEVERITIES:
            raise ValueError(
                f"Invalid severity '{data['severity']}', "
                f"must be one of {sorted(VALID_SEVERITIES)}"
            )
        return cls(
            agent=data["agent"],
            section=data["section"],
            severity=severity,
            raw=data,
        )


@dataclass
class ConflictResolution:
    """Record of a resolved conflict between two agents."""

    section: str
    conflicting_agents: list[str]
    winner: str
    loser: str
    reason: str
    applied_critique: Critique


@dataclass
class AppliedRevision:
    """Record of a critique that was approved and applied."""

    source_agent: str
    section: str
    severity: str
    critique: Critique


# ---------------------------------------------------------------------------
# AgentReviewOrchestrator
# ---------------------------------------------------------------------------


class AgentReviewOrchestrator:
    """Coordinates the 3-pass DOCX agent review cycle.

    Pass 1: Draft generation (handled by DocxEngine, before this class).
    Pass 2: Parallel review — agents produce JSON critique arrays.
    Pass 3: Conflict resolution and revision application.

    This class handles Pass 2 collection and Pass 3 resolution.
    """

    def __init__(self, enabled: bool = False) -> None:
        """Initialize the orchestrator.

        Args:
            enabled: Whether agent review is active. When ``False``,
                all methods are no-ops that return empty results.
        """
        self.enabled = enabled
        self._critiques_by_agent: dict[str, list[Critique]] = {}
        self._completed_agents: set[str] = set()
        self._failed_agents: set[str] = set()
        self._conflicts: list[ConflictResolution] = []
        self._revisions: list[AppliedRevision] = []
        self._resolved = False

    @property
    def all_critiques(self) -> list[Critique]:
        """Flat list of all registered critiques across all agents."""
        result: list[Critique] = []
        for critiques in self._critiques_by_agent.values():
            result.extend(critiques)
        return result

    def register_critiques(
        self, agent_name: str, raw_critiques: list[dict]
    ) -> int:
        """Register critique results from a review agent.

        Validates each critique dict and stores valid ones. Invalid
        critiques are logged and skipped.

        Args:
            agent_name: Name of the agent (must be in AGENT_PRIORITY).
            raw_critiques: List of raw JSON critique dicts.

        Returns:
            Number of valid critiques registered.

        Raises:
            ValueError: If agent_name is not recognized.
        """
        if not self.enabled:
            return 0

        if agent_name not in AGENT_PRIORITY:
            raise ValueError(
                f"Unknown agent '{agent_name}'. "
                f"Valid agents: {sorted(AGENT_PRIORITY.keys())}"
            )

        valid: list[Critique] = []
        for i, raw in enumerate(raw_critiques):
            try:
                critique = Critique.from_dict(raw)
                valid.append(critique)
            except ValueError as exc:
                logger.warning(
                    "Skipping invalid critique %d from %s: %s",
                    i, agent_name, exc,
                )

        self._critiques_by_agent[agent_name] = valid
        self._completed_agents.add(agent_name)
        self._resolved = False  # Invalidate previous resolution

        logger.info(
            "Registered %d critiques from %s (%d skipped)",
            len(valid), agent_name, len(raw_critiques) - len(valid),
        )
        return len(valid)

    def mark_agent_failed(self, agent_name: str) -> None:
        """Record that an agent failed or timed out.

        Args:
            agent_name: Name of the failed agent.
        """
        if not self.enabled:
            return
        self._failed_agents.add(agent_name)
        logger.warning("Agent '%s' marked as failed", agent_name)

    def resolve_conflicts(self) -> list[ConflictResolution]:
        """Apply the conflict resolution algorithm.

        Groups critiques by section, identifies conflicts (same section,
        different agents with opposing recommendations), and resolves
        using the priority hierarchy.

        Returns:
            List of ConflictResolution records.
        """
        if not self.enabled:
            return []

        self._conflicts.clear()
        self._revisions.clear()

        # Group critiques by section
        by_section: dict[str, list[Critique]] = {}
        for critique in self.all_critiques:
            by_section.setdefault(critique.section, []).append(critique)

        for section, critiques in by_section.items():
            if len(critiques) <= 1:
                # No conflict possible — approve directly
                for c in critiques:
                    self._revisions.append(AppliedRevision(
                        source_agent=c.agent,
                        section=c.section,
                        severity=c.severity,
                        critique=c,
                    ))
                continue

            # Check for conflicts: multiple agents on the same section
            # Group by agent priority
            sorted_critiques = sorted(
                critiques,
                key=lambda c: AGENT_PRIORITY.get(c.agent, 99),
            )

            # Identify unique agents for this section
            agents_in_section = list(dict.fromkeys(
                c.agent for c in sorted_critiques
            ))

            if len(agents_in_section) > 1:
                # Potential conflict — highest priority agent wins
                winner_agent = agents_in_section[0]
                winner_priority = AGENT_PRIORITY.get(winner_agent, 99)

                for loser_agent in agents_in_section[1:]:
                    loser_priority = AGENT_PRIORITY.get(loser_agent, 99)
                    self._conflicts.append(ConflictResolution(
                        section=section,
                        conflicting_agents=[winner_agent, loser_agent],
                        winner=winner_agent,
                        loser=loser_agent,
                        reason=(
                            f"Higher priority "
                            f"({winner_agent}[{winner_priority}] > "
                            f"{loser_agent}[{loser_priority}])"
                        ),
                        applied_critique=sorted_critiques[0],
                    ))

            # Approve all critiques from the winning agent(s)
            # and non-conflicting critiques from lower-priority agents
            approved_agents = set()
            for c in sorted_critiques:
                if c.agent not in approved_agents or len(agents_in_section) == 1:
                    self._revisions.append(AppliedRevision(
                        source_agent=c.agent,
                        section=c.section,
                        severity=c.severity,
                        critique=c,
                    ))
                    approved_agents.add(c.agent)

        self._resolved = True
        logger.info(
            "Resolved %d conflicts, approved %d revisions",
            len(self._conflicts), len(self._revisions),
        )
        return self._conflicts

    def check_quality_gate(self) -> dict[str, Any]:
        """Check whether the review passes quality requirements.

        Quality gate conditions:
        - At least 3 of 5 agents completed
        - All critical-severity critiques addressed
        - No unresolved accuracy critiques

        Returns:
            Dict with ``passed`` bool and detail fields.
        """
        if not self.enabled:
            return {"passed": True, "enabled": False, "reason": "disabled"}

        if not self._resolved:
            self.resolve_conflicts()

        agents_completed = len(self._completed_agents)
        enough_agents = agents_completed >= MIN_AGENTS_FOR_QUALITY_GATE

        # Check critical critiques are all addressed
        critical_count = sum(
            1 for c in self.all_critiques if c.severity == "critical"
        )
        critical_resolved = sum(
            1 for r in self._revisions if r.severity == "critical"
        )
        all_critical_resolved = critical_resolved >= critical_count

        # Check no unresolved accuracy critiques
        accuracy_critiques = [
            c for c in self.all_critiques if c.agent == "accuracy-agent"
        ]
        accuracy_revisions = {
            (r.section, r.source_agent)
            for r in self._revisions
            if r.source_agent == "accuracy-agent"
        }
        unresolved_accuracy = sum(
            1 for c in accuracy_critiques
            if (c.section, c.agent) not in accuracy_revisions
        )

        passed = (
            enough_agents
            and all_critical_resolved
            and unresolved_accuracy == 0
        )

        result = {
            "passed": passed,
            "enabled": True,
            "agents_completed": agents_completed,
            "agents_failed": sorted(self._failed_agents),
            "enough_agents": enough_agents,
            "critical_total": critical_count,
            "critical_resolved": critical_resolved,
            "all_critical_resolved": all_critical_resolved,
            "unresolved_accuracy": unresolved_accuracy,
        }

        if not passed:
            reasons = []
            if not enough_agents:
                reasons.append(
                    f"Only {agents_completed}/{MIN_AGENTS_FOR_QUALITY_GATE} "
                    f"agents completed"
                )
            if not all_critical_resolved:
                reasons.append(
                    f"{critical_count - critical_resolved} critical "
                    f"critiques unresolved"
                )
            if unresolved_accuracy > 0:
                reasons.append(
                    f"{unresolved_accuracy} accuracy critiques unresolved"
                )
            result["reasons"] = reasons

        logger.info(
            "Quality gate: %s (agents=%d, critical=%d/%d, accuracy_unresolved=%d)",
            "PASSED" if passed else "FAILED",
            agents_completed, critical_resolved, critical_count,
            unresolved_accuracy,
        )
        return result

    def get_resolution_log(self) -> dict[str, Any]:
        """Return the full resolution log as a JSON-serializable dict.

        Returns:
            Dict matching the resolution log schema defined in
            ``review-orchestrator.md``.
        """
        if not self.enabled:
            return {"enabled": False}

        if not self._resolved:
            self.resolve_conflicts()

        by_severity: dict[str, int] = {"critical": 0, "major": 0, "minor": 0}
        for c in self.all_critiques:
            by_severity[c.severity] = by_severity.get(c.severity, 0) + 1

        return {
            "enabled": True,
            "pass_2_summary": {
                "agents_completed": sorted(self._completed_agents),
                "agents_failed": sorted(self._failed_agents),
                "total_critiques": len(self.all_critiques),
                "by_severity": by_severity,
            },
            "conflicts_resolved": [
                {
                    "section": cr.section,
                    "conflicting_agents": cr.conflicting_agents,
                    "winner": cr.winner,
                    "reason": cr.reason,
                }
                for cr in self._conflicts
            ],
            "revisions_applied": [
                {
                    "source_agent": r.source_agent,
                    "section": r.section,
                    "severity": r.severity,
                }
                for r in self._revisions
            ],
            "quality_gate": self.check_quality_gate(),
        }
