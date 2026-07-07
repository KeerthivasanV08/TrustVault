from __future__ import annotations

try:
    from sse_starlette.sse import EventSourceResponse
except ModuleNotFoundError:
    from starlette.responses import StreamingResponse

    class EventSourceResponse(StreamingResponse):
        def __init__(self, content, status_code=200, headers=None, media_type="text/event-stream", background=None):
            async def _as_sse_stream():
                async for item in content:
                    if isinstance(item, dict):
                        event = item.get("event", "message")
                        data = item.get("data", "")
                        yield f"event: {event}\ndata: {data}\n\n"
                    else:
                        yield item

            super().__init__(
                _as_sse_stream(),
                status_code=status_code,
                headers=headers,
                media_type=media_type,
                background=background,
            )
