# Phase 8: Assembly, Polish, and Web Distribution — Master Plan

> **Status:** Active prompt for Phase 8 execution
> **Created:** 2026-02-10
> **Corrections applied:** Line references verified against actual source code

## Context

Phase 8 completes TCR Policy Scanner v1.1. Phases 5-7 built all the pieces: Tribal registry (592 Tribes), congressional mapping, award matching, hazard profiling, economic impact, DOCX engine, and Hot Sheet renderer. Phase 8 assembles these into complete per-Tribe advocacy packets (Document 1), a shared strategic overview (Document 2), wires CLI batch/ad-hoc generation, adds change tracking, and **adds a web distribution layer** via GitHub Pages + SquareSpace iframe embed.

**AF-05 Update**: The original out-of-scope anti-feature "No web UI or frontend dashboard" is being **superseded**. The web widget is a lightweight static search+download tool, not a dashboard or editing UI. It uses pre-generated DOCX files served from GitHub Pages.

---

## Integration with TCR Project Planning

### Files to create/update in `F:\tcr-policy-scanner\.planning\`:

| File | Action |
|------|--------|
| `.planning/phases/08-assembly-polish/` | CREATE directory |
| `.planning/phases/08-assembly-polish/08-CONTEXT.md` | CREATE phase context |
| `.planning/phases/08-assembly-polish/08-MASTER-PROMPT.md` | CREATE this file |
| `.planning/phases/08-assembly-polish/08-01-PLAN.md` | CREATE -- DOC-05 |
| `.planning/phases/08-assembly-polish/08-02-PLAN.md` | CREATE -- DOC-06 |
| `.planning/phases/08-assembly-polish/08-03-PLAN.md` | CREATE -- OPS-01/02 |
| `.planning/phases/08-assembly-polish/08-04-PLAN.md` | CREATE -- OPS-03 |
| `.planning/phases/08-assembly-polish/08-05-PLAN.md` | CREATE -- WEB-01/02/03 |
| `.planning/phases/08-assembly-polish/08-06-PLAN.md` | CREATE -- E2E + docs |
| `.planning/ROADMAP.md` | UPDATE Phase 8 plans list |
| `.planning/REQUIREMENTS.md` | UPDATE add WEB-01/02/03, update AF-05 |
| `.planning/STATE.md` | UPDATE current position |
| `.planning/PROJECT.md` | UPDATE web widget in scope |

---

## Plan 08-01: Document 1 Full Assembly (DOC-05)

**Objective**: Add executive summary, congressional delegation, hazard profile summary, and structural asks standalone sections to complete the Document 1 assembly.

**What exists** (from Phase 7):
- `DocxEngine.generate()` at `src/packets/docx_engine.py:164` -- currently assembles: cover -> TOC -> Hot Sheets -> appendix
- `render_cover_page()`, `render_table_of_contents()`, `render_appendix()` at `src/packets/docx_sections.py`
- `HotSheetRenderer.render_all_hotsheets()` at `src/packets/docx_hotsheet.py`
- `TribePacketContext` at `src/packets/context.py` with all data fields
- `StyleManager` + styles at `src/packets/docx_styles.py`
- `ProgramRelevanceFilter` returns 8-12 relevant programs per Tribe (AF-04 superseded)

**What's missing** (4 new sections):

### New functions in `src/packets/docx_sections.py`:

1. **`render_executive_summary(document, context, relevant_programs, economic_summary, style_manager)`**
   - 1-page overview: Tribe name, states, top 3 hazards, total funding history, top 3 programs by award amount, delegation snapshot (count of senators/reps), key structural asks
   - Uses existing `context.hazard_profile`, `context.awards`, `context.economic_impact`
   - Rendered between TOC and Hot Sheets

2. **`render_delegation_section(document, context, style_manager)`**
   - Full congressional delegation as formatted table
   - Columns: Name | Role | State | District | Relevant Committees
   - Groups: Senators first, then Representatives
   - Uses `context.senators` and `context.representatives` (already populated from CongressionalMapper)
   - Reuses committee keyword filtering pattern from `docx_hotsheet.py:76` (`RELEVANT_COMMITTEE_KEYWORDS`)
   - Rendered after executive summary

