from fastapi import APIRouter
from schemas.transaction_schema import TransactionRequest
from app.services.transaction.transaction_service import TransactionService
from app.realtime.transaction_memory_store import get_recent_transactions

router = APIRouter(tags=["Transactions"])

service = TransactionService()


@router.post("")
async def create_transaction(request: TransactionRequest):
    return await service.process_transaction(request.model_dump())


@router.post("/analyze")
async def analyze_transaction(request: TransactionRequest):
    return await service.process_transaction(request.model_dump())


@router.get("/recent")
async def recent_transactions(limit: int = 50):
    # Return the bounded live snapshot first, then the compact runtime fallback.
    return get_recent_transactions(limit=limit, newest_first=True)