from __future__ import annotations

from typing import Any, Dict


class GraphTemporalService:
    def detect_layering_chain(self, neo4j_client, user_id: str) -> Dict[str, Any]:
        if neo4j_client is None or not getattr(neo4j_client, "is_available", lambda: False)():
            return {
                "layering_detected": False,
                "chain_depth": 0,
                "chain_count": 0,
                "chain_nodes": [],
                "reasons": ["NEO4J_UNAVAILABLE"],
            }

        query = """
        MATCH (source:Account {user_id: $user_id})-[first:TRANSFER]->(mid:Account)-[second:TRANSFER]->(dest:Account)
        WHERE first.timestamp IS NOT NULL
          AND second.timestamp IS NOT NULL
          AND duration.inSeconds(datetime(first.timestamp), datetime(second.timestamp)) <= 120
        RETURN
            count(DISTINCT mid) AS chain_count,
            count(DISTINCT dest) AS chain_depth,
            collect(DISTINCT mid.user_id)[0..8] AS chain_nodes
        """
        rows = neo4j_client.run_query(query, {"user_id": str(user_id)})
        row = rows[0] if rows else {}
        chain_count = int(row.get("chain_count") or 0)
        chain_depth = int(row.get("chain_depth") or 0)

        return {
            "layering_detected": chain_count > 0,
            "chain_depth": max(chain_depth, 2 if chain_count else 0),
            "chain_count": chain_count,
            "chain_nodes": row.get("chain_nodes", []) or [],
            "reasons": ["TEMPORAL_LAYERING_CHAIN"] if chain_count else [],
        }