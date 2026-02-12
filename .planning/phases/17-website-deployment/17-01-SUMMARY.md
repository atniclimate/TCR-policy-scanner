# Phase 17 Plan 01: Data Pipeline Enhancement Summary

**One-liner:** Alias embedding + per-Tribe timestamps in tribes.json, self-hosted Fuse.js 7.1.0 replaces Awesomplete

## What Was Done

### Task 1: Enhance build_web_index.py with alias embedding and per-Tribe timestamps
- Added `_load_filtered_aliases()` function that reads `data/tribal_aliases.json`, builds reverse mapping (tribe_id -> aliases), filters out housing authority variants, sorts by string length (shortest first), and caps at 10 per Tribe
- Added `_get_tribe_generated_at()` function that checks internal/ and congressional/ subdirectories for DOCX files and returns the most recent modification time as ISO 8601 timestamp
- Enhanced `build_index()` to accept `aliases_path` parameter and embed `aliases` (list) and `generated_at` (ISO timestamp or null) fields in each Tribe entry
- Added `--aliases` CLI argument defaulting to `data/tribal_aliases.json`
- 10MB size guard on aliases file consistent with existing `MAX_REGISTRY_SIZE` pattern
- Missing aliases file handled gracefully (returns empty aliases, no crash)
- **Commit:** `d7d9913`

### Task 2: Self-host Fuse.js and remove Awesomplete
- Downloaded Fuse.js 7.1.0 UMD bundle (26.4KB) to `docs/web/js/fuse.min.js`
- Removed `docs/web/js/awesomplete.min.js` (no longer needed)
- Removed `docs/web/css/awesomplete.css` (no longer needed)
- Zero CDN dependencies: XCUT-02 compliance confirmed (no jsdelivr/cdnjs/unpkg references in docs/web/)
- **Commit:** `319cedb`

## Verification Results

| Check | Status |
|-------|--------|
| `--aliases` flag in CLI help | PASS |
| `docs/web/js/fuse.min.js` exists (~25.8KB) | PASS (26,415 bytes) |
| `docs/web/js/awesomplete.min.js` removed | PASS |
| `docs/web/css/awesomplete.css` removed | PASS |
| No CDN references in docs/web/ | PASS |
| All 22 tests pass (12 existing + 10 new) | PASS |

## Tests Added

| Test Class | Test Name | Validates |
|------------|-----------|-----------|
| TestAliasEmbedding | test_aliases_embedded_in_tribe_entries | Aliases list present per Tribe |
| TestAliasEmbedding | test_housing_aliases_filtered_out | "housing" variants excluded |
| TestAliasEmbedding | test_aliases_sorted_by_length_shortest_first | Shortest-first ordering |
| TestAliasEmbedding | test_aliases_capped_at_max_per_tribe | 10-alias cap enforced |
| TestAliasEmbedding | test_missing_aliases_file_returns_empty | Graceful missing file |
| TestAliasEmbedding | test_oversized_aliases_file_returns_empty | 10MB size guard |
| TestAliasEmbedding | test_missing_aliases_file_graceful_in_build_index | End-to-end graceful degradation |
| TestPerTribeTimestamp | test_generated_at_from_docx_mtime | ISO 8601 timestamp from file mtime |
| TestPerTribeTimestamp | test_generated_at_null_when_no_docx | Null when no DOCX exists |
| TestPerTribeTimestamp | test_generated_at_uses_latest_mtime | Picks most recent across subdirs |

## Deviations from Plan

None -- plan executed exactly as written.

## Key Files

### Created
- `docs/web/js/fuse.min.js` -- Self-hosted Fuse.js 7.1.0 UMD bundle

### Modified
- `scripts/build_web_index.py` -- Added `_load_filtered_aliases`, `_get_tribe_generated_at`, aliases/timestamps in entries, `--aliases` CLI flag
- `tests/test_web_index.py` -- 10 new tests for alias embedding and per-Tribe timestamps

### Removed
- `docs/web/js/awesomplete.min.js` -- Replaced by custom ARIA combobox + Fuse.js
- `docs/web/css/awesomplete.css` -- No longer needed

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| DEC-1701-01 | Housing alias filtering uses case-insensitive substring match | Housing authority variants add noise to search results without helping users find Tribes |
| DEC-1701-02 | Aliases sorted by string length, shortest first | Users more likely to search short names; keeps most useful aliases at top of list |

## Duration

~2 minutes 30 seconds
