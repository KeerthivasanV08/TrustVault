import asyncio
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Iterable, List

import pandas as pd

from app.core import storage_paths

RUNTIME_DIR = storage_paths.RUNTIME_DIR
RECENT_TRANSACTIONS_PATH = storage_paths.RUNTIME_DIR / "recent_transactions.csv"
USER_VELOCITY_STATE_PATH = storage_paths.RUNTIME_VELOCITY_STATE_PATH
# Immutable offline seed dataset. Never write realtime transactions here.
RAW_TRANSACTION_SEED_PATH = storage_paths.DATA_DIR / "raw" / "transactions.csv"

RECENT_TRANSACTION_COLUMNS = [
    "trans_id",
    "sender_id",
    "receiver_id",
    "amount",
    "timestamp",
]

VELOCITY_STATE_COLUMNS = [
    "user_id",
    "rolling_24h_sum",
    "txn_count_24h",
    "unique_counterparties_24h",
    "drain_ratio",
    "round_number_ratio",
    "near_threshold_count",
    "avg_holding_time_mins",
    "velocity_gradient",
    "last_updated",
]

# Bounded in-memory runtime state
LIVE_TRANSACTIONS: deque = deque(maxlen=500)
LIVE_ALERTS: deque = deque(maxlen=200)
LIVE_GRAPH_EVENTS: deque = deque(maxlen=500)
USER_RECENT_HISTORY = defaultdict(lambda: deque(maxlen=100))
USER_TRANSACTION_HISTORY = USER_RECENT_HISTORY
USER_VELOCITY_STATE: Dict[str, Dict[str, Any]] = {}

DASHBOARD_METRICS: Dict[str, Any] = {
    "total_transactions": 0,
    "blocked_transactions": 0,
    "review_queue": 0,
    "high_risk_count": 0,
}

_SUBSCRIBERS: List[asyncio.Queue] = []
_LIVE_TRANSACTION_IDS: set[str] = set()
_SNAPSHOT_LOCK = Lock()
_RECENT_PERSIST_COUNTER = 0
_VELOCITY_PERSIST_COUNTER = 0


def _ensure_runtime_dir() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _normalize_timestamp_column(frame: pd.DataFrame) -> pd.DataFrame:
    if "timestamp" not in frame.columns or frame.empty:
        return frame

    normalized = frame.copy()
    normalized["timestamp"] = pd.to_datetime(normalized["timestamp"], errors="coerce", utc=True)
    normalized = normalized.sort_values(by="timestamp", ascending=False, na_position="last")
    return normalized


def _atomic_write_csv(frame: pd.DataFrame, path: Path) -> None:
    _ensure_runtime_dir()
    tmp_path = path.with_suffix(".tmp")
    frame.to_csv(tmp_path, index=False)
    tmp_path.replace(path)


def _read_csv_tail(path: Path, max_rows: int, usecols: List[str] | None = None) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()

    try:
        if usecols:
            header = pd.read_csv(path, nrows=0)
            present = [column for column in usecols if column in header.columns]
            if present:
                return pd.read_csv(path, usecols=present).tail(max_rows)
        return pd.read_csv(path).tail(max_rows)
    except Exception:
        return pd.DataFrame()


def _seed_recent_transactions(max_rows: int = 500) -> pd.DataFrame:
    seed_columns = [
        "trans_id",
        "sender_id",
        "receiver_id",
        "amount",
        "timestamp",
        "sender_bal_before",
        "receiver_bal_after",
        "payment_mode",
        "device_id",
        "time_since_last_credit_ms",
        "tx_count_24h",
        "drain_ratio",
        "forwarding_delay_mins",
        "amount_deviation",
        "balance_depletion_speed",
        "txn_velocity_1h",
        "is_fraud",
    ]

    frame = _read_csv_tail(RAW_TRANSACTION_SEED_PATH, max_rows=max_rows, usecols=seed_columns)
    if frame.empty:
        return frame

    frame = _normalize_timestamp_column(frame)
    if "trans_id" in frame.columns:
        frame = frame.drop_duplicates(subset=["trans_id"], keep="first")
    return frame.head(max_rows)


