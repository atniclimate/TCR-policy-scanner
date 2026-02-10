# Architecture Patterns: Tribe-Specific Advocacy Packet Generation

**Domain:** Tribal Climate Resilience -- per-Tribe DOCX packet generation
**Researched:** 2026-02-10
**Overall confidence:** HIGH (architecture grounded in thorough reading of existing codebase)

---

## 1. Existing Architecture Summary

The current pipeline is a synchronous DAG with async ingest:

```
CLI (main.py)
  |
  v
Ingest (4 async scrapers) --> Normalize
  |
  v
Analysis (RelevanceScorer, ChangeDetector)
  |
  v
Graph Construction (GraphBuilder -> KnowledgeGraph)
  |
  v
Monitors (5) --> Decision Engine
  |
  v
Reporting (ReportGenerator -> Markdown + JSON)
```

**Key patterns observed:**
- Config-driven: `scanner_config.json` is the single configuration source
- Data files in `data/`: `program_inventory.json`, `graph_schema.json`, `policy_tracking.json`
- Outputs in `outputs/`: `LATEST-BRIEFING.md`, `LATEST-RESULTS.json`, `LATEST-GRAPH.json`
- Atomic writes everywhere (tmp + replace pattern)
- `BaseScraper` provides retry, backoff, rate-limit handling
- `BaseMonitor` provides uniform check() interface
- `GraphBuilder` does static seeding (from schema) + dynamic enrichment (from scrape)
- Node types are dataclasses in `src/graph/schema.py`
- Programs keyed by `id` string (e.g., `"bia_tcr"`) across the entire system

## 2. Recommended Architecture for Packet Generation

### 2.1 Core Design Decision: Separate Command, Not Daily Pipeline Stage

**Recommendation:** Packet generation runs as a **separate CLI command** (`--prep-packets`), NOT as part of the daily scan pipeline.

**Rationale:**
1. **Different cadence.** Daily scans detect changes in 14-day windows. Packets are generated ad-hoc before Hill visits or quarterly updates. Running 574 DOCX generations on every scan wastes time and I/O.
2. **Different data dependencies.** Packets need the *latest* graph + monitor output but also need Tribal registry, congressional mapping, hazard profiles, and USASpending award data -- some of which are expensive to refresh (geocoding, API calls).
3. **Existing pattern.** The codebase already has `--report-only` and `--graph-only` modes that re-use cached pipeline output. Packets follow this pattern: consume cached outputs, produce new output.
4. **Selective generation.** Users will often need packets for a single Tribe or subset, not all 574. A separate command supports `--tribe TRIBE_ID` and `--all-tribes` flags cleanly.

### 2.2 Module Layout

New modules organized under two new source packages plus extensions to existing modules:

```
src/
  packets/                    # NEW PACKAGE: Packet generation
    __init__.py               # PacketOrchestrator (top-level entry point)
    tribal_registry.py        # TribeRegistry class: load/query 574 Tribes
    congressional.py          # CongressionalMapper: district -> delegation
    hazard_profile.py         # HazardProfiler: NRI + EJScreen + USFS + NOAA
    award_matcher.py          # AwardMatcher: fuzzy USASpending -> Tribe matching
    economic_impact.py        # EconomicImpact: BEA multipliers + BCR + avoided cost
    docx_builder.py           # DocxBuilder: python-docx programmatic construction
    overview_builder.py       # OverviewBuilder: shared strategic overview document

  scrapers/
    usaspending.py            # MODIFIED: add per-recipient Tribal query method

  graph/
    schema.py                 # MODIFIED: add TribeNode, HazardNode, DelegationNode

data/
  tribal_registry.json        # NEW: 574 Tribes with location, state, ecoregion, BIA code
  tribal_name_aliases.json    # NEW: USASpending name -> canonical name mapping
  congressional_map.json      # NEW: state/district -> senators, reps, committees
  hazard_profiles/            # NEW DIRECTORY: cached per-Tribe hazard profiles
    {tribe_id}.json           # Per-Tribe NRI + EJScreen + wildfire + flood data
  economic_multipliers.json   # NEW: BEA RIMS II county-level multiplier table
  docx_templates/             # NEW DIRECTORY: DOCX style reference files
    packet_styles.docx        # Reference doc for python-docx styling

config/
  scanner_config.json         # MODIFIED: add "packets" configuration section

outputs/
  packets/                    # NEW DIRECTORY: generated packets
    tribes/                   # Per-Tribe subdirectory
      {tribe_id}.docx         # Individual Tribe packets
    STRATEGIC-OVERVIEW.docx   # Shared overview document
    LATEST-PACKET-RUN.json    # Metadata from last generation run
```

### 2.3 CLI Interface Design

Extend `src/main.py` argument parser:

```
python -m src.main --prep-packets                     # Generate all 574 Tribe packets
python -m src.main --prep-packets --tribe cherokee_nation  # Single Tribe
python -m src.main --prep-packets --tribe cherokee_nation --tribe navajo_nation  # Multiple
python -m src.main --prep-packets --overview-only     # Only regenerate strategic overview
python -m src.main --prep-packets --refresh-data      # Force re-fetch hazard/award data
python -m src.main --prep-packets --dry-run           # Show what would be generated
```

**Why extend main.py instead of new CLI?**
- Consistent UX with existing `--report-only`, `--graph-only`
- Shares config loading, logging setup, program inventory loading
- Access to cached graph/monitor data from latest scan

### 2.4 New Configuration Section

Add to `scanner_config.json`:

```json
{
  "packets": {
    "tribal_registry_path": "data/tribal_registry.json",
    "alias_map_path": "data/tribal_name_aliases.json",
    "congressional_map_path": "data/congressional_map.json",
    "hazard_cache_dir": "data/hazard_profiles",
    "multiplier_path": "data/economic_multipliers.json",
    "style_reference_path": "data/docx_templates/packet_styles.docx",
    "output_dir": "outputs/packets",
    "hazard_sources": {
      "nri": {
        "csv_path": "data/nri_tribal.csv",
        "refresh_days": 90
      },
      "ejscreen": {
        "csv_path": "data/ejscreen_tribal.csv",
        "refresh_days": 90
      }
    },
    "award_matching": {
      "fuzzy_threshold": 85,
      "fiscal_years": ["FY25", "FY26"]
    },
    "economic": {
      "default_multiplier": 1.8,
      "bcr_discount_rate": 0.03
    }
  }
}
```

## 3. Data Flow

### 3.1 Packet Generation Pipeline

```
                                      EXISTING (cached)
                                    +-------------------+
                                    | LATEST-GRAPH.json |
                                    | LATEST-MONITOR-   |
                                    |   DATA.json       |
                                    | program_inventory |
                                    +--------+----------+
                                             |
                         +-------------------+-------------------+
                         |                                       |
  NEW DATA LAYERS        v                                       v
  +-----------+    +------------+    +------------------+   +-----------+
  | Tribal    |--->| Award      |--->| Economic Impact  |   | Decision  |
  | Registry  |    | Matcher    |    | Calculator       |   | Engine    |
  +-----------+    +-----+------+    +--------+---------+   | Results   |
       |                 |                    |              +-----+-----+
       |    +------------+                    |                    |
       |    |                                 |                    |
       v    v                                 v                    v
  +-----------+    +------------------+  +-----------+   +-----------+
  | Congress  |    | Hazard Profiler  |  | Per-Tribe |   | Per-Tribe |
  | Mapper    |    | (NRI/EJScreen/   |  | Award $   |   | Advocacy  |
  +-----------+    |  USFS/NOAA)      |  | Summary   |   | Goal      |
       |           +--------+---------+  +-----+-----+   +-----+-----+
       |                    |                  |                |
       +--------------------+------------------+----------------+
                            |
                            v
                   +------------------+
                   | PacketOrchestrator|
                   | (per Tribe)      |
                   +--------+---------+
                            |
              +-------------+-------------+
              |                           |
              v                           v
     +----------------+        +-------------------+
     | DocxBuilder    |        | OverviewBuilder   |
     | (per-Tribe     |        | (shared strategic |
     |  574 variants) |        |  overview)        |
     +----------------+        +-------------------+
              |                           |
              v                           v
     outputs/packets/tribes/    outputs/packets/
       {tribe_id}.docx         STRATEGIC-OVERVIEW.docx
```

### 3.2 Data Flow Per Tribe

For each Tribe, the PacketOrchestrator collects a `TribePacketContext` dict containing:

