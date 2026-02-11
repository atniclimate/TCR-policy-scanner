# Enhancement Proposal: Confidence Scoring Architecture

**Author:** Horizon Walker, TCR Policy Scanner Research Team
**Date:** 2026-02-11
**Status:** Proposed
**Effort:** 13 story points across 2 sprints

---

## Problem

The TCR Policy Scanner aggregates data from multiple federal sources with
fundamentally different reliability levels. A direct USASpending API award record
is factual -- it represents an actual obligation event recorded in the federal
financial system. A Federal Register notice parsed for funding amounts is generally
reliable but depends on text extraction accuracy. An ecoregion-to-program inference
derived from geographic classification is useful but inherently approximate.

Today, all of these data types arrive in the pipeline with equal implicit weight.
A Tribal Leader reading their advocacy packet sees a funding figure from USASpending
next to an estimated economic impact from published multipliers, and both are
presented with the same visual authority. The 16-program CI scores (ranging from
0.12 for FEMA BRIC to 0.93 for DOT PROTECT) capture policy risk but not data
quality.

When data ages, its reliability degrades. The hazard profiles in
`data/hazard_profiles/` currently show all zeros for all 592 Tribes (NRI county
data not yet loaded), which means the system is silently operating on empty data.
The award caches in `data/award_cache/` also show zero awards for many Tribes --
but is that because the Tribe has no awards, or because the USASpending matching
has not been run against live API data yet? Without confidence scores, there is no
way to distinguish "confirmed zero" from "data not yet loaded."

This matters because Tribal Leaders make real decisions based on this data. A packet
that says "No federal climate resilience awards found" should communicate whether
that means "we checked and found nothing" or "we have not checked yet."

## Vision

Every data point in the pipeline carries a confidence score from 0.0 to 1.0 that
propagates through transformations and appears in output documents. A Tribal Leader
looking at their advocacy packet sees not just the data, but a clear signal of how
much to trust it. The confidence score answers: "How sure are we about this?"

The system distinguishes between:
- **Confirmed data** (score 0.85-1.0): API-verified, cross-referenced, fresh
- **Inferred data** (score 0.50-0.84): Derived from geographic or programmatic logic
- **Stale data** (score below 0.50): Older than 90 days with no refresh
- **Missing data** (score 0.0): Placeholder, not yet loaded

This is not just metadata. This is an act of honesty. Every Tribal Leader deserves
to know the strength of the evidence behind the intelligence they are using to
advocate for their community.

## Technical Approach

### Confidence Score Model

Each data point receives a base confidence score from its source tier, modified by
freshness and cross-reference factors:

```
final_confidence = base_tier_score * freshness_decay * cross_reference_bonus
```

#### Base Tier Scores

| Tier | Score | Description | Examples |
|------|-------|-------------|----------|
| T1: Direct API Record | 1.00 | Primary source, structured data | USASpending award record, Congress.gov bill status |
| T2: Cross-Referenced | 0.95 | Confirmed across 2+ sources | Award matched by CFDA + recipient name + state |
| T3: Parsed Structured | 0.85 | Extracted from structured federal documents | Federal Register funding notice, Grants.gov opportunity |
| T4: Derived/Inferred | 0.70 | Computed from other data via rules | Ecoregion mapping, hazard-to-program relevance |
| T5: Manual/Static | 0.60 | Manually curated, not auto-refreshed | Program inventory CI scores, Hot Sheets status |
| T6: Placeholder | 0.00 | Schema present but data not loaded | Empty hazard profiles, unpopulated award caches |

#### Freshness Decay

Data degrades over time. The decay function uses a sigmoid curve that holds steady
for 30 days, then degrades through 90 days:

```python
import math
from datetime import datetime, timezone

def freshness_decay(generated_at: str, decay_start_days: int = 30,
                    decay_end_days: int = 90) -> float:
    """Compute freshness decay factor (1.0 = fresh, 0.3 = stale).

    Holds at 1.0 for decay_start_days, then decays via sigmoid
    to 0.3 at decay_end_days. Never drops below 0.3 (data exists
    but is stale, not gone).
    """
    if not generated_at:
        return 0.0  # No timestamp = placeholder

    age_days = (datetime.now(timezone.utc) -
                datetime.fromisoformat(generated_at)).days

    if age_days <= decay_start_days:
        return 1.0

    if age_days >= decay_end_days:
        return 0.3

    # Sigmoid decay between start and end
    progress = (age_days - decay_start_days) / (decay_end_days - decay_start_days)
    return 1.0 - 0.7 * (1 / (1 + math.exp(-10 * (progress - 0.5))))
```

#### Cross-Reference Bonus

When a data point is confirmed by multiple independent sources, confidence increases:

