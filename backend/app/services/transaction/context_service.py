from pathlib import Path

import pandas as pd

from app.realtime.transaction_memory_store import LIVE_TRANSACTIONS

BASE_DIR = Path(__file__).resolve().parents[4]

TXN_DIR = BASE_DIR / "data" / "processed" 
ONBOARDING_DIR = BASE_DIR / "data" / "processed"

USER_FEATURES_PATH = TXN_DIR / "user_features.csv"
USER_VELOCITY_PATH = TXN_DIR / "user_velocity.csv"
ONBOARDING_RESULTS_PATH = ONBOARDING_DIR / "onboarding_results.csv"
RECENT_TRANSACTIONS_PATH = TXN_DIR / "recent_transactions.csv"
RECENT_FALLBACK_PATHS = [
    BASE_DIR / "data" / "raw" / "transactions.csv",
    BASE_DIR / "data" / "processed" / "final_dataset.csv",
]


class ContextService:
    _user_df = None
    _velocity_df = None
    _onboarding_df = None
    _recent_txn_df = None

    def __init__(self):
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

    def _write_recent_transactions_csv(self, df: pd.DataFrame) -> None:
        if df.empty:
            return

        RECENT_TRANSACTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(RECENT_TRANSACTIONS_PATH, index=False)

    def _load_recent_transactions(self) -> pd.DataFrame:
        live_records = list(LIVE_TRANSACTIONS)
        if live_records:
            live_df = pd.DataFrame(live_records)
            self._write_recent_transactions_csv(live_df)
            return live_df

        if RECENT_TRANSACTIONS_PATH.exists():
            return pd.read_csv(RECENT_TRANSACTIONS_PATH)

        for fallback_path in RECENT_FALLBACK_PATHS:
            if fallback_path.exists():
                fallback_df = pd.read_csv(fallback_path)
                self._write_recent_transactions_csv(fallback_df)
                return fallback_df

        return pd.DataFrame()

    def _ensure_recent_transactions(self) -> pd.DataFrame:
        if LIVE_TRANSACTIONS:
            recent_df = pd.DataFrame(list(LIVE_TRANSACTIONS))
            self._write_recent_transactions_csv(recent_df)
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

        user_txns = df[mask].tail(limit)

        return user_txns.to_dict(orient="records")