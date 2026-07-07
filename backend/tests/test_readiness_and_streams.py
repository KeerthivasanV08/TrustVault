import asyncio
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import dashboard_routes, graph_routes, health_routes
from app.realtime import alerts_streamer, transaction_streamer
from app.realtime.transaction_memory_store import DASHBOARD_METRICS


@contextmanager
def temp_dashboard_metrics(**updates):
    original = DASHBOARD_METRICS.copy()
    DASHBOARD_METRICS.update(updates)
    try:
        yield
    finally:
        DASHBOARD_METRICS.clear()
        DASHBOARD_METRICS.update(original)


def build_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(health_routes.router, prefix="/api")
    app.include_router(dashboard_routes.router, prefix="/api/dashboard")
    app.include_router(graph_routes.router, prefix="/api/graph")
    app.include_router(transaction_streamer.router, prefix="/api/transactions")
    app.include_router(alerts_streamer.router, prefix="/api/alerts")
    return app


class ReadinessAndStreamTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(build_test_app())

    def _queue_with_events(self, events: list[dict]) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        for event in events:
            queue.put_nowait(event)
        return queue

    def test_readiness_exposes_runtime_fields(self) -> None:
        with patch("app.api.health_routes.get_model_health", return_value={"runtime_mode": "FULL", "behavioral_model": "healthy", "sequence_model": "healthy", "graph_engine": "healthy"}):
            response = self.client.get("/api/ready")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "READY")
        self.assertEqual(payload["backend"], "healthy")
        self.assertEqual(payload["neo4j_graph_engine"], "healthy")
        self.assertEqual(payload["transaction_sse"], "active")
        self.assertEqual(payload["alert_sse"], "active")

    def test_model_health_exposes_runtime_fields(self) -> None:
        with patch("app.api.health_routes.get_model_health", return_value={"runtime_mode": "DEGRADED", "behavioral_model": "healthy", "sequence_model": "healthy", "graph_engine": "degraded"}):
            response = self.client.get("/api/system/model-health")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["backend"], "degraded")
        self.assertEqual(payload["neo4j_graph_engine"], "degraded")
        self.assertEqual(payload["transaction_sse"], "active")
        self.assertEqual(payload["alert_sse"], "active")

    def test_dashboard_metrics_endpoint_returns_live_snapshot(self) -> None:
        with temp_dashboard_metrics(total_transactions=17, blocked_transactions=4, review_queue=2, high_risk_count=3):
            response = self.client.get("/api/dashboard/metrics")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total_transactions"], 17)
        self.assertEqual(payload["blocked_transactions"], 4)
        self.assertEqual(payload["review_queue"], 2)
        self.assertEqual(payload["high_risk_count"], 3)

    def test_graph_network_endpoint_returns_graph_payload(self) -> None:
        sample_payload = {
            "nodes": [{"id": "A"}],
            "edges": [{"source": "A", "target": "B"}],
            "metadata": {"window": 25},
        }
        with patch.object(graph_routes.graph_service, "get_network", return_value=sample_payload):
            response = self.client.get("/api/graph/network?limit=25")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), sample_payload)

    def test_transaction_stream_emits_one_event(self) -> None:
        queue = self._queue_with_events([
            {"event": "transaction", "data": {"trans_id": "TX-1", "risk_score": 0.91}},
        ])

        class FakeRequest:
            def __init__(self) -> None:
                self.calls = 0

            async def is_disconnected(self) -> bool:
                self.calls += 1
                return self.calls > 1

        async def run_test() -> str:
            with patch.object(transaction_streamer, "subscribe", return_value=queue), patch.object(transaction_streamer, "unsubscribe"):
                response = await transaction_streamer.transactions_realtime(FakeRequest())
                chunks = []
                async for chunk in response.body_iterator:
                    if isinstance(chunk, bytes):
                        chunks.append(chunk.decode("utf-8"))
                    else:
                        chunks.append(str(chunk))
                return "".join(chunks)

        body = asyncio.run(run_test())

        self.assertIn("event: transaction", body)
        self.assertIn("TX-1", body)

    def test_alert_stream_filters_non_alert_events(self) -> None:
        queue = self._queue_with_events([
            {"event": "transaction", "data": {"trans_id": "TX-IGNORE"}},
            {"event": "alert", "data": {"alert_id": "AL-1"}},
        ])

        class FakeRequest:
            def __init__(self) -> None:
                self.calls = 0

            async def is_disconnected(self) -> bool:
                self.calls += 1
                return self.calls > 2

        async def run_test() -> str:
            with patch.object(alerts_streamer, "subscribe", return_value=queue), patch.object(alerts_streamer, "unsubscribe"):
                response = await alerts_streamer.alerts_realtime(FakeRequest())
                chunks = []
                async for chunk in response.body_iterator:
                    if isinstance(chunk, bytes):
                        chunks.append(chunk.decode("utf-8"))
                    else:
                        chunks.append(str(chunk))
                return "".join(chunks)

        body = asyncio.run(run_test())

        self.assertNotIn("TX-IGNORE", body)
        self.assertIn("event: alert", body)
        self.assertIn("AL-1", body)


if __name__ == "__main__":
    unittest.main()
