from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List

from dotenv import load_dotenv

from app.db.neo4j_client import Neo4jClient


BASE_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = BASE_DIR / "data" / "raw"


def _read_csv(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return fallback


def _chunked(items: List[Dict[str, Any]], size: int) -> Iterable[List[Dict[str, Any]]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


def main() -> None:
    load_dotenv()
    client = Neo4jClient()
    if not client.is_available():
        raise SystemExit("Neo4j connection details are missing or invalid.")

    users = _read_csv(DATA_DIR / "users.csv")
    transactions = _read_csv(DATA_DIR / "transactions.csv")

    client.execute_write(
        """
        CREATE CONSTRAINT account_user_id IF NOT EXISTS
        FOR (a:Account) REQUIRE a.user_id IS UNIQUE
        """
    )
    client.execute_write(
        """
        CREATE CONSTRAINT device_id IF NOT EXISTS
        FOR (d:Device) REQUIRE d.device_id IS UNIQUE
        """
    )
    client.execute_write(
        """
        CREATE CONSTRAINT ip_address IF NOT EXISTS
        FOR (i:IPAddress) REQUIRE i.ip_address IS UNIQUE
        """
    )

    for row in users:
        user_id = str(row.get("user_id") or row.get("id") or row.get("account_id") or "").strip()
        if not user_id:
            continue
        client.execute_write(
            """
            MERGE (account:Account {user_id: $user_id})
            SET account.name = coalesce($name, account.name),
                account.country = coalesce($country, account.country),
                account.risk_label = coalesce($risk_label, account.risk_label),
                account.created_at = coalesce(account.created_at, datetime())
            """,
            {
                "user_id": user_id,
                "name": row.get("name") or row.get("full_name") or user_id,
                "country": row.get("country") or row.get("residence_country"),
                "risk_label": row.get("risk_label") or row.get("risk_flag"),
            },
        )

    for batch in _chunked(transactions, 250):
        for row in batch:
            sender_id = str(row.get("sender_id") or row.get("from_user") or "").strip()
            receiver_id = str(row.get("receiver_id") or row.get("to_user") or "").strip()
            if not sender_id or not receiver_id:
                continue
            client.execute_write(
                """
                MERGE (sender:Account {user_id: $sender_id})
                MERGE (receiver:Account {user_id: $receiver_id})
                MERGE (sender)-[tx:TRANSFER {transaction_id: $transaction_id}]->(receiver)
                SET tx.amount = $amount,
                    tx.currency = $currency,
                    tx.channel = $channel,
                    tx.timestamp = datetime($timestamp),
                    tx.suspicious = $suspicious,
                    tx.risk_score = $risk_score
                """,
                {
                    "sender_id": sender_id,
                    "receiver_id": receiver_id,
                    "transaction_id": str(row.get("trans_id") or row.get("transaction_id") or row.get("id") or f"TX-{sender_id}-{receiver_id}"),
                    "amount": _safe_float(row.get("amount")),
                    "currency": row.get("currency") or "USD",
                    "channel": row.get("channel") or row.get("payment_channel") or "UNKNOWN",
                    "timestamp": row.get("timestamp") or row.get("created_at") or row.get("ts") or "2025-01-01T00:00:00Z",
                    "suspicious": _safe_float(row.get("risk_score") or row.get("final_score")) >= 0.75,
                    "risk_score": _safe_float(row.get("risk_score") or row.get("final_score")),
                },
            )

    print(f"Loaded {len(users)} users and {len(transactions)} transactions into Neo4j.")


if __name__ == "__main__":
    main()