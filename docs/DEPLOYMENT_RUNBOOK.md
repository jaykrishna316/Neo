# Neo MCP Multitenancy Deployment Runbook

**For Enterprise Operators | Production-Ready | v1.0**

---

## Overview

This runbook covers deploying Neo's multitenancy layer to production. Each tenant (company) operates in complete isolation—no data leakage, no cross-tenant conflict visibility, no shared activity logs.

### Key Facts
- **Data Isolation**: Tenant-scoped directories (`/devsync/tenants/{tenant_id}/`)
- **Zero Configuration**: Defaults to single-tenant if not enabled
- **Backward Compatible**: Existing single-tenant deployments work unchanged
- **Overhead**: <1% performance impact
- **Rollout**: Can be enabled gradually by tenant

---

## Deployment Strategies

### Strategy 1: Per-Company Containers (Recommended for High-Security)

Each company gets an isolated container with its own environment variables.

```bash
# Container for ACME Corp
docker run \
  -e CLAUDE_TENANT_ID=acme-corp \
  -e NEO_MULTITENANCY=true \
  -v /data/acme-corp:/app/.devsync \
  neo-mcp:latest

# Container for Startup AI Lab
docker run \
  -e CLAUDE_TENANT_ID=startup-ai-lab \
  -e NEO_MULTITENANCY=true \
  -v /data/startup-ai-lab:/app/.devsync \
  neo-mcp:latest
```

**Advantages:**
- OS-level isolation
- Separate resource limits per tenant
- Easier compliance auditing
- Can restart one tenant without affecting others

**Disadvantages:**
- More containers to manage
- Higher resource overhead

---

### Strategy 2: Shared Repo with Tenant Validation (Recommended for Cost)

One container, multiple tenants, app-level isolation.

```bash
docker run \
  -e NEO_MULTITENANCY=true \
  -v /data/shared:/app/.devsync \
  -p 5000:5000 \
  neo-mcp:latest
```

Each Claude Code session sets `CLAUDE_TENANT_ID` before calling the MCP server.

```bash
# Terminal for ACME Corp developer
export CLAUDE_TENANT_ID=acme-corp
export NEO_MULTITENANCY=true
python3 -m core.mcp_server

# Terminal for Startup AI Lab developer
export CLAUDE_TENANT_ID=startup-ai-lab
export NEO_MULTITENANCY=true
python3 -m core.mcp_server
```

**Advantages:**
- Single container
- Minimal resource overhead
- Easy to scale

**Disadvantages:**
- Relies on environment variable configuration
- Requires discipline from operators

---

### Strategy 3: Kubernetes (Enterprise)

Deploy Neo as a multi-tenant service in Kubernetes.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: neo-mcp-server
spec:
  replicas: 3
  selector:
    matchLabels:
      app: neo-mcp
  template:
    metadata:
      labels:
        app: neo-mcp
    spec:
      containers:
      - name: neo-mcp
        image: neo-mcp:latest
        env:
        - name: NEO_MULTITENANCY
          value: "true"
        - name: CLAUDE_TENANT_ID
          valueFrom:
            fieldRef:
              fieldPath: metadata.namespace
        volumeMounts:
        - name: devsync
          mountPath: /.devsync
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
      volumes:
      - name: devsync
        persistentVolumeClaim:
          claimName: neo-devsync
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: neo-devsync
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: nfs
  resources:
    requests:
      storage: 100Gi
---
apiVersion: v1
kind: Service
metadata:
  name: neo-mcp-service
spec:
  selector:
    app: neo-mcp
  ports:
  - protocol: TCP
    port: 5000
    targetPort: 5000
  type: LoadBalancer
```

**Per-Tenant Namespace Deployment:**
```yaml
# Create namespace for ACME Corp
kubectl create namespace acme-corp
kubectl set env deployment/neo-mcp-server \
  -n acme-corp \
  CLAUDE_TENANT_ID=acme-corp

# Create namespace for Startup AI Lab
kubectl create namespace startup-ai-lab
kubectl set env deployment/neo-mcp-server \
  -n startup-ai-lab \
  CLAUDE_TENANT_ID=startup-ai-lab
```

**Advantages:**
- Industry-standard orchestration
- Auto-scaling per tenant
- Health checks and auto-recovery
- Easy multi-region deployment

---

## Pre-Deployment Checklist

- [ ] Verify Python 3.8+
- [ ] Run full test suite: `pytest tests/test_multitenancy_phase*.py -v`
- [ ] Verify performance: `pytest tests/test_multitenancy_phase4.py::TestPerformanceBenchmark -v -s`
- [ ] Backup existing `.devsync/activity-log.json` if migrating
- [ ] Set `NEO_MULTITENANCY=false` initially (backward compatibility)
- [ ] Create tenant directory structure
- [ ] Test with 3+ concurrent tenants
- [ ] Verify no data leakage with isolation validator

---

## Installation & Configuration

### 1. Clone Repository
```bash
git clone https://github.com/jaykrishna316/codeNinja.git
cd codeNinja
git checkout mpc-enablement
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
# Ensure: mcp, pytest, pydantic
```

### 3. Set Environment Variables
```bash
# Enable multitenancy
export NEO_MULTITENANCY=true

