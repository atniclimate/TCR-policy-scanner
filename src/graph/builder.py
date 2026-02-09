"""Knowledge Graph builder.

Constructs a graph linking Programs (nodes) to their Statutory Authorities,
Funding Vehicles, Barriers, and Advocacy Levers (edges) from scraped data
and the static graph schema.

The graph is built in two phases:
  1. Static seeding — loads known relationships from data/graph_schema.json
  2. Dynamic enrichment — infers new nodes and edges from scraped items
"""

import json
import logging
import re
from pathlib import Path

from src.graph.schema import (
    ProgramNode, AuthorityNode, FundingVehicleNode,
    BarrierNode, AdvocacyLeverNode, ObligationNode, Edge,
    node_to_dict, edge_to_dict,
)

logger = logging.getLogger(__name__)

GRAPH_SCHEMA_PATH = Path("data/graph_schema.json")

# Patterns for detecting barriers in scraped text
BARRIER_PATTERNS = [
    (r"(\d+)\s*%?\s*(?:cost[- ]share|match(?:ing)?(?:\s+requirement)?)", "Cost Share", "Administrative"),
    (r"(?:requires?|must\s+have)\s+(?:a\s+)?(?:hazard\s+)?mitigation\s+plan", "Plan Requirement", "Administrative"),
    (r"(?:requires?|must\s+have)\s+(?:a\s+)?(?:tribal\s+)?consultation", "Consultation Requirement", "Administrative"),
    (r"(?:new|additional)\s+reporting\s+requirement", "Reporting Requirement", "Administrative"),
    (r"(?:application|submission)\s+deadline", "Deadline", "Administrative"),
    # Bureaucratic friction signals (per Gemini research)
    (r"information\s+collection\s+(?:request|requirement)", "Information Collection / PRA", "Administrative"),
    (r"paperwork\s+reduction\s+act", "PRA Compliance", "Administrative"),
    (r"(?:new|revised)\s+(?:application|reporting)\s+form", "Form Change", "Administrative"),
]

# Patterns for detecting funding signals
FUNDING_PATTERNS = [
    (r"\$\s*([\d,.]+)\s*(million|billion|M|B)", "amount"),
    (r"FY\s*(\d{2,4})", "fiscal_year"),
    (r"(discretionary|mandatory|formula|competitive)", "funding_type"),
]

# Patterns for detecting authority citations
AUTHORITY_PATTERNS = [
    (r"(Stafford\s+Act(?:\s+[§S]\s*\d+)?)", "Statute"),
    (r"(Snyder\s+Act)", "Statute"),
    (r"(NAHASDA)", "Statute"),
    (r"(Infrastructure\s+Investment\s+and\s+Jobs\s+Act|IIJA|BIL)", "Statute"),
    (r"(Inflation\s+Reduction\s+Act|IRA)", "Statute"),
    (r"(Indian\s+Self[- ]Determination(?:\s+Act)?)", "Statute"),
    (r"(Clean\s+Water\s+Act|Safe\s+Drinking\s+Water\s+Act)", "Statute"),
    (r"(\d+\s+(?:U\.?S\.?C\.?|CFR)\s+[§S]?\s*[\d.]+(?:\([a-z]\))?)", "Statute"),
    (r"(Executive\s+Order\s+\d+)", "Guidance"),
    (r"((?:proposed|final|interim)\s+rule)", "Regulation"),
]


