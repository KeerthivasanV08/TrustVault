from __future__ import annotations

from typing import Any, Dict


class GraphRoleService:
    def classify_node_role(self, neo4j_client, user_id: str) -> Dict[str, Any]:
        if neo4j_client is None or not getattr(neo4j_client, "is_available", lambda: False)():
            return {
                "network_role": "UNKNOWN",
                "in_degree": 0,
                "out_degree": 0,
                "reasons": ["NEO4J_UNAVAILABLE"],
            }

        query = """
        MATCH (account:Account {user_id: $user_id})
        OPTIONAL MATCH (account)-[outgoing:TRANSFER]->()
        OPTIONAL MATCH ()-[incoming:TRANSFER]->(account)
        RETURN count(DISTINCT outgoing) AS out_degree, count(DISTINCT incoming) AS in_degree
        """
        rows = neo4j_client.run_query(query, {"user_id": str(user_id)})
        row = rows[0] if rows else {}
        in_degree = int(row.get("in_degree") or 0)
        out_degree = int(row.get("out_degree") or 0)

        if in_degree >= 4 and out_degree >= 4:
            role = "COLLECTOR_HUB"
        elif out_degree >= max(in_degree * 2, 3):
            role = "SOURCE_DISTRIBUTOR"
        elif in_degree >= max(out_degree * 2, 3):
            role = "SINK_NODE"
        elif in_degree >= 2 and out_degree >= 2:
            role = "BRIDGE_LAYER"
        else:
            role = "RETAIL_USER"

        return {
            "network_role": role,
            "in_degree": in_degree,
            "out_degree": out_degree,
            "reasons": [f"NETWORK_ROLE_{role}"] if role != "RETAIL_USER" else [],
        }