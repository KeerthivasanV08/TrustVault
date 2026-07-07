from __future__ import annotations

from typing import Any, Dict


class GraphProximityService:
    def compute_fraud_proximity(self, neo4j_client, user_id: str) -> Dict[str, Any]:
        if neo4j_client is None or not getattr(neo4j_client, "is_available", lambda: False)():
            return {
                "fraud_hop_distance": 999,
                "known_fraud_neighbors": 0,
                "exposure_type": "NEO4J_UNAVAILABLE",
                "reasons": ["NEO4J_UNAVAILABLE"],
            }

        query = """
        MATCH (account:Account {user_id: $user_id})
        OPTIONAL MATCH path = shortestPath((account)-[:TRANSFER|USES_DEVICE|USES_IP*1..4]-(fraud:Account))
        WHERE CASE
            WHEN fraud.risk_label IS NOT NULL THEN fraud.risk_label
            WHEN 'risk_flag' IN keys(fraud) THEN fraud.risk_flag
            ELSE ''
        END IN ['FRAUD', 'FRAUDULENT', 'HIGH_RISK']
        RETURN
            min(length(path)) AS fraud_hop_distance,
            count(path) AS known_fraud_neighbors
        """
        rows = neo4j_client.run_query(query, {"user_id": str(user_id)})
        row = rows[0] if rows else {}
        hop_distance = int(row.get("fraud_hop_distance") or 999)
        neighbors = int(row.get("known_fraud_neighbors") or 0)

        if hop_distance <= 1:
            exposure_type = "DIRECT_FRAUD_EXPOSURE"
        elif hop_distance <= 2:
            exposure_type = "NEAR_FRAUD_CLUSTER"
        elif hop_distance <= 4:
            exposure_type = "INDIRECT_FRAUD_EXPOSURE"
        else:
            exposure_type = "NO_MAJOR_GRAPH_RISK"

        return {
            "fraud_hop_distance": hop_distance,
            "known_fraud_neighbors": neighbors,
            "exposure_type": exposure_type,
            "reasons": [exposure_type] if exposure_type != "NO_MAJOR_GRAPH_RISK" else [],
        }