3. **`render_hazard_summary(document, context, style_manager)`**
   - FEMA NRI: overall risk rating, social vulnerability, top 5 hazards table (type, score, EAL)
   - USFS wildfire: risk to homes, wildfire likelihood (if available)
   - Uses `context.hazard_profile` (same data structure as `_display_hazard_summary` in `orchestrator.py:350`)
   - Rendered after Hot Sheets

4. **`render_structural_asks_section(document, structural_asks, context, style_manager)`**
   - Five Structural Asks as standalone section (vs. woven into Hot Sheets in Phase 7)
   - Each ask: title, description, evidence from Tribe's hazard/award data
   - Cross-references which programs each ask advances
   - Rendered after hazard summary

### Modify `DocxEngine.generate()` -- new document order:

```python
def generate(self, context, relevant_programs, economic_summary,
             structural_asks, omitted_programs=None,
             changes=None, previous_date=None) -> Path:
    document, style_manager = self.create_document()

    # 1. Cover page (existing)
    render_cover_page(document, context, style_manager)

    # 2. Table of contents (existing)
    render_table_of_contents(document, relevant_programs, context, style_manager)

    # 3. Executive summary (NEW - DOC-05)
    document.add_page_break()
    render_executive_summary(document, context, relevant_programs,
                            economic_summary, style_manager)

    # 4. Congressional delegation (NEW - DOC-05)
    document.add_page_break()
    render_delegation_section(document, context, style_manager)

    # 5. Hot Sheets (existing) -- 8-12 relevant programs per Tribe
    renderer = HotSheetRenderer(document, style_manager)
    renderer.render_all_hotsheets(context, relevant_programs,
                                  economic_summary, structural_asks)

    # 6. Hazard profile summary (NEW - DOC-05)
    document.add_page_break()
    render_hazard_summary(document, context, style_manager)

    # 7. Structural asks standalone (NEW - DOC-05)
    document.add_page_break()
    render_structural_asks_section(document, structural_asks, context,
                                   style_manager)

    # 8. Change tracking (NEW - OPS-03, optional)
    if changes:
        document.add_page_break()
        render_change_tracking(document, changes, previous_date, style_manager)

    # 9. Appendix (existing)
    document.add_page_break()
    render_appendix(document, omitted_programs or [], context, style_manager)

    return self.save(document, context.tribe_id)
```

### Tests (`tests/test_doc_assembly.py`):

Must-have truths:
- Full document generation produces DOCX with all sections (verified by paragraph text search)
- Executive summary contains Tribe name and at least 1 program reference
- Delegation section lists senators and reps in tabular format
- Hazard summary renders top hazards from FEMA NRI data
- Structural asks section includes 5 asks
- Zero-award, zero-hazard Tribe produces valid DOCX (graceful empty sections)
- Multi-state Tribe (mock with 3 states) has correct multi-state delegation
- All 214 existing tests still pass

Fixtures: Reuse `_mock_programs()` and `_write_json()` patterns from `tests/test_docx_integration.py`

---

## Plan 08-02: Document 2 -- Strategic Overview (DOC-06)

**Objective**: Generate a single shared DOCX ("FY26 Federal Funding Overview & Strategy") from existing v1.0 pipeline data.

### New file: `src/packets/strategic_overview.py`

```python
class StrategicOverviewGenerator:
    """Generates the shared strategic overview DOCX (Document 2).

    Uses existing v1.0 data: program_inventory.json, policy_tracking.json,
    graph_schema.json, and optionally LATEST-GRAPH.json / LATEST-MONITOR-DATA.json.
    """

    def __init__(self, config: dict, programs: dict[str, dict]):
        self.config = config
        self.programs = programs
        self.ecoregion = EcoregionMapper(config)

    def generate(self, output_dir: Path) -> Path:
        """Generate STRATEGIC-OVERVIEW.docx in output_dir."""
```

**Document sections (7 sections, all from existing data files):**

