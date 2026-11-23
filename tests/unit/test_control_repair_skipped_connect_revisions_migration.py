"""Repair of the connect revisions a fork re-parent let an upgraded database skip.

The fork's ``f54cbd91b63f`` first revised ``dd4e5f6a7b8c``. Merging upstream
re-parented it onto upstream's new ``e9f0a1b2c3d4``, so a database already
stamped at ``f54cbd91b63f`` reported head and never ran ``dc9d3cd8f0b7``,
``d9305dcd765e`` or ``e9f0a1b2c3d4``. These tests rebuild that state on SQLite.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from jentic_one.migrations.run import downgrade, upgrade

_DB = "control"
_STAMP = "f54cbd91b63f"  # pragma: allowlist secret

_SKIPPED_COLUMNS = {
    "connect_sessions": ("intent", "baseline", "current_revision_id", "approved_change"),
    "connect_state_nonces": ("completed_at",),
    "device_authorization_credentials": ("flow_nonce",),
}


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f'PRAGMA table_info("{table}")').fetchall()}


def _tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {row[0] for row in rows}


_REPAIR = "9f110b37d4c9"  # pragma: allowlist secret

_CONNECT_REVISIONS_COLUMNS = {
    table: columns for table, columns in _SKIPPED_COLUMNS.items() if table == "connect_sessions"
}
_FLOW_COMPLETION_COLUMNS = {
    table: columns for table, columns in _SKIPPED_COLUMNS.items() if table != "connect_sessions"
}


def _rebuild_skipped_state(
    db_path: Path,
    *,
    drop_revisions: bool = True,
    drop_flow_completion: bool = True,
) -> None:
    dropped: dict[str, tuple[str, ...]] = {}
    with sqlite3.connect(db_path) as conn:
        if drop_revisions:
            conn.execute("DROP TABLE connect_session_revisions")
            dropped |= _CONNECT_REVISIONS_COLUMNS
        if drop_flow_completion:
            dropped |= _FLOW_COMPLETION_COLUMNS
        for table, columns in dropped.items():
            for column in columns:
                conn.execute(f'ALTER TABLE "{table}" DROP COLUMN "{column}"')
        conn.execute("UPDATE alembic_version SET version_num = ?", (_STAMP,))


def _version(db_path: Path) -> str:
    with sqlite3.connect(db_path) as conn:
        return str(conn.execute("SELECT version_num FROM alembic_version").fetchone()[0])


def _assert_skipped_schema_present(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        assert "connect_session_revisions" in _tables(conn)
        for table, columns in _SKIPPED_COLUMNS.items():
            assert set(columns) <= _columns(conn, table), table


def test_upgrade_applies_revisions_skipped_by_the_reparent(sqlite_stack: Path) -> None:
    db_path = sqlite_stack / f"{_DB}.db"
    upgrade(_DB)
    _rebuild_skipped_state(db_path)

    upgrade(_DB)

    _assert_skipped_schema_present(db_path)
    assert _version(db_path) == _REPAIR


@pytest.mark.parametrize(
    ("drop_revisions", "drop_flow_completion"),
    [(True, False), (False, True)],
    ids=["only-connect-revisions-missing", "only-flow-completion-missing"],
)
def test_upgrade_applies_only_the_missing_revision(
    sqlite_stack: Path, *, drop_revisions: bool, drop_flow_completion: bool
) -> None:
    db_path = sqlite_stack / f"{_DB}.db"
    upgrade(_DB)
    _rebuild_skipped_state(
        db_path, drop_revisions=drop_revisions, drop_flow_completion=drop_flow_completion
    )

    upgrade(_DB)

    _assert_skipped_schema_present(db_path)
    assert _version(db_path) == _REPAIR


def test_upgrade_on_a_linear_install_leaves_the_schema_alone(sqlite_stack: Path) -> None:
    db_path = sqlite_stack / f"{_DB}.db"
    upgrade(_DB, _STAMP)

    upgrade(_DB)

    _assert_skipped_schema_present(db_path)


def test_downgrade_to_the_stamp_keeps_the_repaired_schema(sqlite_stack: Path) -> None:
    db_path = sqlite_stack / f"{_DB}.db"
    upgrade(_DB)
    _rebuild_skipped_state(db_path)
    upgrade(_DB)

    downgrade(_DB, _STAMP)

    _assert_skipped_schema_present(db_path)
