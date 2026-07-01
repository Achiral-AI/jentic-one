"""Pydantic result models for access-request effect application."""

from __future__ import annotations

from pydantic import BaseModel


class CredentialBindEffect(BaseModel):
    """Result of applying a credential-bind effect."""

    binding_id: str
    rules_applied: int
    already_bound: bool


class ToolkitBindEffect(BaseModel):
    """Result of applying a toolkit-bind effect."""

    binding_id: str
    already_bound: bool


class ScopeGrantEffect(BaseModel):
    """Result of applying a scope-grant effect."""

    scope: str
    already_granted: bool


class SkippedEffect(BaseModel):
    """Result when an effect combination is unsupported."""

    skipped: bool = True
    reason: str