1. **Cover page** -- "FY26 Federal Funding Overview & Strategy" with date
2. **Appropriations landscape** -- From `data/policy_tracking.json`: FY26 positions, authorization status per program. From `data/program_inventory.json`: 16 programs with CI status, funding type
3. **Ecoregion strategic priorities** -- 7 ecoregions from `EcoregionMapper`, each with priority programs and status summary. Uses `src/packets/ecoregion.py` `get_priority_programs()` method
4. **Science infrastructure threats** -- From `outputs/LATEST-MONITOR-DATA.json` (if exists): IIJA sunset, DHS funding cliff, reconciliation watch alerts. Graceful fallback if no monitor data
5. **FEMA analysis** -- FEMA programs from program inventory (fema_bric, fema_hmgp, fema_fma, fema_pdm): CI status, advocacy goals, FEMA BCR methodology
6. **Cross-cutting framework** -- Five Structural Asks from `data/graph_schema.json`: title, description, which programs each ask advances
7. **Messaging guidance** -- From program inventory: advocacy_lever fields, tightened_language, grouped by advocacy goal (DEFEND/PROTECT/EXPAND)

**Data sources (all existing):**
- `data/program_inventory.json` -- 16 programs
- `data/policy_tracking.json` -- FY26 positions
- `data/graph_schema.json` -- structural asks, authorities, barriers
- `outputs/LATEST-MONITOR-DATA.json` -- monitor alerts (optional)
- `src/packets/ecoregion.py` -- ecoregion config + mappings

**Output**: `outputs/packets/STRATEGIC-OVERVIEW.docx`

### Modify `src/packets/orchestrator.py`:

Add `generate_strategic_overview()` method:
```python
def generate_strategic_overview(self) -> Path:
    """Generate the shared strategic overview DOCX."""
    from src.packets.strategic_overview import StrategicOverviewGenerator
    generator = StrategicOverviewGenerator(self.config, self.programs)
    output_dir = Path(self.config.get("packets", {}).get("output_dir", "outputs/packets"))
    return generator.generate(output_dir)
```

### Tests (`tests/test_strategic_overview.py`):
- Generates valid DOCX with 7 sections
- Appropriations section includes all 16 program CI statuses
- Ecoregion section covers all 7 ecoregions
- Works with no LATEST-MONITOR-DATA.json (graceful fallback)
- Cross-cutting framework includes 5 structural asks
- Messaging guidance groups by advocacy goal

---

## Plan 08-03: Batch & Ad-hoc CLI (OPS-01, OPS-02)

**Objective**: Wire `run_all_tribes()` to full DOCX generation with memory management, progress reporting, and strategic overview.

### Modify `PacketOrchestrator.run_all_tribes()`:

Currently (lines 128-157): builds context only, prints OK/ERROR. Needs to:
1. Call `generate_packet_from_context()` for each Tribe
2. GC every 25 Tribes (`gc.collect()`)
3. Progress reporting with [N/592] and running duration
4. Error isolation (continue on failure)
5. Generate strategic overview after all Tribes
6. Output packets to `outputs/packets/tribes/{tribe_id}.docx` (subdirectory)
7. Batch summary at end

```python
def run_all_tribes(self) -> dict:
    """Generate DOCX packets for all Tribes + strategic overview.

    Returns: {success: int, errors: int, total: int, duration_s: float, output_dir: str}
    """
    import gc
    import time

    all_tribes = self.registry.get_all()
    total = len(all_tribes)
    start = time.monotonic()
    success_count = 0
    error_count = 0
    error_tribes = []

    for i, tribe in enumerate(all_tribes, 1):
        elapsed = time.monotonic() - start
        print(f"[{i}/{total}] {tribe['name']}...", end="", flush=True)
        try:
            context = self._build_context(tribe)
            self.generate_packet_from_context(context, tribe)
            print(f" OK ({elapsed:.0f}s)")
            success_count += 1
        except Exception as exc:
            print(f" ERROR: {exc}")
            logger.error("Failed: %s: %s", tribe["name"], exc)
            error_count += 1
            error_tribes.append(tribe["name"])
        finally:
            if i % 25 == 0:
                gc.collect()

    # Strategic overview
    print("\nGenerating Strategic Overview...", end="", flush=True)
    try:
        overview_path = self.generate_strategic_overview()
        print(f" OK ({overview_path})")
    except Exception as exc:
        print(f" ERROR: {exc}")
        logger.error("Strategic overview failed: %s", exc)

    duration = time.monotonic() - start
    print(f"\n--- Batch Complete ---")
    print(f"Total: {total} | Success: {success_count} | Errors: {error_count}")
    print(f"Duration: {duration:.0f}s")
    if error_tribes:
        print(f"Failed: {', '.join(error_tribes[:10])}")
    return {"success": success_count, "errors": error_count,
            "total": total, "duration_s": duration}
```

