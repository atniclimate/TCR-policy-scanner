"""Reconciliation Bill Monitor (MON-02).

Detects active bills threatening IRA Section 6417 elective pay,
distinguishing from the already-enacted OBBBA (Public Law 119-21).

CRITICAL PITFALL AVOIDANCE:
  The One Big Beautiful Bill Act (Public Law 119-21, signed July 4, 2025)
  modified but did NOT fully repeal Section 6417. It imposed new
  begin-construction deadlines. The monitor MUST filter out references
  to this enacted law and only flag NEW active bills.
"""

import logging

from src.monitors import BaseMonitor, MonitorAlert

logger = logging.getLogger(__name__)

# Status indicators that a bill is no longer an active threat
ENACTED_STATUS_KEYWORDS = [
    "signed", "became public law", "enacted", "public law",
    "approved by the president",
]


class ReconciliationMonitor(BaseMonitor):
    """MON-02: Detects active reconciliation bills threatening IRA Section 6417.

    Scans Congress.gov scored items for reconciliation/repeal keywords,
    filtering out enacted laws (especially OBBBA / Public Law 119-21)
    to avoid false positives from historical bills.
    """

    def __init__(self, config: dict, programs: dict):
        super().__init__(config, programs)
        monitor_config = config.get("monitors", {}).get("reconciliation", {})
        self.keywords = [
            kw.lower() for kw in
            monitor_config.get("keywords", [
                "reconciliation", "repeal", "section 6417",
                "elective pay", "IRA repeal", "direct pay termination",
            ])
        ]
        self.active_bill_statuses = monitor_config.get(
            "active_bill_statuses",
            ["introduced", "committee", "floor", "conference"],
        )
        self.enacted_laws_exclude = monitor_config.get(
            "enacted_laws_exclude", ["Public Law 119-21"]
        )
        # Use decision engine urgency threshold for days_remaining
        # (reconciliation timelines are unpredictable)
        de_config = config.get("monitors", {}).get("decision_engine", {})
        self.urgency_threshold_days = de_config.get("urgency_threshold_days", 30)

    def check(self, graph_data: dict, scored_items: list[dict]) -> list[MonitorAlert]:
        """Scan scored items for active reconciliation threats."""
        alerts: list[MonitorAlert] = []

        for item in scored_items:
            if item.get("source") != "congress_gov":
                continue

            title = item.get("title", "")
            abstract = item.get("abstract", "")
            text = f"{title} {abstract}".lower()

            # Check if item matches any reconciliation keyword
            if not any(kw in text for kw in self.keywords):
                continue

            # CRITICAL: Filter out enacted laws (e.g., OBBBA / Public Law 119-21)
            if self._is_enacted_law(item, text):
                logger.debug(
                    "Reconciliation: skipping enacted law: %s", title[:80]
                )
                continue

            # Check latest_action to see if bill is still active
            if self._is_historical_bill(item):
                logger.debug(
                    "Reconciliation: skipping historical bill: %s", title[:80]
                )
                continue

            # Active reconciliation bill detected
            source_id = item.get("source_id", "unknown")

            affected_programs = item.get("matched_programs", [])
            if not affected_programs:
                affected_programs = list(self.programs.keys())
            alerts.append(MonitorAlert(
                monitor="reconciliation",
                severity="WARNING",
                program_ids=affected_programs,
                title=(
                    f"Reconciliation threat: {title[:80]}"
                ),
                detail=(
                    f"Active bill detected in Congress.gov that may threaten "
                    f"IRA Section 6417 (Elective Pay). Bill: {title}. "
                    f"Source ID: {source_id}. This is an active legislative "
                    f"threat -- not the already-enacted OBBBA."
                ),
                metadata={
                    "threat_type": "reconciliation",
                    "creates_threatens_edge": True,
                    "bill_id": source_id,
                    "bill_title": title,
                    "description": title,
                    "days_remaining": self.urgency_threshold_days,
                    "matched_keywords": [
                        kw for kw in self.keywords if kw in text
                    ],
                },
            ))

            logger.info(
                "ReconciliationMonitor: active threat detected: %s",
                title[:80],
            )

        logger.info(
            "ReconciliationMonitor: %d alerts from %d congress_gov items",
            len(alerts),
            sum(1 for i in scored_items if i.get("source") == "congress_gov"),
        )
        return alerts

    def _is_enacted_law(self, item: dict, text: str) -> bool:
        """Check if item references an enacted law that should be excluded.

        Filters out the OBBBA (Public Law 119-21) and any other enacted
        laws listed in the config exclusion list.
        """
        # Check config exclusion list
        for law_ref in self.enacted_laws_exclude:
            if law_ref.lower() in text:
                return True
        # Check common OBBBA aliases not in config
        obbba_aliases = ["obbba", "one big beautiful bill"]
        if any(alias in text for alias in obbba_aliases):
            return True
        return False

    def _is_historical_bill(self, item: dict) -> bool:
        """Check if the bill's latest_action indicates it is enacted/historical.

        Bills that have been signed into law or became public law are
        not active threats -- they are already part of the legal landscape.
        """
        latest_action = item.get("latest_action", "")
        if not latest_action:
            return False

        action_lower = latest_action.lower()
        return any(kw in action_lower for kw in ENACTED_STATUS_KEYWORDS)
