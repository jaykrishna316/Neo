#!/usr/bin/env python3
"""
Payment Service - Process Payments

Routes payments to payment processors.
DEPENDS ON: auth-service v1.0

Uses auth-service.authenticate(user_id: str) -> Token
"""

# Import from auth-service (v1.0)
# In real code: from auth_service.auth_api import authenticate, Token
from ..auth-service.auth_api import authenticate, Token


def process_payment(user_id: str, amount: float, currency: str) -> dict:
    """
    Process payment for user.

    1. Authenticate user using auth-service
    2. Validate payment amount
    3. Process payment
    4. Return result
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

    if amount <= 0:
        return {
            "status": 400,
            "error": "Invalid amount",
            "message": f"Amount must be positive, got {amount}"
        }

    return {
        "status": 200,
        "message": f"Payment processed for user {user_id}",
        "amount": amount,
        "currency": currency,
        "token_expires": token.expires_at
    }


def refund_payment(user_id: str, transaction_id: str) -> dict:
    """Refund a payment."""

    # USES AUTH-SERVICE v1.0 SIGNATURE:
    token = authenticate(user_id)  # ← Calls auth-service v1.0

    if not token:
        return {
            "status": 401,
            "error": "Unauthorized"
        }

    return {
        "status": 200,
        "message": f"Refund processed for transaction {transaction_id}",
        "user_id": user_id
    }
