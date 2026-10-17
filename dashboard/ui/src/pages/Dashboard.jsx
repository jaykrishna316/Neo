import React, { useEffect, useState } from 'react';
import io from 'socket.io-client';
import api from '../services/api';
import ServiceNetwork from '../components/ServiceNetwork';
import ActivityFeed from '../components/ActivityFeed';
import CouplingMetrics from '../components/CouplingMetrics';
import ConflictHeatmap from '../components/ConflictHeatmap';
import HealthIndicators from '../components/HealthIndicators';
import '../styles/Dashboard.css';

function Dashboard() {
  const [overview, setOverview] = useState(null);
  const [graph, setGraph] = useState(null);
  const [activity, setActivity] = useState(null);
  const [heatmap, setHeatmap] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [socket, setSocket] = useState(null);

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

  return (
    <div className="dashboard">
      {error && <div className="error-banner">{error}</div>}

      {/* Health Indicators */}
      {overview && (
        <HealthIndicators
          overview={overview}
          onRefresh={() => handleRefresh('overview')}
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

        {/* Coupling Metrics */}
        <div className="dashboard-cell">
          {overview && overview.entropy_summary && (
            <CouplingMetrics
              entropy={overview.entropy_summary}
              onRefresh={() => handleRefresh('coupling')}
            />
          )}
        </div>

        {/* Activity Feed */}
        <div className="dashboard-cell dashboard-cell-tall">
          {activity && (
            <ActivityFeed
              data={activity}
              onRefresh={() => handleRefresh('activity')}
            />
          )}
        </div>

        {/* Conflict Heatmap */}
        <div className="dashboard-cell dashboard-cell-wide">
          {heatmap && (
            <ConflictHeatmap
              data={heatmap}
              onRefresh={() => handleRefresh('heatmap')}
            />
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
    </div>
  );
}

export default Dashboard;
