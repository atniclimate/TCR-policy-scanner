#!/usr/bin/env python3
"""Build tribes.json index for the GitHub Pages widget.

Reads tribal_registry.json + scans packets directory to build
a searchable index with download metadata.

Usage:
    python scripts/build_web_index.py
    python scripts/build_web_index.py --registry data/tribal_registry.json \\
        --packets outputs/packets --output docs/web/data/tribes.json
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on sys.path for src.paths imports
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.paths import PACKETS_OUTPUT_DIR, TRIBAL_REGISTRY_PATH, TRIBES_INDEX_PATH

logger = logging.getLogger(__name__)

DEFAULT_REGISTRY = TRIBAL_REGISTRY_PATH
DEFAULT_PACKETS = PACKETS_OUTPUT_DIR
DEFAULT_OUTPUT = TRIBES_INDEX_PATH

MAX_REGISTRY_SIZE = 10 * 1024 * 1024  # 10 MB


def build_index(
    registry_path: Path,
    packets_dir: Path,
    output_path: Path,
) -> dict:
    """Build tribes.json with searchable index and packet metadata.

    Reads the Tribal registry, scans the packets directory for DOCX files,
    and writes a JSON index suitable for the web widget autocomplete.

    Args:
        registry_path: Path to tribal_registry.json.
        packets_dir: Directory containing per-Tribe DOCX files.
        output_path: Where to write tribes.json.

    Returns:
        The index dict that was written.

    Raises:
        ValueError: If registry file exceeds 10 MB size limit.
        FileNotFoundError: If registry file does not exist.
    """
    # Size guard before loading
    size = registry_path.stat().st_size
    if size > MAX_REGISTRY_SIZE:
        raise ValueError(
            f"Registry file too large: {size:,} bytes (limit: {MAX_REGISTRY_SIZE:,})"
        )

    with open(registry_path, "r", encoding="utf-8") as f:
        registry = json.load(f)

    # Handle both list and {"tribes": [...]} formats
    if isinstance(registry, list):
        tribes_list = registry
    else:
        tribes_list = registry.get("tribes", [])

    # Scan packets directory for existing DOCX files
    existing_packets: dict[str, float] = {}
    if packets_dir.is_dir():
        for docx_file in packets_dir.glob("*.docx"):
            tribe_id = docx_file.stem
            size_kb = round(docx_file.stat().st_size / 1024, 1)
            existing_packets[tribe_id] = size_kb

    # Build index entries
    tribes_index = []
    for tribe in tribes_list:
        # Registry uses tribe_id as the primary key
        tribe_id = tribe.get("tribe_id", tribe.get("epa_id", tribe.get("id", "")))
        entry = {
            "id": tribe_id,
            "name": tribe.get("name", ""),
            "states": tribe.get("states", []),
            "ecoregion": tribe.get("ecoregion", ""),
            "has_packet": tribe_id in existing_packets,
            "file_size_kb": existing_packets.get(tribe_id, 0),
        }
        tribes_index.append(entry)

    index = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "packet_count": len(existing_packets),
        "total_tribes": len(tribes_index),
        "tribes": tribes_index,
    }

    # Atomic write: tmp file + os.replace()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        os.replace(str(tmp_path), str(output_path))
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise

    logger.info(
        "Built tribes.json: %d tribes, %d packets",
        len(tribes_index),
        len(existing_packets),
    )
    return index


def main() -> None:
    """CLI entry point for building the web index."""
    parser = argparse.ArgumentParser(
        description="Build tribes.json index for the web widget."
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=DEFAULT_REGISTRY,
        help=f"Path to tribal_registry.json (default: {DEFAULT_REGISTRY})",
    )
    parser.add_argument(
        "--packets",
        type=Path,
        default=DEFAULT_PACKETS,
        help=f"Directory containing per-Tribe DOCX files (default: {DEFAULT_PACKETS})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output path for tribes.json (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    index = build_index(args.registry, args.packets, args.output)
    print(
        f"Generated tribes.json: {index['total_tribes']} tribes, "
        f"{index['packet_count']} packets"
    )


if __name__ == "__main__":
    main()
