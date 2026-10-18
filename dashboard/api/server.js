#!/usr/bin/env node
/**
 * Neo Dashboard API Server
 * Aggregates MCP tool calls and real-time data for the dashboard
 */

const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const redis = require('redis');
const dotenv = require('dotenv');
const path = require('path');

dotenv.config();

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
  cors: {
    origin: process.env.FRONTEND_URL || 'http://localhost:3000',
    methods: ['GET', 'POST']
  }
});

// Configuration
const PORT = process.env.PORT || 3001;
const NODE_ENV = process.env.NODE_ENV || 'development';
const LOG_LEVEL = process.env.LOG_LEVEL || 'info';

// Redis client
const redisClient = redis.createClient({
  url: process.env.REDIS_URL || 'redis://localhost:6379'
});

// Middleware
app.use(helmet());
app.use(cors());
app.use(express.json());

// Rate limiter
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // limit each IP to 100 requests per windowMs
  message: 'Too many requests from this IP, please try again later.'
});

app.use('/api/', limiter);

// Logger
const logger = {
  error: (...args) => console.error('[ERROR]', new Date().toISOString(), ...args),
  warn: (...args) => console.warn('[WARN]', new Date().toISOString(), ...args),
  info: (...args) => console.info('[INFO]', new Date().toISOString(), ...args),
  debug: (...args) => LOG_LEVEL === 'debug' && console.log('[DEBUG]', new Date().toISOString(), ...args)
};

// Import services
const NeoClient = require('./services/neoClient');
const cacheService = require('./services/cacheService')(redisClient, logger);
const conflictCacheManager = require('./services/conflictCacheManager')(cacheService, logger);

// Initialize Neo client
let neoClient;
const initializeNeoClient = async () => {
  try {
    neoClient = new NeoClient(logger);
    await neoClient.initialize();
    logger.info('Neo MCP client initialized');
  } catch (err) {
    logger.error('Failed to initialize Neo MCP client:', err);
    // Continue anyway - Neo will be unavailable but dashboard can still run
    neoClient = new NeoClient(logger);
  }
};

const aggregator = require('./services/aggregator')(
  neoClient,
  cacheService,
  conflictCacheManager,
  logger
);

// Import routes
const dashboardRoutes = require('./routes/dashboard.routes');
const servicesRoutes = require('./routes/services.routes');
const activityRoutes = require('./routes/activity.routes');

// WebSocket handler
const websocketHandler = require('./websocket/handler')(io, aggregator, logger);

// Middleware for error handling
const errorHandler = (err, req, res, next) => {
  logger.error('Unhandled error:', err);
  res.status(err.status || 500).json({
    success: false,
    error: err.message,
    ...(NODE_ENV === 'development' && { stack: err.stack })
  });
};

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: Date.now() });
});

// API Routes
app.use('/api/dashboard', dashboardRoutes(aggregator, logger));
app.use('/api/services', servicesRoutes(aggregator, logger));
app.use('/api/activity', activityRoutes(aggregator, logger));

// Error handler (must be last)
app.use(errorHandler);

// WebSocket connection handling
io.on('connection', (socket) => {
  logger.info(`WebSocket client connected: ${socket.id}`);

  // Subscribe to service
  socket.on('subscribe:service', (data) => {
    const { service } = data;
    socket.join(`service:${service}`);
    logger.debug(`Client ${socket.id} subscribed to service: ${service}`);
  });

  // Unsubscribe from service
  socket.on('unsubscribe:service', (data) => {
    const { service } = data;
    socket.leave(`service:${service}`);
    logger.debug(`Client ${socket.id} unsubscribed from service: ${service}`);
  });

  // Request refresh
  socket.on('refresh', async (data) => {
    const { section } = data;
    logger.debug(`Refresh requested for section: ${section}`);
    // Emit refreshed data
    websocketHandler.emitRefresh(socket, section);
  });

  socket.on('disconnect', () => {
    logger.info(`WebSocket client disconnected: ${socket.id}`);
  });
});

// Activity monitoring setup
const setupActivityMonitoring = async () => {
  const fs = require('fs').promises;
  const pathModule = require('path');
  let lastActivityLogMTime = 0;

  const checkActivityLog = async () => {
    try {
      const logPath = pathModule.join(__dirname, '../../.devsync/activity-log.json');
      const stats = await fs.stat(logPath).catch(() => null);

      if (stats && stats.mtime.getTime() > lastActivityLogMTime) {
        lastActivityLogMTime = stats.mtime.getTime();
        const data = await fs.readFile(logPath, 'utf8');
        const activityLog = JSON.parse(data);

        if (activityLog.entries && activityLog.entries.length > 0) {
          const latestEntry = activityLog.entries[activityLog.entries.length - 1];
          await aggregator.handleActivityChange(latestEntry);
        }
      }
    } catch (err) {
      if (err.code !== 'ENOENT') {
        logger.debug('Activity monitoring check error:', err.message);
      }
    }
  };

  setInterval(checkActivityLog, 5000);
};

// Redis connection and startup
(async () => {
  try {
    // Connect to Redis
    await redisClient.connect();
    logger.info('Redis connected');

    // Initialize Neo client
    await initializeNeoClient();

    // Setup activity monitoring
    await setupActivityMonitoring();

    // Start server
    server.listen(PORT, () => {
      logger.info(`Dashboard API Server running on port ${PORT}`);
      logger.info(`Environment: ${NODE_ENV}`);
      logger.info(`WebSocket server ready at http://localhost:${PORT}`);
    });
  } catch (err) {
    logger.error('Startup error:', err);
    process.exit(1);
  }
})();

// Graceful shutdown
process.on('SIGTERM', () => {
  logger.info('SIGTERM received, shutting down gracefully');
  server.close(async () => {
    try {
      if (neoClient) {
        await neoClient.shutdown();
      }
      await redisClient.quit();
      logger.info('Server closed');
      process.exit(0);
    } catch (err) {
      logger.error('Shutdown error:', err);
      process.exit(1);
    }
  });
});

module.exports = { app, server, io };
