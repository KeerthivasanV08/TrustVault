from pathlib import Path

import pandas as pd

from app.core import storage_paths
from app.realtime.transaction_memory_store import (
    RAW_TRANSACTION_SEED_PATH,
    RECENT_TRANSACTIONS_PATH,
    get_recent_transactions,
    get_user_recent_history,
    initialize_runtime_store,
)

BASE_DIR = Path(__file__).resolve().parents[4]

TXN_DIR = BASE_DIR / "data" / "processed"
ONBOARDING_DIR = BASE_DIR / "data" / "processed"

USER_FEATURES_PATH = TXN_DIR / "user_features.csv"
USER_VELOCITY_PATH = storage_paths.RUNTIME_VELOCITY_STATE_PATH
ONBOARDING_RESULTS_PATH = storage_paths.ONBOARDING_RISK_SNAPSHOT_PATH
RECENT_FALLBACK_PATHS = [
    RECENT_TRANSACTIONS_PATH,
    RAW_TRANSACTION_SEED_PATH,
    BASE_DIR / "data" / "processed" / "final_dataset.csv",
]


class ContextService:
    _user_df = None
    _velocity_df = None
    _onboarding_df = None
    _recent_txn_df = None

    def __init__(self):
        initialize_runtime_store()
        if ContextService._user_df is None:
            ContextService._user_df = self._load_indexed(USER_FEATURES_PATH, "user_id")

        if ContextService._velocity_df is None:
            ContextService._velocity_df = self._load_indexed(USER_VELOCITY_PATH, "user_id")

        if ContextService._onboarding_df is None:
            ContextService._onboarding_df = self._load_indexed(
                ONBOARDING_RESULTS_PATH,
                "user_id",
            )

        if ContextService._recent_txn_df is None:
            ContextService._recent_txn_df = self._load_recent_transactions()

    def _load_plain(self, path: Path):
        if path.exists():
            return pd.read_csv(path)
        return pd.DataFrame()

    def _load_recent_transactions(self) -> pd.DataFrame:
        frame = pd.DataFrame(get_recent_transactions(limit=500, newest_first=True))
        if not frame.empty:
            return frame

        for fallback_path in RECENT_FALLBACK_PATHS:
            if fallback_path.exists():
                try:
                    fallback_df = pd.read_csv(fallback_path)
                    if not fallback_df.empty:
                        return fallback_df
                except Exception:
                    continue

        return pd.DataFrame()

    def _ensure_recent_transactions(self) -> pd.DataFrame:
        recent_rows = get_recent_transactions(limit=500, newest_first=True)
        if recent_rows:
            recent_df = pd.DataFrame(recent_rows)
            ContextService._recent_txn_df = recent_df
            return recent_df

        if ContextService._recent_txn_df is None or ContextService._recent_txn_df.empty:
            ContextService._recent_txn_df = self._load_recent_transactions()

        return ContextService._recent_txn_df

    def _column_matches(self, df: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
        for column in candidates:
            if column in df.columns:
                return column
        return None

    def _load_indexed(self, path: Path, index_col: str):
        if not path.exists():
            return pd.DataFrame()

        df = pd.read_csv(path)

        if index_col in df.columns:
            df = df.drop_duplicates(subset=[index_col], keep="last")
            df = df.set_index(index_col)

        return df

    def get_user_context(self, user_id: str) -> dict:
        df = ContextService._user_df

        if df.empty or user_id not in df.index:
            return {}

        return df.loc[user_id].to_dict()

    def get_velocity_context(self, user_id: str) -> dict:
        df = ContextService._velocity_df

        if df.empty or user_id not in df.index:
            return {
                "rolling_24h_sum": 0,
                "txn_burst_count": 0,
                "txn_velocity_1h": 0,
                "near_threshold_count": 0,
                "fragmentation_score": 0,
                "round_number_ratio": 0,
                "drain_ratio": 0,
                "pass_through_ratio": 0,
                "rapid_outbound_after_inbound": 0,
                "forwarding_delay_mins": 999,
            }

        return df.loc[user_id].to_dict()

    def get_onboarding_context(self, user_id: str) -> dict:
        df = ContextService._onboarding_df

        if df.empty or user_id not in df.index:
            return {
                "decision": "UNKNOWN",
                "identity_risk": 50,
                "confidence": 0.5,
            }

        return df.loc[user_id].to_dict()

    def get_recent_transactions(self, user_id: str, limit: int = 20) -> list[dict]:
        rows = get_user_recent_history(user_id, limit=limit)
        if rows:
            return rows

        df = self._ensure_recent_transactions()

        if df.empty:
            return []

        sender_col = self._column_matches(df, ("sender_id", "sender", "from", "source_id", "account_id"))
        receiver_col = self._column_matches(df, ("receiver_id", "receiver", "to", "target_id"))

        if not sender_col and not receiver_col:
            return df.tail(limit).to_dict(orient="records")

        mask = pd.Series(False, index=df.index)
        if sender_col:
            mask = mask | (df[sender_col].astype(str) == str(user_id))
        if receiver_col:
            mask = mask | (df[receiver_col].astype(str) == str(user_id))

        user_txns = df[mask]
        if "timestamp" in user_txns.columns:
            user_txns = user_txns.copy()
            user_txns["timestamp"] = pd.to_datetime(user_txns["timestamp"], errors="coerce", utc=True)
            user_txns = user_txns.sort_values(by="timestamp", ascending=True, na_position="last")

        if "trans_id" in user_txns.columns:
            user_txns = user_txns.drop_duplicates(subset=["trans_id"], keep="last")

        return user_txns.tail(limit).to_dict(orient="records")