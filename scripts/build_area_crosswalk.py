"""Build area-weighted AIANNH-to-county geographic crosswalk.

Reads Census TIGER/Line AIANNH and county shapefiles, computes geometric
intersections, calculates area overlap weights, and writes a JSON crosswalk
mapping each AIANNH GEOID to overlapping counties with normalized weights.

Dual-CRS approach for accurate area calculation:
  - Alaska (STATEFP == "02"): EPSG:3338 (NAD83 Alaska Albers)
  - CONUS (everything else): EPSG:5070 (NAD83 Conus Albers Equal Area)

A 1% minimum overlap filter removes sliver intersections caused by boundary
digitization artifacts.

Prerequisites:
    python scripts/download_nri_data.py   # Download shapefiles first

Usage:
    python scripts/build_area_crosswalk.py                    # Default
    python scripts/build_area_crosswalk.py --verbose          # Debug logging
    python scripts/build_area_crosswalk.py --min-overlap 0.02 # 2% threshold
"""

import argparse
import json
import logging
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on sys.path for src.paths imports
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import geopandas as gpd

from src.paths import NRI_DIR, TRIBAL_COUNTY_WEIGHTS_PATH

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CRS constants
# ---------------------------------------------------------------------------

CRS_ALASKA = "EPSG:3338"     # NAD83 Alaska Albers
CRS_CONUS = "EPSG:5070"      # NAD83 Conus Albers Equal Area
ALASKA_STATEFP = "02"

# Area conversion
SQM_TO_SQKM = 1_000_000


# ---------------------------------------------------------------------------
# Shapefile loading
# ---------------------------------------------------------------------------


def _find_shapefile(directory: Path) -> Path:
    """Find the .shp file in *directory*.

    Raises FileNotFoundError if no shapefile is found.
    """
    shp_files = list(directory.glob("*.shp"))
    if not shp_files:
        raise FileNotFoundError(
            f"No .shp file found in {directory}. "
            "Run scripts/download_nri_data.py first."
        )
    if len(shp_files) > 1:
        logger.warning(
            "Multiple .shp files in %s, using %s", directory, shp_files[0].name,
        )
    return shp_files[0]


def load_shapefiles() -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Load AIANNH and county shapefiles from NRI_DIR subdirectories."""
    aiannh_dir = NRI_DIR / "aiannh"
    county_dir = NRI_DIR / "county"

    aiannh_shp = _find_shapefile(aiannh_dir)
    county_shp = _find_shapefile(county_dir)

    logger.info("Loading AIANNH shapefile: %s", aiannh_shp)
    aiannh = gpd.read_file(aiannh_shp)
    logger.info("  %d AIANNH features loaded", len(aiannh))

    logger.info("Loading county shapefile: %s", county_shp)
    counties = gpd.read_file(county_shp)
    logger.info("  %d county features loaded", len(counties))

    return aiannh, counties


# ---------------------------------------------------------------------------
# Intersection and weight computation
# ---------------------------------------------------------------------------


def _split_by_region(
    gdf: gpd.GeoDataFrame, statefp_col: str,
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Split a GeoDataFrame into Alaska and CONUS subsets."""
    mask_ak = gdf[statefp_col] == ALASKA_STATEFP
    return gdf[mask_ak].copy(), gdf[~mask_ak].copy()


