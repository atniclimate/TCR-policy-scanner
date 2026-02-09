"""TCR Policy Scanner — main pipeline orchestrator.

DAG Pipeline: Ingest -> Normalize -> Graph Construction -> Analysis -> Reporting

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
import sys
from pathlib import Path

from src.scrapers.federal_register import FederalRegisterScraper
from src.scrapers.grants_gov import GrantsGovScraper
from src.scrapers.congress_gov import CongressGovScraper
from src.analysis.relevance import RelevanceScorer
from src.analysis.change_detector import ChangeDetector
from src.graph.builder import GraphBuilder
from src.reports.generator import ReportGenerator

logger = logging.getLogger("tcr_scanner")

CONFIG_PATH = Path("config/scanner_config.json")
INVENTORY_PATH = Path("data/program_inventory.json")
GRAPH_OUTPUT_PATH = Path("outputs/LATEST-GRAPH.json")

SCRAPERS = {
    "federal_register": FederalRegisterScraper,
    "grants_gov": GrantsGovScraper,
    "congress_gov": CongressGovScraper,
}


def load_config() -> dict:
    """Load scanner configuration."""
    with open(CONFIG_PATH) as f:
        return json.load(f)


def load_programs() -> list[dict]:
    """Load the program inventory."""
    with open(INVENTORY_PATH) as f:
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
    print("\n=== DRY RUN ===")
    print(f"Pipeline: Ingest -> Normalize -> Graph Construction -> Analysis -> Reporting")
    print(f"Scan window: {config['scan_window_days']} days")
    print(f"Relevance threshold: {config['scoring']['relevance_threshold']}")
    print(f"\nSources to scan:")
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
    schema_path = Path("data/graph_schema.json")
    if schema_path.exists():
        with open(schema_path) as f:
            schema = json.load(f)
        print(f"\nKnowledge Graph schema:")
        print(f"  Authorities: {len(schema.get('authorities', []))}")
        print(f"  Funding vehicles: {len(schema.get('funding_vehicles', []))}")
        print(f"  Barriers: {len(schema.get('barriers', []))}")
    print()


async def run_scan(config: dict, programs: list[dict], sources: list[str]) -> list[dict]:
    """Execute scrapers and return all collected items (Ingest + Normalize)."""
    all_items = []
    for source_name in sources:
        if source_name not in SCRAPERS:
            logger.warning("Unknown source: %s", source_name)
            continue
        scraper_cls = SCRAPERS[source_name]
        scraper = scraper_cls(config)
        logger.info("Scanning %s...", source_name)
        try:
            items = await scraper.scan()
            all_items.extend(items)
            logger.info("  -> %d items from %s", len(items), source_name)
        except Exception:
            logger.exception("Failed to scan %s", source_name)
    return all_items


def build_graph(programs: list[dict], scored_items: list[dict]) -> dict:
    """Build the knowledge graph from scored items (Graph Construction)."""
    builder = GraphBuilder(programs)
    graph = builder.build(scored_items)
    graph_data = graph.to_dict()

    # Write graph output
    GRAPH_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(GRAPH_OUTPUT_PATH, "w") as f:
        json.dump(graph_data, f, indent=2, default=str)
    logger.info("Knowledge graph written to %s", GRAPH_OUTPUT_PATH)

    return graph_data


def run_pipeline(config: dict, programs: list[dict], sources: list[str],
                 report_only: bool = False, graph_only: bool = False) -> None:
    """Run the full DAG pipeline: Ingest -> Normalize -> Graph -> Analysis -> Report."""
    detector = ChangeDetector()
    scorer = RelevanceScorer(config, programs)

    if report_only or graph_only:
        logger.info("Loading cached results")
        previous = detector._load_previous()
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
        logger.info("Total raw items collected: %d", len(raw_items))

        # Stage 4: Analysis (scoring)
        scored = scorer.score_items(raw_items)
        changes = detector.detect_changes(scored)
        detector.save_current(scored)

    # Stage 3: Graph Construction
    graph_data = build_graph(programs, scored)

    if graph_only:
        print(f"\nGraph exported to {GRAPH_OUTPUT_PATH}")
        summary = graph_data["summary"]
        print(f"  Nodes: {summary['total_nodes']} ({summary['node_types']})")
        print(f"  Edges: {summary['total_edges']}")
        return

    # Stage 5: Reporting
    reporter = ReportGenerator(programs)
    paths = reporter.generate(scored, changes, graph_data)
    print(f"\nScan complete.")
    print(f"  Items scored above threshold: {len(scored)}")
    print(f"  New since last scan: {changes['summary']['new_count']}")
    print(f"  Knowledge graph: {graph_data['summary']['total_nodes']} nodes, {graph_data['summary']['total_edges']} edges")
    print(f"  Briefing: {paths['markdown']}")
    print(f"  JSON:     {paths['json']}")
    print(f"  Graph:    {GRAPH_OUTPUT_PATH}")


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
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    config = load_config()
    programs = load_programs()

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
