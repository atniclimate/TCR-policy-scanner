# Prior Bug Hunt Findings (2026-02-18 Session)

Two Dale Gribble agents + manual anti-pattern scans audited `src/` and `scripts/`.
**STATUS: VERIFIED AND RESOLVED (2026-02-18)**
- 3-agent swarm verified all 27 findings, fixed 19, dismissed 4 as not-bugs, deferred 4 P3s
- 1266 tests passing, 0 failures after all fixes

## Resolution Summary

| ID | Status | Notes |
|----|--------|-------|
| BUG-001 | **FIXED** | Atomic tmp+replace pattern applied |
| BUG-002 | **FIXED** | `_sanitize_tribe_id()` added to all 4 path helpers |
| BUG-003 | **FIXED** | `max(0,` -> `max(1,` for minimum 1s retry sleep |
| BUG-004 | **FIXED** | Negative amounts now render as `-$1,234,567` |
| BUG-005 | **FIXED** | try/except on both `int(district)` calls |
| BUG-006 | **FIXED** | Added `exc_info=True` to warning log |
| BUG-007 | **NOT A BUG** | `.get()` on empty dict is safe; all error paths return `{}` |
| BUG-008 | **NOT A BUG** | Single-run caching is correct; file won't appear mid-pipeline |
| BUG-009 | **FIXED** | Empty `actionDate` now maps to `None` not `""` |
| BUG-010 | **FIXED** | `bill_number.isdigit()` validation added |
| BUG-011 | **FIXED** | Replaced `hasattr` with `_ALLOWED_METHODS` frozenset |
| BUG-012 | **FIXED** | 2-year range guard with simple comparison logic |
| BUG-013 | **NOT A BUG** | `_save_source_cache` uses atomic write to known dir; no symlink risk |
| BUG-014 | **NOT A BUG** | Both paths call `tracker.save_current()` identically |
| BUG-015 | **FIXED** | Type signature updated to `float | None` |
| BUG-016 | **FIXED** | `MAX_PAGES = 50` safety cap added |
| BUG-017 | **FIXED** | `logger.info` added for state-level fallback |
| BUG-018 | **FIXED** | `paragraph.clear()` + `add_run()` pattern |
| BUG-019 | **NOT A BUG** | Offset properly scoped within function (Agent 2 verified) |
| BUG-020 | DEFERRED | Field rename is cosmetic; tracked in CLAUDE.md Rule 1 backlog |
| BUG-021 | **FIXED** | Sorted by `action_date` before taking last |
| BUG-022 | DEFERRED | Edge case is theoretical; `hit_count or 0` handles None |
| BUG-023 | DEFERRED | Needs investigation of full call chain |
| BUG-024 | **FIXED** | `try/except OSError` around `iterdir()` |
| BUG-025 | **NOT A BUG** | 592 * ~10KB = ~6MB; within acceptable memory |
| BUG-026 | DEFERRED | Fuzzy tie-breaking cosmetic; no functional impact |
| BUG-027 | DEFERRED | Workflow SHA-pinning is ops concern, not code bug |

## Consolidated Unique Bugs (Deduplicated)

### P1 - Must Fix

| ID | File | Lines | Description |
|----|------|-------|-------------|
| BUG-001 | src/packets/awards.py | 482-484 | Non-atomic cache write: uses `open(w)` not atomic tmp+replace pattern |
| BUG-002 | src/paths.py | 181-199 | Helper functions `award_cache_path()`, `hazard_profile_path()`, etc. have NO path traversal guard |
| BUG-003 | src/scrapers/base.py | 96-117 | 429 retry can hot-spin when Retry-After=0 (min should be 1s) |
| BUG-004 | src/utils.py | 22 | `format_dollars()` produces `$-1,234,567` not `-$1,234,567` for negatives |
| BUG-005 | scripts/build_congress_cache.py | 588,922 | `int(district)` unguarded -- ValueError/TypeError on non-numeric API data |
| BUG-006 | src/scrapers/usaspending.py | 191-200 | `except Exception: break` drops remaining pages, no exc_info logging |
| BUG-007 | src/packets/docx_sections.py | 423-425 | `congressional_intel.get()` without None guard on nested access |

### P2 - Should Fix

| ID | File | Lines | Description |
|----|------|-------|-------------|
| BUG-008 | src/packets/orchestrator.py | 570-608 | Congressional intel cache uses `{}` as sentinel (never retried on failure) |
| BUG-009 | scripts/build_congressional_intel.py | 283-288 | Empty action_date passes Pydantic validation as empty string |
| BUG-010 | src/scrapers/congress_gov.py | 254 | bill_number used in URL without numeric validation |
| BUG-011 | src/scrapers/base.py | 86-88 | Method guard uses `hasattr` (too broad, catches unrelated attrs) |
| BUG-012 | src/packets/awards.py | 587-591 | `_compute_trend` off-by-one: `fy_range[:-2]` empty on 2-year range |
| BUG-013 | src/main.py | 133-157 | `_save_source_cache()` missing symlink check (asymmetric with read guard) |
| BUG-014 | src/packets/orchestrator.py | 887/1061 | Divergent state-save paths between single/all-tribes modes |
| BUG-015 | src/packets/hazards.py | 816 | `_safe_float(default=None)` violates type signature (should be float) |
| BUG-016 | src/scrapers/usaspending.py | 140-218 | `fetch_tribal_awards_for_cfda` has NO safety cap on pagination |
| BUG-017 | src/packets/hazards.py | 499-507 | State-level NRI fallback emits no warning log |
| BUG-018 | src/packets/docx_sections.py | 405-409 | `cell.text=` instead of `paragraph.clear()` creates ghost empty run |
| BUG-019 | scripts/build_congress_cache.py | 693-698 | Pagination fragility with variable shadowing |

### P3 - Low Priority

| ID | File | Lines | Description |
|----|------|-------|-------------|
| BUG-020 | src/schemas/models.py | 286 | `fy26_funding` field name hardcodes fiscal year (CLAUDE.md Rule 1) |
| BUG-021 | scripts/build_congressional_intel.py | 293 | `latest_action = actions[-1]` assumes chronological order |
| BUG-022 | src/scrapers/grants_gov.py | 142 | Pagination edge case with `hit_count or 0` |
| BUG-023 | src/packets/docx_sections.py | 938 | `_render_timing_note` called without `doc_type_config` |
| BUG-024 | src/packets/hazards.py | 213 | `_detect_nri_version` iterdir can raise OSError |
| BUG-025 | src/packets/orchestrator.py | 213-220 | 592 contexts held in memory simultaneously |
| BUG-026 | src/packets/awards.py | 281 | Fuzzy score `>` instead of `>=`, ties not logged |
| BUG-027 | .github/workflows/daily-scan.yml | 17,20 | Not SHA-pinned (inconsistency with other workflows) |

## Anti-Pattern Scan Results (Manual Grep)

All clean:
- `utcnow()`: 0 violations
- `open()` without encoding: 0 violations (all 65+ calls have encoding="utf-8")
- Mutable defaults `def.*=[]`: 0 violations
- Bare `except:`: 0 violations
- `write_text()`: All have encoding="utf-8"
- `os.environ`: Only 2 calls, safe `.get()` defaults
- `subprocess`/`eval`/`exec`: 0 violations
- `.format()` with user input: 0 violations
- `json.load()` in src/: All dynamic caches have 10MB size guards
- aiohttp sessions: Proper per-request timeouts

Acceptable patterns:
- `except Exception:` 31 instances (scrapers/monitors -- expected resilience)
- `json.load()` in scripts/: ~21 calls without size guards (CLI scripts, acceptable)
