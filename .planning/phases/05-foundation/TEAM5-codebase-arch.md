# Team 5: Codebase Architecture & Integration Patterns

**Researched:** 2026-02-10
**Domain:** Codebase structure, CLI patterns, dataclass design, graph integration, testing
**Confidence:** HIGH (all findings derived from direct source code analysis)

---

## CLI Extension Design

### Current CLI Pattern (main.py lines 285-329)

The CLI uses flat `argparse.ArgumentParser` with top-level flags. No subcommands, no subparsers.

```python
parser = argparse.ArgumentParser(
    description="TCR Policy Scanner -- Automated policy intelligence for Tribal Climate Resilience"
)
parser.add_argument("--programs", action="store_true", help="List tracked programs with CI status")
parser.add_argument("--dry-run", action="store_true", help="Show what would be scanned")
parser.add_argument("--source", type=str, help="Scan a specific source only")
parser.add_argument("--report-only", action="store_true", help="Regenerate report from cached data")
parser.add_argument("--graph-only", action="store_true", help="Export knowledge graph from cached data")
parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
```

Dispatch is a simple if-elif chain in `main()`:
```python
if args.programs:
    list_programs(programs)
    return

# ... source validation ...

if args.dry_run:
    dry_run(config, programs, sources)
    return

run_pipeline(config, programs, sources,
             report_only=args.report_only, graph_only=args.graph_only)
```

### Recommendation: `--prep-packets` as a Top-Level Flag (Not a Subcommand)

**Rationale:** The codebase uses flat flags exclusively. Introducing `argparse.add_subparsers()` would break the existing dispatch pattern and require refactoring all current flags into a "scan" subcommand. This is unnecessary churn.

**Design:**
```python
# Add to existing parser
parser.add_argument("--prep-packets", action="store_true",
                    help="Generate Tribe-specific advocacy packets")
parser.add_argument("--tribe", type=str,
                    help="Tribe name to generate packet for (used with --prep-packets)")
parser.add_argument("--all-tribes", action="store_true",
                    help="Generate packets for all 575 Tribes (used with --prep-packets)")
```

**Dispatch pattern (insert before `run_pipeline` call):**
```python
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

**Validation rules:**
- `--prep-packets` requires either `--tribe` or `--all-tribes` (mutually exclusive not needed -- `--all-tribes` overrides `--tribe`)
- `--prep-packets` is mutually exclusive with `--programs`, `--dry-run`, `--report-only`, `--graph-only`
- `--tribe` and `--all-tribes` without `--prep-packets` should produce an error

**Important:** The existing `--source` flag accepts a string argument. Following that pattern, `--tribe` should also be a plain `type=str` argument. No multi-value args in the current codebase.

### Error Message Pattern

Existing pattern for invalid source (line 314-317):
```python
if args.source not in SCRAPERS:
    print(f"Unknown source: {args.source}")
    print(f"Available: {', '.join(SCRAPERS.keys())}")
    sys.exit(1)
```

For tribe resolution failure, follow the same pattern:
```python
if not resolved_tribe:
    print(f"Tribe not found: {args.tribe}")
    print(f"Did you mean: {', '.join(suggestions)}")
    sys.exit(1)
```

---

## Module Organization

### Current Package Structure

```
src/
    __init__.py          # empty
    main.py              # CLI + pipeline orchestrator
    analysis/
        __init__.py      # empty
        relevance.py     # RelevanceScorer
        change_detector.py
        decision_engine.py
    graph/
        __init__.py      # empty
        schema.py        # Node/Edge dataclasses
        builder.py       # GraphBuilder, KnowledgeGraph
    monitors/
        __init__.py      # MonitorAlert, BaseMonitor, MonitorRunner (non-empty)
        iija_sunset.py
        reconciliation.py
        dhs_funding.py
        tribal_consultation.py
        hot_sheets.py
    reports/
        __init__.py      # empty
        generator.py     # ReportGenerator
    scrapers/
        __init__.py      # empty
        base.py          # BaseScraper
        congress_gov.py
        federal_register.py
        grants_gov.py
        usaspending.py
