from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional

from app.db.neo4j_client import Neo4jClient

from .graph_community_service import GraphCommunityService
from .graph_proximity_service import GraphProximityService
from .graph_role_service import GraphRoleService
from .graph_temporal_service import GraphTemporalService


class GraphIntelligenceEngine:
    def __init__(self, neo4j_client: Optional[Neo4jClient] = None) -> None:
        self.neo4j = neo4j_client or Neo4jClient()
        self.temporal = GraphTemporalService()
        self.community = GraphCommunityService()
        self.roles = GraphRoleService()
        self.proximity = GraphProximityService()

    def evaluate_graph_risk(self, user_id: str, txn: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        txn = txn or {}
        amount = _float(txn.get("amount"))

        role_info = self.roles.classify_node_role(self.neo4j, user_id)
        temporal_info = self.temporal.detect_layering_chain(self.neo4j, user_id)
        proximity_info = self.proximity.compute_fraud_proximity(self.neo4j, user_id)
        community_info = self.community.detect_mule_ring(self.neo4j, user_id)

        score = 0.0
        reasons: List[str] = []

        if amount >= 50000:
            score += 0.12
            reasons.append("HIGH_VALUE_TRANSFER")
        if amount >= 100000:
            score += 0.08
            reasons.append("VERY_HIGH_VALUE_TRANSACTION")

        role = str(role_info.get("network_role") or "UNKNOWN")
        if role in {"COLLECTOR_HUB", "SINK_NODE"}:
            score += 0.18
        elif role == "BRIDGE_LAYER":
            score += 0.08
        reasons.extend(_as_list(role_info.get("reasons")))

        if temporal_info.get("layering_detected"):
            score += 0.22
        reasons.extend(_as_list(temporal_info.get("reasons")))

        hop_distance = int(proximity_info.get("fraud_hop_distance") or 999)
        if hop_distance <= 1:
            score += 0.34
        elif hop_distance <= 2:
            score += 0.24
        elif hop_distance <= 4:
            score += 0.10
        reasons.extend(_as_list(proximity_info.get("reasons")))

        community_risk = str(community_info.get("cluster_risk") or "LOW")
        score += _community_weight(community_risk)
        reasons.extend(_as_list(community_info.get("reasons")))

        if role == "SOURCE_DISTRIBUTOR" and amount >= 25000:
            score += 0.05
            reasons.append("DISTRIBUTED_HIGH_VALUE_FLOW")

        neo4j_graph_score = max(0.0, min(score, 1.0))
        confidence = max(0.25, min(0.95, 0.40 + 0.08 * len(set(reasons))))

        return {
            "neo4j_graph_score": round(neo4j_graph_score, 4),
            "graph_score": round(neo4j_graph_score, 4),
            "confidence": round(confidence, 4),
            "fraud_hop_distance": hop_distance,
            "exposure_type": proximity_info.get("exposure_type", "NO_MAJOR_GRAPH_RISK"),
            "network_role": role,
            "chain_depth": int(temporal_info.get("chain_depth") or 0),
            "chain_count": int(temporal_info.get("chain_count") or 0),
            "community_risk": community_risk,
            "known_fraud_neighbors": int(proximity_info.get("known_fraud_neighbors") or 0),
            "txn_context": {
                "amount": amount,
                "currency": txn.get("currency"),
                "channel": txn.get("channel"),
            },
            "reasons": _dedupe(reasons) or ["NO_MAJOR_GRAPH_RISK"],
        }


def _float(value: Any) -> float:
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def _community_weight(value: str) -> float:
    mapping = {"LOW": 0.0, "MEDIUM": 0.10, "HIGH": 0.20, "CRITICAL": 0.30}
    return mapping.get(value.upper(), 0.0)


def _as_list(value: Any) -> List[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value if item]
    return [str(value)]


def _dedupe(values: Iterable[str]) -> List[str]:
    seen = set()
    output = []
    for value in values:
        if value not in seen:
            seen.add(value)
            output.append(value)
    return output