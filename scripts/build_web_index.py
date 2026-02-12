#!/usr/bin/env python3
"""Build tribes.json index for the GitHub Pages widget.

Reads tribal_registry.json + scans packets directory to build
a searchable index with download metadata.  Supports 4 document types:
  Doc A - Internal Strategy (per-Tribe)
  Doc B - Congressional Overview (per-Tribe)
  Doc C - Regional Internal Strategy
  Doc D - Regional Congressional Overview

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
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on sys.path for src.paths imports
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.paths import (
    PACKETS_OUTPUT_DIR,
    REGIONAL_CONFIG_PATH,
    TRIBAL_ALIASES_PATH,
    TRIBAL_REGISTRY_PATH,
    TRIBES_INDEX_PATH,
)

logger = logging.getLogger(__name__)

DEFAULT_REGISTRY = TRIBAL_REGISTRY_PATH
DEFAULT_PACKETS = PACKETS_OUTPUT_DIR
DEFAULT_OUTPUT = TRIBES_INDEX_PATH
DEFAULT_REGIONAL_CONFIG = REGIONAL_CONFIG_PATH
DEFAULT_ALIASES = TRIBAL_ALIASES_PATH

MAX_REGISTRY_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_ALIASES_SIZE = 10 * 1024 * 1024  # 10 MB


def _load_filtered_aliases(
    aliases_path: Path, max_per_tribe: int = 10
) -> dict[str, list[str]]:
    """Load tribal aliases and return filtered per-Tribe alias lists.

    Reads data/tribal_aliases.json, builds a reverse mapping from tribe_id
    to alias strings, filters out housing authority variants, sorts by
    string length (shortest first), and caps at max_per_tribe per Tribe.

    Args:
        aliases_path: Path to tribal_aliases.json.
        max_per_tribe: Maximum aliases to keep per Tribe (default 10).

    Returns:
        Dict mapping tribe_id to list of filtered alias strings.
        Returns empty dict if file missing or exceeds size limit.
    """
    if not aliases_path.is_file():
        logger.warning("Aliases file not found: %s", aliases_path)
        return {}

    # Size guard consistent with MAX_REGISTRY_SIZE pattern
    file_size = aliases_path.stat().st_size
    if file_size > MAX_ALIASES_SIZE:
        logger.warning(
            "Aliases file too large: %s bytes (limit: %s)",
            file_size,
            MAX_ALIASES_SIZE,
        )
        return {}

    with open(aliases_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw_aliases = data.get("aliases", {})

    # Build reverse mapping: tribe_id -> [alias1, alias2, ...]
    reverse: dict[str, list[str]] = defaultdict(list)
    for alias_str, tribe_id in raw_aliases.items():
        # Filter out housing authority variants (not useful for search)
        if "housing" in alias_str.lower():
            continue
        reverse[tribe_id].append(alias_str)

    # Sort by length (shortest first) and cap at max_per_tribe
    result: dict[str, list[str]] = {}
    for tribe_id, aliases in reverse.items():
        aliases.sort(key=len)
        result[tribe_id] = aliases[:max_per_tribe]

    logger.info(
        "Loaded aliases: %d Tribes with aliases (from %d total entries)",
        len(result),
        len(raw_aliases),
    )
    return result


def _get_tribe_generated_at(
    tribe_id: str, packets_dir: Path
) -> str | None:
    """Get the most recent DOCX modification time for a Tribe.

    Checks internal/ and congressional/ subdirectories for the Tribe's
    DOCX files and returns the most recent modification time as an
    ISO 8601 timestamp.

    Args:
        tribe_id: The Tribe's unique identifier (e.g. "epa_100000001").
        packets_dir: Root packets directory.

    Returns:
        ISO 8601 timestamp string or None if no DOCX files exist.
    """
    mtimes: list[float] = []
    for subdir in ("internal", "congressional"):
        docx_path = packets_dir / subdir / f"{tribe_id}.docx"
        if docx_path.is_file():
            mtimes.append(docx_path.stat().st_mtime)

    # Also check flat directory for backward compatibility
    flat_path = packets_dir / f"{tribe_id}.docx"
    if flat_path.is_file():
        mtimes.append(flat_path.stat().st_mtime)

    if not mtimes:
        return None

    latest = max(mtimes)
    return datetime.fromtimestamp(latest, tz=timezone.utc).isoformat()


def _scan_doc_files(directory: Path) -> dict[str, float]:
    """Scan a directory for DOCX files and return {stem: size_kb} mapping."""
    result: dict[str, float] = {}
    if directory.is_dir():
        for docx_file in directory.glob("*.docx"):
            stem = docx_file.stem
            size_kb = round(docx_file.stat().st_size / 1024, 1)
            result[stem] = size_kb
    return result


def build_index(
    registry_path: Path,
    packets_dir: Path,
    output_path: Path,
    regional_config_path: Path | None = None,
    aliases_path: Path | None = None,
) -> dict:
    """Build tribes.json with searchable index and packet metadata.

    Reads the Tribal registry, scans the packets directory for DOCX files
    across internal/ and congressional/ subdirectories, and writes a JSON
    index suitable for the web widget autocomplete.  Embeds per-Tribe
    aliases (for fuzzy search) and per-Tribe generated_at timestamps
    (for freshness badges).

    Args:
        registry_path: Path to tribal_registry.json.
        packets_dir: Directory containing per-Tribe DOCX files in
            internal/ and congressional/ subdirectories.
        output_path: Where to write tribes.json.
        regional_config_path: Path to regional_config.json (optional).
        aliases_path: Path to tribal_aliases.json (optional).  When
            provided, each Tribe entry gets an ``aliases`` list of up
            to 10 alternate names for fuzzy search.

    Returns:
        The index dict that was written.

    Raises:
        ValueError: If registry file exceeds 10 MB size limit.
        FileNotFoundError: If registry file does not exist.
    """
    # Load filtered aliases for fuzzy search embedding
    if aliases_path is None:
        aliases_path = DEFAULT_ALIASES
    filtered_aliases = _load_filtered_aliases(aliases_path)

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

    # Scan packets directory for existing DOCX files in subdirectories
    internal_dir = packets_dir / "internal"
    congressional_dir = packets_dir / "congressional"

    internal_packets = _scan_doc_files(internal_dir)
    congressional_packets = _scan_doc_files(congressional_dir)

    # Also scan flat directory for backward compatibility
    flat_packets = _scan_doc_files(packets_dir)

    # Build index entries
    tribes_index = []
    doc_a_count = 0
    doc_b_count = 0

    for tribe in tribes_list:
        # Registry uses tribe_id as the primary key
        tribe_id = tribe.get("tribe_id", tribe.get("epa_id", tribe.get("id", "")))

        # Determine document availability
        has_internal = tribe_id in internal_packets
        has_congressional = tribe_id in congressional_packets
        # Fallback: flat directory (old layout)
        has_flat = tribe_id in flat_packets

        documents: dict[str, str] = {}
        if has_internal:
            documents["internal_strategy"] = f"internal/{tribe_id}.docx"
            doc_a_count += 1
        if has_congressional:
            documents["congressional_overview"] = f"congressional/{tribe_id}.docx"
            doc_b_count += 1
        elif has_flat:
            # Backward compat: flat packet file
            documents["congressional_overview"] = f"{tribe_id}.docx"
            doc_b_count += 1

        entry = {
            "id": tribe_id,
            "name": tribe.get("name", ""),
            "aliases": filtered_aliases.get(tribe_id, []),
            "states": tribe.get("states", []),
            "ecoregion": tribe.get("ecoregion", ""),
            "documents": documents,
            "has_complete_data": has_internal and has_congressional,
            "generated_at": _get_tribe_generated_at(tribe_id, packets_dir),
        }
        tribes_index.append(entry)

    # Build regions section
    regions_list = _build_regions(packets_dir, regional_config_path)
    doc_c_count = sum(
        1 for r in regions_list if "internal_strategy" in r.get("documents", {})
    )
    doc_d_count = sum(
        1 for r in regions_list
        if "congressional_overview" in r.get("documents", {})
    )

    index = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_tribes": len(tribes_index),
        "tribes": tribes_index,
        "regions": regions_list,
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_tribes": len(tribes_index),
            "doc_a_count": doc_a_count,
            "doc_b_count": doc_b_count,
            "doc_c_count": doc_c_count,
            "doc_d_count": doc_d_count,
        },
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
        "Built tribes.json: %d tribes, %d Doc A, %d Doc B, %d regions",
        len(tribes_index),
        doc_a_count,
        doc_b_count,
        len(regions_list),
    )
    return index


def _build_regions(
    packets_dir: Path,
    regional_config_path: Path | None = None,
) -> list[dict]:
    """Build the regions section of tribes.json.

    Scans regional/ subdirectories for Doc C and Doc D files.

    Args:
        packets_dir: Root packets directory containing regional/ subdirectory.
        regional_config_path: Path to regional_config.json for region metadata.

    Returns:
        List of region dicts with id, name, tribe_count, and documents.
    """
    regional_internal_dir = packets_dir / "regional" / "internal"
    regional_congressional_dir = packets_dir / "regional" / "congressional"

    regional_internal = _scan_doc_files(regional_internal_dir)
    regional_congressional = _scan_doc_files(regional_congressional_dir)

    # Load regional config for names and metadata
    region_config: dict = {}
    if regional_config_path and regional_config_path.is_file():
        with open(regional_config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            region_config = cfg.get("regions", {})

    # Gather all region IDs from config or from files found
    all_region_ids = set(region_config.keys())
    all_region_ids.update(regional_internal.keys())
    all_region_ids.update(regional_congressional.keys())

    regions = []
    for region_id in sorted(all_region_ids):
        cfg_entry = region_config.get(region_id, {})
        region_name = cfg_entry.get("name", region_id.replace("_", " ").title())
        states = cfg_entry.get("states", [])

        documents: dict[str, str] = {}
        if region_id in regional_internal:
            documents["internal_strategy"] = (
                f"regional/internal/{region_id}.docx"
            )
        if region_id in regional_congressional:
            documents["congressional_overview"] = (
                f"regional/congressional/{region_id}.docx"
            )

        regions.append({
            "region_id": region_id,
            "region_name": region_name,
            "states": states,
            "documents": documents,
        })

    return regions


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
    parser.add_argument(
        "--regional-config",
        type=Path,
        default=DEFAULT_REGIONAL_CONFIG,
        help=f"Path to regional_config.json (default: {DEFAULT_REGIONAL_CONFIG})",
    )
    parser.add_argument(
        "--aliases",
        type=Path,
        default=DEFAULT_ALIASES,
        help=f"Path to tribal_aliases.json (default: {DEFAULT_ALIASES})",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    index = build_index(
        args.registry,
        args.packets,
        args.output,
        args.regional_config,
        args.aliases,
    )
    meta = index["metadata"]
    print(
        f"Generated tribes.json: {index['total_tribes']} tribes, "
        f"{meta['doc_a_count']} Doc A, {meta['doc_b_count']} Doc B, "
        f"{meta['doc_c_count']} Doc C, {meta['doc_d_count']} Doc D"
    )


if __name__ == "__main__":
    main()
