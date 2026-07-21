import os
import pandas as pd
from itertools import combinations

from pathlib import Path
from neo4j import GraphDatabase
from dotenv import load_dotenv, find_dotenv

from app.core import storage_paths


# =====================================================
# PATHS
# =====================================================

BASE_DIR = Path(__file__).resolve().parents[2]

RAW_DIR = BASE_DIR / "data" / "raw"

PROCESSED_DIR = BASE_DIR / "data" / "processed"

CO_CREATED_BATCH_SIZE = 500


def to_iso_datetime(value):

    parsed = pd.to_datetime(value, errors="coerce")

    if pd.isna(parsed):
        parsed = pd.Timestamp.now()

    return parsed.isoformat()


# =====================================================
# LOAD ENV
# =====================================================

SCRIPT_DIR = Path(__file__).resolve().parent

PROJECT_ROOT = BASE_DIR

for candidate in (
    find_dotenv(usecwd=True),
    str(SCRIPT_DIR / ".env"),
    str(PROJECT_ROOT / ".env"),
    str(PROJECT_ROOT.parent / ".env")
):
    if candidate:
        load_dotenv(candidate, override=False)

NEO4J_URI = os.getenv("NEO4J_URI") or "bolt://localhost:7687"
NEO4J_USER = os.getenv("NEO4J_USER") or "neo4j"
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD") or "neo4j"

if not os.getenv("NEO4J_URI"):
    print(
        "⚠️ NEO4J_URI was not set. Falling back to bolt://localhost:7687 "
        "for local Neo4j connectivity."
    )


# =====================================================
# NEO4J CONNECTION
# =====================================================

if not NEO4J_URI.startswith(("bolt://", "bolt+ssc://", "bolt+s://", "neo4j://", "neo4j+ssc://", "neo4j+s://")):
    raise RuntimeError(
        f"Invalid NEO4J_URI '{NEO4J_URI}'. Set NEO4J_URI to a valid Neo4j URI such as bolt://localhost:7687."
    )

driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(
        NEO4J_USER,
        NEO4J_PASSWORD
    )
)


# =====================================================
# LOAD DATA
# =====================================================

users_df = pd.read_csv(
    RAW_DIR / "users.csv"
)

tx_df = pd.read_csv(
    RAW_DIR / "transactions.csv"
)

onboarding_df = pd.read_csv(storage_paths.ONBOARDING_RISK_SNAPSHOT_PATH)


# =====================================================
# PREPARE TIMESTAMPS
# =====================================================

if "created_at" in users_df.columns:
    users_df["created_at"] = pd.to_datetime(
        users_df["created_at"],
        errors="coerce"
    )

if "timestamp" in tx_df.columns:
    tx_df["timestamp"] = pd.to_datetime(
        tx_df["timestamp"],
        errors="coerce"
    )


# =====================================================
# MERGE ONBOARDING INTEL
# =====================================================

users_df = users_df.merge(
    onboarding_df[
        [
            "user_id",
            "final_risk_score",
            "risk_level",
            "requires_block"
        ]
    ],
    on="user_id",
    how="left"
)

users_df.fillna(
    {
        "final_risk_score": 0,
        "risk_level": "LOW",
        "requires_block": 0
    },
    inplace=True
)


# =====================================================
# CREATE CONSTRAINTS + INDEXES
# =====================================================

def create_constraints(tx):

    queries = [

        # ---------------------------------------------
        # UNIQUE ACCOUNT
        # ---------------------------------------------

        """
        CREATE CONSTRAINT account_user_id_unique
        IF NOT EXISTS
        FOR (a:Account)
        REQUIRE a.user_id IS UNIQUE
        """,

        # ---------------------------------------------
        # UNIQUE DEVICE
        # ---------------------------------------------

        """
        CREATE CONSTRAINT device_id_unique
        IF NOT EXISTS
        FOR (d:Device)
        REQUIRE d.device_id IS UNIQUE
        """,

        # ---------------------------------------------
        # UNIQUE IP
        # ---------------------------------------------

        """
        CREATE CONSTRAINT ip_unique
        IF NOT EXISTS
        FOR (ip:IPAddress)
        REQUIRE ip.ip_address IS UNIQUE
        """,

        # ---------------------------------------------
        # TRANSFER INDEX
        # ---------------------------------------------

        """
        CREATE INDEX transfer_timestamp_index
        IF NOT EXISTS
        FOR ()-[t:TRANSFER]-()
        ON (t.timestamp)
        """
    ]

    for q in queries:
        tx.run(q)


