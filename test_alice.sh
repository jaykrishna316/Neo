#!/bin/bash
# ALICE TERMINAL
# Run these commands in order

cd ~/Neo
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

echo "✅ Setup complete"
echo ""
echo "Now run Alice's declaration in ALICE TERMINAL:"
echo ""

# STEP 1: Alice declares intent
echo ">>> COPY PASTE THIS <<<<<"
echo '.venv/bin/python3 -m cli.neo_client declare alice src/auth.py "Add bcrypt password hashing" --category feature'
echo ">>> END COPY PASTE <<<<<"
echo ""
read -p "Press enter after running above command... "

# STEP 2: Alice edits file
cat > src/auth.py << 'EOF'
import bcrypt

def authenticate_user(username, password):
    """User authentication with bcrypt."""
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    return bool(username and hashed)

def validate_token(token):
    """Validate auth token."""
    return token.startswith("token_")

def hash_password(password):
    """NEW: Hash password with bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
EOF

echo "✅ Alice's file edited"
echo ""

# STEP 4: Alice completes work (after Bob declares)
echo "After Bob declares intent (next step)..."
echo "Run this to complete Alice's work:"
echo ""
echo ">>> COPY PASTE THIS <<<<<"
echo '.venv/bin/python3 -m cli.neo_client complete alice src/auth.py --added 10 --removed 2'
echo ">>> END COPY PASTE <<<<<"
