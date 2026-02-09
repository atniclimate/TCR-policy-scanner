"""Monitor framework for TCR Policy Scanner.

Provides the base classes and runner for threat-detection monitors
that analyze the knowledge graph and scored items to detect
time-sensitive legislative threats, producing alerts and THREATENS edges.

Exports:
    MonitorAlert  -- standard alert dataclass
    BaseMonitor   -- abstract base class for all monitors
    MonitorRunner -- orchestrator that runs all monitors
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Severity ordering for alert sorting (lower index = higher priority)
_SEVERITY_ORDER = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}


@dataclass
class MonitorAlert:
    """Standard alert produced by any monitor.

    Fields:
        monitor:     Monitor name (e.g. "iija_sunset", "reconciliation")
        severity:    "CRITICAL", "WARNING", or "INFO"
        program_ids: List of affected program IDs
        title:       Short human-readable summary
        detail:      Full explanation
        metadata:    Monitor-specific data (threat_type, deadline, etc.)
        timestamp:   ISO-format UTC timestamp (auto-set)
    """
    monitor: str
    severity: str
    program_ids: list[str]
    title: str
    detail: str
    metadata: dict = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class BaseMonitor(ABC):
    """Abstract base class for all monitors.

    Follows the same simple class hierarchy pattern as BaseScraper
    in src/scrapers/base.py -- no external dependencies, just logging
    and a consistent interface.
    """

    def __init__(self, config: dict, programs: dict):
        """Initialize with scanner config and program inventory.

        Args:
            config:   Full scanner_config.json dict
            programs: Dict mapping program_id -> program dict
        """
        self.config = config
        self.programs = programs

    @abstractmethod
    def check(self, graph_data: dict, scored_items: list[dict]) -> list[MonitorAlert]:
        """Run the monitor check against current graph state and scored items.

        Args:
            graph_data:    Serialized knowledge graph dict with nodes/edges
            scored_items:  List of scored policy items from scraping

        Returns:
            List of MonitorAlert objects (may be empty)
        """
        ...


class MonitorRunner:
    """Orchestrator that instantiates and runs all registered monitors.

    After collecting alerts, scans for THREATENS edge metadata and
    adds corresponding edges to graph_data for decision engine consumption.
    """

    def __init__(self, config: dict, programs: dict):
        self.config = config
        self.programs = programs
        self._monitors: list[BaseMonitor] = []
        self._init_monitors()

    def _init_monitors(self) -> None:
        """Import and instantiate all available monitors.

        Order matters: HotSheetsValidator runs FIRST because it applies
        CI status overrides that affect decision engine classifications.
        Then threat monitors, then consultation (informational) monitor.
        """
        # Lazy imports to avoid circular dependencies and allow
        # individual monitors to be developed independently

        # --- HotSheetsValidator MUST run first (CI override) ---
        try:
            from src.monitors.hot_sheets import HotSheetsValidator
            self._monitors.append(HotSheetsValidator(self.config, self.programs))
        except ImportError:
            logger.warning("HotSheetsValidator not available")

        # --- Threat monitors ---
        try:
            from src.monitors.iija_sunset import IIJASunsetMonitor
            self._monitors.append(IIJASunsetMonitor(self.config, self.programs))
        except ImportError:
            logger.warning("IIJASunsetMonitor not available")

        try:
            from src.monitors.reconciliation import ReconciliationMonitor
            self._monitors.append(ReconciliationMonitor(self.config, self.programs))
        except ImportError:
            logger.warning("ReconciliationMonitor not available")

        try:
            from src.monitors.dhs_funding import DHSFundingCliffMonitor
            self._monitors.append(DHSFundingCliffMonitor(self.config, self.programs))
        except ImportError:
            logger.warning("DHSFundingCliffMonitor not available")

        # --- Informational monitors ---
        try:
            from src.monitors.tribal_consultation import TribalConsultationMonitor
            self._monitors.append(TribalConsultationMonitor(self.config, self.programs))
        except ImportError:
            logger.warning("TribalConsultationMonitor not available")

        logger.info("MonitorRunner initialized with %d monitors", len(self._monitors))

    def run_all(self, graph_data: dict, scored_items: list[dict]) -> list[MonitorAlert]:
        """Run all monitors and collect alerts.

        Also adds THREATENS edges to graph_data for any alert whose
        metadata contains creates_threatens_edge=True.

        Args:
            graph_data:    Mutable graph dict (edges list will be extended)
            scored_items:  Scored policy items from scraping

        Returns:
            All alerts sorted by severity (CRITICAL first, then WARNING, then INFO)
        """
        all_alerts: list[MonitorAlert] = []

        for monitor in self._monitors:
            monitor_name = type(monitor).__name__
            try:
                alerts = monitor.check(graph_data, scored_items)
                logger.info(
                    "%s produced %d alerts", monitor_name, len(alerts)
                )
                all_alerts.extend(alerts)
            except Exception:
                logger.exception("Error running %s", monitor_name)

        # Add THREATENS edges to graph for alerts that request it
        self._add_threatens_edges(graph_data, all_alerts)

        # Sort by severity: CRITICAL first, then WARNING, then INFO
        all_alerts.sort(key=lambda a: _SEVERITY_ORDER.get(a.severity, 99))

        logger.info(
            "MonitorRunner complete: %d total alerts (%d CRITICAL, %d WARNING, %d INFO)",
            len(all_alerts),
            sum(1 for a in all_alerts if a.severity == "CRITICAL"),
            sum(1 for a in all_alerts if a.severity == "WARNING"),
            sum(1 for a in all_alerts if a.severity == "INFO"),
        )

        return all_alerts

    def _add_threatens_edges(self, graph_data: dict, alerts: list[MonitorAlert]) -> None:
        """Scan alerts for THREATENS edge metadata and add edges to graph_data.

        Monitors signal edge creation by including these keys in metadata:
            creates_threatens_edge: True
            threat_type: str (e.g. "iija_sunset", "reconciliation")
        """
        if "edges" not in graph_data:
            graph_data["edges"] = []

        edges_added = 0
        for alert in alerts:
            meta = alert.metadata
            if not meta.get("creates_threatens_edge"):
                continue

            threat_type = meta.get("threat_type", "unknown")

            for program_id in alert.program_ids:
                threat_node_id = f"threat_{threat_type}_{program_id}"
                edge = {
                    "source": threat_node_id,
                    "target": program_id,
                    "type": "THREATENS",
                    "metadata": {
                        "threat_type": threat_type,
                        "deadline": meta.get("deadline", ""),
                        "days_remaining": meta.get("days_remaining"),
                        "description": alert.title,
                        "monitor": alert.monitor,
                        "severity": alert.severity,
                    },
                }
                graph_data["edges"].append(edge)
                edges_added += 1

        if edges_added:
            logger.info("Added %d THREATENS edges to graph", edges_added)
