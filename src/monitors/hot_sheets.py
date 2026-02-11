"""Hot Sheets Sync Validator (MON-04).

Compares CI status from the scanner with Hot Sheets positions stored
in program_inventory.json. When divergences are detected:

  1. First-time divergence: WARNING alert (prominent)
  2. Known divergence: INFO alert (silent log)
  3. Override: mutates in-memory program dict so downstream code
     (decision engine, reports) sees the Hot Sheets status

State persistence: Known divergences are tracked in
outputs/.monitor_state.json to distinguish first-time from
subsequent detections, following the pattern of outputs/.cfda_tracker.json
in src/scrapers/base.py.

Also checks for stale Hot Sheets data -- positions older than a
configurable threshold produce WARNING alerts.
"""

import json
import logging
from datetime import datetime, timezone

from src.monitors import BaseMonitor, MonitorAlert
from src.paths import MONITOR_STATE_PATH

logger = logging.getLogger(__name__)


class HotSheetsValidator(BaseMonitor):
    """MON-04: Validates scanner CI status against Hot Sheets positions.

    Detects divergences between scanner CI status and Hot Sheets status,
    applies in-memory overrides so downstream code uses Hot Sheets values,
    and persists known divergences to distinguish first-time from repeat.
    """

    def __init__(self, config: dict, programs: dict):
        super().__init__(config, programs)
        monitor_config = config.get("monitors", {}).get("hot_sheets", {})
        self.staleness_days = monitor_config.get("staleness_days", 90)

        # Load existing state
        self._state = self._load_state()
        self._known_divergences: set[str] = set(
            self._state.get("hot_sheets_known_divergences", [])
        )

    def check(
        self, graph_data: dict, scored_items: list[dict]
    ) -> list[MonitorAlert]:
        """Check Hot Sheets sync for all programs with hot_sheets_status."""
        alerts: list[MonitorAlert] = []
        now = datetime.now(timezone.utc)

        for pid, program in self.programs.items():
            hs = program.get("hot_sheets_status")
            if not hs:
                continue

            # --- Staleness check ---
            last_updated_str = hs.get("last_updated", "")
            if last_updated_str:
                try:
                    last_updated = datetime.fromisoformat(last_updated_str)
                    # If date-only string, it has no tzinfo -- treat as UTC
                    if last_updated.tzinfo is None:
                        last_updated = last_updated.replace(tzinfo=timezone.utc)
                    age_days = (now - last_updated).days
                    if age_days > self.staleness_days:
                        alerts.append(
                            MonitorAlert(
                                monitor="hot_sheets",
                                severity="WARNING",
                                program_ids=[pid],
                                title=(
                                    f"Stale Hot Sheets data: {program.get('name', pid)} "
                                    f"({age_days} days old)"
                                ),
                                detail=(
                                    f"Hot Sheets position for {program.get('name', pid)} "
                                    f"was last updated {last_updated_str} "
                                    f"({age_days} days ago). Threshold is "
                                    f"{self.staleness_days} days. Source: "
                                    f"{hs.get('source', 'unknown')}."
                                ),
                                metadata={
                                    "check_type": "staleness",
                                    "age_days": age_days,
                                    "threshold_days": self.staleness_days,
                                    "last_updated": last_updated_str,
                                },
                            )
                        )
                except (ValueError, TypeError) as e:
                    logger.warning(
                        "Hot Sheets: could not parse last_updated for %s: %s",
                        pid, e,
                    )

            # --- Divergence check ---
            ci_status = program.get("ci_status", "")
            hs_status = hs.get("status", "")

            if ci_status and hs_status and ci_status != hs_status:
                is_known = pid in self._known_divergences

                if is_known:
                    severity = "INFO"
                    prominence = "Previously known divergence"
                else:
                    severity = "WARNING"
                    prominence = "FIRST DETECTION - alerting prominently"

                alerts.append(
                    MonitorAlert(
                        monitor="hot_sheets",
                        severity=severity,
                        program_ids=[pid],
                        title=(
                            f"Hot Sheets divergence: {program.get('name', pid)} "
                            f"(CI={ci_status} vs HS={hs_status})"
                        ),
                        detail=(
                            f"{prominence}. Scanner CI status is {ci_status} but "
                            f"Hot Sheets position is {hs_status} for "
                            f"{program.get('name', pid)}. Applying Hot Sheets "
                            f"override. Source: {hs.get('source', 'unknown')}."
                        ),
                        metadata={
                            "check_type": "divergence",
                            "original_ci_status": ci_status,
                            "hot_sheets_status": hs_status,
                            "is_known_divergence": is_known,
                            "source": hs.get("source", "unknown"),
                        },
                    )
                )

                # Apply override: mutate in-memory program dict
                program["original_ci_status"] = ci_status
                program["ci_status"] = hs_status

                # Track divergence
                self._known_divergences.add(pid)

        # Save updated state
        self._save_state()

        logger.info(
            "HotSheetsValidator: %d alerts, %d known divergences",
            len(alerts),
            len(self._known_divergences),
        )
        return alerts

    def _load_state(self) -> dict:
        """Load monitor state from outputs/.monitor_state.json."""
        if MONITOR_STATE_PATH.exists():
            try:
                with open(MONITOR_STATE_PATH, encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Could not load monitor state: %s", e)
        return {}

    def _save_state(self) -> None:
        """Save monitor state to outputs/.monitor_state.json."""
        MONITOR_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._state["hot_sheets_known_divergences"] = sorted(
            self._known_divergences
        )
        try:
            tmp_path = MONITOR_STATE_PATH.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2)
            tmp_path.replace(MONITOR_STATE_PATH)
            logger.debug("Monitor state saved to %s", MONITOR_STATE_PATH)
        except OSError as e:
            logger.error("Could not save monitor state: %s", e)
