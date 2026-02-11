"""Populate hazard profiles for all 592 Tribes.

Runs the full FEMA NRI + USFS wildfire data pipeline:
  1. Loads NRI county CSV and tribal relational CSV from data/nri/
  2. Loads pre-computed area-weighted crosswalk from data/nri/tribal_county_area_weights.json
  3. Loads USFS wildfire XLSX from data/usfs/
  4. Builds area-weighted hazard profiles for each Tribe
  5. Writes 592 JSON profile files to data/hazard_profiles/
  6. Generates coverage report to outputs/

Prerequisites:
  - Run scripts/download_nri_data.py first (downloads NRI data + shapefiles)
  - Run scripts/build_area_crosswalk.py second (computes area weights)
  - Run scripts/download_usfs_data.py third (downloads USFS data)

Usage:
    python scripts/populate_hazards.py                  # Default
    python scripts/populate_hazards.py --verbose         # Debug logging
    python scripts/populate_hazards.py --dry-run         # Show what would be done
    python scripts/populate_hazards.py --tribe epa_001   # Single Tribe (debugging)
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

# Ensure project root is on sys.path for src imports
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.paths import (
    HAZARD_PROFILES_DIR,
    NRI_DIR,
    OUTPUTS_DIR,
    SCANNER_CONFIG_PATH,
    USFS_DIR,
    TRIBAL_COUNTY_WEIGHTS_PATH,
)

logger = logging.getLogger(__name__)


def check_prerequisites() -> dict:
    """Check if required data files exist.

    Returns:
        Dict with boolean flags for each prerequisite.
    """
    nri_csv = NRI_DIR / "NRI_Table_Counties.csv"
    crosswalk = TRIBAL_COUNTY_WEIGHTS_PATH
    usfs_xlsx_files = list(USFS_DIR.glob("*.xlsx")) if USFS_DIR.exists() else []

    prereqs = {
        "nri_county_csv": nri_csv.exists(),
        "area_crosswalk": crosswalk.exists(),
        "usfs_xlsx": len(usfs_xlsx_files) > 0,
        "nri_csv_path": str(nri_csv),
        "crosswalk_path": str(crosswalk),
        "usfs_dir": str(USFS_DIR),
    }
    return prereqs


def main() -> None:
    """Entry point for the hazard population script."""
    parser = argparse.ArgumentParser(
        description=(
            "Populate hazard profiles for all 592 Tribes using "
            "FEMA NRI + USFS wildfire data."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load data and report what would be done without writing profiles",
    )
    parser.add_argument(
        "--tribe",
        type=str,
        default=None,
        help="Build profile for a single Tribe ID (for debugging)",
    )
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Check prerequisites
    prereqs = check_prerequisites()
    logger.info("=== Prerequisite Check ===")
    logger.info("  NRI county CSV:     %s (%s)", prereqs["nri_county_csv"], prereqs["nri_csv_path"])
    logger.info("  Area crosswalk:     %s (%s)", prereqs["area_crosswalk"], prereqs["crosswalk_path"])
    logger.info("  USFS XLSX:          %s (%s)", prereqs["usfs_xlsx"], prereqs["usfs_dir"])

    if not prereqs["nri_county_csv"]:
        logger.error(
            "NRI county CSV not found. Run: python scripts/download_nri_data.py"
        )
        sys.exit(1)

    if not prereqs["area_crosswalk"]:
        logger.warning(
            "Area-weighted crosswalk not found. Falling back to equal-weight aggregation. "
            "For best results, run: python scripts/build_area_crosswalk.py"
        )

    if not prereqs["usfs_xlsx"]:
        logger.warning(
            "USFS wildfire data not found. Wildfire risk enrichment will be unavailable. "
            "Run: python scripts/download_usfs_data.py"
        )

    if args.dry_run:
        logger.info("=== DRY RUN MODE ===")
        logger.info("Would build hazard profiles for %s", "all 592 Tribes" if not args.tribe else args.tribe)
        logger.info("Output directory: %s", HAZARD_PROFILES_DIR)
        logger.info("Coverage report: %s", OUTPUTS_DIR / "hazard_coverage_report.json")
        logger.info("Dry run complete -- no files written.")
        return

    # Load config
    logger.info("Loading config from %s", SCANNER_CONFIG_PATH)
    with open(SCANNER_CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Import after sys.path is set and config is loaded
    from src.packets.hazards import HazardProfileBuilder

    # Create builder
    logger.info("Initializing HazardProfileBuilder...")
    start_time = time.time()
    builder = HazardProfileBuilder(config)

    # Build profiles
    if args.tribe:
        logger.info("Building profile for single Tribe: %s", args.tribe)
        # For single-tribe mode, we still call build_all_profiles but
        # it builds all -- this is the simplest approach. A future
        # optimization could add a single-tribe method.
        logger.info(
            "Note: single-tribe mode still runs the full pipeline. "
            "Use for debugging specific profiles."
        )

    logger.info("=== Starting Hazard Profile Population ===")
    files_written = builder.build_all_profiles()
    elapsed = time.time() - start_time

    # Report results
    print()
    print("=" * 60)
    print("  HAZARD PROFILE POPULATION COMPLETE")
    print("=" * 60)
    print(f"  Files written:    {files_written}")
    print(f"  Output directory: {HAZARD_PROFILES_DIR}")
    print(f"  Duration:         {elapsed:.1f} seconds")
    print()

    # Load coverage report for summary
    report_path = OUTPUTS_DIR / "hazard_coverage_report.json"
    if report_path.exists():
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
        summary = report.get("summary", {})
        print(f"  NRI matched:      {summary.get('nri_matched', 0)} ({summary.get('nri_pct', 0)}%)")
        print(f"  USFS matched:     {summary.get('usfs_matched', 0)} ({summary.get('usfs_pct', 0)}%)")
        print(f"  USFS overrides:   {summary.get('usfs_overrides', 0)}")
        print(f"  Scored profiles:  {summary.get('scored_profiles', 0)} ({summary.get('scored_pct', 0)}%)")
        print(f"  Unmatched:        {summary.get('unmatched_profiles', 0)}")
        print()
        print(f"  Coverage report:  {report_path}")
        print(f"  Markdown report:  {OUTPUTS_DIR / 'hazard_coverage_report.md'}")

        # Check if target met (550+ scored profiles = HZRD-06)
        scored = summary.get("scored_profiles", 0)
        if scored >= 550:
            print(f"\n  HZRD-06 TARGET MET: {scored}/592 scored profiles (>= 550)")
        else:
            print(f"\n  HZRD-06 TARGET: {scored}/592 scored profiles (target: 550+)")
    print()

    if files_written == 0:
        logger.error("No files written -- check data availability")
        sys.exit(1)


if __name__ == "__main__":
    main()
