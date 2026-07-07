from fastapi import APIRouter
from schemas.transaction_schema import TransactionRequest
from app.services.transaction.transaction_service import TransactionService
from app.realtime.transaction_memory_store import LIVE_TRANSACTIONS

router = APIRouter(tags=["Transactions"])

service = TransactionService()


@router.post("")
async def create_transaction(request: TransactionRequest):
    return await service.process_transaction(request.model_dump())


@router.post("/analyze")
async def analyze_transaction(request: TransactionRequest):
    return await service.process_transaction(request.model_dump())


@router.get("/recent")
async def recent_transactions():
    # Return a list snapshot of the in-memory recent transactions
    return list(LIVE_TRANSACTIONS)