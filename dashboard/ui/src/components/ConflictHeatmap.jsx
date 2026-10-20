import React, { useMemo } from 'react';
import '../styles/components.css';

function ConflictHeatmap({ data, onRefresh }) {
  const riskCounts = useMemo(() => {
    const counts = { HIGH: 0, MEDIUM: 0, LOW: 0 };
    if (data.heatmap) {
      data.heatmap.forEach(item => {
        counts[item.risk_level] = (counts[item.risk_level] || 0) + 1;
      });
    }
    return counts;
  }, [data.heatmap]);

  const getRiskColor = (level) => {
    switch (level) {
      case 'HIGH':
        return '#ef4444';
      case 'MEDIUM':
        return '#f97316';
      case 'LOW':
        return '#22c55e';
      default:
        return '#94a3b8';
    }
  };

  const topRiskFiles = useMemo(() => {
    if (!data.heatmap) return [];
    return data.heatmap
      .sort((a, b) => {
        const riskOrder = { HIGH: 3, MEDIUM: 2, LOW: 1 };
        return (riskOrder[b.risk_level] || 0) - (riskOrder[a.risk_level] || 0);
      })
      .slice(0, 10);
  }, [data.heatmap]);

  return (
    <div className="component-card heatmap-card">
      <div className="cell-header">
        <h3 className="cell-title">🔥 Conflict Heatmap</h3>
        <button className="btn-small" onClick={onRefresh}>🔄</button>
      </div>

      <div className="heatmap-stats">
        <div className="heatmap-stat">
          <span className="stat-label">High Risk</span>
          <span className="stat-value" style={{ color: getRiskColor('HIGH') }}>
            {riskCounts.HIGH}
          </span>
        </div>
        <div className="heatmap-stat">
          <span className="stat-label">Medium Risk</span>
          <span className="stat-value" style={{ color: getRiskColor('MEDIUM') }}>
            {riskCounts.MEDIUM}
          </span>
        </div>
        <div className="heatmap-stat">
          <span className="stat-label">Low Risk</span>
          <span className="stat-value" style={{ color: getRiskColor('LOW') }}>
            {riskCounts.LOW}
          </span>
        </div>
      </div>

      <div className="heatmap-list">
        <div className="list-header">Top Risk Files</div>
        {topRiskFiles.length > 0 ? (
          topRiskFiles.map(file => (
            <div key={file.file} className="heatmap-row">
              <div className="file-info">
                <div
                  className="risk-indicator"
                  style={{ backgroundColor: getRiskColor(file.risk_level) }}
                ></div>
                <div className="file-details">
                  <div className="file-path">{file.file}</div>
                  <div className="file-service">{file.service}</div>
                </div>
              </div>
              <div className="file-developers">
                {file.developers.map(dev => (
                  <span key={dev} className="dev-badge">{dev.substring(0, 2)}</span>
                ))}
              </div>
            </div>
          ))
        ) : (
          <div className="empty-state">
            <p>No conflict data yet</p>
          </div>
        )}
      </div>

      <div className="heatmap-info">
        <p className="info-text">
          5-layer staged conflict detection: syntactic → scope → semantic → type → data flow
        </p>
      </div>
    </div>
  );
}

export default ConflictHeatmap;
