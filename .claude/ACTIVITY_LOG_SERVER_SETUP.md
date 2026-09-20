# Activity Log Server Setup Guide

For distributed testing with multiple developers, the activity log needs to be hosted on a server instead of local git-committed files.

## Quick Start

### 1. Install Dependencies

```bash
pip install flask requests
```

### 2. Run the Server Locally

```bash
cd /path/to/Neo
python3 .claude/activity_log_server.py
```

Output:
```
 * Running on http://0.0.0.0:5000
 * WARNING: This is a development server. Do not use it in production.
```

### 3. Expose to Internet (using ngrok)

In a new terminal:

```bash
# Install ngrok (one-time)
brew install ngrok  # or download from https://ngrok.com

# Expose your local server
ngrok http 5000
```

Output:
```
Forwarding    https://abc123-def456.ngrok.io -> http://localhost:5000
```

**Share the URL with Dev 2:** `https://abc123-def456.ngrok.io`

---

## Using the Server

### For Developer 1 (You):

```bash
# Set server URL as environment variable
export ACTIVITY_LOG_SERVER="https://abc123.ngrok.io"

# Now use git_activity_log_bridge as normal
python3 << 'EOF'
from git_activity_log_bridge import GitActivityLogBridge

bridge = GitActivityLogBridge(server_url="https://abc123.ngrok.io")
result = bridge.auto_add_approvers_to_mr("feature/your-branch")
print(result)
EOF
```

### For Developer 2:

```bash
# Clone Neo repo
git clone https://github.com/jaykrishna316/Neo.git

# Set server URL
export ACTIVITY_LOG_SERVER="https://abc123.ngrok.io"

# Make changes and log them
python3 << 'EOF'
from activity_log_client import ActivityLogClient

client = ActivityLogClient("https://abc123.ngrok.io")

# Log a change
change = client.log_change(
    developer="Dev2",
    file_path="auth.py",
    function_name="validate_user",
    old_code="def validate(u, p): return check(u, p)",
    new_code="def validate(u, p, email=False): return check(u, p, email)",
    feature_branch="feature/dev2-auth",
    verbal_description="Added email validation parameter"
)
print(change)
EOF
```

---

## REST API Endpoints

All endpoints are JSON-based.

### Health Check
```
GET /health
Response: {"status": "ok", "service": "activity-log-server"}
```

### Log a Change
```
POST /api/log_change
Body: {
    "developer": "Dev1",
    "file_path": "auth.py",
    "function_name": "validate_user",
    "old_code": "...",
    "new_code": "...",
    "feature_branch": "feature/dev1-auth",
    "verbal_description": "Refactored validation logic"
}
Response: {
    "id": "2026-09-15T14:32:45.123456",
    "developer": "Dev1",
    "file": "auth.py",
    "function": "validate_user",
    "branch": "feature/dev1-auth",
    "conflict_severity": "high",
    "related_changes": ["Dev2"],
    ...
}
```

### Record Approval
```
POST /api/record_approval
Body: {
    "developer": "Dev1",
    "file_path": "auth.py",
    "function_name": "validate_user",
    "approval_status": "approved"
}
Response: {
    "approved_by": ["Dev1"],
    "rejected_by": [],
    "last_update": "2026-09-15T14:35:22.123456"
}
```

### Get Conflicts
```
GET /api/conflicts?base_branch=main&head_branch=feature/dev1-auth
Response: {
    "conflicts": [
        {
            "file": "auth.py",
            "function": "validate_user",
            "severity": "HIGH",
            "developers_involved": ["Dev1", "Dev2"],
            "descriptions": [...],
            "changes_count": 2
        }
    ]
}
```

### Check if Can Merge
```
GET /api/can_merge?file_path=auth.py&function_name=validate_user
Response: {
    "can_merge": true,
    "status": {
        "reason": "All developers approved",
        "approved_by": ["Dev1", "Dev2"],
        "status": "APPROVED"
    }
}
```

### Record Rollback
```
POST /api/record_rollback
Body: {
    "merge_commit_sha": "abc123def456",
    "file_path": "auth.py",
    "function_name": "validate_user",
    "reason": "Failed integration test"
}
Response: {
    "timestamp": "2026-09-15T14:40:12.123456",
    "merge_commit": "abc123def456",
    "file": "auth.py",
    "function": "validate_user",
    "reason": "Failed integration test",
    "status": "ROLLED_BACK"
}
```

---

## Testing Workflow with Dev 2

### Step 1: Start Server (Your Laptop)
```bash
python3 .claude/activity_log_server.py
```

### Step 2: Expose via ngrok
```bash
ngrok http 5000
# Get URL like: https://abc123.ngrok.io
```

### Step 3: Share with Dev 2
Send them:
- The ngrok URL
- Instructions to set: `export ACTIVITY_LOG_SERVER="https://abc123.ngrok.io"`

### Step 4: Both Make Changes

