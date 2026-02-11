#!/usr/bin/env python3
"""Validate data coverage across all TCR Policy Scanner data caches.

Reports coverage percentages for awards, hazards, congressional, and
registry data sources.  Also counts document generation outputs and
computes cross-source completeness.

Usage:
    python scripts/validate_coverage.py               # Full report (console + JSON + markdown)
    python scripts/validate_coverage.py --json-only    # JSON output only (no console/markdown)
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on sys.path for src imports (DEC-0902-01)
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.paths import (  # noqa: E402
    AWARD_CACHE_DIR,
    CONGRESSIONAL_CACHE_PATH,
    HAZARD_PROFILES_DIR,
    OUTPUTS_DIR,
    PACKETS_OUTPUT_DIR,
    TRIBAL_REGISTRY_PATH,
)


# ---------------------------------------------------------------------------
# Analysis functions
# ---------------------------------------------------------------------------


def analyze_awards(award_dir: Path) -> dict:
    """Analyze award cache files for coverage.

    Args:
        award_dir: Directory containing per-Tribe award JSON files.

    Returns:
        Dict with total, populated, zero_ids, coverage_pct.
    """
    total = 0
    populated = 0
    zero_ids: list[str] = []

    if not award_dir.is_dir():
        return {
            "total": 0,
            "populated": 0,
            "zero_ids": [],
            "coverage_pct": 0.0,
        }

    for path in sorted(award_dir.glob("*.json")):
        total += 1
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            awards = data.get("awards", [])
            total_obligation = data.get("total_obligation", 0) or 0
            award_count = data.get("award_count", 0) or 0
            if len(awards) > 0 or total_obligation > 0 or award_count > 0:
                populated += 1
            else:
                zero_ids.append(path.stem)
        except (json.JSONDecodeError, OSError):
            zero_ids.append(path.stem)

    coverage_pct = (populated / total * 100) if total > 0 else 0.0
    return {
        "total": total,
        "populated": populated,
        "zero_ids": zero_ids,
        "coverage_pct": round(coverage_pct, 1),
    }


def analyze_hazards(hazard_dir: Path) -> dict:
    """Analyze hazard profile files for coverage.

    Args:
        hazard_dir: Directory containing per-Tribe hazard profile JSON files.

    Returns:
        Dict with total, nri_populated, usfs_populated, zero_ids, coverage_pct.
    """
    total = 0
    nri_populated = 0
    usfs_populated = 0
    zero_ids: list[str] = []

    if not hazard_dir.is_dir():
        return {
            "total": 0,
            "nri_populated": 0,
            "usfs_populated": 0,
            "zero_ids": [],
            "coverage_pct": 0.0,
        }

    for path in sorted(hazard_dir.glob("*.json")):
        total += 1
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            sources = data.get("sources", {})
            nri = sources.get("fema_nri", {})
            composite = nri.get("composite", {})
            risk_score = composite.get("risk_score", 0) or 0
            if risk_score > 0:
                nri_populated += 1
            else:
                zero_ids.append(path.stem)

            usfs = sources.get("usfs_wildfire", {})
            risk_to_homes = usfs.get("risk_to_homes", 0) or 0
            if risk_to_homes > 0:
                usfs_populated += 1
        except (json.JSONDecodeError, OSError):
            zero_ids.append(path.stem)

    coverage_pct = (nri_populated / total * 100) if total > 0 else 0.0
    return {
        "total": total,
        "nri_populated": nri_populated,
        "usfs_populated": usfs_populated,
        "zero_ids": zero_ids,
        "coverage_pct": round(coverage_pct, 1),
    }


def analyze_congressional(
    cache_path: Path,
    total_tribes: int = 0,
) -> dict:
    """Analyze congressional cache for delegation coverage.

    Args:
        cache_path: Path to congressional_cache.json.
        total_tribes: Total Tribe count from the registry universe.
            If > 0, coverage_pct is computed against this total and
            Tribes missing from delegations are listed as unmapped.

    Returns:
        Dict with total, populated, unmapped_ids, coverage_pct.
    """
    if not cache_path.is_file():
        return {
            "total": total_tribes,
            "populated": 0,
            "unmapped_ids": [],
            "coverage_pct": 0.0,
        }

    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {
            "total": total_tribes,
            "populated": 0,
            "unmapped_ids": [],
            "coverage_pct": 0.0,
        }

    delegations = data.get("delegations", {})
    populated = 0
    unmapped_ids: list[str] = []

    for tribe_id, deleg in delegations.items():
        senators = deleg.get("senators", [])
        reps = deleg.get("representatives", [])
        if len(senators) > 0 or len(reps) > 0:
            populated += 1
        else:
            unmapped_ids.append(tribe_id)

    # Use the registry universe size for the denominator when available
    total = total_tribes if total_tribes > 0 else len(delegations)
    coverage_pct = (populated / total * 100) if total > 0 else 0.0
    return {
        "total": total,
        "populated": populated,
        "unmapped_ids": unmapped_ids,
        "coverage_pct": round(coverage_pct, 1),
    }


def analyze_registry(registry_path: Path) -> dict:
    """Analyze tribal registry for completeness.

    Args:
        registry_path: Path to tribal_registry.json.

    Returns:
        Dict with total, with_bia, with_states, coverage_pct.
    """
    if not registry_path.is_file():
        return {
            "total": 0,
            "with_bia": 0,
            "with_states": 0,
            "coverage_pct": 0.0,
        }

    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {
            "total": 0,
            "with_bia": 0,
            "with_states": 0,
            "coverage_pct": 0.0,
        }

    tribes = data.get("tribes", [])
    total = len(tribes)
    with_bia = 0
    with_states = 0

    for tribe in tribes:
        bia_code = tribe.get("bia_code", "")
        if bia_code and bia_code != "TBD":
            with_bia += 1
        states = tribe.get("states", [])
        if states and len(states) > 0:
            with_states += 1

    coverage_pct = (total / total * 100) if total > 0 else 0.0
    return {
        "total": total,
        "with_bia": with_bia,
        "with_states": with_states,
        "coverage_pct": round(coverage_pct, 1),
    }


def analyze_documents(packets_dir: Path) -> dict:
    """Analyze document generation outputs.

    Counts DOCX files in internal/, congressional/, regional/internal/,
    and regional/congressional/ subdirectories.

    Args:
        packets_dir: Path to the packets output directory.

    Returns:
        Dict with doc_a, doc_b, doc_c, doc_d counts and complete_packets.
    """
    internal_dir = packets_dir / "internal"
    congressional_dir = packets_dir / "congressional"
    regional_internal_dir = packets_dir / "regional" / "internal"
    regional_congressional_dir = packets_dir / "regional" / "congressional"

    doc_a_files: set[str] = set()
    doc_b_files: set[str] = set()
    doc_c_count = 0
    doc_d_count = 0

    if internal_dir.is_dir():
        for p in internal_dir.glob("*.docx"):
            doc_a_files.add(p.stem)

    if congressional_dir.is_dir():
        for p in congressional_dir.glob("*.docx"):
            doc_b_files.add(p.stem)

    if regional_internal_dir.is_dir():
        doc_c_count = len(list(regional_internal_dir.glob("*.docx")))

    if regional_congressional_dir.is_dir():
        doc_d_count = len(list(regional_congressional_dir.glob("*.docx")))

    # Complete packets: Tribes with BOTH Doc A and Doc B
    complete_packets = doc_a_files & doc_b_files

    return {
        "doc_a": len(doc_a_files),
        "doc_b": len(doc_b_files),
        "doc_c": doc_c_count,
        "doc_d": doc_d_count,
        "complete_packets": len(complete_packets),
        "doc_b_only": len(doc_b_files - doc_a_files),
    }


def analyze_cross_source(
    award_dir: Path,
    hazard_dir: Path,
    congressional_path: Path,
) -> dict:
    """Analyze cross-source completeness.

    Determines which Tribes have all, partial, or no data.

    Args:
        award_dir: Directory of per-Tribe award JSON files.
        hazard_dir: Directory of per-Tribe hazard profile JSON files.
        congressional_path: Path to congressional_cache.json.

    Returns:
        Dict with complete, partial, none counts and tribe-level breakdown.
    """
    # Collect Tribe IDs with data in each source
    award_ids: set[str] = set()
    if award_dir.is_dir():
        for path in award_dir.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                awards = data.get("awards", [])
                total_obl = data.get("total_obligation", 0) or 0
                if len(awards) > 0 or total_obl > 0:
                    award_ids.add(path.stem)
            except (json.JSONDecodeError, OSError):
                pass

    hazard_ids: set[str] = set()
    if hazard_dir.is_dir():
        for path in hazard_dir.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                risk = (
                    data.get("sources", {})
                    .get("fema_nri", {})
                    .get("composite", {})
                    .get("risk_score", 0)
                ) or 0
                if risk > 0:
                    hazard_ids.add(path.stem)
            except (json.JSONDecodeError, OSError):
                pass

    delegation_ids: set[str] = set()
    if congressional_path.is_file():
        try:
            with open(congressional_path, "r", encoding="utf-8") as f:
                cache = json.load(f)
            for tribe_id, deleg in cache.get("delegations", {}).items():
                senators = deleg.get("senators", [])
                reps = deleg.get("representatives", [])
                if len(senators) > 0 or len(reps) > 0:
                    delegation_ids.add(tribe_id)
        except (json.JSONDecodeError, OSError):
            pass

    # All Tribe IDs across sources
    all_ids = set()
    if award_dir.is_dir():
        all_ids.update(p.stem for p in award_dir.glob("*.json"))
    if hazard_dir.is_dir():
        all_ids.update(p.stem for p in hazard_dir.glob("*.json"))
    all_ids.update(delegation_ids)

    complete = 0  # awards + hazards + delegation
    partial_award_deleg = 0  # awards + delegation (no hazard)
    award_only = 0
    delegation_only = 0
    hazard_only = 0
    none_count = 0

    for tid in sorted(all_ids):
        has_award = tid in award_ids
        has_hazard = tid in hazard_ids
        has_deleg = tid in delegation_ids

        if has_award and has_hazard and has_deleg:
            complete += 1
        elif has_award and has_deleg:
            partial_award_deleg += 1
        elif has_award:
            award_only += 1
        elif has_deleg:
            delegation_only += 1
        elif has_hazard:
            hazard_only += 1
        else:
            none_count += 1

    total = len(all_ids)
    return {
        "total_tribes": total,
        "complete": complete,
        "partial_award_deleg": partial_award_deleg,
        "award_only": award_only,
        "delegation_only": delegation_only,
        "hazard_only": hazard_only,
        "none": none_count,
        "complete_pct": round(complete / total * 100, 1) if total > 0 else 0.0,
    }


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def build_coverage_report(
    award_dir: Path | None = None,
    hazard_dir: Path | None = None,
    congressional_path: Path | None = None,
    registry_path: Path | None = None,
    packets_dir: Path | None = None,
) -> dict:
    """Build the complete coverage report dict.

    All parameters default to the standard project paths if not provided,
    enabling overrides for testing.

    Returns:
        Nested dict with all coverage data.
    """
    award_dir = award_dir or AWARD_CACHE_DIR
    hazard_dir = hazard_dir or HAZARD_PROFILES_DIR
    congressional_path = congressional_path or CONGRESSIONAL_CACHE_PATH
    registry_path = registry_path or TRIBAL_REGISTRY_PATH
    packets_dir = packets_dir or PACKETS_OUTPUT_DIR

    # Determine universe size from registry
    reg = analyze_registry(registry_path)
    total_tribes = reg["total"]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": "1.2",
        "awards": analyze_awards(award_dir),
        "hazards": analyze_hazards(hazard_dir),
        "congressional": analyze_congressional(
            congressional_path, total_tribes=total_tribes
        ),
        "registry": reg,
        "documents": analyze_documents(packets_dir),
        "cross_source": analyze_cross_source(
            award_dir, hazard_dir, congressional_path
        ),
    }


def format_console_report(report: dict) -> str:
    """Format coverage report for console output.

    Args:
        report: Coverage report dict from build_coverage_report.

    Returns:
        Multi-line string for printing to stdout.
    """
    awards = report["awards"]
    hazards = report["hazards"]
    cong = report["congressional"]
    reg = report["registry"]
    docs = report["documents"]
    cross = report["cross_source"]

    lines = [
        "=== Data Coverage Report v1.2 ===",
        "",
        "Data Sources:",
        f"  Awards:        {awards['populated']}/{awards['total']} ({awards['coverage_pct']}%)",
        f"  Hazards (NRI): {hazards['nri_populated']}/{hazards['total']} ({hazards['coverage_pct']}%)",
        f"  Hazards (USFS):{hazards['usfs_populated']}/{hazards['total']}",
        f"  Congressional: {cong['populated']}/{cong['total']} ({cong['coverage_pct']}%)",
        f"  Registry:      {reg['total']}/{reg['total']} ({reg['coverage_pct']}%)",
        f"    BIA codes:   {reg['with_bia']}/{reg['total']}",
        f"    States:      {reg['with_states']}/{reg['total']}",
        "",
        "Document Generation:",
        f"  Doc A (Tribal Internal):        {docs['doc_a']} generated",
        f"  Doc B (Tribal Congressional):   {docs['doc_b']} generated",
        f"  Doc C (Regional Internal):      {docs['doc_c']} generated",
        f"  Doc D (Regional Congressional): {docs['doc_d']} generated",
        "",
        "Completeness:",
        f"  Complete data (all sources):     {cross['complete']}/{cross['total_tribes']} ({cross['complete_pct']}%)",
        f"  Complete packets (A+B):          {docs['complete_packets']} Tribes",
        f"  Partial packets (B only):        {docs['doc_b_only']} Tribes",
        "",
        "Coverage gaps saved to outputs/coverage_report.json",
    ]
    return "\n".join(lines)


def format_markdown_report(report: dict) -> str:
    """Format coverage report as markdown.

    Args:
        report: Coverage report dict from build_coverage_report.

    Returns:
        Markdown string.
    """
    awards = report["awards"]
    hazards = report["hazards"]
    cong = report["congressional"]
    reg = report["registry"]
    docs = report["documents"]
    cross = report["cross_source"]

    lines = [
        "# Data Coverage Report v1.2",
        "",
        f"**Generated:** {report['generated_at']}",
        "",
        "## Data Sources",
        "",
        "| Source | Populated | Total | Coverage |",
        "|--------|-----------|-------|----------|",
        f"| Awards (USASpending) | {awards['populated']} | {awards['total']} | {awards['coverage_pct']}% |",
        f"| Hazards (FEMA NRI) | {hazards['nri_populated']} | {hazards['total']} | {hazards['coverage_pct']}% |",
        f"| Hazards (USFS Wildfire) | {hazards['usfs_populated']} | {hazards['total']} | -- |",
        f"| Congressional | {cong['populated']} | {cong['total']} | {cong['coverage_pct']}% |",
        f"| Registry | {reg['total']} | {reg['total']} | {reg['coverage_pct']}% |",
        "",
        "## Document Generation",
        "",
        "| Document Type | Count |",
        "|--------------|-------|",
        f"| Doc A (Tribal Internal) | {docs['doc_a']} |",
        f"| Doc B (Tribal Congressional) | {docs['doc_b']} |",
        f"| Doc C (Regional Internal) | {docs['doc_c']} |",
        f"| Doc D (Regional Congressional) | {docs['doc_d']} |",
        f"| Complete packets (A+B) | {docs['complete_packets']} |",
        "",
        "## Cross-Source Completeness",
        "",
        "| Category | Count | Percentage |",
        "|----------|-------|------------|",
        f"| Complete (awards + hazards + delegation) | {cross['complete']} | {cross['complete_pct']}% |",
        f"| Partial (awards + delegation) | {cross['partial_award_deleg']} | -- |",
        f"| Award only | {cross['award_only']} | -- |",
        f"| Delegation only | {cross['delegation_only']} | -- |",
        f"| Hazard only | {cross['hazard_only']} | -- |",
        f"| None | {cross['none']} | -- |",
        "",
        "## Coverage Gaps",
        "",
        f"### Awards ({len(awards['zero_ids'])} Tribes at 0%)",
        "",
    ]

    if awards["zero_ids"]:
        for tid in awards["zero_ids"][:20]:
            lines.append(f"- {tid}")
        if len(awards["zero_ids"]) > 20:
            lines.append(f"- ... and {len(awards['zero_ids']) - 20} more")
    else:
        lines.append("None")

    lines.extend([
        "",
        f"### Congressional ({len(cong.get('unmapped_ids', []))} Tribes unmapped)",
        "",
    ])

    unmapped = cong.get("unmapped_ids", [])
    if unmapped:
        for tid in unmapped[:20]:
            lines.append(f"- {tid}")
        if len(unmapped) > 20:
            lines.append(f"- ... and {len(unmapped) - 20} more")
    else:
        lines.append("None")

    lines.extend([
        "",
        "---",
        "*Generated by validate_coverage.py*",
    ])

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Validate data coverage across all data caches."
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Output JSON only (no console summary or markdown file).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> dict:
    """Run coverage validation and produce reports.

    Args:
        argv: Optional CLI argument list (for testing).

    Returns:
        The coverage report dict.
    """
    args = parse_args(argv)
    report = build_coverage_report()

    # Ensure output directory exists
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    # Always write JSON report
    json_path = OUTPUTS_DIR / "coverage_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    if not args.json_only:
        # Write markdown report
        md_path = OUTPUTS_DIR / "coverage_report.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(format_markdown_report(report))

        # Print console summary
        print(format_console_report(report))

    return report


if __name__ == "__main__":
    main()
