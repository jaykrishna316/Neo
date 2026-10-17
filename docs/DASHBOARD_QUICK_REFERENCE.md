# Neo Mission Control Dashboard - Quick Reference

**Full Plan:** See `DASHBOARD_IMPLEMENTATION_PLAN.md` (1,766 lines, comprehensive)

---

## What Gets Built

A real-time visualization platform combining all five Neo features:

```
┌─ REAL-TIME ACTIVITY (Left)
│  └─ Who's working on what files
│  └─ Current risk levels
│  └─ Time spent per file
│
├─ SERVICE COUPLING NETWORK (Center)
│  └─ Spider web visualization (D3.js)
│  └─ Service nodes + coupling edges
│  └─ Color-coded by coupling strength
│  └─ Pulsing active developers
│
├─ COUPLING METRICS (Bottom Left)
│  └─ Trends (increasing/decreasing)
│  └─ Regressions (newly coupled)
│  └─ Stable high-coupling services
│
├─ ENTROPY ANALYSIS (Bottom Right)
│  └─ Service clusters
│  └─ Implicit coupling discovery
│  └─ Architectural misalignments (3)
│  └─ Data quality indicators
│
└─ BLAST RADIUS + CONFLICTS (Right)
   └─ Impact scope (12 files, 6.5 hours, $0.85)
   └─ Risk heatmap (HIGH/MEDIUM/LOW)
   └─ Staged conflict layers
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18 + D3.js + TailwindCSS |
| **Backend** | Node.js + Express + Socket.io |
| **Cache** | Redis (1-6 hour TTL) |
| **Data** | Activity log + Neo MCP tools |
| **Real-time** | WebSocket (live updates) |
| **Dev** | Docker Compose |

---

## Implementation Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| **Phase 1: Foundation** | Weeks 1-2 | API endpoints, D3 network, activity feed, basic metrics |
| **Phase 2: Intelligence** | Weeks 2-3 | Entropy analysis, blast radius, conflict heatmap |
| **Phase 3: Polish** | Week 4 | Drill-downs, filters, real-time updates, performance |

---

## Key API Endpoints

```
GET  /api/dashboard/overview          → System health snapshot
GET  /api/dashboard/services/graph    → Coupling network (nodes + edges)
GET  /api/dashboard/activity          → Who's working on what (live)
GET  /api/dashboard/coupling/trends   → Coupling metrics (regressions, velocity)
GET  /api/dashboard/entropy           → Service clusters + misalignments
GET  /api/dashboard/blast-radius/:f   → Impact scope + cost estimate
GET  /api/dashboard/conflicts/heatmap → Risk assessment by file
WS   /api/dashboard/live              → Real-time events (Socket.io)
```

---

## MCP Integration

```
Dashboard calls Neo tools:
├─ neo_check_conflicts          → Staged layer conflict detection
├─ neo_calculate_blast_radius   → Impact scope & cost
├─ neo_get_coupling_trends      → Coupling metrics analysis
├─ neo_record_change_set        → Record developer changes
└─ neo_analyze_entropy_coupling → Implicit coupling discovery
```

---

## File Structure

```
dashboard/                          (NEW)
├─ api/
│  ├─ server.js                    (Express + WebSocket)
│  ├─ services/
│  │  ├─ neoClient.js            (MCP tool caller)
│  │  ├─ activityAdapter.js       (Activity log reader)
│  │  ├─ cacheService.js          (Redis)
│  │  └─ aggregator.js            (Combines all data)
│  ├─ routes/
│  └─ controllers/
│
├─ ui/
│  ├─ src/
│  │  ├─ pages/Dashboard.jsx
│  │  ├─ components/
│  │  │  ├─ ServiceNetwork.jsx      (D3 spider web)
│  │  │  ├─ ActivityFeed.jsx
│  │  │  ├─ CouplingMetrics.jsx
│  │  │  ├─ EntropyAnalysis.jsx
│  │  │  ├─ BlastRadiusMap.jsx
│  │  │  ├─ ConflictHeatmap.jsx
│  │  │  └─ ...modals & details
│  │  ├─ hooks/
│  │  └─ services/
│  └─ package.json
│
└─ docker-compose.yml
```

---

## Core Components

### Phase 1 (Foundation)
- `ServiceNetwork` - D3.js force-directed graph
- `ActivityFeed` - Real-time who's-working-on-what
- `CouplingMetrics` - Trends + regressions
- `HealthIndicators` - System overview badges

### Phase 2 (Intelligence)
- `EntropyAnalysis` - Service clusters + misalignments
- `ServiceClusters` - Grouped service visualization
- `BlastRadiusMap` - Dependency tree + cost estimate
- `ConflictHeatmap` - Risk by file + staged layers

### Phase 3 (Polish)
- `ServiceDetail` - Drill-down modal
- `CouplingPairDetail` - Pair analysis modal
- Advanced filters + search
- View mode switcher (Network/Timeline/Matrix/List)

---

## Real-World Usage Scenario

**Alice** wants to refactor Payment API:

1. **Dashboard shows:** 🔴 HIGH RISK - Bob also editing payment/api.py
2. **Blast Radius shows:** 12 files affected, 6.5 hours, 5 semantic layers triggered
3. **Entropy shows:** Hidden coupling with Orders (should be explicit)
4. **Coupling metrics show:** Payment ↔ Orders regression (was independent 60 days ago)
5. **Activity feed shows:** bob-agent currently on payment/handlers.py (45 min)

**Result:** Alice sees to coordinate with Bob BEFORE generation, preventing merge conflicts and understanding full architectural impact. Saves tokens, time, and prevents breaking changes.

---

## Performance Targets

| Metric | Target | Method |
|--------|--------|--------|
| Dashboard load | < 3s | Code splitting + lazy load |
| API latency (p95) | < 500ms | Caching + aggregation |
| Network update | < 100ms | Delta updates via WebSocket |
| Service graph render | < 2s | D3 virtualization (< 50 nodes) |
| Detail modal load | < 500ms | On-demand calculation |

---

## Data Models at a Glance

```typescript
// Activity Entry (from log)
{
  timestamp, developer_id, file_path, intent,
  region?, intent_category?, tenant_id?
}