```

**Pattern observations:**
- Each package is a functional domain (analysis, graph, monitors, reports, scrapers)
- `__init__.py` files are empty except `monitors/__init__.py` which contains the framework classes (MonitorAlert, BaseMonitor, MonitorRunner)
- One class per file (exception: schema.py has multiple dataclasses and helpers)
- Module-level logger: `logger = logging.getLogger(__name__)`
- Config paths as module-level constants: `CONFIG_PATH = Path("config/scanner_config.json")`

### Recommendation: `src/packets/` Package

**Create `src/packets/` as a new top-level package, parallel to existing packages:**

```
src/packets/
    __init__.py          # empty (or exports PacketOrchestrator)
    orchestrator.py      # PacketOrchestrator (main coordinator)
    context.py           # TribePacketContext dataclass
    registry.py          # TribalRegistry (loads tribal_registry.json, handles search/resolution)
    congress.py          # CongressionalMapper (loads congressional_cache.json, delegation lookups)
```

**Rationale:**
- `packets` is the functional domain (like `scrapers`, `monitors`)
- Avoids `advocacy` (too broad -- the whole app is about advocacy) and `tribes` (too narrow -- it includes congressional mapping too)
- Each module has a single clear responsibility
- Follows the one-class-per-file pattern
- `registry.py` and `congress.py` are data-loading modules, not scrapers -- they read from pre-built JSON files, not APIs

**Data files location:**
```
data/
    tribal_registry.json       # 575 Tribes (built once, manual updates)
    congressional_cache.json   # 119th Congress delegation data
```

This follows the existing `data/` convention (`program_inventory.json`, `graph_schema.json`).

### Naming Conventions

| Pattern | Examples from Codebase |
|---------|----------------------|
| File names | `snake_case.py` -- `decision_engine.py`, `change_detector.py`, `federal_register.py` |
| Class names | `PascalCase` -- `DecisionEngine`, `RelevanceScorer`, `GraphBuilder`, `MonitorRunner` |
| Dataclass names | `PascalCase` with `Node` suffix -- `ProgramNode`, `AuthorityNode`, `BarrierNode` |
| Edge type constants | `UPPER_SNAKE_CASE` strings -- `"AUTHORIZED_BY"`, `"FUNDED_BY"`, `"THREATENS"` |
| Module constants | `UPPER_SNAKE_CASE` -- `CONFIG_PATH`, `GRAPH_SCHEMA_PATH`, `MAX_RETRIES` |
| Logger init | `logger = logging.getLogger(__name__)` (per file, top-level) |
| Config loading | Function that opens JSON with `encoding="utf-8"` -- `load_config()` |

---

## Dataclass Design (TribeNode, CongressionalDistrictNode, TribePacketContext)

### Existing Node Dataclass Pattern (schema.py)

All nodes follow this pattern:
```python
@dataclass
class ProgramNode:
    """Docstring explaining what this represents."""
    id: str              # Always first field, always str
    name: str            # Human-readable name
    # Domain-specific fields follow
    agency: str
    confidence_index: float = 0.0
    fy26_status: str = ""
    priority: str = ""
    cfda: str = ""
```

**Key conventions:**
1. `id: str` is always the first field (required, no default)
2. Required fields come first, optional fields with defaults come after
3. Defaults are empty strings `""` for str fields, `0.0` for float fields
4. No `field(default_factory=...)` on node classes (only on `Edge.metadata`)
5. All fields are simple types (str, float) -- no nested objects, no lists (exception: `Edge.metadata: dict`)
6. Docstring is a one-liner describing the real-world entity

### TribeNode Design

```python
@dataclass
class TribeNode:
    """Federally recognized Tribal Nation (e.g. 'Navajo Nation')."""
    id: str                    # BIA code (primary key per CONTEXT.md decision)
    name: str                  # Official BIA name
    state: str = ""            # Primary state (or comma-separated for multi-state)
    ecoregion: str = ""        # One of 7 advocacy-relevant ecoregions
    population_category: str = ""  # If available from EPA data
```

**Notes:**
- `id` is the BIA code per CONTEXT.md decision ("Primary key: BIA code")
- Multi-ecoregion Tribes are listed under ALL applicable ecoregions per CONTEXT.md. The graph handles this via edges (LOCATED_IN), not by storing multiple values in the node field. The node's `ecoregion` field holds the primary ecoregion; additional ecoregions are represented as edges.
- Alternatively, for multi-ecoregion Tribes: skip the `ecoregion` field on the node entirely and represent ALL ecoregion associations as edges. This is cleaner for the graph model but less convenient for standalone lookups.

### CongressionalDistrictNode Design

```python
@dataclass
class CongressionalDistrictNode:
    """U.S. Congressional District (e.g. 'AZ-01' or 'AK-AL')."""
    id: str                    # State abbreviation + district (e.g., "AZ-01", "AK-AL")
    state: str = ""            # Full state name
    representative: str = ""   # Current House representative name
    party: str = ""            # Party affiliation
