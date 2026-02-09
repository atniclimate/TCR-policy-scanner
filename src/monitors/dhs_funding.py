"""DHS Funding Cliff Monitor (MON-05).

Tracks the DHS Continuing Resolution expiration date and surfaces
FEMA-related programs when the funding cliff approaches. Also scans
Congress.gov items for new DHS appropriations or CR bills.

As of research date (Feb 2026), DHS was funded only through
February 13, 2026 via a CR, with full-year funding unresolved.
The cr_expiration date is configurable in scanner_config.json.
"""

import logging
from datetime import date

from src.monitors import BaseMonitor, MonitorAlert

logger = logging.getLogger(__name__)

# Keywords indicating a DHS appropriations or CR bill
DHS_FUNDING_KEYWORDS = [
    "dhs appropriations",
    "homeland security funding",
    "homeland security appropriations",
    "department of homeland security appropriations",
]

# Keywords that in combination with CR keywords indicate DHS-related CR
DHS_CR_KEYWORDS = [
    ("continuing resolution", "homeland"),
    ("continuing resolution", "dhs"),
    ("continuing appropriations", "homeland"),
    ("continuing appropriations", "dhs"),
]


class DHSFundingCliffMonitor(BaseMonitor):
    """MON-05: Detects DHS CR expiration proximity for FEMA programs.

    Produces CRITICAL alerts when the CR has expired, WARNING alerts
    when expiration is within warning_days, and notes any new DHS
    funding bills detected in scan results.
    """

    def __init__(self, config: dict, programs: dict):
        super().__init__(config, programs)
        monitor_config = config.get("monitors", {}).get("dhs_funding", {})
        cr_exp_str = monitor_config.get("cr_expiration", "2026-02-13")
        self.cr_expiration = date.fromisoformat(cr_exp_str)
        self.fema_program_ids = monitor_config.get(
            "fema_program_ids", ["fema_bric", "fema_tribal_mitigation"]
        )
        self.warning_days = monitor_config.get("warning_days", 14)

    def check(self, graph_data: dict, scored_items: list[dict]) -> list[MonitorAlert]:
        """Check DHS funding cliff status."""
        alerts: list[MonitorAlert] = []
        today = date.today()
        days_remaining = (self.cr_expiration - today).days

        # Scan for new DHS funding bills
        dhs_bills = self._detect_dhs_funding_bills(scored_items)

        if days_remaining <= 0:
            # CR has expired
            for pid in self.fema_program_ids:
                program = self.programs.get(pid)
                if not program:
                    continue

                bill_note = ""
                if dhs_bills:
                    bill_note = (
                        f" Note: {len(dhs_bills)} DHS funding bill(s) detected "
                        f"in scan results, but passage is not guaranteed."
                    )

                alerts.append(MonitorAlert(
                    monitor="dhs_funding",
                    severity="CRITICAL",
                    program_ids=[pid],
                    title=(
                        f"DHS CR EXPIRED: {program['name']} funding at risk"
                    ),
                    detail=(
                        f"The DHS Continuing Resolution expired on "
                        f"{self.cr_expiration}. {program['name']} (FEMA) "
                        f"may be affected by the funding lapse. "
                        f"{abs(days_remaining)} days since expiration."
                        f"{bill_note}"
                    ),
                    metadata={
                        "threat_type": "dhs_funding_cliff",
                        "deadline": str(self.cr_expiration),
                        "days_remaining": 0,
                        "days_since_expiration": abs(days_remaining),
                        "creates_threatens_edge": True,
                        "dhs_bills_detected": len(dhs_bills),
                    },
                ))

        elif days_remaining <= self.warning_days:
            # CR expiration approaching
            for pid in self.fema_program_ids:
                program = self.programs.get(pid)
                if not program:
                    continue

                bill_note = ""
                if dhs_bills:
                    bill_note = (
                        f" Note: {len(dhs_bills)} DHS funding bill(s) detected "
                        f"in scan results, but passage is not guaranteed."
                    )

                alerts.append(MonitorAlert(
                    monitor="dhs_funding",
                    severity="WARNING",
                    program_ids=[pid],
                    title=(
                        f"DHS funding cliff: {program['name']} -- "
                        f"{days_remaining} days to CR expiration"
                    ),
                    detail=(
                        f"The DHS Continuing Resolution expires on "
                        f"{self.cr_expiration}. {days_remaining} days remain. "
                        f"{program['name']} (FEMA) may be affected if DHS "
                        f"funding lapses.{bill_note}"
                    ),
                    metadata={
                        "threat_type": "dhs_funding_cliff",
                        "deadline": str(self.cr_expiration),
                        "days_remaining": days_remaining,
                        "creates_threatens_edge": True,
                        "dhs_bills_detected": len(dhs_bills),
                    },
                ))

        # If DHS bills detected but no funding cliff alert, still note them
        if dhs_bills and days_remaining > self.warning_days:
            alerts.append(MonitorAlert(
                monitor="dhs_funding",
                severity="INFO",
                program_ids=self.fema_program_ids,
                title=(
                    f"DHS funding activity: {len(dhs_bills)} bill(s) detected"
                ),
                detail=(
                    f"Detected {len(dhs_bills)} DHS appropriations/CR bill(s) "
                    f"in scan results. Current CR expires {self.cr_expiration} "
                    f"({days_remaining} days). Bills: "
                    + "; ".join(b[:80] for b in dhs_bills)
                ),
                metadata={
                    "dhs_bills": dhs_bills,
                    "cr_expiration": str(self.cr_expiration),
                    "days_remaining": days_remaining,
                },
            ))

        logger.info(
            "DHSFundingCliffMonitor: %d alerts (days to CR exp: %d)",
            len(alerts), days_remaining,
        )
        return alerts

    def _detect_dhs_funding_bills(self, scored_items: list[dict]) -> list[str]:
        """Scan Congress.gov items for DHS appropriations or CR bills.

        Returns list of bill titles that reference DHS funding.
        """
        dhs_bills: list[str] = []

        for item in scored_items:
            if item.get("source") != "congress_gov":
                continue

            title = item.get("title", "")
            text = f"{title} {item.get('abstract', '')}".lower()

            # Direct DHS funding keywords
            if any(kw in text for kw in DHS_FUNDING_KEYWORDS):
                dhs_bills.append(title)
                continue

            # CR + DHS combination keywords
            for cr_kw, dhs_kw in DHS_CR_KEYWORDS:
                if cr_kw in text and dhs_kw in text:
                    dhs_bills.append(title)
                    break

        return dhs_bills
