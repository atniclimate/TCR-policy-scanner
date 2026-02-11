#!/usr/bin/env python3
"""Populate award cache files from USASpending API.

Fetches Tribal government awards for all tracked CFDA numbers across
FY22-FY26, matches recipients to the 592-Tribe registry using
two-tier name resolution, and writes per-Tribe JSON cache files.

Usage:
    python scripts/populate_awards.py                    # All 592 Tribes
    python scripts/populate_awards.py --dry-run          # Fetch + match, no writes
    python scripts/populate_awards.py --tribe epa_100000001  # Single Tribe
    python scripts/populate_awards.py --report path.json  # Custom report path
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on sys.path for src imports
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.config import FISCAL_YEAR_INT
from src.paths import OUTPUTS_DIR, SCANNER_CONFIG_PATH
from src.scrapers.usaspending import CFDA_TO_PROGRAM, USASpendingScraper
from src.packets.awards import TribalAwardMatcher

logger = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Parsed argument namespace.
    """
    parser = argparse.ArgumentParser(
        description="Populate award cache files from USASpending API.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Fetch and match but don't write cache files.",
    )
    parser.add_argument(
        "--tribe",
        type=str,
        default=None,
        help="Process only this Tribe ID (still fetches all data).",
    )
    parser.add_argument(
        "--report",
        type=str,
        default=str(OUTPUTS_DIR / "award_population_report.json"),
        help="Path for JSON report (default: outputs/award_population_report.json).",
    )
    parser.add_argument(
        "--fy-start",
        type=int,
        default=FISCAL_YEAR_INT - 4,
        help=f"First fiscal year (default: {FISCAL_YEAR_INT - 4}).",
    )
    parser.add_argument(
        "--fy-end",
        type=int,
        default=FISCAL_YEAR_INT,
        help=f"Last fiscal year (default: {FISCAL_YEAR_INT}).",
    )
    return parser.parse_args(argv)


