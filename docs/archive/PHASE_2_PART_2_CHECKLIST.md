# Neo Phase 2, Part 2: MCP Server Enhancement

**Status**: Ready to start  
**Timeline**: 1.5 hours  
**Branch**: claude/zealous-thompson-zvdoyf  

---

## Overview

Update the MCP server to use cloud-based activity log instead of file-based storage. This enables IDE integration with persistent, multi-team coordination.

**Current State**: MCP server works with file storage  
**Target State**: MCP server reads/writes from cloud (Supabase) with fallback to file

---

## Tasks

### Task 1: Update MCP Server to Use Adapter
**File**: `ide/mcp_neo_server.py`

**Changes**:
- Replace direct `activity_log` imports with `ActivityLogAdapter`
- Update `check_for_conflicts_handler` to use adapter
- Update `log_activity_handler` to use adapter
- Update `get_active_work_handler` to use adapter
- Ensure cloud errors gracefully fall back to file storage

**Code Pattern**:
```python
# Before
from core.activity_log import read_log, log_activity

# After
from core.activity_log_adapter import ActivityLogAdapter

# Usage
entries = ActivityLogAdapter.read_log(tenant_id=tenant_id)
ActivityLogAdapter.append_entry(entry, tenant_id=tenant_id)
```

---

### Task 2: Add Cloud Error Handling
**File**: `ide/mcp_neo_server.py`

**Implement**:
- Try cloud backend first
- On connection error, log warning and fall back to file
- Return informative error messages to IDE
- Include retry logic for transient failures

**Code Pattern**:
```python
try:
    entries = ActivityLogAdapter.read_log(tenant_id)
except Exception as e:
    logger.warning(f"Cloud read failed, falling back to file: {e}")
    # Fallback happens automatically (FileBackend)
    entries = ActivityLogAdapter.read_log(tenant_id)
```

---

### Task 3: Add Request Authentication
**File**: `ide/mcp_neo_server.py`

**Implement**:
- Extract tenant_id from request headers or tool input
- Validate tenant_id format (alphanumeric + hyphens)
- Isolate activities per tenant
- Return 403 if tenant_id invalid

**Code Pattern**:
```python
# From tool input
def check_for_conflicts_handler(input_data):
    tenant_id = input_data.get("tenant_id", DEFAULT_TENANT_ID)
    if not _validate_tenant_id(tenant_id):
        return {"error": "Invalid tenant_id"}
    # Use tenant_id for isolation
    return check_for_conflicts(..., tenant_id=tenant_id)
```

---

### Task 4: Add Rate Limiting
**File**: `ide/mcp_neo_server.py`

**Implement**:
- Track request count per tenant per minute
- Use dict or deque to store timestamps
- Return 429 if limit exceeded (100 requests/min default)
- Log rate limit violations

**Code Pattern**:
```python
class RateLimiter:
    def __init__(self, requests_per_minute=100):
        self.limit = requests_per_minute
        self.requests = defaultdict(deque)  # tenant_id -> deque of timestamps
    
    def is_allowed(self, tenant_id: str) -> bool:
        now = time.time()
        # Remove old timestamps
        while self.requests[tenant_id] and self.requests[tenant_id][0] < now - 60:
            self.requests[tenant_id].popleft()
        
        if len(self.requests[tenant_id]) >= self.limit:
            return False
        
        self.requests[tenant_id].append(now)
        return True
```

---

### Task 5: Test Cloud Integration
**File**: `tests/test_mcp_cloud_integration.py` (NEW)

**Test Scenarios**:
1. MCP server reads from file backend (default)
2. MCP server reads from Supabase (if configured)
3. Cloud connection failure → graceful fallback to file
4. Invalid tenant_id → 403 error
5. Rate limit exceeded → 429 error
6. Multiple tenants isolated

**Test Script**:
```python
def test_mcp_with_file_backend()
def test_mcp_with_supabase_backend()
def test_mcp_cloud_fallback()
def test_mcp_tenant_isolation()
def test_mcp_rate_limiting()
def test_mcp_error_handling()
```

---

## Implementation Checklist

### Step 1: Update MCP Server
- [ ] Add `ActivityLogAdapter` import
- [ ] Update all `read_log` calls
- [ ] Update all `log_activity` calls
- [ ] Add error handling with fallback

### Step 2: Add Authentication
- [ ] Extract tenant_id from requests
- [ ] Validate tenant_id format
- [ ] Return error on invalid tenant
- [ ] Document tenant_id requirements

### Step 3: Add Rate Limiting
- [ ] Implement RateLimiter class
- [ ] Check rate limit on each request
- [ ] Return 429 on limit exceeded
- [ ] Log violations with tenant_id

### Step 4: Test Everything
- [ ] Run MCP cloud integration tests
- [ ] Run all Phase 1 tests (backward compatibility)
- [ ] Manual testing with IDE (if available)
- [ ] Document cloud connectivity status

### Step 5: Document Changes
- [ ] Update ide/README.md
- [ ] Update CLAUDE.md MCP configuration
- [ ] Add troubleshooting guide
- [ ] Document rate limiting

---

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `ide/mcp_neo_server.py` | Modify | Use ActivityLogAdapter, add auth/rate limiting |
| `tests/test_mcp_cloud_integration.py` | Create | Test MCP with cloud backend |
| `ide/README.md` | Modify | Document cloud mode |
| `CLAUDE.md` | Modify | Update MCP configuration |
| `.env.example` | Already done | Configuration template |

---

## Success Criteria

After Part 2 completion:

- [ ] MCP server uses ActivityLogAdapter
- [ ] File backend is default (backward compatible)
- [ ] Supabase backend available (if ACTIVITY_LOG_MODE=supabase)
- [ ] Cloud errors gracefully fall back to file
- [ ] Tenant_id extracted and validated
- [ ] Rate limiting active (100 req/min default)
- [ ] All Phase 1 tests still pass
- [ ] New MCP tests pass
- [ ] Documentation complete

---

## Expected Outcome

When complete, Neo's MCP server will:

1. **Support Both Backends**
   - Uses `ActivityLogAdapter` to switch backends
   - File for testing, Supabase for production
   - Graceful fallback if cloud unavailable

2. **Handle Multi-Team Coordination**
   - Extract tenant_id from requests
   - Isolate activities per tenant
   - Prevent cross-team data leakage

3. **Prevent Abuse**
   - Rate limit per tenant (100 req/min)
   - Return meaningful error codes
   - Log suspicious activity

4. **Maintain Reliability**
   - Cloud failures don't break system
   - Automatic fallback to file storage
   - Clear error messages for debugging

---

## Estimated Time: 1.5 hours

- Update MCP server: 45 minutes
- Add tests: 30 minutes
- Documentation: 15 minutes

**Total**: ~1.5 hours (1 hour 30 minutes)

---

## Related Files

- `core/activity_log_adapter.py` - Adapter pattern (already done)
- `.env.example` - Configuration (already done)
- `docs/SUPABASE_SETUP.md` - Cloud setup (already done)
- `docs/PHASE_2_ROADMAP.md` - Full roadmap

---

## Next Steps After Part 2

1. **Part 3**: IDE integration (pre-generation conflict checks)
2. **Part 4**: Multi-team support (team isolation in database)
3. **Deployment**: Launch Phase 2 to production

---

**Ready to begin Part 2. Start with Task 1: Update MCP Server.**