### Output directory for batch mode:

Update `DocxEngine` output_dir for batch mode. Config change for batch:
```json
"packets": {
    "output_dir": "outputs/packets/tribes"
}
```

The strategic overview goes to `outputs/packets/STRATEGIC-OVERVIEW.docx` (parent directory).

### OPS-02 verification:
Current `run_single_tribe()` (line 67) already calls `generate_packet_from_context()` -- verify it produces the full DOC-05 document after Plan 08-01 changes. No code changes needed; just add a test.

### Tests (`tests/test_batch_generation.py`):
- Batch with 3 mock Tribes produces 3 DOCX + strategic overview
- Per-Tribe error doesn't halt batch (mock one Tribe to raise, others succeed)
- GC triggered every 25 Tribes (mock gc.collect, verify call count)
- Progress output includes [N/total] format
- Return dict has correct counts
- Output directory structure: `outputs/packets/tribes/*.docx`

---

## Plan 08-04: Change Tracking (OPS-03)

**Objective**: Add "Since Last Packet" section showing changes between generations.

### New file: `src/packets/change_tracker.py`

```python
class PacketChangeTracker:
    """Tracks per-Tribe packet state for change detection.

    State stored as JSON: data/packet_state/{tribe_id}.json
    Single-writer-per-tribe_id assumed (no concurrent generation for same Tribe).
    """

    def __init__(self, state_dir: Path = Path("data/packet_state")): ...

    def load_previous(self, tribe_id: str) -> dict | None:
        """Load previous state. None if first generation."""

    def compute_current(self, context: TribePacketContext,
                        programs: dict) -> dict:
        """Snapshot current state."""

    def diff(self, previous: dict, current: dict) -> list[dict]:
        """Compute changes. Returns list of change dicts:
        [{"type": "ci_status_change", "program": "BIA TCR",
          "old": "STABLE", "new": "AT_RISK"}, ...]
        Types: ci_status_change, new_award, award_total_change,
               advocacy_goal_shift, new_threat
        """

    def save_current(self, tribe_id: str, state: dict) -> None:
        """Persist state (atomic write: tmp + os.replace() with cleanup)."""
```

**State snapshot schema** (`data/packet_state/{tribe_id}.json`):
```json
{
  "tribe_id": "epa_123",
  "generated_at": "2026-02-10T12:00:00Z",
  "program_states": {
    "bia_tcr": {"ci_status": "AT_RISK", "advocacy_goal": "DEFEND", "award_total": 150000}
  },
  "total_awards": 5,
  "total_obligation": 500000,
  "top_hazards": ["Wildfire", "Flooding", "Drought"]
}
```

### New function in `src/packets/docx_sections.py`:

```python
def render_change_tracking(document, changes: list[dict],
                           previous_date: str, style_manager) -> None:
    """Render 'Since Last Packet' section.

    If changes list is empty, section is NOT rendered (omitted entirely).
    """
```
- Header: "Since Last Packet (generated {previous_date})"
- Groups changes by type with human-readable descriptions

### Wire into orchestrator and engine:

1. In `PacketOrchestrator.generate_packet_from_context()` (line 429): instantiate `PacketChangeTracker`, load previous, compute current, diff, pass changes to engine, save current after successful generation
2. In `DocxEngine.generate()` (line 164): accept optional `changes` and `previous_date` params; render between structural asks and appendix

### Tests (`tests/test_change_tracking.py`):
- First generation: no changes, no section rendered
- Second generation with CI status change: section appears
- Award total increase detected
- Advocacy goal shift detected
- State file written with correct schema
- Corrupt state file handled gracefully (treated as first generation)
- Atomic write pattern verified (tmp + os.replace())

---

## Plan 08-05: GitHub Pages Widget + Actions Workflow (WEB-01, WEB-02, WEB-03)

**Objective**: Static search widget on GitHub Pages + CI workflow for packet generation + SquareSpace embed code.

### GitHub Pages architecture:

