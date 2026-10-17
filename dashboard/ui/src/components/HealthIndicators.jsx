import React from 'react';
import '../styles/components.css';

function HealthIndicators({ overview, onRefresh }) {
  const getRiskColor = (level) => {
    switch (level) {
      case 'LOW':
        return 'ok';
      case 'MEDIUM':
        return 'warning';
      case 'HIGH':
        return 'error';
      default:
        return 'ok';
    }
  };

  const getEntropyStatus = (entropy) => {
    if (!entropy.is_meaningful) {
      return { label: 'Insufficient Data', value: `${entropy.data_age_days || 0}d old` };
    }
    return { label: 'Issues Found', value: entropy.issue_count };
  };

  const entropyStatus = getEntropyStatus(overview.entropy_summary);

  return (
    <div className="health-indicators">
      <div className="health-indicator">
        <div className="health-title">Conflict Risk</div>
        <div className="health-value">{overview.conflict_summary.risk_level}</div>
        <span className={`health-badge ${getRiskColor(overview.conflict_summary.risk_level)}`}>
          {overview.conflict_summary.message}
        </span>
      </div>

      <div className="health-indicator">
        <div className="health-title">Active Developers</div>
        <div className="health-value">{overview.activity_summary.total_entries}</div>
        <span className="health-badge ok">
          {overview.activity_summary.recent_entries} recent
        </span>
      </div>

      <div className="health-indicator">
        <div className="health-title">Entropy Status</div>
        <div className="health-value">{entropyStatus.value}</div>
        <span className={`health-badge ${overview.entropy_summary.is_meaningful ? 'warning' : 'ok'}`}>
          {entropyStatus.label}
        </span>
      </div>

      <div className="health-indicator">
        <div className="health-title">Server Status</div>
        <div className="health-value">
          {overview.status.status === 'ok' ? '✓' : '✗'}
        </div>
        <span className={`health-badge ${overview.status.status === 'ok' ? 'ok' : 'error'}`}>
          {overview.status.status.toUpperCase()}
        </span>
      </div>

      <button className="btn-small refresh-btn" onClick={onRefresh} title="Refresh">
        🔄 Refresh
      </button>
    </div>
  );
}

export default HealthIndicators;
