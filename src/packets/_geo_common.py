"""Shared geographic data loading utilities for TCR Policy Scanner builders.

Deduplicates crosswalk loading, area weight loading, and atomic file writing
that was previously copy-pasted across hazards.py, nri_expanded.py, and
svi_builder.py (P3-#11, P3-#12).

These are module-level functions, not class methods. Each builder calls
them from its __init__ and stores the results on self.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def load_aiannh_crosswalk(
    crosswalk_path: Path,
    label: str = "",
) -> tuple[dict[str, str], dict[str, list[str]]]:
    """Load and invert the AIANNH-to-tribe_id crosswalk.

    The crosswalk JSON has structure:
        {"mappings": {"GEOID": "tribe_id", ...}}

    One Tribe may span multiple AIANNH areas, so the reverse mapping
    is tribe_id -> list[GEOID].

    Args:
        crosswalk_path: Path to the AIANNH crosswalk JSON file.
        label: Builder label for log messages (e.g., "NRI expanded").

    Returns:
        Tuple of (crosswalk_dict, tribe_to_geoids_dict).
        Both empty dicts if file not found or invalid.
    """
    prefix = f"{label} " if label else ""
    try:
        with open(crosswalk_path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.warning(
            "AIANNH crosswalk not found at %s -- "
            "all Tribes will get empty %sprofiles",
            crosswalk_path,
            prefix,
        )
        return {}, {}
    except json.JSONDecodeError as exc:
        logger.error(
            "Crosswalk at %s is invalid JSON: %s",
            crosswalk_path, exc,
        )
        return {}, {}

    crosswalk = data.get("mappings", {})

    # Build reverse mapping: tribe_id -> [geoid, ...]
    tribe_to_geoids: dict[str, list[str]] = {}
    for geoid, tribe_id in crosswalk.items():
        if tribe_id not in tribe_to_geoids:
            tribe_to_geoids[tribe_id] = []
        tribe_to_geoids[tribe_id].append(geoid)

    logger.info(
        "%scrosswalk loaded: %d GEOIDs -> %d unique tribe_ids",
        prefix,
        len(crosswalk),
        len(tribe_to_geoids),
    )
    return crosswalk, tribe_to_geoids


def load_area_weights(
    weights_path: Path,
    label: str = "",
) -> dict[str, list[dict]]:
    """Load pre-computed area-weighted AIANNH-to-county crosswalk.

    Reads the JSON file produced by scripts/build_area_crosswalk.py.
    Each AIANNH GEOID maps to a list of county entries with weights.

    Args:
        weights_path: Path to the area weights JSON file.
        label: Builder label for log messages (e.g., "SVI").

    Returns:
        Dict mapping AIANNH GEOID -> list of {county_fips, weight, overlap_area_sqkm}.
        Empty dict if file not found.
    """
    prefix = f"{label} " if label else ""
    if not weights_path.exists():
        logger.warning(
            "Area-weighted crosswalk not found at %s -- "
            "%sbuilder will use equal weights. "
            "Run scripts/build_area_crosswalk.py to generate.",
            weights_path,
            prefix,
        )
        return {}

    try:
        with open(weights_path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.error(
            "Failed to load area weights from %s: %s",
            weights_path, exc,
        )
        return {}

    crosswalk = data.get("crosswalk", {})
    metadata = data.get("metadata", {})
    logger.info(
        "%sarea weights loaded: %d AIANNH entities, %d county links",
        prefix,
        metadata.get("total_aiannh_entities", len(crosswalk)),
        metadata.get("total_county_links", 0),
    )
    return crosswalk


def atomic_write_json(
    output_path: Path,
    data: dict,
) -> None:
    """Write JSON data atomically with path traversal guard.

    Uses tempfile.mkstemp + os.fdopen + os.replace pattern for
    crash safety. Cleans up temp file on error.

    Args:
        output_path: Target file path.
        data: Dict to serialize as JSON.

    Raises:
        ValueError: If output_path contains path traversal sequences.
    """
    if ".." in str(output_path):
        raise ValueError(
            f"Path traversal detected in output path: {output_path}"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=output_path.parent,
        suffix=".tmp",
        prefix=f"{output_path.stem}_",
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, output_path)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise


def atomic_write_text(
    output_path: Path,
    text: str,
) -> None:
    """Write text data atomically with path traversal guard.

    Same crash-safe pattern as atomic_write_json but for plain text
    (e.g., Markdown coverage reports).

    Args:
        output_path: Target file path.
        text: Text content to write.

    Raises:
        ValueError: If output_path contains path traversal sequences.
    """
    if ".." in str(output_path):
        raise ValueError(
            f"Path traversal detected in output path: {output_path}"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=output_path.parent,
        suffix=".tmp",
        prefix=f"{output_path.stem}_",
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp_path, output_path)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise
