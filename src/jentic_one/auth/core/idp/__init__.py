"""Pluggable Identity Provider adapters."""

from jentic_one.auth.core.idp.adapter import IdpAdapter, IdpClaims
from jentic_one.auth.core.idp.oidc import OidcAdapter

__all__ = ["IdpAdapter", "IdpClaims", "OidcAdapter"]
