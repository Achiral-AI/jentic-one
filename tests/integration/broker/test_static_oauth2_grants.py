"""Static oauth2 credentials whose tokens Jentic One gets itself.

Two grants with the customer's own OAuth client and no browser sign-in:

- ``client_credentials`` (Marketo): the broker mints an access token at the
  token endpoint on first use and again once it expires.
- ``refresh_token`` (Workday): the caller seeds a refresh token; the broker
  exchanges it for access tokens, stores a rotated refresh token, and answers
  ``credential_needs_reconnect`` when the vendor rejects the grant.

Real control DB and encryption; only the vendor's token endpoint is faked,
behind httpx's mock transport, so the request the provider builds (URL, body
encoding, client authentication) is what the assertions see.
"""

from __future__ import annotations

import base64
import json
from collections.abc import AsyncGenerator, Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs

import httpx
import pytest
from sqlalchemy import delete, update

from jentic_one.broker.core.exceptions import CredentialNeedsReconnectError
from jentic_one.broker.services.credentials.orchestrator import CredentialService
from jentic_one.control.core.schema.credentials import Credential
from jentic_one.control.core.schema.oauth_client_credentials import OAuthClientCredential
from jentic_one.control.core.schema.oauth_tokens import OAuthToken
from jentic_one.control.repos import OAuthTokenRepository
from jentic_one.control.services.credentials.schemas.credentials import CredentialCreate
from jentic_one.control.services.credentials.schemas.oauth_client_options import (
    OAuthClientOptions,
)
from jentic_one.control.services.credentials.schemas.provision import APIReference
from jentic_one.control.services.credentials.service import (
    CredentialService as ControlCredentialService,
)
from jentic_one.shared.auth.identity import Identity
from jentic_one.shared.context import Context
from jentic_one.shared.db.session import DatabaseSession
from jentic_one.shared.models import ActorType
from jentic_one.shared.models.credentials import CredentialType

pytestmark = pytest.mark.integration

_OWNER = Identity(sub="usr_grants", permissions=["credentials:write"])
_AGENT = Identity(
    sub="agent_grants", actor_type=ActorType.AGENT, permissions=["execute"], active=True
)


class _TokenEndpoint:
    """A vendor token endpoint that records each request and answers from a script."""

    def __init__(self, respond: Callable[[httpx.Request], httpx.Response]) -> None:
        self.requests: list[httpx.Request] = []
        self._respond = respond

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self._respond(request)

    def form(self, index: int) -> dict[str, str]:
        parsed = parse_qs(self.requests[index].content.decode())
        return {key: values[0] for key, values in parsed.items()}


@pytest.fixture()
async def clean_oauth(control_db: DatabaseSession) -> AsyncGenerator[None, None]:
    async def _truncate() -> None:
        async with control_db.session() as session:
            await session.execute(delete(OAuthToken))
            await session.execute(delete(OAuthClientCredential))
            await session.execute(delete(Credential))
            await session.commit()

    await _truncate()
    yield
    await _truncate()


def _install(monkeypatch: pytest.MonkeyPatch, endpoint: _TokenEndpoint) -> None:
    real_client = httpx.AsyncClient

    def _client(**kwargs: Any) -> httpx.AsyncClient:
        kwargs.pop("transport", None)
        return real_client(transport=httpx.MockTransport(endpoint.handle), **kwargs)

    monkeypatch.setattr(
        "jentic_one.control.services.credentials.providers.oauth2.httpx.AsyncClient", _client
    )


async def _create(ctx: Context, vendor: str, **fields: Any) -> str:
    view = await ControlCredentialService(ctx).create(
        CredentialCreate(
            type=CredentialType.OAUTH2,
            name=f"{vendor}-cred",
            api=APIReference(vendor=vendor, name="", version=""),
            provider="static",
            **fields,
        ),
        identity=_OWNER,
    )
    return view.credential_id


async def _inject(ctx: Context, vendor: str) -> dict[str, str]:
    result = await CredentialService(ctx).inject(
        api_vendor=vendor, api_name="", api_version="", identity=_AGENT
    )
    return result.headers


async def _expire(ctx: Context, credential_id: str) -> None:
    async with ctx.control_db.transaction() as session:
        await session.execute(
            update(OAuthToken)
            .where(OAuthToken.credential_id == credential_id)
            .values(expires_at=datetime.now(UTC) - timedelta(minutes=1))
        )


async def _stored_refresh_token(ctx: Context, credential_id: str) -> str | None:
    async with ctx.control_db.session() as session:
        row = await OAuthTokenRepository.get_by_credential(session, credential_id)
    assert row is not None
    if row.encrypted_refresh_token is None:
        return None
    return ctx.encryption.decrypt(row.encrypted_refresh_token)


def _token(access: str, **extra: object) -> httpx.Response:
    return httpx.Response(200, json={"access_token": access, "expires_in": 3600, **extra})