def _load_runtime_snapshot() -> pd.DataFrame:
    if RECENT_TRANSACTIONS_PATH.exists():
        frame = pd.read_csv(RECENT_TRANSACTIONS_PATH)
        if not frame.empty:
            frame = _normalize_timestamp_column(frame)
            if "trans_id" in frame.columns:
                frame = frame.drop_duplicates(subset=["trans_id"], keep="first")
            return frame.head(500)

    frame = _seed_recent_transactions(500)
    if frame.empty:
        return frame

    persist_recent_transactions(frame.to_dict(orient="records"), max_rows=500)
    return frame


def _load_velocity_state_frame() -> pd.DataFrame:
    if not USER_VELOCITY_STATE_PATH.exists():
        return pd.DataFrame(columns=VELOCITY_STATE_COLUMNS)

    try:
        frame = pd.read_csv(USER_VELOCITY_STATE_PATH)
    except Exception:
        return pd.DataFrame(columns=VELOCITY_STATE_COLUMNS)

    if frame.empty:
        return pd.DataFrame(columns=VELOCITY_STATE_COLUMNS)

    if "user_id" in frame.columns:
        frame = frame.drop_duplicates(subset=["user_id"], keep="last")

    return frame


def initialize_runtime_store() -> None:
    _ensure_runtime_dir()
    global _RECENT_PERSIST_COUNTER, _VELOCITY_PERSIST_COUNTER
    _RECENT_PERSIST_COUNTER = 0
    _VELOCITY_PERSIST_COUNTER = 0

    LIVE_TRANSACTIONS.clear()
    _LIVE_TRANSACTION_IDS.clear()
    USER_RECENT_HISTORY.clear()
    USER_VELOCITY_STATE.clear()

    recent_frame = _load_runtime_snapshot()
    if not recent_frame.empty:
        for _, row in recent_frame.iterrows():
            record = row.to_dict()
            trans_id = str(record.get("trans_id") or "")
            if trans_id and trans_id in _LIVE_TRANSACTION_IDS:
                continue
            if trans_id:
                _LIVE_TRANSACTION_IDS.add(trans_id)
            LIVE_TRANSACTIONS.append(record)
            sender_id = str(record.get("sender_id") or record.get("user_id") or "")
            if sender_id:
                USER_RECENT_HISTORY[sender_id].append(record)

    velocity_frame = _load_velocity_state_frame()
    for _, row in velocity_frame.iterrows():
        user_id = str(row.get("user_id") or "")
        if not user_id:
            continue
        USER_VELOCITY_STATE[user_id] = row.to_dict()

    if not RECENT_TRANSACTIONS_PATH.exists():
        persist_recent_transactions([], max_rows=500)
    if not USER_VELOCITY_STATE_PATH.exists():
        persist_velocity_state()


def persist_recent_transactions(rows: List[Dict[str, Any]] | None = None, max_rows: int = 500) -> None:
    _ensure_runtime_dir()
    source_rows = rows if rows is not None else list(LIVE_TRANSACTIONS)
    frame = pd.DataFrame(source_rows)

    if frame.empty:
        frame = pd.DataFrame(columns=RECENT_TRANSACTION_COLUMNS)
        _atomic_write_csv(frame, RECENT_TRANSACTIONS_PATH)
        return

    if "timestamp" in frame.columns:
        frame = _normalize_timestamp_column(frame)
    if "trans_id" in frame.columns:
        frame = frame.drop_duplicates(subset=["trans_id"], keep="first")

    frame = frame.head(max_rows)
    _atomic_write_csv(frame, RECENT_TRANSACTIONS_PATH)


def persist_velocity_state(state: Dict[str, Dict[str, Any]] | None = None) -> None:
    _ensure_runtime_dir()
    active_state = state if state is not None else USER_VELOCITY_STATE
    frame = pd.DataFrame(list(active_state.values()))

    if frame.empty:
        frame = pd.DataFrame(columns=VELOCITY_STATE_COLUMNS)
        _atomic_write_csv(frame, USER_VELOCITY_STATE_PATH)
        return

    if "user_id" in frame.columns:
        frame = frame.drop_duplicates(subset=["user_id"], keep="last")
    if "last_updated" in frame.columns:
        frame = frame.sort_values(by="last_updated", ascending=False, na_position="last")

    _atomic_write_csv(frame, USER_VELOCITY_STATE_PATH)