```

**Notes:**
- `id` follows the standard district format: `{state_abbrev}-{district_number}` or `{state_abbrev}-AL` for at-large
- Senators are NOT modeled as district nodes (senators represent states, not districts). Senator data lives in the congressional cache and TribePacketContext.
- Keeping representative name on the node is convenient but becomes stale. Consider whether the node should just be the district identifier, with member data in the cache.

### TribePacketContext Design

This is NOT a graph node -- it is a runtime context object that aggregates data for packet generation. It does not need to follow the Node pattern.

```python
@dataclass
class TribePacketContext:
    """Aggregated context for generating a single Tribe's advocacy packet.

    Assembled by PacketOrchestrator from registry, congressional cache,
    and (in later phases) award data and hazard profiles.
    """
    # Identity (from registry -- REG-01, REG-03)
    tribe_id: str                          # BIA code
    tribe_name: str                        # Official name
    states: list[str] = field(default_factory=list)   # All states
    ecoregions: list[str] = field(default_factory=list)  # All ecoregions

    # Congressional (from cache -- CONG-01, CONG-02)
    districts: list[str] = field(default_factory=list)    # e.g., ["AZ-01", "AZ-02", "NM-03", "UT-03"]
    senators: list[dict] = field(default_factory=list)    # [{name, party, state, committees, contact}]
    representatives: list[dict] = field(default_factory=list)  # [{name, party, district, committees, contact}]

    # Stubs for Phase 6+ (populated later)
    awards: list[dict] = field(default_factory=list)      # Per-program award history
    hazard_profile: dict = field(default_factory=dict)     # NRI + USFS data

    # Metadata
    generated_at: str = ""                 # ISO timestamp
    registry_source: str = ""              # e.g., "EPA Tribes Names Service"
    congress_session: str = ""             # e.g., "119th Congress"
```

**Key design decisions:**
- Uses `list[str]`, `list[dict]`, `dict` -- more complex than graph nodes because this is a working context, not a persistent schema
- `field(default_factory=list)` for mutable defaults (standard Python dataclass pattern)
- Stub fields for Phase 6+ data populated as `list`/`dict` defaults -- zero-cost in Phase 5
- `generated_at` as ISO timestamp string (not datetime) for serialization consistency
- CONTEXT.md specifies "DOCX-aware structure -- minimize transformation needed in Phase 7 DOCX rendering" for congressional cache. The `senators` and `representatives` lists should include all fields needed for DOCX output (name, party, state, committees, leadership roles, contact info) to avoid re-querying the cache during rendering.

---

## Graph Integration

### How the Graph Works (builder.py)

The graph is built in two phases:
1. **Static seeding** -- `_seed_from_programs()` and `_seed_from_schema()` load from `program_inventory.json` and `graph_schema.json`
2. **Dynamic enrichment** -- `_enrich_from_items()` infers nodes/edges from scraped data

**Node addition:**
```python
self.graph.add_node(ProgramNode(id=pid, name=prog["name"], agency=prog["agency"], ...))
```

**Edge addition:**
```python
self.graph.add_edge(Edge(
    source_id=pid,
    target_id=auth["id"],
    edge_type="AUTHORIZED_BY",
))
```

**Edge deduplication:** `KnowledgeGraph.has_edge()` uses an `_edge_keys: set[tuple[str, str, str]]` for O(1) lookup.

### Where TribeNode and CongressionalDistrictNode Fit

**Static seeding path** (same as authorities, barriers, funding vehicles):

The graph builder already imports all node types from `schema.py` (line 17-21). Add TribeNode and CongressionalDistrictNode to this import list.

For static seeding, add a new method to `GraphBuilder`:
```python
def _seed_tribes(self) -> None:
    """Load TribeNodes and CongressionalDistrictNodes from tribal registry and congressional cache."""
    # Load tribal_registry.json -> TribeNode per Tribe
    # Load congressional_cache.json -> CongressionalDistrictNode per district
    # Create edges: REPRESENTED_BY, LOCATED_IN