// Service Node (graph)
{
  id, label, entropy, size, isActive,
  cluster?, riskLevel?, lastChange?, recentDevelopers?
}

// Coupling Edge (graph)
{
  source, target, strength, velocity,
  direction, isRegression, color, tooltip
}

// Conflict Report (heatmap)
{
  filePath, riskLevel, currentDevelopers,
  otherDevelopers, layers, recommendations, timestamp
}

// Architectural Issue (entropy)
{
  id, type, serviceA, serviceB, severity,
  description, mutualInformation, recommendations
}
```

---

## Caching Strategy

```
Cache Layer (Redis):

REAL-TIME (WebSocket):
└─ Activity events

SHORT (1-5 min):
├─ Activity feed
├─ Conflict heatmap
└─ Service graph

MEDIUM (30 min):
├─ Coupling trends
└─ Blast radius

LONG (6 hours):
└─ Entropy analysis + clusters
```

---

## Success Metrics

✅ **Functional:**
- Activity display accurate within 1-2s
- Network renders < 2s (< 50 services)
- All 5 features visible & integrated
- Drill-down details < 500ms

✅ **Performance:**
- API p95 < 500ms
- Lighthouse > 80
- Cache hit rate > 70%
- Memory < 500MB

✅ **UX:**
- Dashboard loads < 3s
- No visual jank
- Mobile usable (480px+)
- WCAG 2.1 AA accessible

✅ **Reliability:**
- 99.5% uptime
- Graceful degradation
- Proper error messages
- WebSocket reconnection

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| MCP call timeout | Request timeout + async queue |
| Activity log corruption | File locking + atomic writes |
| Network graph complexity | Clustering + filtering + lazy rendering |
| WebSocket scaling | Connection pooling + room subscriptions |
| Cache consistency | Event-driven invalidation + TTL tuning |
| React re-render perf | Memoization + virtualization + splitting |

---

## Deployment

```bash
# Development (Docker Compose)
docker-compose up

# Services:
├─ neo-mcp (Python, port 9090)
├─ dashboard-api (Node, port 3001)
├─ dashboard-ui (React, port 3000)
├─ redis (port 6379)
└─ activity-watcher (watches .devsync)

# Monitoring:
├─ Metrics: MCP latency, cache hit rate, error rates
├─ Logs: Structured JSON, correlated by request ID
└─ Alerts: Timeout, error rate, connection issues
```

---

## Next Steps

1. **Review & Approve** this plan
2. **Set up project structure** (boilerplate)
3. **Start Phase 1** (API + first components)
4. **Daily sync** on progress
5. **Weekly review** of timeline vs. actual

---

## Questions?

See `DASHBOARD_IMPLEMENTATION_PLAN.md` for:
- Detailed architecture diagrams
- Component hierarchy
- Full API specification
- WebSocket event definitions
- Implementation checklist
- File structure breakdown
- Performance considerations

**Document Lines:** 1,766  
**Sections:** 12 major  
**Ready to:** Start Phase 1 implementation  
**Branch:** `Extension` (default feature branch)
