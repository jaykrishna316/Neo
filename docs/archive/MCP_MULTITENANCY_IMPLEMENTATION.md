# MCP Multitenancy Implementation Spec

> **Exact code changes to add tenant isolation to core/mcp_server.py and core/activity_log.py**

## File 1: core/activity_log.py

### Change 1.1: Add tenant-aware path resolution

**Location:** Top of file, after imports

```python
import os
from pathlib import Path
from typing import Optional

# Multitenancy support
MULTITENANCY_ENABLED = os.getenv("NEO_MULTITENANCY", "false").lower() == "true"
DEFAULT_TENANT_ID = os.getenv("CLAUDE_TENANT_ID", "default")

def get_tenant_log_path(tenant_id: Optional[str] = None) -> Path:
    """Get isolated activity log for a specific tenant."""
    if not MULTITENANCY_ENABLED:
        return Path(".devsync/activity-log.json")  # Legacy single-tenant
    
    resolved_tenant = tenant_id or DEFAULT_TENANT_ID
    tenant_dir = Path(f".devsync/tenants/{resolved_tenant}")
    tenant_dir.mkdir(parents=True, exist_ok=True)
    
    # Write tenant marker for security validation
    marker = tenant_dir / ".tenant_id"
    if not marker.exists():
        marker.write_text(resolved_tenant)
    
    return tenant_dir / "activity-log.json"

def ensure_tenant_isolation(tenant_id: str):
    """Validate tenant directory structure and permissions."""
    if not MULTITENANCY_ENABLED:
        return
    
    tenant_dir = Path(f".devsync/tenants/{tenant_id}")
    marker_file = tenant_dir / ".tenant_id"
    
    if marker_file.exists():
        stored_tenant = marker_file.read_text().strip()
        if stored_tenant != tenant_id:
            raise ValueError(
                f"Tenant mismatch: Expected '{tenant_id}', "
                f"but directory contains '{stored_tenant}'"
            )
```

### Change 1.2: Update log_activity() to be tenant-aware

**Location:** log_activity() function

**Before:**
```python
def log_activity(agent_id: str, file_path: str, intent: str, 
                region: str = None, intent_category: str = "other"):
    """Log an agent's intent to work on a file."""
    log_file = Path(".devsync/activity-log.json")
```

**After:**
```python
def log_activity(agent_id: str, file_path: str, intent: str, 
                region: str = None, intent_category: str = "other",
                tenant_id: Optional[str] = None):
    """Log an agent's intent to work on a file (tenant-isolated)."""
    ensure_tenant_isolation(tenant_id or DEFAULT_TENANT_ID)
    log_file = get_tenant_log_path(tenant_id)
```

### Change 1.3: Update get_active_entries() to be tenant-aware

**Location:** get_active_entries() function

**Before:**
```python
def get_active_entries():
    """Return currently active entries (not expired)."""
    log_file = Path(".devsync/activity-log.json")
    if not log_file.exists():
        return []
```

**After:**
```python
def get_active_entries(tenant_id: Optional[str] = None):
    """Return currently active entries for a tenant (not expired)."""
    if not MULTITENANCY_ENABLED:
        tenant_id = None  # Use legacy path
    
    log_file = get_tenant_log_path(tenant_id)
    if not log_file.exists():
        return []
```

### Change 1.4: Update clear_log() to be tenant-aware

**Location:** clear_log() function

**Before:**
```python
def clear_log():
    """Clear the activity log (for testing)."""
    log_file = Path(".devsync/activity-log.json")
    log_file.unlink(missing_ok=True)
```

**After:**
```python
def clear_log(tenant_id: Optional[str] = None):
    """Clear the activity log for a tenant (for testing)."""
    log_file = get_tenant_log_path(tenant_id)
    log_file.unlink(missing_ok=True)
    
    # Also clean up empty tenant directory
    if MULTITENANCY_ENABLED and tenant_id:
        tenant_dir = Path(f".devsync/tenants/{tenant_id}")
        if tenant_dir.exists() and not any(tenant_dir.iterdir()):
            tenant_dir.rmdir()
```

---

## File 2: core/pre_gen_check.py

### Change 2.1: Update check_for_conflicts() to be tenant-aware

**Location:** check_for_conflicts() function

**Before:**
```python
def check_for_conflicts(agent_id: str, file_path: str, 
                       intent: str, region: str = None):
    """Check for conflicts with other active work."""
    active = get_active_entries()
```

