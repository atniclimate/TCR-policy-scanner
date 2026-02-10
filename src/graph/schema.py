"""Knowledge Graph schema definitions.

Defines the node and edge types used to organize scraped policy data
into a queryable graph structure linking Programs to their Statutory
Authorities, Funding Status, Barriers, and Advocacy Levers.
"""

from dataclasses import dataclass, field


# ── Node Types ──

@dataclass
class ProgramNode:
    """Central unit of advocacy (e.g. 'BIA Tribal Climate Resilience')."""
    id: str
    name: str
    agency: str
    confidence_index: float = 0.0
    fy26_status: str = ""
    priority: str = ""
    cfda: str = ""


@dataclass
class AuthorityNode:
    """Legal basis for a program (e.g. 'Stafford Act S 203')."""
    id: str
    citation: str
    authority_type: str = ""  # Statute / Regulation / Guidance
    durability: str = ""      # Permanent / Expires


@dataclass
class FundingVehicleNode:
    """Money pipeline (e.g. 'FY26 Consolidated Appropriations')."""
    id: str
    name: str
    amount: float = 0.0
    fiscal_year: str = ""
    funding_type: str = ""  # Discretionary / Mandatory / One-Time


@dataclass
class BarrierNode:
    """Obstacle identified in scraping (e.g. '50% Cost Share')."""
    id: str
    description: str
    barrier_type: str = ""  # Administrative / Statutory
    severity: str = ""      # High / Med / Low


@dataclass
class AdvocacyLeverNode:
    """Action to take (e.g. 'Waive Match')."""
    id: str
    description: str
    target: str = ""        # Congress / Agency
    action_verb: str = ""
    urgency: str = ""       # Immediate / FY26 / Ongoing


@dataclass
class TrustSuperNode:
    """Federal trust responsibility meta-node.

    Represents the overarching federal trust obligation to Tribal Nations,
    connecting to BIA and EPA programs that carry direct trust responsibility
    implications. Creates TRUST_OBLIGATION edges to connected programs.
    """
    id: str
    name: str
    description: str = ""
    legal_basis: str = ""


@dataclass
class ObligationNode:
    """Actual spending record from USASpending.gov."""
    id: str
    amount: float = 0.0
    recipient: str = ""
    fiscal_year: str = ""
    cfda: str = ""


@dataclass
class TribeNode:
    """Federally recognized Tribal Nation."""
    id: str              # epa_{epaTribalInternalId}
    name: str            # Official BIA name
    state: str = ""      # Primary state (or comma-separated for multi-state)
    ecoregion: str = ""  # Primary ecoregion


@dataclass
class CongressionalDistrictNode:
    """U.S. Congressional District (119th Congress)."""
    id: str              # e.g., "AZ-01", "AK-AL"
    state: str = ""
    representative: str = ""
    party: str = ""


# ── Edge Types ──

@dataclass
class Edge:
    """Directed relationship between two nodes.

    Edge types:
      AUTHORIZED_BY    (Program -> Authority)
      FUNDED_BY        (Program -> FundingVehicle)
      BLOCKED_BY       (Program -> Barrier)
      MITIGATED_BY     (Barrier -> AdvocacyLever)
      OBLIGATED_BY     (Program -> ObligationNode) — actual spending
      ADVANCES         (StructuralAsk -> Program)
      TRUST_OBLIGATION (TrustSuperNode -> Program)
      THREATENS        (ThreatNode -> Program) -- time-sensitive legislative threat
      REPRESENTED_BY  (TribeNode -> CongressionalDistrictNode) -- many-to-many Tribe-to-district
      IN_ECOREGION    (TribeNode -> ecoregion_id) -- Tribe's climate advocacy region
    """
    source_id: str
    target_id: str
    edge_type: str
    metadata: dict = field(default_factory=dict)


# ── Serialization helpers ──

def node_to_dict(node) -> dict:
    """Convert any node dataclass to a serializable dict."""
    d = {}
    for k, v in node.__dict__.items():
        d[k] = v
    d["_type"] = type(node).__name__
    return d


def edge_to_dict(edge: Edge) -> dict:
    return {
        "source": edge.source_id,
        "target": edge.target_id,
        "type": edge.edge_type,
        "metadata": edge.metadata,
    }
