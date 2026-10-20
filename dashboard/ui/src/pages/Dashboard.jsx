import React, { useEffect, useState } from 'react';
import io from 'socket.io-client';
import api from '../services/api';
import ServiceNetwork from '../components/ServiceNetwork';
import ActivityFeed from '../components/ActivityFeed';
import CouplingMetrics from '../components/CouplingMetrics';
import ConflictHeatmap from '../components/ConflictHeatmap';
import HealthIndicators from '../components/HealthIndicators';
import EntropyDeepDive from '../components/EntropyDeepDive';
import BlastRadiusExplorer from '../components/BlastRadiusExplorer';
import TrendAnalysis from '../components/TrendAnalysis';
import FilterPanel from '../components/FilterPanel';
import ThemeToggle from '../components/ThemeToggle';
import ExportDialog from '../components/ExportDialog';
import '../styles/Dashboard.css';
import '../styles/modals.css';

function Dashboard() {
  const [overview, setOverview] = useState(null);
  const [graph, setGraph] = useState(null);
  const [activity, setActivity] = useState(null);
  const [heatmap, setHeatmap] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [socket, setSocket] = useState(null);
  const [filters, setFilters] = useState(null);
  const [showFilterPanel, setShowFilterPanel] = useState(false);
  const [showExport, setShowExport] = useState(false);
  const [selectedEntropy, setSelectedEntropy] = useState(null);
  const [selectedBlastRadius, setSelectedBlastRadius] = useState(null);
  const [selectedTrend, setSelectedTrend] = useState(null);

  // Initialize WebSocket connection
  useEffect(() => {
    const newSocket = io();
    setSocket(newSocket);

    newSocket.on('connect', () => {
      console.log('WebSocket connected');
    });

    newSocket.on('metrics:overview', (data) => {
      setOverview(data);
    });

    newSocket.on('graph:update', (data) => {
      setGraph(data);
    });

    newSocket.on('activity:update', (data) => {
      setActivity(data);
    });

    newSocket.on('refresh:heatmap', (data) => {
      setHeatmap(data);
    });

    newSocket.on('error', (err) => {
      console.error('Socket error:', err);
      setError(err.message);
    });

    return () => {
      newSocket.disconnect();
    };
  }, []);

  // Fetch initial data
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [overviewData, graphData, activityData, heatmapData] = await Promise.all([
          api.getDashboardOverview(),
          api.getServicesGraph(),
          api.getActivityFeed(),
          api.getConflictHeatmap()
        ]);

        setOverview(overviewData);
        setGraph(graphData);
        setActivity(activityData);
        setHeatmap(heatmapData);
        setError(null);
      } catch (err) {
        console.error('Error fetching dashboard data:', err);
        setError('Failed to load dashboard data. Check your connection.');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    // Refresh every 30 seconds
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleRefresh = async (section) => {
    try {
      if (socket) {
        socket.emit('refresh', { section });
      }
    } catch (err) {
      console.error('Error refreshing:', err);
    }
  };

  if (loading && !overview) {
    return (
      <div className="dashboard dashboard-loading">
        <div className="loading-spinner">
          <div className="spinner"></div>
          <p>Loading Neo Mission Control...</p>
        </div>
      </div>
    );
  }

  const dashboardData = { overview, graph, activity, heatmap };

  return (
    <div className="dashboard">
      {error && <div className="error-banner">{error}</div>}

      {/* Header Controls */}
      <div className="dashboard-controls">
        <div className="controls-left">
          <button className="btn-small" onClick={() => setShowFilterPanel(true)} title="Filters">
            🔍 Filters
          </button>
          <button className="btn-small" onClick={() => setShowExport(true)} title="Export">
            📥 Export
          </button>
        </div>
        <ThemeToggle />
      </div>

      {/* Health Indicators */}
      {overview && (
        <HealthIndicators
          overview={overview}
          onRefresh={() => handleRefresh('overview')}
          onDrillDown={() => setSelectedEntropy(true)}
        />
      )}

      {/* Main Grid */}
      <div className="dashboard-grid">
        {/* Service Network - Prominent */}
        <div className="dashboard-cell dashboard-cell-wide">
          {graph && (
            <ServiceNetwork
              data={graph}
              onRefresh={() => handleRefresh('graph')}
            />
          )}
        </div>

        {/* Coupling Metrics with Drill-down */}
        <div className="dashboard-cell">
          {overview && overview.entropy_summary && (
            <div className="component-card">
              <div className="cell-header">
                <h3 className="cell-title">📈 Coupling Metrics</h3>
                <button
                  className="btn-small"
                  onClick={() => setSelectedEntropy(true)}
                  title="Deep dive"
                >
                  🔬
                </button>
              </div>
              <CouplingMetrics
                entropy={overview.entropy_summary}
                onRefresh={() => handleRefresh('coupling')}
              />
            </div>
          )}
        </div>

        {/* Activity Feed */}
        <div className="dashboard-cell dashboard-cell-tall">
          {activity && (
            <ActivityFeed
              data={activity}
              onRefresh={() => handleRefresh('activity')}
              onSelectFile={(file) => setSelectedTrend(file)}
            />
          )}
        </div>

        {/* Conflict Heatmap with Drill-downs */}
        <div className="dashboard-cell dashboard-cell-wide">
          {heatmap && (
            <div className="component-card">
              <div className="cell-header">
                <h3 className="cell-title">🔥 Conflict Heatmap</h3>
                <button className="btn-small" onClick={() => handleRefresh('heatmap')}>
                  🔄
                </button>
              </div>
              <ConflictHeatmap
                data={heatmap}
                onRefresh={() => handleRefresh('heatmap')}
                onSelectFile={(file) => setSelectedBlastRadius(file)}
              />
            </div>
          )}
        </div>
      </div>

      {/* Footer Stats */}
      <div className="dashboard-stats">
        {overview && (
          <div className="stat-item">
            <span className="stat-label">Status:</span>
            <span className={`stat-value ${overview.status.status === 'ok' ? 'ok' : 'error'}`}>
              {overview.status.status === 'ok' ? '✓ Operational' : '✗ Error'}
            </span>
          </div>
        )}
        <div className="stat-item">
          <span className="stat-label">Updated:</span>
          <span className="stat-value">
            {new Date().toLocaleTimeString()}
          </span>
        </div>
      </div>

      {/* Phase 2: Drill-down Modals */}
      {selectedEntropy && (
        <EntropyDeepDive onClose={() => setSelectedEntropy(null)} />
      )}

      {selectedBlastRadius && (
        <BlastRadiusExplorer
          filePath={selectedBlastRadius}
          onClose={() => setSelectedBlastRadius(null)}
        />
      )}

      {selectedTrend && (
        <TrendAnalysis
          filePath={selectedTrend}
          onClose={() => setSelectedTrend(null)}
        />
      )}

      {/* Phase 3: Filter Panel */}
      {showFilterPanel && (
        <FilterPanel
          onFilter={setFilters}
          onClose={() => setShowFilterPanel(false)}
        />
      )}

      {/* Phase 3: Export Dialog */}
      {showExport && (
        <ExportDialog
          dashboardData={dashboardData}
          onClose={() => setShowExport(false)}
        />
      )}
    </div>
  );
}

export default Dashboard;