**You (Dev 1):**
```bash
git checkout -b feature/auth-refactor
# Edit auth.py::validate_user()
# Commit and push

# Log the change
python3 << 'EOF'
from activity_log_client import ActivityLogClient
import os

client = ActivityLogClient(os.getenv("ACTIVITY_LOG_SERVER"))
change = client.log_change(
    developer="Dev1",
    file_path="auth.py",
    function_name="validate_user",
    old_code="def validate(u, p): return check(u, p)",
    new_code="def validate(u, p): return db.check(u, p)",
    feature_branch="feature/auth-refactor",
    verbal_description="Refactored to use database"
)
print(f"Change logged: {change['id']}")
EOF
```

**Dev 2:**
```bash
git checkout -b feature/auth-email
# Edit auth.py::validate_user()
# Commit and push

# Log the change (will detect HIGH conflict!)
python3 << 'EOF'
from activity_log_client import ActivityLogClient
import os

client = ActivityLogClient(os.getenv("ACTIVITY_LOG_SERVER"))
change = client.log_change(
    developer="Dev2",
    file_path="auth.py",
    function_name="validate_user",
    old_code="def validate(u, p): return check(u, p)",
    new_code="def validate(u, p, email=False): return check(u, p, email)",
    feature_branch="feature/auth-email",
    verbal_description="Added email validation"
)
print(f"Conflict detected: {change['conflict_severity']}")
EOF
```

### Step 5: Check Conflicts
```bash
python3 << 'EOF'
from activity_log_client import ActivityLogClient
import os

client = ActivityLogClient(os.getenv("ACTIVITY_LOG_SERVER"))
conflicts = client.get_conflicts("main")
for conflict in conflicts:
    print(f"HIGH conflict in {conflict['file']}::{conflict['function']}")
    print(f"  Developers: {conflict['developers_involved']}")
EOF
```

### Step 6: Create PRs and Test Approval
```bash
# Both create PRs on GitHub

# Git Bridge auto-detects conflict and adds reviewers
python3 << 'EOF'
from git_activity_log_bridge import GitActivityLogBridge
import os

bridge = GitActivityLogBridge(server_url=os.getenv("ACTIVITY_LOG_SERVER"))
result = bridge.auto_add_approvers_to_mr("feature/auth-refactor")
print(f"Added reviewers: {result.get('approvers_added')}")
EOF

# Both approve
python3 << 'EOF'
from activity_log_client import ActivityLogClient
import os

client = ActivityLogClient(os.getenv("ACTIVITY_LOG_SERVER"))
client.record_approval("Dev1", "auth.py", "validate_user", "approved")
client.record_approval("Dev2", "auth.py", "validate_user", "approved")

# Check if can merge
can_merge, status = client.can_merge_to_main("auth.py", "validate_user")
print(f"Can merge: {can_merge}")
print(f"Status: {status}")
EOF
```

---

## File Storage

The server stores activity log data in: `.activity_log_storage/`

```
.activity_log_storage/
├── changes/        # Change records
├── approvals/      # Approval records
├── escalations/    # Escalation tracking
└── rollbacks/      # Rollback records
```

This directory is separate from git to avoid conflicts.

---

## Environment Variables

```bash
# For Git Bridge
export ACTIVITY_LOG_SERVER="https://your-ngrok-url.ngrok.io"

# For GitHub integration
export GITHUB_TOKEN="github_pat_xxxxx"
```

---

## Production Deployment

For production, deploy this server to:
- AWS Lambda + S3 (serverless)
- Google Cloud Run (containerized)
- DigitalOcean App Platform
- Heroku
- Any server that can run Python

Example for Google Cloud Run:
```bash
# Create Dockerfile
cat > Dockerfile << 'EOF'
FROM python:3.10
WORKDIR /app
COPY . .
RUN pip install flask requests
CMD ["python", "activity_log_server.py"]
EOF

# Deploy
gcloud run deploy activity-log-server \
  --source . \
  --platform managed \
  --allow-unauthenticated
```

---

## Troubleshooting

### Server Won't Start
```bash
# Make sure port 5000 is free
lsof -i :5000
kill -9 <PID>

# Try different port
python3 activity_log_server.py  # Edit to use port 5001
```

### ngrok URL Expires
- ngrok free tier URLs expire after 2 hours
- Either renew the tunnel or upgrade to paid plan
- Alternative: Use Cloudflare Tunnel (no expiry)

### Dev 2 Can't Connect
```bash
# Check connection
curl https://abc123.ngrok.io/health

# Verify environment variable
echo $ACTIVITY_LOG_SERVER

# Check server logs for errors
```

### Conflicts Not Detected
- Ensure both devs log changes on the same function
- Check `conflict_severity` in response (should be "high" if >50% overlap)
- Verify both changes are in server storage

---

## Next Steps

1. ✅ Start server locally
2. ✅ Expose with ngrok
3. ✅ Test with Dev 2
4. ✅ Verify conflict detection
5. ✅ Test approval workflow
6. 📦 Deploy to production for team use
