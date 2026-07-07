import asyncio
import json
from fastapi import APIRouter, Request

from app.realtime.sse_compat import EventSourceResponse

from app.realtime.transaction_memory_store import subscribe, unsubscribe

router = APIRouter()


@router.get("/realtime")
async def transactions_realtime(request: Request):
    """Server-Sent Events endpoint streaming realtime transactions."""
    q = subscribe()

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    item = await q.get()
                except asyncio.CancelledError:
                    break
                if item is None:
                    continue
                yield {"event": item.get("event", "transaction"), "data": json.dumps(item.get("data"))}
        finally:
            unsubscribe(q)

    return EventSourceResponse(event_generator())
