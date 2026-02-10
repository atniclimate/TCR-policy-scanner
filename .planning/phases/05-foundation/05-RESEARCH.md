# Phase 5: Foundation - Research

**Researched:** 2026-02-10
**Domain:** Tribal registry, congressional mapping, CLI skeleton, graph schema
**Confidence:** HIGH (6 team parallel research + integration synthesis + live API verification)

## Summary

Phase 5 establishes the data backbone for all downstream Tribe-specific advocacy packet generation. It delivers three major components: (1) a 575-Tribe registry built from the EPA Tribes Names Service API with ecoregion classification, (2) a congressional delegation cache combining Census CD119-AIANNH relationship data with Congress.gov member data and unitedstates/congress-legislators committee membership, and (3) a `--prep-packets` CLI skeleton with `PacketOrchestrator` that resolves Tribe names and displays delegation information.

The research identified one critical deviation from the CONTEXT.md: BIA codes cannot serve as the universal primary key because ~230 Alaska Native entities have BIA code "TBD". The EPA Internal ID (`epa_{epaTribalInternalId}`) is the recommended universal primary key. The AIANNH-to-Tribe name linkage (connecting Census geographic entities to EPA Tribe records) is the hardest integration challenge, requiring a three-tier approach: automated name matching, curated alias table, and manual fallback.

**Primary recommendation:** Build `tribal_registry.json` from a single EPA API call, `congressional_cache.json` from Census + Congress.gov + unitedstates YAML, and a `src/packets/` module package that loads these files at runtime -- no geospatial dependencies, no PDF parsing, no complex build pipeline.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| aiohttp | >=3.9.0 (existing) | HTTP client for EPA API and Congress.gov API | Already in requirements.txt; async pattern established in codebase |
| csv | stdlib | Parse Census CD119-AIANNH pipe-delimited file | Zero-dependency, handles pipe delimiter natively |
| json | stdlib | Read/write tribal_registry.json, congressional_cache.json | Existing codebase pattern for all data files |
| pathlib | stdlib | File paths throughout | Existing codebase pattern |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| rapidfuzz | 3.14.x | Fuzzy Tribe name matching (token_sort_ratio) | Tribe name resolution fallback when exact/substring fails; also used in Phase 6 for award matching |
| pyyaml | 6.0.x | Parse unitedstates/congress-legislators YAML files | Committee membership data loading during cache build |
| python-docx | 1.2.0 | DOCX generation (Phase 7, install now) | Install in Phase 5 to stabilize dependencies; openpyxl comes as a transitive dependency |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| rapidfuzz | difflib.SequenceMatcher (stdlib) | difflib is ~10x slower; Phase 6 needs rapidfuzz anyway; single dependency for both phases |
| pyyaml | json (after converting YAML to JSON) | YAML source is canonical; converting adds a manual step; pyyaml is lightweight |
| csv (for Census file) | pandas | Massive overkill for a 178KB pipe-delimited file; pandas adds 40MB+ dependency |
| state-based ecoregion lookup | geopandas + shapefile | geopandas requires GDAL C library; state-level precision sufficient for advocacy classification |

**Installation:**
```bash
pip install rapidfuzz>=3.14.0 pyyaml>=6.0.0 python-docx>=1.1.0
```

**Do NOT add:** geopandas, shapely, fiona, GDAL, camelot, tabula-py, pdfplumber, Pydantic, rich (for v1.1).

## Architecture Patterns

### Recommended Project Structure
```
src/
    packets/
        __init__.py          # empty
        orchestrator.py      # PacketOrchestrator -- main coordinator
        context.py           # TribePacketContext dataclass
        registry.py          # TribalRegistry -- loads registry, resolves names
        congress.py          # CongressionalMapper -- delegation lookups
        ecoregion.py         # EcoregionMapper -- state-to-ecoregion + program priorities
data/
    tribal_registry.json     # 575 Tribes (~280 KB, built once)
    congressional_cache.json # 119th Congress delegation (~650 KB, built once)
    ecoregion_config.json    # 7-region scheme + program priorities (~10 KB, static)
    aiannh_tribe_crosswalk.json  # Census-to-EPA name mapping (~15 KB, curated)
    census/
        tab20_cd11920_aiannh20_natl.txt  # Census relationship file (178 KB, downloaded)
scripts/
    build_registry.py        # One-time: EPA API -> tribal_registry.json
    build_congress_cache.py   # One-time: Census + Congress.gov + YAML -> congressional_cache.json
```

