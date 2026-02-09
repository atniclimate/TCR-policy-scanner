# Phase 4: Report Enhancements - Research

**Researched:** 2026-02-09
**Domain:** Brownfield Python codebase -- enhancing Markdown report generator to consume monitor/decision engine outputs from Phase 3
**Confidence:** HIGH

## Summary

This research investigates how to enhance the existing `src/reports/generator.py` to surface the monitoring data, decision engine classifications, and structural advocacy intelligence produced by Phase 3 in the `LATEST-BRIEFING.md` output. Phase 4 is a pure reporting phase -- it reads data structures that already exist (`outputs/LATEST-MONITOR-DATA.json`, `graph_data` dict, program inventory with `hot_sheets_status`) and formats them into new briefing sections.

The existing report generator (`ReportGenerator` class, 288 lines) uses plain Python string concatenation (`"\n".join(lines)`) to build Markdown. It already has sections for Executive Summary, New Developments, Critical Program Updates, Confidence Index Dashboard, Barriers & Mitigation Pathways, Statutory Authority Map, and Active Advocacy Levers. Phase 4 adds six new sections/indicators: (1) Five Structural Asks mapped to barriers, (2) Hot Sheets sync indicator per program, (3) IIJA Sunset Countdown, (4) Historical CI trend tracking, (5) Reconciliation Watch, and (6) Advocacy goal classification display. All data sources for these sections already exist in the pipeline output.

The critical architectural question is how to get monitor data and classifications into the report generator. Currently, `run_pipeline()` in `src/main.py` calls `reporter.generate(scored, changes, graph_data)` but does NOT pass `monitor_data` or `classifications`. The `generate()` method signature must be extended to accept these. The graph_data dict already contains structural asks (ADVANCES edges, AdvocacyLeverNode entries for `ask_*` IDs) and THREATENS edges from monitors. The `outputs/LATEST-MONITOR-DATA.json` contains alerts and per-program classifications. The `program_inventory.json` has `hot_sheets_status` per program which is already loaded into the in-memory programs dict.

**Primary recommendation:** Extend `ReportGenerator.generate()` to accept `monitor_data` and `classifications` dicts. Add six new `_format_*` methods (one per new section). Modify `_build_markdown()` to call these methods at the appropriate positions in the briefing. Add a CI history tracker (`outputs/.ci_history.json`) that appends per-scan CI snapshots for RPT-04 trend tracking.

## Standard Stack

This is a brownfield project. The "standard stack" is the existing codebase. No new external dependencies needed.

### Core Files to Modify

| File | What Changes | Requirements |
|------|-------------|-------------|
| `src/reports/generator.py` | Add 6 new sections to `_build_markdown()`, extend `generate()` signature | RPT-01 through RPT-06 |
| `src/main.py` | Pass `monitor_data` and `classifications` to `reporter.generate()` | All RPT-* (pipeline wiring) |

### Core Files to Create

| File | Purpose | Requirements |
|------|---------|-------------|
| `outputs/.ci_history.json` | Append-only CI score snapshots per scan | RPT-04 |

### Supporting Files (Read-Only Consumers)

| File | What It Provides | Used By |
|------|-----------------|---------|
| `outputs/LATEST-MONITOR-DATA.json` | Alerts, classifications, summary | RPT-02, RPT-03, RPT-05, RPT-06 |
| `data/graph_schema.json` | Five Structural Asks (`structural_asks[]`) | RPT-01 |
| `outputs/LATEST-GRAPH.json` | ADVANCES edges, THREATENS edges, AdvocacyLeverNodes | RPT-01, RPT-03 |
| `data/program_inventory.json` | `hot_sheets_status` per program | RPT-02 |

### No New Dependencies

All new reporting logic uses standard library (`datetime`, `json`, `pathlib`, `logging`). Jinja2 is in `requirements.txt` but is NOT currently used by the report generator. The existing pattern is plain string concatenation, and maintaining consistency with the existing codebase is more important than switching to a templating library for 6 new sections.

**Installation:** No changes to `requirements.txt`.

## Architecture Patterns

### Current Report Generator Structure

```
src/reports/generator.py
  ReportGenerator
    __init__(programs)
    generate(scored_items, changes, graph_data) -> dict
    _build_markdown(items, changes, timestamp, graph_data) -> str
    _build_json(items, changes, timestamp, graph_data) -> dict
    _format_graph_barriers(graph_data) -> list[str]
    _format_graph_authorities(graph_data) -> list[str]
    _format_item(item, is_new) -> list[str]
    _format_item_brief(item) -> list[str]
```