def _compute_intersections(
    aiannh: gpd.GeoDataFrame,
    counties: gpd.GeoDataFrame,
    crs: str,
    region_label: str,
) -> list[dict]:
    """Compute area intersections between AIANNH and county features.

    Both GeoDataFrames are projected to *crs* for equal-area calculation.
    Returns a list of dicts with keys: aiannh_geoid, county_fips,
    overlap_area_sqm, aiannh_area_sqm.
    """
    if aiannh.empty or counties.empty:
        logger.info("  %s: no features to intersect", region_label)
        return []

    # Project to equal-area CRS
    aiannh_ea = aiannh.to_crs(crs)
    counties_ea = counties.to_crs(crs)

    # Compute original AIANNH areas before intersection
    aiannh_ea["_aiannh_area"] = aiannh_ea.geometry.area

    logger.info(
        "  %s: computing overlay of %d AIANNH x %d counties ...",
        region_label, len(aiannh_ea), len(counties_ea),
    )

    try:
        intersection = gpd.overlay(
            aiannh_ea, counties_ea, how="intersection", keep_geom_type=False,
        )
    except Exception as exc:
        logger.error("  %s: overlay failed: %s", region_label, exc)
        return []

    if intersection.empty:
        logger.warning("  %s: overlay produced no intersections", region_label)
        return []

    intersection["_overlap_area"] = intersection.geometry.area

    # Resolve GEOID column naming after overlay (may have _1 / _2 suffixes)
    aiannh_geoid_col = _resolve_column(intersection, "GEOID", prefer_suffix="_1")
    county_geoid_col = _resolve_column(intersection, "GEOID", prefer_suffix="_2")
    statefp_col = _resolve_column(intersection, "STATEFP", prefer_suffix="_2")
    countyfp_col = _resolve_column(intersection, "COUNTYFP", prefer_suffix=None)

    results: list[dict] = []
    for _, row in intersection.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue

        overlap_area = row["_overlap_area"]
        aiannh_area = row["_aiannh_area"]

        if aiannh_area <= 0:
            continue

        aiannh_geoid = str(row[aiannh_geoid_col]).strip()

        # Build county FIPS: STATEFP (2-digit) + COUNTYFP (3-digit) = 5-digit
        if countyfp_col and statefp_col:
            state_fp = str(row[statefp_col]).strip().zfill(2)
            county_fp = str(row[countyfp_col]).strip().zfill(3)
            county_fips = state_fp + county_fp
        elif county_geoid_col:
            county_fips = str(row[county_geoid_col]).strip().zfill(5)
        else:
            logger.warning(
                "Cannot determine county FIPS for intersection with AIANNH %s",
                aiannh_geoid,
            )
            continue

        results.append({
            "aiannh_geoid": aiannh_geoid,
            "county_fips": county_fips,
            "overlap_area_sqm": overlap_area,
            "aiannh_area_sqm": aiannh_area,
        })

    logger.info(
        "  %s: %d intersection rows produced", region_label, len(results),
    )
    return results


def _resolve_column(
    gdf: gpd.GeoDataFrame, base_name: str, prefer_suffix: str | None,
) -> str | None:
    """Find a column in *gdf* matching *base_name* with optional suffix.

    After gpd.overlay(), columns from both inputs may get _1 / _2 suffixes
    when names collide (e.g. GEOID_1, GEOID_2).
    """
    cols = list(gdf.columns)

    # Try with preferred suffix first
    if prefer_suffix:
        candidate = base_name + prefer_suffix
        if candidate in cols:
            return candidate

    # Try exact match
    if base_name in cols:
        return base_name

    # Try any suffix
    for col in cols:
        if col.startswith(base_name + "_"):
            return col

    return None


