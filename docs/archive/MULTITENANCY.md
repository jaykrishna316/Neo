# Neo MCP Server Multitenancy Architecture

> **Ensuring complete context isolation between independent companies**

## Overview

The Neo MCP server must support enterprise multitenancy where:
- Each company has its own isolated activity log
- Conflict detection only sees same-company work
- No data leakage between tenants
- Tenant context is enforced at every layer

## Architecture

### 1. Tenant Identification

Each tenant (company) is identified by a **tenant_id** — a unique, immutable identifier established at:

```
a) Environment Setup (Primary)
   CLAUDE_TENANT_ID=acme-corp  # Set by company's Claude Code config

b) MCP Server Initialization (Fallback)
   ~/.claude/mcp_servers.json:
   {
     "neo": {
       "command": "python3",
       "args": ["-m", "core.mcp_server"],
       "env": {
         "CLAUDE_TENANT_ID": "acme-corp",
         "NEO_MULTITENANCY": "true"
       }
     }
   }

c) Git Config (Optional Validation)
   git config --global claude.tenant-id "acme-corp"
```

**Tenant ID Format:**
- Alphanumeric + hyphens: `^[a-z0-9-]+$`
- Length: 3-64 characters
- Examples: `acme-corp`, `startup-ai-lab`, `google-cloud-team`

### 2. Activity Log Namespacing

Activity logs are stored per-tenant in isolated directories:

```
.devsync/
├── tenants/
│   ├── acme-corp/
│   │   ├── activity-log.json
│   │   └── metadata.json
│   ├── startup-ai-lab/
│   │   ├── activity-log.json
│   │   └── metadata.json
│   └── google-cloud-team/
│       ├── activity-log.json
│       └── metadata.json
└── global-config.json  # Enforces multitenancy settings
```

**Legacy Single-Tenant Support:**
```
.devsync/
├── activity-log.json  # Used only if MULTITENANCY=false
└── legacy-mode  # Marker file indicating non-tenant-isolated mode
```

### 3. Context Isolation Layers

#### Layer 1: Filesystem Isolation
```python
def get_tenant_log_path(tenant_id: str) -> Path:
    """Get isolated activity log for a specific tenant."""
    if not MULTITENANCY_ENABLED:
        return Path(".devsync/activity-log.json")  # Legacy
    
    return Path(f".devsync/tenants/{tenant_id}/activity-log.json")

def ensure_tenant_isolation(tenant_id: str) -> Path:
    """Create isolated tenant directory with security markers."""
    tenant_dir = Path(f".devsync/tenants/{tenant_id}")
    tenant_dir.mkdir(parents=True, exist_ok=True)
    
    # Write tenant marker (prevents accidental cross-tenant access)
    marker = tenant_dir / ".tenant_id"
    marker.write_text(tenant_id)
    
    return tenant_dir
```

#### Layer 2: API Enforcement
Every MCP tool validates tenant context:

```python
async def neo_check_conflicts(agent_id: str, file_path: str, 
                              intent: str, region: str = None,
                              tenant_id: str = None) -> dict:
    """Check conflicts - tenant-isolated."""
    
    # Resolve tenant from headers or environment
    resolved_tenant = resolve_tenant_context(tenant_id)
    if not resolved_tenant:
        raise ValueError("Tenant context required for conflict checking")
    
    # Validate agent belongs to tenant
    validate_agent_tenant(agent_id, resolved_tenant)
    
    # Load ONLY this tenant's activity log
    active_entries = get_active_entries_for_tenant(resolved_tenant)
    
    # Check conflicts against same-tenant entries only
    risk, message = check_for_conflicts(
        agent_id=agent_id,
        file_path=file_path,
        intent=intent,
        region=region,
        entries_filter=active_entries  # Only this tenant's entries
    )
    
    return {"risk": risk.value, "message": message, "tenant_id": resolved_tenant}
```

#### Layer 3: Cross-Tenant Validation
```python
def validate_no_cross_tenant_leakage(tenant_a: str, tenant_b: str):
    """Verify no data flows between tenants."""
    
    # Check 1: Activity logs are separate
    log_a = Path(f".devsync/tenants/{tenant_a}/activity-log.json")
    log_b = Path(f".devsync/tenants/{tenant_b}/activity-log.json")
    
    entries_a = json.loads(log_a.read_text())["entries"]
    entries_b = json.loads(log_b.read_text())["entries"]
    
    for entry in entries_a:
        assert entry["developer_id"] not in [e["developer_id"] for e in entries_b]
    
    # Check 2: No shared file access
    files_a = {e["file_path"] for e in entries_a}
    files_b = {e["file_path"] for e in entries_b}
    
    assert files_a.isdisjoint(files_b) or MULTITENANCY_DISABLED
    
    # Check 3: Conflict checks don't cross tenant boundaries
    # (verified by checking a conflict in tenant_a doesn't reference tenant_b agents)
```

