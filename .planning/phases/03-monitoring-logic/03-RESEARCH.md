# Phase 3: Monitoring Capabilities and Decision Logic - Research

**Researched:** 2026-02-09
**Domain:** Brownfield Python codebase -- adding monitor modules and rule-based classification to existing pipeline
**Confidence:** HIGH

## Summary

This research investigates how to add five monitoring capabilities (IIJA sunset tracker, reconciliation monitor, Tribal consultation tracker, Hot Sheets sync validator, DHS funding cliff tracker) and five decision rules (advocacy goal classification) to the existing TCR Policy Scanner pipeline. The work is purely Python logic operating on the existing knowledge graph, program inventory, and scraped items. No new external libraries are needed.

The existing codebase follows a clear DAG pipeline: Ingest -> Normalize -> Graph Construction -> Analysis -> Reporting. Phase 3 inserts a new pipeline stage between Graph Construction and Reporting: **Monitoring + Decision Logic**. Each monitor inspects the graph state and scraped items to produce alerts. The decision engine then classifies each program into one of five advocacy goals based on graph edges, CI status, and monitor findings. All output is attached to the existing `scored_items` and `graph_data` structures, which Phase 4 reporting will consume.

The critical legislative context shapes the monitor implementations: IIJA authorization expires September 30, 2026 (4 programs affected). The One Big Beautiful Bill Act (Public Law 119-21, signed July 4, 2025) modified but did NOT fully repeal IRA Section 6417 elective pay -- it imposed new begin-construction deadlines (July 4, 2026 for wind/solar) rather than outright termination. DHS was funded only through February 13, 2026 via a CR, with full-year funding still unresolved. These facts directly inform what the monitors look for and how urgency is calculated.

**Primary recommendation:** Create a new `src/monitors/` package with one module per monitor plus a `decision_engine.py` in `src/analysis/`. Each monitor follows a consistent interface (accepts graph_data + scored_items + config, returns alerts list). The decision engine applies rules in priority order (LOGIC-05 Urgent Stabilization first as override, then LOGIC-01 through LOGIC-04) and attaches the classification to each program in the pipeline output.

## Standard Stack

This is a brownfield project. The "standard stack" is the existing codebase. No new external dependencies are needed.

### Core Files to Create

| File | Purpose | Requirements |
|------|---------|-------------|
| `src/monitors/__init__.py` | Package init, exports monitor runner | All MON-* |
| `src/monitors/iija_sunset.py` | IIJA sunset tracker | MON-01 |
| `src/monitors/reconciliation.py` | Reconciliation bill monitor | MON-02 |
| `src/monitors/tribal_consultation.py` | DTLL / EO 13175 detector | MON-03 |
| `src/monitors/hot_sheets.py` | Hot Sheets sync validator | MON-04 |
| `src/monitors/dhs_funding.py` | DHS funding cliff tracker | MON-05 |
| `src/analysis/decision_engine.py` | 5-rule advocacy classifier | LOGIC-01 through LOGIC-05 |

### Core Files to Modify

| File | What Changes | Why |
|------|-------------|-----|
| `src/main.py` | Insert monitor + decision engine stages into `run_pipeline()` | Pipeline orchestration |
| `data/program_inventory.json` | Add `hot_sheets_status` field to each program | MON-04 per CONTEXT.md decision |
| `data/policy_tracking.json` | Add `hot_sheets_status` references if needed | Sync validator source |
| `config/scanner_config.json` | Add monitor configuration section | Thresholds, time windows |

### Files That Must NOT Break (Downstream Consumers)

| File | What It Reads | Risk |
|------|--------------|------|
| `src/reports/generator.py` | `scored_items` and `graph_data` dicts | New monitor fields must not break existing format |
| `src/analysis/change_detector.py` | `scored_items` via `_item_key()` | New fields are additive; safe |
| `.github/workflows/daily-scan.yml` | Runs `python -m src.main --verbose` | No CLI changes needed for monitors |

### No New Dependencies

All monitor logic uses standard library (`datetime`, `re`, `json`, `logging`) plus the already-installed `python-dateutil` for date calculations. No new pip packages required.

**Installation:** No changes to `requirements.txt`.

## Architecture Patterns

### Recommended Project Structure (Phase 3 additions)

```
src/
  monitors/
    __init__.py              # MonitorRunner class, run_all_monitors()
    iija_sunset.py           # IIJASunsetMonitor
    reconciliation.py        # ReconciliationMonitor
    tribal_consultation.py   # TribalConsultationMonitor
    hot_sheets.py            # HotSheetsValidator
    dhs_funding.py           # DHSFundingCliffMonitor
  analysis/
    decision_engine.py       # DecisionEngine with 5 rules
    relevance.py             # (existing, unchanged)
    change_detector.py       # (existing, unchanged)
```

### Pattern 1: Monitor Interface (Consistent Shape)

**What:** Every monitor follows the same interface so the pipeline runner can call them uniformly.
**When to use:** All 5 monitors.
**Source:** Derived from existing codebase patterns (scrapers share `BaseScraper` with `scan()` method).