async def test_client_credentials_mints_on_first_use_and_after_expiry(
    integration_context: Context, clean_oauth: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = integration_context
    issued = iter(["at-1", "at-2"])
    endpoint = _TokenEndpoint(lambda _: _token(next(issued)))
    _install(monkeypatch, endpoint)
    cred_id = await _create(
        ctx,
        "marketo",
        grant_type="client_credentials",
        token_url="https://{munchkin}.mktorest.com/identity/oauth/token",
        client_id="mkto-client",
        client_secret="mkto-secret",  # pragma: allowlist secret
        server_variables={"munchkin": "123-ABC-456"},
        client_options=OAuthClientOptions(token_auth_method="client_secret_post"),
    )

    assert await _inject(ctx, "marketo") == {"Authorization": "Bearer at-1"}
    assert await _inject(ctx, "marketo") == {"Authorization": "Bearer at-1"}

    assert len(endpoint.requests) == 1
    assert str(endpoint.requests[0].url) == (
        "https://123-abc-456.mktorest.com/identity/oauth/token"
    )
    assert endpoint.form(0) == {
        "grant_type": "client_credentials",
        "client_id": "mkto-client",
        "client_secret": "mkto-secret",  # pragma: allowlist secret
    }

    await _expire(ctx, cred_id)
    assert await _inject(ctx, "marketo") == {"Authorization": "Bearer at-2"}
    assert len(endpoint.requests) == 2


async def test_client_credentials_honours_basic_auth_json_and_scopes(
    integration_context: Context, clean_oauth: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = integration_context
    endpoint = _TokenEndpoint(lambda _: _token("at-json"))
    _install(monkeypatch, endpoint)
    await _create(
        ctx,
        "jsonvendor",
        grant_type="client_credentials",
        token_url="https://auth.jsonvendor.example/token",
        client_id="cid",
        client_secret="csecret",  # pragma: allowlist secret
        scopes=["read", "write"],
        client_options=OAuthClientOptions(
            token_auth_method="client_secret_basic", token_request_encoding="json"
        ),
    )

    assert await _inject(ctx, "jsonvendor") == {"Authorization": "Bearer at-json"}

    request = endpoint.requests[0]
    assert request.headers["Authorization"] == "Basic " + base64.b64encode(b"cid:csecret").decode()
    assert json.loads(request.content) == {
        "grant_type": "client_credentials",
        "scope": "read write",
    }


async def test_refresh_token_grant_exchanges_and_rotates_the_seeded_token(
    integration_context: Context, clean_oauth: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = integration_context
    responses = iter([_token("at-1", refresh_token="rt-2"), _token("at-2")])
    endpoint = _TokenEndpoint(lambda _: next(responses))
    _install(monkeypatch, endpoint)
    cred_id = await _create(
        ctx,
        "workday",
        grant_type="refresh_token",
        token_url="https://wd2-impl-services1.workday.com/ccx/oauth2/acme/token",
        client_id="wd-client",
        client_secret="wd-secret",  # pragma: allowlist secret
        refresh_token="rt-seed",  # pragma: allowlist secret
    )

    assert await _inject(ctx, "workday") == {"Authorization": "Bearer at-1"}
    assert endpoint.form(0) == {
        "grant_type": "refresh_token",
        "refresh_token": "rt-seed",  # pragma: allowlist secret
        "client_id": "wd-client",
        "client_secret": "wd-secret",  # pragma: allowlist secret
    }
    assert await _stored_refresh_token(ctx, cred_id) == "rt-2"

    assert await _inject(ctx, "workday") == {"Authorization": "Bearer at-1"}
    assert len(endpoint.requests) == 1

    await _expire(ctx, cred_id)
    assert await _inject(ctx, "workday") == {"Authorization": "Bearer at-2"}
    assert endpoint.form(1)["refresh_token"] == "rt-2"
    # No rotation in the second response: the stored refresh token stays.
    assert await _stored_refresh_token(ctx, cred_id) == "rt-2"


async def test_rejected_refresh_token_asks_for_a_reconnect(
    integration_context: Context, clean_oauth: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = integration_context
    endpoint = _TokenEndpoint(lambda _: httpx.Response(400, json={"error": "invalid_grant"}))
    _install(monkeypatch, endpoint)
    await _create(
        ctx,
        "workday",
        grant_type="refresh_token",
        token_url="https://wd2-impl-services1.workday.com/ccx/oauth2/acme/token",
        client_id="wd-client",
        client_secret="wd-secret",  # pragma: allowlist secret
        refresh_token="rt-revoked",  # pragma: allowlist secret
    )

    with pytest.raises(CredentialNeedsReconnectError) as exc_info:
        await _inject(ctx, "workday")

    assert exc_info.value.type == "credential_needs_reconnect"