async def run_pipeline(args: argparse.Namespace) -> dict:
    """Execute the full award population pipeline.

    Steps:
        1. Load config and create scraper + matcher instances
        2. Fetch all Tribal awards via USASpending multi-year batch queries
        3. Deduplicate awards by Award ID
        4. Match awards to Tribes using two-tier name resolution
        5. Write per-Tribe cache files (unless --dry-run)
        6. Generate coverage report

    Args:
        args: Parsed CLI arguments.

    Returns:
        Report dict with coverage statistics.
    """
    fy_start = args.fy_start
    fy_end = args.fy_end

    # Load config
    with open(SCANNER_CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Create instances
    scraper = USASpendingScraper(config)
    matcher = TribalAwardMatcher(config)

    # Step 1: Fetch all Tribal awards across FY range
    logger.info(
        "Fetching Tribal awards for %d CFDAs across FY%d-FY%d...",
        len(CFDA_TO_PROGRAM), fy_start, fy_end,
    )
    awards_by_cfda = await scraper.fetch_all_tribal_awards_multi_year(
        fy_start=fy_start, fy_end=fy_end,
    )
    total_raw = sum(len(v) for v in awards_by_cfda.values())
    logger.info("Fetched %d total raw awards.", total_raw)

    # Step 2: Deduplicate
    deduped = matcher.deduplicate_awards(awards_by_cfda)
    total_deduped = sum(len(v) for v in deduped.values())
    logger.info(
        "After dedup: %d awards (removed %d duplicates).",
        total_deduped, total_raw - total_deduped,
    )

    # Step 3: Match to Tribes
    matched = matcher.match_all_awards(deduped)
    matched_count = sum(len(v) for v in matched.values())

    # Access unmatched and consortium from matcher state
    unmatched_awards = getattr(matcher, "_last_unmatched_awards", [])
    consortium_awards = getattr(matcher, "_last_consortium_awards", [])
    unmatched_count = len(unmatched_awards)

    logger.info(
        "Matched %d awards to %d Tribes. Unmatched: %d, Consortium: %d.",
        matched_count, len(matched), unmatched_count, len(consortium_awards),
    )

    # Step 4: Write cache files (unless --dry-run)
    files_written = 0
    if not args.dry_run:
        if args.tribe:
            # Filter to single Tribe
            single = {args.tribe: matched.get(args.tribe, [])}
            files_written = matcher.write_cache(single, fy_start, fy_end)
            logger.info("Wrote cache for single Tribe: %s", args.tribe)
        else:
            files_written = matcher.write_cache(matched, fy_start, fy_end)
            logger.info("Wrote %d cache files.", files_written)
    else:
        logger.info("Dry run -- skipping cache writes.")

    # Step 5: Build top unmatched names (aggregated by name)
    unmatched_by_name: dict[str, float] = {}
    for ua in unmatched_awards:
        name = ua.get("recipient_name", "UNKNOWN")
        unmatched_by_name[name] = unmatched_by_name.get(name, 0.0) + ua.get(
            "obligation", 0.0,
        )
    top_unmatched = sorted(
        [{"name": k, "total_obligation": v} for k, v in unmatched_by_name.items()],
        key=lambda x: x["total_obligation"],
        reverse=True,
    )[:20]

    # Step 6: Build consortium summary
    consortium_by_name: dict[str, float] = {}
    for ca in consortium_awards:
        name = ca.get("recipient_name", "UNKNOWN")
        consortium_by_name[name] = consortium_by_name.get(name, 0.0) + ca.get(
            "obligation", 0.0,
        )
    consortium_summary = sorted(
        [{"name": k, "total_obligation": v} for k, v in consortium_by_name.items()],
        key=lambda x: x["total_obligation"],
        reverse=True,
    )

    # Count Tribes with awards
    tribes_with_awards = sum(
        1 for tribe_id, awards in matched.items() if len(awards) > 0
    )

    # Step 7: Build report
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "fiscal_year_range": {"start": fy_start, "end": fy_end},
        "queries": {
            "cfda_count": len(CFDA_TO_PROGRAM),
            "fy_count": fy_end - fy_start + 1,
            "total_queries": len(CFDA_TO_PROGRAM) * (fy_end - fy_start + 1),
        },
        "fetched": {
            "total_awards": total_raw,
            "after_dedup": total_deduped,
            "duplicates_removed": total_raw - total_deduped,
        },
        "matching": {
            "matched_awards": matched_count,
            "unmatched_awards": unmatched_count,
            "consortium_awards": len(consortium_awards),
            "match_rate_pct": round(
                matched_count / max(total_deduped, 1) * 100, 1,
            ),
        },
        "coverage": {
            "total_tribes": 592,
            "tribes_with_awards": tribes_with_awards,
            "tribes_without_awards": 592 - tribes_with_awards,
            "coverage_pct": round(tribes_with_awards / 592 * 100, 1),
            "target_met": tribes_with_awards >= 450,
        },
        "top_unmatched": top_unmatched,
        "consortium_summary": consortium_summary,
        "dry_run": args.dry_run,
    }

    # Step 8: Write report JSON
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    logger.info("Report written to %s", report_path)

    # Step 9: Print console summary
    print()
    print("=== Award Population Report ===")
    print(f"Fiscal years: FY{fy_start % 100:02d} - FY{fy_end % 100:02d}")
    print(
        f"Queries: {report['queries']['total_queries']} "
        f"({report['queries']['cfda_count']} CFDAs x "
        f"{report['queries']['fy_count']} FYs)"
    )
    print(
        f"Awards fetched: {total_raw} (after dedup: {total_deduped})"
    )
    match_pct = report["matching"]["match_rate_pct"]
    print(
        f"Matched: {matched_count} ({match_pct}%) | "
        f"Unmatched: {unmatched_count} | "
        f"Consortium: {len(consortium_awards)}"
    )
    target_status = "PASS" if report["coverage"]["target_met"] else "FAIL"
    cov_pct = report["coverage"]["coverage_pct"]
    print(
        f"Coverage: {tribes_with_awards}/592 Tribes ({cov_pct}%) "
        f"-- target 450+: {target_status}"
    )
    if not args.dry_run:
        print(f"Cache files written: {files_written}")
    else:
        print("Cache files: SKIPPED (dry run)")
    print(f"Report: {report_path}")
    print()

    return report


def main() -> None:
    """Entry point for the award population script."""
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    asyncio.run(run_pipeline(args))


if __name__ == "__main__":
    main()