```python
# Source: Follows existing BaseScraper pattern from src/scrapers/base.py
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class MonitorAlert:
    """Standard alert produced by any monitor."""
    monitor: str           # e.g., "iija_sunset", "reconciliation"
    severity: str          # "CRITICAL", "WARNING", "INFO"
    program_ids: list[str] # affected programs
    title: str             # short summary
    detail: str            # full explanation
    metadata: dict = field(default_factory=dict)  # monitor-specific data
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


class BaseMonitor:
    """Base class for all monitors."""

    def __init__(self, config: dict, programs: dict):
        self.config = config
        self.programs = programs  # {program_id: program_dict}

    def check(self, graph_data: dict, scored_items: list[dict]) -> list[MonitorAlert]:
        """Run the monitor check. Returns a list of alerts."""
        raise NotImplementedError
```

### Pattern 2: Pipeline Integration Point

**What:** Monitors and decision engine run after graph construction, before reporting.
**When to use:** Modifying `src/main.py` `run_pipeline()`.
**Source:** Existing pipeline flow in `src/main.py` lines 146-192.

```python
# Current pipeline stages in run_pipeline():
#   1-2. Ingest + Normalize (run_scan)
#   3. Graph Construction (build_graph)
#   4. Analysis (scoring)  -- note: actually happens before graph in code
#   5. Reporting (generate)

# Phase 3 adds between Graph Construction and Reporting:
#   3.5  Monitors (run all monitors against graph + scored items)
#   3.6  Decision Engine (classify each program into advocacy goal)

# In run_pipeline(), after build_graph():
from src.monitors import MonitorRunner
from src.analysis.decision_engine import DecisionEngine

monitor_runner = MonitorRunner(config, programs)
alerts = monitor_runner.run_all(graph_data, scored)

decision_engine = DecisionEngine(config, programs)
classifications = decision_engine.classify_all(graph_data, alerts)

# Attach to output for reporting:
# - alerts go into a new "monitor_alerts" key
# - classifications go onto each program entry
```

### Pattern 3: Decision Engine Rule Chain (Priority-Ordered)

**What:** Rules are evaluated in priority order. LOGIC-05 (Urgent Stabilization) is an override that short-circuits. Rules 1-4 are evaluated if no override, and the highest-priority matching rule wins.
**When to use:** `src/analysis/decision_engine.py`.
**Rationale for ordering:** CONTEXT.md gives Claude discretion on priority ordering. The natural ordering from the requirements is: LOGIC-05 overrides everything (explicit in requirement text: "overrides all other classifications"), then LOGIC-01 through LOGIC-04 in decreasing urgency -- Restore/Replace (program dead, most urgent), Protect Base (under active threat), Direct Access Parity (structural disadvantage), Expand and Strengthen (stable, growth-oriented).

```python
ADVOCACY_GOALS = {
    "URGENT_STABILIZATION": "Urgent Stabilization",
    "RESTORE_REPLACE": "Restore/Replace",
    "PROTECT_BASE": "Protect Base",
    "DIRECT_ACCESS_PARITY": "Direct Access Parity",
    "EXPAND_STRENGTHEN": "Expand and Strengthen",
}

# Priority order (first match wins):
RULE_PRIORITY = [
    "URGENT_STABILIZATION",  # LOGIC-05: THREATENS edge within 30 days
    "RESTORE_REPLACE",        # LOGIC-01: TERMINATED + ACTIVE authority
    "PROTECT_BASE",           # LOGIC-02: DISCRETIONARY + ELIMINATE/REDUCE signal
    "DIRECT_ACCESS_PARITY",   # LOGIC-03: STATE_PASS_THROUGH + HIGH burden
    "EXPAND_STRENGTHEN",      # LOGIC-04: STABLE/SECURE + DIRECT/SET_ASIDE access
]
```

### Pattern 4: Hot Sheets Override Logic

**What:** Hot Sheets positions are ground truth per CONTEXT.md decision. When scanner CI status diverges from Hot Sheets, scanner auto-adjusts.
**When to use:** `src/monitors/hot_sheets.py`.
**Source:** CONTEXT.md locked decision.

```python
# Per CONTEXT.md decisions:
# 1. hot_sheets_status embedded in program_inventory.json alongside CI score
# 2. First divergence: alert prominently
# 3. Subsequent runs: log silently
# 4. Staleness warning when last_updated exceeds threshold

# program_inventory.json program entry gets new field:
{
    "id": "irs_elective_pay",
    "confidence_index": 0.55,
    "ci_status": "AT_RISK",
    "hot_sheets_status": {
        "status": "AT_RISK",
        "last_updated": "2026-02-09",
        "source": "FY26 Hot Sheets v2"
    },
    # ... existing fields ...
}
```

### Pattern 5: Graph State Queries for Decision Rules

**What:** Decision rules need to query the knowledge graph for specific edge patterns (e.g., "is there a THREATENS edge within 30 days?"). The existing `KnowledgeGraph` class in `builder.py` has methods like `get_program_subgraph()` and `get_barriers_for_program()` that show the query pattern.
**When to use:** Decision engine rules querying graph_data dict.
**Source:** Existing `KnowledgeGraph` methods in `src/graph/builder.py` lines 81-104.