GitHub Pages serves from `docs/web/` on `main` branch (configure in repo Settings > Pages). This keeps widget source alongside project code (no separate gh-pages branch).

```
docs/web/
  index.html              # Widget page
  css/
    style.css             # Widget styles (~3KB)
    awesomplete.css        # Vendored Awesomplete styles (~1KB)
  js/
    app.js                # Widget logic (~5KB)
    awesomplete.min.js     # Vendored Awesomplete (~2KB)
  data/
    tribes.json           # Generated index (~50KB, committed by CI)
  tribes/                 # Generated DOCX files (committed by CI)
    epa_001.docx
    ...
    STRATEGIC-OVERVIEW.docx
```

**URL structure**: `https://atniclimate.github.io/TCR-policy-scanner/`

### `scripts/build_web_index.py`:

```python
"""Build tribes.json index for the GitHub Pages widget.

Reads tribal_registry.json + scans packets directory to build
a searchable index with download metadata.

Usage: python scripts/build_web_index.py [--registry data/tribal_registry.json]
                                          [--packets outputs/packets/tribes]
                                          [--output docs/web/data/tribes.json]
"""

def build_index(registry_path: Path, packets_dir: Path, output_path: Path) -> dict:
    """Build tribes.json with searchable index and packet metadata."""
```

### Widget design (`docs/web/index.html`):

- Self-contained HTML page (no framework, no build step)
- Header: "Tribal Climate Resilience -- Advocacy Packet Search"
- Search input with Awesomplete autocomplete
- On selection: show info card with Tribe name, state(s), ecoregion
- "Download Report" button: direct `<a href="tribes/{id}.docx" download>`
- "Download Strategic Overview" link in footer
- Mobile-responsive (flexbox, stacks on <600px)
- WCAG 2.1 AA accessible (focus states, aria labels, color contrast)
- Loading spinner while tribes.json loads
- Error state if tribes.json fails to load
- Total widget bundle: <15KB (excluding data/tribes)

