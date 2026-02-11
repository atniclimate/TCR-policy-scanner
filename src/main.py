"""TCR Policy Scanner — main pipeline orchestrator.

DAG Pipeline: Ingest -> Normalize -> Graph Construction -> Monitors -> Decision Engine -> Reporting

Usage:
    python -m src.main              # Full scan
    python -m src.main --programs   # List tracked programs
    python -m src.main --dry-run    # Show what would be scanned
    python -m src.main --source federal_register  # Scan one source
    python -m src.main --report-only              # Regenerate report from cache
    python -m src.main --graph-only               # Export knowledge graph from cache
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.scrapers.circuit_breaker import CircuitOpenError
from src.scrapers.federal_register import FederalRegisterScraper
from src.scrapers.grants_gov import GrantsGovScraper
from src.scrapers.congress_gov import CongressGovScraper
from src.scrapers.usaspending import USASpendingScraper
from src.analysis.relevance import RelevanceScorer
from src.analysis.change_detector import ChangeDetector
from src.graph.builder import GraphBuilder
from src.reports.generator import ReportGenerator
from src.monitors import MonitorRunner
from src.analysis.decision_engine import DecisionEngine
from src.paths import (
    GRAPH_SCHEMA_PATH,
    LATEST_GRAPH_PATH,
    LATEST_MONITOR_DATA_PATH,
    OUTPUTS_DIR,
    PROGRAM_INVENTORY_PATH,
    SCANNER_CONFIG_PATH,
)

logger = logging.getLogger(__name__)

SCRAPERS = {
    "federal_register": FederalRegisterScraper,
    "grants_gov": GrantsGovScraper,
    "congress_gov": CongressGovScraper,
    "usaspending": USASpendingScraper,
}


def load_config() -> dict:
    """Load scanner configuration."""
    with open(SCANNER_CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_programs() -> list[dict]:
    """Load the program inventory."""
    with open(PROGRAM_INVENTORY_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data["programs"]


def list_programs(programs: list[dict]) -> None:
    """Print the tracked program inventory with CI status."""
    print(f"\nTracked Programs ({len(programs)}):")
    print("-" * 80)
    for p in programs:
        priority_tag = f"[{p['priority'].upper()}]"
        ci = p.get("confidence_index")
        ci_str = f"CI:{ci * 100:.0f}%" if ci is not None else ""
        status = p.get("ci_status", "")
        print(f"  {priority_tag:10s} {p['name']:35s} ({p['agency']}) {ci_str} {status}")
        print(f"{'':12s} Lever: {p['advocacy_lever']}")
        if p.get("ci_determination"):
            det = p["ci_determination"][:70]
            print(f"{'':12s} CI: {det}")
    print()


def dry_run(config: dict, programs: list[dict], sources: list[str]) -> None:
    """Show what would be scanned without making API calls."""
    domain = config.get("domain_name", config.get("domain", "unknown"))
    print(f"\n=== DRY RUN === [{domain}]")
    print("Pipeline: Ingest -> Normalize -> Graph -> Monitors -> Decision Engine -> Reporting")
    print(f"Scan window: {config['scan_window_days']} days")
    print(f"Relevance threshold: {config['scoring']['relevance_threshold']}")
    print("\nSources to scan:")
    for name in sources:
        src = config["sources"].get(name, {})
        key_needed = src.get("requires_key", False)
        status = "ready" if not key_needed else "needs API key"
        print(f"  - {src.get('name', name)} ({status})")

    # CFDA coverage
    from src.scrapers.grants_gov import CFDA_NUMBERS
    print(f"\nCFDA-targeted programs ({len(CFDA_NUMBERS)}):")
    for cfda, pid in sorted(CFDA_NUMBERS.items()):
        prog = next((p for p in programs if p["id"] == pid), None)
        name = prog["name"] if prog else pid
        print(f"  - {cfda}: {name}")

    print(f"\nSearch queries ({len(config['search_queries'])}):")
    for q in config["search_queries"]:
        print(f"  - {q}")

    # Graph schema summary
    if GRAPH_SCHEMA_PATH.exists():
        with open(GRAPH_SCHEMA_PATH, encoding="utf-8") as f:
            schema = json.load(f)
        print("\nKnowledge Graph schema:")
        print(f"  Authorities: {len(schema.get('authorities', []))}")
        print(f"  Funding vehicles: {len(schema.get('funding_vehicles', []))}")
        print(f"  Barriers: {len(schema.get('barriers', []))}")

    # Monitor configuration
    monitor_config = config.get("monitors", {})
    if monitor_config:
        print("\nMonitor configuration:")
        for name, mc in monitor_config.items():
            print(f"  - {name}")

    print()


def _source_cache_path(source_name: str) -> Path:
    """Return the per-source cache file path in the outputs directory."""
    return OUTPUTS_DIR / f".cache_{source_name}.json"


def _save_source_cache(source_name: str, items: list[dict]) -> None:
    """Persist scan results to per-source cache with atomic write.

    JSON structure includes timestamp metadata for staleness detection.
    Uses tmp file + os.replace() for crash safety (CLAUDE.md rule 8).
    """
    cache_path = _source_cache_path(source_name)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = cache_path.with_suffix(".tmp")
    try:
        data = {
            "source": source_name,
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "item_count": len(items),
            "items": items,
        }
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        os.replace(str(tmp_path), str(cache_path))
        logger.info("Cached %d items for %s", len(items), source_name)
    except Exception:
        logger.exception("Failed to save cache for %s", source_name)
        # Clean up tmp file on failure
        if tmp_path.exists():
            tmp_path.unlink()


def _load_source_cache(source_name: str, config: dict | None = None) -> list[dict]:
    """Load cached scan results for a source as fallback when API is unreachable.

    Returns an empty list if no cache exists or cache is corrupt.
    Logs WARNING with cache age for degradation visibility.
    Logs CRITICAL if cache exceeds cache_max_age_hours (default 168h = 7 days).

    Single-writer-per-source assumption: only one pipeline run writes a given
    source cache at a time. Concurrent reads during write are safe due to
    atomic os.replace() in _save_source_cache.
    """
    cache_path = _source_cache_path(source_name)
    if not cache_path.exists():
        logger.warning("No cached data available for %s", source_name)
        return []
    try:
        # Security: check file size before parsing (10MB cap)
        file_size = cache_path.stat().st_size
        if file_size > 10 * 1024 * 1024:
            logger.error("Cache file too large for %s (%d bytes), skipping", source_name, file_size)
            return []

        with open(cache_path, encoding="utf-8") as f:
            data = json.load(f)

        cached_at = data.get("cached_at", "unknown")
        logger.warning("DEGRADED: %s using cached data from %s", source_name, cached_at)

        # Check staleness against configured max age
        cache_max_age_hours = (config or {}).get("resilience", {}).get("cache_max_age_hours", 168)
        if cached_at != "unknown":
            try:
                cache_time = datetime.fromisoformat(cached_at)
                age_hours = (datetime.now(timezone.utc) - cache_time).total_seconds() / 3600
                if age_hours > cache_max_age_hours:
                    logger.critical(
                        "STALE CACHE: %s cache is %.0fh old (limit: %dh)",
                        source_name, age_hours, cache_max_age_hours,
                    )
            except (ValueError, TypeError):
                pass

        return data.get("items", [])
    except (json.JSONDecodeError, IOError) as e:
        logger.error("Failed to load cache for %s: %s", source_name, e)
        return []


async def run_scan(config: dict, programs: list[dict], sources: list[str]) -> list[dict]:
    """Execute scrapers concurrently and return all collected items (Ingest + Normalize).

    On successful scan, caches results per source. On CircuitOpenError or any
    other exception, falls back to cached data so the pipeline can continue
    in degraded mode.
    """
    async def _run_one(source_name: str) -> list[dict]:
        if source_name not in SCRAPERS:
            logger.warning("Unknown source: %s", source_name)
            return []
        scraper_cls = SCRAPERS[source_name]
        scraper = scraper_cls(config)
        logger.info("Scanning %s...", source_name)
        try:
            items = await scraper.scan()
            logger.info("  -> %d items from %s", len(items), source_name)
            if items:
                _save_source_cache(source_name, items)
            return items
        except CircuitOpenError:
            logger.warning("DEGRADED: %s circuit OPEN, falling back to cache", source_name)
            return _load_source_cache(source_name, config)
        except Exception:
            logger.exception("Failed to scan %s, falling back to cache", source_name)
            return _load_source_cache(source_name, config)

    results = await asyncio.gather(*[_run_one(s) for s in sources])
    all_items = []
    for result in results:
        all_items.extend(result)
    logger.info("Total raw items collected: %d", len(all_items))
    return all_items


def build_graph(programs: list[dict], scored_items: list[dict]) -> dict:
    """Build the knowledge graph from scored items (Graph Construction)."""
    builder = GraphBuilder(programs)
    graph = builder.build(scored_items)
    graph_data = graph.to_dict()

    # Write graph output (atomic)
    LATEST_GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = LATEST_GRAPH_PATH.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(graph_data, f, indent=2, default=str)
    tmp_path.replace(LATEST_GRAPH_PATH)
    logger.info("Knowledge graph written to %s", LATEST_GRAPH_PATH)

    return graph_data


def run_monitors_and_classify(
    config: dict, programs_dict: dict, graph_data: dict, scored: list[dict]
) -> tuple[list, dict, dict]:
    """Run monitors and decision engine. Returns (alerts, classifications, monitor_data).

    This stage runs after graph construction and before reporting:
        Graph -> [HotSheets -> Monitors -> Decision Engine] -> Report
    """
    # Stage 3.5: Monitors (detect threats, consultation signals, Hot Sheets sync)
    monitor_runner = MonitorRunner(config, programs_dict)
    alerts = monitor_runner.run_all(graph_data, scored)
    logger.info("Monitors produced %d alerts", len(alerts))

    # Stage 3.6: Decision Engine (classify programs into advocacy goals)
    decision_engine = DecisionEngine(config, programs_dict)
    classifications = decision_engine.classify_all(graph_data, alerts)
    logger.info("Classified %d programs into advocacy goals", len(classifications))

    # Build monitor data dict for output
    monitor_data = {
        "alerts": [
            {
                "monitor": a.monitor,
                "severity": a.severity,
                "program_ids": a.program_ids,
                "title": a.title,
                "detail": a.detail,
                "metadata": a.metadata,
                "timestamp": a.timestamp,
            }
            for a in alerts
        ],
        "classifications": classifications,
        "summary": {
            "total_alerts": len(alerts),
            "critical_count": sum(1 for a in alerts if a.severity == "CRITICAL"),
            "warning_count": sum(1 for a in alerts if a.severity == "WARNING"),
            "info_count": sum(1 for a in alerts if a.severity == "INFO"),
            "monitors_run": sorted(set(a.monitor for a in alerts)),
        },
    }

    # Save monitor data for Phase 4 reporting (atomic)
    LATEST_MONITOR_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = LATEST_MONITOR_DATA_PATH.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(monitor_data, f, indent=2, default=str)
    tmp_path.replace(LATEST_MONITOR_DATA_PATH)
    logger.info("Monitor data written to %s", LATEST_MONITOR_DATA_PATH)

    return alerts, classifications, monitor_data


def run_pipeline(config: dict, programs: list[dict], sources: list[str],
                 report_only: bool = False, graph_only: bool = False) -> None:
    """Run the full DAG pipeline: Ingest -> Normalize -> Graph -> Monitors -> Decision -> Report."""
    detector = ChangeDetector()
    scorer = RelevanceScorer(config, programs)

    if report_only or graph_only:
        logger.info("Loading cached results")
        previous = detector.load_cached()
        if not previous:
            logger.error("No cached results found. Run a full scan first.")
            sys.exit(1)
        scored = scorer.score_items(previous)
        changes = {"new_items": [], "updated_items": [], "removed_items": [],
                    "summary": {"new_count": 0, "updated_count": 0,
                                "removed_count": 0, "total_current": len(scored),
                                "total_previous": len(scored)}}
    else:
        # Stage 1-2: Ingest + Normalize
        raw_items = asyncio.run(run_scan(config, programs, sources))

        # Stage 4: Analysis (scoring)
        scored = scorer.score_items(raw_items)
        changes = detector.detect_changes(scored)
        detector.save_current(scored)

    # Stage 3: Graph Construction
    graph_data = build_graph(programs, scored)

    # Stage 3.5-3.6: Monitors + Decision Engine
    # programs_dict is needed by monitors and decision engine (keyed by program_id).
    # Hot Sheets validator mutates program dicts in-place, which is fine since
    # they are the same objects used downstream.
    programs_dict = {p["id"]: p for p in programs}
    alerts, classifications, monitor_data = run_monitors_and_classify(
        config, programs_dict, graph_data, scored
    )

    if graph_only:
        print(f"\nGraph exported to {LATEST_GRAPH_PATH}")
        summary = graph_data["summary"]
        print(f"  Nodes: {summary['total_nodes']} ({summary['node_types']})")
        print(f"  Edges: {summary['total_edges']}")
        print(f"  Monitor alerts: {len(alerts)} ({monitor_data['summary']['critical_count']} critical)")
        print(f"  Advocacy goals: {len([c for c in classifications.values() if c.get('advocacy_goal')])} classified")
        print(f"  Monitor data: {LATEST_MONITOR_DATA_PATH}")
        return

    # Stage 5: Reporting
    reporter = ReportGenerator(programs)
    paths = reporter.generate(
        scored, changes, graph_data,
        monitor_data=monitor_data,
        classifications=classifications,
    )
    print("\nScan complete.")
    print(f"  Items scored above threshold: {len(scored)}")
    print(f"  New since last scan: {changes['summary']['new_count']}")
    print(f"  Knowledge graph: {graph_data['summary']['total_nodes']} nodes, {graph_data['summary']['total_edges']} edges")
    print(f"  Monitor alerts: {len(alerts)} ({monitor_data['summary']['critical_count']} critical)")
    print(f"  Advocacy goals: {len([c for c in classifications.values() if c.get('advocacy_goal')])} classified")
    print(f"  Briefing: {paths['markdown']}")
    print(f"  JSON:     {paths['json']}")
    print(f"  Graph:    {LATEST_GRAPH_PATH}")
    print(f"  Monitor data: {LATEST_MONITOR_DATA_PATH}")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="TCR Policy Scanner — Automated policy intelligence for Tribal Climate Resilience"
    )
    parser.add_argument("--programs", action="store_true", help="List tracked programs with CI status")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be scanned")
    parser.add_argument("--source", type=str, help="Scan a specific source only")
    parser.add_argument("--report-only", action="store_true", help="Regenerate report from cached data")
    parser.add_argument("--graph-only", action="store_true", help="Export knowledge graph from cached data")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--prep-packets", action="store_true",
                        help="Generate Tribe-specific advocacy packets")
    parser.add_argument("--tribe", type=str,
                        help="Tribe name for single packet (used with --prep-packets)")
    parser.add_argument("--all-tribes", action="store_true",
                        help="Generate for all Tribes (used with --prep-packets)")
    parser.add_argument("--health-check", action="store_true",
                        help="Check API availability for all sources")
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    config = load_config()
    programs = load_programs()

    if args.health_check:
        from src.health import HealthChecker, format_report
        checker = HealthChecker(config)
        results = asyncio.run(checker.check_all())
        print(format_report(results))
        return

    if args.prep_packets:
        if not args.tribe and not args.all_tribes:
            print("Error: --prep-packets requires either --tribe <name> or --all-tribes")
            print("Usage:")
            print("  python -m src.main --prep-packets --tribe 'Navajo Nation'")
            print("  python -m src.main --prep-packets --all-tribes")
            sys.exit(1)
        from src.packets.orchestrator import PacketOrchestrator
        orch = PacketOrchestrator(config, programs)
        if args.tribe:
            orch.run_single_tribe(args.tribe)
        else:
            orch.run_all_tribes()
        return

    if args.programs:
        list_programs(programs)
        return

    sources = list(SCRAPERS.keys())
    if args.source:
        if args.source not in SCRAPERS:
            print(f"Unknown source: {args.source}")
            print(f"Available: {', '.join(SCRAPERS.keys())}")
            sys.exit(1)
        sources = [args.source]

    if args.dry_run:
        dry_run(config, programs, sources)
        return

    run_pipeline(config, programs, sources,
                 report_only=args.report_only, graph_only=args.graph_only)


if __name__ == "__main__":
    main()