```python
# Graph data is a serialized dict (from graph.to_dict()):
# {
#   "nodes": { "node_id": { "id": ..., "_type": ..., ... } },
#   "edges": [ { "source": ..., "target": ..., "type": ..., "metadata": {} } ],
#   "summary": { ... }
# }

# Query pattern for finding edges:
def get_edges_for_program(graph_data: dict, program_id: str, edge_type: str) -> list[dict]:
    """Find all edges of a given type connected to a program."""
    return [
        e for e in graph_data["edges"]
        if (e["source"] == program_id or e["target"] == program_id)
        and e["type"] == edge_type
    ]

# For LOGIC-01 (Restore/Replace): Check if program is TERMINATED and has ACTIVE authority
def check_restore_replace(program: dict, graph_data: dict) -> bool:
    if program.get("ci_status") != "TERMINATED":
        return False
    auth_edges = get_edges_for_program(graph_data, program["id"], "AUTHORIZED_BY")
    for edge in auth_edges:
        auth_node = graph_data["nodes"].get(edge["target"], {})
        if auth_node.get("durability", "").lower() in ("permanent", "active"):
            return True
    return False
```

### Pattern 6: New Edge Type for Monitors -- THREATENS

**What:** Monitors need to express time-sensitive threats as graph edges. A THREATENS edge from a threat source to a program node carries a deadline in its metadata.
**When to use:** IIJA sunset tracker, reconciliation monitor, DHS funding cliff tracker create THREATENS edges. Decision engine rule LOGIC-05 looks for them.
**Source:** Follows existing Edge pattern from `src/graph/schema.py`.

```python
# THREATENS edge: source is the threat, target is the program
# metadata carries the deadline and days_remaining
Edge(
    source_id="threat_iija_sunset",
    target_id="epa_stag",
    edge_type="THREATENS",
    metadata={
        "threat_type": "iija_sunset",
        "deadline": "2026-09-30",
        "days_remaining": 233,
        "description": "IIJA supplemental funding expires FY26 end",
    },
)
```

**Update to schema.py Edge docstring:** Add THREATENS to the edge type documentation:
```python
# THREATENS   (ThreatNode -> Program) -- time-sensitive legislative threat
```

### Anti-Patterns to Avoid

- **Modifying scrapers for monitoring:** Monitors run AFTER scraping, on the graph and scored items. Do not add monitor logic into scraper classes.
- **Mutating program_inventory.json at runtime:** The Hot Sheets validator reads `hot_sheets_status` from inventory at load time. It does NOT write back to the JSON file during a scan. Override logic adjusts the in-memory program dict for downstream processing.
- **Complex rule engine library:** The 5 decision rules are simple if/then conditions on graph state. Do not introduce a rule engine library (e.g., Durable Rules, GoRules). Straight Python functions are clearer, more debuggable, and consistent with the existing codebase style.
- **Monitors that make API calls:** Monitors analyze already-scraped data. They do not make new HTTP requests. The scrapers handle all API interaction.
- **Embedding dates as hardcoded magic numbers:** Use `scanner_config.json` for configurable thresholds (sunset warning days, staleness threshold, urgency window). The config already has `scan_window_days: 14` as a precedent.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Date arithmetic | Manual day counting with timedelta gymnastics | `python-dateutil` `relativedelta` + `datetime` (already installed) | Handles month boundaries, fiscal year ends correctly |
| Fiscal year end calculation | Custom FY logic | Hardcode `datetime(2026, 9, 30)` for IIJA sunset; config-driven for others | FY26 end is a known constant; over-generalizing adds complexity |
| Rule engine framework | External rule engine (Durable Rules, GoRules) | Simple Python functions in priority-ordered list | 5 rules is not enough to justify a framework; plain Python is debuggable |
| Alert deduplication | Custom alert ID generation | Use `(monitor, program_id, threat_type)` tuples as natural keys | Follows existing `_item_key()` pattern from change_detector.py |
| Hot Sheets divergence tracking | File-based state for "first time seen" | Compare in-memory CI status against hot_sheets_status on every run; use `change_detector.py` cache for "previously seen divergences" | Existing cache infrastructure handles state persistence |
| Graph edge queries | Custom graph database | Filter the `graph_data["edges"]` list in Python | 118 edges is tiny; linear scan is sub-millisecond; no need for a query engine |

**Key insight:** This phase is about writing classification logic that reads existing data structures. The graph is small (79 nodes, 118 edges), the rule set is small (5 rules), and the monitor set is small (5 monitors). Simplicity and clarity beat abstraction.

## Common Pitfalls

### Pitfall 1: THREATENS Edge Not in Graph at Decision Time

**What goes wrong:** Monitors create THREATENS edges but the decision engine cannot find them because they were not added to the graph.
**Why it happens:** Monitors produce alerts as separate data structures. If THREATENS edges are only in the alerts, the decision engine cannot query them through the graph.
**How to avoid:** Monitors should both (a) return `MonitorAlert` objects for reporting AND (b) add THREATENS edges to the graph_data dict (mutate in place or return edge additions). The decision engine then queries the graph for THREATENS edges like any other edge type.
**Warning signs:** LOGIC-05 (Urgent Stabilization) never triggers despite active threats.

