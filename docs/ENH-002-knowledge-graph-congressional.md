# ENH-002: Knowledge Graph Congressional Extension

**Status:** Proposed
**Requirement:** INTEL-14
**Priority:** P3 (after alert system)
**Author:** Phase 15 Planning
**Date:** 2026-02-12

---

## 1. Overview

The knowledge graph currently models policy intelligence through five node types (ProgramNode, AuthorityNode, FundingVehicleNode, BarrierNode, AdvocacyLeverNode) connected by edges that trace statutory authority, funding pipelines, and advocacy pathways. This extension adds congressional intelligence as first-class graph entities, enabling graph traversals that answer questions like "Which bills affect my programs?" and "Which of my legislators sit on relevant committees?"

**Design goal:** Tribal Leaders should be able to trace any bill back to the programs it affects, the legislators who sponsor it, and the committees with jurisdiction -- all in a single graph query.

**Existing graph:** Defined in `src/graph/schema.py` and `data/graph_schema.json`. This extension adds nodes and edges without modifying existing types.

---

## 2. New Node Types

### 2.1 BillNode

Represents a congressional bill or resolution tracked by the intelligence pipeline.

```python
@dataclass
class BillNode:
    """Congressional bill tracked for Tribal climate resilience relevance."""
    id: str                  # e.g., "bill_119_hr_1234"
    congress: int            # e.g., 119
    bill_type: str           # "hr", "s", "hres", "sres", "hjres", "sjres"
    bill_number: int         # e.g., 1234
    title: str               # Official bill title
    status: str              # "Introduced", "Committee", "Floor", "Enrolled", etc.
    relevance_score: float   # 0.0-1.0, from bill_relevance_scoring()
    sponsor_id: str          # Bioguide ID of primary sponsor (e.g., "C001120")
    introduced_date: str     # ISO 8601 date
```

**ID format:** `bill_{congress}_{type}_{number}` (e.g., `bill_119_hr_1234`)

**Source:** `data/congressional_intel.json` via CongressGovScraper

### 2.2 LegislatorNode

Represents a member of Congress (Senator or Representative).

```python
@dataclass
class LegislatorNode:
    """Member of Congress relevant to Tribal delegation tracking."""
    id: str          # Bioguide ID (e.g., "C001120")
    name: str        # Full name (e.g., "Dan Newhouse")
    chamber: str     # "Senate" or "House"
    state: str       # Two-letter state code (e.g., "WA")
    district: str    # District number or "At-Large" (House only; "" for Senate)
    party: str       # "R", "D", "I"
```

**ID format:** Bioguide ID (e.g., `C001120`), consistent with Congress.gov API

**Source:** `data/congressional_cache.json` members section

### 2.3 CommitteeNode

Represents a congressional committee or subcommittee with jurisdiction over Tribal affairs or climate programs.

```python
@dataclass
class CommitteeNode:
    """Congressional committee relevant to tracked programs."""
    id: str          # System code (e.g., "SLIA", "HSII")
    name: str        # Full name (e.g., "Senate Committee on Indian Affairs")
    chamber: str     # "Senate", "House", or "Joint"
```

**ID format:** Committee system code from Congress.gov (e.g., `SLIA` for Senate Committee on Indian Affairs)

**Source:** `data/congressional_cache.json` committees section

**Key committees tracked:**
| Code | Name | Relevance |
|------|------|-----------|
| SLIA | Senate Committee on Indian Affairs | Primary jurisdiction over Tribal legislation |
| HSII | House Natural Resources (Subcommittee on Indian and Insular Affairs) | Primary House jurisdiction |
| SSAP | Senate Appropriations | Funding for all tracked programs |
| HSAP | House Appropriations | Funding for all tracked programs |
| SSEG | Senate Energy and Natural Resources | Energy and land programs |
| SSCM | Senate Commerce, Science, and Transportation | Infrastructure programs |

### 2.4 VoteNode (Future)

Represents a recorded vote on a bill. Deferred pending Senate.gov structured vote data availability.

```python
@dataclass
class VoteNode:
    """Recorded vote on a bill (future implementation)."""
    id: str          # e.g., "vote_119_h_234"
    bill_id: str     # Reference to BillNode.id
    chamber: str     # "Senate" or "House"
    vote_date: str   # ISO 8601 date
    result: str      # "Passed", "Failed", "Agreed to"
```

**Status:** Future implementation. The Congress.gov API v3 provides vote data for the House but Senate structured vote data requires additional API integration.

---

## 3. New Edge Types

### 3.1 SPONSORED_BY

**Direction:** BillNode -> LegislatorNode
**Semantics:** The legislator is the primary sponsor of the bill.
**Cardinality:** Each bill has exactly one primary sponsor.

```
bill_119_hr_1234 --SPONSORED_BY--> C001120
  (Tribal Climate Resilience Act)    (Rep. Newhouse)
```

**Metadata:** None (sponsorship is binary).

### 3.2 REFERRED_TO

