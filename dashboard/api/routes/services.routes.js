/**
 * Services Routes
 * Service coupling and metrics endpoints
 */

module.exports = (aggregator, logger) => {
  const router = require('express').Router();

  // GET /api/services/coupling
  router.get('/coupling', async (req, res) => {
    try {
      const graph = await aggregator.getServicesGraph();
      res.json({
        success: true,
        data: {
          nodes: graph.nodes,
          links: graph.links,
          timestamp: graph.timestamp
        }
      });
    } catch (err) {
      logger.error('Services coupling error:', err);
      res.status(500).json({
        success: false,
        error: 'Failed to fetch service coupling',
        message: err.message
      });
    }
  });

  // GET /api/services/:service/trends
  router.get('/:service/trends', async (req, res) => {
    try {
      const { service } = req.params;
      const { window = 90 } = req.query;
      const windowInt = parseInt(window);

      // Try cache first
      const cacheKey = `trends:${service}:${windowInt}`;
      let trends = await aggregator.cache.get('trends', cacheKey);

      if (!trends) {
        // Fetch from Neo
        trends = await aggregator.neo.getCouplingTrends(service, windowInt);
        // Cache for 5 minutes
        await aggregator.cache.set('trends', cacheKey, trends, 300);
      }

      res.json({
        success: true,
        data: {
          service,
          window: windowInt,
          ...trends,
          fromCache: !!trends
        }
      });
    } catch (err) {
      logger.error('Service trends error:', err);
      res.status(500).json({
        success: false,
        error: 'Failed to fetch service trends',
        message: err.message
      });
    }
  });

  // GET /api/services/:service/blast-radius
  router.get('/:service/blast-radius', async (req, res) => {
    try {
      const { service } = req.params;
      const { change_type = 'modification' } = req.query;

      // Try cache first
      const cacheKey = `radius:${service}:${change_type}`;
      let radius = await aggregator.cache.get('blast_radius', cacheKey);

      if (!radius) {
        // Fetch from Neo
        radius = await aggregator.neo.calculateBlastRadius(
          'dashboard',
          service,
          change_type
        );
        // Cache for 10 minutes
        await aggregator.cache.set('blast_radius', cacheKey, radius, 600);
      }

      res.json({
        success: true,
        data: {
          service,
          change_type,
          ...radius,
          fromCache: !!radius
        }
      });
    } catch (err) {
      logger.error('Service blast radius error:', err);
      res.status(500).json({
        success: false,
        error: 'Failed to calculate blast radius',
        message: err.message
      });
    }
  });

  // GET /api/services/entropy/analysis
  router.get('/entropy/analysis', async (req, res) => {
    try {
      const { window = 90 } = req.query;
      const windowInt = parseInt(window);

      // Try cache first
      const cacheKey = `analysis:${windowInt}`;
      let analysis = await aggregator.cache.get('entropy', cacheKey);

      if (!analysis) {
        // Fetch from Neo
        analysis = await aggregator.neo.analyzeEntropyCoupling(windowInt);
        // Cache for 1 hour
        await aggregator.cache.set('entropy', cacheKey, analysis, 3600);
      }

      res.json({
        success: true,
        data: {
          window: windowInt,
          ...analysis,
          fromCache: !!analysis
        }
      });
    } catch (err) {
      logger.error('Entropy analysis error:', err);
      res.status(500).json({
        success: false,
        error: 'Failed to analyze entropy',
        message: err.message
      });
    }
  });

  return router;
};