### Pitfall 2: Hot Sheets Override Clobbers Original CI for Reporting

**What goes wrong:** The Hot Sheets validator overwrites `ci_status` in the program dict, and the original scanner-computed CI is lost. Reports cannot show "Scanner says X, Hot Sheets says Y."
**Why it happens:** Mutable dict overwrite without preserving the original value.
**How to avoid:** When overriding, store the original value: `program["original_ci_status"] = program["ci_status"]` before setting `program["ci_status"] = hot_sheets_status`. The report can then show both.
**Warning signs:** Report shows Hot Sheets status but no indication that a divergence occurred.

### Pitfall 3: IIJA Sunset Dates Are Per-Program, Not Global

**What goes wrong:** Treating all IIJA programs as having the same sunset date (September 30, 2026).
**Why it happens:** Assuming all IIJA funding follows the same timeline.
**How to avoid:** The graph_schema already has per-authority durability data. `auth_iija` says "Expires FY26", `auth_iija_wildfire` says "Expires when funds exhausted", `auth_protect_formula` says "Expires FY26", `auth_iija_watersmart` says "Expires FY26". The sunset tracker should use the authority durability field to determine the expiration type, not a global date. For "Expires FY26", use September 30, 2026. For "Expires when funds exhausted", use a different alert type.
**Warning signs:** USDA Wildfire gets a false "FY26 sunset" alert when its IIJA funding expires on fund exhaustion, not on a calendar date.

### Pitfall 4: Reconciliation Monitor Detects Historical Bills, Not Active Threats

**What goes wrong:** The monitor flags every bill mentioning "reconciliation" including already-enacted laws (the OBBBA is Public Law 119-21, already signed July 4, 2025).
**Why it happens:** Pattern matching on bill text without checking bill status.
**How to avoid:** Filter Congress.gov results by bill status. Only bills in active committee, floor consideration, or conference are threats. Enacted bills are historical context, not active threats. The Congress.gov scraper already captures `latest_action` text which indicates status.
**Warning signs:** Every scan produces a "reconciliation threat" alert because the OBBBA text is always present in results.

### Pitfall 5: Decision Rules Produce No Classification for Some Programs

**What goes wrong:** A program matches none of the 5 rules and gets no advocacy goal.
**Why it happens:** The rules as stated in requirements have specific conditions. Programs like DOE Indian Energy (UNCERTAIN, no THREATENS edge, not TERMINATED, not clearly DISCRETIONARY with ELIMINATE signal) might fall through all rules.
**How to avoid:** Add a default classification. Programs that match no rule should get a "Monitor" or "Assess" classification, or the closest matching rule should be applied with lower confidence. Alternatively, ensure every status tier maps to at least one rule: STABLE/SECURE -> LOGIC-04 (Expand and Strengthen), UNCERTAIN/AT_RISK -> LOGIC-02 (Protect Base), etc.
**Warning signs:** Programs appear in reports without an advocacy_goal field.

### Pitfall 6: DHS CR Expiration Date Changes Between Scans

**What goes wrong:** Hardcoding February 13, 2026 as the DHS CR expiration. Congress may pass a new CR with a different date.
**Why it happens:** The DHS funding situation is fluid. As of research date, DHS is funded only through February 13 via CR, but this will change.
**How to avoid:** Make the DHS CR expiration date configurable in `scanner_config.json`. Update it when Congress acts. The monitor should also detect if Congressional scraper returns a new DHS CR/funding bill, which would supersede the configured date.
**Warning signs:** DHS funding cliff alert persists after Congress has extended DHS funding.

### Pitfall 7: OBBBA Changes Mischaracterized as Full Section 6417 Repeal

**What goes wrong:** The reconciliation monitor alerts that Section 6417 has been repealed when it has actually been modified with new construction deadlines.
**Why it happens:** Research shows the OBBBA (Public Law 119-21) modified but did NOT repeal Section 6417. It imposed new begin-construction deadlines (July 4, 2026 for wind/solar under 45Y/48E) but preserved elective pay for existing projects and those meeting the new timelines. The monitor must distinguish between "repealed" and "modified with phase-out."
**How to avoid:** The reconciliation monitor should track the OBBBA's actual impact: construction-start deadlines for new projects, not outright repeal. Active monitoring should focus on any NEW reconciliation bills that would further modify or repeal Section 6417 beyond what the OBBBA already did.
**Warning signs:** Alert says "Section 6417 repeal detected" when scanning OBBBA text, causing unnecessary panic.

## Code Examples

### Example 1: IIJA Sunset Monitor

