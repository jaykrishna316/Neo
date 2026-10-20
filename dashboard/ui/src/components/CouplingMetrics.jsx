import React from 'react';
import '../styles/components.css';

function CouplingMetrics({ entropy, onRefresh }) {
  return (
    <div className="component-card metrics-card">
      <div className="cell-header">
        <h3 className="cell-title">📈 Coupling Metrics</h3>
        <button className="btn-small" onClick={onRefresh}>🔄</button>
      </div>

      <div className="metrics-content">
        <div className="metric-box">
          <div className="metric-label">Entropy Status</div>
          <div className={`metric-badge ${entropy.is_meaningful ? 'warning' : 'ok'}`}>
            {entropy.is_meaningful ? 'Meaningful' : 'Warming Up'}
          </div>
          {!entropy.is_meaningful && (
            <p className="metric-note">
              Data age: {entropy.data_age_days || 0} days
              <br />
              (Need ~90 days for accurate analysis)
            </p>
          )}
        </div>

        <div className="metric-box">
          <div className="metric-label">Architectural Issues</div>
          <div className="metric-number">{entropy.issue_count || 0}</div>
          <p className="metric-note">
            {entropy.issue_count === 0
              ? 'No issues detected'
              : 'Review hidden couplings'}
          </p>
        </div>

        <div className="metric-box">
          <div className="metric-label">Data Window</div>
          <div className="metric-value">90 days</div>
          <p className="metric-note">Rolling analysis window</p>
        </div>
      </div>

      <div className="metrics-info">
        <p className="info-text">
          📊 Time-series coupling metrics track service interdependencies and detect regressions.
        </p>
      </div>
    </div>
  );
}

export default CouplingMetrics;