**After:**
```python
def check_for_conflicts(agent_id: str, file_path: str, 
                       intent: str, region: str = None,
                       tenant_id: Optional[str] = None):
    """Check for conflicts with other active work (tenant-isolated)."""
    from core.activity_log import DEFAULT_TENANT_ID
    
    resolved_tenant = tenant_id or DEFAULT_TENANT_ID
    active = get_active_entries(tenant_id=resolved_tenant)
    
    # Filter to only same-tenant entries
    active = [e for e in active if e.get("tenant_id", "default") == resolved_tenant]
```

### Change 2.2: Update handle_conflict_response() signature

**Location:** handle_conflict_response() function

**Before:**
```python
def handle_conflict_response(risk: RiskLevel, agent_id: str, 
                            file_path: str) -> dict:
    """Handle agent's response to conflict gate."""
```

**After:**
```python
def handle_conflict_response(risk: RiskLevel, agent_id: str, 
                            file_path: str, tenant_id: Optional[str] = None) -> dict:
    """Handle agent's response to conflict gate (tenant-isolated)."""
```

---

## File 3: core/mcp_server.py

### Change 3.1: Add tenant resolution helper at top of file

**Location:** After imports, before server initialization

```python
from typing import Optional
import os

# Multitenancy support
MULTITENANCY_ENABLED = os.getenv("NEO_MULTITENANCY", "false").lower() == "true"
DEFAULT_TENANT_ID = os.getenv("CLAUDE_TENANT_ID", "default")

def resolve_tenant_context(tenant_id: Optional[str] = None) -> str:
    """Resolve tenant context from parameter or environment."""
    if tenant_id:
        return tenant_id
    
    tenant = DEFAULT_TENANT_ID
    if not MULTITENANCY_ENABLED and tenant != "default":
        print(f"Warning: CLAUDE_TENANT_ID set but NEO_MULTITENANCY=false. "
              f"Using single-tenant mode.")
    return tenant

def validate_tenant_id(tenant_id: str) -> bool:
    """Validate tenant ID format."""
    if not tenant_id:
        return False
    
    import re
    # Allow alphanumeric, hyphens, underscores; 3-64 chars
    return bool(re.match(r"^[a-z0-9_-]{3,64}$", tenant_id, re.IGNORECASE))
```

### Change 3.2: Update list_resources() to include tenant-aware URIs

**Location:** list_resources() function

**Before:**
```python
@server.list_resources()
async def list_resources() -> list[Resource]:
    """List all Neo resources available to clients."""
    resources = [
        Resource(
            uri="neo://activity-log",
            ...
        ),
```

**After:**
```python
@server.list_resources()
async def list_resources() -> list[Resource]:
    """List all Neo resources available to clients."""
    tenant = resolve_tenant_context()
    
    resources = [
        Resource(
            uri=f"neo://tenants/{tenant}/activity-log",
            name="Activity Log",
            description=f"Shared activity log for tenant '{tenant}'",
            mimeType="application/json",
        ),
        Resource(
            uri=f"neo://tenants/{tenant}/active-entries",
            name="Active Entries",
            description=f"Currently active work for tenant '{tenant}' (30 min expiry)",
            mimeType="application/json",
        ),
        Resource(
            uri=f"neo://tenants/{tenant}/conflict-status",
            name="Conflict Status",
            description=f"Conflict detection metrics for tenant '{tenant}'",
            mimeType="application/json",
        ),
    ]
    
    return resources
```

### Change 3.3: Update read_resource() to be tenant-aware

**Location:** read_resource() function

**Before:**
```python
@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read resource content by URI."""
    if uri == "neo://activity-log":
        log_content = read_log()
```

**After:**
```python
@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read resource content by URI (tenant-isolated)."""
    tenant = resolve_tenant_context()
    
    if uri == f"neo://tenants/{tenant}/activity-log":
        log_content = read_log()
```

### Change 3.4: Update neo_log_activity() MCP tool

**Location:** Tool handler definition in list_tools()

**Add to inputSchema:**
```python
"tenant_id": {
    "type": "string",
    "description": "Tenant ID (company). Defaults to CLAUDE_TENANT_ID env var",
    "default": os.getenv("CLAUDE_TENANT_ID", "default"),
}
```

**Update tool handler:**
```python
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[ToolResult]:
    """Call a Neo coordination tool (tenant-isolated)."""
    
    if name == "neo_log_activity":
        tenant_id = arguments.get("tenant_id", DEFAULT_TENANT_ID)
        
        if not validate_tenant_id(tenant_id):
            return [ToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Invalid tenant ID format: '{tenant_id}'"
                )],
                is_error=True
            )]
        
        try:
            log_activity(
                agent_id=arguments["agent_id"],
                file_path=arguments["file_path"],
                intent=arguments["intent"],
                region=arguments.get("region"),
                intent_category=arguments.get("intent_category", "other"),
                tenant_id=tenant_id
            )
            
            return [ToolResult(
                content=[TextContent(
                    type="text",
                    text=f"✓ Intent logged for tenant '{tenant_id}'. "
                         f"Agent '{arguments['agent_id']}' can now generate code."
                )]
            )]
        except Exception as e:
            return [ToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Error logging activity: {str(e)}"
                )],
                is_error=True
            )]
```

### Change 3.5: Update neo_check_conflicts() MCP tool

**Location:** Tool handler in call_tool()

**Before:**
```python
elif name == "neo_check_conflicts":
    risk, message = check_for_conflicts(
        agent_id=arguments["agent_id"],
        file_path=arguments["file_path"],
        intent=arguments["intent"],
        region=arguments.get("region")
    )
```

**After:**
```python
elif name == "neo_check_conflicts":
    tenant_id = arguments.get("tenant_id", DEFAULT_TENANT_ID)
    
    if not validate_tenant_id(tenant_id):
        return [ToolResult(
            content=[TextContent(
                type="text",
                text=f"Invalid tenant ID format: '{tenant_id}'"
            )],
            is_error=True
        )]
    
    risk, message = check_for_conflicts(
        agent_id=arguments["agent_id"],
        file_path=arguments["file_path"],
        intent=arguments["intent"],
        region=arguments.get("region"),
        tenant_id=tenant_id
    )
```

### Change 3.6: Update neo_get_active_entries() MCP tool

```python
elif name == "neo_get_active_entries":
    tenant_id = arguments.get("tenant_id", DEFAULT_TENANT_ID)
    
    if not validate_tenant_id(tenant_id):
        return [ToolResult(
            content=[TextContent(
                type="text",
                text=f"Invalid tenant ID format: '{tenant_id}'"
            )],
            is_error=True
        )]
    
    entries = get_active_entries(tenant_id=tenant_id)
    return [ToolResult(
        content=[TextContent(
            type="text",
            text=json.dumps(entries, indent=2)
        )]
    )]
```

### Change 3.7: Update neo_clear_log() MCP tool

```python
elif name == "neo_clear_log":
    tenant_id = arguments.get("tenant_id", DEFAULT_TENANT_ID)
    
    if not validate_tenant_id(tenant_id):
        return [ToolResult(
            content=[TextContent(
                type="text",
                text=f"Invalid tenant ID format: '{tenant_id}'"
            )],
            is_error=True
        )]
    
    clear_log(tenant_id=tenant_id)
    return [ToolResult(
        content=[TextContent(
            type="text",
            text=f"✓ Activity log cleared for tenant '{tenant_id}'"
        )]
    )]
```

---

## File 4: Update MCP_SETUP.md

### Change 4.1: Add multitenancy configuration example

**Add new section after "Basic Setup":**

```markdown
## Multitenancy Setup (Enterprise)

For companies using Neo on shared infrastructure:

```bash
# Set both multitenancy mode and tenant identifier
export NEO_MULTITENANCY=true
export CLAUDE_TENANT_ID=acme-corp

python3 -m core.mcp_server
```

### Multiple Companies (Same Repository)

```bash
# Company A
export NEO_MULTITENANCY=true
export CLAUDE_TENANT_ID=acme-corp
python3 -m core.mcp_server  # Uses .devsync/tenants/acme-corp/

# Company B (different terminal/container)
export NEO_MULTITENANCY=true
export CLAUDE_TENANT_ID=startup-ai-lab
python3 -m core.mcp_server  # Uses .devsync/tenants/startup-ai-lab/

# Result: Complete context isolation ✓
```

### Kubernetes Deployment

```yaml
env:
  - name: CLAUDE_TENANT_ID
    valueFrom:
      fieldRef:
        fieldPath: metadata.namespace
  - name: NEO_MULTITENANCY
    value: "true"
```

### Verification

```bash
# Verify tenant isolation
python3 -c "
from core.activity_log import get_active_entries
import os

os.environ['NEO_MULTITENANCY'] = 'true'
os.environ['CLAUDE_TENANT_ID'] = 'acme-corp'