```python
# Source: Existing graph_schema.json authority data + python-dateutil
import logging
from datetime import datetime, date

logger = logging.getLogger(__name__)

# IIJA programs from graph_schema.json authorities with "Expires FY26" durability
IIJA_FY26_PROGRAMS = {
    "epa_stag": "auth_iija",
    "dot_protect": "auth_protect_formula",
    "usbr_watersmart": "auth_iija_watersmart",
}
# Separate: USDA wildfire has "Expires when funds exhausted"
IIJA_FUND_EXHAUSTION_PROGRAMS = {
    "usda_wildfire": "auth_iija_wildfire",
}
IIJA_FY26_END = date(2026, 9, 30)


class IIJASunsetMonitor:
    """MON-01: Flags IIJA-funded programs approaching FY26 expiration."""

    def __init__(self, config: dict, programs: dict):
        self.programs = programs
        # Default: start warning 180 days before expiration
        monitor_config = config.get("monitors", {}).get("iija_sunset", {})
        self.warning_days = monitor_config.get("warning_days", 180)
        self.critical_days = monitor_config.get("critical_days", 90)

    def check(self, graph_data: dict, scored_items: list[dict]) -> list:
        alerts = []
        today = date.today()
        days_remaining = (IIJA_FY26_END - today).days

        if days_remaining <= 0:
            # Already expired
            return alerts

        # Check if any reauthorization bill has been detected in scored items
        reauth_detected = self._detect_reauthorization(scored_items)

        for pid, auth_id in IIJA_FY26_PROGRAMS.items():
            program = self.programs.get(pid)
            if not program:
                continue

            has_reauth = pid in reauth_detected
            if has_reauth:
                continue  # Reauthorization bill found; no sunset warning

            severity = "CRITICAL" if days_remaining <= self.critical_days else "WARNING"
            if days_remaining > self.warning_days:
                severity = "INFO"

            alerts.append(MonitorAlert(
                monitor="iija_sunset",
                severity=severity,
                program_ids=[pid],
                title=f"IIJA sunset: {program['name']} - {days_remaining} days remaining",
                detail=(
                    f"{program['name']} is funded under {auth_id} which expires "
                    f"September 30, 2026. {days_remaining} days remain. "
                    f"No reauthorization bill detected in scan results."
                ),
                metadata={
                    "deadline": str(IIJA_FY26_END),
                    "days_remaining": days_remaining,
                    "authority_id": auth_id,
                    "reauth_detected": False,
                },
            ))

        return alerts

    def _detect_reauthorization(self, scored_items: list[dict]) -> set:
        """Check scored items for reauthorization bill signals."""
        reauth_programs = set()
        reauth_keywords = ["reauthorization", "reauthorize", "extension of"]
        for item in scored_items:
            if item.get("source") != "congress_gov":
                continue
            text = f"{item.get('title', '')} {item.get('abstract', '')}".lower()
            if any(kw in text for kw in reauth_keywords):
                for pid in item.get("matched_programs", []):
                    reauth_programs.add(pid)
        return reauth_programs
```

### Example 2: Decision Engine with Priority-Ordered Rules

```python
# Source: Follows existing analysis module patterns from src/analysis/
import logging
from typing import Optional

logger = logging.getLogger(__name__)

ADVOCACY_GOALS = {
    "URGENT_STABILIZATION": "Urgent Stabilization",
    "RESTORE_REPLACE": "Restore/Replace",
    "PROTECT_BASE": "Protect Base",
    "DIRECT_ACCESS_PARITY": "Direct Access Parity",
    "EXPAND_STRENGTHEN": "Expand and Strengthen",
}


class DecisionEngine:
    """Classifies programs into advocacy goals using 5 decision rules."""

    def __init__(self, config: dict, programs: dict):
        self.config = config
        self.programs = programs  # {pid: program_dict}
        self.urgency_days = config.get("monitors", {}).get(
            "urgency_threshold_days", 30
        )

    def classify_all(
        self, graph_data: dict, alerts: list
    ) -> dict[str, dict]:
        """Classify every program. Returns {program_id: classification}."""
        results = {}
        for pid, program in self.programs.items():
            classification = self._classify_program(pid, program, graph_data, alerts)
            results[pid] = classification
        return results

    def _classify_program(
        self, pid: str, program: dict, graph_data: dict, alerts: list
    ) -> dict:
        """Apply rules in priority order. First match wins."""

        # LOGIC-05: Urgent Stabilization (override -- check first)
        urgent = self._check_urgent_stabilization(pid, graph_data, alerts)
        if urgent:
            return urgent

        # LOGIC-01: Restore/Replace
        restore = self._check_restore_replace(pid, program, graph_data)
        if restore:
            return restore

        # LOGIC-02: Protect Base
        protect = self._check_protect_base(pid, program, graph_data, alerts)
        if protect:
            return protect

        # LOGIC-03: Direct Access Parity
        parity = self._check_direct_access_parity(pid, program, graph_data)
        if parity:
            return parity

        # LOGIC-04: Expand and Strengthen
        expand = self._check_expand_strengthen(pid, program, graph_data)
        if expand:
            return expand

        # Default: no rule matched
        return {
            "advocacy_goal": None,
            "rule": None,
            "confidence": "LOW",
            "reason": "No decision rule matched for this program",
        }

    def _check_urgent_stabilization(self, pid, graph_data, alerts):
        """LOGIC-05: THREATENS edge within urgency_days overrides all."""
        threatens_edges = [
            e for e in graph_data.get("edges", [])
            if e["target"] == pid and e["type"] == "THREATENS"
        ]
        for edge in threatens_edges:
            days = edge.get("metadata", {}).get("days_remaining", 999)
            if days <= self.urgency_days:
                return {
                    "advocacy_goal": "URGENT_STABILIZATION",
                    "rule": "LOGIC-05",
                    "confidence": "HIGH",
                    "reason": f"THREATENS edge: {edge['metadata'].get('description', '')} "
                              f"({days} days remaining)",
                    "threat_metadata": edge["metadata"],
                }
        return None

    def _check_restore_replace(self, pid, program, graph_data):
        """LOGIC-01: TERMINATED program + ACTIVE authority."""
        if program.get("ci_status") not in ("TERMINATED", "FLAGGED"):
            return None
        # Check for active authorities
        auth_edges = [
            e for e in graph_data.get("edges", [])
            if e["source"] == pid and e["type"] == "AUTHORIZED_BY"
        ]
        for edge in auth_edges:
            auth = graph_data["nodes"].get(edge["target"], {})
            durability = auth.get("durability", "").lower()
            if "permanent" in durability or "active" in durability:
                return {
                    "advocacy_goal": "RESTORE_REPLACE",
                    "rule": "LOGIC-01",
                    "confidence": "HIGH",
                    "reason": f"Program is {program.get('ci_status')} but "
                              f"authorized under {auth.get('citation', 'unknown')} "
                              f"(durability: {auth.get('durability', 'unknown')})",
                }
        return None
```