**Direction:** BillNode -> CommitteeNode
**Semantics:** The bill has been referred to this committee for consideration.
**Cardinality:** A bill may be referred to multiple committees (sequential or joint referral).

```
bill_119_hr_1234 --REFERRED_TO--> SLIA
  (Tribal Climate Resilience Act)    (Senate Indian Affairs)
```

**Metadata:**
- `referral_date`: ISO 8601 date of referral
- `referral_type`: "Primary" | "Secondary" | "Joint"

### 3.3 AFFECTS_PROGRAM

**Direction:** BillNode -> ProgramNode
**Semantics:** The bill, if enacted, would affect this program's funding, authorization, or administration.
**Cardinality:** A bill may affect multiple programs; a program may be affected by multiple bills.

```
bill_119_hr_1234 --AFFECTS_PROGRAM--> bia_tcr
  (Tribal Climate Resilience Act)      (BIA TCR Program)
  relevance_score: 0.92
```

**Metadata:**
- `relevance_score`: Float 0.0-1.0 from bill_relevance_scoring()
- `impact_type`: "Funding" | "Authorization" | "Administration" | "Mixed"

### 3.4 DELEGATES_TO

**Direction:** TribeNode -> LegislatorNode
**Semantics:** The legislator represents geographic areas overlapping with the Tribal Nation's territory.
**Cardinality:** Each Tribe typically has 2 Senators + 1-3 Representatives (depending on geographic overlap).

```
epa_100000171 --DELEGATES_TO--> M001153
  (Confederated Tribes of Warm Springs)  (Sen. Merkley)
  overlap_pct: 100.0
```

**Metadata:**
- `overlap_pct`: Float 0.0-100.0, percentage of Tribal land in the legislator's district/state
- `delegation_type`: "Senator" | "Representative"

### 3.5 MEMBER_OF

**Direction:** LegislatorNode -> CommitteeNode
**Semantics:** The legislator serves on this committee.
**Cardinality:** Legislators typically serve on 2-4 committees.

```
M001153 --MEMBER_OF--> SLIA
  (Sen. Merkley)    (Senate Indian Affairs)
  role: "Member"
```

**Metadata:**
- `role`: "Chair" | "Ranking Member" | "Member"
- `subcommittee`: Optional subcommittee name

### 3.6 VOTED_ON (Future)

**Direction:** LegislatorNode -> VoteNode
**Semantics:** The legislator cast a vote on this recorded vote.
**Cardinality:** Each legislator votes on many bills; each vote has many legislators.

```
M001153 --VOTED_ON--> vote_119_s_89
  (Sen. Merkley)      (S. 567 Final Passage)
  vote: "Yea"
```

**Metadata:**
- `vote`: "Yea" | "Nay" | "Present" | "Not Voting"

**Status:** Future implementation, pending VoteNode availability.

### 3.7 REPRESENTS

**Direction:** LegislatorNode -> TribeNode
**Semantics:** Inverse of DELEGATES_TO. The legislator represents this Tribal Nation.
**Cardinality:** A legislator may represent 0-50+ Tribal Nations depending on state/district.

```
M001153 --REPRESENTS--> epa_100000171
  (Sen. Merkley)        (Confederated Tribes of Warm Springs)
  overlap_pct: 100.0
```

**Metadata:** Same as DELEGATES_TO (mirrored).

**Purpose:** Enables reverse traversals: "Which Tribal Nations does this legislator represent?" This supports aggregate reporting for Doc C/D regional documents.

---

## 4. Edge Summary Table

| Edge | From | To | Metadata | Source |
|------|------|----|----------|--------|
| SPONSORED_BY | BillNode | LegislatorNode | None | congressional_intel.json |
| REFERRED_TO | BillNode | CommitteeNode | referral_date, referral_type | congressional_intel.json |
| AFFECTS_PROGRAM | BillNode | ProgramNode | relevance_score, impact_type | bill_relevance_scoring() |
| DELEGATES_TO | TribeNode | LegislatorNode | overlap_pct, delegation_type | congressional_cache.json |
| MEMBER_OF | LegislatorNode | CommitteeNode | role, subcommittee | congressional_cache.json |
| VOTED_ON | LegislatorNode | VoteNode | vote | Future (Congress.gov API) |
| REPRESENTS | LegislatorNode | TribeNode | overlap_pct | congressional_cache.json |

---

## 5. Query Examples

These graph traversal patterns demonstrate how the congressional extension enables policy intelligence queries that cross data source boundaries.

### 5.1 "Which bills affect programs tracked by Tribe X?"

**Use case:** A Tribal Leader wants to know what legislation could impact their climate resilience funding.

**Traversal:**
```
TribeNode(epa_100000171)
  -> [HAS_PROGRAM] -> ProgramNode(bia_tcr)
  -> [AFFECTS_PROGRAM (reverse)] -> BillNode(bill_119_hr_1234)
  -> return bill.title, bill.status, edge.relevance_score
```

**Result example:**
| Bill | Title | Status | Relevance |
|------|-------|--------|-----------|
| HR 1234 | Tribal Climate Resilience Act | Committee | 0.92 |
| S 567 | IIJA Tribal Set-Aside Extension | Floor | 0.85 |
| HR 8901 | Wildfire Mitigation Grants | Introduced | 0.71 |

