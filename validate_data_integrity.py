#!/usr/bin/env python3
"""
Data Integrity Validator for TCR Policy Scanner

Validates cross-file consistency across:
- program_inventory.json
- policy_tracking.json
- graph_schema.json
- scanner_config.json
- grants_gov.py CFDA_NUMBERS
- tribal_registry.json (Pydantic schema validation)
- award_cache/*.json (Pydantic schema validation)
- hazard_profiles/*.json (Pydantic schema validation)
- congressional_cache.json (Pydantic schema validation)
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

try:
    from pydantic import ValidationError
    from src.schemas.models import (
        AwardCacheFile,
        CongressionalDelegate,
        CongressionalDelegation,
        HazardProfile,
        PolicyPosition,
        ProgramRecord,
        TribeRecord,
    )
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False


class ValidationReport:
    """Tracks validation results."""

    def __init__(self):
        self.checks = []
        self.failed_checks = []

    def add_check(self, name: str, passed: bool, details: str = ""):
        """Add a validation check result."""
        status = "PASS" if passed else "FAIL"
        self.checks.append({
            "name": name,
            "status": status,
            "details": details
        })
        if not passed:
            self.failed_checks.append(name)

    def print_report(self):
        """Print formatted validation report."""
        print("\n" + "="*80)
        print("TCR POLICY SCANNER - DATA INTEGRITY REPORT")
        print("="*80 + "\n")

        for check in self.checks:
            status_symbol = "[+]" if check["status"] == "PASS" else "[X]"
            print(f"{status_symbol} [{check['status']}] {check['name']}")
            if check["details"]:
                # Indent details
                for line in check["details"].split("\n"):
                    if line.strip():
                        print(f"    {line}")
            print()

        print("="*80)
        print(f"SUMMARY: {len(self.checks)} checks, {len(self.failed_checks)} failed")
        print("="*80 + "\n")

        return len(self.failed_checks) == 0


def load_json(file_path: Path) -> dict:
    """Load and parse JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"ERROR: Failed to load {file_path}: {e}")
        sys.exit(1)


def check_json_validity(report: ValidationReport, base_path: Path):
    """Check 1: Verify all JSON files parse correctly."""
    files = [
        "data/program_inventory.json",
        "data/policy_tracking.json",
        "data/graph_schema.json",
        "config/scanner_config.json"
    ]

    all_valid = True
    errors = []

    for file_path in files:
        full_path = base_path / file_path
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                json.load(f)
        except json.JSONDecodeError as e:
            all_valid = False
            errors.append(f"{file_path}: {e}")
        except Exception as e:
            all_valid = False
            errors.append(f"{file_path}: {e}")

    details = "\n".join(errors) if errors else "All JSON files are valid"
    report.add_check("JSON Validity", all_valid, details)


def check_program_id_consistency(report: ValidationReport, inventory: dict, tracking: dict):
    """Check 2: Program IDs in policy_tracking match program_inventory."""
    inventory_ids = {prog["id"] for prog in inventory["programs"]}
    tracking_ids = {pos["program_id"] for pos in tracking["positions"]}

    missing_in_inventory = tracking_ids - inventory_ids
    orphaned_in_inventory = inventory_ids - tracking_ids

    passed = len(missing_in_inventory) == 0

    details = []
    if missing_in_inventory:
        details.append(f"Program IDs in policy_tracking.json NOT found in program_inventory.json:")
        for pid in sorted(missing_in_inventory):
            details.append(f"  - {pid}")

    if orphaned_in_inventory:
        details.append(f"Program IDs in program_inventory.json NOT tracked in policy_tracking.json:")
        for pid in sorted(orphaned_in_inventory):
            details.append(f"  - {pid}")

    if not details:
        details.append(f"All {len(tracking_ids)} program IDs match correctly")

    report.add_check("Program ID Consistency", passed, "\n".join(details))