### Example 3: Hot Sheets Sync Validator

```python
# Source: CONTEXT.md locked decisions on Hot Sheets handling
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

DEFAULT_STALENESS_DAYS = 90  # Recommended default per research


class HotSheetsValidator:
    """MON-04: Compares scanner CI vs Hot Sheets positions."""

    def __init__(self, config: dict, programs: dict):
        self.programs = programs
        monitor_config = config.get("monitors", {}).get("hot_sheets", {})
        self.staleness_days = monitor_config.get("staleness_days", DEFAULT_STALENESS_DAYS)
        # Track previously-seen divergences for quiet logging
        self._known_divergences: set[str] = set()

    def check(self, graph_data: dict, scored_items: list[dict]) -> list:
        alerts = []

        for pid, program in self.programs.items():
            hs = program.get("hot_sheets_status")
            if not hs:
                continue

            hs_status = hs.get("status", "")
            scanner_status = program.get("ci_status", "")

            # Check staleness
            last_updated = hs.get("last_updated", "")
            if last_updated:
                try:
                    updated_dt = datetime.fromisoformat(last_updated)
                    days_old = (datetime.utcnow() - updated_dt).days
                    if days_old > self.staleness_days:
                        alerts.append(MonitorAlert(
                            monitor="hot_sheets",
                            severity="WARNING",
                            program_ids=[pid],
                            title=f"Stale Hot Sheets: {program['name']}",
                            detail=(
                                f"Hot Sheets position for {program['name']} was last "
                                f"updated {days_old} days ago ({last_updated}). "
                                f"Threshold: {self.staleness_days} days."
                            ),
                            metadata={"days_old": days_old, "threshold": self.staleness_days},
                        ))
                except (ValueError, TypeError):
                    pass

            # Check divergence
            if hs_status and scanner_status and hs_status != scanner_status:
                is_new = pid not in self._known_divergences
                self._known_divergences.add(pid)

                severity = "WARNING" if is_new else "INFO"
                alerts.append(MonitorAlert(
                    monitor="hot_sheets",
                    severity=severity,
                    program_ids=[pid],
                    title=f"Hot Sheets override: {program['name']}",
                    detail=(
                        f"Scanner CI status '{scanner_status}' diverges from "
                        f"Hot Sheets position '{hs_status}'. "
                        f"Hot Sheets takes precedence per policy. "
                        f"{'FIRST DETECTION - alerting prominently.' if is_new else 'Previously known divergence.'}"
                    ),
                    metadata={
                        "scanner_status": scanner_status,
                        "hot_sheets_status": hs_status,
                        "first_detection": is_new,
                        "override_applied": True,
                    },
                ))

                # Apply override (mutate in-memory program dict)
                program["original_ci_status"] = scanner_status
                program["ci_status"] = hs_status

        return alerts
```

### Example 4: Monitor Configuration in scanner_config.json

```json
{
  "monitors": {
    "iija_sunset": {
      "warning_days": 180,
      "critical_days": 90,
      "fy26_end": "2026-09-30"
    },
    "reconciliation": {
      "keywords": ["reconciliation", "repeal", "section 6417", "elective pay",
                    "IRA repeal", "direct pay termination"],
      "active_bill_statuses": ["introduced", "committee", "floor", "conference"]
    },
    "tribal_consultation": {
      "keywords": ["dear tribal leader", "DTLL", "tribal consultation",
                    "EO 13175", "Executive Order 13175", "consultation notice",
                    "government-to-government", "nation-to-nation",
                    "consent decree", "tribal consultation policy"],
      "agency_slugs": ["indian-affairs-bureau", "environmental-protection-agency",
                       "interior-department", "energy-department"]
    },
    "hot_sheets": {
      "staleness_days": 90
    },
    "dhs_funding": {
      "cr_expiration": "2026-02-13",
      "fema_program_ids": ["fema_bric", "fema_tribal_mitigation"],
      "warning_days": 14
    },
    "decision_engine": {
      "urgency_threshold_days": 30
    }
  }
}
```