| Cross-Reference | Bonus Factor |
|-----------------|-------------|
| Single source | 1.00 (no bonus) |
| 2 sources agree | 1.05 (capped at 1.0 for final score) |
| 3+ sources agree | 1.10 (capped at 1.0 for final score) |

Example: A USASpending award (T1, base 1.00) matched by both CFDA number and
rapidfuzz name matching (two independent signals) receives a cross-reference
bonus of 1.05, producing a final confidence of min(1.0, 1.00 * 1.0 * 1.05) = 1.0.

### Data Model

Confidence scores attach to data at the field level, not the document level.
A single Tribe's award cache might contain:

```json
{
  "tribe_id": "epa_100000123",
  "tribe_name": "Muckleshoot Indian Tribe",
  "_confidence": {
    "tribe_id": {"score": 1.0, "tier": "T1", "source": "epa_api", "as_of": "2026-02-10"},
    "awards": {"score": 0.95, "tier": "T2", "source": "usaspending_api+alias_match", "as_of": "2026-02-10"},
    "total_obligation": {"score": 0.95, "tier": "T2", "source": "usaspending_api", "as_of": "2026-02-10"}
  },
  "awards": [...],
  "total_obligation": 1250000,
  "award_count": 3
}
```

The `_confidence` dict is a parallel metadata structure that rides alongside the
data without modifying existing field schemas. This preserves backward compatibility
with all v1.1 code that reads these files.

### Pipeline Integration

Confidence scores propagate through the 6-stage pipeline:

```
Stage 1: Ingest
  └── Each scraped item gets source-tier confidence
      (congress_gov -> T1, federal_register -> T3, grants_gov -> T3, usaspending -> T1)

Stage 2: Normalize
  └── Confidence preserved; text extraction steps may degrade tier
      (e.g., amount extracted from text -> T3, not T1)

Stage 3: Graph Construction
  └── Nodes inherit confidence from source data
      ProgramNode.confidence_index stays (policy risk)
      ProgramNode._data_confidence added (data quality)
      Edge metadata includes confidence of the relationship

Stage 4: Monitors
  └── Monitor outputs carry confidence based on input data
      IIJA sunset countdown: T1 (statutory date is fixed)
      Reconciliation watch: T3 (parsed from congressional actions)

Stage 5: Decision Engine
  └── Advocacy goals inherit minimum confidence of input factors
      If hazard data is T6 (placeholder), hazard-based goals flag as low-confidence

Stage 6: Reporting
  └── Confidence scores render in output documents (see below)
```

### TribePacketContext Integration

The existing `TribePacketContext` dataclass (`src/packets/context.py`) gains a
confidence summary:

```python
@dataclass
class TribePacketContext:
    # ... existing fields ...

    # Confidence metadata (new)
    confidence_summary: dict = field(default_factory=dict)
    # Example:
    # {
    #   "overall": 0.72,
    #   "identity": 1.0,     # EPA registry data
    #   "congressional": 0.95, # Congress.gov API + Census crosswalk
    #   "awards": 0.0,        # Not yet loaded
    #   "hazards": 0.0,       # NRI data not loaded
    #   "economic": 0.0,      # Depends on awards + hazards
    # }
```

The overall confidence is the weighted average of section confidences, using weights
that reflect advocacy importance:

| Section | Weight | Rationale |
|---------|--------|-----------|
| Identity | 0.10 | Foundational but rarely wrong |
| Congressional | 0.15 | Important for advocacy routing |
| Awards | 0.30 | Core evidence for funding arguments |
| Hazards | 0.30 | Core evidence for risk arguments |
| Economic | 0.15 | Multiplier of awards + hazards |

### DOCX Output Rendering

Confidence scores appear in the advocacy packet as a visual indicator:

**Section-level confidence badges:**
Each major section of the DOCX packet gets a confidence indicator in its header:

```
Federal Award History                          Data Confidence: HIGH (0.95)
─────────────────────────────────────────────────────────────────────────
[award data here]
```

**Color coding (aligns with existing CI status color palette):**