entries = get_active_entries()
print(f'Acme entries: {len(entries)}')
print(f'All entries belong to acme-corp: {all(e.get(\"tenant_id\") == \"acme-corp\" for e in entries)}')
"
```
```

---

## Testing Strategy

### Unit Tests: tests/test_multitenancy.py

```python
import pytest
from core.activity_log import (
    log_activity, get_active_entries, get_tenant_log_path,
    ensure_tenant_isolation
)
from core.pre_gen_check import check_for_conflicts
from pathlib import Path
import os

@pytest.fixture(autouse=True)
def enable_multitenancy(monkeypatch):
    monkeypatch.setenv("NEO_MULTITENANCY", "true")

def test_tenant_log_isolation():
    """Verify activity logs are isolated per tenant."""
    # Company A logs intent
    log_activity("claude-a", "src/auth.py", "Add OAuth", tenant_id="company-a")
    
    # Company B logs intent
    log_activity("claude-b", "src/auth.py", "Add SAML", tenant_id="company-b")
    
    # Verify Company A only sees its entries
    entries_a = get_active_entries(tenant_id="company-a")
    assert len(entries_a) == 1
    assert entries_a[0]["developer_id"] == "claude-a"
    
    # Verify Company B only sees its entries
    entries_b = get_active_entries(tenant_id="company-b")
    assert len(entries_b) == 1
    assert entries_b[0]["developer_id"] == "claude-b"
    
    # Verify no cross-contamination
    assert entries_a != entries_b

def test_conflict_check_tenant_isolation():
    """Verify conflict checks don't cross tenant boundaries."""
    # Company A: Agent working on auth.py
    log_activity("alice", "src/auth.py", "Add OAuth", 
                 region="authenticate_user", tenant_id="company-a")
    
    # Company B: Same file, same region (should NOT conflict)
    risk_b, msg_b = check_for_conflicts(
        "bob", "src/auth.py", "Add SAML", 
        region="authenticate_user", tenant_id="company-b"
    )
    assert risk_b.value == "LOW"  # No conflict across tenants
    
    # Company A: Same file, different agent (SHOULD conflict)
    risk_a, msg_a = check_for_conflicts(
        "alice-2", "src/auth.py", "Refactor auth", 
        region="authenticate_user", tenant_id="company-a"
    )
    assert risk_a.value == "MEDIUM"  # Conflict within same tenant

def test_invalid_tenant_id():
    """Verify invalid tenant IDs are rejected."""
    from core.mcp_server import validate_tenant_id
    
    assert not validate_tenant_id("")
    assert not validate_tenant_id("ab")  # Too short
    assert not validate_tenant_id("AB" * 33)  # Too long
    assert not validate_tenant_id("my company")  # Spaces
    assert validate_tenant_id("my-company")
    assert validate_tenant_id("MY_COMPANY_123")
```

---

## Rollout Plan

### Phase 1: Code Changes (3 days)
- [ ] Update core/activity_log.py with tenant path functions
- [ ] Update core/pre_gen_check.py with tenant filtering
- [ ] Update core/mcp_server.py with tenant-aware tools
- [ ] Add comprehensive unit tests

### Phase 2: Testing (2 days)
- [ ] Run full test suite
- [ ] Test 3+ concurrent companies in multitenancy mode
- [ ] Verify backward compatibility (MULTITENANCY=false)
- [ ] Performance testing (no overhead)

### Phase 3: Documentation (1 day)
- [ ] Update MCP_SETUP.md with examples
- [ ] Create runbook for ops/SREs
- [ ] Add troubleshooting guide

### Phase 4: Release (1 day)
- [ ] Merge to mcp-enablement branch
- [ ] Tag version (e.g., v0.1.0-multitenancy)
- [ ] Announce in docs

**Total: ~1 week implementation**

---

## Backward Compatibility

When `NEO_MULTITENANCY=false` (or unset):
- All tools work as before
- Uses `.devsync/activity-log.json` (single file)
- No tenant_id parameter required
- No performance impact

When migrating to multitenancy:
```bash
python3 -m core.migrate_to_multitenancy \
  --old-log .devsync/activity-log.json \
  --tenant-id my-company
# Moves entries to .devsync/tenants/my-company/activity-log.json
```

---

## Validation Checklist

- [ ] No cross-tenant data leakage in tests
- [ ] Tenant validation on all MCP tool inputs
- [ ] Activity log directories properly isolated
- [ ] Conflict checks only see same-tenant entries
- [ ] Performance overhead < 1%
- [ ] Backward compatibility verified
- [ ] Documentation complete
- [ ] Security audit passed