# Set default tenant ID (used if not overridden)
export CLAUDE_TENANT_ID=default

# Optional: set log level
export NEO_LOG_LEVEL=INFO
```

### 4. Verify Installation
```bash
# Check syntax
python3 -m py_compile core/mcp_server.py core/activity_log.py core/pre_gen_check.py

# Run unit tests
pytest tests/test_multitenancy_phase1.py -v

# Run integration tests
pytest tests/test_multitenancy_phase4.py::TestConcurrentTenants -v -s

# Run performance tests
pytest tests/test_multitenancy_phase4.py::TestPerformanceBenchmark -v -s
```

### 5. Start MCP Server
```bash
python3 -m core.mcp_server
# Output: Neo MCP Server ready (Listening on stdio)
```

---

## Migration Path (Single-Tenant → Multi-Tenant)

### Phase A: Pre-Migration (Day 1)

1. **Backup existing logs:**
   ```bash
   cp .devsync/activity-log.json .devsync/activity-log.json.backup
   ```

2. **Keep multitenancy disabled (default):**
   ```bash
   export NEO_MULTITENANCY=false
   ```

3. **Verify existing functionality works:**
   ```bash
   pytest tests/test_multitenancy_phase1.py::TestSingleTenantMode -v
   ```

### Phase B: Enable Multitenancy (Day 2-3)

1. **Set environment variables:**
   ```bash
   export NEO_MULTITENANCY=true
   export CLAUDE_TENANT_ID=default
   ```

2. **Migrate legacy data (optional):**
   ```python
   # Script to migrate entries to default tenant
   import json
   from pathlib import Path

   legacy_log = Path(".devsync/activity-log.json.backup")
   entries = json.loads(legacy_log.read_text())
   
   # Add tenant_id field
   for entry in entries:
       entry["tenant_id"] = "default"
   
   new_path = Path(".devsync/tenants/default/activity-log.json")
   new_path.parent.mkdir(parents=True, exist_ok=True)
   new_path.write_text(json.dumps(entries, indent=2))
   ```

3. **Restart MCP server:**
   ```bash
   pkill -f "python3 -m core.mcp_server"
   python3 -m core.mcp_server
   ```

4. **Verify isolation:**
   ```bash
   pytest tests/test_multitenancy_phase1.py::TestMultiTenantMode -v
   ```

### Phase C: Add Tenants (Day 4+)

1. **For each new tenant, create container or session:**
   ```bash
   export CLAUDE_TENANT_ID=acme-corp
   export NEO_MULTITENANCY=true
   python3 -m core.mcp_server
   ```

2. **Verify no data leakage:**
   ```bash
   pytest tests/test_multitenancy_phase4.py::TestConcurrentTenants -v
   ```

3. **Monitor performance:**
   ```bash
   # Check <1% overhead
   pytest tests/test_multitenancy_phase4.py::TestPerformanceBenchmark -v -s
   ```

---

## Production Monitoring

### Key Metrics to Track

```bash
# 1. Tenant directory sizes
du -sh .devsync/tenants/*/

# 2. Active entries per tenant
curl http://localhost:5000/neo/tenants/acme-corp/active-entries

# 3. Conflict detection rate
grep -c "HIGH_RISK" .devsync/tenants/*/audit.log 2>/dev/null || echo "0"

