"""Tests for provider config parsing (discriminated union)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from jentic_one.shared.config import (
    CredentialsConfig,
    DirectOAuth2ProviderConfig,
    PipedreamProviderConfig,
)


def test_direct_oauth2_parses() -> None:
    cfg = CredentialsConfig.model_validate(
        {
            "providers": {
                "github": {
                    "kind": "direct_oauth2",
                    "redirect_uri": "https://example.com/callback",
                    "default_scopes": ["repo"],
                }
            }
        }
    )
    provider_cfg = cfg.providers["github"]
    assert isinstance(provider_cfg, DirectOAuth2ProviderConfig)
    assert provider_cfg.kind == "direct_oauth2"
    assert provider_cfg.redirect_uri == "https://example.com/callback"
    assert provider_cfg.default_scopes == ["repo"]
    assert provider_cfg.expiry_skew_seconds == 60
    assert provider_cfg.authorize_extra_params == {
        "prompt": "consent",
        "access_type": "offline",
    }


def test_direct_oauth2_authorize_extra_params_overridable() -> None:
    cfg = CredentialsConfig.model_validate(
        {
            "providers": {
                "github": {
                    "kind": "direct_oauth2",
                    "redirect_uri": "https://example.com/callback",
                    "authorize_extra_params": {"prompt": "select_account"},
                }
            }
        }
    )
    provider_cfg = cfg.providers["github"]
    assert isinstance(provider_cfg, DirectOAuth2ProviderConfig)
    assert provider_cfg.authorize_extra_params == {"prompt": "select_account"}


def test_pipedream_parses() -> None:
    cfg = CredentialsConfig.model_validate(
        {
            "providers": {
                "pd": {
                    "kind": "pipedream",
                    "project_id": "proj_123",
                    "client_id": "cid",
                    "client_secret": "csecret",
                }
            }
        }
    )
    provider_cfg = cfg.providers["pd"]
    assert isinstance(provider_cfg, PipedreamProviderConfig)
    assert provider_cfg.kind == "pipedream"
    assert provider_cfg.project_id == "proj_123"
    assert provider_cfg.environment == "production"


def test_bad_kind_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        CredentialsConfig.model_validate(
            {
                "providers": {
                    "bad": {
                        "kind": "unknown_kind",
                        "some_field": "value",
                    }
                }
            }
        )


def test_empty_providers_valid() -> None:
    cfg = CredentialsConfig.model_validate({"providers": {}})
    assert cfg.providers == {}
