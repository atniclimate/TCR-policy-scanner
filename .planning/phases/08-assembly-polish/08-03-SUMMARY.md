# Phase 8 Plan 3: Batch Generation (OPS-02/OPS-03) Summary

**One-liner:** run_all_tribes() upgraded from context-only to full DOCX generation with GC, progress, error isolation, and strategic overview

## Metadata

- **Phase:** 08-assembly-polish
- **Plan:** 03
- **Subsystem:** packets/orchestrator
- **Tags:** docx, batch, gc, error-isolation, progress, strategic-overview
- **Completed:** 2026-02-10
- **Duration:** ~4 minutes

## What Was Done

### Task 1: Update run_all_tribes() in orchestrator.py
- Replaced context-only build loop with full DOCX generation via `generate_packet_from_context()`
- Changed return type from `None` to `dict` with keys: success, errors, total, duration_s
- Added `gc.collect()` every 25 Tribes to prevent memory buildup across 592 Tribes
- Added elapsed time tracking via `time.monotonic()` (immune to clock adjustments)
- Per-Tribe `try/except` ensures one failure does not halt the entire batch
- Error list capped at 10 in printed output (prevents wall of text for mass failures)
- Strategic overview generated after all Tribes via `generate_strategic_overview()`
- Commit: `ddceff0`

### Task 2: Create tests/test_batch_generation.py
- 7 tests covering batch generation, error isolation, GC, progress format, return dict, strategic overview, and single-Tribe OPS-02 verification
- 401 lines total
- Full test suite: 256/256 passing (249 existing + 7 new)
- Commit: `b8a7076`

## Tests Added

| Test | Purpose |
|------|---------|
| test_batch_generates_docx_per_tribe | 3 mock Tribes produce 3 .docx files |
| test_batch_error_isolation | 1 failure of 3 yields success=2, errors=1 |
| test_batch_gc_called | gc.collect() invoked at Tribe 25 of 30 |
| test_batch_progress_format | stdout shows [1/3] and [3/3] progress |
| test_batch_return_dict | return dict has success/errors/total/duration_s |
| test_batch_strategic_overview_called | generate_strategic_overview() called once |
| test_single_tribe_generates_full_document | OPS-02: run_single_tribe() produces .docx |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Output directory path correction in tests**

- **Found during:** Task 2 (initial test run)
- **Issue:** Plan specified output at `outputs/packets/tribes/*.docx` but DocxEngine.save() writes to `outputs/packets/{tribe_id}.docx` (no `tribes` subdirectory)
- **Fix:** Tests look in `output_dir` directly instead of `output_dir / "tribes"`
- **Files modified:** tests/test_batch_generation.py
- **Impact:** None on production code; test assertions match actual engine behavior

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Import gc and time inside method body | Lazy import avoids module-level overhead; these are only needed during batch runs |
| gc.collect() in finally block | Runs even if the Tribe fails, ensuring memory cleanup regardless |
| time.monotonic() over time.time() | Immune to system clock adjustments; better for measuring elapsed durations |
| Error tribes list (not just count) | Named error list enables debugging which specific Tribes failed |
| Return dict (not None) | Enables programmatic checking in tests and CI pipelines |

## Key Files

### Created
- `tests/test_batch_generation.py` -- 7 tests for batch and single-Tribe generation

### Modified
- `src/packets/orchestrator.py` -- run_all_tribes() method updated (lines 128-184)

## Dependency Graph

- **Requires:** 08-01 (DOC-05 full assembly), 08-02 (DOC-06 strategic overview)
- **Provides:** OPS-02 (batch generation), OPS-03 (error isolation + progress)
- **Affects:** 08-05 (CLI polish), 08-06 (distribution)

## Requirements Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| OPS-02 | Complete | run_all_tribes() generates DOCX per Tribe; test_batch_generates_docx_per_tribe passes |
| OPS-03 | Complete | Error isolation (test_batch_error_isolation), progress format (test_batch_progress_format), GC (test_batch_gc_called) |

## Next Phase Readiness

- run_all_tribes() returns dict for CLI reporting in 08-05
- Strategic overview generation integrated into batch flow
- Error isolation prevents single-Tribe failures from blocking 592-Tribe batches
- No blockers for Wave 3 (08-05 + 08-06)
