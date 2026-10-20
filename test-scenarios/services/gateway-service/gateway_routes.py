#!/usr/bin/env python3
"""
Gateway Service - API Gateway

Routes requests to backend services.
DEPENDS ON: auth-service v1.0

Uses auth-service.authenticate(user_id: str) -> Token
"""

# Import from auth-service (v1.0)
# In real code: from auth_service.auth_api import authenticate, Token
from ..auth-service.auth_api import authenticate, Token


def handle_request(user_id: str, action: str) -> dict:
    """
    Handle incoming request.

    1. Authenticate user using auth-service
    2. Route request to appropriate backend
    3. Return response
    """

    # USES AUTH-SERVICE v1.0 SIGNATURE:
    # authenticate(user_id: str) -> Token
    token = authenticate(user_id)  # ← Calls auth-service v1.0

    if not token:
        return {
            "status": 401,
            "error": "Unauthorized",
            "message": "User authentication failed"
        }

    return {
        "status": 200,
        "message": f"Request processed for user {user_id}",
        "action": action,
        "token_expires": token.expires_at
    }


def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "auth_service": "connected",
        "version": "1.0"
    }
