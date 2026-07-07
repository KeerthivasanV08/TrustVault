from fastapi import APIRouter
from app.realtime.transaction_memory_store import DASHBOARD_METRICS

router = APIRouter(tags=["Dashboard"])


@router.get("/metrics")
async def metrics():
    return DASHBOARD_METRICS