# 4. API call latency (log analysis)
tail -f .devsync/tenants/*/mcp-server.log | grep "ms"
```

### Health Check

```bash
#!/bin/bash
# health_check.sh

TENANT_ID="acme-corp"
LOG_FILE=".devsync/tenants/$TENANT_ID/activity-log.json"

# Check if log file exists and is readable
if [ ! -r "$LOG_FILE" ]; then
  echo "FAIL: Cannot read log for tenant $TENANT_ID"
  exit 1
fi

# Check if log is valid JSON
if ! jq empty "$LOG_FILE" 2>/dev/null; then
  echo "FAIL: Invalid JSON in activity log"
  exit 1
fi

# Check if tenant marker exists
if [ ! -f ".devsync/tenants/$TENANT_ID/.tenant_id" ]; then
  echo "FAIL: Tenant marker missing"
  exit 1
fi

echo "OK: Tenant $TENANT_ID healthy"
exit 0
```

---

## Troubleshooting

### Issue: "Tenant mismatch: Expected X, but directory contains Y"

**Cause:** Tenant marker file was corrupted or manually edited

**Fix:**
```bash
# Verify tenant ID
cat .devsync/tenants/acme-corp/.tenant_id

# Restore if corrupted
echo "acme-corp" > .devsync/tenants/acme-corp/.tenant_id
```

### Issue: Cross-Tenant Data Leakage Detected

**Cause:** Bug in tenant filtering logic

**Verification:**
```python
from core.activity_log import get_active_entries

# Should return empty if no entries exist
entries_a = get_active_entries(tenant_id="acme-corp")
entries_b = get_active_entries(tenant_id="startup-ai-lab")

# Should not overlap
assert not any(e["tenant_id"] == "startup-ai-lab" for e in entries_a)
assert not any(e["tenant_id"] == "acme-corp" for e in entries_b)
```

**Fix:**
1. Verify `NEO_MULTITENANCY=true`
2. Check `CLAUDE_TENANT_ID` is set correctly
3. Run isolation tests: `pytest tests/test_multitenancy_phase1.py::TestTenantFiltering -v`

### Issue: Performance Degradation (>5% overhead)

**Cause:** Too many concurrent tenants or large activity logs

**Fix:**
```bash
# Archive old entries per tenant
find .devsync/tenants -name "activity-log.json" -type f | while read f; do
  # Keep only last 7 days
  python3 scripts/archive_old_entries.py "$f" 7
done

# Monitor performance
pytest tests/test_multitenancy_phase4.py::TestPerformanceBenchmark -v -s
```

### Issue: Tenant Isolation Validator Fails

**Cause:** Partial multitenancy enable (some envs set, others not)

**Fix:**
```bash
# Verify all systems have same settings
env | grep -E "NEO_MULTITENANCY|CLAUDE_TENANT_ID"

# Should show:
# NEO_MULTITENANCY=true
# CLAUDE_TENANT_ID=acme-corp

# Run consistency check
pytest tests/test_multitenancy_phase1.py::TestMultiTenantMode::test_ensure_tenant_isolation_validation -v
```

---

## Security Considerations

### Tenant ID Validation

All tenant IDs are validated against: `^[a-z0-9_-]{1,64}$`

Invalid tenant IDs are rejected:
```bash
# This FAILS:
CLAUDE_TENANT_ID="../../etc/passwd" neo_log_activity

# This SUCCEEDS:
CLAUDE_TENANT_ID="acme-corp-team_1" neo_log_activity
```

### Filesystem Permissions

```bash
# Set restrictive permissions on tenant directories
chmod 700 .devsync/tenants/*/
chmod 600 .devsync/tenants/*/.tenant_id
chmod 600 .devsync/tenants/*/activity-log.json
```

### Audit Logging

Each tenant operation should log to their audit trail:
```bash
# Check audit logs
tail -f .devsync/tenants/acme-corp/audit.log
```

---

## Scaling Considerations

| Scenario | Recommendation |
|----------|-----------------|
| <10 tenants | Single container (Strategy 2) |
| 10-100 tenants | Shared container with load balancer (Strategy 2) |
| 100+ tenants | Per-tenant containers (Strategy 1) or K8s (Strategy 3) |
| High-security requirement | Per-tenant containers with OS isolation (Strategy 1) |
| Multi-region deployment | Kubernetes with federation (Strategy 3) |

---

## Rollback Procedure

If multitenancy causes issues:

```bash
# 1. Stop Neo MCP server
pkill -f "python3 -m core.mcp_server"

# 2. Disable multitenancy
unset NEO_MULTITENANCY
export NEO_MULTITENANCY=false

# 3. Restore backup if needed
cp .devsync/activity-log.json.backup .devsync/activity-log.json

# 4. Restart in single-tenant mode
python3 -m core.mcp_server

# 5. Verify functionality
pytest tests/test_multitenancy_phase1.py::TestSingleTenantMode -v
```

---

## Support & Contact

**For issues with:**
- Deployment: Contact DevOps team
- Tenant configuration: Contact Platform team
- Performance: Contact SRE team
- Security: Contact Security team

**Emergency hotline:** See CLAUDE.md for contacts

---

## Appendix: Sample Tenant Configuration

```bash
#!/bin/bash
# setup_tenant.sh

TENANT_ID=$1

if [ -z "$TENANT_ID" ]; then
  echo "Usage: ./setup_tenant.sh <tenant-id>"
  exit 1
fi

# Create tenant directory
mkdir -p .devsync/tenants/$TENANT_ID

# Initialize activity log
echo "[]" > .devsync/tenants/$TENANT_ID/activity-log.json

# Create tenant marker
echo "$TENANT_ID" > .devsync/tenants/$TENANT_ID/.tenant_id

# Set permissions
chmod 700 .devsync/tenants/$TENANT_ID
chmod 600 .devsync/tenants/$TENANT_ID/.tenant_id

# Log entry
echo "✓ Tenant $TENANT_ID initialized at $(date)"
ls -la .devsync/tenants/$TENANT_ID/
```

Usage:
```bash
./setup_tenant.sh acme-corp
./setup_tenant.sh startup-ai-lab
```

---

**Last Updated:** 2026-09-14  
**Maintained By:** Platform Team  
**Status:** Production Ready