### Pattern 1: CLI Extension as Flat Flag
**What:** Add `--prep-packets`, `--tribe`, `--all-tribes` as top-level argparse flags
**When to use:** Extending the existing CLI without breaking the flat-flag pattern
**Example:**
```python
# Source: Existing main.py pattern (lines 285-329)
parser.add_argument("--prep-packets", action="store_true",
                    help="Generate Tribe-specific advocacy packets")
parser.add_argument("--tribe", type=str,
                    help="Tribe name for single packet (used with --prep-packets)")
parser.add_argument("--all-tribes", action="store_true",
                    help="Generate for all 575 Tribes (used with --prep-packets)")

# Dispatch before run_pipeline (lazy import):
if args.prep_packets:
    from src.packets.orchestrator import PacketOrchestrator
    orchestrator = PacketOrchestrator(config, programs)
    if args.all_tribes:
        orchestrator.run_all_tribes()
    elif args.tribe:
        orchestrator.run_single_tribe(args.tribe)
    else:
        parser.error("--prep-packets requires --tribe <name> or --all-tribes")
    return
```

### Pattern 2: Lazy-Load JSON Data Files
**What:** Load registry/congress data on first access, not at import time
**When to use:** Registry and congress modules -- avoid loading 1MB+ data when not needed
**Example:**
```python
# Source: Existing codebase pattern (config loading)
class TribalRegistry:
    def __init__(self, config: dict):
        packet_config = config.get("packets", {})
        self.data_path = Path(
            packet_config.get("tribal_registry", {}).get("data_path", "data/tribal_registry.json")
        )
        self._tribes: list[dict] = []
        self._loaded = False

    def _load(self) -> None:
        if self._loaded:
            return
        with open(self.data_path, encoding="utf-8") as f:
            data = json.load(f)
        self._tribes = data.get("tribes", [])
        self._loaded = True
        logger.info("Loaded %d Tribes from %s", len(self._tribes), self.data_path)
```

### Pattern 3: Three-Tier Name Resolution
**What:** Exact match -> substring match -> fuzzy match, with early termination
**When to use:** `TribalRegistry.resolve(name)` -- the core search pipeline
**Example:**
```python
def resolve(self, query: str) -> dict | None:
    self._load()
    q = query.strip().lower()

    # Tier 1: Exact match on official name
    for tribe in self._tribes:
        if tribe["name"].lower() == q:
            return tribe

    # Tier 2: Substring match across name + alternates
    candidates = []
    for tribe in self._tribes:
        searchable = [tribe["name"]] + tribe.get("alternate_names", [])
        searchable += [h["name"] for h in tribe.get("historical_names", [])]
        for name in searchable:
            if q in name.lower():
                candidates.append(tribe)
                break
    if len(candidates) == 1:
        return candidates[0]
    if candidates:
        return candidates  # Ambiguous -- caller decides

    # Tier 3: Fuzzy fallback (rapidfuzz)
    from rapidfuzz import fuzz, process
    corpus = self._build_search_corpus()
    results = process.extract(q, [c[0] for c in corpus], scorer=fuzz.token_sort_ratio, limit=5)
    # Return best match if score > threshold
```

### Pattern 4: Dataclass Node Types in schema.py
**What:** Add TribeNode and CongressionalDistrictNode alongside existing node types
**When to use:** Graph schema additions -- follow existing ProgramNode pattern exactly
**Example:**
```python
# Source: Existing src/graph/schema.py pattern
@dataclass
class TribeNode:
    """Federally recognized Tribal Nation."""
    id: str              # epa_{epaTribalInternalId}
    name: str            # Official BIA name
    state: str = ""      # Primary state (or comma-separated)
    ecoregion: str = ""  # Primary ecoregion

@dataclass
class CongressionalDistrictNode:
    """U.S. Congressional District."""
    id: str              # e.g., "AZ-01", "AK-AL"
    state: str = ""
    representative: str = ""
    party: str = ""
```

