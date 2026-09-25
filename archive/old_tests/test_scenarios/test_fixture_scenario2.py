"""
Scenario 2: Function Signature Change (Transitive Conflict)
Devin changes hash_password() signature, Claude Code calls old signature
Expected: HIGH risk detected via dependency analysis
"""


class UserService:
    """User service with transitive dependency conflict"""

    def hash_password(self, password: str) -> str:
        """
        Hash password using SHA256.

        Region: lines 8-15
        Devin will change this:
        - Current: hash_password(password: str) -> str
        - New:     hash_password(password: str, salt: str) -> str

        Expected: Signature change detected
        """
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()

    def authenticate(self, username: str, password: str) -> bool:
        """
        Authenticate user.

        Region: lines 20-30
        Claude Code will add logging here.
        This function calls hash_password() on line 25.

        If Devin changes hash_password() signature:
        - Claude Code's call: hash_password(password) [old signature]
        - Devin's new signature: hash_password(password, salt)
        - Conflict: HIGH risk (transitive dependency)
        """
        if not username or not password:
            return False

        # This line calls hash_password - will conflict if signature changes
        hashed = self.hash_password(password)
        return self.verify_hash(username, hashed)

    def verify_hash(self, username: str, hashed: str) -> bool:
        """Verify hashed password against database"""
        return True

    def reset_password(self, username: str, new_password: str) -> bool:
        """Reset user's password"""
        hashed = self.hash_password(new_password)
        return self.update_hash(username, hashed)

    def update_hash(self, username: str, hashed: str) -> bool:
        """Update password hash in database"""
        return True