```python
@dataclass
class TribePacketContext:
    """Everything the DocxBuilder needs for one Tribe's packet."""
    # Identity
    tribe_id: str
    tribe_name: str
    state: str
    bia_code: str
    ecoregion: str
    location: dict  # lat, lon, county FIPS

    # Congressional delegation
    senators: list[dict]         # name, party, committees
    house_reps: list[dict]       # name, party, district, committees
    relevant_committees: list[str]

    # Hazard profile
    hazard_profile: dict         # NRI risk rating, top hazards, EJ percentiles

    # Per-program data (keyed by program_id)
    program_awards: dict[str, list[dict]]  # USASpending awards matched to this Tribe
    program_totals: dict[str, float]       # Sum of awards per program
    economic_impact: dict[str, dict]       # Multiplied impact per program

    # From existing pipeline (program-level, shared across Tribes)
    advocacy_classifications: dict  # Decision engine output
    graph_data: dict                # Knowledge graph
    monitor_alerts: list[dict]      # Monitor output
```

### 3.3 Interaction with Existing Components

| Existing Component | How Packets Use It | Modification Needed |
|----|----|----|
| `program_inventory.json` | Programs are the unit of advocacy; each packet section maps to a program | None |
| `LATEST-GRAPH.json` | Barriers, authorities, structural asks are pulled from graph per program | None |
| `LATEST-MONITOR-DATA.json` | Monitor alerts shown per program in packet | None |
| `DecisionEngine` output | Advocacy goal classification drives packet narrative framing | None -- consumed from cached JSON |
| `USASpendingScraper` | Extended to support per-recipient queries for Tribal award matching | Add `fetch_by_recipient()` method |
| `graph/schema.py` | Add TribeNode, HazardNode, CongressionalDistrictNode types | Add 3 new dataclass types |
| `scanner_config.json` | Add `packets` configuration section | Add new config block |
| `main.py` | Add `--prep-packets` flag and packet orchestration pathway | Extend CLI and add pathway |

**Critical: No modifications to existing pipeline logic.** The packet system is a pure consumer of existing outputs. It reads cached JSON files. It does not alter how scans, scoring, graph building, monitors, or decision engine work.

## 4. Component Design Details

### 4.1 TribeRegistry (`src/packets/tribal_registry.py`)

**Purpose:** Load and query the 574 federally recognized Tribes.

**Data source:** BIA Tribal Leaders Directory CSV/Excel dataset (available at bia.gov), transformed into `data/tribal_registry.json`.

**Schema for `data/tribal_registry.json`:**
```json
{
  "metadata": {
    "source": "BIA Tribal Leaders Directory + Federal Register 89 FR 944",
    "last_updated": "2026-XX-XX",
    "tribe_count": 574
  },
  "tribes": [
    {
      "id": "cherokee_nation",
      "name": "Cherokee Nation",
      "bia_code": "CN",
      "state": "OK",
      "states": ["OK"],
      "county_fips": ["40001"],
      "lat": 35.9078,
      "lon": -94.9541,
      "ecoregion": "Central Irregular Plains",
      "census_tribal_area_fips": "1234567",
      "congressional_districts": ["OK-02"]
    }
  ]
}
```

**Class interface:**
```python
class TribeRegistry:
    def __init__(self, registry_path: Path): ...
    def get_tribe(self, tribe_id: str) -> dict | None: ...
    def get_all_tribes(self) -> list[dict]: ...
    def get_tribes_by_state(self, state: str) -> list[dict]: ...
    def search(self, query: str) -> list[dict]: ...  # fuzzy name search
```

**Build order:** Phase 1 foundation. Everything else depends on this.

### 4.2 CongressionalMapper (`src/packets/congressional.py`)

**Purpose:** Map each Tribe's geographic location to congressional delegation.

**Data sources:**
- Census TIGER/Line Shapefiles for congressional district boundaries (119th Congress)
- Congress.gov API (existing `congress_gov` source in config) for member info
- Pre-computed and cached in `data/congressional_map.json`

**Design decision: Pre-compute, not real-time.**
Congressional districts change only at redistricting (every 10 years). Member data changes at most every 2 years. Pre-compute the full mapping once, refresh manually when Congress changes.