### Pattern 5: Atomic Writes for Data Files
**What:** Write to tmp file, then rename (atomic replace)
**When to use:** All JSON file writes (registry build, congress cache build)
**Example:**
```python
# Source: Existing main.py pattern (lines 155-159)
tmp_path = output_path.with_suffix(".tmp")
with open(tmp_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, default=str)
tmp_path.replace(output_path)
```

### Anti-Patterns to Avoid
- **Importing geospatial libraries:** No geopandas, shapely, GDAL. State-based ecoregion lookup replaces all geospatial needs.
- **PDF parsing for CRS R48107:** R48107 covers the 118th Congress (stale). Census CD119-AIANNH file is the correct 119th Congress source.
- **Using BIA code as universal primary key:** ~230 Alaska Native Tribes have BIA code "TBD". Use EPA Internal ID.
- **Subcommands in argparse:** The existing CLI uses flat flags only. Do not refactor to subparsers.
- **Print statements in library code:** Use `logger.info()` in `src/packets/` modules. Only `main.py` dispatch code uses `print()`.
- **Relative imports:** Always use absolute `from src.packets.registry import TribalRegistry`.
- **`datetime.utcnow()`:** Deprecated in Python 3.12. Use `datetime.now(timezone.utc)`.
- **`open()` without encoding:** Always pass `encoding="utf-8"` on Windows.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tribe-to-district crosswalk | PDF parser for CRS R48107 | Census CD119-AIANNH file (`tab20_cd11920_aiannh20_natl.txt`) | R48107 is 118th Congress (stale); Census file is 119th, machine-readable, includes area overlap |
| Committee membership mapping | Congressional committee page scraper | `unitedstates/congress-legislators` `committee-membership-current.yaml` | Congress.gov API has NO committee membership endpoint (verified through Jan 2026 changelog) |
| Congressional member data | Custom member scraper | Congress.gov API v3 `/member/congress/119` | Official API, 5000 req/hr, well-documented |
| Fuzzy name matching | difflib.SequenceMatcher | `rapidfuzz.fuzz.token_sort_ratio` | C++ speed; same library Phase 6 needs for award matching |
| YAML parsing | Custom parser or JSON conversion | `pyyaml` (yaml.safe_load) | Standard library for unitedstates dataset; 1 line to parse |
| Ecoregion classification | Geospatial join with shapefiles | Static state-to-ecoregion JSON lookup | Eliminates GDAL/geopandas dependency entirely; state-level precision sufficient |
| Tribe ID generation | Slugified names ("navajo-nation") | EPA Internal ID (`epa_100000171`) | Tribe names contain apostrophes/diacritics; names change over time; BIA codes missing for Alaska |
| Member photos for DOCX | Custom bioguide scraper | `depiction.imageUrl` from Congress.gov member detail endpoint | API already provides portrait URL |
| FIPS-to-state mapping | External data file | Static 56-entry Python dict | Only 56 FIPS codes; never changes |

**Key insight:** Every data source for Phase 5 is either a single API call (EPA), a downloadable flat file (Census), a GitHub YAML file (unitedstates), or a paginated API (Congress.gov). No scraping, no parsing complex formats, no geospatial processing.

## Common Pitfalls

### Pitfall 1: EPA API Default Filter Excludes Most Tribes
**What goes wrong:** Calling the EPA API without `tribalBandFilter=AllTribes` returns only ~260 records instead of ~574.
**Why it happens:** The default value of `tribalBandFilter` is `"ExcludeTribalBands"`, which excludes Alaska Native entities and tribal bands.
**How to avoid:** Always pass `tribalBandFilter=AllTribes` in the API request.
**Warning signs:** Registry loads with ~260 Tribes instead of ~574.

### Pitfall 2: Alaska Native BIA Codes Are "TBD"
**What goes wrong:** Using BIA code as primary key leaves ~230 Alaska Native entities without a valid key.
**Why it happens:** BIA has not assigned tribal codes to Alaska Native entities. The EPA API returns `currentBIATribalCode: "TBD"` for all Alaska records.
**How to avoid:** Use `epa_{epaTribalInternalId}` as universal primary key. Store BIA code as optional secondary field.
**Warning signs:** 40% of Tribes have `tribe_id` of `bia_TBD` (collision).

