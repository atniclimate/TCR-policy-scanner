# Phase 3 Plan 2: Advocacy Decision Engine Summary

**One-liner:** 5-rule priority-ordered decision engine classifying programs into advocacy goals (Urgent Stabilization, Restore/Replace, Protect Base, Direct Access Parity, Expand and Strengthen) with secondary_rules transparency and configurable urgency threshold.

---

## Frontmatter

- **Phase:** 03-monitoring-logic
- **Plan:** 02
- **Type:** TDD
- **Subsystem:** analysis
- **Tags:** decision-engine, advocacy-goals, classification, rules-engine, TDD
- **Requires:** Phase 2 (enriched graph with authorities, funding vehicles, barriers)
- **Provides:** DecisionEngine with classify_all() for all 16 programs
- **Affects:** Phase 3 Plan 3 (pipeline integration), Phase 4 (report display of advocacy goals)

### Tech Tracking

- **tech-stack.added:** pytest (test framework, dev dependency)
- **tech-stack.patterns:** Priority-ordered rule chain, graph edge queries with direction filtering

### Metrics

- **Duration:** ~5 minutes
- **Completed:** 2026-02-09
- **Tests:** 45 passing
- **Test execution time:** 0.12s

---

## Performance

| Metric | Value |
|--------|-------|
| Tests written | 45 |
| Tests passing | 45 |
| Test execution time | 0.12s |
| Implementation LoC | ~380 |
| Test LoC | ~670 |

---

## TDD Phases

### RED Phase

Wrote 45 test cases across 10 test classes covering:

- **TestAdvocacyGoals** (3 tests): ADVOCACY_GOALS constant has 5 goals with correct keys and human-readable labels
- **TestLogic05UrgentStabilization** (6 tests): THREATENS edge within/at/beyond threshold, custom threshold, override of LOGIC-01, reason text
- **TestLogic01RestoreReplace** (5 tests): TERMINATED/FLAGGED with permanent authority, STABLE exclusion, expiring authority exclusion, reason includes citation
- **TestLogic02ProtectBase** (6 tests): Discretionary + eliminate/reduce alerts, AT_RISK/UNCERTAIN status, mandatory exclusion, program-level funding_type fallback
- **TestLogic03DirectAccessParity** (3 tests): State pass-through + high admin barrier, direct access exclusion, low severity exclusion
- **TestLogic04ExpandStrengthen** (5 tests): STABLE/SECURE/STABLE_BUT_VULNERABLE with direct/set_aside/tribal_set_aside, AT_RISK exclusion, missing access_type exclusion
- **TestDefaultNoMatch** (3 tests): None goal, reason present, every program gets classification
- **TestClassificationShape** (3 tests): Required fields present on matched and default classifications, goal_label matches ADVOCACY_GOALS
- **TestPriorityOrdering** (3 tests): LOGIC-05 > LOGIC-01, LOGIC-01 > LOGIC-02, LOGIC-02 > LOGIC-04
- **TestSecondaryRules** (3 tests): Secondary rule collection, empty when single match, empty on default
- **TestEdgeCases** (5 tests): Empty graph, empty programs, missing ci_status, missing edges key, default config

All tests failed with `ModuleNotFoundError` (expected -- module did not exist).

### GREEN Phase

Implemented `src/analysis/decision_engine.py` with:

- `ADVOCACY_GOALS` constant mapping 5 goal keys to human-readable labels
- `DecisionEngine` class accepting config dict and programs dict
- `classify_all(graph_data, alerts)` iterating over all programs
- `_classify_program()` evaluating all 5 rules, collecting matches, returning highest-priority as primary with secondary_rules
- 5 private rule methods each returning classification dict or None
- `_get_edges_for_program()` helper with direction filtering (source/target/any)
- `_has_discretionary_funding()` checking graph edges then falling back to program-level field
- `_has_eliminate_reduce_signal()` checking alerts, THREATENS edges, and ci_status
- DEBUG-level logging for each classification decision

All 45 tests passed on first run.

### REFACTOR Phase

Minor cleanup:
- Removed unused `_RULE_ORDER` constant (priority is implicit in evaluation list order)
- Replaced `typing.Optional` import with Python 3.13 native `dict | None` syntax
- All 45 tests continued passing

---

## Task Commits

| Phase | Commit | Message |
|-------|--------|---------|
| RED | b8ec13e | test(03-02): add failing tests for advocacy decision engine |
| GREEN | 105560f | feat(03-02): implement advocacy decision engine |
| REFACTOR | 7072ce1 | refactor(03-02): clean up advocacy decision engine |

---

## Files Created

| File | Purpose |
|------|---------|
| `src/analysis/decision_engine.py` | DecisionEngine with 5 advocacy goal rules, ADVOCACY_GOALS constant |
| `tests/__init__.py` | Test package init |
| `tests/test_decision_engine.py` | 45 test cases covering all 5 rules, priority, defaults, edge cases |

## Files Modified

None -- this plan only created new files.

---

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Rule evaluation as explicit list, not data-driven | 5 rules is too few to justify a dispatch table; explicit list is clearer and matches the existing codebase style |
| FLAGGED treated as near-TERMINATED for LOGIC-01 | Per plan specification; FEMA BRIC at CI 0.12 is FLAGGED and needs Restore/Replace classification |
| AT_RISK/UNCERTAIN with discretionary = threat signal for LOGIC-02 | Status itself indicates risk; combined with discretionary funding confirms Protect Base need |
| access_type required for LOGIC-03 and LOGIC-04 | Programs without explicit access_type fall through gracefully to default classification |
| Alerts accessed via getattr() for duck-typing compatibility | Tests can use simple mock objects; MonitorAlert dataclass and test mocks both work |
| Removed _RULE_ORDER constant in refactor | Unused constant; priority ordering is enforced by the evaluation list in _classify_program() |

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed pytest**
- **Found during:** RED phase setup
- **Issue:** pytest was not installed in the environment
- **Fix:** Ran `pip install pytest`
- **Rationale:** Cannot run TDD without a test framework

**2. [Rule 3 - Blocking] Created tests/__init__.py**
- **Found during:** RED phase
- **Issue:** No tests directory or package init existed
- **Fix:** Created `tests/` directory and `tests/__init__.py`
- **Rationale:** Required for Python test discovery

---

## Issues Encountered

None.

---

## Next Phase Readiness

**Ready for 03-03 (Signal monitors + pipeline integration):**
- DecisionEngine is importable and tested
- classify_all() accepts graph_data dict and alerts list (compatible with MonitorRunner output from 03-01)
- Classification dict shape is stable and documented
- Pipeline integration in 03-03 will wire MonitorRunner alerts into DecisionEngine.classify_all()

**Requirements addressed:**
- LOGIC-01: Restore/Replace for TERMINATED + active authority
- LOGIC-02: Protect Base for discretionary + eliminate/reduce signals
- LOGIC-03: Direct Access Parity for state pass-through + high admin burden
- LOGIC-04: Expand and Strengthen for STABLE/SECURE + direct/set-aside
- LOGIC-05: Urgent Stabilization override for THREATENS within threshold

---
*Summary created: 2026-02-09*
