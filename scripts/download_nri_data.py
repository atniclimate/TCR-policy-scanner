"""Download FEMA NRI county data and Census TIGER/Line shapefiles.

Fetches four datasets needed for the area-weighted AIANNH-to-county crosswalk:
  1. NRI county-level CSV (FEMA National Risk Index)
  2. NRI Tribal-county relational CSV
  3. Census TIGER/Line AIANNH shapefile (2024)
  4. Census TIGER/Line county shapefile (2024)

Files are downloaded to ``data/nri/`` with subdirectories for shapefiles.

Usage:
    python scripts/download_nri_data.py              # Download missing files
    python scripts/download_nri_data.py --force       # Re-download all
    python scripts/download_nri_data.py --verbose     # Debug logging
"""

import argparse
import logging
import os
import sys
import tempfile
import time
import zipfile
from pathlib import Path

# Ensure project root is on sys.path for src.paths imports
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import requests

from src.paths import NRI_DIR

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Download targets
# ---------------------------------------------------------------------------

DOWNLOADS = [
    {
        "name": "NRI County CSV",
        "url": "https://www.fema.gov/about/reports-and-data/openfema/nri/v120/NRI_Table_Counties.zip",
        "zip_dest": NRI_DIR / "NRI_Table_Counties.zip",
        "extract_dir": NRI_DIR,
        "check_glob": "NRI_Table_Counties*.csv",
    },
    {
        "name": "NRI Tribal County Relational CSV",
        "url": "https://www.fema.gov/about/reports-and-data/openfema/nri/v120/NRI_Table_Tribal_Counties.zip",
        "zip_dest": NRI_DIR / "NRI_Table_Tribal_Counties.zip",
        "extract_dir": NRI_DIR,
        "check_glob": "NRI_Table_Tribal_Counties*.csv",
    },
    {
        "name": "Census TIGER/Line AIANNH Shapefile (2024)",
        "url": "https://www2.census.gov/geo/tiger/TIGER2024/AIANNH/tl_2024_us_aiannh.zip",
        "zip_dest": NRI_DIR / "tl_2024_us_aiannh.zip",
        "extract_dir": NRI_DIR / "aiannh",
        "check_glob": "*.shp",
    },
    {
        "name": "Census TIGER/Line County Shapefile (2024)",
        "url": "https://www2.census.gov/geo/tiger/TIGER2024/COUNTY/tl_2024_us_county.zip",
        "zip_dest": NRI_DIR / "tl_2024_us_county.zip",
        "extract_dir": NRI_DIR / "county",
        "check_glob": "*.shp",
    },
]

# Retry configuration
MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 5
REQUEST_TIMEOUT_SECONDS = 300
CHUNK_SIZE = 8192


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extracted_exists(extract_dir: Path, check_glob: str) -> bool:
    """Return True if the expected extracted file already exists."""
    return any(extract_dir.glob(check_glob))


def _download_with_retry(url: str, dest: Path) -> None:
    """Stream-download *url* to *dest* with retry and progress reporting.

    Uses atomic write pattern: streams to a temp file first, then replaces.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(
                "Downloading %s (attempt %d/%d)...", url, attempt, MAX_RETRIES,
            )
            resp = requests.get(
                url, stream=True, timeout=REQUEST_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()

            total = int(resp.headers.get("content-length", 0))
            downloaded = 0

            # Write to temp file in same directory for atomic replace
            fd, tmp_path_str = tempfile.mkstemp(
                dir=str(dest.parent), suffix=".tmp",
            )
            tmp_path = Path(tmp_path_str)
            try:
                with os.fdopen(fd, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0 and logger.isEnabledFor(logging.DEBUG):
                            pct = downloaded * 100 // total
                            logger.debug("  %d%% (%d / %d bytes)", pct, downloaded, total)

                # Atomic replace
                os.replace(tmp_path, dest)
            except Exception:
                if tmp_path.exists():
                    tmp_path.unlink()
                raise

            size_mb = dest.stat().st_size / (1024 * 1024)
            logger.info("Downloaded %s (%.1f MB)", dest.name, size_mb)
            return

        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as exc:
            last_error = exc
            logger.warning("Download attempt %d failed: %s", attempt, exc)
            if attempt < MAX_RETRIES:
                logger.info("Retrying in %d seconds...", RETRY_DELAY_SECONDS)
                time.sleep(RETRY_DELAY_SECONDS)

    raise RuntimeError(
        f"Download failed after {MAX_RETRIES} attempts: {last_error}"
    )


def _extract_zip(zip_path: Path, extract_dir: Path) -> None:
    """Extract a ZIP archive to *extract_dir*."""
    extract_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Extracting %s to %s ...", zip_path.name, extract_dir)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)
    logger.info(
        "Extracted %d files to %s",
        len(list(extract_dir.iterdir())),
        extract_dir,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Download NRI data and Census shapefiles."""
    parser = argparse.ArgumentParser(
        description=(
            "Download FEMA NRI county data and Census TIGER/Line shapefiles "
            "for the area-weighted AIANNH-to-county crosswalk."
        ),
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if extracted files already exist",
    )
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    NRI_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("NRI data directory: %s", NRI_DIR)

    downloaded = 0
    skipped = 0

    for item in DOWNLOADS:
        name = item["name"]
        extract_dir = item["extract_dir"]
        check_glob = item["check_glob"]

        if not args.force and _extracted_exists(extract_dir, check_glob):
            logger.info("Skipping %s (already extracted)", name)
            skipped += 1
            continue

        _download_with_retry(item["url"], item["zip_dest"])
        _extract_zip(item["zip_dest"], extract_dir)
        downloaded += 1

    logger.info(
        "Complete: %d downloaded, %d skipped (already present)",
        downloaded,
        skipped,
    )


if __name__ == "__main__":
    main()