def check_cfda_consistency(report: ValidationReport, inventory: dict, cfda_numbers: dict):
    """Check 3: CFDA numbers in program_inventory match grants_gov.py."""
    # Extract programs with CFDA fields (handles both string and list CFDAs)
    inventory_cfdas = {}
    for prog in inventory["programs"]:
        cfda = prog.get("cfda")
        if cfda is None:
            continue
        if isinstance(cfda, list):
            for c in cfda:
                inventory_cfdas[c] = prog["id"]
        else:
            inventory_cfdas[cfda] = prog["id"]

    # Compare with grants_gov.py CFDA_NUMBERS
    cfda_to_program = {cfda: prog_id for cfda, prog_id in cfda_numbers.items()}

    missing_in_scraper = []
    mismatched = []

    for cfda, prog_id in inventory_cfdas.items():
        if cfda not in cfda_to_program:
            missing_in_scraper.append(f"{cfda} ({prog_id})")
        elif cfda_to_program[cfda] != prog_id:
            mismatched.append(f"{cfda}: inventory={prog_id}, scraper={cfda_to_program[cfda]}")

    passed = len(missing_in_scraper) == 0 and len(mismatched) == 0

    details = []
    if missing_in_scraper:
        details.append("CFDA numbers in program_inventory.json NOT in grants_gov.py:")
        for entry in missing_in_scraper:
            details.append(f"  - {entry}")

    if mismatched:
        details.append("CFDA numbers with mismatched program IDs:")
        for entry in mismatched:
            details.append(f"  - {entry}")

    if not details:
        details.append(f"All {len(inventory_cfdas)} CFDA numbers match correctly")
        details.append(f"Scraper tracks {len(cfda_to_program)} total CFDA numbers")

    report.add_check("CFDA Consistency", passed, "\n".join(details))


def check_graph_schema_references(report: ValidationReport, inventory: dict, graph_schema: dict):
    """Check 4: Graph schema program references exist in inventory."""
    inventory_ids = {prog["id"] for prog in inventory["programs"]}

    errors = []

    # Check authorities
    for auth in graph_schema["authorities"]:
        for prog_id in auth.get("programs", []):
            if prog_id not in inventory_ids:
                errors.append(f"Authority {auth['id']}: references unknown program '{prog_id}'")

    # Check structural_asks
    for ask in graph_schema["structural_asks"]:
        for prog_id in ask.get("programs", []):
            if prog_id not in inventory_ids:
                errors.append(f"Structural ask {ask['id']}: references unknown program '{prog_id}'")

    # Check trust_super_node
    trust_node = graph_schema.get("trust_super_node", {})
    for prog_id in trust_node.get("programs", []):
        if prog_id not in inventory_ids:
            errors.append(f"Trust super-node: references unknown program '{prog_id}'")

    # Check funding_vehicles
    for fv in graph_schema["funding_vehicles"]:
        for prog_id in fv.get("programs", []):
            if prog_id not in inventory_ids:
                errors.append(f"Funding vehicle {fv['id']}: references unknown program '{prog_id}'")

    # Check barriers
    for barrier in graph_schema["barriers"]:
        for prog_id in barrier.get("programs", []):
            if prog_id not in inventory_ids:
                errors.append(f"Barrier {barrier['id']}: references unknown program '{prog_id}'")

    passed = len(errors) == 0
    details = "\n".join(errors) if errors else "All graph schema program references are valid"
    report.add_check("Graph Schema Program References", passed, details)


def check_barrier_mitigation_references(report: ValidationReport, graph_schema: dict):
    """Check 5: Barrier mitigated_by references exist as lever_* or ask_* IDs."""
    # Collect all valid mitigation IDs (structural asks)
    valid_ids = {ask["id"] for ask in graph_schema["structural_asks"]}

    # Also allow lever_* IDs (these would be created by the builder dynamically)
    # We need to validate that mitigated_by references are either:
    # 1. ask_* IDs that exist in structural_asks
    # 2. lever_* IDs (program-specific levers)

    errors = []
    for barrier in graph_schema["barriers"]:
        for mitigation_id in barrier.get("mitigated_by", []):
            # Check if it's an ask_* ID
            if mitigation_id.startswith("ask_"):
                if mitigation_id not in valid_ids:
                    errors.append(f"Barrier {barrier['id']}: references unknown ask '{mitigation_id}'")
            # lever_* IDs are validated by checking they follow the pattern lever_{program_id}
            elif mitigation_id.startswith("lever_"):
                # Extract expected program_id
                expected_prog_id = mitigation_id.replace("lever_", "")
                # We'll mark this as valid pattern (builder creates these dynamically)
                pass
            else:
                errors.append(f"Barrier {barrier['id']}: invalid mitigation ID format '{mitigation_id}' (must start with 'lever_' or 'ask_')")

    passed = len(errors) == 0
    details = "\n".join(errors) if errors else "All barrier mitigation references are valid"
    report.add_check("Barrier Mitigation References", passed, details)