| Score Range | Label | Color | Meaning |
|-------------|-------|-------|---------|
| 0.85 - 1.00 | HIGH | Green (#2E7D32) | Verified, current, reliable |
| 0.50 - 0.84 | MODERATE | Amber (#F57F17) | Usable with caveats |
| 0.01 - 0.49 | LOW | Red (#C62828) | Stale or incomplete |
| 0.00 | NOT LOADED | Gray (#757575) | Data not yet available |

**Packet-level summary table** (appears on page 1):

```
╔═══════════════════════════════════════════════════════════╗
║  Data Quality Summary                                     ║
║                                                           ║
║  Identity & Registration     ████████████████████  HIGH   ║
║  Congressional Delegation    ████████████████████  HIGH   ║
║  Federal Award History       ░░░░░░░░░░░░░░░░░░░  N/A    ║
║  Hazard Profile              ░░░░░░░░░░░░░░░░░░░  N/A    ║
║  Economic Impact             ░░░░░░░░░░░░░░░░░░░  N/A    ║
║                                                           ║
║  Overall Data Confidence: 0.38 (MODERATE)                 ║
║  Last Full Refresh: 2026-02-10                            ║
╚═══════════════════════════════════════════════════════════╝
```

This summary tells the reader, at a glance, which sections of their packet are
backed by strong data and which sections need data population.

### Current Data Quality Snapshot

Based on the existing data files as of 2026-02-11:

| Data Source | Files | Coverage | Current Quality |
|-------------|-------|----------|----------------|
| Tribal Registry (`tribal_registry.json`) | 1 | 592/592 Tribes | T1 (1.0) -- EPA API source |
| Congressional Cache (`congressional_cache.json`) | 1 | 538 members | T2 (0.95) -- Congress.gov + Census |
| Tribal Aliases (`tribal_aliases.json`) | 1 | 3,751 aliases | T5 (0.60) -- manually curated |
| Award Cache (`data/award_cache/`) | 592 | 592 files, 0 populated | T6 (0.00) -- schema only |
| Hazard Profiles (`data/hazard_profiles/`) | 592 | 592 files, 0 populated | T6 (0.00) -- NRI not loaded |
| Program Inventory (`program_inventory.json`) | 1 | 16 programs | T5 (0.60) -- manual + Hot Sheets |
| Graph Schema (`graph_schema.json`) | 1 | 20 authorities, 13 barriers | T5 (0.60) -- manual |
| Ecoregion Config (`ecoregion_config.json`) | 1 | 7 NCA5 regions | T4 (0.70) -- geographic inference |

**Current overall system confidence: approximately 0.36** -- driven primarily by the
unpopulated award and hazard caches. Populating these two data sources would raise
overall system confidence to approximately 0.78.

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| `src/packets/context.py` | Exists (v1.1) | Add `confidence_summary` field |
| `src/packets/docx_engine.py` | Exists (v1.1) | Add confidence rendering |
| `src/packets/docx_styles.py` | Exists (v1.1) | Add confidence color mappings |
| `src/analysis/relevance.py` | Exists (v1.0) | Attach confidence to scored items |
| `src/graph/schema.py` | Exists (v1.0) | Add `_data_confidence` to node types |
| Data cache population | v1.2 tech debt | Required to move scores above T6 |

## Effort Estimate

### Phase 1: Core Scoring Model (8 SP, Sprint 1)

- Define `ConfidenceScore` dataclass with tier, freshness, cross-reference
- Implement `freshness_decay()` function
- Add `_confidence` metadata to all data cache schemas
- Attach source-tier confidence in all 4 scrapers
- Propagate through `ChangeDetector` and `RelevanceScorer`
- Tests: 20-25 new tests

### Phase 2: Output Integration (5 SP, Sprint 2)

- Add `confidence_summary` to `TribePacketContext`
- Implement DOCX confidence badge rendering in `DocxEngine`
- Add packet-level data quality summary table
- Update strategic overview with aggregate confidence metrics
- Color-code section headers by confidence level
- Tests: 10-15 new tests

**Total: 13 story points across 2 sprints (~4 weeks)**

## Impact Statement: How This Serves Tribal Sovereignty

Data sovereignty is not just about who controls the data -- it is about the quality
and transparency of the data that informs decisions. When a Tribal Leader walks into
a congressional meeting with an advocacy packet, they need to know the strength of
every number in that document.

A confidence scoring system turns implicit assumptions into explicit signals. Instead
of presenting a hazard profile with all zeros and hoping the reader understands that
the data has not been loaded yet, the system clearly labels it: "Data Confidence:
NOT LOADED." Instead of presenting a "first-time applicant opportunity" framing that
might actually mean "our matching algorithm has not been run yet," the system
distinguishes confirmed absence from missing data.

This transparency builds trust. A Tribal climate coordinator who sees "Data
Confidence: HIGH (0.95)" on their award history section knows she can cite those
numbers in testimony. One who sees "Data Confidence: LOW (0.38)" knows to seek
additional verification before making a funding argument.

For 592 Tribal Nations, honest data is more valuable than impressive data. The
confidence scoring system ensures that every piece of intelligence this tool
produces comes with a clear, calibrated assessment of its reliability.

That honesty is itself an act of respect.

---

*Proposed by Horizon Walker. Every number deserves a truth label.*