**Schema for `data/congressional_map.json`:**
```json
{
  "metadata": {
    "congress": 119,
    "last_updated": "2026-XX-XX"
  },
  "districts": {
    "OK-02": {
      "state": "OK",
      "district": 2,
      "representative": {
        "name": "Rep Name",
        "party": "R",
        "committees": ["Natural Resources", "Appropriations"]
      }
    }
  },
  "senators": {
    "OK": [
      {
        "name": "Sen Name",
        "party": "R",
        "committees": ["Indian Affairs", "Appropriations"]
      }
    ]
  },
  "key_committees": [
    "Senate Committee on Indian Affairs",
    "House Natural Resources Subcommittee on Indian and Insular Affairs",
    "Senate Appropriations Interior Subcommittee",
    "House Appropriations Interior Subcommittee"
  ]
}
```

**Class interface:**
```python
class CongressionalMapper:
    def __init__(self, map_path: Path): ...
    def get_delegation(self, tribe: dict) -> dict: ...
    def get_relevant_committees(self, tribe: dict) -> list[str]: ...
```

**Build order:** Phase 1 or early Phase 2. Independent of hazard/award layers.

### 4.3 AwardMatcher (`src/packets/award_matcher.py`)

**Purpose:** Match USASpending award records to specific Tribes using fuzzy name matching.

**The core problem:** USASpending records list recipients by name, but Tribal names in USASpending often differ from BIA registry names. Examples:
- BIA: "Cherokee Nation" vs USASpending: "CHEROKEE NATION OF OKLAHOMA"
- BIA: "Navajo Nation" vs USASpending: "THE NAVAJO NATION"
- BIA: "Poarch Band of Creek Indians" vs USASpending: "POARCH BAND OF CREEK INDIANS INC"

**Strategy: Two-tier matching.**

1. **Alias table** (`data/tribal_name_aliases.json`): Manual curated mapping of known variant names. This catches the 80% of cases where names are known to differ.
2. **Fuzzy fallback** (rapidfuzz or thefuzz): For unmatched recipients, compute token_sort_ratio against all Tribe names. Threshold of 85 catches most remaining matches.

**Schema for `data/tribal_name_aliases.json`:**
```json
{
  "metadata": {
    "description": "Maps USASpending recipient names to canonical tribe_id",
    "last_curated": "2026-XX-XX"
  },
  "aliases": {
    "CHEROKEE NATION OF OKLAHOMA": "cherokee_nation",
    "THE NAVAJO NATION": "navajo_nation",
    "NAVAJO NATION": "navajo_nation"
  }
}
```

**Class interface:**
```python
class AwardMatcher:
    def __init__(self, registry: TribeRegistry, alias_path: Path, config: dict): ...
    def match_recipient(self, recipient_name: str) -> str | None: ...  # -> tribe_id
    def match_awards(self, awards: list[dict]) -> dict[str, list[dict]]: ...  # tribe_id -> awards
    async def fetch_tribal_awards(self, program_cfda: str) -> list[dict]: ...  # query USASpending
```

**Modification to existing `USASpendingScraper`:** Add a method to fetch ALL awards for a given CFDA (not just top 10), paginating through results. The existing scraper fetches top-10 by amount per CFDA for the daily briefing; the award matcher needs the full dataset to find per-Tribe awards.

**Build order:** Phase 2. Depends on TribeRegistry.

### 4.4 HazardProfiler (`src/packets/hazard_profile.py`)

**Purpose:** Build a per-Tribe hazard profile from multiple federal data sources.

**Data sources (all downloadable as CSV/Geodatabase -- no real-time API needed):**

| Source | Data | Format | Refresh |
|--------|------|--------|---------|
| FEMA NRI | Risk ratings for 18 hazard types by county/Census tract | CSV download from hazards.fema.gov/nri/data-resources | Quarterly |
| EPA EJScreen | Environmental justice indicators by Census block group | CSV download (community-mirrored since Feb 2025 EPA takedown) | Annual |
| USFS | Wildfire risk data (Wildfire Hazard Potential) | GeoTIFF/Shapefile | Annual |
| NOAA | Climate normals, sea level rise projections | CSV/API | Annual |

**Design decision: Pre-downloaded static files, not real-time API calls.**
- NRI data is 20GB+ as full geodatabase. Download the **tribal-specific** CSV subset (available directly from FEMA at hazards.fema.gov/nri/data-resources as "tribal datasets").
- EJScreen: Download CSV, join by Census block group FIPS to Tribal area FIPS.
- Cache per-Tribe hazard profiles in `data/hazard_profiles/{tribe_id}.json`.