```

Call this from `build()` after `_seed_from_schema()`:
```python
def build(self, scored_items: list[dict]) -> KnowledgeGraph:
    self._seed_from_programs()
    self._seed_from_schema()
    self._seed_tribes()          # NEW
    self._enrich_from_items(scored_items)
    ...
```

### New Edge Types

Add to the Edge docstring in schema.py:

```python
@dataclass
class Edge:
    """Directed relationship between two nodes.

    Edge types:
      AUTHORIZED_BY       (Program -> Authority)
      FUNDED_BY           (Program -> FundingVehicle)
      BLOCKED_BY          (Program -> Barrier)
      MITIGATED_BY        (Barrier -> AdvocacyLever)
      OBLIGATED_BY        (Program -> ObligationNode)
      ADVANCES            (StructuralAsk -> Program)
      TRUST_OBLIGATION    (TrustSuperNode -> Program)
      THREATENS           (ThreatNode -> Program)
      REPRESENTED_BY      (Tribe -> CongressionalDistrict)  # NEW
      LOCATED_IN          (Tribe -> EcoregionNode)           # NEW (if ecoregions become nodes)
    """
```

**REPRESENTED_BY direction:** Tribe -> District (a Tribe is represented by a district's member). This allows querying "which districts represent this Tribe?" by following outgoing edges from TribeNode.

**Edge metadata for REPRESENTED_BY:**
```python
Edge(
    source_id="tribe_navajo",
    target_id="AZ-01",
    edge_type="REPRESENTED_BY",
    metadata={"reservation_overlap": "Western Navajo lands", "state": "AZ"},
)
```

### Note on Ecoregions

CONTEXT.md says "7 custom advocacy-relevant regions." Two options:
1. **EcoregionNode** -- create a node type, connect Tribes via LOCATED_IN edges. Cleaner graph model.
2. **String field on TribeNode** -- simpler, no graph overhead.

Recommendation: Use string fields on TribeNode for now. Ecoregions are static classification metadata, not entities that connect to other graph objects (no edges to programs or barriers). If Phase 7+ needs ecoregion-based graph queries, upgrade to nodes then.

### Important: Graph Integration is Optional

The ROADMAP.md explicitly states: "Graph node integration for Tribes/Hazards/Districts optional (PacketOrchestrator works from JSON data files; graph enrichment can come later)."

The PacketOrchestrator should work from the JSON data files directly. Graph integration enriches the knowledge graph but is not required for packet generation. This means:
- TribeNode and CongressionalDistrictNode should be defined in schema.py (ready to use)
- Graph seeding in builder.py is optional and can be deferred
- The registry and congressional modules should NOT depend on the graph -- they load from JSON files independently

---

## Configuration Patterns

### Current scanner_config.json Structure

```json
{
  "domain": "tcr",
  "domain_name": "Tribal Climate Resilience",
  "sources": {
    "federal_register": { "name": ..., "base_url": ..., "requires_key": false, ... },
    "congress_gov": { "name": ..., "base_url": ..., "requires_key": true, "key_env_var": "CONGRESS_API_KEY", ... }
  },
  "scoring": { ... },
  "tribal_keywords": [...],
  "action_keywords": [...],
  "search_queries": [...],
  "scan_window_days": 14,
  "monitors": {
    "iija_sunset": { ... },
    "reconciliation": { ... },
    ...
  }
}
```

**Patterns:**
- Config is a single flat JSON file
- Source configs include `base_url`, `requires_key`, `key_env_var`
- API keys are stored in environment variables, referenced by `key_env_var` in config
- Monitor-specific config nested under `"monitors"` key
- No separate config files per module -- everything in one file

### Where to Add Tribal/Congressional Config

Add a top-level `"packets"` section (parallel to `"monitors"`):

```json
{
  "domain": "tcr",
  "sources": { ... },
  "scoring": { ... },
  "monitors": { ... },
  "packets": {
    "tribal_registry": {
      "data_path": "data/tribal_registry.json",
      "source": "EPA Tribes Names Service",
      "ecoregion_count": 7
    },
    "congressional": {
      "data_path": "data/congressional_cache.json",
      "congress_session": 119,
      "congress_api_key_env": "CONGRESS_API_KEY",
      "committees_of_interest": [
        "Senate Indian Affairs",
        "Senate Appropriations",
        "Senate Energy and Natural Resources",
        "House Natural Resources",
        "House Appropriations"
      ]
    },
    "output_dir": "outputs/packets"
  }
}
```

**API key handling:** Reuse the existing `CONGRESS_API_KEY` env var pattern already established by `congress_gov.py` (line 45):
```python
self.api_key = os.environ.get(src.get("key_env_var", "CONGRESS_API_KEY"), "")
```

The congressional cache builder (Phase 5 data preparation script) will use this same key.

### Config Loading Pattern

Modules access config through the dict passed to constructors:
```python
class PacketOrchestrator:
    def __init__(self, config: dict, programs: list[dict]):
        packet_config = config.get("packets", {})
        self.registry_path = Path(packet_config.get("tribal_registry", {}).get("data_path", "data/tribal_registry.json"))
        self.congress_path = Path(packet_config.get("congressional", {}).get("data_path", "data/congressional_cache.json"))
