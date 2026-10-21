#!/usr/bin/env python3
"""
Payment Service - Payment processing and validation

Depends on auth-service for authentication.
This service is vulnerable to breaking changes in auth-service.authenticate()
"""

from typing import Dict, Optional, Tuple
from datetime import datetime
import sys
from pathlib import Path

# Add auth-service to path
sys.path.insert(0, str(Path(__file__).parent.parent / "auth-service"))

try:
    from auth_service import authenticate, validate_token, check_scope
except ImportError:
    # Fallback for testing
    authenticate = None
    validate_token = None
    check_scope = None


class PaymentService:
    """Payment processing and validation"""

    def __init__(self):
        self.transactions = {}
        self.payment_methods = {}

    def process_payment(
        self,
        username: str,
        password: str,
        amount: float,
        currency: str = "USD"
    ) -> Dict:
        """
        Process a payment by authenticating user and charging card.

        DEPENDS ON: auth-service.authenticate(username, password)

        This is the BREAKING CHANGE vulnerability point!

        Old code expected 3 parameters: username, password, timestamp
        New code only takes 2 parameters: username, password

        Args:
            username: User authenticating
            password: User password
            amount: Amount to charge
            currency: Currency code

        Returns:
            Payment result with transaction ID
        """
        if authenticate is None:
            return {"success": False, "error": "Auth service unavailable"}

        # BREAKING CHANGE POINT:
        # Old code: success, token, user = authenticate(username, password, int(time.time()))
        # New code: success, token, user = authenticate(username, password)
        #
        # The timestamp parameter was removed from authenticate()
        # This function will fail with the new signature!

        success, token, user_data = authenticate(username, password)

        if not success:
            return {
                "success": False,
                "error": "Authentication failed",
                "transaction_id": None
            }

        # Validate token has payment scope
        if not check_scope(token, "write"):
            return {
                "success": False,
                "error": "Token missing required scope",
                "transaction_id": None
            }

        # Process payment (simplified)
        transaction_id = f"TXN-{len(self.transactions) + 1}"
        self.transactions[transaction_id] = {
            "username": username,
            "amount": amount,
            "currency": currency,
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
            "token": token
        }

        return {
            "success": True,
            "transaction_id": transaction_id,
            "amount": amount,
            "currency": currency,
            "username": username,
            "timestamp": datetime.utcnow().isoformat()
        }

    def validate_payment_amount(self, amount: float) -> Tuple[bool, Optional[str]]:
        """
        Validate payment amount.

        Args:
            amount: Amount to validate

        Returns:
            (is_valid, error_message)
        """
        if amount <= 0:
            return False, "Amount must be positive"

        if amount > 999_999.99:
            return False, "Amount exceeds maximum limit"

        return True, None

    def get_transaction(self, transaction_id: str) -> Optional[Dict]:
        """Get transaction details"""
        return self.transactions.get(transaction_id)

    def get_all_transactions(self) -> Dict:
        """Get all transactions"""
        return self.transactions


# Global service instance
_payment_service = PaymentService()


def get_payment_service() -> PaymentService:
    """Get global payment service instance"""
    return _payment_service


def process_payment(username: str, password: str, amount: float, currency: str = "USD") -> Dict:
    """Convenience function to process payment"""
    return _payment_service.process_payment(username, password, amount, currency)
