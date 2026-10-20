#!/usr/bin/env node
/**
 * Activity Watcher
 * Watches the activity log and invalidates relevant caches
 */

const fs = require('fs');
const path = require('path');
const redis = require('redis');

const ACTIVITY_LOG_PATH = process.env.ACTIVITY_LOG_PATH || '/app/.devsync/activity-log.json';
const REDIS_URL = process.env.REDIS_URL || 'redis://localhost:6379';

const redisClient = redis.createClient({ url: REDIS_URL });

const logger = {
  info: (...args) => console.log('[INFO]', new Date().toISOString(), ...args),
  error: (...args) => console.error('[ERROR]', new Date().toISOString(), ...args)
};

async function invalidateCaches() {
  try {
    // Invalidate activity-related caches
    const keys = await redisClient.keys('neo:activity:*');
    const graphKeys = await redisClient.keys('neo:graph:*');
    const dashboardKeys = await redisClient.keys('neo:dashboard:*');

    const allKeys = [...keys, ...graphKeys, ...dashboardKeys];

    if (allKeys.length > 0) {
      await redisClient.del(allKeys);
      logger.info(`Invalidated ${allKeys.length} cache entries`);
    }
  } catch (err) {
    logger.error('Cache invalidation error:', err);
  }
}

async function watchActivityLog() {
  if (!fs.existsSync(ACTIVITY_LOG_PATH)) {
    logger.info(`Activity log not found, waiting for creation: ${ACTIVITY_LOG_PATH}`);
  }

  // Watch the parent directory since the file might not exist yet
  const dir = path.dirname(ACTIVITY_LOG_PATH);

  let lastMtime = 0;

  // Poll for changes every 5 seconds
  setInterval(() => {
    try {
      if (fs.existsSync(ACTIVITY_LOG_PATH)) {
        const stat = fs.statSync(ACTIVITY_LOG_PATH);
        if (stat.mtime.getTime() > lastMtime) {
          lastMtime = stat.mtime.getTime();
          logger.info('Activity log changed, invalidating caches');
          invalidateCaches();
        }
      }
    } catch (err) {
      logger.error('Error checking activity log:', err);
    }
  }, 5000);
}

async function main() {
  try {
    // Connect to Redis
    await redisClient.connect();
    logger.info('Redis connected');

    // Start watching
    watchActivityLog();
    logger.info('Activity watcher started');
  } catch (err) {
    logger.error('Startup error:', err);
    process.exit(1);
  }
}

// Graceful shutdown
process.on('SIGTERM', () => {
  logger.info('SIGTERM received, shutting down');
  redisClient.quit().then(() => {
    logger.info('Activity watcher stopped');
    process.exit(0);
  }).catch(err => {
    logger.error('Shutdown error:', err);
    process.exit(1);
  });
});

main();