**Per-Tribe hazard profile schema:**
```json
{
  "tribe_id": "cherokee_nation",
  "generated": "2026-XX-XX",
  "nri": {
    "overall_risk_rating": "Relatively High",
    "overall_risk_score": 24.5,
    "top_hazards": [
      {"type": "Tornado", "risk_score": 32.1, "eal": 145000},
      {"type": "Hail", "risk_score": 28.3, "eal": 89000},
      {"type": "Flooding", "risk_score": 22.7, "eal": 210000}
    ],
    "expected_annual_loss": 890000,
    "social_vulnerability": "Relatively High",
    "community_resilience": "Relatively Low"
  },
  "ejscreen": {
    "pm25_percentile": 67,
    "ozone_percentile": 72,
    "wastewater_percentile": 45,
    "superfund_percentile": 12,
    "ej_index": 78
  },
  "wildfire": {
    "whp_rating": "High",
    "acres_at_risk": 45000
  },
  "flood": {
    "fema_zone": "AE",
    "percent_in_floodplain": 18
  }
}
```

**Class interface:**
```python
class HazardProfiler:
    def __init__(self, config: dict, registry: TribeRegistry): ...
    def get_profile(self, tribe_id: str) -> dict: ...  # Load from cache
    def refresh_profile(self, tribe_id: str) -> dict: ...  # Rebuild from source data
    def refresh_all(self) -> None: ...  # Rebuild all 574 profiles
    def get_top_hazards(self, tribe_id: str, n: int = 3) -> list[dict]: ...
```

**Build order:** Phase 2. Depends on TribeRegistry. Independent of award matching.

### 4.5 EconomicImpact (`src/packets/economic_impact.py`)

**Purpose:** Transform raw award dollar amounts into district-level economic impact framing.

**Calculation layers:**

1. **BEA RIMS II Multiplier:** Award dollars x regional output multiplier = total economic activity.
   - RIMS II multipliers cost $500/region from BEA. For a no-cost approach, use published average multipliers by sector (government grants to tribal entities typically 1.5-2.2x).
   - Store county-level multipliers in `data/economic_multipliers.json`.

2. **FEMA Benefit-Cost Ratio (BCR):** For hazard mitigation programs, express investment as avoided future losses.
   - Formula: `BCR = (hazard_EAL * useful_life * discount_factor) / project_cost`
   - Uses NRI Expected Annual Loss data from HazardProfiler.

3. **Avoided Cost Narrative:** Generate human-readable framing text.
   - Example: "The $2.3M BIA TCR investment in Cherokee Nation generated an estimated $4.1M in total economic activity in OK-02, supporting approximately 28 jobs."

**Class interface:**
```python
class EconomicImpact:
    def __init__(self, config: dict, hazard_profiler: HazardProfiler): ...
    def calculate_impact(self, tribe_id: str, program_id: str, award_amount: float) -> dict: ...
    def format_narrative(self, impact: dict, delegation: dict) -> str: ...
```

**Output per program per Tribe:**
```json
{
  "program_id": "bia_tcr",
  "tribe_id": "cherokee_nation",
  "award_total": 2300000,
  "multiplier": 1.8,
  "total_economic_activity": 4140000,
  "estimated_jobs": 28,
  "bcr": 3.2,
  "narrative": "The $2.3M BIA TCR investment...",
  "district": "OK-02"
}
```

**Build order:** Phase 3. Depends on AwardMatcher + HazardProfiler.

### 4.6 DocxBuilder (`src/packets/docx_builder.py`)

**Purpose:** Programmatically construct per-Tribe advocacy packets using python-docx.

**Design decision: Programmatic construction, NOT template-based.**
- Template approaches (docxtpl/jinja2) work well for form-fill documents but break down when document structure varies per Tribe (different number of programs, different hazards, different delegation).
- Programmatic python-docx construction with a style reference document gives full control over variable-structure documents.
- The style reference doc (`data/docx_templates/packet_styles.docx`) defines paragraph styles, table styles, headers/footers, and fonts. python-docx applies these styles without the template needing content.

**Document sections per Tribe packet:**

