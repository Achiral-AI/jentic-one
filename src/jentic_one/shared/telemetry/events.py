"""Telemetry event names — the canonical, code-defined allowlist.

``TelemetryEventName`` is the **only** set of events an opted-in instance may
send to Jentic. It is fixed in code (never config- or DB-tunable): consent is
all-or-nothing, so the ingest side always knows the full event vocabulary and
funnels are never silently skewed by suppressed events.

``TELEMETRY_EVENTS`` maps the internal ``EventType`` taxonomy to the wire name.
An ``EventType`` absent from this map is internal-only and never forwarded —
``emit_event`` consults this map to decide what (if anything) to hand the sink.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from jentic_one.shared.models.actors import ActorType
from jentic_one.shared.models.events import EventTag, EventType


class TelemetryEventName(StrEnum):
    """Every event name the client may put on the wire (the allowlist)."""

    # Lifecycle / liveness
    INSTANCE_INITIALIZED = "instance_initialized"
    INSTANCE_BOOTED = "instance_booted"
    # Setup / activation funnel
    SPEC_IMPORTED = "spec_imported"
    CREDENTIAL_STORED = "credential_stored"
    CREDENTIAL_CONNECTED = "credential_connected"
    TOOLKIT_CREATED = "toolkit_created"
    TOOLKIT_KEY_CREATED = "toolkit_key_created"
    TOOLKIT_PERMISSION_RULE_SET = "toolkit_permission_rule_set"
    CREDENTIAL_BOUND_TO_TOOLKIT = "credential_bound_to_toolkit"
    CREDENTIAL_UNBOUND_FROM_TOOLKIT = "credential_unbound_from_toolkit"
    AGENT_CREATED = "agent_created"
    AGENT_SELF_REGISTERED = "agent_self_registered"
    AGENT_REGISTRATION_APPROVED = "agent_registration_approved"
    AGENT_REGISTRATION_DENIED = "agent_registration_denied"
    TOOLKIT_BOUND_TO_AGENT = "toolkit_bound_to_agent"
    TOOLKIT_UNBOUND_FROM_AGENT = "toolkit_unbound_from_agent"
    # Access-request flow
    ACCESS_REQUEST_FILED = "access_request_filed"
    ACCESS_REQUEST_APPROVED = "access_request_approved"
    ACCESS_REQUEST_DENIED = "access_request_denied"
    # Usage / activation moment
    BROKER_EXECUTION = "broker_execution"
    # Health / friction
    PBAC_DENIED = "pbac_denied"
    BROKER_EXECUTION_FAILED = "broker_execution_failed"
    CREDENTIAL_NOT_PROVISIONED = "credential_not_provisioned"
    SPEC_IMPORT_FAILED = "spec_import_failed"
    CREDENTIAL_CONNECTION_FAILED = "credential_connection_failed"
    CREDENTIAL_REFRESH_FAILED = "credential_refresh_failed"


#: Allowlist: internal ``EventType`` → wire ``TelemetryEventName``. Only events
#: present here are forwarded to Jentic (when telemetry is enabled). ``emit_event``
#: looks the event up here; a miss means "internal-only, do not forward".
TELEMETRY_EVENTS: dict[str, TelemetryEventName] = {
    EventType.INSTANCE_INITIALIZED: TelemetryEventName.INSTANCE_INITIALIZED,
    EventType.INSTANCE_BOOTED: TelemetryEventName.INSTANCE_BOOTED,
    EventType.IMPORT_COMPLETED: TelemetryEventName.SPEC_IMPORTED,
    EventType.IMPORT_FAILED: TelemetryEventName.SPEC_IMPORT_FAILED,
    EventType.CREDENTIAL_STORED: TelemetryEventName.CREDENTIAL_STORED,
    EventType.CREDENTIAL_CONNECTED: TelemetryEventName.CREDENTIAL_CONNECTED,
    EventType.CREDENTIAL_CONNECTION_FAILED: TelemetryEventName.CREDENTIAL_CONNECTION_FAILED,
    EventType.CREDENTIAL_REFRESH_FAILED: TelemetryEventName.CREDENTIAL_REFRESH_FAILED,
    EventType.CREDENTIAL_NOT_PROVISIONED: TelemetryEventName.CREDENTIAL_NOT_PROVISIONED,
    EventType.CREDENTIAL_BOUND_TO_TOOLKIT: TelemetryEventName.CREDENTIAL_BOUND_TO_TOOLKIT,
    EventType.CREDENTIAL_UNBOUND_FROM_TOOLKIT: TelemetryEventName.CREDENTIAL_UNBOUND_FROM_TOOLKIT,
    EventType.TOOLKIT_CREATED: TelemetryEventName.TOOLKIT_CREATED,
    EventType.TOOLKIT_KEY_CREATED: TelemetryEventName.TOOLKIT_KEY_CREATED,
    EventType.TOOLKIT_PERMISSION_RULE_SET: TelemetryEventName.TOOLKIT_PERMISSION_RULE_SET,
    EventType.TOOLKIT_BOUND_TO_AGENT: TelemetryEventName.TOOLKIT_BOUND_TO_AGENT,
    EventType.TOOLKIT_UNBOUND_FROM_AGENT: TelemetryEventName.TOOLKIT_UNBOUND_FROM_AGENT,
    EventType.AGENT_CREATED: TelemetryEventName.AGENT_CREATED,
    EventType.AGENT_SELF_REGISTERED: TelemetryEventName.AGENT_SELF_REGISTERED,
    EventType.AGENT_REGISTRATION_APPROVED: TelemetryEventName.AGENT_REGISTRATION_APPROVED,
    EventType.AGENT_REGISTRATION_DENIED: TelemetryEventName.AGENT_REGISTRATION_DENIED,
    EventType.ACCESS_REQUEST_FILED: TelemetryEventName.ACCESS_REQUEST_FILED,
    EventType.ACCESS_REQUEST_APPROVED: TelemetryEventName.ACCESS_REQUEST_APPROVED,
    EventType.ACCESS_REQUEST_DENIED: TelemetryEventName.ACCESS_REQUEST_DENIED,
    EventType.EXECUTION_COMPLETED: TelemetryEventName.BROKER_EXECUTION,
    EventType.EXECUTION_FAILED: TelemetryEventName.BROKER_EXECUTION_FAILED,
    EventType.PBAC_DENIED: TelemetryEventName.PBAC_DENIED,
}


@dataclass(frozen=True, slots=True)
class TelemetryEvent:
    """A single queued telemetry event.

    Carries **only** the wire name, the validated closed-enum tags, the actor
    type, and a record timestamp — there is deliberately nowhere to put
    free-form props, URLs, identities, or secrets. The opaque instance id and
    app version are stamped on at flush time (request-level fields), not per
    event.

    ``actor_type`` is typed as the closed ``ActorType`` enum (never a free-form
    ``str``): the sink coerces the caller's value at record time and drops
    anything that is not an enum member, so a raw label/email can never reach
    the wire. This makes the "PII is structurally impossible" guarantee real for
    ``actor_type`` rather than by-convention.
    """

    name: TelemetryEventName
    tags: tuple[EventTag, ...]
    ts: datetime
    actor_type: ActorType | None = None
