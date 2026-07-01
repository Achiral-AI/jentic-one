"""Unit tests for the telemetry flush loop — batching + graceful drain."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from jentic_one.shared.telemetry.events import TelemetryEvent, TelemetryEventName
from jentic_one.shared.telemetry.loop import TelemetryFlushLoop
from jentic_one.shared.telemetry.sink import TelemetrySink


class _RecordingClient:
    def __init__(self) -> None:
        self.batches: list[list[TelemetryEvent]] = []

    async def send(self, events: list[TelemetryEvent]) -> None:
        self.batches.append(list(events))

    async def aclose(self) -> None:
        pass


def _event() -> TelemetryEvent:
    return TelemetryEvent(
        name=TelemetryEventName.BROKER_EXECUTION,
        tags=(),
        ts=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_drain_flushes_queued_events_in_batches() -> None:
    """drain() empties the queue, sending at most max_batch per call."""
    sink = TelemetrySink(enabled=True, queue_max=100)
    client = _RecordingClient()
    loop = TelemetryFlushLoop(
        sink,
        client,  # type: ignore[arg-type]
        flush_interval_s=60.0,
        max_batch=2,
    )

    for _ in range(5):
        sink.record(TelemetryEventName.BROKER_EXECUTION)

    await loop.drain()

    # 5 events, batched by 2 → 2 + 2 + 1.
    assert [len(b) for b in client.batches] == [2, 2, 1]
    assert sink.queue.qsize() == 0


@pytest.mark.asyncio
async def test_drain_on_empty_queue_sends_nothing() -> None:
    """Draining an empty queue is a no-op (no empty batches sent)."""
    sink = TelemetrySink(enabled=True, queue_max=10)
    client = _RecordingClient()
    loop = TelemetryFlushLoop(
        sink,
        client,  # type: ignore[arg-type]
        flush_interval_s=60.0,
        max_batch=10,
    )

    await loop.drain()

    assert client.batches == []