### CSS approach (`docs/web/css/style.css`):
- Mobile-first responsive design
- TCR brand: dark teal (#1a5276) header, white cards, professional look
- High contrast for accessibility
- Print-friendly styles

### GitHub Actions workflow (`.github/workflows/generate-packets.yml`):

```yaml
name: Generate Advocacy Packets
on:
  schedule:
    - cron: '0 15 * * 0'  # Sunday 8AM Pacific (15:00 UTC)
  workflow_dispatch:

permissions:
  contents: write

jobs:
  generate:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
      - run: pip install -r requirements.txt

      - name: Generate all packets
        env:
          CONGRESS_API_KEY: ${{ secrets.CONGRESS_API_KEY }}
          SAM_API_KEY: ${{ secrets.SAM_API_KEY }}
        run: python -m src.main --prep-packets --all-tribes

      - name: Build web index
        run: python scripts/build_web_index.py

      - name: Stage for GitHub Pages
        run: |
          mkdir -p docs/web/tribes docs/web/data
          cp outputs/packets/tribes/*.docx docs/web/tribes/ || true
          cp outputs/packets/STRATEGIC-OVERVIEW.docx docs/web/tribes/ || true

      - name: Commit and push
        run: |
          git config user.name "TCR Policy Scanner"
          git config user.email "scanner@tcr-policy-scanner.local"
          git add docs/web/tribes/ docs/web/data/tribes.json
          if git diff --cached --quiet; then
            echo "No changes to commit"
          else
            git commit -m "packets: generate $(date -u +%Y-%m-%d)"
            git push
          fi
```

### SquareSpace embed code (WEB-03):

```html
<div style="width:100%;max-width:800px;margin:0 auto;">
  <iframe
    src="https://atniclimate.github.io/TCR-policy-scanner/"
    width="100%" height="700" frameborder="0"
    style="border:1px solid #e0e0e0;border-radius:8px;"
    title="TCR Policy Scanner - Tribal Advocacy Packet Search"
    loading="lazy">
  </iframe>
</div>
```

### Size feasibility:
- Per-Tribe DOCX: ~50-150KB (20 pages, tables, no images)
- 592 packets: ~60-90MB total
- GitHub Pages soft limit: 1GB
- Within limits, no issues

### Tests (`tests/test_web_index.py`):
- `build_index()` produces valid JSON with all registry Tribes
- Tribes with DOCX files have `has_packet: true`
- Tribes without DOCX files have `has_packet: false`
- `file_size_kb` is accurate for existing files
- Widget manual verification: open `docs/web/index.html` in browser

---

## Plan 08-06: E2E Integration Testing + Documentation

**Objective**: End-to-end verification + project documentation updates.

### E2E test (`tests/test_e2e_phase8.py`):
- Mock 3 Tribes with full data (awards, hazards, delegation)
- Batch generation produces 3 DOCX + strategic overview
- Web index builder produces valid tribes.json
- Single Tribe generation produces 1 complete DOCX with all sections
- Run same Tribe twice -> "Since Last Packet" section appears
- Multi-state Tribe has multi-state delegation
- All 214+ existing tests still pass

### Documentation updates:
- `README.md`: Add web widget section, SquareSpace embed instructions
- `.planning/ROADMAP.md`: Mark Phase 8 plans complete
- `.planning/REQUIREMENTS.md`: Mark DOC-05, DOC-06, OPS-01-03, WEB-01-03 complete
- `.planning/STATE.md`: Update to Phase 8 complete, v1.1 milestone finished
- `.planning/PROJECT.md`: Add web widget to scope, update AF-05

---

## Execution Plan

### Wave 1 (2 parallel agents):
| Agent | Plan | Focus | Files |
|-------|------|-------|-------|
| A | 08-01 | DOC-05: 4 new section renderers + engine assembly | docx_sections.py, docx_engine.py, tests |
| B | 08-02 | DOC-06: Strategic overview generator | strategic_overview.py, orchestrator.py, tests |

### Wave 2 (2 parallel agents, after Wave 1):
| Agent | Plan | Focus | Files |
|-------|------|-------|-------|
| C | 08-03 | OPS-01/02: Batch generation + memory mgmt | orchestrator.py, main.py, tests |
| D | 08-04 | OPS-03: Change tracker + DOCX section | change_tracker.py, docx_sections.py, tests |

**Note on file conflicts:** Plans 08-01 and 08-04 both modify `docx_sections.py` and `docx_engine.py`. This is safe because 08-04 depends on 08-01 (Wave 2 after Wave 1). Plans 08-02 and 08-03 both modify `orchestrator.py`; 08-03 depends on 08-02 (Wave 2 after Wave 1).

### Wave 3 (2 parallel agents, after Wave 2):
| Agent | Plan | Focus | Files |
|-------|------|-------|-------|
| E | 08-05 | WEB: Widget + CI workflow + embed | docs/web/*, scripts/*, .github/workflows/* |
| F | 08-06 | E2E tests + docs | tests/*, .planning/*, README.md |

**Total: 6 plans, 3 waves, ~6 agents**

---

## Verification Checklist

1. `pytest tests/ -v` -- all tests pass (214 existing + ~80 new = ~294 total)
2. `python -m src.main --prep-packets --tribe "Cherokee Nation"` -- complete DOCX with all sections
3. `python -m src.main --prep-packets --all-tribes` -- 592 packets + strategic overview
4. Run single Tribe twice -> "Since Last Packet" section on second run
5. `python scripts/build_web_index.py` -> valid tribes.json
6. Open `docs/web/index.html` in browser -> search works, download works
7. After push + GitHub Pages enable -> widget loads at published URL
8. iframe embed code works in SquareSpace test page

---

## Corrections Applied to Original Prompt

| Item | Original | Corrected | Reason |
|------|----------|-----------|--------|
| DocxEngine.generate() line | 150 | 164 | Verified against actual source |
| _display_hazard_summary line | 338 | 350 | Verified against actual source |
| RELEVANT_COMMITTEE_KEYWORDS line | 77 | 76 | Verified against actual source |
| run_all_tribes() lines | 126-155 | 128-157 | Verified against actual source |
| Hot Sheets count | "16 Hot Sheets" | "8-12 relevant programs" | AF-04 superseded; ProgramRelevanceFilter active |
| run_single_tribe() line | not specified | 67 | Added for reference |
| generate_packet_from_context() line | not specified | 429 | Added for reference |
| DocxEngine.generate() params | missing changes/previous_date | added | Forward-compatible for OPS-03 |
