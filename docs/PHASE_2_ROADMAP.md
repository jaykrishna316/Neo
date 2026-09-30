# Neo Phase 2: Cloud Deployment & IDE Integration Roadmap

**Status**: Ready to start (Phase 1 ✅ COMPLETE)  
**Timeline**: 5-6 hours  
**Target**: Supabase or MongoDB + MCP IDE Integration  

---

## Overview

Phase 2 scales Neo from local file-based coordination to cloud-hosted with real IDE integration. Developers on separate machines coordinate through a persistent cloud activity log instead of a local file.

**Phase 1 Validated**: File-based coordination works. Zero conflicts with 3 developers.  
**Phase 2 Goal**: Move coordination to cloud with IDE integration.  

---

## What Phase 2 Delivers

✅ **Cloud-hosted Activity Log** (Supabase or MongoDB)  
✅ **MCP Server Integration** with Claude Code IDE  
✅ **Multi-team Support** (isolated activity logs per team)  
✅ **Real-time Notifications** (developers alerted when conflicts detected)  
✅ **IDE Pre-generation Checks** (block risky generations before they start)  

---

## Phase 2 Breakdown

### Part 1: Database Migration (2 hours)

**Current State**: Activity log in `.devsync/activity-log.json` (file-based)  
**Target State**: Activity log in Supabase or MongoDB (cloud-based)

**Tasks**:
1. Choose cloud provider (Supabase or MongoDB Atlas)
2. Create activity_log schema in cloud database
3. Update `core/activity_log.py` to read/write to cloud instead of file
4. Implement connection pooling and retry logic
5. Add configuration for local vs cloud mode
6. Test cloud connection with existing tests (should still pass)

**Deliverables**:
- `core/activity_log_cloud.py` (cloud-based implementation)
- `.env.example` (configuration template)
- Connection tests passing

---

### Part 2: MCP Server Enhancement (1.5 hours)

**Current State**: MCP server works locally for IDE testing  
**Target State**: MCP server connects to cloud activity log

**Tasks**:
1. Update `ide/mcp_neo_server.py` to use cloud activity log
2. Add request authentication (IDE identifies as a specific tenant/team)
3. Implement rate limiting (prevent abuse)
4. Add error handling for cloud connectivity issues
5. Test MCP server with cloud activity log

**Deliverables**:
- `ide/mcp_neo_server.py` (updated for cloud)
- Authentication configuration
- Error handling for cloud failures

---

### Part 3: IDE Integration (1.5 hours)

**Current State**: MCP server available, not integrated with IDE  
**Target State**: Claude Code IDE uses Neo before every generation

**Tasks**:
1. Update MCP server configuration in `.claude.md`
2. Test MCP server connection from Claude Code IDE
3. Create IDE plugin/extension that calls `neo_check_conflicts`
4. Display risk assessment in IDE (✅/⚠️/🚫)
5. Block/warn/allow generation based on risk level

**Deliverables**:
- Updated CLAUDE.md (MCP configuration)
- IDE integration guide
- Risk visualization in IDE

---

### Part 4: Multi-Team Support (1 hour)

**Current State**: Single activity log for all developers  
**Target State**: Isolated logs per team (multitenancy)

**Tasks**:
1. Add `team_id` to activity log schema
2. Filter activities by team when checking conflicts
3. Support multiple teams on same database
4. Add team configuration to IDE

**Deliverables**:
- Multitenancy support in cloud implementation
- Team isolation tests

---

## Technology Choices

### Cloud Database: Supabase vs MongoDB

| Feature | Supabase | MongoDB |
|---------|----------|---------|
| **Setup** | Easier (PostgreSQL + Supabase UI) | Requires Atlas account |
| **Cost** | Free tier available | Free tier available |
| **Scalability** | Good (PostgreSQL) | Excellent (MongoDB) |
| **Real-time** | Built-in (PostgreSQL Realtime) | Requires Realm (paid) |
| **Python SDK** | supabase-py | pymongo |

**Recommendation**: Start with Supabase (easier setup), migrate to MongoDB if needed for scale.

---

## Testing Strategy for Phase 2

### Test 1: Cloud Connection
```python
# Verify connection to cloud database
python tests/test_cloud_connection.py
```

Expected: ✅ Connected to cloud database

### Test 2: Cloud Activity Log (Rerun Existing Tests)
```python
# Run with cloud activity log instead of file
ACTIVITY_LOG_MODE=cloud python tests/test_two_developer_coordination.py
ACTIVITY_LOG_MODE=cloud python tests/test_three_developer_coordination.py
ACTIVITY_LOG_MODE=cloud python tests/test_edge_cases.py
```

Expected: ✅ All tests pass with cloud storage

### Test 3: MCP Server with Cloud
```python
# Verify MCP server reads from cloud
python -c "
import asyncio
from ide.mcp_neo_server import test_cloud_integration
asyncio.run(test_cloud_integration())
"
```

Expected: ✅ MCP server connects to cloud activity log