def get_recent_transactions(limit: int = 500, newest_first: bool = True) -> List[Dict[str, Any]]:
    if LIVE_TRANSACTIONS:
        rows = list(LIVE_TRANSACTIONS)
    elif RECENT_TRANSACTIONS_PATH.exists():
        frame = pd.read_csv(RECENT_TRANSACTIONS_PATH)
        if frame.empty:
            rows = []
        else:
            frame = _normalize_timestamp_column(frame)
            if "trans_id" in frame.columns:
                frame = frame.drop_duplicates(subset=["trans_id"], keep="first")
            rows = frame.head(limit).to_dict(orient="records")
    else:
        frame = _seed_recent_transactions(limit)
        rows = frame.to_dict(orient="records") if not frame.empty else []

    if not rows:
        return []

    frame = pd.DataFrame(rows)
    if "timestamp" in frame.columns:
        frame = _normalize_timestamp_column(frame)
    if "trans_id" in frame.columns:
        frame = frame.drop_duplicates(subset=["trans_id"], keep="first")

    if newest_first:
        return frame.head(limit).to_dict(orient="records")

    ordered = frame.sort_values(by="timestamp", ascending=True, na_position="last") if "timestamp" in frame.columns else frame.iloc[::-1]
    return ordered.head(limit).to_dict(orient="records")


def append_transaction(txn: Dict[str, Any]) -> bool:
    record = dict(txn)
    trans_id = str(record.get("trans_id") or record.get("transaction_id") or record.get("id") or "")
    if trans_id and trans_id in _LIVE_TRANSACTION_IDS:
        return False

    if trans_id:
        _LIVE_TRANSACTION_IDS.add(trans_id)

    if len(LIVE_TRANSACTIONS) >= LIVE_TRANSACTIONS.maxlen:
        dropped = LIVE_TRANSACTIONS.pop()
        dropped_id = str(dropped.get("trans_id") or dropped.get("transaction_id") or dropped.get("id") or "")
        if dropped_id:
            _LIVE_TRANSACTION_IDS.discard(dropped_id)

    LIVE_TRANSACTIONS.appendleft(record)

    sender_id = str(record.get("sender_id") or record.get("user_id") or "")
    if sender_id:
        USER_RECENT_HISTORY[sender_id].append(record)

    global _RECENT_PERSIST_COUNTER
    _RECENT_PERSIST_COUNTER += 1
    if _RECENT_PERSIST_COUNTER >= 10:
        persist_recent_transactions(max_rows=500)
        _RECENT_PERSIST_COUNTER = 0

    DASHBOARD_METRICS["total_transactions"] = DASHBOARD_METRICS.get("total_transactions", 0) + 1
    return True


def update_user_velocity_state(user_id: str, state: Dict[str, Any]) -> None:
    if not user_id:
        return

    USER_VELOCITY_STATE[str(user_id)] = dict(state)

    global _VELOCITY_PERSIST_COUNTER
    _VELOCITY_PERSIST_COUNTER += 1
    if _VELOCITY_PERSIST_COUNTER >= 20:
        persist_velocity_state()
        _VELOCITY_PERSIST_COUNTER = 0


def get_user_recent_history(user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    history = list(USER_RECENT_HISTORY.get(str(user_id), deque()))
    if not history:
        return []

    frame = pd.DataFrame(history)
    if frame.empty:
        return []
    if "timestamp" in frame.columns:
        frame = _normalize_timestamp_column(frame)
        frame = frame.sort_values(by="timestamp", ascending=True, na_position="last")
    if "trans_id" in frame.columns:
        frame = frame.drop_duplicates(subset=["trans_id"], keep="last")
    return frame.tail(limit).to_dict(orient="records")


def append_alert(alert: Dict[str, Any]) -> None:
    LIVE_ALERTS.appendleft(alert)
    DASHBOARD_METRICS["review_queue"] = max(0, DASHBOARD_METRICS.get("review_queue", 0) + 1)


def append_graph_event(event: Dict[str, Any]) -> None:
    LIVE_GRAPH_EVENTS.appendleft(event)


def update_metrics(updates: Dict[str, int]) -> None:
    for k, v in updates.items():
        DASHBOARD_METRICS[k] = v


def subscribe() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _SUBSCRIBERS.append(q)
    return q


def unsubscribe(q: asyncio.Queue) -> None:
    try:
        _SUBSCRIBERS.remove(q)
    except ValueError:
        pass


async def publish_event(event: Dict[str, Any]) -> None:
    for q in list(_SUBSCRIBERS):
        try:
            q.put_nowait(event)
        except Exception:
            try:
                _SUBSCRIBERS.remove(q)
            except Exception:
                pass
