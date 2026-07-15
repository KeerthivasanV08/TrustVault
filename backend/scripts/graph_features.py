# scripts/graph_features.py

import pandas as pd
from pathlib import Path
import sys

# -----------------------------
# FIX PYTHON IMPORT PATH
# -----------------------------
BACKEND_DIR = Path(__file__).resolve().parents[1]
AML_DIR = Path(__file__).resolve().parents[2]

sys.path.append(str(BACKEND_DIR))

from app.services.graph_service import (
    get_graph_intelligence
)

# -----------------------------
# PATH CONFIG
# -----------------------------
RAW_PATH = (
    AML_DIR
    / "data"
    / "raw"
    / "users.csv"
)

OUT_PATH = AML_DIR / "data" / "processed" / "training" / "graph_features.csv"


def build_graph_features():
    """
    Transform Neo4j topology into ML-ready graph features.
    """

    # -----------------------------
    # LOAD USERS
    # -----------------------------
    if not RAW_PATH.exists():

        print(
            f"❌ users.csv not found: {RAW_PATH}"
        )

        return

    users_df = pd.read_csv(RAW_PATH)

    print(
        f"🚀 Starting Graph Extraction "
        f"for {len(users_df)} users..."
    )

    graph_rows = []

    # -----------------------------
    # GRAPH INTELLIGENCE EXTRACTION
    # -----------------------------
    for i, uid in enumerate(users_df["user_id"]):

        try:

            intel = get_graph_intelligence(
                str(uid)
            )

            metrics = intel.get(
                "graph_metrics",
                {}
            )

            flags = intel.get(
                "graph_flags",
                {}
            )

            graph_rows.append({

                "user_id": uid,

                # normalized graph signal
                "graph_score":
                    intel.get(
                        "graph_score",
                        0.0
                    ),

                # topology metrics
                "known_fraud_connections":
                    metrics.get(
                        "known_fraud_connections",
                        0
                    ),

                "mule_cluster_size":
                    metrics.get(
                        "mule_cluster_size",
                        0
                    ),

                "inbound_sources":
                    metrics.get(
                        "inbound_sources",
                        0
                    ),

                "outbound_dest":
                    metrics.get(
                        "outbound_dest",
                        0
                    ),

                # corrected flag
                "rapid_account_cluster_flag": int(
                    flags.get(
                        "mule_cluster",
                        False
                    )
                ),

                "mule_cluster_flag": int(
                    flags.get(
                        "mule_cluster",
                        False
                    )
                )
            })

            # progress logger
            if (i + 1) % 1000 == 0:

                print(
                    f"📊 Processed "
                    f"{i+1}/{len(users_df)} users"
                )

        except Exception as e:

            print(
                f"⚠️ Failed for {uid}: {e}"
            )

            continue

    # -----------------------------
    # SAVE FEATURES
    # -----------------------------
    graph_df = pd.DataFrame(graph_rows)

    OUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    graph_df.to_csv(
        OUT_PATH,
        index=False
    )

    print("\n✅ training/graph_features.csv created")
    print(f"📍 Saved at: {OUT_PATH}")
    print(
        f"📈 Rows: {len(graph_df)} | "
        f"Columns: {len(graph_df.columns)}"
    )


if __name__ == "__main__":
    build_graph_features()