### Example 5: Tribal Consultation Monitor Pattern Matching

```python
# Source: Federal Register API response fields + CONTEXT.md discretion areas
import re
import logging

logger = logging.getLogger(__name__)

# Tiered pattern matching for consultation signals
CONSULTATION_PATTERNS = {
    "DTLL": [
        re.compile(r"dear\s+tribal\s+leader", re.IGNORECASE),
        re.compile(r"\bDTLL\b"),
    ],
    "EO_13175": [
        re.compile(r"Executive\s+Order\s+13175", re.IGNORECASE),
        re.compile(r"EO\s+13175"),
        re.compile(r"consultation\s+and\s+coordination\s+with\s+indian\s+tribal", re.IGNORECASE),
    ],
    "CONSULTATION_NOTICE": [
        re.compile(r"tribal\s+consultation\s+(?:notice|meeting|session)", re.IGNORECASE),
        re.compile(r"government-to-government\s+consultation", re.IGNORECASE),
        re.compile(r"nation-to-nation\s+consultation", re.IGNORECASE),
    ],
}


class TribalConsultationMonitor:
    """MON-03: Detects DTLLs, consultation notices, EO 13175 signals."""

    def check(self, graph_data: dict, scored_items: list[dict]) -> list:
        alerts = []
        for item in scored_items:
            text = f"{item.get('title', '')} {item.get('abstract', '')} {item.get('action', '')}"
            for signal_type, patterns in CONSULTATION_PATTERNS.items():
                for pattern in patterns:
                    if pattern.search(text):
                        alerts.append(MonitorAlert(
                            monitor="tribal_consultation",
                            severity="INFO",
                            program_ids=item.get("matched_programs", []),
                            title=f"Consultation signal ({signal_type}): {item.get('title', '')[:80]}",
                            detail=f"Detected {signal_type} signal in {item.get('source', '')} item. "
                                   f"Source: {item.get('url', '')}",
                            metadata={
                                "signal_type": signal_type,
                                "source": item.get("source", ""),
                                "source_id": item.get("source_id", ""),
                                "url": item.get("url", ""),
                            },
                        ))
                        break  # One alert per signal type per item
        return alerts
```

## State of the Art

| Aspect | Current State | Phase 3 Target | What Changes |
|--------|--------------|----------------|-------------|
| Pipeline stages | Ingest -> Normalize -> Graph -> Analysis -> Report | Add Monitor + Decision stages between Graph and Report | New stage in `run_pipeline()` |
| Monitor capabilities | None | 5 monitors producing alerts | New `src/monitors/` package |
| Decision logic | None (advocacy_lever is static per-program text) | 5 rules classify each program into advocacy goal | New `src/analysis/decision_engine.py` |
| Hot Sheets integration | CI scores manually aligned per Phase 2 | Auto-override + divergence alerting + staleness checking | `hot_sheets_status` field in inventory |
| THREATENS edge type | Does not exist | Created by monitors, consumed by LOGIC-05 | New edge type in graph |
| Graph edge types | 7 types (AUTHORIZED_BY, FUNDED_BY, BLOCKED_BY, MITIGATED_BY, OBLIGATED_BY, ADVANCES, TRUST_OBLIGATION) | 8 types (add THREATENS) | String-based; minimal code change |
| Config structure | Sources, scoring, keywords only | Add `monitors` section with per-monitor config | JSON config addition |

**Key legislative facts informing monitor design:**
- IIJA expires September 30, 2026 (confirmed via FHWA, DOT official sites)
- OBBBA (Public Law 119-21) modified but did NOT repeal Section 6417; imposed construction deadlines
- DHS funded through February 13, 2026 via CR; full-year funding unresolved
- Federal Register API supports filtering by agency slug and document type for consultation detection

## Open Questions

1. **Hot Sheets divergence state persistence**
   - What we know: CONTEXT.md says first divergence alerts prominently, subsequent runs log silently.
   - What's unclear: Where to persist "previously seen divergences" between scan runs. Options: (a) add a field to `program_inventory.json`, (b) use a separate state file in `outputs/`, (c) infer from `LATEST-RESULTS.json` previous scan data.
   - Recommendation: Use a small state file `outputs/.monitor_state.json` that tracks known divergences by program_id. This follows the existing pattern of `outputs/.cfda_tracker.json` used by the zombie CFDA tracker in `base.py`.

2. **THREATENS edges -- ephemeral or persistent?**
   - What we know: Monitors add THREATENS edges to the graph. The graph is rebuilt from scratch each scan.
   - What's unclear: Should THREATENS edges be persisted in `graph_schema.json` or regenerated each scan?
   - Recommendation: Regenerate each scan. THREATENS edges are time-sensitive and their metadata (days_remaining) changes daily. Persisting them would create stale data. The monitors recalculate on every run.

3. **Programs that match multiple decision rules**
   - What we know: CONTEXT.md gives Claude discretion on priority ordering when multiple rules match.
   - What's unclear: Should we report only the highest-priority match, or all matches?
   - Recommendation: Report the highest-priority match as the primary `advocacy_goal`, but include a `secondary_rules` list in the classification output for transparency. This lets reporting show "Primary: Urgent Stabilization; also qualifies for: Protect Base."

