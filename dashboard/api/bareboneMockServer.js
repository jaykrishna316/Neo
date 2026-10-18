// Bare-bones Mock API server using only Node.js built-ins
const http = require('http');
const url = require('url');

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
      { id: 'dashboard', label: 'Dashboard UI', size: 30 },
      { id: 'api', label: 'API Server', size: 28 },
      { id: 'core', label: 'Neo Core', size: 32 },
      { id: 'cache', label: 'Redis Cache', size: 20 },
      { id: 'activity', label: 'Activity Log', size: 22 }
    ],
    links: [
      { source: 'dashboard', target: 'api', value: 0.85 },
      { source: 'api', target: 'core', value: 0.92 },
      { source: 'api', target: 'cache', value: 0.78 },
      { source: 'core', target: 'activity', value: 0.88 },
      { source: 'dashboard', target: 'cache', value: 0.65 }
    ]
  },
  activity: {
    entries: [
      { timestamp: new Date(Date.now() - 60000).toISOString(), agent_id: 'claude-haiku-frontend', file_path: 'dashboard/ui/src/components/Dashboard.jsx', intent: 'Add WebSocket support', intent_category: 'modification' },
      { timestamp: new Date(Date.now() - 180000).toISOString(), agent_id: 'claude-opus-backend', file_path: 'dashboard/api/services/neoClient.js', intent: 'Optimize response time', intent_category: 'modification' },
      { timestamp: new Date(Date.now() - 420000).toISOString(), agent_id: 'claude-sonnet-data', file_path: 'core/analysis/entropy.py', intent: '90-day rolling window', intent_category: 'modification' }
    ]
  },
  heatmap: {
    stats: { high_risk_files: 3, medium_risk_files: 8, low_risk_files: 24 },
    heatmap: [
      { file: 'dashboard/ui/src/pages/Dashboard.jsx', service: 'dashboard', risk_level: 'HIGH', developers: ['claude-haiku', 'human-reviewer'] },
      { file: 'core/conflict_detection.py', service: 'core', risk_level: 'HIGH', developers: ['claude-opus', 'claude-sonnet'] },
      { file: 'dashboard/api/services/neoClient.js', service: 'api', risk_level: 'HIGH', developers: ['claude-opus'] }
    ]
  }
};

const server = http.createServer((req, res) => {
  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  res.setHeader('Content-Type', 'application/json');

  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  const parsedUrl = url.parse(req.url, true);
  const pathname = parsedUrl.pathname;

  // Routes
  if (pathname === '/health') {
    res.writeHead(200);
    res.end(JSON.stringify({ status: 'ok', mode: 'mock', timestamp: new Date().toISOString() }));
  }
  else if (pathname === '/api/dashboard/overview') {
    res.writeHead(200);
    res.end(JSON.stringify(mockData.overview));
  }
  else if (pathname === '/api/dashboard/graph') {
    res.writeHead(200);
    res.end(JSON.stringify(mockData.graph));
  }
  else if (pathname === '/api/dashboard/heatmap') {
    res.writeHead(200);
    res.end(JSON.stringify(mockData.heatmap));
  }
  else if (pathname === '/api/activity/feed') {
    res.writeHead(200);
    res.end(JSON.stringify({ entries: mockData.activity.entries, total: mockData.activity.entries.length }));
  }
  else {
    res.writeHead(404);
    res.end(JSON.stringify({ error: 'Not found' }));
  }
});

const PORT = 3001;
server.listen(PORT, () => {
  console.log('\n🚀 Neo Mock Dashboard API running on http://localhost:' + PORT);
  console.log('📡 Mode: MOCK DATA (no dependencies required)\n');
});

// Handle graceful shutdown
process.on('SIGINT', () => {
  console.log('\n👋 Shutting down...');
  server.close();
  process.exit(0);
});
