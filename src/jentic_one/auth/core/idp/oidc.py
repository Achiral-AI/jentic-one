"""Generic OIDC identity provider adapter."""

from __future__ import annotations

from urllib.parse import urlencode

import httpx

from jentic_one.auth.core.idp.adapter import IdpClaims
from jentic_one.shared.config import IdpConfig


class OidcAdapter:
    """Generic OIDC-compliant identity provider adapter.

    Implements the IdpAdapter protocol for any standards-compliant OIDC provider.
    """

    def __init__(self, config: IdpConfig) -> None:
        self._config = config
        self._discovery: dict[str, object] | None = None

    @property
    def _authorization_endpoint(self) -> str:
        if self._config.authorization_endpoint:
            return self._config.authorization_endpoint
        return f"{self._config.issuer.rstrip('/')}/authorize"

    @property
    def _token_endpoint(self) -> str:
        if self._config.exchange_endpoint:
            return self._config.exchange_endpoint
        return f"{self._config.issuer.rstrip('/')}/oauth/token"

    @property
    def _userinfo_endpoint(self) -> str:
        if self._config.userinfo_endpoint:
            return self._config.userinfo_endpoint
        return f"{self._config.issuer.rstrip('/')}/userinfo"

    def authorize_url(self, *, state: str, nonce: str, redirect_uri: str) -> str:
        """Build the OIDC authorization URL."""
        params = {
            "response_type": "code",
            "client_id": self._config.client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(self._config.scopes),
            "state": state,
            "nonce": nonce,
        }
        return f"{self._authorization_endpoint}?{urlencode(params)}"

    async def exchange_code(self, code: str, *, redirect_uri: str) -> dict[str, object]:
        """Exchange upstream code for tokens, then fetch userinfo."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            token_resp = await client.post(
                self._token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": self._config.client_id,
                    "client_secret": self._config.client_secret.get_secret_value(),
                },
            )
            token_resp.raise_for_status()
            token_data = token_resp.json()

            access_token = token_data.get("access_token", "")
            userinfo_resp = await client.get(
                self._userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            userinfo_resp.raise_for_status()
            return userinfo_resp.json()  # type: ignore[no-any-return]

    def map_claims(self, userinfo: dict[str, object]) -> IdpClaims:
        """Map standard OIDC claims to IdpClaims."""
        return IdpClaims(
            external_subject=str(userinfo.get("sub", "")),
            email=str(userinfo.get("email", "")),
            first_name=str(userinfo.get("given_name", "")),
            last_name=str(userinfo.get("family_name", "")),
            email_verified=bool(userinfo.get("email_verified", False)),
        )