### Extended Structure (Phase 4)

```
src/reports/generator.py
  ReportGenerator
    __init__(programs)
    generate(scored_items, changes, graph_data,
             monitor_data=None, classifications=None) -> dict   # EXTENDED
    _build_markdown(..., monitor_data, classifications) -> str   # EXTENDED
    _build_json(..., monitor_data, classifications) -> dict      # EXTENDED

    # Existing formatting methods (unchanged)
    _format_graph_barriers(graph_data) -> list[str]
    _format_graph_authorities(graph_data) -> list[str]
    _format_item(item, is_new) -> list[str]
    _format_item_brief(item) -> list[str]

    # NEW formatting methods (Phase 4)
    _format_structural_asks(graph_data) -> list[str]             # RPT-01
    _format_hot_sheets_indicator() -> list[str]                  # RPT-02
    _format_iija_countdown(monitor_data) -> list[str]            # RPT-03
    _format_ci_trends(ci_history) -> list[str]                   # RPT-04
    _format_reconciliation_watch(monitor_data) -> list[str]      # RPT-05
    _format_advocacy_goals(classifications) -> list[str]         # RPT-06
    _save_ci_snapshot(timestamp) -> None                         # RPT-04 helper
    _load_ci_history() -> list[dict]                             # RPT-04 helper
```

### Pattern 1: Extending generate() Signature (Backward Compatible)

**What:** The `generate()` and `_build_markdown()` methods get new optional parameters so existing callers (if any) are not broken.
**When to use:** Modifying `src/reports/generator.py` and `src/main.py`.

```python
# Source: Existing src/reports/generator.py line 28-48
def generate(self, scored_items: list[dict], changes: dict,
             graph_data: dict | None = None,
             monitor_data: dict | None = None,          # NEW
             classifications: dict | None = None) -> dict:  # NEW
    """Generate both Markdown and JSON reports."""
    timestamp = datetime.utcnow().strftime("%Y-%m-%d")

    # NEW: Save CI snapshot for historical tracking before generating
    self._save_ci_snapshot(timestamp)
    ci_history = self._load_ci_history()

    md_content = self._build_markdown(
        scored_items, changes, timestamp, graph_data,
        monitor_data, classifications, ci_history
    )
    # ...
```

### Pattern 2: Pipeline Wiring in main.py

**What:** Pass monitor outputs to report generator. Currently `reporter.generate(scored, changes, graph_data)` -- needs `monitor_data` and `classifications` added.
**When to use:** Modifying `src/main.py` `run_pipeline()`.
**Source:** Existing `src/main.py` lines 257-259.

```python
# Current (line 257-259):
reporter = ReportGenerator(programs)
paths = reporter.generate(scored, changes, graph_data)

# Phase 4 target:
reporter = ReportGenerator(programs)
paths = reporter.generate(
    scored, changes, graph_data,
    monitor_data=monitor_data,
    classifications=classifications,
)
```

### Pattern 3: Section Ordering in Briefing

**What:** New sections are inserted at semantically appropriate positions in the briefing, not appended at the end. The Markdown briefing should flow: header -> executive summary -> urgent items -> structural analysis -> status indicators -> historical data -> detailed items.
**When to use:** `_build_markdown()` method.

Recommended section order for the complete briefing:

```
1. Header (scan date, items count, graph stats)
2. Executive Summary
3. NEW: Reconciliation Watch (RPT-05) -- urgent, above the fold
4. NEW: IIJA Sunset Countdown (RPT-03) -- time-sensitive
5. New Developments
6. Critical Program Updates
7. Confidence Index Dashboard
   - With Hot Sheets sync indicator (RPT-02) integrated per row
8. FLAGGED programs detail
9. NEW: Advocacy Goal Classifications (RPT-06) -- per program
10. NEW: Five Structural Asks (RPT-01) -- strategic context
11. Barriers & Mitigation Pathways (existing)
12. Statutory Authority Map (existing)
13. Active Advocacy Levers (existing)
14. NEW: CI Trend History (RPT-04) -- reference data
15. All Relevant Items (existing)
16. Footer
```

### Pattern 4: Data Access Patterns for Each New Section

**RPT-01 (Five Structural Asks):** Query `graph_data["nodes"]` for nodes where `_type == "AdvocacyLeverNode"` and `id` starts with `ask_`. Cross-reference `graph_data["edges"]` for `ADVANCES` edges (ask -> program) and `MITIGATED_BY` edges (barrier -> ask). The `data/graph_schema.json` has 5 structural asks with `id`, `name`, `description`, `target`, `urgency`, `mitigates[]`, and `programs[]`.

**RPT-02 (Hot Sheets Indicator):** Read `self.programs[pid].get("hot_sheets_status")` for each program. Compare `hot_sheets_status.status` against `ci_status`. Display as a column in the CI Dashboard table or as an inline badge. Also check `monitor_data["alerts"]` for `monitor == "hot_sheets"` alerts to surface active divergences.

**RPT-03 (IIJA Countdown):** Filter `monitor_data["alerts"]` for alerts where `monitor == "iija_sunset"`. Extract `metadata.days_remaining`, `metadata.deadline`, `metadata.threat_type`. Display as a countdown table with color-coded urgency.

**RPT-04 (CI Trends):** No existing history infrastructure. Must create `outputs/.ci_history.json` as an append-only JSON file storing `{timestamp, programs: {pid: {ci, status}}}` per scan. On each `generate()` call, append the current snapshot. Then read the full history and render a text-based trend line (ASCII sparklines or simple delta indicators like arrows/plus-minus).

**RPT-05 (Reconciliation Watch):** Filter `monitor_data["alerts"]` for `monitor == "reconciliation"`. If no alerts, show "No active reconciliation threats detected." If alerts exist, format bill details with urgency. Also check `monitor_data["classifications"]` for programs classified as `URGENT_STABILIZATION` with `threat_type == "reconciliation"`.

**RPT-06 (Advocacy Goals):** Read `classifications` dict (keyed by program_id). Each entry has `advocacy_goal`, `goal_label`, `rule`, `confidence`, `reason`, `secondary_rules[]`. Render as a table mapping each program to its primary advocacy goal with the rule reference and confidence level.

### Pattern 5: CI History Persistence

**What:** Append-only JSON file that grows across scan cycles, one entry per scan date.
**When to use:** RPT-04 implementation.
**Source:** Follows existing cache/state persistence patterns from `outputs/.monitor_state.json` and `outputs/.cfda_tracker.json`.

```python
CI_HISTORY_PATH = Path("outputs/.ci_history.json")

def _save_ci_snapshot(self, timestamp: str) -> None:
    """Append current CI scores to history file."""
    snapshot = {
        "timestamp": timestamp,
        "programs": {
            pid: {
                "ci": prog.get("confidence_index"),
                "status": prog.get("ci_status"),
            }
            for pid, prog in self.programs.items()
        },
    }
    history = self._load_ci_history()
    # Only append if this timestamp is new (avoid duplicates on re-runs)
    existing_timestamps = {h["timestamp"] for h in history}
    if timestamp not in existing_timestamps:
        history.append(snapshot)
    # Write back
    CI_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CI_HISTORY_PATH, "w") as f:
        json.dump(history, f, indent=2)

def _load_ci_history(self) -> list[dict]:
    """Load CI history from file."""
    if not CI_HISTORY_PATH.exists():
        return []
    try:
        with open(CI_HISTORY_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
```

### Pattern 6: Markdown Rendering Conventions

**What:** All sections follow the existing Markdown conventions established in the report generator.
**Source:** Existing `_format_graph_barriers()` and CI Dashboard formatting in `generator.py`.

Conventions to follow:
- Section headers use `##` (H2) for major sections, `###` (H3) for subsections
- Tables use standard Markdown pipe syntax with alignment
- Badges/indicators use `**[BADGE]**` inline bold syntax
- Status colors expressed as words (not emoji): `CRITICAL`, `WARNING`, `INFO`
- Programs referenced by name, not ID
- Percentages for CI scores: `{ci * 100:.0f}%`
- Days remaining as integer with units: `4 days`

### Anti-Patterns to Avoid

- **Switching to Jinja2 templates:** Although Jinja2 is in `requirements.txt`, the existing report generator does not use it. Mixing two rendering approaches (some sections string-concatenated, some Jinja2-templated) creates inconsistency. Stay with the existing `list[str]` + `"\n".join()` pattern.
- **Making API calls from the report generator:** The generator is a pure formatter. All data must be passed in through `generate()` parameters. Do not load files or call APIs from formatting methods (exception: CI history file read/write which is a local persistence pattern, not an API call).
- **Creating separate report files per section:** Phase 4 enhances `LATEST-BRIEFING.md`, not creates separate files. All new sections go into the same briefing. The JSON output (`LATEST-RESULTS.json`) should also be enhanced to include the new data.
- **Removing existing sections:** All existing sections (Executive Summary, CI Dashboard, Barriers, Authorities, Advocacy Levers, All Items) remain. New sections are additive.
- **Hard-coding monitor names:** Use constants or check `alert.get("monitor")` strings rather than hardcoding monitor class names. This allows future monitors to be added without modifying reporting code.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Markdown table generation | Custom table builder class | Continue existing inline `f"| {col} | {col} |"` pattern | 6 new tables is not enough to justify abstraction; consistency with 4 existing tables |
| CI trend visualization | ASCII chart library (plotext, asciichart) | Simple delta indicators (`+3%`, `-5%`, `--`, arrow text) | Markdown output must render in any viewer; ASCII charts break in many renderers |
| Date formatting | Custom date format logic | `datetime.strftime()` already used throughout | Consistent with existing `timestamp` usage |
| Section conditional rendering | Complex template engine | Simple `if data:` guards before each section | Follows existing pattern: `if ci_programs:`, `if graph_data:`, `if critical_items:` |
| Monitor data filtering | Generic query builder | List comprehensions: `[a for a in alerts if a.get("monitor") == "iija_sunset"]` | Data is small (5 alerts typical); linear scan is instant |
| Sparkline/trend rendering | External library | Text-based: `12% -> 12% -> 12%` or `STABLE (3 scans)` | Must work in plain Markdown; no image generation |

**Key insight:** Phase 4 is pure data formatting. All intelligence is already computed by Phase 3 monitors and decision engine. The report generator just needs to read the right data structures and format them into readable Markdown sections.

## Common Pitfalls

### Pitfall 1: monitor_data Not Passed to ReportGenerator

**What goes wrong:** New sections render empty because `monitor_data` is `None` -- the pipeline wiring in `main.py` was not updated.
**Why it happens:** `generate()` is called with positional args and the new params have defaults of `None`.
**How to avoid:** Update `run_pipeline()` in `main.py` to explicitly pass `monitor_data=monitor_data, classifications=classifications` as keyword arguments. Add a guard in `_build_markdown()` that logs a warning if monitor_data is None.
**Warning signs:** Briefing generates without errors but IIJA countdown, Reconciliation Watch, and Advocacy Goals sections are missing.

### Pitfall 2: Structural Asks Not in graph_data

**What goes wrong:** RPT-01 section shows no structural asks because the code looks for them in the wrong place.
**Why it happens:** The structural asks are seeded from `data/graph_schema.json` into the graph as AdvocacyLeverNode entries with IDs starting with `ask_`. They connect to programs via ADVANCES edges and to barriers via MITIGATED_BY edges. The report must query `graph_data["nodes"]` for `_type == "AdvocacyLeverNode"` with `id.startswith("ask_")`, NOT look in `graph_schema.json` directly.
**How to avoid:** Query the serialized graph_data dict (which was already built by GraphBuilder and contains all structural asks). Filter by `id.startswith("ask_")` to distinguish structural asks from per-program advocacy levers (which have `id` starting with `lever_`).
**Warning signs:** Five Structural Asks section shows program-level levers instead of the 5 strategic asks.

### Pitfall 3: CI History File Grows Without Bounds

**What goes wrong:** After months of daily scans, `.ci_history.json` becomes very large (365 entries x 16 programs = manageable, but the file should still have a cap).
**Why it happens:** Append-only file with no pruning.
**How to avoid:** Cap history to the last 90 entries (roughly 3 months of daily scans). On each save, if history exceeds 90 entries, trim the oldest. This provides ample trend data while keeping the file small.
**Warning signs:** `.ci_history.json` exceeds 1MB after extended operation.

### Pitfall 4: Hot Sheets Indicator Shows Stale Override Data

**What goes wrong:** The Hot Sheets indicator shows "aligned" for all programs because the HotSheetsValidator already overrode `ci_status` to match `hot_sheets_status` before the report runs.
**Why it happens:** HotSheetsValidator runs FIRST in the monitor chain and mutates the program dict in-place, setting `program["ci_status"] = hot_sheets_status`. By the time the report runs, the two values are identical.
**How to avoid:** The HotSheetsValidator stores the original value in `program["original_ci_status"]` before overriding. The report should check for `original_ci_status`: if present, the program had a divergence. Also check `monitor_data["alerts"]` for `hot_sheets` alerts with `check_type == "divergence"` to surface the divergence information.
**Warning signs:** Hot Sheets indicator shows 100% alignment when divergences actually occurred during the scan.

### Pitfall 5: Duplicate Information Across Sections

**What goes wrong:** The same program's IIJA sunset countdown appears in: (a) IIJA Countdown section, (b) Reconciliation Watch, (c) Advocacy Goals as "Urgent Stabilization", (d) Barriers section, and (e) existing CI Dashboard. The reader gets information overload.
**Why it happens:** Multiple sections independently pull from the same data sources.
**How to avoid:** Each section has a distinct purpose. Use cross-references ("see IIJA Countdown above") rather than duplicating details. The IIJA section shows the countdown; the Advocacy Goals section shows the classification; the CI Dashboard shows the score. Brief cross-references keep sections focused.
**Warning signs:** Briefing is excessively long with repetitive information per program.

### Pitfall 6: Programs With No Classification Clutter the Advocacy Goals Table

**What goes wrong:** The Advocacy Goals table has 16 rows, 14 of which say "No rule matched" with LOW confidence, making the 2 classified programs hard to find.
**Why it happens:** Displaying all programs including those with no advocacy goal classification.
**How to avoid:** Split the table: show classified programs first (with advocacy goal), then show unclassified programs in a separate compact list or omit them. Use the `advocacy_goal is not None` filter. Optionally, group by advocacy goal.
**Warning signs:** Advocacy Goals section is dominated by "No match" rows.

### Pitfall 7: Reconciliation Watch Shows Nothing When No Threats Detected

**What goes wrong:** The Reconciliation Watch section is completely absent when there are no reconciliation alerts, but users expect to see a reassuring "No active threats."
**Why it happens:** The section is conditionally rendered only when alerts exist (following the existing pattern of `if critical_items:`).
**How to avoid:** Reconciliation Watch should ALWAYS render, even when empty. "No active reconciliation threats detected" is valuable information for Tribal leaders preparing for Congressional meetings. Same applies to IIJA Countdown (always show countdowns even at INFO level).
**Warning signs:** Users ask "what about reconciliation?" because the section vanished from the briefing.

## Code Examples

### Example 1: Five Structural Asks Section (RPT-01)

```python
# Source: Existing graph_data structure from src/graph/builder.py _seed_structural_asks()
def _format_structural_asks(self, graph_data: dict) -> list[str]:
    """Format Five Structural Asks mapped to barriers and programs."""
    if not graph_data:
        return []

    nodes = graph_data.get("nodes", {})
    edges = graph_data.get("edges", [])

    # Find structural ask nodes (id starts with "ask_")
    asks = {
        nid: n for nid, n in nodes.items()
        if n.get("_type") == "AdvocacyLeverNode" and nid.startswith("ask_")
    }
    if not asks:
        return []

    lines = [
        "## Five Structural Asks",
        "",
    ]

    for ask_id, ask in sorted(asks.items()):
        name = ask.get("description", ask_id)
        urgency = ask.get("urgency", "")
        target = ask.get("target", "")

        # Find programs this ask ADVANCES
        program_ids = [
            e["target"] for e in edges
            if e["source"] == ask_id and e["type"] == "ADVANCES"
        ]
        program_names = []
        for pid in program_ids:
            prog = self.programs.get(pid)
            if prog:
                program_names.append(prog["name"])

        # Find barriers this ask mitigates
        barrier_ids = [
            e["source"] for e in edges
            if e["target"] == ask_id and e["type"] == "MITIGATED_BY"
        ]
        barrier_descs = []
        for bid in barrier_ids:
            bar = nodes.get(bid, {})
            if bar:
                barrier_descs.append(bar.get("description", bid))

        urgency_badge = f" [{urgency}]" if urgency else ""
        lines.append(f"### {name}{urgency_badge}")
        lines.append(f"**Target:** {target}")
        if program_names:
            lines.append(f"**Programs:** {', '.join(program_names)}")
        if barrier_descs:
            lines.append(f"**Mitigates:**")
            for bd in barrier_descs:
                lines.append(f"- {bd}")
        lines.append("")

    return lines
```

### Example 2: Hot Sheets Sync Indicator (RPT-02)

```python
# Source: Existing CI Dashboard in generator.py lines 102-128
# Integrated as a column in the CI Dashboard table
def _format_ci_dashboard_with_hot_sheets(self) -> list[str]:
    """Enhanced CI Dashboard with Hot Sheets sync indicator."""
    ci_programs = [p for p in self.programs.values() if "confidence_index" in p]
    if not ci_programs:
        return []

    lines = [
        "## Confidence Index Dashboard",
        "",
        "| Program | CI | Status | Hot Sheets | Determination |",
        "|---------|---:|--------|:----------:|--------------|",
    ]

    for prog in sorted(ci_programs, key=lambda p: p.get("confidence_index", 0)):
        ci = prog.get("confidence_index", 0)
        status = prog.get("ci_status", "N/A")
        det = prog.get("ci_determination", "")[:70]
        ci_pct = f"{ci * 100:.0f}%"

        # Hot Sheets sync indicator
        hs = prog.get("hot_sheets_status")
        if hs:
            hs_status = hs.get("status", "")
            original = prog.get("original_ci_status")
            if original and original != hs_status:
                hs_badge = f"OVERRIDE ({original}->{hs_status})"
            elif hs_status == status:
                hs_badge = "ALIGNED"
            else:
                hs_badge = f"DIVERGED ({hs_status})"
        else:
            hs_badge = "--"

        lines.append(f"| {prog['name']} | {ci_pct} | {status} | {hs_badge} | {det} |")

    lines.append("")
    return lines
```

### Example 3: IIJA Sunset Countdown (RPT-03)

```python
# Source: monitor_data alerts from src/monitors/iija_sunset.py
def _format_iija_countdown(self, monitor_data: dict | None) -> list[str]:
    """Format IIJA sunset countdown table."""
    lines = [
        "## IIJA Sunset Countdown",
        "",
    ]

    if not monitor_data:
        lines.append("*No monitor data available.*")
        lines.append("")
        return lines

    iija_alerts = [
        a for a in monitor_data.get("alerts", [])
        if a.get("monitor") == "iija_sunset"
    ]

    if not iija_alerts:
        lines.append("No IIJA-funded programs currently tracked.")
        lines.append("")
        return lines

    lines.append("| Program | Deadline | Days Remaining | Severity | Type |")
    lines.append("|---------|----------|---------------:|----------|------|")

    for alert in sorted(iija_alerts, key=lambda a: a.get("metadata", {}).get("days_remaining") or 9999):
        meta = alert.get("metadata", {})
        program_names = [
            self.programs.get(pid, {}).get("name", pid)
            for pid in alert.get("program_ids", [])
        ]
        name = ", ".join(program_names)
        deadline = meta.get("deadline", "N/A")
        days = meta.get("days_remaining")
        days_str = str(days) if days is not None else "N/A"
        severity = alert.get("severity", "INFO")
        threat_type = meta.get("threat_type", "sunset")

        lines.append(f"| {name} | {deadline} | {days_str} | {severity} | {threat_type} |")

    lines.append("")
    return lines
```

### Example 4: Reconciliation Watch (RPT-05)

```python
# Source: monitor_data alerts from src/monitors/reconciliation.py
def _format_reconciliation_watch(self, monitor_data: dict | None) -> list[str]:
    """Format Reconciliation Watch section. Always renders."""
    lines = [
        "## Reconciliation Watch",
        "",
    ]

    if not monitor_data:
        lines.append("*No monitor data available.*")
        lines.append("")
        return lines

    recon_alerts = [
        a for a in monitor_data.get("alerts", [])
        if a.get("monitor") == "reconciliation"
    ]

    if not recon_alerts:
        lines.append("No active reconciliation threats detected in current scan.")
        lines.append("")
        return lines

    for alert in recon_alerts:
        meta = alert.get("metadata", {})
        lines.append(f"**{alert.get('severity', 'WARNING')}:** {alert.get('title', '')}")
        lines.append("")
        lines.append(f"> {alert.get('detail', '')}")
        if meta.get("matched_keywords"):
            lines.append(f"> Keywords: {', '.join(meta['matched_keywords'])}")
        lines.append("")

    return lines
```

### Example 5: Advocacy Goal Classifications (RPT-06)

```python
# Source: classifications dict from src/analysis/decision_engine.py
def _format_advocacy_goals(self, classifications: dict | None) -> list[str]:
    """Format advocacy goal classifications per program."""
    if not classifications:
        return []

    # Separate classified from unclassified
    classified = {
        pid: c for pid, c in classifications.items()
        if c.get("advocacy_goal") is not None
    }

    if not classified:
        return []

    lines = [
        "## Advocacy Goal Classifications",
        "",
        "| Program | Advocacy Goal | Rule | Confidence | Reason |",
        "|---------|--------------|------|-----------|--------|",
    ]

    for pid, c in sorted(classified.items(),
                         key=lambda x: x[1].get("rule", "Z")):
        prog = self.programs.get(pid)
        name = prog["name"] if prog else pid
        goal = c.get("goal_label", "--")
        rule = c.get("rule", "--")
        conf = c.get("confidence", "--")
        reason = c.get("reason", "")[:80]
        lines.append(f"| {name} | {goal} | {rule} | {conf} | {reason} |")

    # Unclassified summary
    unclassified = [
        pid for pid, c in classifications.items()
        if c.get("advocacy_goal") is None
    ]
    if unclassified:
        lines.append("")
        names = [self.programs.get(pid, {}).get("name", pid) for pid in unclassified]
        lines.append(f"*{len(unclassified)} programs unclassified:* {', '.join(names)}")

    lines.append("")
    return lines
```

### Example 6: CI Trend History (RPT-04)

```python
# Source: outputs/.ci_history.json append-only file
def _format_ci_trends(self, ci_history: list[dict]) -> list[str]:
    """Format CI score trajectory table showing trends across scans."""
    if len(ci_history) < 2:
        lines = [
            "## CI Score Trends",
            "",
            f"*Trend data requires at least 2 scan cycles. Current: {len(ci_history)} scan(s).*",
            "",
        ]
        return lines

    lines = [
        "## CI Score Trends",
        "",
    ]

    # Show last 10 scans max
    recent = ci_history[-10:]
    dates = [h["timestamp"] for h in recent]

    lines.append(f"*Tracking {len(ci_history)} scan(s). Showing last {len(recent)}.*")
    lines.append("")

    # Table header
    header = "| Program | " + " | ".join(dates) + " | Trend |"
    separator = "|---------|" + "|".join(["-----:" for _ in dates]) + "|-------|"
    lines.append(header)
    lines.append(separator)

    # Get all program IDs from latest scan
    latest_pids = recent[-1].get("programs", {}).keys()
    for pid in sorted(latest_pids):
        prog = self.programs.get(pid)
        name = prog["name"] if prog else pid
        scores = []
        for h in recent:
            ci = h.get("programs", {}).get(pid, {}).get("ci")
            scores.append(f"{ci * 100:.0f}%" if ci is not None else "--")

        # Calculate trend indicator
        first_ci = recent[0].get("programs", {}).get(pid, {}).get("ci")
        last_ci = recent[-1].get("programs", {}).get(pid, {}).get("ci")
        if first_ci is not None and last_ci is not None:
            delta = last_ci - first_ci
            if delta > 0.02:
                trend = f"+{delta * 100:.0f}%"
            elif delta < -0.02:
                trend = f"{delta * 100:.0f}%"
            else:
                trend = "STABLE"
        else:
            trend = "--"

        row = f"| {name} | " + " | ".join(scores) + f" | {trend} |"
        lines.append(row)

    lines.append("")
    return lines
```

## State of the Art

| Aspect | Current State (Post Phase 3) | Phase 4 Target | What Changes |
|--------|------------------------------|----------------|-------------|
| Briefing sections | 7 sections | 13 sections (add 6 new) | New sections in `_build_markdown()` |
| `generate()` params | `scored_items, changes, graph_data` | Add `monitor_data, classifications` | Backward-compatible signature extension |
| CI tracking | Single-point snapshot only | Append-only history file + trend table | New `.ci_history.json` persistence |
| Hot Sheets visibility | HotSheetsValidator runs silently | Inline indicator in CI Dashboard | New column in dashboard table |
| Structural asks | In graph as nodes/edges, not in briefing | Dedicated briefing section | New `_format_structural_asks()` |
| IIJA countdown | Alerts in `LATEST-MONITOR-DATA.json` only | Visual countdown table in briefing | New `_format_iija_countdown()` |
| Reconciliation | Alerts in `LATEST-MONITOR-DATA.json` only | Dedicated watch section in briefing | New `_format_reconciliation_watch()` |
| Advocacy goals | Classifications in `LATEST-MONITOR-DATA.json` only | Table in briefing per program | New `_format_advocacy_goals()` |
| JSON output | `scan_date, summary, scan_results, changes, knowledge_graph` | Add `monitor_data, classifications, ci_history` | Extended `_build_json()` |

## Open Questions

1. **CI History file location and gitignoring**
   - What we know: History file should be at `outputs/.ci_history.json` following the `.monitor_state.json` pattern. The dot prefix conventionally hides it.
   - What's unclear: Should this file be gitignored? It grows over time and is machine-specific.
   - Recommendation: Do NOT gitignore -- it is valuable operational data. Cap at 90 entries to keep file small. Archive is already git-tracked (the `outputs/archive/` directory has archived briefings).

2. **CI Dashboard table width with Hot Sheets column**
   - What we know: The current CI Dashboard table has 4 columns. Adding Hot Sheets makes 5. The Determination column is already truncated to 80 chars.
   - What's unclear: Whether the 5-column table renders well in narrow Markdown viewers.
   - Recommendation: Shorten Determination truncation from 80 to 70 chars. Use short Hot Sheets badges: "ALIGNED", "OVERRIDE", "DIVERGED", "--". This keeps the table compact.

