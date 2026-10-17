/**
 * Cache Service
 * Multi-tier Redis caching with TTL management
 */

const TTL = {
  SHORT: 60,        // 1 minute - real-time conflict data
  MEDIUM: 300,      // 5 minutes - coupling metrics
  LONG: 3600,       // 1 hour - entropy analysis (older data)
  VERY_LONG: 21600  // 6 hours - historical snapshots
};

class CacheService {
  constructor(redisClient, logger) {
    this.redis = redisClient;
    this.logger = logger;
    this.namespace = 'neo';
  }

  key(prefix, identifier) {
    return `${this.namespace}:${prefix}:${identifier}`;
  }

  async get(prefix, identifier) {
    try {
      const cacheKey = this.key(prefix, identifier);
      const cached = await this.redis.get(cacheKey);
      if (cached) {
        this.logger.debug(`Cache hit: ${cacheKey}`);
        return JSON.parse(cached);
      }
      return null;
    } catch (err) {
      this.logger.error('Cache get error:', err);
      return null;
    }
  }

  async set(prefix, identifier, data, ttl = TTL.MEDIUM) {
    try {
      const cacheKey = this.key(prefix, identifier);
      await this.redis.setEx(cacheKey, ttl, JSON.stringify(data));
      this.logger.debug(`Cache set: ${cacheKey} (TTL: ${ttl}s)`);
    } catch (err) {
      this.logger.error('Cache set error:', err);
    }
  }

  async invalidate(prefix, identifier) {
    try {
      const cacheKey = this.key(prefix, identifier);
      await this.redis.del(cacheKey);
      this.logger.debug(`Cache invalidated: ${cacheKey}`);
    } catch (err) {
      this.logger.error('Cache invalidate error:', err);
    }
  }

  async invalidatePattern(prefix) {
    try {
      const pattern = this.key(prefix, '*');
      const keys = await this.redis.keys(pattern);
      if (keys.length > 0) {
        await this.redis.del(keys);
        this.logger.debug(`Cache invalidated ${keys.length} keys matching: ${pattern}`);
      }
    } catch (err) {
      this.logger.error('Cache pattern invalidate error:', err);
    }
  }

  async getOrSet(prefix, identifier, fetchFn, ttl = TTL.MEDIUM) {
    let cached = await this.get(prefix, identifier);
    if (cached) {
      return cached;
    }

    try {
      const data = await fetchFn();
      await this.set(prefix, identifier, data, ttl);
      return data;
    } catch (err) {
      this.logger.error('getOrSet error:', err);
      throw err;
    }
  }

  // Specific cache operations for dashboard
  async cacheConflictCheck(filePath, data) {
    await this.set('conflict', filePath, data, TTL.SHORT);
  }

  async cacheBlastRadius(filePath, data) {
    await this.set('blast_radius', filePath, data, TTL.MEDIUM);
  }

  async cacheCouplingTrends(filePath, data) {
    await this.set('coupling_trends', filePath, data, TTL.MEDIUM);
  }

  async cacheEntropyCoupling(data) {
    await this.set('entropy', 'global', data, TTL.LONG);
  }

  async cacheActivitySnapshot(data) {
    await this.set('activity', 'snapshot', data, TTL.SHORT);
  }

  async cacheServiceGraph(data) {
    await this.set('graph', 'services', data, TTL.MEDIUM);
  }

  async getConflictCheck(filePath) {
    return this.get('conflict', filePath);
  }

  async getBlastRadius(filePath) {
    return this.get('blast_radius', filePath);
  }

  async getCouplingTrends(filePath) {
    return this.get('coupling_trends', filePath);
  }

  async getEntropyCoupling() {
    return this.get('entropy', 'global');
  }

  async getActivitySnapshot() {
    return this.get('activity', 'snapshot');
  }

  async getServiceGraph() {
    return this.get('graph', 'services');
  }

  // Metrics tracking
  async recordMetric(metricName, value, timestamp = Date.now()) {
    try {
      const key = this.key('metric', metricName);
      const entry = { value, timestamp };
      await this.redis.lPush(key, JSON.stringify(entry));
      // Keep last 1000 metrics
      await this.redis.lTrim(key, 0, 999);
      // Expire old metrics after 90 days
      await this.redis.expire(key, 7776000);
    } catch (err) {
      this.logger.error('Metric recording error:', err);
    }
  }

  async getMetrics(metricName, count = 100) {
    try {
      const key = this.key('metric', metricName);
      const metrics = await this.redis.lRange(key, 0, count - 1);
      return metrics.map(m => JSON.parse(m));
    } catch (err) {
      this.logger.error('Metrics fetch error:', err);
      return [];
    }
  }

  // Cache stats for monitoring
  async getStats() {
    try {
      const info = await this.redis.info('keyspace');
      const keys = await this.redis.keys(`${this.namespace}:*`);
      return {
        namespace: this.namespace,
        total_keys: keys.length,
        redis_info: info
      };
    } catch (err) {
      this.logger.error('Cache stats error:', err);
      return { namespace: this.namespace, total_keys: 0 };
    }
  }
}

module.exports = (redisClient, logger) => new CacheService(redisClient, logger);