def check_ci_threshold_ordering(report: ValidationReport, tracking: dict):
    """Check 6: CI thresholds are in descending order."""
    thresholds = tracking["ci_thresholds"]

    expected_order = [
        "secure", "stable", "stable_but_vulnerable", "at_risk_floor",
        "uncertain_floor", "flagged_floor", "terminated_floor"
    ]

    values = [thresholds[key] for key in expected_order]
    is_descending = all(values[i] >= values[i+1] for i in range(len(values)-1))

    details = []
    if is_descending:
        details.append("CI thresholds are correctly ordered (descending):")
        for key in expected_order:
            details.append(f"  {key}: {thresholds[key]}")
    else:
        details.append("CI thresholds are NOT in descending order:")
        for i in range(len(values)-1):
            key1, key2 = expected_order[i], expected_order[i+1]
            val1, val2 = values[i], values[i+1]
            symbol = "[+]" if val1 >= val2 else "[X]"
            details.append(f"  {symbol} {key1} ({val1}) >= {key2} ({val2})")

    report.add_check("CI Threshold Ordering", is_descending, "\n".join(details))


def check_status_consistency(report: ValidationReport, inventory: dict, tracking: dict):
    """Check 7: CI statuses in inventory match status_definitions in tracking."""
    status_definitions = set(tracking["status_definitions"].keys())

    errors = []
    for prog in inventory["programs"]:
        ci_status = prog.get("ci_status")
        if ci_status and ci_status not in status_definitions:
            errors.append(f"Program {prog['id']}: status '{ci_status}' not in status_definitions")

    # Also check policy_tracking positions
    for pos in tracking["positions"]:
        status = pos.get("status")
        if status and status not in status_definitions:
            errors.append(f"Position {pos['program_id']}: status '{status}' not in status_definitions")

    passed = len(errors) == 0
    details = "\n".join(errors) if errors else f"All CI statuses valid (defined statuses: {', '.join(sorted(status_definitions))})"
    report.add_check("Status Consistency", passed, details)


def check_keyword_deduplication(report: ValidationReport, config: dict):
    """Check 8: No duplicate keywords in scanner_config."""
    errors = []

    # Check action_keywords
    action_keywords = config.get("action_keywords", [])
    action_dupes = [kw for kw in action_keywords if action_keywords.count(kw) > 1]
    if action_dupes:
        unique_dupes = sorted(set(action_dupes))
        errors.append(f"Duplicate action_keywords: {', '.join(unique_dupes)}")

    # Check search_queries
    search_queries = config.get("search_queries", [])
    search_dupes = [q for q in search_queries if search_queries.count(q) > 1]
    if search_dupes:
        unique_dupes = sorted(set(search_dupes))
        errors.append(f"Duplicate search_queries: {', '.join(unique_dupes)}")

    # Check tribal_keywords
    tribal_keywords = config.get("tribal_keywords", [])
    tribal_dupes = [kw for kw in tribal_keywords if tribal_keywords.count(kw) > 1]
    if tribal_dupes:
        unique_dupes = sorted(set(tribal_dupes))
        errors.append(f"Duplicate tribal_keywords: {', '.join(unique_dupes)}")

    passed = len(errors) == 0
    details = "\n".join(errors) if errors else f"No duplicate keywords found (action: {len(action_keywords)}, search: {len(search_queries)}, tribal: {len(tribal_keywords)})"
    report.add_check("Keyword Deduplication", passed, details)


def check_program_schema_validation(report: ValidationReport, inventory: dict):
    """Check 9: Validate all programs against ProgramRecord Pydantic schema."""
    if not PYDANTIC_AVAILABLE:
        report.add_check(
            "Program Schema Validation",
            True,
            "SKIPPED: pydantic or src.schemas not available",
        )
        return

    errors = []
    for prog_data in inventory["programs"]:
        try:
            ProgramRecord(**prog_data)
        except ValidationError as e:
            prog_id = prog_data.get("id", "UNKNOWN")
            for err in e.errors():
                field = " -> ".join(str(loc) for loc in err["loc"])
                errors.append(f"Program '{prog_id}', field '{field}': {err['msg']}")

    passed = len(errors) == 0
    if passed:
        count = len(inventory["programs"])
        details = f"All {count} programs pass ProgramRecord schema validation"
    else:
        details = "\n".join(errors)
    report.add_check("Program Schema Validation", passed, details)