3. **Trend table readability with 16 programs and 10 date columns**
   - What we know: A 16-row by 10-column trend table is wide.
   - What's unclear: Whether this renders well in Markdown.
   - Recommendation: Group by CI status tier (FLAGGED/AT_RISK/UNCERTAIN first, then STABLE/SECURE). Only show programs where CI actually changed. If no changes across the history window, show a summary line instead of individual rows. This keeps the table focused.

4. **Section ordering relative to existing briefing flow**
   - What we know: The existing briefing puts Executive Summary first, then items, then CI Dashboard, then graph analysis.
   - What's unclear: Exact placement of new sections relative to existing ones.
   - Recommendation: Urgent/time-sensitive sections (Reconciliation Watch, IIJA Countdown) go right after Executive Summary. Analytical sections (Advocacy Goals, Structural Asks) go after CI Dashboard and before the detailed item lists. CI Trends go near the end as reference data.

## Sources

### Primary (HIGH confidence)
- `F:/tcr-policy-scanner/src/reports/generator.py` -- complete report generator code (288 lines, read in full)
- `F:/tcr-policy-scanner/src/main.py` -- pipeline orchestration showing how reporter is called (317 lines, read in full)
- `F:/tcr-policy-scanner/src/analysis/decision_engine.py` -- classification output structure (384 lines, read in full)
- `F:/tcr-policy-scanner/src/monitors/__init__.py` -- MonitorAlert dataclass, MonitorRunner (250 lines, read in full)
- `F:/tcr-policy-scanner/src/monitors/hot_sheets.py` -- Hot Sheets validator showing override mechanics (183 lines, read in full)
- `F:/tcr-policy-scanner/src/monitors/iija_sunset.py` -- IIJA sunset alert format (181 lines, read in full)
- `F:/tcr-policy-scanner/src/monitors/reconciliation.py` -- Reconciliation alert format (158 lines, read in full)
- `F:/tcr-policy-scanner/src/graph/builder.py` -- structural asks seeding via `_seed_structural_asks()` (399 lines, read in full)
- `F:/tcr-policy-scanner/src/graph/schema.py` -- node/edge type definitions (127 lines, read in full)
- `F:/tcr-policy-scanner/data/graph_schema.json` -- 5 structural asks data with programs/mitigates/urgency (370 lines, read in full)
- `F:/tcr-policy-scanner/data/program_inventory.json` -- program entries with hot_sheets_status field (read first 100 lines)
- `F:/tcr-policy-scanner/outputs/LATEST-MONITOR-DATA.json` -- actual monitor output: 5 alerts, 16 classifications (232 lines, read in full)
- `F:/tcr-policy-scanner/outputs/LATEST-BRIEFING.md` -- current briefing format (602 lines, read in full)
- `F:/tcr-policy-scanner/config/scanner_config.json` -- monitor configuration (131 lines, read in full)
- `F:/tcr-policy-scanner/outputs/LATEST-GRAPH.json` -- graph data structure (read first 50 lines)
- `F:/tcr-policy-scanner/.planning/phases/03-monitoring-logic/03-RESEARCH.md` -- Phase 3 research with upstream patterns

### Secondary (MEDIUM confidence)
- `F:/tcr-policy-scanner/src/analysis/change_detector.py` -- cache persistence pattern (91 lines, read in full)
- `F:/tcr-policy-scanner/requirements.txt` -- confirms Jinja2 available but unused

### Tertiary (LOW confidence)
- None -- this phase is entirely codebase-internal; no external library research needed

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- entirely brownfield; all source files read, all data structures verified against actual output
- Architecture: HIGH -- new sections follow exact same patterns as existing sections; pipeline wiring change is minimal (2 keyword args added to one function call)
- Data access patterns: HIGH -- all data sources (monitor_data, classifications, graph_data structural asks, hot_sheets_status) verified to exist with known structures from actual `LATEST-MONITOR-DATA.json` and `LATEST-GRAPH.json` outputs
- CI history tracking: MEDIUM -- new persistence mechanism; follows existing `.monitor_state.json` pattern but is untested; file growth management is an estimate
- Pitfalls: HIGH -- pitfalls derived from actual code analysis (Hot Sheets override mechanics, structural ask node identification, empty section rendering)

**Research date:** 2026-02-09
**Valid until:** 2026-03-09 (stable codebase; report format is internal so no external dependency drift)
