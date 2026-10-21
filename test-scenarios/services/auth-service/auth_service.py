#!/usr/bin/env python3
"""
Auth Service - OAuth2 and JWT token management

Provides authentication and authorization for the payment system.
Other services depend on the authenticate() and validate_token() functions.
"""

from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import hashlib
import json


class AuthService:
    """OAuth2 and JWT token management"""

    def __init__(self, secret_key: str = "default-secret"):
        self.secret_key = secret_key
        self.tokens = {}  # In-memory token store
        self.users = {}   # User registry

    def register_user(self, username: str, password: str, email: str) -> Dict:
        """
        Register a new user.

        Args:
            username: Unique username
            password: User password (should be hashed in production)
            email: User email

        Returns:
            Registration confirmation
        """
        if username in self.users:
            return {"success": False, "error": "User already exists"}

        self.users[username] = {
            "password": hashlib.sha256(password.encode()).hexdigest(),
            "email": email,
            "created_at": datetime.utcnow().isoformat(),
            "scopes": ["read", "write"]
        }

        return {
            "success": True,
            "username": username,
            "email": email
        }

    def authenticate(
        self,
        username: str,
        password: str
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Authenticate user and return JWT token.

        FUNCTION SIGNATURE:
        - OLD (v1): authenticate(username: str, password: str, timestamp: int) -> Tuple
        - NEW (v2): authenticate(username: str, password: str) -> Tuple

        Breaking change: timestamp parameter REMOVED
        Downstream impact: payment-service calls this function

        Args:
            username: Username to authenticate
            password: Password to verify

        Returns:
            (success: bool, token: Optional[str], user_data: Optional[Dict])
        """
        if username not in self.users:
            return False, None, {"error": "Invalid credentials"}

        user = self.users[username]
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        if user["password"] != password_hash:
            return False, None, {"error": "Invalid credentials"}

        # Generate JWT token
        token_data = {
            "username": username,
            "scopes": user["scopes"],
            "issued_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat()
        }

        token = self._encode_jwt(token_data)
        self.tokens[token] = token_data

        return True, token, {
            "username": username,
            "email": user["email"],
            "scopes": user["scopes"]
        }

    def validate_token(self, token: str) -> Tuple[bool, Optional[Dict]]:
        """
        Validate JWT token.

        Args:
            token: JWT token to validate

        Returns:
            (is_valid: bool, token_data: Optional[Dict])
        """
        if token not in self.tokens:
            return False, None

        token_data = self.tokens[token]

        # Check expiration
        expires_at = datetime.fromisoformat(token_data["expires_at"])
        if datetime.utcnow() > expires_at:
            return False, None

        return True, token_data

    def check_scope(self, token: str, required_scope: str) -> bool:
        """
        Check if token has required scope.

        Args:
            token: JWT token
            required_scope: Required scope (e.g., "write")

        Returns:
            True if token has scope, False otherwise
        """
        is_valid, token_data = self.validate_token(token)

        if not is_valid or token_data is None:
            return False

        return required_scope in token_data.get("scopes", [])

    def _encode_jwt(self, data: Dict) -> str:
        """Encode JWT token (simplified, not production-grade)"""
        payload = json.dumps(data)
        signature = hashlib.sha256(
            (payload + self.secret_key).encode()
        ).hexdigest()
        return f"{payload}.{signature}"

    def _decode_jwt(self, token: str) -> Optional[Dict]:
        """Decode JWT token (simplified)"""
        try:
            payload, signature = token.rsplit(".", 1)
            expected_sig = hashlib.sha256(
                (payload + self.secret_key).encode()
            ).hexdigest()

            if signature == expected_sig:
                return json.loads(payload)
        except:
            pass

        return None


# Global service instance
_auth_service = AuthService()


def get_auth_service() -> AuthService:
    """Get global auth service instance"""
    return _auth_service


def authenticate(username: str, password: str) -> Tuple[bool, Optional[str], Optional[Dict]]:
    """Convenience function to authenticate user"""
    return _auth_service.authenticate(username, password)


def validate_token(token: str) -> Tuple[bool, Optional[Dict]]:
    """Convenience function to validate token"""
    return _auth_service.validate_token(token)


def check_scope(token: str, required_scope: str) -> bool:
    """Convenience function to check token scope"""
    return _auth_service.check_scope(token, required_scope)
