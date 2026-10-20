# Neo Mission Control Dashboard

A real-time visualization dashboard that brings all of Neo's advanced conflict detection, coupling analysis, and entropy metrics to life.

## 🚀 Features

### 1. **Conflict Detection Network**
- Interactive D3 force-directed graph showing service relationships
- Color-coded edges by coupling strength (🟢 Low → 🔴 High)
- Draggable nodes for exploration
- Real-time updates via WebSocket

### 2. **Activity Timeline**
- Real-time activity feed grouped by time
- Developer identity tracking
- File path and intent capture
- Just Now / Last Hour / Last 24h / Older grouping

### 3. **Coupling Metrics**
- Entropy analysis status with data age tracking
- Architectural issues counter
- 90-day rolling window analysis
- Meaningful data readiness indicator

### 4. **Conflict Heatmap**
- File-level risk assessment
- 5-layer semantic conflict detection visualization
- Developer involvement per file
- Service filtering

### 5. **Health Indicators**
- Overall conflict risk (LOW/MEDIUM/HIGH)
- Active developer count
- Entropy meaningful status
- Server health status

## 📊 Architecture

### Backend Stack
- **Express.js** - REST API and WebSocket server
- **Socket.io** - Real-time event broadcasting
- **Redis** - Multi-tier caching (1min-6hr TTL)
- **Neo MCP** - Integration with conflict detection engine

### Frontend Stack
- **React 18** - Component framework
- **D3.js** - Force-directed graph visualization
- **Socket.io Client** - Real-time updates
- **Tailwind CSS** - Responsive styling

### Services

#### `neoClient.js`
Bridge to Neo's MCP tools:
```javascript
checkConflicts(agentId, filePath, intent)
calculateBlastRadius(agentId, filePath, changeType)
getCouplingTrends(filePath, window)
analyzeEntropyCoupling(window)
getActiveWork()
getStatus()
```

#### `cacheService.js`
Redis caching with semantic keys:
- `neo:conflict:filePath` - 60s TTL
- `neo:coupling_trends:filePath` - 300s TTL
- `neo:entropy:global` - 3600s TTL
- `neo:graph:services` - 300s TTL

#### `aggregator.js`
Combines Neo data, activity log, and cache:
- `getDashboardOverview()` - Health snapshot
- `getServicesGraph()` - D3-ready graph model
- `getConflictHeatmap()` - Risk assessment
- `getActivityFeed(limit)` - Recent activity

### API Endpoints

#### Dashboard
```
GET  /api/dashboard/overview     - Status, activity, metrics
GET  /api/dashboard/graph        - Service network graph
GET  /api/dashboard/heatmap      - Conflict risk heatmap
GET  /api/dashboard/metrics/:metric  - Time-series metrics
```

#### Services
```
GET  /api/services/coupling              - Service coupling edges
GET  /api/services/:service/trends       - Coupling trends (90d window)
GET  /api/services/:service/blast-radius - Impact estimation
GET  /api/services/entropy/analysis      - Architectural issues
```

#### Activity
```
GET  /api/activity/feed                  - Recent activity (50 entries)
GET  /api/activity/developer/:agentId   - Per-developer activity
GET  /api/activity/file/*filePath       - Per-file activity
GET  /api/activity/summary              - Summary stats
```

#### WebSocket Events
```
metrics:overview   - Dashboard overview broadcast (10s)
activity:update    - Activity feed update (30s)
graph:update       - Service graph update (60s)
refresh:*          - On-demand refresh responses
```

## 🏃 Getting Started

### Prerequisites
- Docker & Docker Compose
- Node.js 18+ (for local development)
- Python 3.9+ (for Neo MCP)

### Quick Start

```bash
cd dashboard

# Start all services
docker-compose up

# Dashboard UI will be available at http://localhost:3000
# API will be available at http://localhost:3001
```

### Manual Setup (Development)

```bash
# Terminal 1: API Server
cd api
npm install
npm run dev

# Terminal 2: UI Server
cd ui
npm install
npm start

# Terminal 3: Redis
redis-server

# Terminal 4: Neo MCP
cd ..
PYTHONPATH=. python3 -m ide.mcp_neo_server
```

## 📁 Project Structure

