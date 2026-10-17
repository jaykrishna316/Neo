// Mock API server for dashboard visualization
require('dotenv').config();
const express = require('express');
const cors = require('cors');
const rateLimit = require('express-rate-limit');
const http = require('http');
const socketIo = require('socket.io');
const mockData = require('./mockData');

const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
  cors: { origin: '*', methods: ['GET', 'POST'] }
});

// Middleware
app.use(express.json());
app.use(cors());
app.use(rateLimit({ windowMs: 15 * 60 * 1000, max: 100 }));

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', mode: 'mock', timestamp: new Date().toISOString() });
});

// Dashboard endpoints
app.get('/api/dashboard/overview', (req, res) => {
  res.json(mockData.overview);
});

app.get('/api/dashboard/graph', (req, res) => {
  res.json(mockData.graph);
});

app.get('/api/dashboard/heatmap', (req, res) => {
  res.json(mockData.heatmap);
});

app.get('/api/activity/feed', (req, res) => {
  const limit = parseInt(req.query.limit) || 50;
  res.json({
    entries: mockData.activity.entries.slice(0, limit),
    total: mockData.activity.entries.length
  });
});

// Additional endpoints for drill-down components
app.get('/api/entropy/analysis', (req, res) => {
  res.json(mockData.entropy);
});

app.get('/api/blast-radius/:file', (req, res) => {
  res.json(mockData.blastRadius);
});

app.get('/api/trends/:file', (req, res) => {
  res.json(mockData.trends);
});

// WebSocket: Real-time updates
io.on('connection', (socket) => {
  console.log('Client connected:', socket.id);

  // Send initial data
  socket.emit('metrics:overview', mockData.overview);
  socket.emit('graph:update', mockData.graph);
  socket.emit('activity:update', mockData.activity);
  socket.emit('refresh:heatmap', mockData.heatmap);

  // Simulate periodic updates (every 30 seconds)
  const updateInterval = setInterval(() => {
    // Add slight variation to entropy
    mockData.overview.entropy_summary.current_entropy += (Math.random() - 0.5) * 0.05;
    mockData.overview.entropy_summary.current_entropy = Math.max(0, Math.min(1, mockData.overview.entropy_summary.current_entropy));

    socket.emit('metrics:overview', mockData.overview);

    // Add new activity entry occasionally
    if (Math.random() < 0.3) {
      const newEntry = {
        timestamp: new Date().toISOString(),
        agent_id: ['claude-haiku-frontend', 'claude-opus-backend', 'claude-sonnet-data'][Math.floor(Math.random() * 3)],
        file_path: mockData.heatmap.heatmap[Math.floor(Math.random() * mockData.heatmap.heatmap.length)].file,
        intent: 'Real-time activity update',
        intent_category: ['modification', 'creation'][Math.floor(Math.random() * 2)]
      };
      mockData.activity.entries.unshift(newEntry);
      socket.emit('activity:update', mockData.activity);
    }
  }, 30000);

  // Handle refresh requests
  socket.on('refresh', (data) => {
    console.log('Refresh requested for:', data.section);
    switch (data.section) {
      case 'overview':
        socket.emit('metrics:overview', mockData.overview);
        break;
      case 'graph':
        socket.emit('graph:update', mockData.graph);
        break;
      case 'activity':
        socket.emit('activity:update', mockData.activity);
        break;
      case 'heatmap':
        socket.emit('refresh:heatmap', mockData.heatmap);
        break;
    }
  });

  socket.on('disconnect', () => {
    console.log('Client disconnected:', socket.id);
    clearInterval(updateInterval);
  });
});

// Start server
const PORT = process.env.PORT || 3001;
server.listen(PORT, () => {
  console.log(`Mock Dashboard API running on http://localhost:${PORT}`);
  console.log('Mode: MOCK DATA (no Neo MCP server required)');
});