# =====================================================
# CREATE ACCOUNT NODES
# =====================================================

def create_account_nodes(tx, row):

    query = """
    MERGE (a:Account {user_id:$user_id})

    SET
        a.created_at = datetime($created_at),
        a.kyc_status = $kyc_status,
        a.risk_score = $risk_score,
        a.risk_level = $risk_level,
        a.requires_block = $requires_block
    """

    tx.run(
        query,

        user_id=row["user_id"],

        created_at=to_iso_datetime(
            row.get(
                "created_at",
                pd.Timestamp.now()
            )
        ),

        kyc_status=row.get(
            "kyc_status",
            "UNKNOWN"
        ),

        risk_score=float(
            row.get(
                "final_risk_score",
                0
            )
        ),

        risk_level=row.get(
            "risk_level",
            "LOW"
        ),

        requires_block=int(
            row.get(
                "requires_block",
                0
            )
        )
    )


# =====================================================
# MARK FRAUDULENT NODES
# =====================================================

def mark_fraudulent_nodes(tx, row):

    if int(row.get("requires_block", 0)) != 1:
        return

    query = """
    MATCH (a:Account {
        user_id:$user_id
    })

    SET a:Fraudulent
    """

    tx.run(
        query,
        user_id=row["user_id"]
    )


# =====================================================
# CREATE TRANSFER EDGES
# =====================================================

def create_transfer_edges(tx, row):

    query = """
    MATCH (s:Account {
        user_id:$sender_id
    })

    MATCH (r:Account {
        user_id:$receiver_id
    })

    MERGE (s)-[t:TRANSFER {
        trans_id:$trans_id
    }]->(r)

    SET
        t.amount = $amount,
        t.timestamp = datetime($timestamp),
        t.channel = $channel,
        t.is_high_value = (
            $amount > 49000
        )
    """

    tx.run(
        query,

        sender_id=row["sender_id"],

        receiver_id=row["receiver_id"],

        trans_id=row["trans_id"],

        amount=float(
            row["amount"]
        ),

        timestamp=to_iso_datetime(
            row["timestamp"]
        ),

        channel=row.get(
            "channel",
            "UPI"
        )
    )


# =====================================================
# CREATE DEVICE RELATIONSHIPS
# =====================================================

def create_device_relationships(tx, row):

    if "device_id" not in row:
        return

    query = """
    MATCH (a:Account {
        user_id:$user_id
    })

    MERGE (d:Device {
        device_id:$device_id
    })

    MERGE (a)-[:USES_DEVICE]->(d)
    """

    tx.run(
        query,

        user_id=row["user_id"],

        device_id=row["device_id"]
    )


# =====================================================
# CREATE IP RELATIONSHIPS
# =====================================================

def create_ip_relationships(tx, row):

    if "ip_address" not in row:
        return

    query = """
    MATCH (a:Account {
        user_id:$user_id
    })

    MERGE (ip:IPAddress {
        ip_address:$ip_address
    })

    MERGE (a)-[:USES_IP]->(ip)
    """

    tx.run(
        query,

        user_id=row["user_id"],

        ip_address=row["ip_address"]
    )


# =====================================================
# CREATE CO-CREATED RELATIONSHIPS
# =====================================================

