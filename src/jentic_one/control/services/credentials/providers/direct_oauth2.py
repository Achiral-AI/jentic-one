"""DirectOAuth2Provider — handles authorization_code and client_credentials OAuth2 flows."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

from jentic_one.control.repos import CredentialRepository, OAuthClientCredentialRepository
from jentic_one.control.services.credentials.providers.base import (
    NotConnectableError,
    ProviderError,
)
from jentic_one.control.services.credentials.providers.oauth2 import (
    InvalidGrantError,
    OAuth2Provider,
    TokenExchangeError,
)
from jentic_one.control.services.credentials.schemas.connect import (
    AuthCodeChallenge,
    ConnectCallback,
    ConnectRequest,
    ConnectState,
)
from jentic_one.control.services.credentials.schemas.oauth_client_options import (
    OAuthClientOptions,
)
from jentic_one.control.services.credentials.schemas.provision import (
    APIReference,
    OAuthTokenView,
    ProvisionResult,
    RefreshResult,
)
from jentic_one.control.services.credentials.state import (
    encode_state,
    generate_nonce,
    pkce_challenge,
    pkce_verifier,
)
from jentic_one.shared.config import DirectOAuth2ProviderConfig
from jentic_one.shared.context import Context

# Re-exported for existing importers of these error types through
# ``providers.direct_oauth2`` (they now live on the shared OAuth2 base).
__all__ = [
    "DirectOAuth2Provider",
    "InvalidGrantError",
    "TokenExchangeError",
]


class DirectOAuth2Provider(OAuth2Provider):
    """Provider for direct OAuth2 credentials (platform is the OAuth2 client)."""

    name: str = "direct_oauth2"

    def __init__(self, cfg: DirectOAuth2ProviderConfig) -> None:
        # Explicit override; when None, begin_connect derives per request.
        self._configured_redirect_uri = cfg.redirect_uri
        self._default_scopes = cfg.default_scopes
        self._expiry_skew_seconds = cfg.expiry_skew_seconds
        self._authorize_extra_params = dict(cfg.authorize_extra_params)

    @property
    def managed(self) -> bool:
        return True

    async def begin_connect(
        self,
        ctx: Context,
        *,
        api: APIReference,
        request: ConnectRequest,
    ) -> AuthCodeChallenge:
        credential_id = request.extra.get("credential_id", "")
        if not credential_id:
            raise ProviderError("credential_id required in request.extra")

        async with ctx.control_db.session() as session:
            credential = await CredentialRepository.get_by_id(session, credential_id)
            if credential is None:
                raise ProviderError(f"Credential '{credential_id}' not found")

            occ = await OAuthClientCredentialRepository.get_by_credential(session, credential_id)
            if occ is None:
                raise ProviderError(f"No oauth_client_credentials for credential '{credential_id}'")

            if not occ.authorize_url:
                raise NotConnectableError(
                    "Credential has no authorize_url — cannot initiate connect flow"
                )

        scopes = request.scopes or self._default_scopes
        scope_str = " ".join(scopes) if scopes else (occ.scope or "")
        options = OAuthClientOptions.from_stored(occ.client_options)

        # The credential's own redirect_uri wins, then explicit config, then
        # the callback URL the web layer derived for this request
        # (public_base_url or request origin). The resolved value is embedded
        # in the signed state so the token exchange replays it byte-identically
        # (RFC 6749 §4.1.3).
        redirect_uri = options.redirect_uri or self._configured_redirect_uri or request.redirect_uri
        if not redirect_uri:
            raise ProviderError(
                "No redirect_uri available: set providers.direct_oauth2.redirect_uri "
                "or server.public_base_url, or call via the web connect endpoint"
            )

        state_secret = ctx.config.credentials.connect.state_secret.get_secret_value()
        ttl = ctx.config.credentials.connect.state_ttl_seconds
        nonce = generate_nonce()

        connect_state = ConnectState(
            credential_id=credential_id,
            provider=self.name,
            actor_id=request.extra.get("actor_id"),
            actor_type=request.extra.get("actor_type"),
            issued_at=datetime.now(UTC),
            nonce=nonce,
            redirect_uri=redirect_uri,
        )
        signed_state = encode_state(state_secret, connect_state, ttl)

        params: dict[str, str] = {
            "response_type": "code",
            "client_id": occ.client_id,
            "redirect_uri": redirect_uri,
            "state": signed_state,
        }
        if scope_str:
            params["scope"] = scope_str
        if options.pkce:
            params["code_challenge"] = pkce_challenge(pkce_verifier(state_secret, nonce))
            params["code_challenge_method"] = "S256"
        # Apply config-supplied extras LAST so they win over every standard
        # parameter (including ``state`` and ``scope``). This is the only
        # knob general enough to accommodate non-standard IdPs, and it's
        # operator-only — misconfiguration is on the configurer.
        # Don't do it unless you really know what you're doing.
        params.update(self._authorize_extra_params)

        authorize_url = f"{occ.authorize_url}?{urlencode(params)}"
        return AuthCodeChallenge(authorize_url=authorize_url, state=signed_state)

    async def complete_connect(
        self,
        ctx: Context,
        *,
        state: ConnectState,
        callback: ConnectCallback,
    ) -> ProvisionResult:
        if callback.error:
            raise ProviderError(f"Authorization denied: {callback.error}")

        if not callback.code:
            raise ProviderError("No authorization code in callback")

        async with ctx.control_db.session() as session:
            occ = await OAuthClientCredentialRepository.get_by_credential(
                session, state.credential_id
            )
            if occ is None:
                raise ProviderError(
                    f"No oauth_client_credentials for credential '{state.credential_id}'"
                )

        client_secret = ctx.encryption.decrypt(occ.encrypted_client_secret)
        options = OAuthClientOptions.from_stored(occ.client_options)

        # Replay the exact redirect_uri the authorize request used (carried in
        # the signed state); RFC 6749 requires the token exchange to match. Fall
        # back to the configured value for states minted before this claim
        # existed (rolling upgrade).
        redirect_uri = state.redirect_uri or self._configured_redirect_uri
        if not redirect_uri:
            raise ProviderError("Connect state is missing the redirect_uri")

        payload = {
            "grant_type": "authorization_code",
            "code": callback.code,
            "redirect_uri": redirect_uri,
        }
        if options.pkce:
            state_secret = ctx.config.credentials.connect.state_secret.get_secret_value()
            payload["code_verifier"] = pkce_verifier(state_secret, state.nonce)
        token_data = await self._post_client_token(
            occ.token_url, payload, occ.client_id, client_secret, options
        )

        expires_at = None
        if "expires_in" in token_data:
            expires_at = datetime.now(UTC) + timedelta(
                seconds=int(token_data["expires_in"]) - self._expiry_skew_seconds
            )

        return ProvisionResult(
            access_token=token_data.get("access_token"),
            refresh_token=token_data.get("refresh_token"),
            expires_at=expires_at,
            scope=token_data.get("scope"),
            provider_account_ref=None,
            server_variables=_kept_fields(token_data, options.keep_token_fields),
        )

    async def refresh(
        self,
        ctx: Context,
        *,
        token: OAuthTokenView,
    ) -> RefreshResult:
        async with ctx.control_db.session() as session:
            occ = await OAuthClientCredentialRepository.get_by_credential(
                session, token.credential_id
            )
            if occ is None:
                raise ProviderError(
                    f"No oauth_client_credentials for credential '{token.credential_id}'"
                )

        client_secret = ctx.encryption.decrypt(occ.encrypted_client_secret)
        refresh_token_value = await token.decrypt()

        token_data = await self._post_client_token(
            occ.token_url,
            {"grant_type": "refresh_token", "refresh_token": refresh_token_value},
            occ.client_id,
            client_secret,
            OAuthClientOptions.from_stored(occ.client_options),
        )

        expires_at = None
        if "expires_in" in token_data:
            expires_at = datetime.now(UTC) + timedelta(
                seconds=int(token_data["expires_in"]) - self._expiry_skew_seconds
            )

        return RefreshResult(
            access_token=token_data["access_token"],
            expires_at=expires_at,
            refresh_token=token_data.get("refresh_token"),
            scope=token_data.get("scope"),
        )

    async def _post_client_token(
        self,
        token_url: str,
        payload: dict[str, str],
        client_id: str,
        client_secret: str,
        options: OAuthClientOptions,
    ) -> dict[str, Any]:
        """Call the token endpoint, authenticating the way the vendor expects."""
        auth: tuple[str, str] | None = None
        if options.token_auth_method == "client_secret_basic":
            auth = (client_id, client_secret)
        else:
            payload = {**payload, "client_id": client_id, "client_secret": client_secret}
        return await self._post_token(
            token_url, payload, auth=auth, as_json=options.token_request_encoding == "json"
        )


def _kept_fields(token_data: dict[str, Any], fields: dict[str, str]) -> dict[str, str] | None:
    """The named token-response fields, as server variables; None when there are none."""
    kept: dict[str, str] = {}
    for path, name in fields.items():
        value: object = token_data
        for key in path.split("."):
            value = value.get(key) if isinstance(value, dict) else None
        if isinstance(value, str | int) and not isinstance(value, bool) and str(value):
            kept[name] = str(value)
    return kept or None
