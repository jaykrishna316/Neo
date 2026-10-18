/**
 * Conflict Cache Manager
 * Intelligent caching for conflict detection results with activity-pattern-based invalidation
 */

class ConflictCacheManager {
  constructor(cacheService, logger) {
    this.cache = cacheService;
    this.logger = logger;
    this.activityPatterns = new Map();
    this.accessPatterns = new Map();
    this.invalidationQueue = new Set();
  }

  buildCacheKey(agentId, filePath, intent) {
    return `${agentId}|${filePath}|${intent}`;
  }

  async getOrCheckConflict(neoClient, agentId, filePath, intent, region = 'all') {
    const cacheKey = this.buildCacheKey(agentId, filePath, intent);

    // Try cache first
    const cached = await this.cache.getConflictCheck(cacheKey);
    if (cached) {
      this.recordAccessPattern(filePath, 'hit');
      this.logger.debug(`Conflict cache hit: ${cacheKey}`);
      return cached;
    }

    // Cache miss - fetch from Neo
    this.logger.debug(`Conflict cache miss: ${cacheKey}`);
    const result = await neoClient.checkConflicts(agentId, filePath, intent, region);

    // Cache the result
    await this.cache.cacheConflictCheck(cacheKey, result);
    this.recordAccessPattern(filePath, 'miss');

    return result;
  }

  async getOrCheckMultipleConflicts(neoClient, entries) {
    const results = [];
    const uncachedEntries = [];
    const cacheKeyMap = new Map();

    // Phase 1: Check cache for all entries
    for (const entry of entries) {
      const { agentId, filePath, intent, region = 'all' } = entry;
      const cacheKey = this.buildCacheKey(agentId, filePath, intent);
      cacheKeyMap.set(cacheKey, entry);

      const cached = await this.cache.getConflictCheck(cacheKey);
      if (cached) {
        results.push({ ...entry, conflict: cached, source: 'cache' });
        this.recordAccessPattern(filePath, 'hit');
      } else {
        uncachedEntries.push({ cacheKey, ...entry });
        this.recordAccessPattern(filePath, 'miss');
      }
    }

    // Phase 2: Batch fetch uncached entries
    if (uncachedEntries.length > 0) {
      this.logger.debug(`Batch fetching ${uncachedEntries.length} uncached conflict checks`);

      const fetchPromises = uncachedEntries.map(async (entry) => {
        const result = await neoClient.checkConflicts(
          entry.agentId,
          entry.filePath,
          entry.intent,
          entry.region
        );
        await this.cache.cacheConflictCheck(entry.cacheKey, result);
        return { ...entry, conflict: result, source: 'neo' };
      });

      const fetched = await Promise.all(fetchPromises);
      results.push(...fetched);
    }

    return results;
  }

  recordAccessPattern(filePath, type) {
    const key = filePath;
    if (!this.accessPatterns.has(key)) {
      this.accessPatterns.set(key, { hits: 0, misses: 0, lastAccess: Date.now() });
    }

    const pattern = this.accessPatterns.get(key);
    if (type === 'hit') {
      pattern.hits++;
    } else {
      pattern.misses++;
    }
    pattern.lastAccess = Date.now();
  }

  getAccessStats() {
    const stats = Array.from(this.accessPatterns.entries())
      .map(([filePath, pattern]) => ({
        filePath,
        ...pattern,
        hitRate: pattern.hits / (pattern.hits + pattern.misses),
        totalAccesses: pattern.hits + pattern.misses
      }))
      .sort((a, b) => b.totalAccesses - a.totalAccesses);

    return {
      totalFiles: stats.length,
      totalAccesses: stats.reduce((sum, s) => sum + s.totalAccesses, 0),
      averageHitRate: stats.length > 0
        ? stats.reduce((sum, s) => sum + s.hitRate, 0) / stats.length
        : 0,
      topFiles: stats.slice(0, 10)
    };
  }

  async invalidateFileConflicts(filePath) {
    // Invalidate all conflict checks for a specific file
    await this.cache.invalidatePattern(`conflict:${filePath}|*`);
    this.logger.info(`Invalidated all conflict caches for file: ${filePath}`);
  }

  async invalidateServiceConflicts(service) {
    // Invalidate all conflict checks for a service (pattern match)
    const pattern = `conflict:${service}/*`;
    await this.cache.invalidatePattern(pattern);
    this.logger.info(`Invalidated all conflict caches for service: ${service}`);
  }

  async invalidateAgentConflicts(agentId) {
    // Invalidate all conflict checks for a specific agent
    const pattern = `conflict:${agentId}|*`;
    await this.cache.invalidatePattern(pattern);
    this.logger.info(`Invalidated all conflict caches for agent: ${agentId}`);
  }

  async invalidateBasedOnActivityChange(activityEntry) {
    // Smart invalidation based on activity patterns
    const { agent_id, file_path, intent_category } = activityEntry;

    // Invalidate direct file conflicts
    await this.invalidateFileConflicts(file_path);

    // Invalidate related service conflicts (extract service from path)
    const service = this.extractService(file_path);
    if (service) {
      await this.invalidateServiceConflicts(service);
    }

    // Invalidate agent conflicts to force re-evaluation
    await this.invalidateAgentConflicts(agent_id);

    this.logger.info(`Invalidated caches based on activity: ${agent_id}/${file_path}`);
  }

  extractService(filePath) {
    const parts = filePath.split('/');
    return parts.length > 0 ? parts[0] : null;
  }

  async prewarmCache(neoClient, files) {
    // Prewarm cache for frequently accessed files
    this.logger.info(`Prewarming cache for ${files.length} files`);

    const prewarmPromises = files.map(async (file) => {
      try {
        const conflict = await neoClient.checkConflicts('prewarm', file, 'analysis');
        await this.cache.cacheConflictCheck(this.buildCacheKey('prewarm', file, 'analysis'), conflict);
        this.logger.debug(`Prewarmed cache for: ${file}`);
      } catch (err) {
        this.logger.error(`Failed to prewarm cache for ${file}:`, err);
      }
    });

    await Promise.all(prewarmPromises);
  }

  resetAccessPatterns() {
    this.accessPatterns.clear();
    this.logger.info('Access patterns reset');
  }
}

module.exports = (cacheService, logger) =>
  new ConflictCacheManager(cacheService, logger);