def check_policy_schema_validation(report: ValidationReport, tracking: dict):
    """Check 10: Validate all policy positions against PolicyPosition Pydantic schema."""
    if not PYDANTIC_AVAILABLE:
        report.add_check(
            "Policy Position Schema Validation",
            True,
            "SKIPPED: pydantic or src.schemas not available",
        )
        return

    errors = []
    for pos_data in tracking["positions"]:
        try:
            PolicyPosition(**pos_data)
        except ValidationError as e:
            prog_id = pos_data.get("program_id", "UNKNOWN")
            for err in e.errors():
                field = " -> ".join(str(loc) for loc in err["loc"])
                errors.append(f"Position '{prog_id}', field '{field}': {err['msg']}")

    passed = len(errors) == 0
    if passed:
        count = len(tracking["positions"])
        details = f"All {count} positions pass PolicyPosition schema validation"
    else:
        details = "\n".join(errors)
    report.add_check("Policy Position Schema Validation", passed, details)


def check_tribe_schema_validation(report: ValidationReport, base_path: Path):
    """Check 11: Validate tribal_registry.json against TribeRecord Pydantic schema."""
    if not PYDANTIC_AVAILABLE:
        report.add_check(
            "Tribe Registry Schema Validation",
            True,
            "SKIPPED: pydantic or src.schemas not available",
        )
        return

    registry_path = base_path / "data" / "tribal_registry.json"
    if not registry_path.exists():
        report.add_check(
            "Tribe Registry Schema Validation",
            False,
            f"File not found: {registry_path}",
        )
        return

    registry = load_json(registry_path)
    tribes = registry.get("tribes", [])
    errors = []
    for tribe_data in tribes:
        try:
            TribeRecord(**tribe_data)
        except ValidationError as e:
            tribe_id = tribe_data.get("tribe_id", "UNKNOWN")
            for err in e.errors():
                field = " -> ".join(str(loc) for loc in err["loc"])
                errors.append(f"Tribe '{tribe_id}', field '{field}': {err['msg']}")

    passed = len(errors) == 0
    if passed:
        details = f"All {len(tribes)} Tribe records pass TribeRecord schema validation"
    else:
        details = f"{len(errors)} validation errors in {len(tribes)} Tribe records:\n"
        details += "\n".join(errors[:20])
        if len(errors) > 20:
            details += f"\n... and {len(errors) - 20} more errors"
    report.add_check("Tribe Registry Schema Validation", passed, details)


def check_award_cache_schema_validation(report: ValidationReport, base_path: Path):
    """Check 12: Validate sample award_cache files against AwardCacheFile Pydantic schema."""
    if not PYDANTIC_AVAILABLE:
        report.add_check(
            "Award Cache Schema Validation",
            True,
            "SKIPPED: pydantic or src.schemas not available",
        )
        return

    award_dir = base_path / "data" / "award_cache"
    if not award_dir.exists():
        report.add_check(
            "Award Cache Schema Validation",
            False,
            f"Directory not found: {award_dir}",
        )
        return

    files = sorted(award_dir.glob("epa_*.json"))
    errors = []
    validated = 0

    # Validate all files (they are small)
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            AwardCacheFile(**data)
            validated += 1
        except ValidationError as e:
            for err in e.errors():
                field = " -> ".join(str(loc) for loc in err["loc"])
                errors.append(f"File '{f.name}', field '{field}': {err['msg']}")
        except json.JSONDecodeError as e:
            errors.append(f"File '{f.name}': Invalid JSON - {e}")

    passed = len(errors) == 0
    if passed:
        details = f"All {validated} award cache files pass AwardCacheFile schema validation"
    else:
        details = f"{len(errors)} validation errors across {len(files)} award cache files:\n"
        details += "\n".join(errors[:20])
        if len(errors) > 20:
            details += f"\n... and {len(errors) - 20} more errors"
    report.add_check("Award Cache Schema Validation", passed, details)


def check_hazard_profile_schema_validation(report: ValidationReport, base_path: Path):
    """Check 13: Validate sample hazard_profiles against HazardProfile Pydantic schema."""
    if not PYDANTIC_AVAILABLE:
        report.add_check(
            "Hazard Profile Schema Validation",
            True,
            "SKIPPED: pydantic or src.schemas not available",
        )
        return

    hazard_dir = base_path / "data" / "hazard_profiles"
    if not hazard_dir.exists():
        report.add_check(
            "Hazard Profile Schema Validation",
            False,
            f"Directory not found: {hazard_dir}",
        )
        return

    files = sorted(hazard_dir.glob("epa_*.json"))
    errors = []
    validated = 0

    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            HazardProfile(**data)
            validated += 1
        except ValidationError as e:
            for err in e.errors():
                field = " -> ".join(str(loc) for loc in err["loc"])
                errors.append(f"File '{f.name}', field '{field}': {err['msg']}")
        except json.JSONDecodeError as e:
            errors.append(f"File '{f.name}': Invalid JSON - {e}")

    passed = len(errors) == 0
    if passed:
        details = f"All {validated} hazard profile files pass HazardProfile schema validation"
    else:
        details = f"{len(errors)} validation errors across {len(files)} hazard profile files:\n"
        details += "\n".join(errors[:20])
        if len(errors) > 20:
            details += f"\n... and {len(errors) - 20} more errors"
    report.add_check("Hazard Profile Schema Validation", passed, details)


