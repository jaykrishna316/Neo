/**
 * Activity Routes
 * Activity log and real-time events endpoints
 */

module.exports = (aggregator, logger) => {
  const router = require('express').Router();

  // GET /api/activity/feed
  router.get('/feed', async (req, res) => {
    try {
      const { limit = 50 } = req.query;
      const feed = await aggregator.getActivityFeed(parseInt(limit));
      res.json({ success: true, data: feed });
    } catch (err) {
      logger.error('Activity feed error:', err);
      res.status(500).json({
        success: false,
        error: 'Failed to fetch activity feed',
        message: err.message
      });
    }
  });

  // GET /api/activity/developer/:agent_id
  router.get('/developer/:agent_id', async (req, res) => {
    try {
      const { agent_id } = req.params;
      const { limit = 50 } = req.query;

      const allActivity = await aggregator.readActivityLog();
      const developerActivity = (allActivity.entries || [])
        .filter(e => e.agent_id === agent_id)
        .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
        .slice(0, parseInt(limit))
        .map(e => ({
          ...e,
          relative_time: aggregator.getRelativeTime(e.timestamp)
        }));

      res.json({
        success: true,
        data: {
          agent_id,
          entries: developerActivity,
          total_count: developerActivity.length
        }
      });
    } catch (err) {
      logger.error('Developer activity error:', err);
      res.status(500).json({
        success: false,
        error: 'Failed to fetch developer activity',
        message: err.message
      });
    }
  });

  // GET /api/activity/file/:file_path
  router.get('/file/*', async (req, res) => {
    try {
      const filePath = req.params[0];
      const { limit = 50 } = req.query;

      const allActivity = await aggregator.readActivityLog();
      const fileActivity = (allActivity.entries || [])
        .filter(e => e.file_path === filePath)
        .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
        .slice(0, parseInt(limit))
        .map(e => ({
          ...e,
          relative_time: aggregator.getRelativeTime(e.timestamp)
        }));

      res.json({
        success: true,
        data: {
          file_path: filePath,
          entries: fileActivity,
          total_count: fileActivity.length
        }
      });
    } catch (err) {
      logger.error('File activity error:', err);
      res.status(500).json({
        success: false,
        error: 'Failed to fetch file activity',
        message: err.message
      });
    }
  });

  // GET /api/activity/summary
  router.get('/summary', async (req, res) => {
    try {
      const allActivity = await aggregator.readActivityLog();
      const entries = allActivity.entries || [];

      // Count by service
      const byService = {};
      const byDeveloper = {};
      const byIntentCategory = {};

      entries.forEach(e => {
        const service = aggregator.extractServiceName(e.file_path);
        byService[service] = (byService[service] || 0) + 1;
        byDeveloper[e.agent_id] = (byDeveloper[e.agent_id] || 0) + 1;

        const category = e.intent_category || 'unknown';
        byIntentCategory[category] = (byIntentCategory[category] || 0) + 1;
      });

      res.json({
        success: true,
        data: {
          total_entries: entries.length,
          total_developers: Object.keys(byDeveloper).length,
          total_services: Object.keys(byService).length,
          by_service: byService,
          by_developer: byDeveloper,
          by_intent_category: byIntentCategory,
          timestamp: new Date().toISOString()
        }
      });
    } catch (err) {
      logger.error('Activity summary error:', err);
      res.status(500).json({
        success: false,
        error: 'Failed to fetch activity summary',
        message: err.message
      });
    }
  });

  return router;
};
