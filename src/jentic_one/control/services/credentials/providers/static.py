"""StaticProvider — handles bearer_token, api_key, and basic credentials."""

from __future__ import annotations

from jentic_one.control.services.credentials.providers.base import NotConnectableError
from jentic_one.control.services.credentials.providers.direct_oauth2 import DirectOAuth2Provider
from jentic_one.control.services.credentials.schemas.connect import (
    ConnectCallback,
    ConnectChallenge,
    ConnectRequest,
    ConnectState,
)
from jentic_one.control.services.credentials.schemas.provision import (
    APIReference,
    OAuthTokenView,
    ProvisionResult,
    RefreshResult,
)
from jentic_one.shared.config import DirectOAuth2ProviderConfig
from jentic_one.shared.context import Context
from jentic_one.shared.models.credentials import CredentialType


class StaticProvider:
    """Provider for statically-provisioned credentials (no OAuth flow)."""

    name: str = "static"

    def __init__(self) -> None:
        # Static oauth2 credentials carry their own client and token URL; the
        # broker gets their tokens (client_credentials, refresh_token) the way
        # a direct OAuth2 client does.
        self._oauth2 = DirectOAuth2Provider(DirectOAuth2ProviderConfig())
        self._expiry_skew_seconds = self._oauth2._expiry_skew_seconds

    @property
    def managed(self) -> bool:
        return False

    @property
    def supported_types(self) -> list[CredentialType]:
        return list(CredentialType)

    def supports(self, wire_type: CredentialType) -> bool:
        return wire_type in (
            CredentialType.BEARER_TOKEN,
            CredentialType.API_KEY,
            CredentialType.BASIC,
            CredentialType.OAUTH2,
            CredentialType.NO_AUTH,
            CredentialType.SIGV4,
        )

    async def begin_connect(
        self,
        ctx: Context,
        *,
        api: APIReference,
        request: ConnectRequest,
    ) -> ConnectChallenge:
        raise NotConnectableError("StaticProvider does not support the connect flow")

    async def complete_connect(
        self,
        ctx: Context,
        *,
        state: ConnectState,
        callback: ConnectCallback,
    ) -> ProvisionResult:
        raise NotConnectableError("StaticProvider does not support the connect flow")

    async def refresh(
        self,
        ctx: Context,
        *,
        token: OAuthTokenView,
    ) -> RefreshResult:
        return await self._oauth2.refresh(ctx, token=token)
