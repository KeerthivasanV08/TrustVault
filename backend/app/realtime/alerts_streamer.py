import asyncio
import json
from fastapi import APIRouter, Request

from app.realtime.sse_compat import EventSourceResponse

from app.realtime.transaction_memory_store import subscribe, unsubscribe

router = APIRouter()


@router.get("/realtime")
async def alerts_realtime(request: Request):
    """SSE endpoint streaming alerts, escalations, queue changes and assignments."""
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
                # only forward alert-related events
                ev = item.get('event')
                if ev in ('alert', 'escalation', 'queue_update', 'assignment'):
                    yield {"event": ev, "data": json.dumps(item.get('data'))}
        finally:
            unsubscribe(q)

    return EventSourceResponse(event_generator())
