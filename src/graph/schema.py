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


# ── Edge Types ──

@dataclass
class Edge:
    """Directed relationship between two nodes."""
    source_id: str
    target_id: str
    edge_type: str        # AUTHORIZED_BY, FUNDED_BY, BLOCKED_BY, MITIGATED_BY
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
