/**
 * Aggregator Service
 * Combines data from Neo, activity log, and cache to create dashboard snapshots
 */

const fs = require('fs').promises;
const path = require('path');
const { execSync } = require('child_process');

class Aggregator {
  constructor(neoClient, cacheService, conflictCacheManager, logger) {
    this.neo = neoClient;
    this.cache = cacheService;
    this.conflictCache = conflictCacheManager;
    this.logger = logger;
    this.activityLogPath = path.join(__dirname, '../../.devsync/activity-log.json');
    this.lastActivityCheck = Date.now();
  }

  async readActivityLog() {
    try {
      const data = await fs.readFile(this.activityLogPath, 'utf8');
      return JSON.parse(data);
    } catch (err) {
      if (err.code === 'ENOENT') {
        return { entries: [] };
      }
      this.logger.error('Activity log read error:', err);
      return { entries: [] };
    }
  }

  buildServiceGraph(activityData, couplingData) {
    const nodes = new Map();
    const links = new Map();

    // Extract services from activity log
    if (activityData.entries) {
      activityData.entries.forEach((entry) => {
        const file = entry.file_path;
        const service = this.extractServiceName(file);

        if (!nodes.has(service)) {
          nodes.set(service, {
            id: service,
            name: service,
            developers: new Set(),
            activity_count: 0,
            last_activity: null,
            files: new Set()
          });
        }

        const node = nodes.get(service);
        node.developers.add(entry.agent_id);
        node.activity_count++;
        node.files.add(file);

        if (!node.last_activity || new Date(entry.timestamp) > new Date(node.last_activity)) {
          node.last_activity = entry.timestamp;
        }
      });
    }

    // Build edges from coupling data
    if (couplingData && couplingData.services) {
      couplingData.services.forEach((service) => {
        const couplings = service.coupled_services || [];
        couplings.forEach((coupling) => {
          const linkKey = [service.name, coupling.name].sort().join('|');

          if (!links.has(linkKey)) {
            links.set(linkKey, {
              source: service.name,
              target: coupling.name,
              value: coupling.coupling_score || 0.5,
              type: coupling.type || 'change',
              color: this.getCouplingColor(coupling.coupling_score || 0.5)
            });
          }
        });
      });
    }

    // Convert maps to arrays with proper structure
    const nodeArray = Array.from(nodes.values()).map(n => ({
      ...n,
      developers: Array.from(n.developers),
      files: Array.from(n.files)
    }));

    const linkArray = Array.from(links.values());

    return {
      nodes: nodeArray,
      links: linkArray,
      timestamp: new Date().toISOString()
    };
  }

  extractServiceName(filePath) {
    // Extract service name from file path (e.g., 'dashboard/api' -> 'dashboard')
    const parts = filePath.split('/');
    if (parts.length > 1) {
      return parts[0];
    }
    return 'core';
  }

  getCouplingColor(score) {
    if (score >= 0.8) return '#ef4444'; // red - high coupling
    if (score >= 0.6) return '#f97316'; // orange - medium-high
    if (score >= 0.4) return '#eab308'; // yellow - medium
    return '#22c55e'; // green - low
  }

  async getActivityFeed(limit = 50) {
    try {
      const activity = await this.readActivityLog();
      const entries = activity.entries || [];

      // Sort by timestamp descending and limit
      const sorted = entries
        .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
        .slice(0, limit)
        .map(e => ({
          ...e,
          relative_time: this.getRelativeTime(e.timestamp)
        }));

      return {
        entries: sorted,
        total_count: entries.length,
        timestamp: new Date().toISOString()
      };
    } catch (err) {
      this.logger.error('Activity feed fetch error:', err);
      return { entries: [], total_count: 0, timestamp: new Date().toISOString() };
    }
  }

  getRelativeTime(timestamp) {
    const now = new Date();
    const then = new Date(timestamp);
    const seconds = Math.floor((now - then) / 1000);

    if (seconds < 60) return 'just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
  }

  async getDashboardOverview() {
    try {
      // Check cache first
      let overview = await this.cache.get('dashboard', 'overview');
      if (overview) {
        overview.fromCache = true;
        return overview;
      }

      // Fetch fresh data with conflict caching
      const [activity, conflicts, entropy, status] = await Promise.all([
        this.getActivityFeed(10),
        this.conflictCache.getOrCheckConflict(
          this.neo,
          'dashboard',
          '*',
          'overview',
          'all'
        ),
        this.neo.analyzeEntropyCoupling(),
        this.neo.getStatus()
      ]);

      overview = {
        timestamp: new Date().toISOString(),
        status,
        activity_summary: {
          total_entries: activity.total_count,
          recent_entries: activity.entries.length,
          entries: activity.entries
        },
        conflict_summary: {
          risk_level: conflicts.risk_level,
          message: conflicts.message
        },
        entropy_summary: {
          is_meaningful: entropy.is_meaningful,
          data_age_days: entropy.data_age_days,
          issue_count: (entropy.architectural_issues || []).length
        },
        fromCache: false
      };

      // Cache for 1 minute
      await this.cache.set('dashboard', 'overview', overview, 60);
      return overview;
    } catch (err) {
      this.logger.error('Dashboard overview fetch error:', err);
      return {
        timestamp: new Date().toISOString(),
        status: { status: 'ERROR' },
        activity_summary: { total_entries: 0, recent_entries: 0, entries: [] },
        conflict_summary: { risk_level: 'UNKNOWN', message: 'Error fetching data' },
        entropy_summary: { is_meaningful: false, data_age_days: null, issue_count: 0 },
        fromCache: false
      };
    }
  }

