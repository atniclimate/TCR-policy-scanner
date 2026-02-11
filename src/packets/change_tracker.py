"""PacketChangeTracker -- detects differences between packet generations.

Stores per-Tribe state snapshots as JSON in a configurable state directory
(default: ``data/packet_state/{tribe_id}.json``).  On each generation, the
tracker compares the current state against the previous snapshot and returns
a list of human-readable change dicts.

First generation (no previous state): returns empty changes list; the
"Since Last Packet" section is omitted entirely.

Security considerations:
    - Path traversal protection via ``Path(tribe_id).name`` + reject ``.``/``..``
    - JSON cache size limit: 10 MB cap via ``stat().st_size`` before ``json.load()``
    - Atomic write: tmp file + ``os.replace()`` with cleanup on exception
    - All file I/O uses ``encoding="utf-8"``

Concurrency:
    Assumes single-writer-per-tribe_id. If parallel generation for the same
    Tribe is needed, use external locking or a task queue with per-tribe_id
    worker affinity.
"""

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from src.packets.context import TribePacketContext
from src.paths import PACKET_STATE_DIR

logger = logging.getLogger(__name__)

MAX_STATE_FILE_SIZE: int = 10 * 1024 * 1024  # 10 MB


class PacketChangeTracker:
    """Tracks state between packet generations to detect meaningful changes.

    Usage::

        tracker = PacketChangeTracker()
        previous = tracker.load_previous("epa_123")
        current = tracker.compute_current(context, programs)
        changes = tracker.diff(previous, current) if previous else []
        tracker.save_current("epa_123", current)

    Concurrency:
        Assumes single-writer-per-tribe_id. Do not run multiple concurrent
        generations for the same Tribe without external coordination.
    """

    def __init__(self, state_dir: Path | None = None) -> None:
        """Initialize the tracker with a state directory.

        Args:
            state_dir: Directory for per-Tribe state JSON files.
                Defaults to ``Path("data/packet_state")``.
        """
        self.state_dir = state_dir or PACKET_STATE_DIR

    def _safe_path(self, tribe_id: str) -> Path:
        """Build a safe file path for a tribe_id, preventing path traversal.

        Args:
            tribe_id: Tribe identifier.

        Returns:
            Path to the state JSON file inside ``self.state_dir``.

        Raises:
            ValueError: If tribe_id resolves to an unsafe path component.
        """
        safe_id = Path(tribe_id).name
        if not safe_id or safe_id in (".", ".."):
            raise ValueError(f"Invalid tribe_id: {tribe_id!r}")
        return self.state_dir / f"{safe_id}.json"

    def load_previous(self, tribe_id: str) -> dict | None:
        """Load the previous state snapshot for a Tribe.

        Returns ``None`` for first-generation (file missing) or when the
        state file is corrupt/oversized.  Corrupt files are treated as
        first-generation to allow graceful degradation.

        Args:
            tribe_id: Tribe identifier.

        Returns:
            Previous state dict, or None if unavailable.
        """
        path = self._safe_path(tribe_id)
        if not path.exists():
            logger.debug("No previous state for %s (first generation)", tribe_id)
            return None

        try:
            file_size = path.stat().st_size
        except OSError:
            logger.warning("Cannot stat state file for %s", tribe_id)
            return None

        if file_size > MAX_STATE_FILE_SIZE:
            logger.warning(
                "State file for %s exceeds size limit (%d bytes > %d), "
                "treating as first generation",
                tribe_id, file_size, MAX_STATE_FILE_SIZE,
            )
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                logger.warning("State file for %s is not a dict, ignoring", tribe_id)
                return None
            return data
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(
                "Corrupt state file for %s: %s (treating as first generation)",
                tribe_id, exc,
            )
            return None

    def compute_current(
        self, context: TribePacketContext, programs: dict
    ) -> dict:
        """Snapshot the current state from context and programs.

        The snapshot schema captures tribe_id, generation timestamp,
        per-program CI statuses, total awards, total obligation, and
        top hazard types.

        Args:
            context: Fully populated TribePacketContext.
            programs: Dict of program dicts keyed by program ID.

        Returns:
            State snapshot dict.
        """
        # Per-program CI status (from program inventory)
        program_states: dict[str, str] = {}
        for pid, prog in programs.items():
            ci_status = prog.get("ci_status", "")
            if ci_status:
                program_states[pid] = ci_status

        # Total awards and obligation
        total_awards = len(context.awards) if context.awards else 0
        total_obligation = 0.0
        for award in (context.awards or []):
            obligation = award.get("obligation", 0.0)
            if isinstance(obligation, (int, float)):
                total_obligation += obligation

        # Top hazards
        hazard_profile = context.hazard_profile or {}
        fema_nri = hazard_profile.get("fema_nri") or hazard_profile.get(
            "sources", {}
        ).get("fema_nri", {})
        top_hazards_raw = fema_nri.get("top_hazards", []) if fema_nri else []
        top_hazards = [h.get("type", "Unknown") for h in top_hazards_raw[:5]]

        # Advocacy goal: derive from top hazard + award status
        advocacy_goal = "new_applicant" if total_awards == 0 else "renewal"

        return {
            "tribe_id": context.tribe_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "program_states": program_states,
            "total_awards": total_awards,
            "total_obligation": total_obligation,
            "top_hazards": top_hazards,
            "advocacy_goal": advocacy_goal,
        }

    def diff(self, previous: dict, current: dict) -> list[dict]:
        """Detect changes between previous and current state snapshots.

        Change types:
            - ci_status_change: A program's CI status changed.
            - new_award: Total award count increased.
            - award_total_change: Total obligation amount changed.
            - advocacy_goal_shift: Advocacy goal changed (e.g. new_applicant -> renewal).
            - new_threat: A new hazard type appeared in top hazards.

        Args:
            previous: Previous state dict from ``load_previous()``.
            current: Current state dict from ``compute_current()``.

        Returns:
            List of change dicts, each with ``type`` and ``description`` keys.
            Empty list if no changes detected.
        """
        changes: list[dict] = []

        # CI status changes
        prev_states = previous.get("program_states", {})
        curr_states = current.get("program_states", {})
        for pid, curr_status in curr_states.items():
            prev_status = prev_states.get(pid, "")
            if prev_status and prev_status != curr_status:
                changes.append({
                    "type": "ci_status_change",
                    "description": (
                        f"Program {pid}: CI status changed from "
                        f"'{prev_status}' to '{curr_status}'"
                    ),
                })

        # New awards
        prev_awards = previous.get("total_awards", 0)
        curr_awards = current.get("total_awards", 0)
        if curr_awards > prev_awards:
            new_count = curr_awards - prev_awards
            changes.append({
                "type": "new_award",
                "description": (
                    f"{new_count} new award(s) recorded "
                    f"(total: {prev_awards} -> {curr_awards})"
                ),
            })

        # Award total change
        prev_obligation = previous.get("total_obligation", 0.0)
        curr_obligation = current.get("total_obligation", 0.0)
        if abs(curr_obligation - prev_obligation) > 0.01:
            changes.append({
                "type": "award_total_change",
                "description": (
                    f"Total obligation changed: "
                    f"${prev_obligation:,.0f} -> ${curr_obligation:,.0f}"
                ),
            })

        # Advocacy goal shift
        prev_goal = previous.get("advocacy_goal", "")
        curr_goal = current.get("advocacy_goal", "")
        if prev_goal and curr_goal and prev_goal != curr_goal:
            changes.append({
                "type": "advocacy_goal_shift",
                "description": (
                    f"Advocacy goal shifted from '{prev_goal}' to '{curr_goal}'"
                ),
            })

        # New threats
        prev_hazards = set(previous.get("top_hazards", []))
        curr_hazards = set(current.get("top_hazards", []))
        new_hazards = curr_hazards - prev_hazards
        for hazard in sorted(new_hazards):
            changes.append({
                "type": "new_threat",
                "description": f"New hazard threat detected: {hazard}",
            })

        return changes

    def save_current(self, tribe_id: str, state: dict) -> None:
        """Persist the current state snapshot using atomic write.

        Writes to a temporary file first, then atomically replaces the
        target path. This prevents partial/corrupt files on crash.

        Concurrency:
            Assumes single-writer-per-tribe_id. If parallel packet
            generation is needed, use external locking.

        Args:
            tribe_id: Tribe identifier.
            state: State snapshot dict from ``compute_current()``.

        Raises:
            ValueError: If tribe_id contains path traversal sequences.
        """
        path = self._safe_path(tribe_id)
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Atomic write: tmp file + os.replace
        tmp_fd = tempfile.NamedTemporaryFile(
            dir=str(self.state_dir),
            suffix=".json",
            mode="w",
            encoding="utf-8",
            delete=False,
        )
        tmp_name = tmp_fd.name
        try:
            json.dump(state, tmp_fd, indent=2, ensure_ascii=False)
            tmp_fd.close()
            os.replace(tmp_name, str(path))
            logger.debug("Saved state for %s: %s", tribe_id, path)
        except Exception:
            tmp_fd.close()
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise
