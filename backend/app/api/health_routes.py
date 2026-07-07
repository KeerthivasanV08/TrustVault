from fastapi import APIRouter
import time

from app.core.model_loader import get_model_health

router = APIRouter()

START_TIME = time.time()


@router.get("/health")
def health_check():
    return {
        "status": "OK",
        "service": "TrustVault AML Engine",
        "uptime_sec": int(time.time() - START_TIME)
    }


@router.get("/ready")
def readiness_check():
    health = get_model_health()
    graph_engine = health.get("graph_engine", health.get("graph_model", "degraded"))
    transaction_sse = "active"
    alert_sse = "active"
    backend_status = "healthy" if health.get("runtime_mode") == "FULL" else "degraded"
    return {
        "status": "READY" if health.get("runtime_mode") == "FULL" else "DEGRADED",
        "backend": backend_status,
        "ml_engine": "ACTIVE" if health.get("behavioral_model") == "healthy" else "DEGRADED",
        "behavioral_model": health.get("behavioral_model", "failed"),
        "sequence_model": health.get("sequence_model", "failed"),
        "graph_engine": "ACTIVE" if graph_engine == "healthy" else "DEGRADED",
        "neo4j_graph_engine": graph_engine,
        "control_engine": "ACTIVE",
        "runtime_mode": health.get("runtime_mode", "DEGRADED"),
        "transaction_sse": transaction_sse,
        "alert_sse": alert_sse,
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