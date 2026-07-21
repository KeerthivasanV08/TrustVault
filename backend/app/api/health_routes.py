from fastapi import APIRouter
import time

from app.core.model_loader import get_model_health
from app.core.runtime_context import get_runtime_session_id, get_runtime_started_at
from app.core.policy_engine import get_policy_engine
from app.realtime.transaction_memory_store import LIVE_ALERTS, LIVE_TRANSACTIONS, USER_VELOCITY_STATE
from app.db.neo4j_client import Neo4jClient

router = APIRouter()

START_TIME = time.time()


@router.get("/health")
def health_check():
    return {
        "status": "OK",
        "service": "TrustVault AML Engine",
        "uptime_sec": int(time.time() - START_TIME),
        "runtime_session_id": get_runtime_session_id(),
        "started_at": get_runtime_started_at(),
    }


@router.get("/ready")
def readiness_check():
    health = get_model_health()
    graph_engine = health.get("graph_engine", health.get("graph_model", "degraded"))
    transaction_sse = "active"
    alert_sse = "active"
    backend_status = "healthy" if health.get("runtime_mode") == "FULL" else "degraded"
    policy = get_policy_engine()
    neo4j = Neo4jClient()
    return {
        "status": "READY" if health.get("runtime_mode") == "FULL" else "DEGRADED",
        "backend": backend_status,
        "ml_engine": "ACTIVE" if health.get("behavioral_model") == "healthy" else "DEGRADED",
        "behavioral_model": health.get("behavioral_model", "failed"),
        "sequence_model": health.get("sequence_model", "failed"),
        "graph_engine": "ACTIVE" if graph_engine == "healthy" else "DEGRADED",
        "neo4j_graph_engine": graph_engine,
        "control_engine": "ACTIVE",
        "policy_engine": "ACTIVE" if policy.loaded() else "DEGRADED",
        "runtime_mode": health.get("runtime_mode", "DEGRADED"),
        "transaction_sse": transaction_sse,
        "alert_sse": alert_sse,
        "runtime_session_id": get_runtime_session_id(),
        "started_at": get_runtime_started_at(),
        "recent_transaction_count": len(LIVE_TRANSACTIONS),
        "active_velocity_users": len(USER_VELOCITY_STATE),
        "live_alert_count": len(LIVE_ALERTS),
        "neo4j_available": neo4j.is_available(),
    }


@router.get("/system/model-health")
def model_health():
    health = get_model_health()
    return {
        "backend": "healthy" if health.get("runtime_mode") == "FULL" else "degraded",
        "behavioral_model": health.get("behavioral_model", "failed"),
        "sequence_model": health.get("sequence_model", "failed"),
        "graph_engine": health.get("graph_engine", health.get("graph_model", "failed")),
        "neo4j_graph_engine": health.get("graph_engine", health.get("graph_model", "failed")),
        "runtime_mode": health.get("runtime_mode", "DEGRADED"),
        "transaction_sse": "active",
        "alert_sse": "active",
    }