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

  return router;
};
