#!/usr/bin/env python3
"""Build deployment manifest.json for the website.

Counts DOCX files in docs/web/tribes/ subdirectories and writes a
manifest with document counts and deployment timestamp.

Used by both deploy-website.yml and generate-packets.yml workflows
to avoid duplicated inline manifest generation code (MK-CODE-12).

Usage:
    python scripts/build_manifest.py
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def build_manifest(tribes_dir: Path) -> dict:
    """Build manifest dict with document counts.

    Args:
        tribes_dir: Path to docs/web/tribes/ directory.

    Returns:
        Manifest dict with deployed_at, document_counts, total_documents.
    """
    counts = {
        "internal": (
            len(list((tribes_dir / "internal").glob("*.docx")))
            if (tribes_dir / "internal").is_dir()
            else 0
        ),
        "congressional": (
            len(list((tribes_dir / "congressional").glob("*.docx")))
            if (tribes_dir / "congressional").is_dir()
            else 0
        ),
        "regional_internal": (
            len(list((tribes_dir / "regional/internal").glob("*.docx")))
            if (tribes_dir / "regional/internal").is_dir()
            else 0
        ),
        "regional_congressional": (
            len(list((tribes_dir / "regional/congressional").glob("*.docx")))
            if (tribes_dir / "regional/congressional").is_dir()
            else 0
        ),
    }
    return {
        "deployed_at": datetime.now(timezone.utc).isoformat(),
        "document_counts": counts,
        "total_documents": sum(counts.values()),
    }


def main() -> None:
    """Generate manifest.json in docs/web/data/."""
    tribes_dir = Path("docs/web/tribes")
    manifest = build_manifest(tribes_dir)

    output_dir = Path("docs/web/data")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "manifest.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Manifest: {manifest['total_documents']} documents deployed")


if __name__ == "__main__":
    main()
