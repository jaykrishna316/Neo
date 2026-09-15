"""
Scenario 1: Same Function, Overlapping Regions
Both agents modify authenticate() function (lines 8-15)
Expected: MEDIUM risk detected
"""


class AuthService:
    """Authentication service with overlapping regions for testing"""

    def authenticate(self, username: str, password: str) -> bool:
        """
        Authenticate user with username and password.

        Region: lines 8-15
        - Claude Code will add: detailed logging
        - Devin will add: rate limiting + exponential backoff

        Expected conflict: MEDIUM risk (same function)
        """
        import logging
        logger = logging.getLogger("AuthService")
        logger.info(f"Auth attempt: {username}")

        if not username or not password:
            logger.warning("Auth failed: missing credentials")
            return False

        result = self.verify_credentials(username, password)
        if not result:
            logger.warning(f"Auth failed: {username}")
        else:
            logger.info(f"Auth succeeded: {username}")
        return result

    def verify_credentials(self, username: str, password: str) -> bool:
        """Verify credentials against database"""
        # Placeholder implementation
        return True

    def get_user(self, username: str) -> dict:
        """Get user by username (non-overlapping region)"""
        return {"username": username, "id": 123}

    def hash_password(self, password: str) -> str:
        """Hash password using SHA256"""
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()