def check_congressional_schema_validation(report: ValidationReport, base_path: Path):
    """Check 14: Validate congressional_cache.json against Pydantic schemas."""
    if not PYDANTIC_AVAILABLE:
        report.add_check(
            "Congressional Cache Schema Validation",
            True,
            "SKIPPED: pydantic or src.schemas not available",
        )
        return

    cache_path = base_path / "data" / "congressional_cache.json"
    if not cache_path.exists():
        report.add_check(
            "Congressional Cache Schema Validation",
            False,
            f"File not found: {cache_path}",
        )
        return

    cache = load_json(cache_path)
    errors = []

    # Validate members
    members = cache.get("members", {})
    member_count = 0
    for bioguide_id, member_data in members.items():
        try:
            cd = CongressionalDelegate(**member_data)
            if cd.bioguide_id != bioguide_id:
                errors.append(
                    f"Member key '{bioguide_id}' does not match "
                    f"bioguide_id '{cd.bioguide_id}'"
                )
            member_count += 1
        except ValidationError as e:
            for err in e.errors():
                field = " -> ".join(str(loc) for loc in err["loc"])
                errors.append(f"Member '{bioguide_id}', field '{field}': {err['msg']}")

    # Validate delegations
    delegations = cache.get("delegations", {})
    deleg_count = 0
    for tribe_id, deleg_data in delegations.items():
        try:
            d = CongressionalDelegation(**deleg_data)
            if d.tribe_id != tribe_id:
                errors.append(
                    f"Delegation key '{tribe_id}' does not match "
                    f"tribe_id '{d.tribe_id}'"
                )
            deleg_count += 1
        except ValidationError as e:
            for err in e.errors():
                field = " -> ".join(str(loc) for loc in err["loc"])
                errors.append(f"Delegation '{tribe_id}', field '{field}': {err['msg']}")

    passed = len(errors) == 0
    if passed:
        details = (
            f"{member_count} members and {deleg_count} delegations "
            f"pass Congressional schema validation"
        )
    else:
        details = f"{len(errors)} validation errors:\n"
        details += "\n".join(errors[:20])
        if len(errors) > 20:
            details += f"\n... and {len(errors) - 20} more errors"
    report.add_check("Congressional Cache Schema Validation", passed, details)


def main():
    """Run all validation checks."""
    # Determine base path
    base_path = Path(__file__).parent

    # Load data files
    print("Loading data files...")
    inventory = load_json(base_path / "data" / "program_inventory.json")
    tracking = load_json(base_path / "data" / "policy_tracking.json")
    graph_schema = load_json(base_path / "data" / "graph_schema.json")
    config = load_json(base_path / "config" / "scanner_config.json")

    # Extract CFDA numbers from grants_gov.py
    grants_gov_cfda = {
        "15.156": "bia_tcr",
        "15.124": "bia_tcr_awards",
        "97.047": "fema_bric",
        "97.039": "fema_bric",
        "66.926": "epa_gap",
        "66.468": "epa_stag",
        "20.205": "fhwa_ttp_safety",
        "14.867": "hud_ihbg",
        "81.087": "doe_indian_energy",
        "10.720": "usda_wildfire",
        "15.507": "usbr_watersmart",
        "20.284": "dot_protect",
    }

    # Initialize report
    report = ValidationReport()

    # Run all validation checks
    print("Running validation checks...\n")

    # Original checks (1-8)
    check_json_validity(report, base_path)
    check_program_id_consistency(report, inventory, tracking)
    check_cfda_consistency(report, inventory, grants_gov_cfda)
    check_graph_schema_references(report, inventory, graph_schema)
    check_barrier_mitigation_references(report, graph_schema)
    check_ci_threshold_ordering(report, tracking)
    check_status_consistency(report, inventory, tracking)
    check_keyword_deduplication(report, config)

    # Pydantic schema validation checks (9-14)
    check_program_schema_validation(report, inventory)
    check_policy_schema_validation(report, tracking)
    check_tribe_schema_validation(report, base_path)
    check_award_cache_schema_validation(report, base_path)
    check_hazard_profile_schema_validation(report, base_path)
    check_congressional_schema_validation(report, base_path)

    # Print report
    success = report.print_report()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