```

---

## Testing Patterns

### Current Test Structure

Single test file: `tests/test_decision_engine.py` (826 lines, 52 tests).

**Organization:**
- Module-level helper functions for building test fixtures (prefixed with `_`)
- Test classes grouped by functional area / rule being tested
- Class names: `TestLogic01RestoreReplace`, `TestEdgeCases`, `TestClassificationShape`
- Method names: `test_terminated_with_permanent_authority`, `test_no_match_returns_monitor_engage`

**Fixture pattern** (NO pytest fixtures -- plain helper functions):
```python
def _default_config(urgency_days=30):
    """Config with decision_engine section."""
    return {
        "monitors": {
            "decision_engine": {
                "urgency_threshold_days": urgency_days,
            }
        }
    }

def _make_graph(nodes=None, edges=None):
    """Build a minimal graph_data dict."""
    return {
        "nodes": nodes or {},
        "edges": edges or [],
    }
```

**No conftest.py exists.** No pytest configuration file (no pytest.ini, no pyproject.toml). Tests run with `pytest tests/` using default discovery.

### Testing Patterns for New Modules

Follow the same patterns. Create:

```
tests/
    test_decision_engine.py    # existing (52 tests)
    test_tribal_registry.py    # NEW: registry loading, search, fuzzy matching
    test_congressional.py      # NEW: delegation lookup, multi-state, Alaska at-large
    test_packet_context.py     # NEW: TribePacketContext assembly, field validation
    test_graph_schema.py       # NEW: TribeNode/CongressionalDistrictNode serialization
```

**Test file naming:** `test_{module_name}.py` -- matches existing `test_decision_engine.py`.

**Fixture pattern for registry tests:**
```python
def _sample_registry():
    """Minimal registry for testing."""
    return [
        {
            "id": "BIA001",
            "name": "Navajo Nation",
            "states": ["AZ", "NM", "UT"],
            "ecoregion": "Southwest",
            "alternate_names": ["Navajo", "Dine Nation"]
        },
        {
            "id": "BIA002",
            "name": "Cherokee Nation",
            "states": ["OK"],
            "ecoregion": "Southeast",
            "alternate_names": ["Cherokee Nation of Oklahoma"]
        },
    ]

def _sample_congressional_cache():
    """Minimal congressional data for testing."""
    return {
        "districts": {
            "AZ-01": {"representative": "Rep. John Doe", "party": "R"},
            "AK-AL": {"representative": "Rep. Jane Smith", "party": "R"},
        },
        "senators": {
            "AZ": [
                {"name": "Sen. Mark Kelly", "party": "D", "committees": ["Appropriations"]},
                {"name": "Sen. Kyrsten Sinema", "party": "I", "committees": []}
            ]
        }
    }
```

**Test class organization:**
```python
class TestTribalRegistryLoading:
    """Tests for loading the 575-Tribe registry."""

class TestTribalRegistrySearch:
    """Tests for exact and fuzzy Tribe name search."""

class TestCongressionalMapper:
    """Tests for Tribe-to-delegation lookup."""

class TestAlaskaHandling:
    """Tests for Alaska at-large district edge case."""

class TestMultiStateTribe:
    """Tests for multi-state Tribes (Navajo: AZ, NM, UT)."""
