"""IIJA Sunset Monitor (MON-01).

Flags IIJA-funded programs approaching FY26 expiration with sunset
warnings, days remaining, and severity tiers. Scans Congress.gov scored
items for reauthorization signals -- if a reauth bill is detected for
a program, the sunset warning is suppressed.

IIJA FY26 programs (calendar deadline Sep 30, 2026):
  - epa_stag      (auth_iija)
  - dot_protect   (auth_protect_formula)
  - usbr_watersmart (auth_iija_watersmart)

IIJA fund-exhaustion programs (no calendar deadline):
  - usda_wildfire  (auth_iija_wildfire)
"""

import logging
from datetime import date

from src.monitors import BaseMonitor, MonitorAlert

logger = logging.getLogger(__name__)

# IIJA programs with FY26 calendar expiration (Sep 30, 2026)
IIJA_FY26_PROGRAMS = {
    "epa_stag": "auth_iija",
    "dot_protect": "auth_protect_formula",
    "usbr_watersmart": "auth_iija_watersmart",
}

# IIJA programs with fund-exhaustion expiration (no fixed date)
IIJA_FUND_EXHAUSTION_PROGRAMS = {
    "usda_wildfire": "auth_iija_wildfire",
}

# Keywords that signal a reauthorization bill in Congress.gov results
REAUTH_KEYWORDS = ["reauthorization", "reauthorize", "extension of"]


class IIJASunsetMonitor(BaseMonitor):
    """MON-01: Flags IIJA-funded programs approaching FY26 expiration.

    Produces CRITICAL/WARNING/INFO alerts based on days remaining.
    Also creates THREATENS edge metadata for MonitorRunner to add
    to the knowledge graph.
    """

    def __init__(self, config: dict, programs: dict):
        super().__init__(config, programs)
        monitor_config = config.get("monitors", {}).get("iija_sunset", {})
        self.warning_days = monitor_config.get("warning_days", 180)
        self.critical_days = monitor_config.get("critical_days", 90)
        fy26_end_str = monitor_config.get("fy26_end", "2026-09-30")
        self.fy26_end = date.fromisoformat(fy26_end_str)

    def check(self, graph_data: dict, scored_items: list[dict]) -> list[MonitorAlert]:
        """Check IIJA sunset status for all tracked programs."""
        alerts: list[MonitorAlert] = []
        today = date.today()
        days_remaining = (self.fy26_end - today).days

        # Scan scored items for reauthorization signals
        reauth_programs = self._detect_reauthorization(scored_items)

        # --- FY26 calendar-expiration programs ---
        for pid, auth_id in IIJA_FY26_PROGRAMS.items():
            program = self.programs.get(pid)
            if not program:
                continue

            # Skip if reauthorization bill detected for this program
            if pid in reauth_programs:
                logger.info(
                    "IIJA sunset: skipping %s -- reauthorization bill detected", pid
                )
                continue

            if days_remaining <= 0:
                # Already expired
                severity = "CRITICAL"
                title = f"IIJA EXPIRED: {program['name']} authorization has lapsed"
                detail = (
                    f"{program['name']} was funded under {auth_id} which expired "
                    f"on {self.fy26_end}. Authorization has lapsed. "
                    f"No reauthorization bill detected in scan results."
                )
            else:
                # Determine severity tier
                if days_remaining <= self.critical_days:
                    severity = "CRITICAL"
                elif days_remaining <= self.warning_days:
                    severity = "WARNING"
                else:
                    severity = "INFO"

                title = (
                    f"IIJA sunset: {program['name']} -- "
                    f"{days_remaining} days remaining"
                )
                detail = (
                    f"{program['name']} is funded under {auth_id} which expires "
                    f"September 30, 2026. {days_remaining} days remain. "
                    f"No reauthorization bill detected in scan results."
                )

            alerts.append(MonitorAlert(
                monitor="iija_sunset",
                severity=severity,
                program_ids=[pid],
                title=title,
                detail=detail,
                metadata={
                    "threat_type": "iija_sunset",
                    "deadline": str(self.fy26_end),
                    "days_remaining": max(days_remaining, 0),
                    "authority_id": auth_id,
                    "reauth_detected": False,
                    "creates_threatens_edge": True,
                },
            ))

        # --- Fund-exhaustion programs (separate alert type) ---
        for pid, auth_id in IIJA_FUND_EXHAUSTION_PROGRAMS.items():
            program = self.programs.get(pid)
            if not program:
                continue

            alerts.append(MonitorAlert(
                monitor="iija_sunset",
                severity="INFO",
                program_ids=[pid],
                title=(
                    f"IIJA fund-exhaustion: {program['name']} -- "
                    f"expires when funds exhausted"
                ),
                detail=(
                    f"{program['name']} is funded under {auth_id} with "
                    f"'expires when funds exhausted' durability. No fixed "
                    f"calendar deadline, but IIJA one-time allocation is finite. "
                    f"Monitor fund obligation rates for depletion signals."
                ),
                metadata={
                    "threat_type": "iija_fund_exhaustion",
                    "authority_id": auth_id,
                    "expiration_type": "fund_exhaustion",
                    "days_remaining": None,
                },
            ))

        logger.info(
            "IIJASunsetMonitor: %d alerts (days to FY26 end: %d)",
            len(alerts), days_remaining,
        )
        return alerts

    def _detect_reauthorization(self, scored_items: list[dict]) -> set[str]:
        """Scan Congress.gov items for reauthorization bill signals.

        Returns set of program_ids that have a reauth bill detected.
        """
        reauth_programs: set[str] = set()

        for item in scored_items:
            if item.get("source") != "congress_gov":
                continue

            text = (
                f"{item.get('title', '')} {item.get('abstract', '')}"
            ).lower()

            if any(kw in text for kw in REAUTH_KEYWORDS):
                for pid in item.get("matched_programs", []):
                    if pid in IIJA_FY26_PROGRAMS or pid in IIJA_FUND_EXHAUSTION_PROGRAMS:
                        reauth_programs.add(pid)
                        logger.info(
                            "Reauthorization signal for %s: %s",
                            pid, item.get("title", "")[:80],
                        )

        return reauth_programs
