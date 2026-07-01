"""Enforce that telemetry is NEVER sent unless the user has explicitly opted in.

Telemetry is opt-out-by-default: a single ``telemetry.enabled: true`` is the only
thing that may switch network emission on. These tests guard that invariant
*structurally* (so a future refactor can't silently bypass it) rather than just
behaviourally:

1. The only thing that performs network I/O is ``TelemetryClient.send``, driven by
   ``TelemetryFlushLoop`` off the active ``TelemetrySink``. All three are wired up
   in exactly one place — ``shared/web/app_factory.py`` — and ``set_active_sink``
   (the switch that makes ``_forward_to_telemetry`` start recording) is called
   nowhere else. No other module may construct the client/loop or activate a sink.
2. That single wiring site sits behind the consent gate: ``_start_telemetry``
   returns early when ``telemetry.enabled`` is false, so the client/loop/sink are
   never even created when the operator hasn't opted in.
3. The per-emit fast path ``_forward_to_telemetry`` checks ``sink.enabled`` before
   it ever calls ``sink.record`` — a second, independent gate.

Behavioural coverage (disabled sink posts nothing, etc.) lives in
``tests/unit/shared/telemetry/test_pipeline.py``; this file protects the shape.
"""

from __future__ import annotations

import ast

import pytest

from tests.arch.conftest import SRC_ROOT, python_files_in

APP_FACTORY = SRC_ROOT / "shared" / "web" / "app_factory.py"
EVENTS_INIT = SRC_ROOT / "shared" / "events" / "__init__.py"
SINK_MODULE = SRC_ROOT / "shared" / "telemetry" / "sink.py"

# Calls that can activate telemetry or build the thing that talks to the network.
# These must only ever appear inside the single sanctioned wiring site.
WIRING_CALLS = {"set_active_sink", "TelemetryClient", "TelemetryFlushLoop"}


def _call_names(tree: ast.AST) -> list[str]:
    """Return the bare callee name of every call in *tree* (``Foo()`` -> ``Foo``)."""
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                names.append(func.id)
            elif isinstance(func, ast.Attribute):
                names.append(func.attr)
    return names


def _function_def(tree: ast.AST, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == name:
            return node
    return None


@pytest.mark.arch
def test_telemetry_wiring_confined_to_app_factory():
    """Only app_factory.py may activate a sink or construct the telemetry client/loop.

    ``set_active_sink`` is the switch that turns ``_forward_to_telemetry`` from a
    no-op into a recorder, and ``TelemetryClient``/``TelemetryFlushLoop`` are the
    only things that perform/drive network sends. Confining all three to the single
    consent-gated wiring site means no other code path can start sending telemetry.
    """
    violations: list[tuple[str, list[str]]] = []
    for path in python_files_in(SRC_ROOT):
        if path in (APP_FACTORY, SINK_MODULE):
            # app_factory: the sanctioned wiring site (behind the consent gate).
            # sink.py: *defines* set_active_sink; defining is not activating.
            continue
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            continue
        found = sorted({name for name in _call_names(tree) if name in WIRING_CALLS})
        if found:
            violations.append((str(path.relative_to(SRC_ROOT)), found))

    assert not violations, (
        "Telemetry sink/client/loop wiring must live ONLY in shared/web/app_factory.py "
        "(behind the telemetry.enabled consent gate). Found wiring calls elsewhere:\n"
        + "\n".join(f"  {f}: {calls}" for f, calls in violations)
    )


@pytest.mark.arch
def test_start_telemetry_is_gated_on_enabled():
    """``_start_telemetry`` must short-circuit when telemetry is not enabled.

    The sink/loop/client are created *after* this gate, so an early ``return`` on
    ``not ...enabled`` guarantees nothing telemetry-related is constructed unless
    the operator opted in.
    """
    tree = ast.parse(APP_FACTORY.read_text())
    func = _function_def(tree, "_start_telemetry")
    assert func is not None, "_start_telemetry not found in app_factory.py"

    # Find an early `return` guarded by a `not ...enabled` test, appearing before
    # any of the wiring calls in the function body.
    enabled_guard_line: int | None = None
    for node in ast.walk(func):
        if not isinstance(node, ast.If):
            continue
        test_src = ast.dump(node.test)
        if "enabled" in test_src and "Not" in test_src:
            for stmt in node.body:
                if isinstance(stmt, ast.Return):
                    enabled_guard_line = node.lineno
                    break
    assert enabled_guard_line is not None, (
        "_start_telemetry must early-return on `not <config>.enabled` (the consent "
        "gate) before wiring the sink/loop/client."
    )

    first_wiring_line = min(
        (
            node.lineno
            for node in ast.walk(func)
            if isinstance(node, ast.Call)
            and (
                (isinstance(node.func, ast.Name) and node.func.id in WIRING_CALLS)
                or (isinstance(node.func, ast.Attribute) and node.func.attr in WIRING_CALLS)
            )
        ),
        default=None,
    )
    assert first_wiring_line is not None, "expected telemetry wiring inside _start_telemetry"
    assert enabled_guard_line < first_wiring_line, (
        "the telemetry.enabled gate must come BEFORE any sink/client/loop wiring "
        "in _start_telemetry."
    )


@pytest.mark.arch
def test_forward_to_telemetry_checks_enabled_before_record():
    """``_forward_to_telemetry`` must consult ``sink.enabled`` before ``sink.record``.

    This is the second, independent gate on the hot path: even with an active sink,
    a disabled one must record nothing.
    """
    tree = ast.parse(EVENTS_INIT.read_text())
    func = _function_def(tree, "_forward_to_telemetry")
    assert func is not None, "_forward_to_telemetry not found in shared/events/__init__.py"

    enabled_line: int | None = None
    record_line: int | None = None
    for node in ast.walk(func):
        if isinstance(node, ast.Attribute) and node.attr == "enabled" and enabled_line is None:
            enabled_line = node.lineno
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "record"
        ):
            record_line = node.lineno

    assert enabled_line is not None, "_forward_to_telemetry must check `sink.enabled`."
    assert record_line is not None, "_forward_to_telemetry must call `sink.record(...)`."
    assert enabled_line < record_line, (
        "_forward_to_telemetry must check `sink.enabled` BEFORE calling `sink.record` "
        "— the consent gate has to come first."
    )