def build_crosswalk(
    aiannh: gpd.GeoDataFrame,
    counties: gpd.GeoDataFrame,
    min_overlap: float,
) -> dict[str, list[dict]]:
    """Build the area-weighted AIANNH-to-county crosswalk.

    Returns a dict keyed by AIANNH GEOID, each value a list of
    {county_fips, overlap_area_sqkm, weight} dicts.
    """
    # Determine STATEFP column name for AIANNH
    # AIANNH shapefile uses STATEFP for the primary state
    aiannh_statefp = "STATEFP" if "STATEFP" in aiannh.columns else None

    # For AIANNH, split by examining which state each feature is primarily in.
    # Some AIANNH features span multiple states; use the STATEFP field.
    if aiannh_statefp:
        aiannh_ak, aiannh_conus = _split_by_region(aiannh, aiannh_statefp)
    else:
        # Fallback: all CONUS if no STATEFP
        logger.warning("AIANNH shapefile missing STATEFP column; treating all as CONUS")
        aiannh_ak = aiannh.iloc[0:0]  # empty
        aiannh_conus = aiannh

    # Split counties by state
    counties_ak, counties_conus = _split_by_region(counties, "STATEFP")

    # Compute intersections for each region
    all_rows: list[dict] = []

    ak_rows = _compute_intersections(
        aiannh_ak, counties_ak, CRS_ALASKA, "Alaska",
    )
    all_rows.extend(ak_rows)

    conus_rows = _compute_intersections(
        aiannh_conus, counties_conus, CRS_CONUS, "CONUS",
    )
    all_rows.extend(conus_rows)

    logger.info("Total intersection rows: %d", len(all_rows))

    # Group by AIANNH GEOID and compute weights
    from collections import defaultdict

    by_geoid: dict[str, list[dict]] = defaultdict(list)
    for row in all_rows:
        geoid = row["aiannh_geoid"]
        overlap_pct = row["overlap_area_sqm"] / row["aiannh_area_sqm"]

        # Apply minimum overlap filter
        if overlap_pct < min_overlap:
            continue

        by_geoid[geoid].append({
            "county_fips": row["county_fips"],
            "overlap_area_sqkm": round(row["overlap_area_sqm"] / SQM_TO_SQKM, 4),
            "raw_weight": overlap_pct,
        })

    # Normalize weights to sum to 1.0 per GEOID
    crosswalk: dict[str, list[dict]] = {}
    zero_match_count = 0

    for geoid, entries in sorted(by_geoid.items()):
        total_weight = sum(e["raw_weight"] for e in entries)
        if total_weight <= 0:
            zero_match_count += 1
            continue

        normalized: list[dict] = []
        for entry in entries:
            normalized.append({
                "county_fips": entry["county_fips"],
                "overlap_area_sqkm": entry["overlap_area_sqkm"],
                "weight": round(entry["raw_weight"] / total_weight, 6),
            })

        # Sort by weight descending for readability
        normalized.sort(key=lambda x: x["weight"], reverse=True)
        crosswalk[geoid] = normalized

    if zero_match_count:
        logger.warning(
            "%d AIANNH GEOIDs had zero total weight after filtering", zero_match_count,
        )

    return crosswalk


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def write_crosswalk(
    crosswalk: dict[str, list[dict]],
    output_path: Path,
    min_overlap: float,
) -> None:
    """Write crosswalk JSON with metadata using atomic write pattern."""
    total_links = sum(len(v) for v in crosswalk.values())

    payload = {
        "metadata": {
            "description": "Area-weighted AIANNH-to-county geographic crosswalk",
            "source_aiannh": "Census TIGER/Line AIANNH 2024",
            "source_county": "Census TIGER/Line County 2024",
            "crs_alaska": CRS_ALASKA,
            "crs_conus": CRS_CONUS,
            "min_overlap_pct": min_overlap,
            "total_aiannh_entities": len(crosswalk),
            "total_county_links": total_links,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "version": "1.0",
        },
        "crosswalk": crosswalk,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Atomic write: temp file + replace
    fd, tmp_path_str = tempfile.mkstemp(
        dir=str(output_path.parent), suffix=".tmp",
    )
    tmp_path = Path(tmp_path_str)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, output_path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise

    size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(
        "Wrote crosswalk to %s (%.2f MB): %d AIANNH entities, %d county links",
        output_path, size_mb, len(crosswalk), total_links,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Build the AIANNH-to-county area-weighted crosswalk."""
    parser = argparse.ArgumentParser(
        description=(
            "Build area-weighted AIANNH-to-county geographic crosswalk "
            "from Census TIGER/Line shapefiles."
        ),
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--min-overlap",
        type=float,
        default=0.01,
        help="Minimum overlap fraction to include (default: 0.01 = 1%%)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=TRIBAL_COUNTY_WEIGHTS_PATH,
        help=f"Output file path (default: {TRIBAL_COUNTY_WEIGHTS_PATH})",
    )
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    logger.info("Min overlap threshold: %.1f%%", args.min_overlap * 100)
    logger.info("Output path: %s", args.output)

    # Load shapefiles
    aiannh, counties = load_shapefiles()

    # Build crosswalk
    crosswalk = build_crosswalk(aiannh, counties, args.min_overlap)

    # Write output
    write_crosswalk(crosswalk, args.output.resolve(), args.min_overlap)

    # Summary
    total_links = sum(len(v) for v in crosswalk.values())
    logger.info("--- Summary ---")
    logger.info("  AIANNH entities matched: %d", len(crosswalk))
    logger.info("  Total county links: %d", total_links)
    if crosswalk:
        avg_counties = total_links / len(crosswalk)
        logger.info("  Average counties per AIANNH: %.1f", avg_counties)

    logger.info("Done.")


if __name__ == "__main__":
    main()