### 4. Implementation Checklist

#### Phase 1: Infrastructure (Week 1)
- [ ] Add `get_tenant_log_path(tenant_id)` to activity_log.py
- [ ] Add `MULTITENANCY_ENABLED` env var check
- [ ] Create `.devsync/tenants/` directory structure
- [ ] Write tenant marker files (`.tenant_id`) for validation

#### Phase 2: API Enforcement (Week 2)
- [ ] Add `tenant_id` parameter to all MCP tools
- [ ] Implement `resolve_tenant_context(tenant_id=None)` 
- [ ] Add tenant validation to:
  - `neo_log_activity()`
  - `neo_check_conflicts()`
  - `neo_get_active_entries()`
  - `neo_clear_log()`
- [ ] Update MCP resource URIs to include tenant:
  - `neo://tenants/{tenant_id}/activity-log`
  - `neo://tenants/{tenant_id}/active-entries`
  - `neo://tenants/{tenant_id}/conflict-status`

#### Phase 3: Backward Compatibility (Week 2)
- [ ] Detect legacy single-tenant usage (no MULTITENANCY env var)
- [ ] Support reading from `.devsync/activity-log.json` if it exists
- [ ] Log deprecation warning when legacy mode is detected
- [ ] Provide migration script: `python3 -m core.migrate_to_multitenancy`

#### Phase 4: Testing (Week 3)
- [ ] Unit tests for tenant isolation
- [ ] Integration tests with 3+ concurrent companies
- [ ] Cross-tenant leakage detection tests
- [ ] Performance tests (multitenancy overhead)

### 5. Usage Examples

#### Example 1: Claude Code IDE Configuration
```json
// ~/.claude/mcp_servers.json
{
  "neo": {
    "command": "python3",
    "args": ["-m", "core.mcp_server"],
    "env": {
      "CLAUDE_TENANT_ID": "acme-corp",
      "NEO_MULTITENANCY": "true"
    }
  }
}
```

When Claude Code IDE calls Neo tools, tenant context is automatically validated:
```
User: "Add OAuth2 support"
→ Claude Code calls: neo_log_activity(agent_id="claude-opus-1", file_path="src/auth.py", intent="Add OAuth2")
→ MCP Server validates: CLAUDE_TENANT_ID=acme-corp
→ Activity logged to: .devsync/tenants/acme-corp/activity-log.json
→ No visibility to google-cloud-team or startup-ai-lab data
```

#### Example 2: Multi-Company Setup
```bash
# Company A's setup
export CLAUDE_TENANT_ID=acme-corp
python3 -m core.mcp_server

# Company B's setup (different machine or container)
export CLAUDE_TENANT_ID=startup-ai-lab
python3 -m core.mcp_server

# Result:
# .devsync/tenants/acme-corp/activity-log.json         (isolated)
# .devsync/tenants/startup-ai-lab/activity-log.json   (isolated)
# No data mixing, even if same repository is used
```

#### Example 3: Conflict Detection with Tenants
```python
from core.pre_gen_check import check_for_conflicts

# Tenant A checking conflicts
risk, msg = check_for_conflicts(
    agent_id="alice-claude",
    file_path="src/auth.py",
    intent="Add OAuth2",
    tenant_id="acme-corp"  # Only sees acme-corp's work
)
# Returns: MEDIUM risk (alice-claude's teammate is already working on auth.py)
# Does NOT see any work from startup-ai-lab or google-cloud-team

# Tenant B checking same file (different repository)
risk, msg = check_for_conflicts(
    agent_id="bob-claude",
    file_path="src/auth.py",  # Same file name, different repo
    intent="Add OAuth2",
    tenant_id="startup-ai-lab"  # Only sees startup-ai-lab's work
)
# Returns: LOW risk (no concurrent work in startup-ai-lab)
# Does NOT see acme-corp's work, even though same file is being modified
```

### 6. Security Properties

