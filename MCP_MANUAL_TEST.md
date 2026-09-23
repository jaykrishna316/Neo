# Neo MCP Manual Test - 4 Terminals

## Terminal 1 (Start First - Keep Running)
```bash
cd /home/user/Neo
tail -f .devsync/activity-log.json | jq '.'
```

## Terminal 2 (T+0s)
```bash
cd /home/user/Neo
python3 -m ide.mcp_neo_server &
sleep 1

python3 << 'EOF'
from ide.mcp_neo_server import neo_log_activity, neo_check_conflicts, neo_get_active_work

neo_log_activity(agent_id="dev_alice", file_path="src/auth.py", intent="Add OAuth2 authentication module", intent_category="feature")
neo_check_conflicts(agent_id="dev_alice", file_path="src/auth.py", intent="Add OAuth2 authentication module")
neo_get_active_work()

import time
time.sleep(5)
EOF
```

## Terminal 3 (T+5s - Wait 5 Seconds)
```bash
cd /home/user/Neo
python3 << 'EOF'
from ide.mcp_neo_server import neo_log_activity, neo_check_conflicts, neo_get_active_work

neo_log_activity(agent_id="dev_bob", file_path="src/auth.py", intent="Add JWT token validation", intent_category="feature")
neo_check_conflicts(agent_id="dev_bob", file_path="src/auth.py", intent="Add JWT token validation")
neo_get_active_work()

import time
time.sleep(5)
EOF
```

## Terminal 4 (T+10s - Wait 10 Seconds)
```bash
cd /home/user/Neo
python3 << 'EOF'
from ide.mcp_neo_server import neo_log_activity, neo_check_conflicts, neo_get_active_work

neo_log_activity(agent_id="dev_charlie", file_path="src/auth.py", intent="Add 2FA support", intent_category="feature")
neo_check_conflicts(agent_id="dev_charlie", file_path="src/auth.py", intent="Add 2FA support")
neo_get_active_work()

import time
time.sleep(5)
EOF
```

## Terminal 5 (T+15s - Wait 15 Seconds)
```bash
cd /home/user/Neo
python3 << 'EOF'
from ide.mcp_neo_server import neo_log_activity, neo_check_conflicts, neo_get_active_work

neo_log_activity(agent_id="dev_diana", file_path="src/auth.py", intent="Add account lockout mechanism", intent_category="feature")
neo_check_conflicts(agent_id="dev_diana", file_path="src/auth.py", intent="Add account lockout mechanism")
neo_get_active_work()

import time
time.sleep(5)
EOF
```
