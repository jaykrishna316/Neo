# Neo Mission Control Dashboard - Implementation Plan

**Version:** 1.0  
**Status:** Planning Phase  
**Branch:** Extension (default feature branch)  
**Timeline:** 3-4 weeks (3 phases)  
**Scope:** Full-stack dashboard visualization for all Neo features

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Phase 1: Foundation (Weeks 1-2)](#phase-1-foundation-weeks-1-2)
4. [Phase 2: Intelligence (Weeks 2-3)](#phase-2-intelligence-weeks-2-3)
5. [Phase 3: Interactivity & Polish (Week 4)](#phase-3-interactivity--polish-week-4)
6. [Technical Deep Dive](#technical-deep-dive)
7. [Data Models](#data-models)
8. [API Specification](#api-specification)
9. [Component Structure](#component-structure)
10. [Integration Points](#integration-points)
11. [Performance Considerations](#performance-considerations)
12. [Deployment & DevOps](#deployment--devops)

---

## Executive Summary

**Neo Mission Control Dashboard** is a real-time visualization platform that combines:
- **Activity Log**: Who is working on what files, right now
- **Service Coupling Network**: Spider web visualization of service dependencies
- **Coupling Metrics**: Trends, regressions, architectural health
- **Entropy Analysis**: Implicit coupling, architectural misalignments, service clusters
- **Blast Radius**: Impact scope and cost estimation for changes
- **Conflict Detection**: Real-time risk assessment with staged semantic layers

**Primary Goal:** Enable teams to see the entire microservices architecture health and active development in **one glance**, preventing conflicts before they happen.

**Success Metrics:**
- Team coordination time reduced by 40%
- Conflicts detected before generation: 95%+ (vs. 0% currently)
- Architectural misalignments identified proactively
- Token savings: 50-70% fewer regenerations

---

## Architecture Overview

### System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     NEO MISSION CONTROL                         │
│                    (React + D3.js Dashboard)                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
        ┌──────────────────┴──────────────────┐
        │                                     │
   ┌────▼────────────┐            ┌─────────▼────────┐
   │  Dashboard API  │            │   WebSocket      │
   │  Layer (Node)   │            │   Server (Live)  │
   └────┬────────────┘            └─────────┬────────┘
        │                                   │
        │         ┌───────────────────────────┘
        │         │
        ├─────────┼────────────────────────────┐
        │         │                            │
   ┌────▼──┐  ┌──▼────────┐  ┌───────────┐  ┌─▼──────────┐
   │  MCP  │  │  Activity │  │ Coupling  │  │  Entropy   │
   │Server │  │  Log      │  │  Metrics  │  │  Analysis  │
   └───────┘  │ Adapter   │  │  Store    │  │  Cache     │
              └───────────┘  └───────────┘  └────────────┘
                  │               │              │
                  └───────────────┼──────────────┘
                                  │
                        ┌─────────▼──────────┐
                        │  Neo Core Engine   │
                        │ (Existing Python)  │
                        └────────────────────┘
```

### Technology Stack

**Frontend:**
```
React 18.x
├─ D3.js 7.x (network visualization)
├─ Chart.js (metrics/trends)
├─ WebSocket client (real-time updates)
├─ TailwindCSS (styling)
└─ React Query (data fetching & caching)
```

**Backend:**
```
Node.js + Express
├─ Dashboard API (aggregation layer)
├─ WebSocket server (Socket.io)
├─ Redis client (caching)
└─ Python subprocess calls to Neo MCP
```

**Data Layer:**
```
Redis (cache, real-time data)
├─ Activity cache (10min TTL)
├─ Coupling metrics (1h TTL)
├─ Entropy analysis results (6h TTL)
└─ Conflict detection results (5min TTL)

Filesystem (source of truth)
├─ Activity log (.devsync/activity-log.json)
├─ Coupling history (.devsync/coupling/coupling_history.jsonl)
└─ Entropy cache (.devsync/entropy/analysis_cache.json)
```

**Infrastructure:**
```
Docker Compose (dev)
├─ Neo backend (Python MCP server)
├─ Dashboard API (Node.js)
├─ Redis (cache)
└─ Dashboard UI (React dev server)
```

---

## Phase 1: Foundation (Weeks 1-2)

### Goals
- [ ] Dashboard API layer that aggregates Neo MCP tools
- [ ] Spider web visualization of service coupling network
- [ ] Real-time activity feed showing who's working on what
- [ ] Basic coupling metrics panel
- [ ] Mock data flow working end-to-end

### Deliverables

#### 1.1 Dashboard API (`dashboard/api/server.js`)
**Purpose:** Aggregate MCP tool calls into dashboard-friendly endpoints

**Endpoints:**
```
GET /api/dashboard/overview
  Returns: {
    systemCouplingScore: 0.54,
    activeConflicts: 2,
    regressions: 2,
    architecturalIssues: 3,
    teamsActive: 3,
    filesAtRisk: 5
  }

GET /api/dashboard/services/graph
  Returns: {
    nodes: [
      { id: "payment", label: "Payment", entropy: 0.45, size: 12 },
      { id: "orders", label: "Orders", entropy: 0.52, size: 8 }
    ],
    edges: [
      {
        source: "payment",
        target: "orders",
        strength: 0.62,
        direction: "increasing",
        velocity: 0.025,
        isRegression: true,
        color: "#ef4444"
      }
    ]
  }

GET /api/dashboard/activity?limit=50
  Returns: {
    active: [
      {
        agentId: "alice-agent",
        filePath: "services/payment/api.py",
        intent: "refactor API to async",
        duration: "2h 15m",
        riskLevel: "MEDIUM",
        layers: ["semantic", "type"]
      }
    ],
    recentFiles: [...],
    recentIntents: [...]
  }

GET /api/dashboard/coupling/trends?window=90
  Returns: {
    increasing: [...],
    regressions: [...],
    stable: [...],
    decreasing: [...]
  }
```

**Implementation:**
- Calls existing Neo MCP tools
- Caches results in Redis (configurable TTL)
- Handles multi-tenant scenarios
- Error handling & fallbacks
- Rate limiting per client

#### 1.2 Service Network Visualization (`dashboard/ui/components/ServiceNetwork.jsx`)
**Purpose:** Interactive D3.js force-directed graph showing service coupling

**Features:**
- Force layout simulation
- Node sizing by importance/file count
- Edge thickness by coupling strength
- Color coding:
  - 🟢 Green (0.3-0.5): stable, expected
  - 🟡 Yellow (0.5-0.7): increasing, watch
  - 🔴 Red (0.7+): high risk
  - ⚠️ Purple: regression
- Pulsing animation for currently-edited services
- Zoom & pan controls
- Click node for detail view

**Data Source:**
```javascript
// Fetches from /api/dashboard/services/graph every 30s
const { data: graph } = useQuery(
  ['services', 'graph'],
  () => fetchServiceGraph(),
  { refetchInterval: 30000 }
);
```

#### 1.3 Real-Time Activity Feed (`dashboard/ui/components/ActivityFeed.jsx`)
**Purpose:** Live view of who's working on what

**Features:**
- Live list of active developers/agents
- File path being edited
- Time spent on current file
- Intent description
- Risk level badge
- Timestamp

**Data Source:**
```javascript
// WebSocket connection for real-time updates
useEffect(() => {
  const socket = io('/api/dashboard/live');
  socket.on('activity:update', (data) => {
    setActivityFeed(data.active);
  });
  return () => socket.disconnect();
}, []);
```

#### 1.4 Coupling Metrics Panel (`dashboard/ui/components/CouplingMetrics.jsx`)
**Purpose:** Show coupling trends and regressions

**Structure:**
```
Regressions (2 services)
├─ Payment ↔ Orders: 0.43 (was independent)
├─ Notifications ↔ Analytics: 0.38 (was independent)

Increasing Coupling (4 services)
├─ Payment ↔ Notifications: +0.025/day
├─ Orders ↔ Inventory: +0.012/day

Stable High Coupling (3 services)
└─ Orders ↔ Inventory: 0.71 (45 days)
```

**Implementation:**
- Bar charts for velocity
- Color-coded badges
- Click through to details
- Sortable/filterable

### File Structure

```
dashboard/
├─ api/
│  ├─ server.js              (Express + Socket.io server)
│  ├─ middleware/
│  │  ├─ auth.js
│  │  ├─ rateLimit.js
│  │  └─ errorHandler.js
│  ├─ routes/
│  │  ├─ dashboard.routes.js
│  │  ├─ services.routes.js
│  │  └─ activity.routes.js
│  ├─ controllers/
│  │  ├─ dashboardCtrl.js
│  │  ├─ servicesCtrl.js
│  │  └─ activityCtrl.js
│  ├─ services/
│  │  ├─ neoClient.js        (MCP tool caller)
│  │  ├─ cacheService.js     (Redis)
│  │  └─ aggregator.js       (combines multiple sources)
│  └─ utils/
│     ├─ logger.js
│     ├─ validators.js
│     └─ transformers.js
│
├─ ui/
│  ├─ public/
│  │  ├─ index.html
│  │  └─ favicon.ico
│  ├─ src/
│  │  ├─ App.jsx             (main app)
│  │  ├─ index.css           (Tailwind)
│  │  ├─ pages/
│  │  │  └─ Dashboard.jsx    (main dashboard page)
│  │  ├─ components/
│  │  │  ├─ Header.jsx
│  │  │  ├─ ServiceNetwork.jsx
│  │  │  ├─ ActivityFeed.jsx
│  │  │  ├─ CouplingMetrics.jsx
│  │  │  ├─ HealthIndicators.jsx
│  │  │  └─ Sidebar.jsx
│  │  ├─ hooks/
│  │  │  ├─ useServiceGraph.js
│  │  │  ├─ useActivity.js
│  │  │  └─ useMetrics.js
│  │  ├─ services/
│  │  │  └─ api.js           (dashboard API client)
│  │  └─ utils/
│  │     ├─ colors.js        (risk/entropy color mapping)
│  │     └─ formatting.js    (time, numbers, etc)
│
├─ docker-compose.yml
├─ Dockerfile
└─ package.json
```

---

## Phase 2: Intelligence (Weeks 2-3)

### Goals
- [ ] Entropy Analysis visualization
- [ ] Architectural misalignments detection display
- [ ] Blast Radius impact map
- [ ] Service clustering visualization
- [ ] Conflict heatmap with staged layers

### Deliverables

#### 2.1 Entropy Analysis Panel (`dashboard/ui/components/EntropyAnalysis.jsx`)

**Data from:**
```
neo_analyze_entropy_couplings() → /api/dashboard/entropy
```

**Display:**
```
ENTROPY ANALYSIS
├─ Data Quality: Mature (180+ days)
├─ Service Clusters:
│  ├─ Cluster 1: {Payment, Notifications, Orders}
│  │  └─ Cohesion Score: 0.72
│  └─ Cluster 2: {Orders, Inventory}
│     └─ Cohesion Score: 0.68
└─ Architectural Issues: 3
   ├─ Orders → Payment (hidden coupling: I(A;B)=0.62)
   ├─ Notifications → Payment (temporal coupling)
   └─ Analytics → Notifications (implicit coupling)
```

**Components:**
- Cluster group visualization (colored boxes)
- Mutual information heatmap
- Misalignment severity badges
- Action recommendations

#### 2.2 Service Clustering Visualization (`dashboard/ui/components/ServiceClusters.jsx`)

**Purpose:** Visual grouping of related services

**Layout:**
```
┌─────────────────────────────────────────┐
│  CLUSTER 1: Financial Flow              │
│  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │ Payment  │──│  Orders  │──│Orders  │ │
│  └──────────┘  └──────────┘  └────────┘ │
│  Cohesion: 0.72 | Isolation: Good      │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  CLUSTER 2: Fulfillment                 │
│  ┌──────────┐  ┌──────────┐             │
│  │  Orders  │──│Inventory │             │
│  └──────────┘  └──────────┘             │
│  Cohesion: 0.68 | Isolation: Good      │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  ISOLATED: Analytics                    │
│  ┌──────────┐                           │
│  │Analytics │ ⚠️ Coupled to Notif      │
│  └──────────┘                           │
│  Isolation: 0.15 | Issue: Alert         │
└─────────────────────────────────────────┘
```

#### 2.3 Blast Radius Impact Map (`dashboard/ui/components/BlastRadiusMap.jsx`)

**Triggered by:**
- Hovering over a service node
- Selecting a file in activity feed
- Searching for a specific impact

**Display:**
```
BLAST RADIUS: services/payment/api.py

Dependency Tree (12 files):
├─ 🟢 EASY (3 files - 2-5 min each):
│  ├─ orders/payment_client.py
│  ├─ notifications/consumer.py
│  └─ analytics/tracker.py
│
├─ 🟡 MEDIUM (6 files - 5-10 min each):
│  ├─ orders/handlers.py
│  ├─ inventory/sync.py
│  └─ ... (3 more)
│
└─ 🔴 HARD (3 files - 30-60 min each):
   ├─ payment/transaction_queue.py
   ├─ notifications/strategy.py
   └─ orders/retry_logic.py

ESTIMATED COST:
├─ Time: 6.5 hours
├─ Tokens: ~8,500 ($0.85)
└─ Risk: MEDIUM-HIGH
```

**Implementation:**
- Tree layout visualization
- Color-coded by complexity
- Collapsible/expandable
- Click file → show code preview
- Show who maintains each file

#### 2.4 Architectural Misalignment Report (`dashboard/ui/components/MisalignmentReport.jsx`)

**Shows:**
```
ARCHITECTURAL MISALIGNMENTS (3 issues)

Issue 1: Hidden Queue Coupling
├─ Services: Orders ↔ Payment
├─ Type: Implicit coupling
├─ Impact: I(A;B) = 0.62 (high mutual information)
├─ Problem: No direct imports, but change together 62% of time
├─ Location: orders/payment_client.py uses shared queue
├─ Risk: Silent breaking when Payment changes
└─ Recommendation:
   └─ Add message versioning to payment queue protocol
   └─ Document contract explicitly
   └─ Add integration tests

Issue 2: Temporal Coupling
├─ Services: Notifications ↔ Payment
├─ Type: Event subscription without versioning
├─ Impact: Always change together, no isolation
├─ Problem: Notifications doesn't know Payment schema version
├─ Risk: Notifications breaks on Payment API changes
└─ Recommendation:
   └─ Create PaymentEventAdapter
   └─ Version event schema
   └─ Add schema validation

Issue 3: Implicit Consumer Coupling
├─ Services: Analytics ← Notifications
├─ Type: Undocumented event schema dependency
├─ Impact: I(A;B) = 0.41 (unexpected coupling)
├─ Problem: No integration versioning
├─ Risk: Analytics silently fails on event schema change
└─ Recommendation:
   └─ Add event schema versioning
   └─ Document Analytics dependencies
   └─ Create integration tests
```

#### 2.5 Conflict Heatmap (`dashboard/ui/components/ConflictHeatmap.jsx`)

**Shows:**
```
CONFLICT RISK (Last 24h)

File                          Risk    Layers Triggered    Developer
──────────────────────────────────────────────────────────────────
services/payment/api.py       🔴 HIGH  3 layers           alice-agent
  └─ bob-agent also editing                              bob-agent
  └─ Syntactic + Semantic + Type changes
  └─ Recommendation: Coordinate before generation

services/orders/models.py     🟡 MED   2 layers           charlie-agent
  └─ No other developers
  └─ Scope + Semantic
  └─ Recommendation: Safe to proceed (watch for types)

services/inventory/sync.py    🟢 LOW   1 layer            alice-agent
  └─ No other developers
  └─ Syntactic only (different lines)
  └─ Recommendation: Safe to proceed
```

**Technical Implementation:**

**API Endpoint:**
```
GET /api/dashboard/conflicts/heatmap?time_window=24h
  Returns: [
    {
      filePath: "services/payment/api.py",
      riskLevel: "HIGH",
      layers: ["syntactic", "semantic", "type"],
      currentDevelopers: [{ id: "alice-agent", duration: "2h 15m" }],
      otherDevelopers: [{ id: "bob-agent", intent: "handle refunds", duration: "45m" }],
      recommendations: [...]
    }
  ]
```

---

## Phase 3: Interactivity & Polish (Week 4)

### Goals
- [ ] Drill-down details for all metrics
- [ ] Real-time WebSocket updates
- [ ] Advanced filtering & search
- [ ] Dark/light theme toggle
- [ ] Mobile responsive design
- [ ] Performance optimization
- [ ] Error handling & fallbacks

### Deliverables

#### 3.1 Detail Drill-Down Views

**Service Detail Modal:**
```
When clicking a node on service network:
├─ Service name & overview
├─ Files in service (with sizes)
├─ Dependencies (incoming & outgoing)
├─ Current developers
├─ Recent changes (last 7 days)
├─ Coupling relationships:
│  ├─ Who depends on this service
│  ├─ Coupling scores & trends
│  ├─ Regressions involving this service
│  └─ Historical coupling timeline
├─ Entropy metrics
│  ├─ Cluster membership
│  ├─ Implicit dependencies
│  └─ Architectural issues
└─ Risk assessment
   ├─ High-risk files
   ├─ Current conflicts
   └─ Recommendations
```

**Coupling Pair Detail:**
```
When clicking an edge (coupling relationship):
├─ Service A ↔ Service B
├─ Metrics:
│  ├─ Mutual information: I(A;B) = 0.62
│  ├─ Current coupling score: 0.67
│  ├─ Velocity: +0.025/day (increasing)
│  ├─ Direction: increasing
│  ├─ Age: 45 days
│  └─ Regression: true (was independent)
├─ Co-change History:
│  ├─ Changed together: 28 times (last 90 days)
│  ├─ Timeline: [chart showing co-changes over time]
│  └─ Frequency: 38% of changes
├─ Shared Elements:
│  ├─ Shared dependencies: [list]
│  ├─ Direct function calls: [list]
│  └─ Type references: [list]
├─ Recent Changes:
│  ├─ Last changed together: 2 days ago
│  │  └─ Files: [list]
│  └─ Individual changes: [list]
└─ Recommendations:
   ├─ Reduce coupling by: [suggestions]
   └─ Consider refactoring: [areas]
```

#### 3.2 WebSocket Real-Time Updates

**Live Events:**
```javascript
// Connect to dashboard WebSocket
const socket = io('/api/dashboard/live', {
  reconnection: true,
  reconnectionDelay: 1000,
  reconnectionDelayMax: 5000,
  reconnectionAttempts: 5
});

socket.on('activity:new', (data) => {
  // New developer started working
  // Update activity feed in real-time
});

socket.on('activity:update', (data) => {
  // Developer still working, update duration
});

socket.on('activity:end', (data) => {
  // Developer finished working
});

socket.on('conflict:detected', (data) => {
  // New conflict detected
  // Show alert + update heatmap
});

socket.on('coupling:change', (data) => {
  // Coupling metric changed
  // Update network graph
});

socket.on('metrics:refresh', (data) => {
  // New entropy/blast radius calculated
  // Update panels
});
```

**Backend WebSocket Handler:**
```
dashboard/api/websocket/handler.js
├─ Connects to Neo activity log watcher
├─ Watches file changes
├─ Calculates deltas
├─ Broadcasts to all connected clients
├─ Maintains room for per-service subscriptions
└─ Graceful disconnect handling
```

#### 3.3 Advanced Filtering

**Filter Options:**
```
Time Range: [Last 1h] [Last 24h] [Last 7d] [Custom ▼]
Risk Level: [All] [High] [Medium] [Low]
Services: [All] [Select services...▼]
Developers: [All] [Select developers...▼]
View Type: [Network] [Timeline] [Matrix] [List]
Sort By: [Coupling Strength] [Activity] [Risk] [Time]
```

**Search:**
```
Search: [_____________________]
├─ By service name (fuzzy match)
├─ By developer/agent name
├─ By file path
├─ By intent keyword
└─ Highlight matches on network
```

#### 3.4 Responsive Design

**Breakpoints:**
```
Desktop (1920px):
├─ Left panel: 25% (Activity + Metrics)
├─ Center: 50% (Network visualization)
└─ Right panel: 25% (Blast Radius + Details)

Tablet (1024px):
├─ Stack: Activity (top)
├─ Network (middle, full width)
└─ Metrics (bottom)

Mobile (480px):
├─ Hamburger menu (Activity, Filters)
├─ Full-width Network (simplified)
└─ Bottom sheet (details)
```

#### 3.5 Performance Optimization

**Strategies:**
```
Data Fetching:
├─ GraphQL subscriptions for selective updates
├─ Lazy load detail views
├─ Pagination for activity feed (50 items/page)
└─ Redis caching with smart TTLs

Rendering:
├─ React.memo for static components
├─ useMemo for expensive calculations
├─ Virtualization for long lists
├─ Debounce zoom/pan events
└─ Limit network re-renders to 1s intervals

Network:
├─ Compress WebSocket payloads (delta updates)
├─ Batch updates (don't send every millisecond)
├─ Connection pooling for MCP calls
└─ Request deduplication
```

---

## Technical Deep Dive

### 3.1 MCP Integration Points

**How Dashboard Calls Neo:**

```javascript
// dashboard/api/services/neoClient.js

const neoClient = {
  // Call MCP tool via stdio
  async callTool(toolName, input) {
    const { spawn } = require('child_process');
    const python = spawn('python3', [
      '-m', 'ide.mcp_neo_server'
    ], {
      env: {
        PYTHONPATH: '/path/to/Neo',
        NEO_MULTITENANCY: 'false',
        CLAUDE_TENANT_ID: 'default'
      }
    });
    
    // Send JSON-RPC request
    python.stdin.write(JSON.stringify({
      jsonrpc: '2.0',
      method: toolName,
      params: input,
      id: Date.now()
    }));
    
    // Get response
    return new Promise((resolve, reject) => {
      python.stdout.on('data', (data) => {
        resolve(JSON.parse(data.toString()));
      });
    });
  },

  // Wrapper functions
  async checkConflicts(agentId, filePath, intent, region) {
    return this.callTool('neo_check_conflicts', {
      agent_id: agentId,
      file_path: filePath,
      intent: intent,
      region: region,
      use_unified_check: true
    });
  },

  async calculateBlastRadius(filePath, changeType, dependencies) {
    return this.callTool('neo_calculate_blast_radius', {
      file_path: filePath,
      change_type: changeType,
      dependencies: dependencies
    });
  },

  async getCouplingTrends(windowDays) {
    return this.callTool('neo_get_coupling_trends', {
      window_days: windowDays
    });
  },

  async recordChangeSet(changedFiles, developerId, intent) {
    return this.callTool('neo_record_change_set', {
      changed_files: changedFiles,
      developer_id: developerId,
      intent: intent
    });
  },

  async analyzeEntropyCoupling(historyFile, actualImports) {
    return this.callTool('neo_analyze_entropy_coupling', {
      history_file: historyFile,
      actual_imports: actualImports
    });
  }
};
```

### 3.2 Activity Log Adapter

**How Dashboard Reads Activity Log:**

```javascript
// dashboard/api/services/activityAdapter.js

class ActivityLogAdapter {
  constructor(logPath = '.devsync/activity-log.json') {
    this.logPath = logPath;
    this.watchers = [];
  }

  // Real-time file watching
  watch(callback) {
    const fs = require('fs');
    const watcher = fs.watch(this.logPath, async () => {
      const entries = await this.read();
      callback(entries);
    });
    this.watchers.push(watcher);
  }

  // Read entire log
  async read() {
    const fs = require('fs').promises;
    const content = await fs.readFile(this.logPath, 'utf-8');
    return content
      .split('\n')
      .filter(line => line.trim())
      .map(line => JSON.parse(line));
  }

  // Get active entries (last 1 hour)
  async getActive(maxAgeMinutes = 60) {
    const entries = await this.read();
    const now = Date.now();
    return entries.filter(e => {
      const age = (now - e.timestamp * 1000) / (1000 * 60);
      return age <= maxAgeMinutes;
    });
  }

  // Group by agent
  async getActiveByAgent() {
    const active = await this.getActive();
    return active.reduce((map, e) => {
      if (!map[e.developer_id]) {
        map[e.developer_id] = [];
      }
      map[e.developer_id].push(e);
      return map;
    }, {});
  }

  // Get files at risk (being edited right now)
  async getFilesAtRisk() {
    const active = await this.getActive();
    const files = new Set();
    active.forEach(e => files.add(e.file_path));
    return Array.from(files);
  }
}
```

### 3.3 Data Aggregation Pipeline

```javascript
// dashboard/api/services/aggregator.js

class DashboardAggregator {
  constructor(neoClient, activityAdapter, cache) {
    this.neo = neoClient;
    this.activity = activityAdapter;
    this.cache = cache; // Redis
  }

  // Get complete dashboard snapshot
  async getDashboardOverview() {
    const cached = await this.cache.get('dashboard:overview');
    if (cached) return cached;

    const [
      active,
      conflicts,
      coupling,
      entropy,
      blastRadius
    ] = await Promise.all([
      this.activity.getActive(),
      this.getActiveConflicts(),
      this.neo.getCouplingTrends(90),
      this.neo.analyzeEntropyCoupling(),
      this.getBlastRadiusEstimates()
    ]);

    const overview = {
      timestamp: Date.now(),
      activeCount: active.length,
      activeFilesCount: new Set(active.map(a => a.file_path)).size,
      conflictCount: conflicts.length,
      highRiskCount: conflicts.filter(c => c.riskLevel === 'HIGH').length,
      regressions: coupling.regressions,
      architecturalIssues: entropy.misalignments?.length || 0,
      couplingScore: this.calculateCouplingScore(coupling),
      overallRisk: this.calculateOverallRisk(conflicts, coupling)
    };

    // Cache for 1 minute
    await this.cache.set('dashboard:overview', overview, 60);
    return overview;
  }

  // Get service coupling network for visualization
  async getServiceGraph() {
    const cached = await this.cache.get('dashboard:services:graph');
    if (cached) return cached;

    const coupling = await this.neo.getCouplingTrends(90);
    const entropy = await this.neo.analyzeEntropyCoupling();
    const active = await this.activity.getActive();

    // Extract services from coupling trends
    const services = new Set();
    coupling.trends.forEach(trend => {
      services.add(trend.service_a);
      services.add(trend.service_b);
    });

    // Build node list
    const nodes = Array.from(services).map(service => ({
      id: service,
      label: service,
      entropy: entropy.coupling_matrix?.[service] || 0.3,
      size: this.calculateServiceSize(service),
      isActive: active.some(a => a.file_path.includes(service)),
      cluster: this.findCluster(service, entropy.clusters)
    }));

    // Build edge list
    const edges = coupling.trends.map(trend => ({
      source: trend.service_a,
      target: trend.service_b,
      strength: trend.current_score,
      velocity: trend.velocity,
      direction: trend.direction,
      isRegression: trend.regression,
      color: this.getEdgeColor(trend),
      tooltip: `${trend.service_a} ↔ ${trend.service_b}: ${trend.current_score.toFixed(2)}`
    }));

    const graph = { nodes, edges, timestamp: Date.now() };
    await this.cache.set('dashboard:services:graph', graph, 300); // 5 min
    return graph;
  }

  // Calculate overall risk score
  calculateOverallRisk(conflicts, coupling) {
    let risk = 0;
    risk += conflicts.length * 5; // Each conflict adds 5 points
    risk += coupling.regressions * 10; // Each regression adds 10 points
    return Math.min(100, risk); // Cap at 100
  }

  // Color edge by risk
  getEdgeColor(trend) {
    if (trend.regression) return '#a855f7'; // Purple
    if (trend.current_score > 0.7) return '#ef4444'; // Red
    if (trend.current_score > 0.5) return '#f59e0b'; // Yellow
    return '#10b981'; // Green
  }
}
```

---

## Data Models

### Activity Entry

```typescript
interface ActivityEntry {
  timestamp: number;           // Unix timestamp
  developer_id: string;        // Agent/developer ID
  file_path: string;          // Full path to file
  intent: string;             // What they're doing
  region?: string;            // Specific region (lines/function)
  intent_category?: string;   // feature/bugfix/refactor/other
  tenant_id?: string;         // For multitenancy
}
```

### Service Node

```typescript
interface ServiceNode {
  id: string;
  label: string;
  entropy: number;           // 0-1, from entropy analysis
  size: number;              // Files in service
  isActive: boolean;         // Currently being edited
  cluster?: string;          // Cluster ID from entropy
  riskLevel?: "LOW" | "MEDIUM" | "HIGH";
  lastChange?: number;       // Timestamp
  recentDevelopers?: string[];
}
```

### Coupling Edge

```typescript
interface CouplingEdge {
  source: string;
  target: string;
  strength: number;          // 0-1, coupling score
  velocity: number;          // Change per day
  direction: "increasing" | "decreasing" | "stable";
  isRegression: boolean;
  color: string;
  tooltip: string;
  history?: CouplingSnapshot[];
  mutualInformation?: number;
}
```

### Conflict Report

```typescript
interface ConflictReport {
  filePath: string;
  riskLevel: "LOW" | "MEDIUM" | "HIGH";
  currentDevelopers: DeveloperInfo[];
  otherDevelopers: DeveloperInfo[];
  layers: string[];           // Triggered semantic layers
  recommendations: string[];
  timestamp: number;
}
```

### Architectural Issue

```typescript
interface ArchitecturalIssue {
  id: string;
  type: "hidden_coupling" | "implicit_coupling" | "temporal_coupling";
  serviceA: string;
  serviceB: string;
  severity: "low" | "medium" | "high";
  description: string;
  mutualInformation: number;
  recommendations: string[];
}
```

---

## API Specification

### Dashboard API (`/api/dashboard/*`)

#### GET /api/dashboard/overview
**Purpose:** High-level system health
**Cache:** 1 minute
**Response:**
```json
{
  "timestamp": 1729189200000,
  "systemCouplingScore": 0.54,
  "activeCount": 3,
  "activeFilesCount": 5,
  "conflictCount": 2,
  "highRiskCount": 1,
  "regressions": 2,
  "architecturalIssues": 3,
  "teamsActive": 2,
  "filesAtRisk": 5,
  "overallRisk": 27
}
```

#### GET /api/dashboard/services/graph
**Purpose:** Service coupling network
**Cache:** 5 minutes
**Query Params:** 
- `cluster`: Filter by cluster
- `minCoupling`: Min coupling strength to show (default 0.1)
**Response:**
```json
{
  "timestamp": 1729189200000,
  "nodes": [...],
  "edges": [...],
  "clusters": [
    {
      "id": "cluster-1",
      "services": ["payment", "orders", "notifications"],
      "cohesion": 0.72
    }
  ]
}
```

#### GET /api/dashboard/activity
**Purpose:** Current development activity
**Cache:** Real-time (WebSocket preferred)
**Query Params:**
- `limit`: Max entries (default 50)
- `filter`: developer/file filter
**Response:**
```json
{
  "timestamp": 1729189200000,
  "active": [
    {
      "agentId": "alice-agent",
      "filePath": "services/payment/api.py",
      "intent": "refactor API to async",
      "startTime": 1729188000000,
      "duration": "2h 15m",
      "riskLevel": "MEDIUM",
      "layers": ["semantic", "type"]
    }
  ],
  "recentFiles": [...],
  "filesAtRisk": [...]
}
```

#### GET /api/dashboard/coupling/trends
**Purpose:** Coupling metric analysis
**Cache:** 30 minutes
**Query Params:**
- `window`: Analysis window (default 90 days)
**Response:**
```json
{
  "timestamp": 1729189200000,
  "increasing": [
    {
      "serviceA": "payment",
      "serviceB": "notifications",
      "currentScore": 0.67,
      "velocity": 0.025,
      "direction": "increasing"
    }
  ],
  "regressions": [...],
  "stable": [...],
  "decreasing": [...]
}
```

#### GET /api/dashboard/entropy
**Purpose:** Entropy-based coupling analysis
**Cache:** 6 hours
**Response:**
```json
{
  "timestamp": 1729189200000,
  "dataAgeStatus": "✅ Mature (180+ days)",
  "couplingMatrix": {
    "payment-notifications": 0.78,
    "payment-orders": 0.62,
    "orders-inventory": 0.71
  },
  "clusters": [
    {
      "id": "cluster-1",
      "services": ["payment", "notifications", "orders"],
      "cohesion": 0.72,
      "type": "financial_flow"
    }
  ],
  "misalignments": [
    {
      "id": "issue-1",
      "type": "hidden_coupling",
      "serviceA": "orders",
      "serviceB": "payment",
      "severity": "high",
      "description": "Orders talks to Payment indirectly via shared Queue",
      "recommendations": ["Add message versioning", "Document contract"]
    }
  ]
}
```

#### GET /api/dashboard/blast-radius/:filePath
**Purpose:** Impact scope for a file change
**Cache:** 10 minutes
**Query Params:**
- `changeType`: general/signature/logic/refactor (default general)
**Response:**
```json
{
  "timestamp": 1729189200000,
  "sourceFile": "services/payment/api.py",
  "totalDependents": 12,
  "easyFixes": 3,
  "mediumFixes": 6,
  "hardFixes": 3,
  "totalEstimatedHours": 6.5,
  "totalTokenCost": 8500,
  "details": [
    {
      "file": "services/orders/payment_client.py",
      "complexity": "easy",
      "estimatedMinutes": 3,
      "tokenEstimate": 150,
      "type": "syntactic",
      "reason": "Import fix"
    }
  ]
}
```

#### GET /api/dashboard/conflicts/heatmap
**Purpose:** File-level conflict risk
**Cache:** 5 minutes (updated via WebSocket)
**Query Params:**
- `timeWindow`: 1h/24h/7d (default 24h)
**Response:**
```json
{
  "timestamp": 1729189200000,
  "conflicts": [
    {
      "filePath": "services/payment/api.py",
      "riskLevel": "HIGH",
      "layers": ["syntactic", "semantic", "type"],
      "currentDevelopers": [
        {
          "id": "alice-agent",
          "startTime": 1729188000000,
          "duration": "2h 15m"
        }
      ],
      "otherDevelopers": [
        {
          "id": "bob-agent",
          "intent": "handle refunds",
          "duration": "45m"
        }
      ],
      "recommendations": ["Coordinate with bob-agent before proceeding"]
    }
  ]
}
```

### WebSocket Events (`/api/dashboard/live`)

**Client → Server:**
```javascript
// Subscribe to specific service
socket.emit('subscribe:service', { service: 'payment' });

// Unsubscribe
socket.emit('unsubscribe:service', { service: 'payment' });

// Request refresh
socket.emit('refresh', { section: 'overview' });
```

**Server → Client:**
```javascript
socket.on('activity:new', (data) => {
  // {agentId, filePath, intent, timestamp}
});

socket.on('activity:update', (data) => {
  // {agentId, filePath, duration}
});

socket.on('activity:end', (data) => {
  // {agentId, filePath, endTime}
});

socket.on('conflict:detected', (data) => {
  // {filePath, riskLevel, conflictingDeveloper}
});

socket.on('conflict:resolved', (data) => {
  // {filePath}
});

socket.on('coupling:changed', (data) => {
  // {serviceA, serviceB, newScore, direction}
});

socket.on('metrics:refresh', (data) => {
  // {section, timestamp}
});
```

---

## Component Structure

### Core Components

```
Dashboard (main container)
├─ Header
│  ├─ Title & Status
│  ├─ Time Range Selector
│  ├─ View Mode Selector
│  └─ Refresh Controls
│
├─ Main Grid (Responsive 3-column on desktop)
│  ├─ Left Panel (25%)
│  │  ├─ HealthIndicators
│  │  ├─ ActivityFeed
│  │  └─ CouplingMetrics
│  │
│  ├─ Center Panel (50%)
│  │  ├─ ServiceNetwork (D3 visualization)
│  │  └─ ServiceDetail (modal)
│  │
│  └─ Right Panel (25%)
│     ├─ BlastRadiusMap
│     ├─ ConflictHeatmap
│     └─ EntropyAnalysis
│
└─ Footer
   ├─ Status
   ├─ Last Update Time
   └─ Help/Documentation
```

### Hierarchy by Phase

**Phase 1:**
```
- Header
- ServiceNetwork
- ActivityFeed
- CouplingMetrics
- HealthIndicators
```

**Phase 2:**
```
+ EntropyAnalysis
+ ServiceClusters
+ BlastRadiusMap
+ ConflictHeatmap
+ ArchitecturalIssues
```

**Phase 3:**
```
+ ServiceDetail (modal)
+ CouplingPairDetail (modal)
+ AdvancedFilters
+ SearchBar
+ ViewModeSwitcher
```

---

## Integration Points

### 1. MCP Server Integration
- **File:** `dashboard/api/services/neoClient.js`
- **Method:** Spawn Python subprocess, send JSON-RPC
- **Tools Called:**
  - `neo_check_conflicts`
  - `neo_calculate_blast_radius`
  - `neo_get_coupling_trends`
  - `neo_record_change_set`
  - `neo_analyze_entropy_coupling`

### 2. Activity Log Integration
- **File:** `dashboard/api/services/activityAdapter.js`
- **Source:** `.devsync/activity-log.json`
- **Polling:** File system watcher (inotify/kqueue)
- **Update Frequency:** Real-time (debounced 1s)

### 3. Neo Core Integration
- All existing Neo modules remain unchanged
- Dashboard is purely read-only observer
- No modification to core conflict detection or metrics

### 4. IDE Integration Path
```
Claude Code IDE
    ↓
neo_check_conflicts (MCP)
    ↓
dashboard updates in real-time
    ↓
Team sees conflict on dashboard
    ↓
Developers coordinate
    ↓
Safe generation proceeds
```

---

## Performance Considerations

### Caching Strategy

```
Cache Layer (Redis):

Short TTL (1-5 min):
├─ Activity feed (1 min)
├─ Conflict heatmap (5 min)
└─ Service graph (5 min)

Medium TTL (30 min):
├─ Coupling trends (30 min)
└─ Blast radius estimates (30 min)

Long TTL (6 hours):
├─ Entropy analysis (6h)
└─ Cluster definitions (6h)

No Cache (Real-time):
└─ WebSocket events (live)
```

### Query Optimization

```
N+1 Prevention:
├─ Batch coupling trend queries
├─ Single entropy analysis per window
└─ Aggregate activity log once

Pagination:
├─ Activity feed: 50 items/page
├─ Conflict heatmap: 20 items/page
└─ Details: lazy load on click

Index Strategy:
├─ Activity log: indexed by timestamp, developer_id
├─ Coupling history: indexed by (service_a, service_b)
└─ File paths: full-text search index
```

### Network Optimization

```
Compression:
├─ Gzip all API responses
├─ Delta updates via WebSocket
└─ Selective field projection

Lazy Loading:
├─ Detail views load on demand
├─ Blast radius calculated when clicked
└─ Service details modal on-demand

Bundling:
├─ Code split by feature/page
├─ Vendor bundle (D3, Chart.js, etc)
└─ CSS critical path inlined
```

---

## Deployment & DevOps

### Docker Compose (Development)

```yaml
version: '3.8'
services:
  neo-mcp:
    build:
      context: .
      dockerfile: Dockerfile.python
    environment:
      PYTHONPATH: /app
      NEO_MULTITENANCY: 'false'
      CLAUDE_TENANT_ID: 'default'
    volumes:
      - .:/app
      - .devsync:/app/.devsync

  dashboard-api:
    build:
      context: ./dashboard
      dockerfile: Dockerfile.nodejs
    environment:
      NODE_ENV: development
      NEO_MCP_PATH: /app/ide/mcp_neo_server.py
      REDIS_URL: redis://redis:6379
      PORT: 3001
    ports:
      - "3001:3001"
    depends_on:
      - redis
    volumes:
      - ./dashboard/api:/app/api
      - /app/node_modules

  dashboard-ui:
    build:
      context: ./dashboard/ui
      dockerfile: Dockerfile.react
    environment:
      NODE_ENV: development
      REACT_APP_API_URL: http://localhost:3001
    ports:
      - "3000:3000"
    depends_on:
      - dashboard-api
    volumes:
      - ./dashboard/ui/src:/app/src
      - /app/node_modules

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  # Development: file watcher for activity log
  activity-watcher:
    build:
      context: ./dashboard
      dockerfile: Dockerfile.watcher
    volumes:
      - .devsync:/app/.devsync
    depends_on:
      - redis
```

### Monitoring & Observability

```
Metrics to track:
├─ MCP call latency (avg, p95, p99)
├─ Cache hit rate
├─ WebSocket connection count
├─ API response times
├─ Error rates by endpoint
├─ Activity log write throughput
└─ CPU/memory usage

Logging:
├─ Structured JSON logs
├─ Log levels: ERROR, WARN, INFO, DEBUG
├─ Request IDs for tracing
└─ Correlation across services

Alerting:
├─ MCP call timeout (> 5s)
├─ API error rate > 5%
├─ Cache miss > 40%
├─ WebSocket disconnects > 10/min
└─ Disk space for activity log
```

---

## File Structure Summary

```
neo/
├─ dashboard/                 (NEW)
│  ├─ api/
│  │  ├─ server.js
│  │  ├─ middleware/
│  │  ├─ routes/
│  │  ├─ controllers/
│  │  ├─ services/
│  │  │  ├─ neoClient.js
│  │  │  ├─ activityAdapter.js
│  │  │  ├─ cacheService.js
│  │  │  └─ aggregator.js
│  │  ├─ websocket/
│  │  │  ├─ handler.js
│  │  │  └─ events.js
│  │  ├─ config.js
│  │  └─ package.json
│  │
│  ├─ ui/
│  │  ├─ public/
│  │  │  └─ index.html
│  │  ├─ src/
│  │  │  ├─ App.jsx
│  │  │  ├─ pages/
│  │  │  │  └─ Dashboard.jsx
│  │  │  ├─ components/
│  │  │  │  ├─ Header.jsx
│  │  │  │  ├─ ServiceNetwork.jsx
│  │  │  │  ├─ ActivityFeed.jsx
│  │  │  │  ├─ CouplingMetrics.jsx
│  │  │  │  ├─ EntropyAnalysis.jsx
│  │  │  │  ├─ BlastRadiusMap.jsx
│  │  │  │  ├─ ConflictHeatmap.jsx
│  │  │  │  └─ ...
│  │  │  ├─ hooks/
│  │  │  │  ├─ useServiceGraph.js
│  │  │  │  ├─ useActivity.js
│  │  │  │  └─ useMetrics.js
│  │  │  ├─ services/
│  │  │  │  └─ api.js
│  │  │  ├─ utils/
│  │  │  └─ index.css
│  │  ├─ package.json
│  │  └─ Dockerfile.react
│  │
│  ├─ docker-compose.yml
│  ├─ Dockerfile.nodejs
│  └─ package.json (root)
│
├─ core/                      (EXISTING - unchanged)
├─ ide/                        (EXISTING - add dashboard routes)
└─ docs/
   ├─ DASHBOARD_IMPLEMENTATION_PLAN.md (this file)
   └─ ...
```

---

## Implementation Checklist

### Phase 1
- [ ] Set up Node.js backend boilerplate
- [ ] Create Express API server with middleware
- [ ] Implement MCP client (neoClient.js)
- [ ] Implement activity log adapter
- [ ] Create caching layer (Redis)
- [ ] Build dashboard aggregator
- [ ] Implement dashboard overview endpoint
- [ ] Implement service graph endpoint
- [ ] Implement activity endpoint
- [ ] Implement coupling metrics endpoint
- [ ] Create React app boilerplate
- [ ] Build ServiceNetwork D3 visualization
- [ ] Build ActivityFeed component
- [ ] Build CouplingMetrics component
- [ ] Build HealthIndicators component
- [ ] Create responsive layout
- [ ] Set up WebSocket connection (basic)
- [ ] Docker Compose setup (dev)
- [ ] End-to-end testing

### Phase 2
- [ ] Implement entropy analysis endpoint
- [ ] Implement blast radius endpoint
- [ ] Implement conflict heatmap endpoint
- [ ] Build EntropyAnalysis component
- [ ] Build ServiceClusters visualization
- [ ] Build BlastRadiusMap component
- [ ] Build ConflictHeatmap component
- [ ] Build ArchitecturalIssues list
- [ ] Add architectural misalignment logic
- [ ] Advanced WebSocket events
- [ ] Performance optimization (caching tuning)
- [ ] Error handling & fallbacks
- [ ] Integration testing

### Phase 3
- [ ] Build detail modals (ServiceDetail, CouplingPairDetail)
- [ ] Implement drill-down functionality
- [ ] Add advanced filtering UI
- [ ] Implement search functionality
- [ ] Add view mode switcher
- [ ] Dark/light theme support
- [ ] Mobile responsive refinement
- [ ] WebSocket real-time updates
- [ ] Accessibility audit (WCAG 2.1 AA)
- [ ] Performance profiling & optimization
- [ ] Error boundary components
- [ ] Loading skeletons
- [ ] Empty states
- [ ] E2E testing
- [ ] Production deployment
- [ ] Documentation

---

## Success Criteria

### Functional
- ✅ Real-time activity display accurate within 1-2 seconds
- ✅ Service coupling network renders < 2s for < 50 services
- ✅ All five features visible and integrated
- ✅ Drill-down details load < 500ms
- ✅ WebSocket updates < 100ms latency

### Performance
- ✅ API p95 latency < 500ms
- ✅ API p99 latency < 2s
- ✅ Lighthouse score > 80
- ✅ Cache hit rate > 70%
- ✅ Memory usage < 500MB (Node), < 1GB (React)

### User Experience
- ✅ Dashboard loads in < 3s
- ✅ No visual jank on interactions
- ✅ Mobile usable at 480px width
- ✅ Accessible (WCAG 2.1 AA)
- ✅ Works with 6+ months of data (large datasets)

### Reliability
- ✅ 99.5% uptime during development
- ✅ Graceful degradation when services unavailable
- ✅ Proper error messages for all failure modes
- ✅ WebSocket reconnection handling
- ✅ Cache invalidation strategy tested

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| MCP calls timeout | Medium | High | Implement request timeout, async queue |
| Activity log corruption | Low | High | File locking, atomic writes, backup |
| Network graph too complex (many services) | Low | High | Clustering, filtering, lazy rendering |
| WebSocket scaling issues | Medium | Medium | Connection pooling, room-based subscriptions |
| Cache consistency | Medium | Medium | Event-driven invalidation, TTL tuning |
| React re-render performance | High | Medium | Memoization, virtualization, code splitting |

---

## Timeline Estimate

```
Week 1 (Phase 1 - Foundation):
├─ Day 1-2: API boilerplate, MCP client
├─ Day 3: Activity adapter, caching
├─ Day 4-5: Aggregator, endpoints
├─ Day 5: React setup, first component
└─ Day 6-7: D3 visualization, integration

Week 2 (Phase 1 Complete - Intelligence):
├─ Day 1-2: Entropy & blast radius endpoints
├─ Day 3-4: Clustering, misalignments
├─ Day 5-6: Advanced components
├─ Day 7: Testing, optimization

Week 3 (Phase 2-3 - Polish):
├─ Day 1-2: Detail modals, drill-down
├─ Day 3-4: Filters, search, themes
├─ Day 5: WebSocket polish
├─ Day 6-7: Testing, documentation

Week 4 (Phase 3 Complete):
├─ Day 1-2: Performance tuning
├─ Day 3-4: E2E testing, accessibility
├─ Day 5-6: Deployment, monitoring
└─ Day 7: Demo, handoff
```

---

## Next Steps

1. **Approve Plan**: Get stakeholder sign-off on architecture
2. **Set Up Environment**: Docker Compose, Node/React boilerplate
3. **Begin Phase 1**: Start with API and foundation components
4. **Daily Syncs**: Quick standup on progress, blockers
5. **Weekly Reviews**: Check against timeline, scope adjustments

---

**Owner:** Jay Krishna  
**Status:** Draft - Ready for Review  
**Last Updated:** 2026-10-17