```

**What to test for Phase 5 specifically:**
1. Registry loads without error, all 575 entries parsed
2. Exact name search returns correct Tribe
3. Substring search returns candidates
4. Fuzzy search falls back when no exact match
5. Multi-state Tribe returns all districts across all states
6. Alaska at-large maps correctly
7. Senator deduplication (one per state, not per district)
8. TribePacketContext has all required fields populated
9. TribeNode serialization via `node_to_dict()` works
10. Edge cases: empty registry, unknown Tribe name, missing congressional data

---

## Code Hygiene Standards

### Encoding

**Every `open()` call uses `encoding="utf-8"`** -- no exceptions in the entire codebase:
```python
with open(CONFIG_PATH, encoding="utf-8") as f:
    return json.load(f)
```

This is critical on Windows where the default encoding is the system locale (often cp1252), not UTF-8. Tribe names contain special characters (diacritics, apostrophes) that will corrupt without explicit UTF-8.

### Atomic Writes

**Pattern used for all output files** (main.py lines 155-159, 208-213, generator.py lines 536-539):
```python
tmp_path = output_path.with_suffix(".tmp")
with open(tmp_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, default=str)
tmp_path.replace(output_path)
```

Use this pattern for:
- Writing `tribal_registry.json`
- Writing `congressional_cache.json`
- Any packet output files

### Logging

**One logger per module, at module level:**
```python
logger = logging.getLogger(__name__)
```

**Log level usage:**
- `logger.info()` -- normal operation (scan counts, file paths)
- `logger.warning()` -- degraded but continuing (missing API key, data gap)
- `logger.error()` -- failure (corrupt file, exhausted retries)
- `logger.exception()` -- caught exception with traceback

**No print() for operational messages** in library code. Only main.py uses `print()` for user-facing output. The new packet modules should use `logger.info()` for operational messages and `print()` only in the CLI dispatch path.

### Import Style

**Standard library first, then third-party, then local:**
```python
import json
import logging
from pathlib import Path

import aiohttp

from src.graph.schema import ProgramNode, Edge
```

**Relative imports not used** -- all imports are absolute from `src.`:
```python
from src.scrapers.base import BaseScraper
from src.analysis.decision_engine import DecisionEngine
```

### Datetime Handling

**Uses `datetime.now(timezone.utc)`** (not deprecated `datetime.utcnow()`):
```python
from datetime import datetime, timezone
now = datetime.now(timezone.utc).isoformat()
```

### Path Handling

**Uses `pathlib.Path`** throughout:
```python
CONFIG_PATH = Path("config/scanner_config.json")
OUTPUTS_DIR = Path("outputs")
```

**Creates directories with `mkdir(parents=True, exist_ok=True)`:**
```python
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
```

### Type Hints

**Uses Python 3.12+ syntax** -- `list[dict]` not `List[Dict]`, `dict | None` not `Optional[dict]`:
```python
def generate(self, scored_items: list[dict], changes: dict,
             graph_data: dict | None = None,
             monitor_data: dict | None = None) -> dict:
```

### Docstrings

**Every module has a module-level docstring.** Every public class and method has a docstring. Style is descriptive (not Google/NumPy format):
```python
"""Report generator.

Produces Markdown briefings and JSON output from scored and change-detected
policy items, formatted for Tribal Leaders. Includes Knowledge Graph
insights: barriers, authorities, and funding vehicle summaries.
"""
```

---

## Recommendations

### 1. New Module Structure

```
src/packets/
    __init__.py          # empty
    orchestrator.py      # PacketOrchestrator class
    context.py           # TribePacketContext dataclass
    registry.py          # TribalRegistry class (load, search, resolve)
    congress.py          # CongressionalMapper class (delegation lookup)
```

### 2. Lazy Import in main.py

Follow the MonitorRunner pattern (lazy imports to avoid import-time overhead):
```python
if args.prep_packets:
    from src.packets.orchestrator import PacketOrchestrator
    # ...
