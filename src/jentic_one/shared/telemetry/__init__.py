"""Product-telemetry package — anonymous activation/usage/health signals.

This package owns the *client* side of issue #446: an opaque per-instance id, a
fixed code-defined allowlist of event names, an in-memory queue + drained flush
loop, and a dedicated HTTP client that POSTs to the Jentic ingest endpoint.

Everything here no-ops unless ``config.telemetry.enabled`` is True. Events reach
the sink **only** through ``shared.events.emit_event`` (the single entry point);
services never touch the sink directly.
"""