```
1. Cover Page
   - Tribe name, date, "Prepared for [Tribe]"

2. Executive Summary
   - Tribe location, ecoregion, congressional district
   - Key hazards (from HazardProfiler)
   - Total federal investment (from AwardMatcher)
   - Advocacy goal summary (from DecisionEngine)

3. Congressional Delegation
   - Senators (name, party, relevant committees)
   - House Representative(s) (name, party, district)
   - Committee memberships relevant to programs

4. Per-Program Sections (one per tracked program, sorted by advocacy goal priority)
   4a. Program Status
       - Name, agency, CI status, advocacy goal classification
       - Current funding level, authority basis
   4b. This Tribe's Awards
       - Table of USASpending awards for this program + Tribe
       - Total dollars, fiscal year
   4c. Economic Impact
       - Multiplied economic activity
       - Jobs supported
       - Benefit-cost ratio (for mitigation programs)
   4d. Advocacy Framing
       - Barrier from knowledge graph
       - Structural ask from graph
       - Specific talking point for delegation

5. Hazard Profile
   - Top hazards from NRI
   - EJ indicators from EJScreen
   - Wildfire/flood risk summary

6. Five Structural Asks (shared across Tribes, contextualized)
   - Each ask with Tribe-specific evidence

7. Appendix
   - Data sources, methodology notes, contact info
```

**Class interface:**
```python
class DocxBuilder:
    def __init__(self, style_ref_path: Path): ...
    def build_packet(self, context: TribePacketContext) -> Document: ...
    def save(self, doc: Document, output_path: Path) -> None: ...
```

**Build order:** Phase 3-4. Depends on all data layers being ready.

### 4.7 OverviewBuilder (`src/packets/overview_builder.py`)

**Purpose:** Generate the shared Strategic Overview document (not per-Tribe).

**Content:**
- Aggregate statistics across all 574 Tribes
- Program landscape summary (from existing pipeline)
- Top hazards by ecoregion
- Total federal investment summary
- Congressional committee focus areas
- Five Structural Asks with aggregate evidence

**Build order:** Phase 4. Final assembly after per-Tribe data is all computed.

### 4.8 PacketOrchestrator (`src/packets/__init__.py`)

**Purpose:** Top-level coordination of the packet generation pipeline.

```python
class PacketOrchestrator:
    def __init__(self, config: dict, programs: list[dict]): ...

    def generate_all(self, refresh_data: bool = False) -> dict:
        """Generate packets for all 574 Tribes + strategic overview."""
        ...

    def generate_for_tribes(self, tribe_ids: list[str],
                            refresh_data: bool = False) -> dict:
        """Generate packets for specific Tribes."""
        ...

    def generate_overview_only(self) -> Path:
        """Regenerate only the strategic overview."""
        ...
```

**Orchestration steps:**
```python
def generate_all(self, refresh_data=False):
    # 1. Load existing pipeline outputs (cached)
    graph_data = load_json("outputs/LATEST-GRAPH.json")
    monitor_data = load_json("outputs/LATEST-MONITOR-DATA.json")
    programs = load_json("data/program_inventory.json")

    # 2. Initialize data layers
    registry = TribeRegistry(config["packets"]["tribal_registry_path"])
    congress = CongressionalMapper(config["packets"]["congressional_map_path"])
    hazards = HazardProfiler(config, registry)
    matcher = AwardMatcher(registry, config["packets"]["alias_map_path"], config)
    economics = EconomicImpact(config, hazards)

    # 3. Fetch/refresh award data if needed
    if refresh_data:
        awards = await matcher.fetch_all_tribal_awards()
    else:
        awards = matcher.load_cached_awards()

    # 4. Build per-Tribe contexts
    contexts = []
    for tribe in registry.get_all_tribes():
        ctx = self._build_context(
            tribe, congress, hazards, matcher, economics,
            graph_data, monitor_data, programs
        )
        contexts.append(ctx)

    # 5. Generate DOCX files
    builder = DocxBuilder(config["packets"]["style_reference_path"])
    for ctx in contexts:
        doc = builder.build_packet(ctx)
        builder.save(doc, output_dir / f"{ctx.tribe_id}.docx")

    # 6. Generate overview
    overview = OverviewBuilder(config)
    overview.build(contexts, graph_data, monitor_data)

    return {"tribes_generated": len(contexts), "output_dir": str(output_dir)}
```

## 5. New Graph Schema Additions

Add to `src/graph/schema.py`:

