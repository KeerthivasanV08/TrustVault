from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase
from dotenv import load_dotenv


_BACKEND_ENV = Path(__file__).resolve().parents[2] / ".env"
if _BACKEND_ENV.exists():
    load_dotenv(_BACKEND_ENV)


class Neo4jClient:
    def __init__(self) -> None:
        self.uri = os.getenv("NEO4J_URI")
        self.user = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME")
        self.password = os.getenv("NEO4J_PASSWORD")
        self.database = os.getenv("NEO4J_DATABASE")
        self._available = bool(self.uri and self.user and self.password)
        self.driver = None

        if self._available:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
            )

    def is_available(self) -> bool:
        return bool(self._available and self.driver is not None)

    def close(self) -> None:
        if self.driver is not None:
            self.driver.close()

    def health_check(self) -> Dict[str, Any]:
        if not self.is_available():
            return {
                "status": "degraded",
                "connected": False,
                "uri": self.uri,
                "reason": "missing_environment_configuration",
            }

        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1 AS ok")
                row = result.single()
                return {
                    "status": "connected",
                    "connected": True,
                    "uri": self.uri,
                    "database": self.database,
                    "probe": int(row["ok"]) if row else 1,
                }
        except Exception as exc:
            return {
                "status": "degraded",
                "connected": False,
                "uri": self.uri,
                "database": self.database,
                "reason": str(exc),
            }

    def run_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if not self.is_available():
            return []

        try:
            with self.driver.session() as session:
                result = session.run(query, params or {})
                return [record.data() for record in result]
        except Exception:
            return []

    def execute_write(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return self.run_query(query, params)