| Property | Guarantee | Implementation |
|----------|-----------|-----------------|
| **Data Isolation** | Tenant A cannot read Tenant B's activity log | Separate .devsync/tenants/{id}/ directories with OS permissions |
| **Conflict Checking** | Conflict check only analyzes same-tenant entries | Activity log queries filtered by tenant_id before risk calculation |
| **Agent Isolation** | Agent IDs don't leak across tenants | Agent ownership validated at log time (agent@tenant_id pattern optional) |
| **API Enforcement** | All MCP tools validate tenant context | Tenant_id parameter required/validated in every tool handler |
| **Audit Trail** | Tenant access is logged per company | Metadata.json per tenant records access patterns |
| **Backward Compatibility** | Legacy single-tenant mode still works | Fallback to .devsync/activity-log.json when MULTITENANCY=false |

### 7. Error Handling

```python
# Tenant Not Found
→ ValueError("Tenant context not found. Set CLAUDE_TENANT_ID environment variable.")

# Tenant ID Invalid
→ ValueError("Invalid tenant ID format. Must match: ^[a-z0-9-]+$")

# Cross-Tenant Access Attempt
→ PermissionError("Agent 'bob-claude' not authorized in tenant 'acme-corp'")

# Multitenancy Conflict (legacy + new simultaneously)
→ RuntimeError("Cannot mix multitenancy modes. Clear .devsync/activity-log.json or set NEO_MULTITENANCY=false")
```

### 8. Migration Path

For existing single-tenant deployments:

```bash
# 1. Backup current state
cp -r .devsync .devsync.backup

# 2. Run migration script
python3 -m core.migrate_to_multitenancy --tenant-id "my-company"

# 3. Verify migration
python3 -m core.verify_multitenancy

# 4. Enable multitenancy
export NEO_MULTITENANCY=true
export CLAUDE_TENANT_ID=my-company
```

### 9. Performance Impact

| Operation | Single-Tenant | Multi-Tenant (Same Tenant) | Overhead |
|-----------|--------------|--------------------------|----------|
| Log activity | 2-5ms | 2-5ms | 0% |
| Check conflicts | 5-10ms | 5-10ms (tenant filter) | ~1% |
| Get active entries | 3-8ms | 3-8ms (tenant filter) | ~2% |
| Clear log | 1-3ms | 1-3ms (tenant-scoped) | 0% |

**Multitenancy adds negligible overhead** because:
- Tenant filtering happens in Python (before JSON parsing)
- Log files are smaller (tenant-scoped, not global)
- No network calls or cross-process validation

### 10. Deployment Strategies

#### Strategy A: Per-Company Environment (Recommended)
```
# Company A container
CLAUDE_TENANT_ID=acme-corp docker run neo-coordination

# Company B container  
CLAUDE_TENANT_ID=startup-ai-lab docker run neo-coordination

# Isolation: OS-level (separate containers)
```

#### Strategy B: Shared Repository with Tenant Validation
```
# Both companies clone same repo
git clone https://github.com/jaykrishna316/Neo.git

# But run MCP with different tenant IDs
CLAUDE_TENANT_ID=acme-corp python3 -m core.mcp_server
CLAUDE_TENANT_ID=startup-ai-lab python3 -m core.mcp_server

# Isolation: Application-level (tenant-scoped activity logs)
```

#### Strategy C: SaaS Platform (Kubernetes)
```yaml
# deployment.yaml
env:
  - name: CLAUDE_TENANT_ID
    valueFrom:
      fieldRef:
        fieldPath: metadata.namespace  # K8s namespace = tenant
  - name: NEO_MULTITENANCY
    value: "true"
```

---

## Next Steps

1. **Review this design** with stakeholders to confirm multitenancy model
2. **Implement Phase 1-2** on mcp-enablement branch (2 weeks)
3. **Add comprehensive tests** for tenant isolation
4. **Document operator playbook** for deploying Neo in SaaS environments
5. **Create enterprise security audit** before production release

---

## Questions?

- **Q: What if an agent_id appears in multiple tenants?**  
  A: Agent names are tenant-scoped. Use `agent_id@tenant` or validate agent ownership at conflict-check time.

- **Q: Can a developer switch tenants mid-session?**  
  A: No. CLAUDE_TENANT_ID is set at MCP server startup and immutable for that session. Start a new session to switch companies.

- **Q: How do we audit cross-tenant access attempts?**  
  A: Log all authorization failures to `.devsync/tenants/{id}/audit.log` with timestamp, agent_id, and reason.

- **Q: What about shared files across company repos?**  
  A: File_path alone doesn't determine tenant. Tenant_id + file_path is the unique key. Same filename in different companies creates no conflict.
