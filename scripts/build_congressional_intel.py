"""Build congressional_intel.json from Congress.gov API bill searches.

One-time or periodic build script that:
1. Searches Congress.gov for Tribal-relevant bills using configured queries
2. Scores each bill for relevance to tracked programs (INTEL-03)
3. Fetches full bill detail for top-scoring bills (INTEL-01)
4. Validates records against BillIntelligence Pydantic model
5. Writes validated bills to data/congressional_intel.json

INTEL-04 delegation enhancement: Committee data is already present in
congressional_cache.json. Voting records (House roll call) are available
via Congress.gov API v3 beta (118th+ Congress) but Senate votes are NOT
yet available in the API. This script logs that status.

Usage:
    python scripts/build_congressional_intel.py
    python scripts/build_congressional_intel.py --verbose
    python scripts/build_congressional_intel.py --max-bills 25
    python scripts/build_congressional_intel.py --dry-run
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on sys.path
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.paths import (
    CONGRESSIONAL_INTEL_PATH,
    PROGRAM_INVENTORY_PATH,
    SCANNER_CONFIG_PATH,
)
from src.schemas.models import BillAction, BillIntelligence
from src.scrapers.congress_gov import CongressGovScraper

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Relevance scoring: bill-to-program mapping (INTEL-03)
# ---------------------------------------------------------------------------

# Committees relevant to Tribal climate programs -- used for committee match scoring
TRIBAL_COMMITTEES = {
    "SLIA": "Senate Committee on Indian Affairs",
    "HSII": "House Subcommittee for Indigenous Peoples of the United States",
    "SSAP": "Senate Appropriations Committee",
    "HSAP": "House Appropriations Committee",
    "SSEG": "Senate Energy and Natural Resources Committee",
    "SSCM": "Senate Commerce, Science, and Transportation Committee",
}


def _build_program_keyword_index(programs: list[dict]) -> dict[str, set[str]]:
    """Build a program_id -> set of lowercase keywords index.

    Combines program keywords, search_queries, and CFDA numbers for matching.
    """
    index: dict[str, set[str]] = {}
    for prog in programs:
        pid = prog["id"]
        kws: set[str] = set()

        # Program keywords
        for kw in prog.get("keywords", []):
            kws.add(kw.lower().strip())

        # Search queries
        for sq in prog.get("search_queries", []):
            kws.add(sq.lower().strip())

        # CFDA numbers (as strings for text matching)
        cfda = prog.get("cfda")
        if cfda:
            if isinstance(cfda, list):
                for c in cfda:
                    if isinstance(c, str):
                        kws.add(c.strip())
            elif isinstance(cfda, str) and not cfda.startswith("N/A"):
                kws.add(cfda.strip())

        index[pid] = kws
    return index


def _build_cfda_to_program(programs: list[dict]) -> dict[str, str]:
    """Build a CFDA number -> program_id mapping."""
    mapping: dict[str, str] = {}
    for prog in programs:
        cfda = prog.get("cfda")
        if cfda:
            if isinstance(cfda, list):
                for c in cfda:
                    if isinstance(c, str):
                        mapping[c.strip()] = prog["id"]
            elif isinstance(cfda, str) and not cfda.startswith("N/A"):
                mapping[cfda.strip()] = prog["id"]
    return mapping


def score_bill_relevance(
    bill: dict,
    program_keywords: dict[str, set[str]],
    cfda_to_program: dict[str, str],
    tribal_keywords: list[str],
) -> tuple[float, list[str]]:
    """Score a bill's relevance to tracked Tribal climate programs.

    Scoring components:
    1. Subject overlap (0.30): bill's legislativeSubjects vs program keywords
    2. CFDA/ALN reference (0.25): bill title mentions a tracked CFDA number
    3. Committee match (0.20): bill referred to Tribal-relevant committees
    4. Keyword density (0.25): Tribal-relevant keyword matches in title

    Returns:
        (relevance_score, matched_program_ids)
    """
    title_lower = bill.get("title", "").lower()
    bill_subjects = [s.get("name", "").lower() for s in bill.get("subjects", [])]
    bill_text = f"{title_lower} {' '.join(bill_subjects)}"

    matched_programs: set[str] = set()

    # 1. Subject overlap: check each program's keywords against bill subjects
    subject_score = 0.0
    if bill_subjects:
        for pid, kws in program_keywords.items():
            for kw in kws:
                for subj in bill_subjects:
                    if kw in subj or subj in kw:
                        matched_programs.add(pid)
                        subject_score = max(subject_score, 1.0)
                        break
                if pid in matched_programs:
                    break

    # 2. CFDA/ALN reference: check bill title/subjects for CFDA numbers
    cfda_score = 0.0
    for cfda_num, pid in cfda_to_program.items():
        if cfda_num in bill_text:
            cfda_score = 1.0
            matched_programs.add(pid)
            break

    # 3. Committee match: check if bill's committees are Tribal-relevant
    committee_score = 0.0
    committees = bill.get("committees", [])
    if committees:
        for comm in committees:
            comm_id = comm.get("systemCode", "").upper()
            comm_name = comm.get("name", "").lower()
            for tc_id, tc_name in TRIBAL_COMMITTEES.items():
                if tc_id.lower() in comm_id.lower() or tc_name.lower() in comm_name:
                    committee_score = 1.0
                    break
            if committee_score > 0:
                break

    # 4. Keyword density: count Tribal keyword matches in title
    keyword_score = 0.0
    if tribal_keywords:
        matches = sum(1 for kw in tribal_keywords if kw.lower() in title_lower)
        # Normalize: 3+ matches = full score
        keyword_score = min(matches / 3.0, 1.0)

    # Also check program keywords against title for additional program matches
    for pid, kws in program_keywords.items():
        for kw in kws:
            if len(kw) >= 4 and kw in title_lower:
                matched_programs.add(pid)
                break

    # Weighted average
    score = (
        subject_score * 0.30
        + cfda_score * 0.25
        + committee_score * 0.20
        + keyword_score * 0.25
    )

    return round(score, 4), sorted(matched_programs)


def compute_initial_relevance(
    bill: dict,
    tribal_keywords: list[str],
    program_keywords: dict[str, set[str]],
) -> float:
    """Quick relevance estimate from search result data (no detail fetch needed).

    Used to rank bills before deciding which ones to fetch full detail for.
    Based on title keyword density only (fast, no API calls).
    """
    title_lower = bill.get("title", "").lower()

    # Tribal keyword matches
    matches = sum(1 for kw in tribal_keywords if kw.lower() in title_lower)
    tribal_score = min(matches / 3.0, 1.0)

    # Program keyword matches
    program_score = 0.0
    for pid, kws in program_keywords.items():
        for kw in kws:
            if len(kw) >= 4 and kw in title_lower:
                program_score = 1.0
                break
        if program_score > 0:
            break

    return round(tribal_score * 0.6 + program_score * 0.4, 4)


# ---------------------------------------------------------------------------
# Bill detail -> BillIntelligence record transformation
# ---------------------------------------------------------------------------

def transform_to_bill_intel(
    bill_detail: dict,
    congress: int,
    bill_type_code: str,
    bill_number_str: str,
    relevance_score: float,
    matched_programs: list[str],
) -> dict:
    """Transform raw Congress.gov API bill detail to BillIntelligence dict.

    The returned dict is ready for BillIntelligence(**result) validation.
    """
    bill = bill_detail.get("bill", {})
    actions_raw = bill_detail.get("actions", [])
    cosponsors_raw = bill_detail.get("cosponsors", [])
    subjects_raw = bill_detail.get("subjects", [])
    policy_area_raw = bill_detail.get("policy_area", {})
    text_versions_raw = bill_detail.get("text_versions", [])

    # Bill type code: uppercase for model validation
    bill_type_upper = bill_type_code.upper()

    # Bill number as int
    try:
        bill_num_int = int(bill_number_str)
    except (ValueError, TypeError):
        bill_num_int = 0

    # Build bill_id
    bill_id = f"{congress}-{bill_type_upper}-{bill_num_int}"

    # Sponsor
    sponsor = None
    sponsors_data = bill.get("sponsors", [])
    if sponsors_data:
        sp = sponsors_data[0] if isinstance(sponsors_data, list) else {}
        sponsor = {
            "bioguide_id": sp.get("bioguideId", ""),
            "name": _format_sponsor_name(sp),
            "party": sp.get("party", ""),
            "state": sp.get("state", ""),
        }

    # Cosponsors (compact list)
    cosponsors = []
    for cs in cosponsors_raw:
        cosponsors.append({
            "bioguide_id": cs.get("bioguideId", ""),
            "name": _format_sponsor_name(cs),
            "party": cs.get("party", ""),
            "state": cs.get("state", ""),
        })

    # Actions
    actions = []
    for act in actions_raw:
        actions.append({
            "action_date": act.get("actionDate") or None,
            "text": act.get("text", ""),
            "action_type": act.get("type", ""),
            "chamber": act.get("chamber", ""),
        })

    # Latest action (sort by date to guard against out-of-order API responses)
    latest_action = None
    if actions:
        sorted_actions = sorted(actions, key=lambda a: a.get("action_date") or "")
        latest_action = sorted_actions[-1]

    # Committees (from main bill record)
    committees = []
    bill_committees = bill.get("committees", {})
    if isinstance(bill_committees, dict):
        for comm in bill_committees.get("item", []):
            committees.append({
                "name": comm.get("name", ""),
                "systemCode": comm.get("systemCode", ""),
                "chamber": comm.get("chamber", ""),
            })

    # Subjects
    subject_names = [s.get("name", "") for s in subjects_raw if s.get("name")]

    # Policy area
    policy_area_name = policy_area_raw.get("name", "") if policy_area_raw else ""

    # Text URL (most recent version)
    text_url = ""
    if text_versions_raw:
        latest_text = text_versions_raw[0]  # API returns newest first
        formats = latest_text.get("formats", [])
        for fmt in formats:
            if fmt.get("type") == "Formatted Text":
                text_url = fmt.get("url", "")
                break
        if not text_url and formats:
            text_url = formats[0].get("url", "")

    # Congress.gov URL
    congress_url = (
        f"https://www.congress.gov/bill/"
        f"{congress}th-congress/{bill_type_code.lower()}/{bill_num_int}"
    )

    # Dates
    update_date = bill.get("updateDate", "")
    if update_date and "T" in update_date:
        update_date = update_date.split("T")[0]

    introduced_date = bill.get("introducedDate", "")

    return {
        "bill_id": bill_id,
        "congress": congress,
        "bill_type": bill_type_upper,
        "bill_number": bill_num_int,
        "title": bill.get("title", ""),
        "sponsor": sponsor,
        "cosponsors": cosponsors,
        "cosponsor_count": len(cosponsors),
        "actions": [BillAction(**a).model_dump() for a in actions],
        "latest_action": BillAction(**latest_action).model_dump() if latest_action else None,
        "committees": committees,
        "subjects": subject_names,
        "policy_area": policy_area_name,
        "text_url": text_url,
        "congress_url": congress_url,
        "relevance_score": relevance_score,
        "matched_programs": matched_programs,
        "update_date": update_date,
        "introduced_date": introduced_date,
    }


def _format_sponsor_name(member: dict) -> str:
    """Format a sponsor/cosponsor name from Congress.gov API data."""
    first = member.get("firstName", "")
    last = member.get("lastName", "")
    if first and last:
        return f"{first} {last}"
    # Fallback to full name field
    name = member.get("fullName", "") or member.get("name", "")
    if ", " in name:
        parts = name.split(", ", 1)
        return f"{parts[1]} {parts[0]}"
    return name


# ---------------------------------------------------------------------------
# Main build pipeline
# ---------------------------------------------------------------------------

async def build_congressional_intel(
    config: dict,
    programs: list[dict],
    *,
    max_bills: int | None = None,
    dry_run: bool = False,
    output_path: Path | None = None,
) -> dict:
    """Run the full congressional intelligence build pipeline.

    Args:
        config: Scanner configuration dict.
        programs: List of program records from program_inventory.json.
        max_bills: Override max bills to fetch detail for (default: from config).
        dry_run: If True, skip bill detail fetching and output writing.
        output_path: Override output file path.

    Returns:
        Dict with metadata and validated bill records.
    """
    intel_config = config.get("congressional_intel", {})
    congress = intel_config.get("congress", 119)
    relevance_threshold = intel_config.get("relevance_threshold", 0.30)
    max_bills_detail = max_bills or intel_config.get("max_bills_detail", 50)
    detail_delay = intel_config.get("detail_delay_seconds", 0.3)
    bill_types = intel_config.get("bill_types", ["hr", "s", "hjres", "sjres"])
    out_path = output_path or Path(
        intel_config.get("data_path", "data/congressional_intel.json")
    )

    # Resolve relative to project root
    if not out_path.is_absolute():
        out_path = _PROJECT_ROOT / out_path

    tribal_keywords = config.get("tribal_keywords", [])

    # Build scoring indexes
    program_keywords = _build_program_keyword_index(programs)
    cfda_to_program = _build_cfda_to_program(programs)

    logger.info(
        "Congressional intel build: congress=%d, threshold=%.2f, max_detail=%d",
        congress, relevance_threshold, max_bills_detail,
    )
    logger.info(
        "Program keyword index: %d programs, %d CFDA mappings",
        len(program_keywords), len(cfda_to_program),
    )

    # INTEL-04: Delegation enhancement note
    logger.info(
        "Delegation enhancement: committee data from cache; "
        "voting records pending Senate API availability"
    )

    # Instantiate scraper
    scraper = CongressGovScraper(config)

    if not scraper.api_key:
        logger.error(
            "CONGRESS_API_KEY not set. Cannot build congressional intel."
        )
        return {"metadata": {"error": "CONGRESS_API_KEY not set"}, "bills": []}

    # Phase 1: Collect bills via scan
    logger.info("Phase 1: Searching for Tribal-relevant bills...")
    all_items = await scraper.scan()
    logger.info("Collected %d unique bill items from scan", len(all_items))

    # Phase 2: Compute initial relevance and rank
    logger.info("Phase 2: Computing initial relevance scores...")
    scored_items: list[tuple[float, dict]] = []
    for item in all_items:
        score = compute_initial_relevance(item, tribal_keywords, program_keywords)
        scored_items.append((score, item))

    # Sort by score descending
    scored_items.sort(key=lambda x: x[0], reverse=True)

    # Select top N for detail fetching
    top_items = scored_items[:max_bills_detail]
    logger.info(
        "Top %d bills for detail fetch (score range: %.4f - %.4f)",
        len(top_items),
        top_items[0][0] if top_items else 0,
        top_items[-1][0] if top_items else 0,
    )

    if dry_run:
        logger.info("DRY RUN: Skipping detail fetches and output writing")
        for score, item in top_items[:10]:
            logger.info(
                "  %.4f  %s  %s",
                score, item.get("source_id", "?"), item.get("title", "?")[:80],
            )
        return {
            "metadata": {"dry_run": True, "candidates": len(top_items)},
            "bills": [],
        }

    # Phase 3: Fetch bill details for top candidates
    logger.info("Phase 3: Fetching bill details...")
    validated_bills: list[dict] = []
    skipped = 0
    errors = 0

    async with scraper._create_session() as session:
        for idx, (initial_score, item) in enumerate(top_items):
            bill_type = item.get("bill_type", "").lower()
            bill_number = str(item.get("bill_number", ""))
            item_congress = item.get("congress", congress)

            if not bill_type or not bill_number:
                logger.warning(
                    "Skipping item with missing bill_type/number: %s",
                    item.get("source_id", "?"),
                )
                skipped += 1
                continue

            # Only fetch detail for configured bill types
            if bill_type not in bill_types:
                skipped += 1
                continue

            try:
                detail = await scraper._fetch_bill_detail(
                    session, item_congress, bill_type, bill_number,
                )
            except Exception:
                logger.warning(
                    "Failed to fetch detail for %s-%s-%s",
                    item_congress, bill_type, bill_number,
                )
                errors += 1
                continue

            # Compute full relevance score with detail data
            full_score, matched = score_bill_relevance(
                {
                    "title": detail.get("bill", {}).get("title", item.get("title", "")),
                    "subjects": detail.get("subjects", []),
                    "committees": detail.get("bill", {}).get("committees", {}).get("item", []),
                },
                program_keywords,
                cfda_to_program,
                tribal_keywords,
            )

            # Apply threshold
            if full_score < relevance_threshold:
                skipped += 1
                continue

            # Transform to BillIntelligence format
            try:
                bill_dict = transform_to_bill_intel(
                    detail,
                    item_congress,
                    bill_type,
                    bill_number,
                    full_score,
                    matched,
                )

                # Validate with Pydantic model
                validated = BillIntelligence(**bill_dict)
                validated_bills.append(validated.model_dump())

            except Exception as exc:
                logger.warning(
                    "Validation failed for %s-%s-%s: %s",
                    item_congress, bill_type, bill_number, exc,
                )
                errors += 1

            # Rate limiting between detail fetches
            if idx < len(top_items) - 1:
                await asyncio.sleep(detail_delay)

            if (idx + 1) % 10 == 0:
                logger.info(
                    "Progress: %d/%d fetched, %d validated",
                    idx + 1, len(top_items), len(validated_bills),
                )

    # Sort by relevance score descending
    validated_bills.sort(key=lambda b: b.get("relevance_score", 0), reverse=True)

    logger.info(
        "Phase 3 complete: %d validated, %d skipped, %d errors",
        len(validated_bills), skipped, errors,
    )

    # Phase 4: Write output
    result = {
        "metadata": {
            "description": "Congressional intelligence cache for TCR advocacy",
            "built_at": datetime.now(timezone.utc).isoformat(),
            "congress": congress,
            "total_searched": len(all_items),
            "detail_fetched": len(top_items) - skipped,
            "validated_bills": len(validated_bills),
            "relevance_threshold": relevance_threshold,
            "errors": errors,
            "delegation_enhanced": True,
            "voting_records_status": (
                "House roll call votes available via Congress.gov API v3 beta "
                "(118th+ Congress); Senate votes NOT yet available in API"
            ),
        },
        "bills": validated_bills,
    }

    # Atomic write
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path_str = tempfile.mkstemp(
        dir=str(out_path.parent), suffix=".tmp", prefix="congressional_intel_"
    )
    tmp_path = Path(tmp_path_str)
    try:
        os.close(tmp_fd)
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        tmp_path.replace(out_path)
        logger.info(
            "Wrote %d validated bills to %s",
            len(validated_bills), out_path,
        )
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise

    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    """CLI entry point for the congressional intel builder."""
    parser = argparse.ArgumentParser(
        description="Build congressional_intel.json from Congress.gov API",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file path (default: from config)",
    )
    parser.add_argument(
        "--max-bills",
        type=int,
        default=None,
        help="Max bills to fetch full detail for (default: from config)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Search and score only, skip detail fetches and output",
    )
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Load config
    try:
        with open(SCANNER_CONFIG_PATH, encoding="utf-8") as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        logger.error("Failed to load config from %s: %s", SCANNER_CONFIG_PATH, exc)
        sys.exit(1)

    # Load program inventory
    try:
        with open(PROGRAM_INVENTORY_PATH, encoding="utf-8") as f:
            inventory = json.load(f)
        programs = inventory.get("programs", [])
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        logger.error(
            "Failed to load program inventory from %s: %s",
            PROGRAM_INVENTORY_PATH, exc,
        )
        sys.exit(1)

    logger.info("Loaded %d programs from inventory", len(programs))

    result = await build_congressional_intel(
        config,
        programs,
        max_bills=args.max_bills,
        dry_run=args.dry_run,
        output_path=args.output,
    )

    validated_count = len(result.get("bills", []))
    logger.info("Congressional intel build complete: %d bills", validated_count)


if __name__ == "__main__":
    asyncio.run(main())
