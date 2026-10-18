// Simplified Mock API server - no dependencies required except built-ins
const express = require('express');
const cors = require('cors');
const rateLimit = require('express-rate-limit');
const http = require('http');
const socketIo = require('socket.io');

// Mock data
const mockData = {
  overview: {
    status: { status: 'ok', message: 'All systems operational', lastCheck: new Date().toISOString() },
    conflict_summary: { total_conflicts: 12, high_risk_files: 3, risk_level: 'MEDIUM' },
    activity_summary: { total_entries: 156, active_developers: 4, last_activity: new Date(Date.now() - 5 * 60000).toISOString() },
    entropy_summary: { current_entropy: 0.72, threshold: 0.65, meaningful_data_percent: 94, architectural_issues: 8, data_window_days: 90, last_update: new Date().toISOString() }
  },
  graph: {
    nodes: [
      { id: 'dashboard', label: 'Dashboard UI', type: 'service', size: 30 },
      { id: 'api', label: 'API Server', type: 'service', size: 28 },
      { id: 'core', label: 'Neo Core', type: 'service', size: 32 },
      { id: 'cache', label: 'Redis Cache', type: 'service', size: 20 },
      { id: 'activity', label: 'Activity Log', type: 'service', size: 22 }
    ],
    links: [
      { source: 'dashboard', target: 'api', value: 0.85, label: 'REST API' },
      { source: 'api', target: 'core', value: 0.92, label: 'Conflict Detection' },
      { source: 'api', target: 'cache', value: 0.78, label: 'Query Cache' },
      { source: 'core', target: 'activity', value: 0.88, label: 'Log Activity' },
      { source: 'dashboard', target: 'cache', value: 0.65, label: 'Real-time Data' }
    ]
  },
  activity: {
    entries: [
      { timestamp: new Date(Date.now() - 1 * 60000).toISOString(), agent_id: 'claude-haiku-frontend', file_path: 'dashboard/ui/src/components/Dashboard.jsx', intent: 'Add real-time WebSocket support', intent_category: 'modification' },
      { timestamp: new Date(Date.now() - 3 * 60000).toISOString(), agent_id: 'claude-opus-backend', file_path: 'dashboard/api/services/neoClient.js', intent: 'Optimize conflict detection response time', intent_category: 'modification' },
      { timestamp: new Date(Date.now() - 7 * 60000).toISOString(), agent_id: 'claude-sonnet-data', file_path: 'core/analysis/entropy.py', intent: 'Implement 90-day rolling window analysis', intent_category: 'modification' },
      { timestamp: new Date(Date.now() - 15 * 60000).toISOString(), agent_id: 'claude-haiku-frontend', file_path: 'dashboard/ui/src/components/BlastRadiusExplorer.jsx', intent: 'Create impact visualization component', intent_category: 'creation' },
      { timestamp: new Date(Date.now() - 32 * 60000).toISOString(), agent_id: 'claude-opus-backend', file_path: 'dashboard/api/routes/services.routes.js', intent: 'Add blast radius estimation endpoint', intent_category: 'creation' }
    ]
  },
  heatmap: {
    stats: { high_risk_files: 3, medium_risk_files: 8, low_risk_files: 24 },
    heatmap: [
      { file: 'dashboard/ui/src/pages/Dashboard.jsx', service: 'dashboard', risk_level: 'HIGH', conflict_count: 4, developers: ['claude-haiku-frontend', 'human-reviewer'], last_modified: new Date(Date.now() - 5 * 60000).toISOString() },
      { file: 'core/conflict_detection.py', service: 'core', risk_level: 'HIGH', conflict_count: 3, developers: ['claude-opus-backend', 'claude-sonnet-data'], last_modified: new Date(Date.now() - 20 * 60000).toISOString() },
      { file: 'dashboard/api/services/neoClient.js', service: 'api', risk_level: 'HIGH', conflict_count: 2, developers: ['claude-opus-backend'], last_modified: new Date(Date.now() - 45 * 60000).toISOString() }
    ]
  }
};

const app = express();
const server = http.createServer(app);
const io = socketIo(server, { cors: { origin: '*', methods: ['GET', 'POST'] } });

app.use(express.json());
app.use(cors());

const limiter = rateLimit({ windowMs: 15 * 60 * 1000, max: 100 });
app.use(limiter);

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', mode: 'mock', timestamp: new Date().toISOString() });
});

// Dashboard endpoints
app.get('/api/dashboard/overview', (req, res) => res.json(mockData.overview));
app.get('/api/dashboard/graph', (req, res) => res.json(mockData.graph));
app.get('/api/dashboard/heatmap', (req, res) => res.json(mockData.heatmap));
app.get('/api/activity/feed', (req, res) => {
  const limit = parseInt(req.query.limit) || 50;
  res.json({ entries: mockData.activity.entries.slice(0, limit), total: mockData.activity.entries.length });
});

// WebSocket
io.on('connection', (socket) => {
  console.log('✅ Client connected:', socket.id);

  socket.emit('metrics:overview', mockData.overview);
  socket.emit('graph:update', mockData.graph);
  socket.emit('activity:update', mockData.activity);
  socket.emit('refresh:heatmap', mockData.heatmap);

  const updateInterval = setInterval(() => {
    mockData.overview.entropy_summary.current_entropy += (Math.random() - 0.5) * 0.05;
    mockData.overview.entropy_summary.current_entropy = Math.max(0, Math.min(1, mockData.overview.entropy_summary.current_entropy));
    socket.emit('metrics:overview', mockData.overview);
  }, 30000);

  socket.on('refresh', (data) => {
    console.log('🔄 Refresh requested:', data.section);
    switch (data.section) {
      case 'overview': socket.emit('metrics:overview', mockData.overview); break;
      case 'graph': socket.emit('graph:update', mockData.graph); break;
      case 'activity': socket.emit('activity:update', mockData.activity); break;
      case 'heatmap': socket.emit('refresh:heatmap', mockData.heatmap); break;
    }
  });

  socket.on('disconnect', () => {
    console.log('👋 Client disconnected:', socket.id);
    clearInterval(updateInterval);
  });
});

const PORT = process.env.PORT || 3001;
server.listen(PORT, () => {
  console.log(`\n🚀 Neo Mock Dashboard API running on http://localhost:${PORT}`);
  console.log('📡 Mode: MOCK DATA (no Neo MCP server required)\n');
});