### 5.2 "Which of Tribe X's legislators sponsored relevant bills?"

**Use case:** A Tribal Leader wants to identify allies in their delegation who are actively supporting relevant legislation.

**Traversal:**
```
TribeNode(epa_100000171)
  -> [DELEGATES_TO] -> LegislatorNode(M001153)
  -> [SPONSORED_BY (reverse)] -> BillNode(bill_119_s_567)
  -> filter: bill in (bills affecting Tribe's programs)
  -> return legislator.name, bill.title, bill.status
```

**Result example:**
| Legislator | Bill | Title | Status |
|-----------|------|-------|--------|
| Sen. Merkley | S 567 | IIJA Tribal Set-Aside Extension | Floor |

### 5.3 "Which committees have jurisdiction over Tribe X's programs?"

**Use case:** A Tribal Leader preparing testimony needs to know which committees to target.

**Traversal:**
```
TribeNode(epa_100000171)
  -> [HAS_PROGRAM] -> ProgramNode(bia_tcr, fema_bric, ...)
  -> [AFFECTS_PROGRAM (reverse)] -> BillNode(*)
  -> [REFERRED_TO] -> CommitteeNode(SLIA, HSII, ...)
  -> return committee.name, count(bills), committee.chamber
```

**Result example:**
| Committee | Bills Referred | Chamber |
|-----------|---------------|---------|
| Senate Committee on Indian Affairs | 4 | Senate |
| House Natural Resources (Indian Affairs) | 3 | House |
| Senate Appropriations | 2 | Senate |

### 5.4 "Which Tribal Nations share a legislative interest?" (Regional Query)

**Use case:** Doc C/D regional documents need to identify shared advocacy opportunities.

**Traversal:**
```
BillNode(bill_119_hr_1234)
  -> [AFFECTS_PROGRAM] -> ProgramNode(bia_tcr)
  -> [HAS_PROGRAM (reverse)] -> TribeNode(*)
  -> filter: Tribe.region == target_region
  -> return tribe.name, count(shared_bills)
```

**Result example:**
| Tribal Nation | Shared Bills | Region |
|--------------|-------------|--------|
| Confederated Tribes of Warm Springs | 5 | Pacific Northwest |
| Yakama Nation | 4 | Pacific Northwest |
| Nez Perce Tribe | 3 | Pacific Northwest |

---

## 6. Data Sources

| Data Source | Graph Entities Populated | Refresh Cadence |
|-------------|------------------------|-----------------|
| Congress.gov API v3 | BillNode, SPONSORED_BY, REFERRED_TO | Daily scan (weekday) |
| `data/congressional_cache.json` | LegislatorNode, CommitteeNode, DELEGATES_TO, MEMBER_OF, REPRESENTS | Monthly rebuild |
| `data/graph_schema.json` | ProgramNode (existing) | Updated per phase |
| bill_relevance_scoring() | AFFECTS_PROGRAM edges | Computed at scan time |

---

## 7. Implementation Notes

### 7.1 Graph Storage

The existing graph uses in-memory Python dataclasses (`src/graph/schema.py`) with JSON serialization to `data/graph_schema.json`. Congressional nodes and edges follow the same pattern -- no external graph database required.

### 7.2 ID Conventions

All node IDs are deterministic and derived from source data:
- BillNode: `bill_{congress}_{type}_{number}` (e.g., `bill_119_hr_1234`)
- LegislatorNode: Bioguide ID (e.g., `C001120`)
- CommitteeNode: System code (e.g., `SLIA`)
- VoteNode: `vote_{congress}_{chamber_abbrev}_{number}` (future)

### 7.3 Schema Extension Pattern

New node and edge types are added as new dataclasses in `src/graph/schema.py`. The graph builder (`src/graph/builder.py`) gains new methods to construct congressional subgraph from data sources. Existing nodes and edges are untouched.

### 7.4 Estimated Size

| Entity | Estimated Count | Notes |
|--------|----------------|-------|
| BillNode | 50-200 per scan | Filtered by relevance to tracked programs |
| LegislatorNode | ~535 | All current members of Congress |
| CommitteeNode | ~6-20 | Filtered to relevant committees |
| VoteNode | 0 (future) | Pending implementation |
| SPONSORED_BY edges | 50-200 | 1:1 with bills |
| REFERRED_TO edges | 75-300 | 1-2 committees per bill |
| AFFECTS_PROGRAM edges | 100-500 | Multiple programs per bill |
| DELEGATES_TO edges | ~2,500 | 501 Tribes x ~5 legislators avg |
| MEMBER_OF edges | ~1,500 | ~535 legislators x ~3 committees avg |
| REPRESENTS edges | ~2,500 | Mirror of DELEGATES_TO |

---

*This specification extends the knowledge graph defined in `src/graph/schema.py`. Implementation adds new dataclasses and graph builder methods without modifying existing node or edge types.*