### Pitfall 3: Census AIANNH Names Differ from EPA/BIA Names
**What goes wrong:** Automated matching between Census and EPA names fails for many Tribes because naming conventions differ.
**Why it happens:** Census uses geographic descriptions ("Navajo Nation Reservation and Off-Reservation Trust Land") while EPA uses political names ("Navajo Nation, Arizona, New Mexico, & Utah").
**How to avoid:** Three-tier linkage: (1) normalize and strip suffixes, (2) curated alias table in `aiannh_tribe_crosswalk.json`, (3) manual fallback for remaining ~10%.
**Warning signs:** After automated matching, >50 Tribes are unmatched.

### Pitfall 4: CRS R48107 Maps to Wrong Congress
**What goes wrong:** Using R48107 district data produces incorrect mappings because the 119th Congress has different district boundaries than the 118th.
**Why it happens:** R48107 version 6 (Sep 2024) covers the 118th Congress (2023-2025), not the current 119th Congress (2025-2027).
**How to avoid:** Use Census CD119-AIANNH relationship file instead. It is dated 2024-10-24 and specifically covers the 119th Congress.
**Warning signs:** District numbers don't match current congressional records.

### Pitfall 5: Congress.gov API Has No Committee Membership Endpoint
**What goes wrong:** Attempting to list members of a specific committee via the Congress.gov API returns no results.
**Why it happens:** The API provides committee metadata, bills, reports, and nominations -- but NOT member rosters. Verified through ChangeLog January 2026.
**How to avoid:** Use the `unitedstates/congress-legislators` `committee-membership-current.yaml` file for committee assignments. Cross-reference via `bioguideId`.
**Warning signs:** Empty committee member lists in the cache despite committees existing.

### Pitfall 6: Lumbee Tribe Missing from EPA Data
**What goes wrong:** The 575th federally recognized Tribe (Lumbee, added via FY2026 NDAA) is not found in the EPA API.
**Why it happens:** EPA updates its Tribes Names Service from the BIA Federal Register list periodically (at least annually). The Lumbee addition (Federal Register 2026-01899, published 2026-01-30) has not been reflected yet.
**How to avoid:** Log a warning: "Lumbee Tribe not found in EPA data." Do not fabricate an entry. The registry will show 574 Tribes until EPA updates.
**Warning signs:** Tribe count is 574 instead of 575.

