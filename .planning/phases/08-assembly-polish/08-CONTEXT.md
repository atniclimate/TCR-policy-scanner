# Phase 8 Context: Assembly, Polish, and Web Distribution

## Phase Goal

Complete per-Tribe packets (Document 1) and the shared strategic overview (Document 2) are generated via CLI in batch and ad-hoc modes, with change tracking showing what shifted since the last generation -- ready for distribution to congressional offices. Additionally, a lightweight web distribution layer via GitHub Pages provides search+download access.

## Dependencies

Phase 8 depends on:
- **Phase 7** (complete): DOCX engine, Hot Sheet renderer, style manager, economic impact calculator
- **Phase 6** (complete): Award cache, hazard profiles for all 592 Tribes
- **Phase 5** (complete): Tribal registry, congressional mapping, CLI skeleton

## Existing Code State

### Files to extend:
- `src/packets/docx_engine.py` -- DocxEngine.generate() at line 164 (add new section calls)
- `src/packets/docx_sections.py` -- 3 existing renderers (add 5 new renderers)
- `src/packets/orchestrator.py` -- PacketOrchestrator with generate_packet_from_context() at line 429
- `src/main.py` -- CLI with --prep-packets, --tribe, --all-tribes args

### Files to create:
- `src/packets/strategic_overview.py` -- Document 2 generator
- `src/packets/change_tracker.py` -- Per-Tribe state tracking
- `scripts/build_web_index.py` -- Web index builder
- `docs/web/` -- Static search widget (HTML/CSS/JS)
- `.github/workflows/generate-packets.yml` -- CI workflow

### Test files:
- `tests/test_doc_assembly.py` -- Plan 08-01
- `tests/test_strategic_overview.py` -- Plan 08-02
- `tests/test_batch_generation.py` -- Plan 08-03
- `tests/test_change_tracking.py` -- Plan 08-04
- `tests/test_web_index.py` -- Plan 08-05
- `tests/test_e2e_phase8.py` -- Plan 08-06

### Current test count: 214 tests passing

## Key Patterns to Follow

- **Page breaks, not section breaks** between document sections (sections disrupt headers/footers)
- **paragraph.clear()** not `cell.text=""` (latter creates ghost empty run)
- **OxmlElement** must be fresh per call (not reused across cells)
- **Atomic write**: tmp file + `os.replace()` with cleanup on exception
- **NamedTemporaryFile**: close handle before `document.save()` (Windows file lock)
- **Path traversal**: `Path(tribe_id).name` + reject `.`/`..`
- **JSON cache size**: 10MB cap via `stat().st_size` check before `json.load()`
- **encoding="utf-8"** on all file I/O
- **datetime.now(timezone.utc)** not `datetime.utcnow()`

## Data Flow

```
CLI (--prep-packets --all-tribes)
  -> PacketOrchestrator.run_all_tribes()
    -> For each of 592 Tribes:
      -> _build_context(tribe) -> TribePacketContext
      -> generate_packet_from_context(context, tribe)
        -> EconomicImpactCalculator.compute()
        -> ProgramRelevanceFilter.filter_for_tribe() -> 8-12 programs
        -> PacketChangeTracker.diff() -> changes (NEW)
        -> DocxEngine.generate() -> .docx file
          -> render_cover_page()
          -> render_table_of_contents()
          -> render_executive_summary() (NEW)
          -> render_delegation_section() (NEW)
          -> HotSheetRenderer.render_all_hotsheets()
          -> render_hazard_summary() (NEW)
          -> render_structural_asks_section() (NEW)
          -> render_change_tracking() (NEW, if changes)
          -> render_appendix()
        -> PacketChangeTracker.save_current() (NEW)
    -> generate_strategic_overview() (NEW)
      -> StrategicOverviewGenerator.generate()
  -> build_web_index() (post-batch)
```

## Requirements Covered

| Requirement | Plan | Description |
|-------------|------|-------------|
| DOC-05 | 08-01 | Document 1 full assembly |
| DOC-06 | 08-02 | Document 2 strategic overview |
| OPS-01 | 08-03 | Batch generation CLI |
| OPS-02 | 08-03 | Ad-hoc single-Tribe CLI |
| OPS-03 | 08-04 | Change tracking |
| WEB-01 | 08-05 | GitHub Pages search widget |
| WEB-02 | 08-05 | GitHub Actions workflow |
| WEB-03 | 08-05 | SquareSpace embed code |

---
*Created: 2026-02-10*
