# Phase 15 Plan 01: Data Model Contract Summary

Congressional Pydantic models (BillAction, BillIntelligence, VoteRecord, Legislator, CongressionalIntelReport), TribePacketContext extension with congressional_intel dict, confidence scoring module with exponential freshness decay, and BillNode/LegislatorNode graph schema additions with 4 edge types.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add congressional Pydantic models to schemas/models.py | e7500ee | src/schemas/models.py |
| 2 | Extend TribePacketContext + create confidence module + extend graph schema | 5b024d1 | src/packets/context.py, src/packets/confidence.py, src/graph/schema.py |

## What Was Built

### Congressional Pydantic Models (INTEL-05)

Five models added to `src/schemas/models.py`:

- **BillAction**: Legislative action with date, text, action_type, chamber
- **BillIntelligence**: Full bill record with sponsorship, committees, subjects, relevance scoring, matched programs; field_validator restricts bill_type to 8 valid Congress.gov codes (HR, S, HJRES, SJRES, HCONRES, SCONRES, HRES, SRES)
- **VoteRecord**: Roll call vote with chamber, result, yea/nay counts
- **Legislator**: Lightweight member reference with bioguide_id, committees, sponsored/cosponsored bills
- **CongressionalIntelReport**: Top-level container with tribe_id, bills, delegation_enhanced flag, confidence dict, scan_date

### TribePacketContext Extension (INTEL-06)

Added `congressional_intel: dict = field(default_factory=dict)` to TribePacketContext dataclass. Backward compatible -- defaults to empty dict. Carries bill intelligence, enhanced delegation, committee activity, appropriations status, scan_date, and confidence scores from PacketOrchestrator to DOCX renderers.

### Confidence Scoring Module (INTEL-08)

Created `src/packets/confidence.py` with three functions:

- **compute_confidence(source_weight, last_updated, decay_rate, reference_date)**: Exponential decay `confidence = weight * e^(-lambda * days)`. Default decay_rate=0.01 gives ~69 day half-life. Returns float 0.0-1.0 rounded to 3 decimal places.
- **confidence_level(score)**: Maps to "HIGH" (>=0.7), "MEDIUM" (0.4-0.69), "LOW" (<0.4)
- **section_confidence(source, last_updated, ...)**: Convenience wrapper returning dict with score, level, source, last_updated

DEFAULT_SOURCE_WEIGHTS dict maps 6 sources to authority weights (congress_gov=0.80, federal_register=0.90, grants_gov=0.85, usaspending=0.70, congressional_cache=0.75, inferred=0.50).

### Graph Schema Extension (INTEL-14)

Added to `src/graph/schema.py`:

- **BillNode**: id, congress, bill_type, bill_number, title, status, relevance_score, sponsor_id, introduced_date
- **LegislatorNode**: id (bioguide_id), name, chamber, state, district, party

Documented 4 new edge types: SPONSORED_BY, REFERRED_TO, AFFECTS_PROGRAM, DELEGATES_TO.

## Requirements Met

| Requirement | Description | Status |
|-------------|-------------|--------|
| INTEL-05 | Congressional Pydantic models with validations | PASS |
| INTEL-06 | TribePacketContext extended with congressional_intel | PASS |
| INTEL-08 | Confidence scoring module (compute_confidence, confidence_level, section_confidence) | PASS |
| INTEL-14 | BillNode, LegislatorNode in graph schema with edge documentation | PASS |

## Deviations from Plan

None -- plan executed exactly as written.

## Test Results

- 743 existing tests: ALL PASS (zero regressions)
- Verification checks: 5/5 PASS
- Duration: 68.17s test suite runtime

## Key Files

### Created
- `src/packets/confidence.py` -- confidence scoring pure-function module

### Modified
- `src/schemas/models.py` -- 5 congressional Pydantic models + BILL_TYPE_CODES frozenset
- `src/packets/context.py` -- congressional_intel field added to TribePacketContext
- `src/graph/schema.py` -- BillNode, LegislatorNode dataclasses + edge type documentation

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| DEC-1501-01 | Legislator model kept lightweight vs full CongressionalDelegate | BillIntelligence needs sponsor/cosponsor references, not full committee assignments and contact info |
| DEC-1501-02 | Confidence decay_rate=0.01 (~69 day half-life) | Congressional session data remains relevant for months; rapid decay would undervalue recent legislation |
| DEC-1501-03 | DEFAULT_SOURCE_WEIGHTS as module-level dict | Allows override by callers while providing sensible defaults matching scanner_config.json authority_weight pattern |

## Next Steps

This data contract unblocks:
- **Plan 15-02** (Congress.gov API client): BillIntelligence model defines the shape of API responses
- **Plan 15-03** (Congressional intelligence cache): CongressionalIntelReport defines the cache file format
- **Plan 15-04** (Scout agent): Uses all models to produce intelligence reports
- **Plan 15-05** (Fire Keeper agent): Consumes TribePacketContext.congressional_intel for DOCX rendering

## Execution Metadata

- **Started:** 2026-02-12T07:46:07Z
- **Completed:** 2026-02-12T08:06:40Z
- **Duration:** ~20 minutes
- **Tasks:** 2/2
- **Commits:** 2
