"""Per-credential options for vendors whose OAuth differs from the default.

The default is the RFC 6749 confidential client: the client secret in a
form-encoded token request, no PKCE, the deployment's callback URL, and only
the standard token fields kept. Some vendors need otherwise (Notion: HTTP
Basic and a JSON body; Salesforce: its ``instance_url`` from the token
response), so each OAuth client credential may carry these options.
"""

from __future__ import annotations

import re
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator

_MAX_KEPT_FIELDS = 20
_SERVER_VARIABLE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
_FIELD_PATH = re.compile(r"^[A-Za-z0-9_]+(\.[A-Za-z0-9_]+){0,4}$")
# Set by the provider from the credential and the signed state.
_PROTOCOL_PARAMS = frozenset(
    {
        "response_type",
        "client_id",
        "redirect_uri",
        "state",
        "code_challenge",
        "code_challenge_method",
    }
)


class OAuthClientOptions(BaseModel):
    """How to talk to one vendor's authorize and token endpoints."""

    model_config = ConfigDict(extra="forbid")

    # RFC 6749 §2.3.1: the secret in the body, or HTTP Basic.
    token_auth_method: Literal["client_secret_post", "client_secret_basic"] = "client_secret_post"
    token_request_encoding: Literal["form", "json"] = "form"
    # RFC 7636 with S256.
    pkce: bool = False
    # The callback registered with the vendor, when it is not this
    # deployment's own (for example an app that relays the callback here).
    redirect_uri: str | None = None
    # Non-secret token-response fields to keep as server variables:
    # dotted response path -> server variable name.
    keep_token_fields: dict[str, str] = Field(default_factory=dict)
    # Extra authorize-URL parameters for this vendor (Atlassian's
    # ``audience``); they win over the provider's authorize_extra_params.
    authorize_params: dict[str, str] = Field(default_factory=dict)

    @field_validator("redirect_uri")
    @classmethod
    def _http_url(cls, value: str | None) -> str | None:
        if value is None:
            return value
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("redirect_uri must be an absolute http(s) URL")
        return value

    @field_validator("keep_token_fields")
    @classmethod
    def _field_names(cls, value: dict[str, str]) -> dict[str, str]:
        if len(value) > _MAX_KEPT_FIELDS:
            raise ValueError(f"keep_token_fields may name at most {_MAX_KEPT_FIELDS} fields")
        for path, name in value.items():
            if not _FIELD_PATH.match(path):
                raise ValueError(f"keep_token_fields path {path!r} is not a dotted field path")
            if not _SERVER_VARIABLE_NAME.match(name):
                raise ValueError(f"keep_token_fields name {name!r} is not a server variable name")
        return value

    @field_validator("authorize_params")
    @classmethod
    def _not_protocol_params(cls, value: dict[str, str]) -> dict[str, str]:
        reserved = sorted(_PROTOCOL_PARAMS & value.keys())
        if reserved:
            raise ValueError(f"authorize_params may not set {', '.join(reserved)}")
        return value

    @classmethod
    def from_stored(cls, value: dict[str, object] | None) -> OAuthClientOptions:
        """Options from the stored column; a NULL column is the default client."""
        return cls.model_validate(value or {})
