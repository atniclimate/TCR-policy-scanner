---
phase: 05-foundation
plan: 04
subsystem: packet-orchestrator
tags: [orchestrator, cli, integration, packets, registry, ecoregion, congress]
dependency-graph:
  requires: [05-01, 05-02, 05-03]
  provides: [packet_orchestrator, prep_packets_cli, phase5_test_suite]
  affects: [06-xx, 07-xx, 08-xx]
tech-stack:
  added: []
  patterns: [lazy-import-cli, multi-module-orchestration, 3-tier-resolution-display]
key-files:
  created:
    - src/packets/orchestrator.py
    - tests/test_packets.py
  modified:
    - src/main.py
    - config/scanner_config.json
decisions:
  - id: auto-select-first-match
    description: "When resolve() returns multiple fuzzy matches, orchestrator auto-selects the first (best score) and displays alternatives as warnings"
  - id: lazy-import-packets
    description: "PacketOrchestrator imported only when --prep-packets flag is set, avoiding import overhead for existing pipeline"
  - id: graceful-no-delegation
    description: "Tribes with no congressional delegation data display 'No congressional delegation data available' instead of crashing"
metrics:
  duration: "~4 minutes"
  completed: 2026-02-10
---

# Phase 5 Plan 4: PacketOrchestrator and CLI Integration Summary

**One-liner:** PacketOrchestrator wires registry (592 Tribes), ecoregion (7 regions), and congress (501 delegations) into `--prep-packets --tribe <name>` CLI flow, with 31-test suite covering all 5 Phase 5 requirements.

## What Was Built

### PacketOrchestrator (`src/packets/orchestrator.py`)

Integration class that coordinates all Phase 5 modules:

1. **`run_single_tribe(name)`** -- Resolves via TribalRegistry.resolve(), handles 3 outcomes (exact match, ambiguous list with auto-select, no-match with fuzzy suggestions + sys.exit(1))
2. **`run_all_tribes()`** -- Iterates all 592 Tribes, builds context for each, prints progress counter and summary
3. **`_build_context(tribe)`** -- Assembles TribePacketContext from registry identity + ecoregion classification + congressional delegation
4. **`_display_tribe_info(context)`** -- Formatted CLI output with identity block, ecoregion priority programs, districts with overlap %, senators/representatives with committee assignments

### CLI Integration (`src/main.py`)

Three new argparse flags added without modifying existing behavior:
- `--prep-packets` (required gate flag)
- `--tribe <name>` (single Tribe mode)
- `--all-tribes` (batch mode)

Lazy import pattern: `from src.packets.orchestrator import PacketOrchestrator` only executes when `--prep-packets` is set. Existing pipeline flags (`--programs`, `--dry-run`, `--source`, `--report-only`, `--graph-only`, `--verbose`) unaffected.

### Config Update (`config/scanner_config.json`)

Added `"packets"` top-level key with data paths for tribal_registry, congressional_cache, ecoregion, and output_dir. No existing config sections modified.

### Test Suite (`tests/test_packets.py`)

31 tests across 5 test classes, all using tmp_path fixtures with mock data:

| Class | Tests | Requirement |
|-------|-------|-------------|
| TestEcoregionMapper | 7 | REG-02 |
| TestTribalRegistry | 10 | REG-01 |
| TestCongressionalMapper | 8 | CONG-01, CONG-02 |
| TestTribePacketContext | 3 | REG-03 |
| TestPacketOrchestrator | 3 | Integration |

Total project test count: 83 (52 existing + 31 new), all passing.

## Verification Results

| Test | Result |
|------|--------|
| `--prep-packets --tribe "Navajo Nation"` | Resolves, displays 4 districts, 6 senators, 4 reps |
| `--prep-packets --tribe "Tlingit"` | Substring match, auto-selects Central Council, shows Yakutat alternative |
| `--prep-packets --tribe "nonexistent"` | Error message with 5 fuzzy suggestions, exit(1) |
| `--prep-packets` (no --tribe/--all-tribes) | Usage error with examples |
| `--programs` (existing flag) | Still works, 16 programs listed |
| `pytest tests/ -v` | 83/83 pass |

## Decisions Made

1. **Auto-select first match**: When resolve() returns a list (ambiguous substring or fuzzy), the orchestrator auto-selects the first result (best match) and displays alternatives as a warning. This avoids blocking on user input in batch mode.

2. **Lazy import for packets**: PacketOrchestrator is only imported when `--prep-packets` is active. This keeps the existing pipeline startup fast (no rapidfuzz import overhead unless needed).

3. **Graceful no-delegation handling**: Tribes without congressional delegation data (e.g., some Alaska Tribes not in Census AIANNH file) display a clear message instead of crashing.

## Deviations from Plan

None -- plan executed exactly as written.

## Phase 5 Completion Status

All 4 plans in Phase 5 are now complete:

| Plan | Name | Status |
|------|------|--------|
| 05-01 | Ecoregion + Context + Dependencies | Complete |
| 05-02 | Tribal Registry + Resolution | Complete |
| 05-03 | Congressional Mapping Data Layer | Complete |
| 05-04 | PacketOrchestrator + CLI + Tests | Complete |

**Phase 5 success criterion met:** `--prep-packets --tribe "Navajo Nation"` resolves the Tribe, displays its identity and congressional delegation with committee assignments.

## Next Phase Readiness

Phase 6 (Data Acquisition) can proceed. All data layers are available:
- `data/tribal_registry.json` (592 Tribes)
- `data/congressional_cache.json` (538 members, 501 delegations, 46 committees)
- `data/ecoregion_config.json` (7 ecoregions, 51 states)
- `src/packets/orchestrator.py` (integration point for Phase 6 award matching + hazard profiling)
