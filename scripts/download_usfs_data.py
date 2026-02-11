"""Download USFS Wildfire Risk to Communities data.

Fetches the USFS Wildfire Risk to Communities XLSX dataset, which provides
community-level wildfire risk metrics (conditional risk to structures,
wildfire likelihood, etc.) for use in Tribal hazard profiles.

The XLSX file is downloaded to ``data/usfs/wrc_download.xlsx``.

Usage:
    python scripts/download_usfs_data.py              # Download if missing
    python scripts/download_usfs_data.py --force       # Re-download
    python scripts/download_usfs_data.py --verbose     # Debug logging
"""

import argparse
import logging
import os
import sys
import tempfile
import time
from pathlib import Path

# Ensure project root is on sys.path for src.paths imports
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import requests

from src.paths import USFS_DIR

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Download configuration
# ---------------------------------------------------------------------------

USFS_XLSX_URL = (
    "https://wildfirerisk.org/wp-content/uploads/2025/05/wrc_download_202505.xlsx"
)
USFS_XLSX_DEST = USFS_DIR / "wrc_download.xlsx"

# Retry configuration
MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 5
REQUEST_TIMEOUT_SECONDS = 300
CHUNK_SIZE = 8192


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _download_with_retry(url: str, dest: Path) -> None:
    """Stream-download *url* to *dest* with retry and progress reporting.

    Uses atomic write pattern: streams to a temp file first, then replaces.

    Args:
        url: URL to download from.
        dest: Destination file path.

    Raises:
        RuntimeError: If download fails after all retry attempts.
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
                            logger.debug(
                                "  %d%% (%d / %d bytes)", pct, downloaded, total,
                            )

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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Download USFS Wildfire Risk to Communities XLSX."""
    parser = argparse.ArgumentParser(
        description=(
            "Download USFS Wildfire Risk to Communities XLSX dataset "
            "for wildfire risk enrichment of Tribal hazard profiles."
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
        help="Re-download even if file already exists",
    )
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    USFS_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("USFS data directory: %s", USFS_DIR)

    if not args.force and USFS_XLSX_DEST.exists():
        size_mb = USFS_XLSX_DEST.stat().st_size / (1024 * 1024)
        logger.info(
            "Skipping download -- %s already exists (%.1f MB). "
            "Use --force to re-download.",
            USFS_XLSX_DEST.name, size_mb,
        )
        return

    _download_with_retry(USFS_XLSX_URL, USFS_XLSX_DEST)
    logger.info("USFS wildfire data download complete: %s", USFS_XLSX_DEST)


if __name__ == "__main__":
    main()
