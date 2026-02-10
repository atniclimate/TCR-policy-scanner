---
phase: "08"
plan: "02"
subsystem: "packets-strategic-overview"
tags: ["docx", "strategic-overview", "appropriations", "ecoregion", "fema", "messaging"]
dependency_graph:
  requires: ["07-04"]
  provides: ["StrategicOverviewGenerator", "generate_strategic_overview()", "STRATEGIC-OVERVIEW.docx"]
  affects: ["08-03", "08-04"]
tech_stack:
  added: []
  patterns: ["atomic-save", "graceful-fallback", "lazy-import", "goal-grouping"]
key_files:
  created:
    - "src/packets/strategic_overview.py"
    - "tests/test_strategic_overview.py"
  modified:
    - "src/packets/orchestrator.py"
decisions:
  - id: "DEC-0802-01"
    decision: "Policy tracking authorization looked up from extensible_fields, with fallback to truncated reasoning"
    rationale: "policy_tracking.json uses 'positions' key (not 'programs') and authorization_status is in extensible_fields; reasoning provides a usable fallback"
  - id: "DEC-0802-02"
    decision: "Monitor data extraction tries multiple key names (alerts, findings, threats, monitors)"
    rationale: "Monitor output format may vary; cascading lookup ensures graceful handling of different output structures"
  - id: "DEC-0802-03"
    decision: "_FEMA_PROGRAM_IDS includes 5 IDs even though only 2 exist in current inventory"
    rationale: "Future-proof for when fema_hmgp, fema_fma, fema_pdm are added to program_inventory.json"
metrics:
  duration: "8 minutes"
  completed: "2026-02-10"
  tests_added: 22
  tests_total: 249
  tests_passing: 249
---

# Phase 8 Plan 2: Strategic Overview Generator Summary

**One-liner:** StrategicOverviewGenerator produces a 7-section STRATEGIC-OVERVIEW.docx covering 16 programs, 7 ecoregions, 5 structural asks, FEMA analysis, and DEFEND/PROTECT/EXPAND messaging guidance, with 22 tests and 249 total passing.

## What Was Built

### strategic_overview.py (new, 424 lines)

`StrategicOverviewGenerator` class with `generate()` method producing a shared strategic overview DOCX:

1. **Cover page** -- "FY26 Federal Funding Overview & Strategy", subtitle, description, generation date, confidentiality notice
2. **Appropriations Landscape** -- 5-column table (Program, Agency, CI Status, Funding Type, Authorization) for all 16 programs, sorted by name, with zebra striping and status summary counts
3. **Ecoregion Strategic Priorities** -- All 7 ecoregions via `EcoregionMapper.get_all_ecoregions()`, each with priority programs and inline CI status labels
4. **Science Infrastructure Threats** -- Extracts alerts from LATEST-MONITOR-DATA.json with graceful fallback ("Monitor data not available") when missing
5. **FEMA Programs Analysis** -- Filters for `_FEMA_PROGRAM_IDS`, shows CI status badges, descriptions, advocacy levers, and BCR methodology note
6. **Cross-Cutting Policy Framework** -- All 5 structural asks from graph_schema.json with name, description, target, urgency, and programs advanced
7. **Messaging Guidance** -- Programs grouped by `_GOAL_BY_STATUS` (DEFEND/PROTECT/EXPAND), with tightened language, advocacy levers, and framing verbs from `FRAMING_BY_STATUS`

Key implementation patterns:
- Atomic save (NamedTemporaryFile + close + save + os.replace)
- 10MB file size guard on all JSON loads
- `datetime.now(timezone.utc)` for timestamps
- `encoding="utf-8"` on all file I/O
- Page breaks between sections (not section breaks)
- Graceful fallback for all missing data files

### orchestrator.py (extended)

Added `generate_strategic_overview()` method to `PacketOrchestrator`:
- Lazy import of `StrategicOverviewGenerator` to avoid circular imports
- Uses same `packets.output_dir` config as DocxEngine
- `self.programs` dict passed directly (already keyed by program ID)
- No existing methods modified

### test_strategic_overview.py (new, 22 tests)

Comprehensive test coverage across 12 test classes:
- `TestGenerateValidDocx` -- file existence, size, re-readability
- `TestSectionStructure` -- all 7 section headings present
- `TestAppropriationsSection` -- 16-row table, status summary
- `TestEcoregionSection` -- 7 ecoregion Heading 3 entries
- `TestGracefulFallback` -- missing monitor data handled
- `TestCrossCuttingFramework` -- 5 structural ask names
- `TestMessagingGuidance` -- DEFEND/PROTECT/EXPAND groups, template disclaimer
- `TestFemaAnalysis` -- FEMA program names, BCR note
- `TestCoverPage` -- title, confidentiality, date
- `TestScienceThreats` -- alerts from monitor data
- `TestOrchestratorIntegration` -- end-to-end via PacketOrchestrator
- `TestAtomicSave` -- nested output dir creation
- `TestConstants` -- _GOAL_BY_STATUS, _FEMA_PROGRAM_IDS, _MAX_DATA_FILE_BYTES
- `TestLoadJson` -- nonexistent, valid, invalid JSON

All tests use `tmp_path` fixtures with mock data; no real data files required.

## Deviations from Plan

None -- plan executed exactly as written.

## Commits

| Hash | Type | Description |
|------|------|-------------|
| e4b2a60 | feat | Create StrategicOverviewGenerator with 7-section DOCX |
| 2dc60f7 | feat | Add generate_strategic_overview() to PacketOrchestrator |
| 8078f0c | test | Add 22 tests for strategic overview generator |

## Next Phase Readiness

Plan 08-02 complete. DOC-06 requirement satisfied:
- `StrategicOverviewGenerator.generate()` produces a complete STRATEGIC-OVERVIEW.docx
- All 16 programs covered in appropriations table
- All 7 ecoregions with priority programs
- 5 structural asks in cross-cutting framework
- Programs grouped by DEFEND/PROTECT/EXPAND advocacy goals
- Graceful fallback for missing monitor data
- Atomic save pattern for crash safety
- `PacketOrchestrator.generate_strategic_overview()` provides orchestration entry point
- 249 tests passing (214 existing + 13 from 08-01 + 22 new)

**Ready for Wave 2:** Plans 08-03 (OPS-01/02/03) and 08-04 depend on 08-01 + 08-02 both complete.