```python
@dataclass
class TribeNode:
    """Federally recognized Tribe."""
    id: str
    name: str
    state: str
    bia_code: str = ""
    ecoregion: str = ""
    county_fips: str = ""

@dataclass
class HazardNode:
    """Climate/environmental hazard affecting a Tribe."""
    id: str
    hazard_type: str       # e.g. "Tornado", "Flooding", "Wildfire"
    risk_score: float = 0.0
    expected_annual_loss: float = 0.0

@dataclass
class CongressionalDistrictNode:
    """Congressional district for delegation mapping."""
    id: str                # e.g. "OK-02"
    state: str
    district: int
    representative: str = ""
    party: str = ""
```

**New edge types:**
```
LOCATED_IN       (TribeNode -> CongressionalDistrictNode)
EXPOSED_TO       (TribeNode -> HazardNode)
AWARDED_TO       (ProgramNode -> TribeNode) via ObligationNode
REPRESENTED_BY   (TribeNode -> CongressionalDistrictNode)
```

**Note:** These graph extensions are optional for Phase 1 packet generation. The PacketOrchestrator can work purely from JSON data files without integrating into the existing KnowledgeGraph. Graph integration can be deferred to a later phase if desired.

## 6. Anti-Patterns to Avoid

### Anti-Pattern 1: Coupling Packet Generation into the Daily Pipeline

**What:** Adding packet generation as a stage after Reporting in the daily scan pipeline.
**Why bad:** 574 DOCX files take significant I/O. Daily scan would slow from seconds to minutes. Most runs do not need packets.
**Instead:** Separate `--prep-packets` command that consumes cached pipeline output.

### Anti-Pattern 2: Real-Time API Calls During DOCX Generation

**What:** Calling USASpending API, NRI API, or Congress.gov API during the docx build loop.
**Why bad:** 574 Tribes x multiple API calls = thousands of requests. Rate limits, failures, and 10+ minute generation times.
**Instead:** Pre-fetch and cache all data layers. DOCX generation reads only from local JSON files.

### Anti-Pattern 3: Template-per-Tribe Approach

**What:** Creating 574 DOCX templates with Tribe-specific placeholders.
**Why bad:** Unmaintainable. Any formatting change requires updating 574 files.
**Instead:** Single style reference doc + programmatic python-docx construction. One code change updates all 574 packets.

### Anti-Pattern 4: Monolithic DocxBuilder

**What:** Single 2000-line function that builds the entire DOCX document.
**Why bad:** Untestable, hard to maintain, impossible to parallelize.
**Instead:** DocxBuilder delegates to section-builder methods. Each section is independently testable.

### Anti-Pattern 5: Storing 574 Hazard Profiles in Memory

**What:** Loading all NRI + EJScreen data for all Tribes simultaneously.
**Why bad:** NRI data is large. Loading all 574 profiles at once could consume significant memory.
**Instead:** HazardProfiler loads profiles on-demand from per-Tribe JSON cache files. Process Tribes sequentially or in small batches.

## 7. Build Order (Dependency-Driven)

The dependency graph dictates the build order:

```
Phase 1: Foundation (no external API dependencies)
  |-- tribal_registry.py + data/tribal_registry.json
  |-- congressional.py + data/congressional_map.json
  |-- CLI extension in main.py (--prep-packets flag)
  |-- PacketOrchestrator skeleton
  |-- graph/schema.py additions (TribeNode, etc.)

Phase 2: Data Acquisition Layers
  |-- award_matcher.py + tribal_name_aliases.json
  |     |-- Modify USASpendingScraper for paginated Tribal queries
  |     \-- Fuzzy matching (rapidfuzz dependency)
  |-- hazard_profile.py + data/hazard_profiles/
  |     |-- NRI CSV ingestion
  |     |-- EJScreen CSV ingestion
  |     \-- Wildfire/flood data ingestion

Phase 3: Computation + Generation
  |-- economic_impact.py + economic_multipliers.json
  |     \-- Depends on Phase 2 (awards + hazards)
  |-- docx_builder.py + data/docx_templates/packet_styles.docx
  |     \-- python-docx dependency
  |-- Per-section builder methods

Phase 4: Assembly + Polish
  |-- overview_builder.py
  |-- Full PacketOrchestrator integration
  |-- End-to-end testing (single Tribe, then all 574)
  |-- Output validation
```

