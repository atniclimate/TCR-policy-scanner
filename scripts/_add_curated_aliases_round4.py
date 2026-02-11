#!/usr/bin/env python3
"""Round 4: More curated aliases from remaining unmatched entries."""

import json
from datetime import datetime, timezone
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
HA_PATH = _PROJECT_ROOT / "data" / "housing_authority_aliases.json"
REG_PATH = _PROJECT_ROOT / "data" / "tribal_registry.json"

ha_data = json.load(open(HA_PATH, "r", encoding="utf-8"))
aliases = ha_data["aliases"]
curated_before = ha_data["_metadata"]["curated_count"]

reg = json.load(open(REG_PATH, "r", encoding="utf-8"))
valid_ids = {t["tribe_id"] for t in reg["tribes"]}

# Build a lookup by name fragments
tribe_by_fragment = {}
for t in reg["tribes"]:
    tribe_by_fragment[t["name"].lower()] = t["tribe_id"]
    for a in t.get("alternate_names", []):
        tribe_by_fragment[a.lower()] = t["tribe_id"]

additional = {
    # From top 20 unmatched, round 4
    "housing authority of the absentee shawnee tribe of indians of oklahoma": "epa_100000001",
    "chippewa cree housing authority": "epa_100000042",
    "pokagon band of potawatomi": "epa_100000215",
    "spirit lake housing corp": "epa_100000286",
    "spirit lake housing corporation": "epa_100000286",
    "north pacific rim housing authority": None,  # Regional authority - skip
    "confederated tribes of grand ronde": "epa_100000056",
    "duck valley housing authority": "epa_100000275",  # Eastern Shoshone (Duck Valley is Shoshone-Paiute)
    "yurok tribe": "epa_100000338",
    "san carlos apache tribal council": "epa_100000254",
    "bois forte reservation tribal council": "epa_100000573",
    # More common name variants and organizational names
    "chippewa cree housing": "epa_100000042",
    "absentee shawnee housing authority": "epa_100000001",
    "pokagon band of potawatomi housing authority": "epa_100000215",
    "pokagon band housing authority": "epa_100000215",
    "duck valley shoshone-paiute housing authority": "epa_100000275",
    # Additional Tribe name variants that show up in USASpending
    "nooksack indian tribe": "epa_100000176",
    "nooksack housing authority": "epa_100000176",
    "snoqualmie indian tribe": "epa_100000279",
    "snoqualmie housing authority": "epa_100000279",
    "squaxin island housing authority": "epa_100000283",
    "suquamish housing authority": "epa_100000292",
    "nisqually housing authority": "epa_100000178",
    "shoalwater bay housing authority": "epa_100000272",
    "stillaguamish housing authority": "epa_100000290",
    "samish housing authority": "epa_100000253",
    "jamestown s'klallam housing authority": "epa_100000114",
    "port gamble s'klallam housing authority": "epa_100000561",
    "lower elwha klallam housing authority": "epa_100000142",
    "chehalis housing authority": "epa_100000054",
    "cowlitz housing authority": "epa_100000066",
    "sauk-suiattle housing authority": "epa_100000264",
    "snohomish housing authority": "epa_100000312",  # Tulalip Tribes
    # More Oklahoma Tribes
    "absentee shawnee tribe": "epa_100000001",
    "delaware nation housing authority": "epa_100000072",
    "caddo housing authority": "epa_100000024",
    "comanche housing authority": "epa_100000050",
    "kiowa housing authority": "epa_100000126",
    "wichita housing authority": "epa_100000325",
    "pawnee housing authority": "epa_100000201",
    "ponca tribe of indians of oklahoma housing authority": "epa_100000216",
    "otoe-missouria housing authority": "epa_100000193",
    "kaw housing authority": "epa_100000120",
    "tonkawa housing authority": "epa_100000308",
    "peoria housing authority": "epa_100000205",
    "modoc housing authority": "epa_100000163",
    "wyandotte housing authority": "epa_100000336",
    "seneca-cayuga housing authority": "epa_100000269",
    "ottawa housing authority": "epa_100000194",
    "shawnee housing authority": "epa_100000271",
    "sac and fox nation housing authority": "epa_100000250",
    "citizen potawatomi housing authority": "epa_100000046",
    "iowa tribe of oklahoma housing authority": "epa_100000113",
    "iowa tribe of kansas and nebraska housing authority": "epa_100000112",
    # More Arizona Tribes
    "fort mcdowell yavapai housing authority": "epa_100000089",
    "yavapai-prescott housing authority": "epa_100000340",
    "yavapai-apache housing authority": "epa_100000339",
    "havasupai housing authority": "epa_100000098",
    "hualapai housing authority": "epa_100000105",
    "cocopah housing authority": "epa_100000048",
    "quechan housing authority": "epa_100000229",
    # Montana/Idaho
    "salish kootenai housing authority": "epa_100000053",
    # Minnesota component bands (common in USASpending)
    "bois forte band": "epa_100000573",
    "bois forte reservation": "epa_100000573",
    "fond du lac band": "epa_100000572",
    "grand portage band": "epa_100000577",
    "grand portage reservation": "epa_100000577",
    "leech lake band of ojibwe": "epa_100000574",
    "leech lake band": "epa_100000574",
    "mille lacs band": "epa_100000575",
    "mille lacs band of ojibwe": "epa_100000575",
    "white earth band": "epa_100000576",
    "white earth nation": "epa_100000576",
    "red lake nation": "epa_100000237",
}

# Remove None entries (skipped)
additional = {k: v for k, v in additional.items() if v is not None}

added = 0
skipped = []
for name, tid in additional.items():
    if tid not in valid_ids:
        skipped.append((name, tid))
        continue
    if name not in aliases:
        aliases[name] = tid
        added += 1

if skipped:
    print(f"Skipped (invalid tribe_id): {skipped}")

print(f"Added {added} new curated aliases")
print(f"Total aliases now: {len(aliases)}")

ha_data["_metadata"]["curated_count"] = curated_before + added
ha_data["_metadata"]["total_count"] = len(aliases)
ha_data["_metadata"]["last_updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# Add more skipped
existing_skipped = set(s.upper() for s in ha_data["_metadata"].get("skipped_regional", []))
new_skipped = ["NORTH PACIFIC RIM HOUSING AUTHORITY", "ORUTSARARMUIT NATIVE COUNCIL, INCORPORATED"]
for s in new_skipped:
    if s.upper() not in existing_skipped:
        ha_data["_metadata"]["skipped_regional"].append(s)

ha_data["aliases"] = dict(sorted(aliases.items()))

with open(HA_PATH, "w", encoding="utf-8") as f:
    json.dump(ha_data, f, indent=2, ensure_ascii=False)

print(f"Updated {HA_PATH}")