### Pitfall 7: Windows Encoding Corruption
**What goes wrong:** Tribe names with apostrophes (Coeur d'Alene), ampersands, or diacritics are corrupted when written to files.
**Why it happens:** Python `open()` on Windows defaults to the system locale encoding (often cp1252), not UTF-8.
**How to avoid:** Every `open()` call must include `encoding="utf-8"`. Every `Path.write_text()` must include `encoding="utf-8"`.
**Warning signs:** Mojibake in Tribe names, test failures on Windows but not Linux.

### Pitfall 8: Congress.gov API Key in URL Query Params
**What goes wrong:** API key leaks in HTTP referer headers, server logs, and browser history.
**Why it happens:** Some examples show `?api_key=XXX` in the URL.
**How to avoid:** Pass the API key via the `X-Api-Key` header (already the pattern in existing `congress_gov.py` line 49).
**Warning signs:** API key visible in URL strings in logs.

## Code Examples

Verified patterns from official sources:

### EPA API: Fetch All Tribes (REG-01)
```python
# Source: EPA Tribes Names Service API -- verified live 2026-02-10
# Endpoint returns ~574 records in a single call, no auth required
async def fetch_all_tribes(session: aiohttp.ClientSession) -> list[dict]:
    """Fetch all federally recognized Tribes from EPA Tribes Names Service."""
    url = "https://cdxapi.epa.gov/oms-tribes-rest-services/api/v1/tribeDetails"
    params = {"tribalBandFilter": "AllTribes"}
    async with session.get(url, params=params) as resp:
        resp.raise_for_status()
        data = await resp.json()
        logger.info("EPA API returned %d Tribe records", len(data))
        return data
```

### Census CD119-AIANNH File Parser (CONG-01)
```python
# Source: Census relationship file format -- verified via direct download 2026-02-10
# File: tab20_cd11920_aiannh20_natl.txt (pipe-delimited, 17 columns, 178KB)
import csv
from collections import defaultdict

FEDERAL_CLASSFP = {"D1", "D2", "D3", "D5", "D8", "D6", "E1"}

FIPS_TO_STATE = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA",
    "08": "CO", "09": "CT", "10": "DE", "11": "DC", "12": "FL",
    "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN",
    "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME",
    "24": "MD", "25": "MA", "26": "MI", "27": "MN", "28": "MS",
    "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
    "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND",
    "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI",
    "45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT",
    "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI",
    "56": "WY",
}

def parse_cd119_aiannh(filepath: str) -> dict[str, list[dict]]:
    """Parse Census CD119-AIANNH relationship file into tribe-district mapping.

    Returns dict keyed by AIANNH GEOID -> list of district records.
    """
    tribe_districts = defaultdict(list)

    with open(filepath, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="|")
        for row in reader:
            if row["CLASSFP_AIANNH_20"] not in FEDERAL_CLASSFP:
                continue

            cd_geoid = row["GEOID_CD119_20"]
            state_fips = cd_geoid[:2]
            district_num = cd_geoid[2:]
            state_abbr = FIPS_TO_STATE.get(state_fips, state_fips)

            if district_num == "00":
                district_label = f"{state_abbr}-AL"
            else:
                district_label = f"{state_abbr}-{district_num.zfill(2)}"

            aiannh_geoid = row["GEOID_AIANNH_20"]
            overlap_land = int(row["AREALAND_PART"])
            total_land = int(row["AREALAND_AIANNH_20"])

            tribe_districts[aiannh_geoid].append({
                "district": district_label,
                "state": state_abbr,
                "aiannh_name": row["NAMELSAD_AIANNH_20"],
                "classfp": row["CLASSFP_AIANNH_20"],
                "overlap_pct": round(overlap_land / total_land * 100, 1) if total_land > 0 else 0,
            })
    return dict(tribe_districts)
```

### Congress.gov API: Fetch 119th Members (CONG-02)
```python
# Source: Congress.gov API v3 -- verified from official GitHub docs
# Auth: X-Api-Key header (existing pattern in src/scrapers/congress_gov.py line 49)
# Rate limit: 5,000 req/hr; pagination max 250 per page
async def fetch_119th_members(session: aiohttp.ClientSession, api_key: str) -> list[dict]:
    """Fetch all 119th Congress members (3 paginated calls)."""
    all_members = []
    headers = {"X-Api-Key": api_key}
    for offset in [0, 250, 500]:
        url = (
            f"https://api.congress.gov/v3/member/congress/119"
            f"?limit=250&offset={offset}&currentMember=true"
        )
        async with session.get(url, headers=headers) as resp:
            resp.raise_for_status()
            data = await resp.json()
            all_members.extend(data.get("members", []))
    logger.info("Fetched %d members of 119th Congress", len(all_members))
    return all_members
```

### State-to-Ecoregion Lookup (REG-02)
```python
# Source: Custom NCA5-derived 7-region scheme (Team 4 research)
# No external data files needed -- static lookup
STATE_TO_ECOREGION = {
    "AK": "alaska",
    "WA": "pacific_northwest", "OR": "pacific_northwest",
    "AZ": "southwest", "NM": "southwest", "NV": "southwest",
    "UT": "southwest", "CA": "southwest",
    "CO": "mountain_west", "MT": "mountain_west", "WY": "mountain_west",
    "ID": "mountain_west", "ND": "mountain_west", "SD": "mountain_west",
    "NE": "mountain_west",
    "OK": "great_plains_south", "TX": "great_plains_south",
    "KS": "great_plains_south", "AR": "great_plains_south",
    "LA": "great_plains_south", "IA": "great_plains_south",
    "FL": "southeast", "NC": "southeast", "SC": "southeast",
    "VA": "southeast", "GA": "southeast", "AL": "southeast",
    "MS": "southeast", "TN": "southeast", "KY": "southeast",
    "WV": "southeast",
    "CT": "northeast_midwest", "ME": "northeast_midwest",
    "MA": "northeast_midwest", "NY": "northeast_midwest",
    "MN": "northeast_midwest", "WI": "northeast_midwest",
    "MI": "northeast_midwest", "NH": "northeast_midwest",
    "NJ": "northeast_midwest", "PA": "northeast_midwest",
    "RI": "northeast_midwest", "VT": "northeast_midwest",
    "DE": "northeast_midwest", "MD": "northeast_midwest",
    "IL": "northeast_midwest", "IN": "northeast_midwest",
    "OH": "northeast_midwest", "MO": "northeast_midwest",
}

def get_tribe_ecoregions(tribe_states: list[str]) -> list[str]:
    """Return all ecoregions for a Tribe's states, deduplicated and sorted."""
    return sorted(set(
        STATE_TO_ECOREGION[s] for s in tribe_states if s in STATE_TO_ECOREGION
    ))
```

### TribePacketContext Dataclass (REG-03)
```python
# Source: Existing schema.py pattern + CONTEXT.md field requirements
from dataclasses import dataclass, field

@dataclass
class TribePacketContext:
    """Aggregated context for generating a single Tribe's advocacy packet.

    Assembled by PacketOrchestrator from registry, congressional cache,
    and (in later phases) award data and hazard profiles.
    """
    # Identity (REG-01, REG-03)
    tribe_id: str
    tribe_name: str
    states: list[str] = field(default_factory=list)
    ecoregions: list[str] = field(default_factory=list)

    # Congressional (CONG-01, CONG-02)
    districts: list[dict] = field(default_factory=list)
    senators: list[dict] = field(default_factory=list)
    representatives: list[dict] = field(default_factory=list)

    # Stubs for Phase 6+
    awards: list[dict] = field(default_factory=list)
    hazard_profile: dict = field(default_factory=dict)

    # Metadata
    generated_at: str = ""
    congress_session: str = ""
```

### PacketOrchestrator Skeleton
```python
# Source: Existing ReportGenerator pattern in src/reports/generator.py
class PacketOrchestrator:
    """Orchestrates Tribe-specific advocacy packet generation.

    Phase 5: resolves Tribe, displays delegation (stub output).
    Phase 7: generates DOCX packets.
    """

    def __init__(self, config: dict, programs: list[dict]):
        self.config = config
        self.programs = {p["id"]: p for p in programs}
        self.registry = TribalRegistry(config)
        self.congress = CongressionalMapper(config)

    def run_single_tribe(self, tribe_name: str) -> None:
        tribe = self.registry.resolve(tribe_name)
        if tribe is None:
            suggestions = self.registry.fuzzy_search(tribe_name, limit=5)
            print(f"Tribe not found: {tribe_name}")
            if suggestions:
                print("Did you mean:")
                for s in suggestions:
                    print(f"  - {s['name']} (score: {s['score']})")
            sys.exit(1)

        if isinstance(tribe, list):
            # Ambiguous: multiple substring matches
            print(f"Multiple Tribes match '{tribe_name}':")
            best = tribe[0]  # Auto-select best
            print(f"  Selected: {best['name']}")
            for alt in tribe[1:]:
                print(f"  Also matched: {alt['name']}")
            tribe = best

        context = self._build_context(tribe)
        self._display_tribe_info(context)

    def run_all_tribes(self) -> None:
        tribes = self.registry.get_all()
        for i, tribe in enumerate(tribes, 1):
            print(f"[{i}/{len(tribes)}] {tribe['name']}...")
            context = self._build_context(tribe)
            # Phase 7+: self._generate_docx(context)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| CRS R48107 PDF (118th Congress) | Census CD119-AIANNH relationship file (119th Congress) | Identified in this research | Machine-readable, correct Congress, includes area overlap |
| BIA code as primary key | EPA Internal ID as primary key | CONTEXT.md override needed | 40% of Tribes (Alaska) now have valid keys |
| Geospatial ecoregion join (shapefiles) | State-based lookup dict | Design decision | Eliminates GDAL dependency entirely |
| difflib fuzzy matching | rapidfuzz C++ implementation | Industry standard since ~2022 | 10x+ faster; needed for Phase 6 award matching anyway |
| Congress.gov API for committee rosters | unitedstates/congress-legislators YAML | API never provided this; YAML is canonical | Two-source strategy is the only viable approach |

**Deprecated/outdated:**
- CRS R48107 for 119th Congress mapping: Use Census CD119-AIANNH instead
- EPA Exchange Network SOAP/XML TRIBES: Replaced by REST API at cdxapi.epa.gov
- `datetime.utcnow()`: Deprecated in Python 3.12; use `datetime.now(timezone.utc)`

## Key Decisions

| Decision | Chosen Approach | Rationale |
|----------|----------------|-----------|
| **Primary key** | `epa_{epaTribalInternalId}` | 40% of Tribes lack BIA codes. EPA ID is universal, stable, sequential. **Overrides CONTEXT.md** which says "BIA code." |
| **District mapping** | Census CD119-AIANNH file | R48107 is 118th Congress. Census is 119th, machine-readable, includes overlap areas. |
| **Committee data** | Congress.gov API + unitedstates YAML | API lacks committee membership endpoint. Two-source cross-referenced by bioguideId. |
| **Ecoregion method** | State-based lookup, no geospatial | Eliminates GDAL/geopandas. State-level precision sufficient for advocacy. |
| **7-region scheme** | Custom NCA5-derived | No standard 7-region scheme exists. Alaska, Pacific NW, Southwest, Mountain West, Great Plains & South, Southeast, NE & Midwest. |
| **Graph integration** | Define dataclasses now, defer builder.py | ROADMAP says optional. PacketOrchestrator works from JSON files directly. |
| **DOCX data format** | Pre-formatted strings in cache | `formatted_name` ("Sen. Jane Doe (R-AZ)"), `district_label` ("AZ-01") ready for Phase 7. |
| **Module location** | `src/packets/` package | Parallel to existing `src/scrapers/`, `src/analysis/`. Clear functional domain. |
| **Fuzzy matching lib** | rapidfuzz 3.14.x | Same lib Phase 6 needs. C++ performance. Single dependency for both phases. |
| **Build scripts** | `scripts/` directory | One-time API fetchers are tools, not runtime modules. Creates `scripts/` (new directory). |
| **Config location** | `config/scanner_config.json` `packets` section | Follows existing pattern of single config file with nested sections. |

## Data Sources

| Source | URL | Format | Auth | Verified | Use |
|--------|-----|--------|------|----------|-----|
| EPA Tribes Names Service | `cdxapi.epa.gov/oms-tribes-rest-services/api/v1/tribeDetails?tribalBandFilter=AllTribes` | JSON | None | Live 2026-02-10 | REG-01: 575 Tribes |
| EPA Tribe Entity Mapping XLSX | `epa.gov/system/files/documents/2025-01/tribe_entity_mapping_2024-12-11.xlsx` | XLSX | None | Referenced | Fallback for REG-01 |
| BIA Tribal Leaders Directory | `bia.gov/tribal-leaders-csv` | CSV | None | Referenced | Lat/lon enrichment |
| Census CD119-AIANNH | `www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/tab20_cd11920_aiannh20_natl.txt` | Pipe-delimited | None | Verified 2026-02-10 | CONG-01: Districts |
| Congress.gov API v3 | `api.congress.gov/v3/member/congress/119` | JSON | X-Api-Key header | Docs verified | CONG-02: Members |
| unitedstates/congress-legislators | `github.com/unitedstates/congress-legislators` | YAML | None | Verified 2026-02-10 | CONG-02: Committees |
| NCA5 Regions | `nca2023.globalchange.gov/regions/` | Reference | None | Verified | REG-02: Ecoregion design |

## Open Questions

Things that couldn't be fully resolved:

1. **BIA Code Override Approval**
   - What we know: CONTEXT.md says "Primary key: BIA code." ~230 Alaska Natives have code "TBD." EPA Internal ID is viable.
   - What's unclear: Whether the user formally approves this override.
   - Recommendation: Proceed with `epa_{id}` as primary key, store BIA code as secondary field. Flag in plan as CONTEXT.md deviation.

2. **AIANNH-to-Tribe Linkage Coverage**
   - What we know: Census has 620+ AIANNH entities; EPA has ~574 Tribes. Names differ significantly. Estimated ~90% automatable.
   - What's unclear: Exact number of Tribes that will need manual alias table entries.
   - Recommendation: Build automated matching first, then curate remaining mismatches. Budget 50-60 manual entries in `aiannh_tribe_crosswalk.json`.

3. **Build Script Location**
   - What we know: No `scripts/` directory exists. Build scripts are one-time tools, not runtime modules.
   - What's unclear: Whether `scripts/` or `src/packets/` is preferred.
   - Recommendation: Create `scripts/` directory. Build scripts call APIs and write data files; they are not part of the runtime packet generation path.

4. **Geographic Coordinates for Map Generation**
   - What we know: EPA API lacks lat/lon. BIA Tribal Leaders Directory CSV has coordinates. Phase 7 needs coordinates for district map images.
   - What's unclear: Whether to fetch coordinates in Phase 5 or defer to Phase 6.
   - Recommendation: Include `location` field in registry schema as optional. Populate from BIA CSV during registry build if available. Not blocking for Phase 5 success criteria.

5. **Lumbee Tribe EPA Update Timeline**
   - What we know: Lumbee added to Federal Register 2026-01-30. EPA updates "at least annually."
   - What's unclear: When EPA will add Lumbee to their Tribes Names Service.
   - Recommendation: Log warning, skip gracefully. Re-run registry build when EPA updates.

6. **Congress.gov API Key Provisioning**
   - What we know: Existing scraper uses `CONGRESS_API_KEY` env var. Same key works for member endpoints.
   - What's unclear: Whether the existing key has sufficient rate limit headroom for 541 detail fetches during cache build.
   - Recommendation: Use existing key. Budget ~554 API calls total (well within 5,000/hr limit). Add 0.3s inter-request delay (existing pattern).

## Sources

### Primary (HIGH confidence)
- EPA Tribes Names Service API -- live queries verified 2026-02-10, returned valid data for Navajo, Cherokee, Alaska entities
- Census CD119-AIANNH relationship file -- downloaded and verified column structure 2026-02-10
- Congress.gov API documentation -- [MemberEndpoint.md](https://github.com/LibraryOfCongress/api.congress.gov/blob/main/Documentation/MemberEndpoint.md), [CommitteeEndpoint.md](https://github.com/LibraryOfCongress/api.congress.gov/blob/main/Documentation/CommitteeEndpoint.md)
- [unitedstates/congress-legislators](https://github.com/unitedstates/congress-legislators) -- committee-membership-current.yaml verified for 119th Congress
- Existing codebase analysis -- src/main.py, src/graph/schema.py, src/scrapers/congress_gov.py, src/reports/generator.py
- [RapidFuzz 3.14.3](https://rapidfuzz.github.io/RapidFuzz/) -- latest stable version verified on PyPI
- [python-docx 1.2.0](https://python-docx.readthedocs.io/) -- latest stable version verified on PyPI
- [PyYAML 6.0.3](https://pypi.org/project/PyYAML/) -- latest stable version verified on PyPI

### Secondary (MEDIUM confidence)
- NCA5 Chapter 16: Tribes and Indigenous Peoples -- ecoregion scheme design basis
- [Congress.gov Senate Indian Affairs](https://www.congress.gov/committee/senate-indian-affairs/slia00) -- system code verification
- EPA Tribe Entity Mapping Spreadsheet -- referenced but XLSX not directly parsed

### Tertiary (LOW confidence)
- BIA Tribal Leaders Directory CSV field list -- column names from documentation, not directly downloaded
- CRS IR10001 (119th Congress tribal lands report) -- referenced in CRS documentation but could not access
- AIANNH-to-Tribe matching coverage estimate (~90% automated) -- based on known naming conventions, not empirically tested

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries verified on PyPI with current versions, existing codebase patterns documented
- Architecture: HIGH -- derived from direct source code analysis of existing modules + official API documentation
- Data sources: HIGH -- EPA API and Census file verified live; Congress.gov docs verified from official GitHub
- Ecoregion scheme: MEDIUM -- custom 7-region grouping is a judgment call; aligns with NCA5 and CONTEXT.md examples
- AIANNH linkage: MEDIUM -- approach is sound but coverage estimate is untested
- Pitfalls: HIGH -- all 8 pitfalls verified against live data or official documentation

**Research date:** 2026-02-10
**Valid until:** 2026-03-12 (30 days -- data sources are stable; congressional data fixed for 119th Congress session)
**Research method:** 6-agent parallel swarm (Pass 1) + integration synthesis (Pass 2) + live API verification (Pass 3)