class KnowledgeGraph:
    """In-memory knowledge graph for TCR policy data."""

    def __init__(self):
        self.nodes: dict[str, dict] = {}
        self.edges: list[Edge] = []
        self._program_ids: set[str] = set()

    def add_node(self, node) -> None:
        """Add a node (any schema type) to the graph."""
        d = node_to_dict(node)
        self.nodes[d["id"]] = d
        if isinstance(node, ProgramNode):
            self._program_ids.add(node.id)

    def add_edge(self, edge: Edge) -> None:
        """Add an edge to the graph."""
        self.edges.append(edge)

    def get_program_subgraph(self, program_id: str) -> dict:
        """Return all nodes and edges connected to a program."""
        connected_edges = [e for e in self.edges
                           if e.source_id == program_id or e.target_id == program_id]
        connected_ids = {program_id}
        for e in connected_edges:
            connected_ids.add(e.source_id)
            connected_ids.add(e.target_id)
        return {
            "nodes": {k: v for k, v in self.nodes.items() if k in connected_ids},
            "edges": [edge_to_dict(e) for e in connected_edges],
        }

    def get_barriers_for_program(self, program_id: str) -> list[dict]:
        """Return all barriers blocking a specific program."""
        barrier_ids = [e.target_id for e in self.edges
                       if e.source_id == program_id and e.edge_type == "BLOCKED_BY"]
        return [self.nodes[bid] for bid in barrier_ids if bid in self.nodes]

    def get_levers_for_barrier(self, barrier_id: str) -> list[dict]:
        """Return advocacy levers that mitigate a specific barrier."""
        lever_ids = [e.target_id for e in self.edges
                     if e.source_id == barrier_id and e.edge_type == "MITIGATED_BY"]
        return [self.nodes[lid] for lid in lever_ids if lid in self.nodes]

    def to_dict(self) -> dict:
        """Serialize the full graph for JSON output."""
        return {
            "nodes": self.nodes,
            "edges": [edge_to_dict(e) for e in self.edges],
            "summary": {
                "total_nodes": len(self.nodes),
                "total_edges": len(self.edges),
                "programs": len(self._program_ids),
                "node_types": self._count_types(),
            },
        }

    def _count_types(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for node in self.nodes.values():
            t = node.get("_type", "Unknown")
            counts[t] = counts.get(t, 0) + 1
        return counts


class GraphBuilder:
    """Builds the knowledge graph from static schema + scraped data."""

    def __init__(self, programs: list[dict], schema_path: Path | None = None):
        self.programs = {p["id"]: p for p in programs}
        self.schema_path = schema_path or GRAPH_SCHEMA_PATH
        self.graph = KnowledgeGraph()

    def build(self, scored_items: list[dict]) -> KnowledgeGraph:
        """Build the full graph: seed from static schema, then enrich from scan."""
        self._seed_from_programs()
        self._seed_from_schema()
        self._enrich_from_items(scored_items)

        logger.info(
            "Knowledge Graph: %d nodes, %d edges",
            len(self.graph.nodes), len(self.graph.edges),
        )
        return self.graph

    def _seed_from_programs(self) -> None:
        """Create ProgramNodes from the program inventory."""
        for pid, prog in self.programs.items():
            node = ProgramNode(
                id=pid,
                name=prog["name"],
                agency=prog["agency"],
                confidence_index=prog.get("confidence_index", 0),
                fy26_status=prog.get("ci_status", ""),
                priority=prog.get("priority", ""),
                cfda=prog.get("cfda", ""),
            )
            self.graph.add_node(node)

            # Create advocacy lever nodes from program data
            if prog.get("advocacy_lever"):
                lever_id = f"lever_{pid}"
                lever = AdvocacyLeverNode(
                    id=lever_id,
                    description=prog["advocacy_lever"],
                    target="Congress" if "approp" in prog["advocacy_lever"].lower()
                           or "FY" in prog["advocacy_lever"]
                           else "Agency",
                    urgency="Immediate" if prog.get("ci_status") == "FLAGGED" else "FY26",
                )
                self.graph.add_node(lever)

    def _seed_from_schema(self) -> None:
        """Load static authority, funding, and barrier data from schema file."""
        if not self.schema_path.exists():
            logger.info("No graph schema file at %s, skipping static seed", self.schema_path)
            return

        with open(self.schema_path) as f:
            schema = json.load(f)

        # Authorities
        for auth in schema.get("authorities", []):
            node = AuthorityNode(
                id=auth["id"],
                citation=auth["citation"],
                authority_type=auth.get("type", ""),
                durability=auth.get("durability", ""),
            )
            self.graph.add_node(node)
            for pid in auth.get("programs", []):
                self.graph.add_edge(Edge(
                    source_id=pid,
                    target_id=auth["id"],
                    edge_type="AUTHORIZED_BY",
                ))

        # Funding vehicles
        for fv in schema.get("funding_vehicles", []):
            node = FundingVehicleNode(
                id=fv["id"],
                name=fv["name"],
                amount=fv.get("amount", 0),
                fiscal_year=fv.get("fiscal_year", ""),
                funding_type=fv.get("type", ""),
            )
            self.graph.add_node(node)
            for pid in fv.get("programs", []):
                self.graph.add_edge(Edge(
                    source_id=pid,
                    target_id=fv["id"],
                    edge_type="FUNDED_BY",
                ))

        # Barriers
        for bar in schema.get("barriers", []):
            node = BarrierNode(
                id=bar["id"],
                description=bar["description"],
                barrier_type=bar.get("type", ""),
                severity=bar.get("severity", ""),
            )
            self.graph.add_node(node)
            for pid in bar.get("programs", []):
                self.graph.add_edge(Edge(
                    source_id=pid,
                    target_id=bar["id"],
                    edge_type="BLOCKED_BY",
                ))
            # Barrier -> Lever mitigations
            for lever_id in bar.get("mitigated_by", []):
                self.graph.add_edge(Edge(
                    source_id=bar["id"],
                    target_id=lever_id,
                    edge_type="MITIGATED_BY",
                ))

    def _enrich_from_items(self, items: list[dict]) -> None:
        """Infer new nodes and edges from scraped policy items."""
        for item in items:
            # Handle USASpending obligation records as ObligationNodes
            if item.get("source") == "usaspending" and item.get("award_amount"):
                self._add_obligation(item)
                continue

            text = f"{item.get('title', '')} {item.get('abstract', '')} {item.get('action', '')}"
            matched_pids = item.get("matched_programs", [])

            # Detect authorities mentioned in text
            for pattern, auth_type in AUTHORITY_PATTERNS:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    citation = match.group(1).strip()
                    auth_id = f"auth_{re.sub(r'[^a-z0-9]+', '_', citation.lower())}"
                    if auth_id not in self.graph.nodes:
                        self.graph.add_node(AuthorityNode(
                            id=auth_id,
                            citation=citation,
                            authority_type=auth_type,
                        ))
                    for pid in matched_pids:
                        # Avoid duplicate edges
                        if not any(e.source_id == pid and e.target_id == auth_id
                                   for e in self.graph.edges):
                            self.graph.add_edge(Edge(
                                source_id=pid,
                                target_id=auth_id,
                                edge_type="AUTHORIZED_BY",
                                metadata={"inferred_from": item.get("source_id", "")},
                            ))

            # Detect barriers mentioned in text
            for pattern, desc, barrier_type in BARRIER_PATTERNS:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    barrier_text = match.group(0).strip()
                    bar_id = f"bar_{re.sub(r'[^a-z0-9]+', '_', barrier_text.lower())[:40]}"
                    if bar_id not in self.graph.nodes:
                        self.graph.add_node(BarrierNode(
                            id=bar_id,
                            description=barrier_text,
                            barrier_type=barrier_type,
                            severity="Med",
                        ))
                    for pid in matched_pids:
                        if not any(e.source_id == pid and e.target_id == bar_id
                                   for e in self.graph.edges):
                            self.graph.add_edge(Edge(
                                source_id=pid,
                                target_id=bar_id,
                                edge_type="BLOCKED_BY",
                                metadata={"inferred_from": item.get("source_id", "")},
                            ))

            # Detect funding signals
            for pattern, field_name in FUNDING_PATTERNS:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    if field_name == "amount":
                        raw = match.group(1).replace(",", "")
                        unit = match.group(2).lower()
                        try:
                            amount = float(raw)
                            if unit in ("billion", "b"):
                                amount *= 1_000_000_000
                            elif unit in ("million", "m"):
                                amount *= 1_000_000
                        except ValueError:
                            continue
                        for pid in matched_pids:
                            fv_id = f"fv_{pid}_{item.get('source_id', 'unknown')}"
                            if fv_id not in self.graph.nodes:
                                self.graph.add_node(FundingVehicleNode(
                                    id=fv_id,
                                    name=item.get("title", "")[:60],
                                    amount=amount,
                                    funding_type="",
                                ))
                                self.graph.add_edge(Edge(
                                    source_id=pid,
                                    target_id=fv_id,
                                    edge_type="FUNDED_BY",
                                    metadata={"inferred_from": item.get("source_id", "")},
                                ))

    def _add_obligation(self, item: dict) -> None:
        """Add a USASpending obligation record to the graph."""
        obl_id = item.get("source_id", "")
        amount = item.get("award_amount", 0)
        recipient = item.get("recipient", "")
        cfda = item.get("cfda", "")
        matched_pids = item.get("matched_programs", [])

        if not obl_id or obl_id in self.graph.nodes:
            return

        self.graph.add_node(ObligationNode(
            id=obl_id,
            amount=amount,
            recipient=recipient,
            fiscal_year="FY26",
            cfda=cfda,
        ))
        for pid in matched_pids:
            self.graph.add_edge(Edge(
                source_id=pid,
                target_id=obl_id,
                edge_type="OBLIGATED_BY",
                metadata={"amount": amount, "recipient": recipient},
            ))
