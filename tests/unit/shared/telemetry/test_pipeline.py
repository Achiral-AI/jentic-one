"""End-to-end telemetry pipeline test — real sink + real flush loop + real client.

Every other telemetry unit test stops at a boundary (the sink, the loop, or the
client in isolation). This one composes the real ``TelemetrySink``,
``TelemetryFlushLoop``, and ``TelemetryClient`` over an ``httpx.MockTransport`` so
the whole ``record() → drain() → send() → POST`` chain is exercised together and
the captured request body is asserted against the canonical wire contract
``{id, version, event, tags?, ts}``. No network, no DB — it picks up where
``test_emit_tags.py`` (emit → sink) leaves off.
"""

from __future__ import annotations

import json

import httpx
import pytest

from jentic_one.shared.models.events import ErrorSource
from jentic_one.shared.telemetry.client import TelemetryClient
from jentic_one.shared.telemetry.events import TelemetryEventName
from jentic_one.shared.telemetry.loop import TelemetryFlushLoop
from jentic_one.shared.telemetry.sink import TelemetrySink


def _client(transport: httpx.MockTransport) -> TelemetryClient:
    client = TelemetryClient(
        endpoint="https://api.jentic.com",
        instance_id="inst-123",
        version="1.4.2",
        request_timeout_s=5.0,
    )
    client._client = httpx.AsyncClient(transport=transport)
    return client


@pytest.mark.asyncio
async def test_record_to_post_round_trip() -> None:
    """A tagged and an untagged event flow sink → loop → client → POST intact."""
    captured: list[dict[str, object]] = []

    def handle(req: httpx.Request) -> httpx.Response:
        captured.append(json.loads(req.content))
        return httpx.Response(201)

    sink = TelemetrySink(enabled=True, queue_max=100)
    client = _client(httpx.MockTransport(handle))
    loop = TelemetryFlushLoop(sink, client, flush_interval_s=60.0, max_batch=10)

    sink.record(
        TelemetryEventName.CREDENTIAL_REFRESH_FAILED,
        [ErrorSource.AUTH_THIRDPARTY_UNAUTHORIZED],
        "agent",
    )
    sink.record(TelemetryEventName.INSTANCE_BOOTED)

    await loop.drain()
    await client.aclose()

    assert len(captured) == 2

    tagged, untagged = captured
    assert set(tagged) == {"id", "version", "event", "actor_type", "tags", "ts"}
    assert tagged["id"] == "inst-123"
    assert tagged["version"] == "1.4.2"
    assert tagged["event"] == "credential_refresh_failed"
    assert tagged["tags"] == ["auth_thirdparty_unauthorized"]
    assert tagged["actor_type"] == "agent"

    # The untagged event omits ``tags`` and ``actor_type`` entirely — never null/empty-list.
    assert set(untagged) == {"id", "version", "event", "ts"}
    assert untagged["event"] == "instance_booted"


@pytest.mark.asyncio
async def test_disabled_sink_posts_nothing() -> None:
    """A disabled sink is the consent gate — nothing reaches the wire end-to-end."""
    captured: list[dict[str, object]] = []

    def handle(req: httpx.Request) -> httpx.Response:
        captured.append(json.loads(req.content))
        return httpx.Response(201)

    sink = TelemetrySink(enabled=False, queue_max=100)
    client = _client(httpx.MockTransport(handle))
    loop = TelemetryFlushLoop(sink, client, flush_interval_s=60.0, max_batch=10)

    sink.record(TelemetryEventName.BROKER_EXECUTION)

    await loop.drain()
    await client.aclose()

    assert captured == []


@pytest.mark.asyncio
async def test_send_failure_does_not_break_drain() -> None:
    """A rejecting endpoint is swallowed — drain still empties the queue."""

    def handle(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    sink = TelemetrySink(enabled=True, queue_max=100)
    client = _client(httpx.MockTransport(handle))
    loop = TelemetryFlushLoop(sink, client, flush_interval_s=60.0, max_batch=10)

    sink.record(TelemetryEventName.BROKER_EXECUTION)
    sink.record(TelemetryEventName.BROKER_EXECUTION)

    # Must not raise despite the 500s; queue is drained regardless.
    await loop.drain()
    await client.aclose()

    assert sink.queue.qsize() == 0
