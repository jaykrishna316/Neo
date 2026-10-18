/**
 * Dashboard Routes
 * Main dashboard endpoints
 */

module.exports = (aggregator, logger) => {
  const router = require('express').Router();

  // GET /api/dashboard/overview
  router.get('/overview', async (req, res) => {
    try {
      const overview = await aggregator.getDashboardOverview();
      res.json({ success: true, data: overview });
    } catch (err) {
      logger.error('Dashboard overview error:', err);
      res.status(500).json({
        success: false,
        error: 'Failed to fetch overview',
        message: err.message
      });
    }
  });

  // GET /api/dashboard/graph
  router.get('/graph', async (req, res) => {
    try {
      const graph = await aggregator.getServicesGraph();
      res.json({ success: true, data: graph });
    } catch (err) {
      logger.error('Dashboard graph error:', err);
      res.status(500).json({
        success: false,
        error: 'Failed to fetch service graph',
        message: err.message
      });
    }
  });

  // GET /api/dashboard/heatmap
  router.get('/heatmap', async (req, res) => {
    try {
      const heatmap = await aggregator.getConflictHeatmap();
      res.json({ success: true, data: heatmap });
    } catch (err) {
      logger.error('Dashboard heatmap error:', err);
      res.status(500).json({
        success: false,
        error: 'Failed to fetch conflict heatmap',
        message: err.message
      });
    }
  });

  // GET /api/dashboard/metrics/:metric
  router.get('/metrics/:metric', async (req, res) => {
    try {
      const { metric } = req.params;
      const { points = 100 } = req.query;
      const data = await aggregator.getMetricsTimeSeries(metric, parseInt(points));
      res.json({ success: true, data });
    } catch (err) {
      logger.error('Dashboard metrics error:', err);
      res.status(500).json({
        success: false,
        error: 'Failed to fetch metrics',
        message: err.message
      });
    }
  });

  // GET /api/dashboard/cache/stats
  router.get('/cache/stats', async (req, res) => {
    try {
      const stats = await aggregator.cache.getStats();
      const conflictStats = aggregator.conflictCache.getAccessStats();
      res.json({
        success: true,
        data: {
          redis: stats,
          conflicts: conflictStats,
          timestamp: new Date().toISOString()
        }
      });
    } catch (err) {
      logger.error('Cache stats error:', err);
      res.status(500).json({
        success: false,
        error: 'Failed to fetch cache stats',
        message: err.message
      });
    }
  });

  // POST /api/dashboard/cache/invalidate/:prefix
  router.post('/cache/invalidate/:prefix', async (req, res) => {
    try {
      const { prefix } = req.params;
      const count = await aggregator.cache.invalidateByPattern(`${prefix}:*`);
      res.json({
        success: true,
        data: {
          invalidated: count,
          prefix,
          timestamp: new Date().toISOString()
        }
      });
    } catch (err) {
      logger.error('Cache invalidation error:', err);
      res.status(500).json({
        success: false,
        error: 'Failed to invalidate cache',
        message: err.message
      });
    }
  });

  // POST /api/dashboard/cache/clear
  router.post('/cache/clear', async (req, res) => {
    try {
      const count = await aggregator.cache.invalidateByPattern('neo:*');
      aggregator.conflictCache.resetAccessPatterns();
      res.json({
        success: true,
        data: {
          invalidated: count,
          message: 'All caches cleared',
          timestamp: new Date().toISOString()
        }
      });
    } catch (err) {
      logger.error('Cache clear error:', err);
      res.status(500).json({
        success: false,
        error: 'Failed to clear cache',
        message: err.message
      });
    }
  });

  return router;
};
