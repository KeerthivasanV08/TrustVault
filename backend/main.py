from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.runtime_context import initialize_runtime_session
from app.core.policy_engine import get_policy_engine

# Ensure storage directories exist before importing services that may write files
from app.core.storage_paths import initialize_storage_directories
initialize_storage_directories()
runtime_session = initialize_runtime_session()
policy_engine = get_policy_engine()

from app.realtime.transaction_memory_store import initialize_runtime_store
initialize_runtime_store()

from app.services.transaction.audit_service import initialize_transaction_audit_storage
initialize_transaction_audit_storage()

from app.api.onboarding_routes import router as onboarding_router
from app.api.health_routes import router as health_router
from app.api.officer_routes import router as officer_router
from app.api.transaction_routes import router as transaction_router
from app.api.v1.reports import router as reports_router

# Preload ML models at startup
from app.core.model_loader import initialize_model_runtime, get_model_loader

# Realtime engine
from app.realtime.realtime_engine import start_realtime_engine_once
from app.realtime.transaction_streamer import router as realtime_router
from app.api.accounts_routes import router as accounts_router

# SLA monitoring
from app.services.officer.sla_breach_monitor import sla_breach_monitor


@asynccontextmanager
async def lifespan(app: FastAPI):

    print("\n🚀 TrustVault AML Platform Starting...")

    startup_health = initialize_model_runtime()
    app.state.model_health = startup_health
    app.state.runtime_mode = startup_health.get("runtime_mode", "DEGRADED")
    app.state.runtime_session_id = runtime_session.runtime_session_id
    app.state.started_at = runtime_session.started_at
    app.state.policy_version = policy_engine.get_policy_version()

    print("✅ Behavioral Model Loaded" if startup_health.get("behavioral_model") == "healthy" else f"❌ Behavioral Model Failed: {startup_health.get('artifacts', {}).get('behavioral_model', {}).get('reason', 'unknown')}")
    print("✅ Sequence Model Loaded" if startup_health.get("sequence_model") == "healthy" else f"❌ Sequence Model Failed: {startup_health.get('artifacts', {}).get('sequence_model', {}).get('reason', 'unknown')}")
    print("✅ Graph Engine Connected" if startup_health.get("graph_engine") == "healthy" else f"❌ Graph Engine Degraded: {startup_health.get('artifacts', {}).get('graph_engine', {}).get('reason', 'unknown')}")
    print(f"✅ Runtime Mode: {startup_health.get('runtime_mode', 'DEGRADED')}")

    print("✅ AML Services Initialized")
    print(f"✅ Runtime Session: {runtime_session.runtime_session_id}")
    print(f"✅ Policy Version: {app.state.policy_version}")
    print("✅ API Ready\n")
    # start realtime engine in background
    try:
        start_realtime_engine_once()
        print("✅ Realtime engine started")
    except Exception:
        print("⚠️ Failed to start realtime engine")

    # Start SLA monitoring
    try:
        sla_breach_monitor.start_monitoring()
        print("✅ SLA monitoring started")
    except Exception as e:
        print(f"⚠️ Failed to start SLA monitoring: {e}")

    yield

    print("\n🛑 TrustVault AML Platform Shutdown")
    
    # Stop SLA monitoring
    try:
        sla_breach_monitor.stop_monitoring()
    except Exception:
        pass


app = FastAPI(
    title="TrustVault AML Platform",
    version="2026.1",
    description="Enterprise AML Monitoring & Mule Detection Platform",
    lifespan=lifespan,
)

# ---------------------------------------------------
# CORS
# ---------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_ORIGINS or ["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------
# ROUTERS
# ---------------------------------------------------

app.include_router(
    onboarding_router,
    prefix="/api/onboarding",
    tags=["Onboarding AML"],
)

app.include_router(
    transaction_router,
    prefix="/api/transactions",
    tags=["Transaction AML"],
)

app.include_router(
    accounts_router,
    prefix="/api/accounts",
    tags=["Accounts"],
)

# realtime SSE router (streams under /api/transactions/realtime)
app.include_router(realtime_router, prefix="/api/transactions", tags=["Realtime"])

from app.api.graph_routes import router as graph_router
from app.api.dashboard_routes import router as dashboard_router
from app.realtime.alerts_streamer import router as alerts_realtime_router
from app.api.alerts_routes import router as alerts_router
from app.api.case_routes import router as cases_router

app.include_router(graph_router, prefix="/api/graph", tags=["Graph"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(alerts_realtime_router, prefix="/api/alerts", tags=["Alerts Realtime"])
app.include_router(alerts_router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(cases_router, prefix="/api/cases", tags=["Cases"])

app.include_router(
    reports_router,
    prefix="/api",
    tags=["Reports"],
)

app.include_router(
    health_router,
    prefix="/api",
    tags=["Health"],
)

app.include_router(
    officer_router,
    prefix="/api/officer",
    tags=["Officer Review"],
)

@app.get("/")
def root():

    return {
        "message": "TrustVault AML Platform Running",
        "docs": "/docs",
    }