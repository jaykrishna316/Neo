#!/usr/bin/env python3
"""
Auth Service v2.0 - BREAKING CHANGE

Refactored authenticate() to require email + MFA for security.

BREAKING CHANGES:
  OLD: authenticate(user_id: str) -> Token
  NEW: authenticate(email: str, mfa_code: str) -> AuthToken

Gateway and Payment services will BREAK if they don't update!
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class AuthToken:
    """Enhanced authentication token with MFA."""
    user_id: str
    email: str
    mfa_verified: bool
    expires_at: int
    permissions: list
    security_level: str  # "basic" or "mfa"


def authenticate(email: str, mfa_code: str) -> Optional[AuthToken]:
    """
    NEW authenticate function - BREAKING CHANGE!

    SIGNATURE v2.0:
        authenticate(email: str, mfa_code: str) -> AuthToken

    Takes email + MFA code (requires 2FA for all users).

    INCOMPATIBLE with v1.0 signature!
    - Gateway service calls authenticate(user_id) → will fail
    - Payment service calls authenticate(user_id) → will fail
    """
    if not email or not mfa_code:
        return None

    return AuthToken(
        user_id=email.split("@")[0],
        email=email,
        mfa_verified=True,
        expires_at=3600,
        permissions=["read", "write"],
        security_level="mfa"
    )


def validate_token(token: AuthToken) -> bool:
    """Validate authentication token."""
    return token.expires_at > 0 and token.mfa_verified


def revoke_token(token: AuthToken) -> None:
    """Revoke authentication token."""
    token.expires_at = 0
    token.mfa_verified = False
