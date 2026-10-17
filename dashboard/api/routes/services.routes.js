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

      // For demo, return coupling trends
      const trends = await aggregator.neo.getCouplingTrends(service, parseInt(window));

      res.json({
        success: true,
        data: {
          service,
          window: parseInt(window),
          ...trends
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

      const radius = await aggregator.neo.calculateBlastRadius(
        'dashboard',
        service,
        change_type
      );

      res.json({
        success: true,
        data: {
          service,
          change_type,
          ...radius
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

      const analysis = await aggregator.neo.analyzeEntropyCoupling(parseInt(window));

      res.json({
        success: true,
        data: {
          window: parseInt(window),
          ...analysis
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
