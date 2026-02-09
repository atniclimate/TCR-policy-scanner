"""Tribal Consultation Signal Monitor (MON-03).

Detects tribal consultation signals in scored items using tiered regex
pattern matching. Signals include Dear Tribal Leader Letters (DTLLs),
Executive Order 13175 references, and formal consultation notices.

These are informational signals, NOT threats -- they indicate active
government-to-government engagement. No THREATENS edges are created.
"""

import logging
import re

from src.monitors import BaseMonitor, MonitorAlert

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Compiled regex patterns (module-level, not per-call)
# ---------------------------------------------------------------------------

DTLL_PATTERNS = [
    re.compile(r"dear\s+tribal\s+leader", re.IGNORECASE),
    re.compile(r"\bDTLL\b"),
]

EO_13175_PATTERNS = [
    re.compile(r"Executive\s+Order\s+13175", re.IGNORECASE),
    re.compile(r"EO\s+13175"),
    re.compile(
        r"consultation\s+and\s+coordination\s+with\s+indian\s+tribal",
        re.IGNORECASE,
    ),
]

CONSULTATION_NOTICE_PATTERNS = [
    re.compile(
        r"tribal\s+consultation\s+(?:notice|meeting|session)", re.IGNORECASE
    ),
    re.compile(r"government-to-government\s+consultation", re.IGNORECASE),
    re.compile(r"nation-to-nation\s+consultation", re.IGNORECASE),
]

# Tier name -> (patterns list, signal_type string)
SIGNAL_TIERS = [
    ("DTLL", DTLL_PATTERNS, "dtll"),
    ("EO_13175", EO_13175_PATTERNS, "eo_13175"),
    ("CONSULTATION_NOTICE", CONSULTATION_NOTICE_PATTERNS, "consultation_notice"),
]


class TribalConsultationMonitor(BaseMonitor):
    """MON-03: Detects tribal consultation signals in scored items.

    Scans title, abstract, and action fields for DTLL references,
    EO 13175 citations, and formal consultation notices. One alert
    per signal_type per item (break after first match within a tier).

    All alerts are INFO severity -- consultations are informational
    signals, not threats. No THREATENS edges are created.
    """

    def check(
        self, graph_data: dict, scored_items: list[dict]
    ) -> list[MonitorAlert]:
        """Scan scored items for tribal consultation signals."""
        alerts: list[MonitorAlert] = []

        for item in scored_items:
            # Build searchable text from title + abstract + action fields
            title = item.get("title", "")
            abstract = item.get("abstract", "")
            action = item.get("action", item.get("latest_action", ""))
            searchable = f"{title} {abstract} {action}"

            if not searchable.strip():
                continue

            # Check each tier; one alert per signal_type per item
            for tier_name, patterns, signal_type in SIGNAL_TIERS:
                matched = False
                for pattern in patterns:
                    if pattern.search(searchable):
                        matched = True
                        break  # One match per tier is enough

                if matched:
                    source_id = item.get("source_id", "unknown")
                    url = item.get("url", "")
                    program_ids = item.get("matched_programs", [])

                    alerts.append(
                        MonitorAlert(
                            monitor="tribal_consultation",
                            severity="INFO",
                            program_ids=program_ids,
                            title=(
                                f"Tribal consultation signal ({tier_name}): "
                                f"{title[:80]}"
                            ),
                            detail=(
                                f"Detected {tier_name} signal in scored item: "
                                f"{title}. Signal type: {signal_type}. "
                                f"Source: {item.get('source', 'unknown')}."
                            ),
                            metadata={
                                "signal_type": signal_type,
                                "source": item.get("source", "unknown"),
                                "source_id": source_id,
                                "url": url,
                            },
                        )
                    )

        logger.info(
            "TribalConsultationMonitor: %d alerts from %d items",
            len(alerts),
            len(scored_items),
        )
        return alerts
