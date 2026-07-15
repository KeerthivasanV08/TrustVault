from __future__ import annotations

from datetime import datetime, timezone
from math import cos, sin, tau
from typing import Any, Dict, List, Mapping, Optional

from app.db.neo4j_client import Neo4jClient

from .graph_community_service import GraphCommunityService
from .graph_proximity_service import GraphProximityService
from .graph_role_service import GraphRoleService
from .graph_service import GraphIntelligenceEngine
from .graph_temporal_service import GraphTemporalService


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        number = float(value)
    except Exception:
        return fallback
    return number if number == number else fallback


def _safe_str(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text or fallback


class GraphFeatureService:
    def __init__(self) -> None:
        self.neo4j = Neo4jClient()
        self.engine = GraphIntelligenceEngine()
        self.engine.neo4j = self.neo4j
        self.temporal = GraphTemporalService()
        self.role = GraphRoleService()
        self.proximity = GraphProximityService()
        self.community = GraphCommunityService()

    def record_transaction(self, txn: Mapping[str, Any], decision_result: Optional[Mapping[str, Any]] = None, graph_result: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        if not self.neo4j.is_available():
            return {"status": "degraded", "connected": False}

        sender_id = _safe_str(txn.get("sender_id") or txn.get("sender") or txn.get("from") or txn.get("user_id"))
        receiver_id = _safe_str(txn.get("receiver_id") or txn.get("receiver") or txn.get("to"))
        if not sender_id or not receiver_id:
            return {"status": "skipped", "reason": "missing_sender_or_receiver"}

        timestamp = _safe_str(txn.get("timestamp") or txn.get("ts") or datetime.now(tz=timezone.utc).isoformat())
        payload = {
            "transaction_id": _safe_str(txn.get("trans_id") or txn.get("transaction_id") or txn.get("id"), fallback=f"TX-{sender_id}-{receiver_id}-{int(datetime.now(tz=timezone.utc).timestamp())}"),
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "amount": _safe_float(txn.get("amount")),
            "currency": _safe_str(txn.get("currency"), "USD"),
            "channel": _safe_str(txn.get("channel"), "UNKNOWN"),
            "timestamp": timestamp,
            "decision": _safe_str((decision_result or {}).get("decision") or txn.get("decision"), "UNKNOWN"),
            "final_score": _safe_float((decision_result or {}).get("final_score") or txn.get("final_score")),
            "behavior_score": _safe_float(txn.get("behavior_score")),
            "sequence_score": _safe_float(txn.get("sequence_score")),
            "neo4j_graph_score": _safe_float((graph_result or {}).get("neo4j_graph_score") or (graph_result or {}).get("graph_score") or txn.get("graph_score")),
            "risk_label": _safe_str(txn.get("risk_label") or txn.get("decision"), "UNKNOWN"),
            "device_id": _safe_str(txn.get("device_id")),
            "ip_address": _safe_str(txn.get("ip_address") or txn.get("ip")),
            "location": _safe_str(txn.get("location")),
            "suspicious": bool(float((decision_result or {}).get("final_score") or txn.get("final_score") or 0) >= 0.75),
        }

        query = """
        MERGE (sender:Account {user_id: $sender_id})
          ON CREATE SET sender.created_at = datetime($timestamp)
          ON MATCH SET sender.last_seen = datetime($timestamp)
        MERGE (receiver:Account {user_id: $receiver_id})
          ON CREATE SET receiver.created_at = datetime($timestamp)
          ON MATCH SET receiver.last_seen = datetime($timestamp)
        MERGE (sender)-[tx:TRANSFER {transaction_id: $transaction_id}]->(receiver)
          SET
            tx.amount = $amount,
            tx.currency = $currency,
            tx.channel = $channel,
            tx.timestamp = $timestamp,
            tx.decision = $decision,
            tx.final_score = $final_score,
            tx.behavior_score = $behavior_score,
            tx.sequence_score = $sequence_score,
            tx.neo4j_graph_score = $neo4j_graph_score,
            tx.risk_label = $risk_label,
            tx.suspicious = $suspicious
        WITH sender, receiver
        FOREACH (_ IN CASE WHEN $device_id = '' THEN [] ELSE [1] END |
          MERGE (device:Device {device_id: $device_id})
          MERGE (sender)-[:USES_DEVICE]->(device)
          MERGE (receiver)-[:USES_DEVICE]->(device)
        )
        FOREACH (_ IN CASE WHEN $ip_address = '' THEN [] ELSE [1] END |
          MERGE (ip:IPAddress {ip_address: $ip_address})
          MERGE (sender)-[:USES_IP]->(ip)
          MERGE (receiver)-[:USES_IP]->(ip)
        )
        RETURN sender.user_id AS sender_id, receiver.user_id AS receiver_id
        """

        rows = self.neo4j.execute_write(query, payload)
        return {"status": "recorded", "rows": rows}

    def get_network(self, limit: int = 75) -> Dict[str, Any]:
        if not self.neo4j.is_available():
            return self._empty_graph("NEO4J_UNAVAILABLE")

        query = """
        MATCH (source:Account)-[transfer:TRANSFER]->(target:Account)
        RETURN properties(source) AS source, properties(transfer) AS transfer, properties(target) AS target
        ORDER BY coalesce(transfer.timestamp, '') DESC
        LIMIT $limit
        """
        rows = self.neo4j.run_query(query, {"limit": int(limit)})
        return self._build_graph(rows)

    def get_account_graph(self, account_id: str, depth: int = 2) -> Dict[str, Any]:
        if not self.neo4j.is_available():
            return self._empty_graph("NEO4J_UNAVAILABLE", selected_account=account_id)

        safe_depth = max(1, min(int(depth), 4))
        query = """
        MATCH (center:Account {user_id: $account_id})
        OPTIONAL MATCH path = (center)-[:TRANSFER|USES_DEVICE|USES_IP*1..%d]-(neighbor)
        RETURN properties(center) AS center, collect(DISTINCT properties(neighbor)) AS neighbors
        """ % safe_depth
        rows = self.neo4j.run_query(query, {"account_id": _safe_str(account_id)})
        return self._build_account_graph(account_id, rows)

    def get_risk_summary(self, account_id: str, txn: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        return self.engine.evaluate_graph_risk(account_id, txn or {})

    def get_layering_summary(self, account_id: str) -> Dict[str, Any]:
        return self.temporal.detect_layering_chain(self.neo4j, account_id)

    def get_community_summary(self, account_id: str) -> Dict[str, Any]:
        return self.community.detect_mule_ring(self.neo4j, account_id)

    def _empty_graph(self, reason: str, selected_account: Optional[str] = None) -> Dict[str, Any]:
        return {
            "graph_available": False,
            "graph_status": "UNAVAILABLE",
            "nodes": [],
            "edges": [],
            "circularFlows": [],
            "clusterSummaries": [],
            "selectedAccount": selected_account,
            "updatedAt": datetime.now(tz=timezone.utc).isoformat(),
            "metadata": {"status": "degraded", "reason": reason},
        }

    def _build_graph(self, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        nodes: Dict[str, Dict[str, Any]] = {}
        edges: List[Dict[str, Any]] = []

        for row in rows:
            source = row.get("source") or {}
            target = row.get("target") or {}
            transfer = row.get("transfer") or {}

            source_id = _safe_str(source.get("user_id") or source.get("id") or source.get("label"))
            target_id = _safe_str(target.get("user_id") or target.get("id") or target.get("label"))
            if not source_id or not target_id:
                continue

            nodes[source_id] = self._node_payload(source_id, source, role="SOURCE")
            nodes[target_id] = self._node_payload(target_id, target, role="TARGET")
            edges.append({
                "source": source_id,
                "target": target_id,
                "amount": _safe_float(transfer.get("amount")),
                "weight": _safe_float(transfer.get("amount"), 1.0),
                "suspicious": bool(transfer.get("suspicious") or _safe_float(transfer.get("final_score")) >= 0.75),
            })

        laid_out_nodes = self._layout_nodes(list(nodes.values()))
        cluster_summaries = self._cluster_summaries(laid_out_nodes)
        circular_flows = [
            {
                "path": [edge["source"], edge["target"]],
                "score": edge.get("amount", 0),
            }
            for edge in edges
            if edge.get("suspicious")
        ]

        return {
            "graph_available": True,
            "graph_status": "AVAILABLE" if self.neo4j.is_available() else "UNAVAILABLE",
            "nodes": laid_out_nodes,
            "edges": edges,
            "circularFlows": circular_flows,
            "clusterSummaries": cluster_summaries,
            "updatedAt": datetime.now(tz=timezone.utc).isoformat(),
            "metadata": {"status": "connected" if self.neo4j.is_available() else "degraded"},
        }

    def _build_account_graph(self, account_id: str, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        account_id = _safe_str(account_id)
        center = {"id": account_id, "label": account_id, "type": "account", "risk": 92, "riskLevel": "high", "volume": 0, "cluster": 1, "x": 420, "y": 260}
        nodes: Dict[str, Dict[str, Any]] = {account_id: center}
        edges: List[Dict[str, Any]] = []

        for row in rows:
            for neighbor in row.get("neighbors") or []:
                if not neighbor:
                    continue
                neighbor_id = _safe_str(neighbor.get("user_id") or neighbor.get("device_id") or neighbor.get("ip_address") or neighbor.get("id") or neighbor.get("label"))
                if not neighbor_id or neighbor_id == account_id:
                    continue
                nodes.setdefault(neighbor_id, self._node_payload(neighbor_id, neighbor, role="NEIGHBOR"))

        laid_out = self._layout_account_nodes(list(nodes.values()), account_id)
        nodes = {node["id"]: node for node in laid_out}

        for neighbor_id, node in nodes.items():
            if neighbor_id == account_id:
                continue
            edges.append({"source": account_id, "target": neighbor_id, "amount": 1, "suspicious": node.get("risk", 0) >= 70})

        return {
            "graph_available": True,
            "graph_status": "AVAILABLE" if self.neo4j.is_available() else "UNAVAILABLE",
            "nodes": list(nodes.values()),
            "edges": edges,
            "circularFlows": [
                {"path": [account_id, node_id], "score": node.get("risk", 0)}
                for node_id, node in nodes.items()
                if node_id != account_id and node.get("risk", 0) >= 75
            ],
            "clusterSummaries": self._cluster_summaries(list(nodes.values())),
            "selectedAccount": account_id,
            "updatedAt": datetime.now(tz=timezone.utc).isoformat(),
            "metadata": {"status": "connected" if self.neo4j.is_available() else "degraded"},
        }

    def _node_payload(self, node_id: str, raw: Mapping[str, Any], role: str) -> Dict[str, Any]:
        risk = _safe_float(raw.get("risk_score") or raw.get("risk") or raw.get("neo4j_graph_score") or raw.get("final_score"), 58.0)
        risk_level = "high" if risk >= 75 else "medium" if risk >= 45 else "low"
        volume = _safe_float(raw.get("volume") or raw.get("total_volume") or raw.get("amount"), 100000.0)
        return {
            "id": node_id,
            "label": _safe_str(raw.get("label") or raw.get("name") or node_id),
            "type": _safe_str(raw.get("type") or raw.get("entity_type") or role.lower(), "account"),
            "role": _safe_str(raw.get("role") or role),
            "risk": risk,
            "riskScore": risk,
            "riskLevel": risk_level,
            "volume": volume,
            "cluster": int(_safe_float(raw.get("cluster") or raw.get("cluster_id") or (1 if risk >= 75 else 2 if risk >= 45 else 3), 1)),
        }

    def _layout_nodes(self, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not nodes:
            return []

        count = len(nodes)
        radius = 170.0
        center_x = 500.0
        center_y = 300.0
        laid_out = []
        for index, node in enumerate(nodes):
            angle = (tau * index / max(count, 1)) - 1.2
            offset = 40 + (index % 4) * 14
            placed = dict(node)
            if index == 0:
                placed["x"] = center_x
                placed["y"] = center_y
            else:
                placed["x"] = center_x + cos(angle) * (radius + offset)
                placed["y"] = center_y + sin(angle) * (radius + offset * 0.75)
            laid_out.append(placed)
        return laid_out

    def _layout_account_nodes(self, nodes: List[Dict[str, Any]], account_id: str) -> List[Dict[str, Any]]:
        if not nodes:
            return []

        center_x = 420.0
        center_y = 260.0
        radius = 210.0
        output: List[Dict[str, Any]] = []
        center = next((node for node in nodes if node.get("id") == account_id), dict(nodes[0]))
        center["x"] = center_x
        center["y"] = center_y
        output.append(center)

        others = [node for node in nodes if node.get("id") != account_id]
        for index, node in enumerate(others, start=1):
            angle = (tau * index / max(len(others), 1)) - 1.0
            placed = dict(node)
            placed["x"] = center_x + cos(angle) * radius
            placed["y"] = center_y + sin(angle) * radius
            output.append(placed)
        return output

    def _cluster_summaries(self, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        clusters: Dict[int, List[Dict[str, Any]]] = {}
        for node in nodes:
            cluster_id = int(node.get("cluster") or 0)
            clusters.setdefault(cluster_id, []).append(node)

        summaries = []
        for cluster_id, items in sorted(clusters.items(), key=lambda entry: entry[0]):
            total_risk = sum(_safe_float(item.get("risk") or item.get("riskScore")) for item in items)
            avg_risk = round(total_risk / max(len(items), 1), 2)
            summaries.append({
                "id": cluster_id,
                "name": f"Cluster {cluster_id}",
                "accounts": len(items),
                "totalRiskScore": round(total_risk, 2),
                "avgRisk": avg_risk,
                "hasCircularFlow": avg_risk >= 70,
                "color": "#ef4444" if avg_risk >= 70 else "#f59e0b" if avg_risk >= 45 else "#22c55e",
            })
        return summaries