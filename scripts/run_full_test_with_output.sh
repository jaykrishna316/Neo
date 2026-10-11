#!/bin/bash
# Full Neo Test Runner - Captures REAL output from Neo coordination

set -e

cd "$(dirname "$0")/.."

echo "╔════════════════════════════════════════════════════════════╗"
echo "║          NEO FULL TEST WITH REAL OUTPUT CAPTURE            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Setup
echo "[SETUP] Creating test environment..."
mkdir -p .devsync src lib
rm -f .devsync/activity-log.json

cat > src/auth.py << 'EOF'
def authenticate_user(username, password):
    """User authentication."""
    return bool(username and password)

def validate_token(token):
    """Validate auth token."""
    return token.startswith("token_")
EOF

echo "✅ Test environment ready"
echo ""

# Start server and capture output
echo "[SERVER] Starting Neo server (will show real output)..."
echo "IMPORTANT: Leave this running in Terminal 1"
echo ""
echo "Run this command in Terminal 1:"
echo "  cd ~/Neo && .venv/bin/python3 -m cli.neo_server --clear"
echo ""
echo "Once server is running, proceed to Terminal 2 for next steps..."
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "[TEST] When ready, run these commands in Terminal 2:"
echo ""
echo "# STEP 5: Alice declares intent"
echo "cd ~/Neo"
echo ".venv/bin/python3 -m cli.neo_client declare alice src/auth.py 'Add bcrypt password hashing' --category feature"
echo ""
echo "# STEP 6: Alice edits file"
echo "cat > src/auth.py << 'INNER_EOF'"
echo "import bcrypt"
echo ""
echo "def authenticate_user(username, password):"
echo "    \"\"\"User authentication with bcrypt.\"\"\""
echo "    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())"
echo "    return bool(username and hashed)"
echo ""
echo "def validate_token(token):"
echo "    \"\"\"Validate auth token.\"\"\""
echo "    return token.startswith('token_')"
echo ""
echo "def hash_password(password):"
echo "    \"\"\"NEW: Hash password with bcrypt.\"\"\""
echo "    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()"
echo "INNER_EOF"
echo ""
echo "# STEP 7: Bob declares intent (THIS IS WHERE LOCK APPEARS!)"
echo ".venv/bin/python3 -m cli.neo_client declare bob src/auth.py 'Add OAuth2 support' --category feature"
echo ""
echo "# STEP 8: Alice completes work"
echo ".venv/bin/python3 -m cli.neo_client complete alice src/auth.py --added 10 --removed 2"
echo ""
echo "# STEP 9: View activity log"
echo "cat .devsync/activity-log.json | jq '.[] | {dev: .developer_id, intent: .intent[:35], lock_state, lock_holder, queue_pos: .queue_position}' | head -20"
echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "📝 INSTRUCTIONS:"
echo "1. Copy the server command above to Terminal 1 and run it"
echo "2. Copy each test command to Terminal 2 and run it"
echo "3. Watch Terminal 1 for REAL Neo output (locks, conflicts, etc)"
echo "4. After Step 9, share the Terminal 1 output with me"
echo ""