```
dashboard/
├── api/
│   ├── services/
│   │   ├── neoClient.js          # MCP bridge
│   │   ├── cacheService.js       # Redis wrapper
│   │   ├── aggregator.js         # Data aggregation
│   │   └── activityWatcher.js    # Log watcher
│   ├── routes/
│   │   ├── dashboard.routes.js   # Dashboard endpoints
│   │   ├── services.routes.js    # Services endpoints
│   │   └── activity.routes.js    # Activity endpoints
│   ├── websocket/
│   │   └── handler.js            # WebSocket events
│   ├── server.js                 # Express app
│   └── package.json
├── ui/
│   ├── src/
│   │   ├── components/
│   │   │   ├── HealthIndicators.jsx
│   │   │   ├── ServiceNetwork.jsx
│   │   │   ├── ActivityFeed.jsx
│   │   │   ├── CouplingMetrics.jsx
│   │   │   └── ConflictHeatmap.jsx
│   │   ├── pages/
│   │   │   └── Dashboard.jsx
│   │   ├── services/
│   │   │   └── api.js
│   │   ├── styles/
│   │   │   ├── Dashboard.css
│   │   │   └── components.css
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── index.jsx
│   │   └── index.css
│   ├── public/
│   │   └── index.html
│   └── package.json
├── docker-compose.yml
├── Dockerfile.api
├── Dockerfile.watcher
└── package.json (root)
```

## 🔧 Configuration

### Environment Variables

**API Service**
```
NODE_ENV=development
PORT=3001
LOG_LEVEL=debug
REDIS_URL=redis://redis:6379
NEO_MCP_PATH=/app/ide/mcp_neo_server.py
PYTHONPATH=/app
```

**UI Service**
```
REACT_APP_API_URL=http://localhost:3001
REACT_APP_WS_URL=ws://localhost:3001
```

**Activity Watcher**
```
REDIS_URL=redis://redis:6379
ACTIVITY_LOG_PATH=/app/.devsync/activity-log.json
```

## 📈 Performance

### Caching Strategy
- **Real-time** (60s): Conflict checks
- **Near-real-time** (300s): Coupling metrics, service graph
- **Long-term** (3600s): Entropy analysis
- **Historical** (21600s): Metric snapshots

### Broadcast Frequency
- Overview metrics: Every 10 seconds
- Activity feed: Every 30 seconds
- Service graph: Every 60 seconds

### Optimization Techniques
- Connection pooling (Redis)
- Rate limiting (100 req/15min per IP)
- Selective subscriptions (Socket.io rooms)
- Lazy loading of drill-downs

## 🧪 Testing

```bash
# API tests
cd api
npm test

# UI tests
cd ../ui
npm test

# Integration test (full stack)
docker-compose up --abort-on-container-exit
```

## 🐛 Troubleshooting

### Redis Connection Failed
```bash
# Check Redis is running
docker-compose ps redis

# View Redis logs
docker-compose logs redis
```

### Neo MCP Connection Failed
```bash
# Check Neo server is running
python3 -m ide.mcp_neo_server

# Verify PYTHONPATH
export PYTHONPATH=/absolute/path/to/Neo
```

### UI Not Updating
```bash
# Check WebSocket connection
open http://localhost:3000
# Open DevTools → Network → WS
# Should show Socket.io connection active
```

## 🚢 Deployment

### Docker Compose Production
```yaml
# Adjust environment variables in docker-compose.yml
NODE_ENV: production
LOG_LEVEL: info
REDIS_URL: redis://your-redis-host:6379
```

### Kubernetes
```bash
# Build images
docker build -f Dockerfile.api -t neo-dashboard-api .
docker build -f ui/Dockerfile -t neo-dashboard-ui .

# Deploy using provided k8s manifests (future)
kubectl apply -f k8s/
```

## 📚 Next Steps

### Phase 2: Intelligence Layer
- Entropy deep-dive component
- Blast radius explorer
- Conflict decision tree
- Historical trend analysis

### Phase 3: Polish
- Advanced filtering (service, risk level, time range)
- Drill-down to code snippets
- Export reports (PDF/CSV)
- Dark/light theme toggle
- Mobile responsiveness

### Future Enhancements
- Slack integration
- GitHub actions trigger
- Custom alerts and webhooks
- Team multi-tenancy
- Audit logging

## 📝 License

MIT - See LICENSE in project root

---

**Built with ❤️ for better multi-developer coordination**