**Rationale for this ordering:**
1. **Phase 1** establishes the skeleton with no external dependencies. You can test the full pipeline flow with mock data.
2. **Phase 2** adds the two hardest data acquisition challenges (fuzzy name matching and multi-source hazard profiling) while Phase 1 provides the test harness.
3. **Phase 3** combines Phase 2 data into computed outputs and builds the actual DOCX. By this point, all data is flowing.
4. **Phase 4** is assembly and the strategic overview, which is a simpler aggregation of per-Tribe data.

## 8. Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| DOCX library | python-docx (programmatic) | Faster than COM automation, no Word dependency, supports style references |
| Template vs programmatic | Programmatic with style reference | Variable document structure (different programs/hazards per Tribe) |
| Fuzzy matching library | rapidfuzz | C-extension, 10x faster than thefuzz/fuzzywuzzy for 574 Tribes x thousands of recipients |
| NRI data format | Pre-downloaded CSV (tribal subset) | 90-day refresh cycle, avoids real-time API overhead |
| Congressional data | Pre-computed static JSON | Changes at most every 2 years, no API needed at generation time |
| Hazard profile caching | Per-Tribe JSON files in data/hazard_profiles/ | On-demand loading, independently refreshable |
| BEA multipliers | Static lookup table with published averages | RIMS II costs $500/region; published sector averages are sufficient for advocacy framing |
| Packet output format | Per-Tribe DOCX in outputs/packets/tribes/ | Matches user need for individual Tribe packets for Hill visits |

## 9. Scalability Considerations

| Concern | At 1 Tribe | At 50 Tribes | At 574 Tribes |
|---------|------------|--------------|---------------|
| Generation time | <1 second | ~10 seconds | ~2 minutes |
| Disk space (packets) | ~200KB | ~10MB | ~115MB |
| Memory (peak) | ~50MB | ~100MB | ~200MB (streaming) |
| USASpending queries | 16 (one per CFDA) | Same (shared) | Same (shared) |
| Hazard profile loads | 1 file | 50 files | 574 files (on-demand) |

**The 574-Tribe generation is bounded by DOCX file I/O, not computation.** python-docx generates files at ~100ms each for this document complexity, so 574 Tribes complete in under 2 minutes on modest hardware.

## 10. Testing Strategy

| Layer | Test Type | What to Verify |
|-------|-----------|----------------|
| TribeRegistry | Unit | Load, query, search across all 574 entries |
| CongressionalMapper | Unit | Correct delegation for known Tribe locations |
| AwardMatcher | Unit | Alias lookup, fuzzy matching, threshold behavior |
| AwardMatcher | Integration | Real USASpending API returns parseable data |
| HazardProfiler | Unit | CSV parsing, profile construction, caching |
| EconomicImpact | Unit | Multiplier arithmetic, BCR calculation, narrative generation |
| DocxBuilder | Unit | DOCX opens in Word, has correct sections, formatting |
| PacketOrchestrator | Integration | End-to-end single Tribe, end-to-end all Tribes |
| DocxBuilder | Snapshot | Generated DOCX content matches expected text for test Tribe |

## Sources

- [BIA Tribal Leaders Directory CSV/Excel Dataset](https://www.bia.gov/service/tribal-leaders-directory/tld-csvexcel-dataset)
- [Federal Register: Indian Entities Recognized by BIA](https://www.federalregister.gov/documents/2024/01/08/2024-00109/indian-entities-recognized-by-and-eligible-to-receive-services-from-the-united-states-bureau-of)
- [FEMA National Risk Index Data Resources](https://hazards.fema.gov/nri/data-resources) -- tribal datasets available as CSV/Shapefile
- [EPA EJScreen Data Download](https://screening-tools.com/epa-ejscreen) -- community-mirrored since Feb 2025
- [Census TIGERweb GeoServices REST API](https://www.census.gov/data/developers/data-sets/TIGERweb-map-service.html)
- [USASpending API Endpoints](https://api.usaspending.gov/docs/endpoints)
- [USASpending API Search Filters](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/search_filters.md)
- [BEA RIMS II Multipliers](https://www.bea.gov/resources/methodologies/RIMSII-user-guide)
- [python-docx Guide](https://www.w3resource.com/python/mastering-python-docx.php)
- [Data.gov: Federally Recognized Tribes](https://catalog.data.gov/dataset/federally-recognized-tribes)
