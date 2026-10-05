"""Unit tests for POST /agents (manual agent creation)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from jentic_one.auth.services.agent_service import AgentService
from jentic_one.auth.services.errors import AuthServiceError
from jentic_one.auth.services.schemas.agents import AgentView
from jentic_one.auth.web.deps import get_agent_service
from jentic_one.auth.web.errors import service_error_handler
from jentic_one.auth.web.routers import agents
from jentic_one.shared.auth.identity import Identity
from jentic_one.shared.models import ActorType
from jentic_one.shared.web.deps import resolve_identity


def _admin_identity() -> Identity:
    return Identity(
        sub="usr_admin",
        email="admin@example.com",
        permissions=["agents:write", "agents:read", "org:admin"],
    )


def _readonly_identity() -> Identity:
    return Identity(
        sub="usr_reader",
        email="reader@example.com",
        permissions=["agents:read"],
    )


def _agent_view() -> AgentView:
    return AgentView(
        id="agnt_new123",
        name="my-bot",
        description="A test bot",
        owner_id="usr_admin",
        registered_by="usr_admin",
        parent_agent_id=None,
        approved_by=None,
        status="active",
        denial_reason=None,
        denied_by=None,
        created_at=datetime(2026, 6, 23, tzinfo=UTC),
        approved_at=None,
    )


@pytest.fixture()
def mock_agent_svc() -> MagicMock:
    svc = MagicMock(spec=AgentService)
    svc.create = AsyncMock(return_value=_agent_view())
    return svc


@pytest.fixture()
def client(mock_agent_svc: MagicMock) -> TestClient:
    app = FastAPI()
    app.include_router(agents.router)
    app.add_exception_handler(AuthServiceError, service_error_handler)
    app.dependency_overrides[resolve_identity] = _admin_identity
    app.dependency_overrides[get_agent_service] = lambda: mock_agent_svc

    mock_ctx = MagicMock()
    app.state.ctx = mock_ctx
    return TestClient(app)


@pytest.fixture()
def readonly_client(mock_agent_svc: MagicMock) -> TestClient:
    app = FastAPI()
    app.include_router(agents.router)
    app.add_exception_handler(AuthServiceError, service_error_handler)
    app.dependency_overrides[resolve_identity] = _readonly_identity
    app.dependency_overrides[get_agent_service] = lambda: mock_agent_svc

    mock_ctx = MagicMock()
    app.state.ctx = mock_ctx
    return TestClient(app)


def test_create_agent_201(client: TestClient) -> None:
    resp = client.post("/agents", json={"name": "my-bot", "description": "A test bot"})

    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] == "agnt_new123"
    assert data["name"] == "my-bot"
    assert data["status"] == "active"


def test_create_agent_validates_empty_name(client: TestClient) -> None:
    resp = client.post("/agents", json={"name": ""})
    assert resp.status_code == 422


def test_create_agent_requires_agents_write(readonly_client: TestClient) -> None:
    resp = readonly_client.post("/agents", json={"name": "my-bot"})
    assert resp.status_code == 403


def test_create_agent_description_optional(client: TestClient) -> None:
    resp = client.post("/agents", json={"name": "minimal-bot"})
    assert resp.status_code == 201


def _agent_identity() -> Identity:
    return Identity(
        sub="agnt_control",
        permissions=["agents:write", "agents:read", "org:admin"],
        actor_type=ActorType.AGENT,
        parent_actor_id="usr_owner",
    )


def test_agent_created_by_an_agent_is_owned_by_its_owner(mock_agent_svc: MagicMock) -> None:
    # agents.owner_id references users, so an agent caller cannot own the new
    # agent; its owner does, and the caller is recorded as the parent agent.
    app = FastAPI()
    app.include_router(agents.router)
    app.add_exception_handler(AuthServiceError, service_error_handler)
    app.dependency_overrides[resolve_identity] = _agent_identity
    app.dependency_overrides[get_agent_service] = lambda: mock_agent_svc
    app.state.ctx = MagicMock()

    resp = TestClient(app).post("/agents", json={"name": "sub-bot"})

    assert resp.status_code == 201
    kwargs = mock_agent_svc.create.await_args.kwargs
    assert kwargs["owner_id"] == "usr_owner"
    assert kwargs["parent_agent_id"] == "agnt_control"


def test_agent_created_by_a_user_has_no_parent_agent(
    client: TestClient, mock_agent_svc: MagicMock
) -> None:
    client.post("/agents", json={"name": "my-bot"})

    kwargs = mock_agent_svc.create.await_args.kwargs
    assert kwargs["owner_id"] == "usr_admin"
    assert kwargs["parent_agent_id"] is None