### Test 4: IDE Integration
```
1. Open Claude Code IDE
2. Configure MCP server in .claude.md
3. Reload .claude.md configuration
4. Start generating code
5. Verify Neo conflict check runs before generation
```

Expected: ✅ IDE shows risk assessment before code generation

### Test 5: Multi-Team Isolation
```python
# Verify teams don't see each other's activities
TEAM_ID=team-a python tests/test_multitenancy.py
TEAM_ID=team-b python tests/test_multitenancy.py
```

Expected: ✅ Teams isolated, zero conflicts between teams

---

## Success Criteria

### Part 1: Database Migration
- [ ] Cloud database connection verified
- [ ] Activity log schema created in cloud
- [ ] Read/write operations working
- [ ] Existing tests pass with cloud storage
- [ ] No data loss during migration

### Part 2: MCP Server Enhancement
- [ ] MCP server reads from cloud activity log
- [ ] Authentication working
- [ ] Rate limiting implemented
- [ ] Error handling for cloud failures
- [ ] MCP server tests pass

### Part 3: IDE Integration
- [ ] IDE recognizes MCP server
- [ ] Pre-generation conflict check runs
- [ ] Risk assessment displayed in IDE
- [ ] Developers can allow/block generation
- [ ] Log shows IDE integration working

### Part 4: Multi-Team Support
- [ ] Teams isolated in database
- [ ] Conflict detection works per-team
- [ ] Teams don't see each other's activities
- [ ] Multitenancy tests pass

---

## Timeline Estimate

| Phase | Task | Time | Cumulative |
|-------|------|------|-----------|
| **1** | Choose cloud provider | 30 min | 30 min |
| **1** | Database schema & migration | 60 min | 1.5 hours |
| **1** | Cloud activity log implementation | 30 min | 2 hours |
| **2** | MCP server cloud integration | 60 min | 3 hours |
| **2** | Authentication & rate limiting | 30 min | 3.5 hours |
| **3** | IDE integration setup | 60 min | 4.5 hours |
| **3** | Risk display in IDE | 30 min | 5 hours |
| **4** | Multitenancy support | 60 min | 6 hours |

**Total**: 6 hours (can be done in one session or split across 2-3 sessions)

---

## Dependencies & Blockers

### Before Starting Phase 2
- [ ] Phase 1 tests all pass ✅
- [ ] Decision made on cloud provider (Supabase or MongoDB)
- [ ] Cloud account created and database provisioned
- [ ] `.env` configured with database credentials

### Optional but Helpful
- [ ] Understanding of Neo's semantic coordination model
- [ ] Experience with MCP (Model Context Protocol)
- [ ] Knowledge of Claude Code IDE integration

---

## File Changes Summary

### Files to Create
- `core/activity_log_cloud.py` - Cloud-based activity log
- `tests/test_cloud_connection.py` - Cloud connection tests
- `tests/test_multitenancy.py` - Multitenancy tests
- `.env.example` - Configuration template
- `docs/CLOUD_SETUP.md` - Cloud deployment guide

### Files to Modify
- `core/activity_log.py` - Add cloud mode support
- `ide/mcp_neo_server.py` - Connect to cloud
- `CLAUDE.md` - Update MCP configuration
- `requirements.txt` - Add cloud database SDK

### Files to Keep (No Changes)
- `core/pre_gen_check.py` (conflict detection logic unchanged)
- `core/risk_classifier.py` (risk assessment unchanged)
- `core/lock_manager.py` (lock mechanism unchanged)
- All Phase 1 tests (should still pass)

---

## Risk Mitigation

| Risk | Probability | Mitigation |
|------|------------|-----------|
| Cloud connection fails | Medium | Implement fallback to local file mode |
| Cloud latency affects IDE | Low | Cache recent activities locally, sync periodically |
| Team isolation bugs | Medium | Comprehensive multitenancy tests |
| MCP integration complexity | Medium | Start with simple MCP test, then add IDE |

---

## Next Steps After Phase 2

Once Phase 2 is complete:

1. **Phase 3**: Cross-agent orchestration (Claude + Devin + OpenAI)
2. **Phase 4**: Real multi-developer testing (separate machines)
3. **Phase 5**: Production deployment (security, compliance, scaling)

---

## Getting Help

- **Cloud Setup Questions**: See `docs/CLOUD_SETUP.md` (to be created)
- **MCP Integration Questions**: See `ide/INTEGRATION_GUIDE.md`
- **Multitenancy Questions**: See `docs/MULTITENANCY.md`

---

## Summary

Phase 2 takes Neo from local file-based coordination to cloud-hosted with IDE integration. The foundation (Phase 1) is solid. Phase 2 is about scale and real-world integration.

**Start date**: When ready  
**Estimated duration**: 6 hours  
**Expected outcome**: Neo working in Claude Code IDE with cloud coordination  

Ready to proceed? Create the cloud database and start Part 1.

---

Last updated: 2026-09-30
