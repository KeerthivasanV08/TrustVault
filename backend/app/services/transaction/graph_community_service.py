from __future__ import annotations

from typing import Any, Dict


class GraphCommunityService:
    def detect_mule_ring(self, neo4j_client, user_id: str) -> Dict[str, Any]:
        if neo4j_client is None or not getattr(neo4j_client, "is_available", lambda: False)():
            return {
                "cluster_risk": "UNKNOWN",
                "community_score": 0.0,
                "shared_device_neighbors": 0,
                "shared_ip_neighbors": 0,
                "suspicious_edges": 0,
                "reasons": ["NEO4J_UNAVAILABLE"],
            }

        query = """
        MATCH (account:Account {user_id: $user_id})
        OPTIONAL MATCH (account)-[:USES_DEVICE]->(device:Device)<-[:USES_DEVICE]-(device_peer:Account)
        OPTIONAL MATCH (account)-[:USES_IP]->(ip:IPAddress)<-[:USES_IP]-(ip_peer:Account)
        OPTIONAL MATCH (account)-[tx:TRANSFER]->(peer:Account)
        RETURN
            count(DISTINCT device_peer) AS shared_device_neighbors,
            count(DISTINCT ip_peer) AS shared_ip_neighbors,
            sum(CASE WHEN coalesce(tx.suspicious, false) = true OR coalesce(tx.risk_score, 0) >= 0.75 THEN 1 ELSE 0 END) AS suspicious_edges,
            count(DISTINCT peer) AS peer_count
        """
        rows = neo4j_client.run_query(query, {"user_id": str(user_id)})
        row = rows[0] if rows else {}
        shared_device_neighbors = int(row.get("shared_device_neighbors") or 0)
        shared_ip_neighbors = int(row.get("shared_ip_neighbors") or 0)
        suspicious_edges = int(row.get("suspicious_edges") or 0)
        peer_count = int(row.get("peer_count") or 0)

        raw_score = (shared_device_neighbors * 0.25) + (shared_ip_neighbors * 0.20) + (suspicious_edges * 0.35) + (peer_count * 0.05)
        community_score = round(min(raw_score / 4.0, 1.0), 4)

        if community_score >= 0.85:
            cluster_risk = "CRITICAL"
        elif community_score >= 0.65:
            cluster_risk = "HIGH"
        elif community_score >= 0.35:
            cluster_risk = "MEDIUM"
        else:
            cluster_risk = "LOW"

        reasons = []
        if shared_device_neighbors > 0:
            reasons.append("SHARED_DEVICE_CLUSTER")
        if shared_ip_neighbors > 0:
            reasons.append("SHARED_IP_CLUSTER")
        if suspicious_edges > 0:
            reasons.append("COORDINATED_TRANSFER_PATTERN")

        return {
            "cluster_risk": cluster_risk,
            "community_score": community_score,
            "shared_device_neighbors": shared_device_neighbors,
            "shared_ip_neighbors": shared_ip_neighbors,
            "suspicious_edges": suspicious_edges,
            "peer_count": peer_count,
            "reasons": reasons,
        }