#!/usr/bin/env python3
"""
Auth Service v1.0 - Original API

Provides authentication for other services.
Gateway and Payment services import this.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Token:
    """Authentication token."""
    user_id: str
    expires_at: int
    permissions: list


def authenticate(user_id: str) -> Optional[Token]:
    """
    Original authenticate function.

    SIGNATURE v1.0:
        authenticate(user_id: str) -> Token

    Takes user_id and returns authentication token.
    Gateway service and Payment service depend on this signature.
    """
    if not user_id:
        return None

    return Token(
        user_id=user_id,
        expires_at=3600,
        permissions=["read", "write"]
    )


def validate_token(token: Token) -> bool:
    """Validate authentication token."""
    return token.expires_at > 0


def revoke_token(token: Token) -> None:
    """Revoke authentication token."""
    token.expires_at = 0