  async getServicesGraph() {
    try {
      // Check cache first
      let graph = await this.cache.getServiceGraph();
      if (graph) {
        return graph;
      }

      // Fetch fresh data
      const [activity, coupling, entropy] = await Promise.all([
        this.readActivityLog(),
        this.neo.getCouplingTrends('*', 90),
        this.neo.analyzeEntropyCoupling()
      ]);

      graph = this.buildServiceGraph(activity, entropy);

      // Cache for 5 minutes
      await this.cache.cacheServiceGraph(graph);
      return graph;
    } catch (err) {
      this.logger.error('Services graph fetch error:', err);
      return { nodes: [], links: [], timestamp: new Date().toISOString() };
    }
  }

  async getConflictHeatmap() {
    try {
      const activity = await this.readActivityLog();
      const entries = activity.entries || [];

      // Prepare batch conflict checks
      const conflictEntries = entries.map(entry => ({
        agentId: entry.agent_id,
        filePath: entry.file_path,
        intent: entry.intent || 'modification',
        region: 'all'
      }));

      // Use batch conflict checking with caching
      const conflictResults = await this.conflictCache.getOrCheckMultipleConflicts(
        this.neo,
        conflictEntries
      );

      // Build heatmap from results
      const heatmap = new Map();
      conflictResults.forEach((result, idx) => {
        const entry = entries[idx];
        const file = entry.file_path;
        const conflict = result.conflict;

        if (!heatmap.has(file)) {
          heatmap.set(file, {
            file: file,
            service: this.extractServiceName(file),
            risk_level: 'LOW',
            developers: new Set(),
            last_activity: entry.timestamp,
            conflict_details: [],
            cache_source: result.source
          });
        }

        const entry_data = heatmap.get(file);
        entry_data.developers.add(entry.agent_id);
        entry_data.conflict_details.push({
          agent_id: entry.agent_id,
          risk_level: conflict.risk_level,
          timestamp: entry.timestamp,
          cache_source: result.source
        });

        // Update overall risk level to highest
        if (conflict.risk_level === 'HIGH') {
          entry_data.risk_level = 'HIGH';
        } else if (conflict.risk_level === 'MEDIUM' && entry_data.risk_level !== 'HIGH') {
          entry_data.risk_level = 'MEDIUM';
        }
      });

      const heatmapArray = Array.from(heatmap.values()).map(h => ({
        ...h,
        developers: Array.from(h.developers)
      }));

      return {
        heatmap: heatmapArray,
        timestamp: new Date().toISOString(),
        cacheStats: this.conflictCache.getAccessStats()
      };
    } catch (err) {
      this.logger.error('Conflict heatmap fetch error:', err);
      return { heatmap: [], timestamp: new Date().toISOString() };
    }
  }

  async getMetricsTimeSeries(metricName, points = 100) {
    try {
      const metrics = await this.cache.getMetrics(metricName, points);
      return {
        metric: metricName,
        data_points: metrics,
        timestamp: new Date().toISOString()
      };
    } catch (err) {
      this.logger.error('Metrics fetch error:', err);
      return { metric: metricName, data_points: [], timestamp: new Date().toISOString() };
    }
  }

  async handleActivityChange(activityEntry) {
    try {
      // Invalidate caches based on the activity change
      await this.conflictCache.invalidateBasedOnActivityChange(activityEntry);

      // Invalidate dashboard overview cache
      await this.cache.invalidate('dashboard', 'overview');

      // Invalidate service graph cache
      await this.cache.invalidatePattern('graph:services');

      // Track this activity for monitoring
      await this.cache.trackActivityForInvalidation(activityEntry);

      this.logger.info(`Handled activity change for file: ${activityEntry.file_path}`);
    } catch (err) {
      this.logger.error('Activity change handling error:', err);
    }
  }

  async emitRefresh(socket, section) {
    try {
      let data;

      switch (section) {
        case 'overview':
          data = await this.getDashboardOverview();
          socket.emit('refresh:overview', data);
          break;
        case 'graph':
          data = await this.getServicesGraph();
          socket.emit('refresh:graph', data);
          break;
        case 'activity':
          data = await this.getActivityFeed();
          socket.emit('refresh:activity', data);
          break;
        case 'heatmap':
          data = await this.getConflictHeatmap();
          socket.emit('refresh:heatmap', data);
          break;
        default:
          data = await this.getDashboardOverview();
          socket.emit('refresh:all', data);
      }
    } catch (err) {
      this.logger.error('Emit refresh error:', err);
      socket.emit('error', { message: 'Refresh failed' });
    }
  }
}

module.exports = (neoClient, cacheService, conflictCacheManager, logger) =>
  new Aggregator(neoClient, cacheService, conflictCacheManager, logger);
