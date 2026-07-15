from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4


_runtime_lock = Lock()
_runtime_session_id: str | None = None
_started_at: str | None = None


@dataclass(frozen=True)
class RuntimeSessionMetadata:
    runtime_session_id: str
    started_at: str


def initialize_runtime_session() -> RuntimeSessionMetadata:
    global _runtime_session_id, _started_at
    with _runtime_lock:
        if _runtime_session_id is None:
            _started_at = datetime.now(timezone.utc).isoformat()
            _runtime_session_id = f"RUN-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:6].upper()}"
        return RuntimeSessionMetadata(runtime_session_id=_runtime_session_id, started_at=_started_at or datetime.now(timezone.utc).isoformat())


def get_runtime_session_id() -> str:
    return initialize_runtime_session().runtime_session_id


def get_runtime_started_at() -> str:
    return initialize_runtime_session().started_at