```

### 3. PacketOrchestrator Design

Follow the ReportGenerator pattern: constructor takes config + programs, main method orchestrates the workflow:

```python
class PacketOrchestrator:
    """Orchestrates Tribe-specific advocacy packet generation.

    Phase 5 skeleton: resolves Tribe identity, displays delegation.
    Phase 6+: populates award history, hazard profiles.
    Phase 7+: generates DOCX output.
    """

    def __init__(self, config: dict, programs: list[dict]):
        self.config = config
        self.programs = {p["id"]: p for p in programs}
        self.registry = TribalRegistry(config)
        self.congress = CongressionalMapper(config)

    def run_single_tribe(self, tribe_name: str) -> None:
        """Resolve Tribe, display delegation, generate packet (stub in Phase 5)."""
        tribe = self.registry.resolve(tribe_name)
        if not tribe:
            # Handle not found
            return
        context = self._build_context(tribe)
        self._display_tribe_info(context)
        # Phase 7+: self._generate_docx(context)

    def run_all_tribes(self) -> None:
        """Batch generate for all 575 Tribes."""
        tribes = self.registry.get_all()
        for i, tribe in enumerate(tribes, 1):
            print(f"[{i}/{len(tribes)}] {tribe['name']}...")
            context = self._build_context(tribe)
            # Phase 7+: self._generate_docx(context)

    def _build_context(self, tribe: dict) -> TribePacketContext:
        """Assemble TribePacketContext from all data sources."""
        # ...
```

### 4. TribalRegistry Design

```python
class TribalRegistry:
    """Loads and searches the 575-Tribe registry."""

    def __init__(self, config: dict):
        packet_config = config.get("packets", {})
        self.data_path = Path(
            packet_config.get("tribal_registry", {}).get("data_path", "data/tribal_registry.json")
        )
        self._tribes: list[dict] = []
        self._loaded = False

    def _load(self) -> None:
        """Lazy load the registry on first access."""
        if self._loaded:
            return
        with open(self.data_path, encoding="utf-8") as f:
            data = json.load(f)
        self._tribes = data if isinstance(data, list) else data.get("tribes", [])
        self._loaded = True
        logger.info("Loaded %d Tribes from %s", len(self._tribes), self.data_path)

    def resolve(self, name: str) -> dict | None:
        """Resolve a Tribe name: exact match first, then substring, then fuzzy."""
        self._load()
        # 1. Exact match on official name
        # 2. Exact match on alternate names
        # 3. Substring match
        # 4. Fuzzy fallback

    def get_all(self) -> list[dict]:
        """Return all 575 Tribes."""
        self._load()
        return self._tribes
```

### 5. Graph Schema Additions (schema.py)

Add TribeNode and CongressionalDistrictNode to the existing schema.py file (not a new file). This follows the convention of all node types being defined together.

Update the Edge docstring to include the new edge types.

Add new node types to the import list in builder.py.

### 6. Test Strategy

- Create `tests/test_tribal_registry.py` and `tests/test_congressional.py`
- Use plain helper functions (not pytest fixtures)
- Build test data that exercises: exact match, substring, fuzzy, not found, multi-state, Alaska at-large
- Aim for 20-30 tests covering the Phase 5 requirements

---

## Open Questions

1. **Should `rich` be added as a dependency for progress bars?** CONTEXT.md mentions "Rich progress bars for multi-step operations." The current codebase has zero third-party CLI dependencies (only aiohttp, dateutil, jinja2). Adding `rich` is a new dependency category. Alternative: use simple `print()` progress (already shown in batch mode pattern `[142/575] Cherokee Nation... done`).

2. **Where does the fuzzy matching library go?** CONTEXT.md mentions fuzzy search. Phase 6 uses `rapidfuzz` for award matching. Should Phase 5 also use `rapidfuzz` for Tribe name search, or use a simpler approach (difflib.SequenceMatcher from stdlib)? Using `rapidfuzz` would add a compile-time dependency in Phase 5 that Phase 6 also needs. Using `difflib` avoids the dependency now but means two different fuzzy matching implementations.

3. **Should graph integration be in Phase 5 or deferred?** ROADMAP says "optional." The planner should decide: define the dataclasses in schema.py now (zero-cost), defer the builder.py integration to later.

4. **Where does the registry build script live?** The one-time script that fetches from EPA API and builds `tribal_registry.json` is a build tool, not a runtime module. Options: `scripts/build_registry.py`, `tools/build_registry.py`, or `src/packets/build_registry.py`. The codebase has no `scripts/` or `tools/` directory currently.

5. **What exactly goes in `congressional_cache.json`?** The CONTEXT.md specifies extensive data (committees, leadership roles, contact info, geographic overlap). The exact schema depends on what Congress.gov API provides and what the CRS R48107 extraction yields. This should be designed after Teams 2 and 3 report their API findings.

---

*Research complete. All findings derived from direct source code analysis of the existing codebase.*