4. **Reconciliation monitor scope post-OBBBA**
   - What we know: The OBBBA already passed and modified IRA credits. The existing `scanner_trigger_keywords` on IRS Elective Pay reference "reconciliation" and "IRA repeal."
   - What's unclear: Should the reconciliation monitor focus only on NEW bills that would further modify Section 6417, or also track the OBBBA's ongoing implementation?
   - Recommendation: Focus on NEW legislative actions. The OBBBA is enacted law; its effects are background context, not active threats. The monitor should detect new reconciliation bills or amendments that would go beyond the OBBBA's modifications (e.g., full repeal of Section 6417 elective pay for tribal entities).

5. **DHS CR expiration is already past research date**
   - What we know: DHS CR expires February 13, 2026. Today is February 9.
   - What's unclear: By the time this code is implemented, the DHS situation may have changed (new CR, full-year bill, or lapse).
   - Recommendation: Make the DHS CR expiration date a config value that can be updated. The monitor should also scan Congress.gov results for new DHS appropriations or CR bills to auto-detect date changes.

## Sources

### Primary (HIGH confidence)
- `F:\tcr-policy-scanner\src\main.py` -- pipeline orchestration flow (240 lines, read in full)
- `F:\tcr-policy-scanner\src\graph\builder.py` -- KnowledgeGraph class and GraphBuilder (399 lines, read in full)
- `F:\tcr-policy-scanner\src\graph\schema.py` -- node/edge dataclasses (126 lines, read in full)
- `F:\tcr-policy-scanner\src\analysis\relevance.py` -- scoring patterns (171 lines, read in full)
- `F:\tcr-policy-scanner\src\analysis\change_detector.py` -- state persistence pattern (91 lines, read in full)
- `F:\tcr-policy-scanner\src\scrapers\base.py` -- base scraper pattern + zombie CFDA tracker (152 lines, read in full)
- `F:\tcr-policy-scanner\src\scrapers\congress_gov.py` -- Congress.gov data model (158 lines, read in full)
- `F:\tcr-policy-scanner\src\scrapers\federal_register.py` -- FR data model (168 lines, read in full)
- `F:\tcr-policy-scanner\data\program_inventory.json` -- 16 programs with CI and status fields
- `F:\tcr-policy-scanner\data\graph_schema.json` -- 19 authorities (with durability), 13 barriers, 5 structural asks, trust super-node
- `F:\tcr-policy-scanner\data\policy_tracking.json` -- CI thresholds and status definitions
- `F:\tcr-policy-scanner\config\scanner_config.json` -- source configs and keyword lists
- `F:\tcr-policy-scanner\docs\STRATEGIC-FRAMEWORK.md` -- requirements and implementation checklist
- `F:\tcr-policy-scanner\.planning\phases\03-monitoring-logic\03-CONTEXT.md` -- user decisions on Hot Sheets handling

### Secondary (MEDIUM confidence)
- [IIJA expiration confirmed via FHWA](https://www.fhwa.dot.gov/infrastructure-investment-and-jobs-act/) -- "through September 30, 2026"
- [DHS CR through Feb 13 confirmed via CRFB](https://www.crfb.org/blogs/upcoming-congressional-fiscal-policy-deadlines) -- "Homeland Security accounts funded until February 13"
- [OBBBA IRA modifications confirmed via White & Case analysis](https://www.whitecase.com/insight-alert/amendments-to-ira-tax-credits-congressional-budget-bill-july-6) -- Section 6417 not repealed, construction deadlines modified
- [CRS analysis of IRA tax credit changes](https://www.congress.gov/crs-product/IN12625) -- reconciliation law reform details
- [EO 13175 consultation requirements via EPA](https://www.epa.gov/laws-regulations/summary-executive-order-13175-consultation-and-coordination-indian-tribal) -- consultation framework reference
- [python-dateutil relativedelta docs](https://dateutil.readthedocs.io/en/stable/relativedelta.html) -- date arithmetic capabilities

### Tertiary (LOW confidence)
- Web search results for Python rule engine patterns -- confirmed that external rule engines are unnecessary for 5 rules; simple functions recommended
- Web search for Federal Register API tribal consultation filtering -- no dedicated tribal consultation filter exists; must use keyword search with agency slugs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- entirely brownfield; all files read, all patterns understood
- Architecture: HIGH -- monitor interface pattern derived from existing scraper pattern; pipeline insertion point is clear
- Decision rules: HIGH -- requirements are explicit (5 rules with clear conditions); graph query patterns verified against existing code
- Monitor implementations: HIGH for IIJA/Hot Sheets/DHS (clear data sources); MEDIUM for reconciliation (OBBBA complicates detection scope); MEDIUM for Tribal consultation (pattern matching breadth is subjective)
- Legislative context: MEDIUM -- verified IIJA expiration and OBBBA impact via multiple sources; DHS situation is fluid

**Research date:** 2026-02-09
**Valid until:** 2026-03-09 (stable codebase; DHS funding situation may change sooner)