def create_co_created_relationships(tx, pairs):

    query = """
    UNWIND $pairs AS pair
    MATCH (a1:Account {user_id: pair.a1})
    MATCH (a2:Account {user_id: pair.a2})

    MERGE (a1)-[r:CO_CREATED]->(a2)

    SET r.time_gap_secs = pair.time_gap_secs
    """

    tx.run(
        query,
        pairs=pairs
    )


def iter_co_created_batches():

    if "created_at" not in users_df.columns:
        return

    working_df = users_df.copy()

    working_df["created_at"] = pd.to_datetime(
        working_df["created_at"],
        errors="coerce"
    )

    working_df["created_minute"] = (
        working_df["created_at"].dt.floor("min")
    )

    working_df = working_df.dropna(
        subset=["created_minute", "created_at"]
    )

    batch = []

    for _, group in working_df.groupby("created_minute"):

        rows = list(
            group[["user_id", "created_at"]]
            .sort_values("user_id")
            .itertuples(index=False, name=None)
        )

        if len(rows) < 2:
            continue

        for left, right in combinations(rows, 2):

            time_gap_secs = abs(
                (right[1] - left[1]).total_seconds()
            )

            if time_gap_secs > 60:
                continue

            batch.append({
                "a1": left[0],
                "a2": right[0],
                "time_gap_secs": int(time_gap_secs)
            })

            if len(batch) >= CO_CREATED_BATCH_SIZE:

                yield batch

                batch = []

    if len(batch) > 0:

        yield batch


# =====================================================
# CREATE SHARED DEVICE RELATIONSHIPS
# =====================================================

def create_shared_device_links(tx):

    query = """
    MATCH (a1:Account)-[:USES_DEVICE]->(d:Device)<-[:USES_DEVICE]-(a2:Account)

    WHERE a1.user_id < a2.user_id

    MERGE (a1)-[:SHARED_DEVICE]->(a2)
    """

    tx.run(query)


# =====================================================
# CREATE SHARED IP RELATIONSHIPS
# =====================================================

def create_shared_ip_links(tx):

    query = """
    MATCH (a1:Account)-[:USES_IP]->(ip:IPAddress)<-[:USES_IP]-(a2:Account)

    WHERE a1.user_id < a2.user_id

    MERGE (a1)-[:SHARED_IP]->(a2)
    """

    tx.run(query)


# =====================================================
# MAIN LOAD
# =====================================================

def load_graph():

    print("🚀 Loading Enterprise AML Graph into Neo4j...")

    with driver.session() as session:

        # ---------------------------------------------
        # CONSTRAINTS
        # ---------------------------------------------

        print("⚙️ Creating Constraints & Indexes...")

        session.execute_write(
            create_constraints
        )

        # ---------------------------------------------
        # ACCOUNT NODES
        # ---------------------------------------------

        print("📦 Creating Account Nodes...")

        for _, row in users_df.iterrows():

            session.execute_write(
                create_account_nodes,
                row
            )

            session.execute_write(
                mark_fraudulent_nodes,
                row
            )

            session.execute_write(
                create_device_relationships,
                row
            )

            session.execute_write(
                create_ip_relationships,
                row
            )

        # ---------------------------------------------
        # TRANSFER RELATIONSHIPS
        # ---------------------------------------------

        print("🔗 Creating Transfer Relationships...")

        for _, row in tx_df.iterrows():

            session.execute_write(
                create_transfer_edges,
                row
            )

        # ---------------------------------------------
        # SYNTHETIC RELATIONSHIPS
        # ---------------------------------------------

        print("🕸️ Creating Shared Infrastructure Links...")

        session.execute_write(
            create_shared_device_links
        )

        session.execute_write(
            create_shared_ip_links
        )

        print("🧩 Creating Co-Created Relationships...")

        for batch in iter_co_created_batches():

            session.execute_write(
                create_co_created_relationships,
                batch
            )

    print("✅ Enterprise Neo4j AML Graph Loaded Successfully")


# =====================================================
# ENTRYPOINT
# =====================================================

if __name__ == "__main__":

    load_graph()

    driver.close()