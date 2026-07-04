"""Unit tests for the telemetry sink: consent gate + non-blocking drop-on-full."""

from __future__ import annotations

from jentic_one.shared.telemetry.events import TelemetryEventName
from jentic_one.shared.telemetry.sink import TelemetrySink


def test_disabled_sink_records_nothing() -> None:
    """The consent gate: a disabled sink is a no-op (queue stays empty)."""
    sink = TelemetrySink(enabled=False, queue_max=10)

    for _ in range(5):
        sink.record(TelemetryEventName.INSTANCE_BOOTED)

    assert sink.queue.qsize() == 0
    assert sink.dropped == 0


def test_enabled_sink_enqueues() -> None:
    """An enabled sink enqueues each recorded event."""
    sink = TelemetrySink(enabled=True, queue_max=10)

    sink.record(TelemetryEventName.CREDENTIAL_STORED)
    sink.record(TelemetryEventName.BROKER_EXECUTION)

    assert sink.queue.qsize() == 2


def test_full_queue_drops_without_raising() -> None:
    """When the queue is full, record drops the event and never raises/blocks."""
    sink = TelemetrySink(enabled=True, queue_max=2)

    sink.record(TelemetryEventName.BROKER_EXECUTION)
    sink.record(TelemetryEventName.BROKER_EXECUTION)
    # Third record exceeds capacity — must drop silently.
    sink.record(TelemetryEventName.BROKER_EXECUTION)

    assert sink.queue.qsize() == 2
    assert sink.dropped == 1
