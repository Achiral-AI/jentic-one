"""Enforce that the telemetry instance id is durable — never regenerated/overwritten.

The opaque instance id is a *stable correlation key*: it must survive restarts,
deploys, and version upgrades so the ingest side can group one deployment's events
into a single funnel/cohort for its whole lifetime. A value that changed on boot
would make every restart look like a brand-new instance and corrupt all
"first-ness"/activation derivations downstream.

That stability rests on the durable admin-DB ``instance_identities`` row being
touched in exactly ONE place — ``shared/telemetry/instance_id.py`` — which only
ever reads it on subsequent boots (the single sanctioned mutation is an explicit
operator change to ``config.instance_id``). This test guards the invariant
structurally: no other module may reference the ``InstanceIdentity`` ORM model,
so nothing can insert/update/delete (i.e. regenerate or clobber) the identity row
behind the resolver's back.
"""

from __future__ import annotations

import ast

import pytest

from tests.arch.conftest import SRC_ROOT, python_files_in

MODEL_NAME = "InstanceIdentity"

# Files allowed to reference the InstanceIdentity model:
#   - the resolver: the ONLY place that may persist/read the identity row
#   - the schema module: defines the model
#   - the admin schema barrel: re-exports it for ORM registration
RESOLVER = SRC_ROOT / "shared" / "telemetry" / "instance_id.py"
SCHEMA = SRC_ROOT / "admin" / "core" / "schema" / "instance_identity.py"
SCHEMA_BARREL = SRC_ROOT / "admin" / "core" / "schema" / "__init__.py"
EXEMPT = {RESOLVER, SCHEMA, SCHEMA_BARREL}


def _references_model(tree: ast.AST) -> bool:
    """True if the tree names ``InstanceIdentity`` anywhere (import or use)."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == MODEL_NAME:
            return True
        if isinstance(node, ast.Attribute) and node.attr == MODEL_NAME:
            return True
        if isinstance(node, ast.ImportFrom) and any(
            alias.name == MODEL_NAME for alias in node.names
        ):
            return True
    return False


@pytest.mark.arch
def test_instance_identity_model_confined_to_resolver():
    """Only the resolver (+ schema/barrel) may touch the InstanceIdentity row.

    Confining all reads/writes of the identity row to ``instance_id.py`` is what
    guarantees the instance id is never regenerated or overwritten elsewhere, so it
    stays stable across restarts/deploys/upgrades.
    """
    offenders: list[str] = []
    for path in python_files_in(SRC_ROOT):
        if path in EXEMPT:
            continue
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            continue
        if _references_model(tree):
            offenders.append(str(path.relative_to(SRC_ROOT)))

    assert not offenders, (
        "The InstanceIdentity row must only be persisted/read by "
        "shared/telemetry/instance_id.py (to keep the telemetry instance id stable "
        "across restarts). These modules reference the model:\n"
        + "\n".join(f"  {o}" for o in offenders)
    )


@pytest.mark.arch
def test_resolver_never_deletes_the_identity_row():
    """``instance_id.py`` must not delete/truncate the identity row.

    A delete would orphan the durable id and let the next boot mint a fresh one,
    breaking stability. The resolver only inserts-if-absent, reads, or reconciles.
    """
    tree = ast.parse(RESOLVER.read_text())
    called = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    forbidden = called & {"delete", "execute"}  # `execute` would allow raw DELETE/UPDATE
    assert not forbidden, (
        "shared/telemetry/instance_id.py must not delete the identity row or run raw "
        f"DML against it (found calls: {sorted(forbidden)}); the instance id must persist."
    )
