"""Shared credential-generation and hashing utilities for auth services."""

from __future__ import annotations

import hashlib
import secrets

_CLIENT_SECRET_PREFIX = "jcs_"
_AGENT_API_KEY_PREFIX = "jak_"
_SERVICE_ACCOUNT_API_KEY_PREFIX = "sak_"


def hash_secret(value: str) -> str:
    """One-way SHA-256 hash for credential storage."""
    return hashlib.sha256(value.encode()).hexdigest()


def generate_client_secret() -> str:
    """Generate a prefixed, URL-safe client secret."""
    return f"{_CLIENT_SECRET_PREFIX}{secrets.token_urlsafe(32)}"


def generate_agent_api_key() -> str:
    """Generate a prefixed, URL-safe API key for agents."""
    return f"{_AGENT_API_KEY_PREFIX}{secrets.token_urlsafe(32)}"


def generate_service_account_api_key() -> str:
    """Generate a prefixed, URL-safe API key for service accounts."""
    return f"{_SERVICE_ACCOUNT_API_KEY_PREFIX}{secrets.token_urlsafe(32)}"
