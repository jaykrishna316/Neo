import React, { useMemo } from 'react';
import '../styles/components.css';

function ActivityFeed({ data, onRefresh }) {
  const groupedEntries = useMemo(() => {
    const now = new Date();
    const grouped = {
      'Just Now': [],
      'Last Hour': [],
      'Last 24h': [],
      'Older': []
    };

    data.entries.forEach(entry => {
      const time = new Date(entry.timestamp);
      const diffMs = now - time;
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMs / 3600000);
      const diffDays = Math.floor(diffMs / 86400000);

      if (diffMins < 5) {
        grouped['Just Now'].push(entry);
      } else if (diffHours < 1) {
        grouped['Last Hour'].push(entry);
      } else if (diffDays < 1) {
        grouped['Last 24h'].push(entry);
      } else {
        grouped['Older'].push(entry);
      }
    });

    return grouped;
  }, [data.entries]);

  const renderEntry = (entry) => (
    <div key={`${entry.agent_id}-${entry.timestamp}`} className="activity-entry">
      <div className="entry-time">{entry.relative_time}</div>
      <div className="entry-content">
        <div className="entry-agent">{entry.agent_id}</div>
        <div className="entry-file">{entry.file_path}</div>
        {entry.intent && <div className="entry-intent">📝 {entry.intent}</div>}
      </div>
      {entry.intent_category && (
        <span className={`entry-badge ${entry.intent_category.toLowerCase()}`}>
          {entry.intent_category}
        </span>
      )}
    </div>
  );

  return (
    <div className="component-card activity-card">
      <div className="cell-header">
        <h3 className="cell-title">📊 Activity Timeline</h3>
        <div className="cell-actions">
          <button className="btn-small" onClick={onRefresh}>🔄</button>
        </div>
      </div>

      <div className="activity-feed">
        {Object.entries(groupedEntries).map(([group, entries]) => {
          if (entries.length === 0) return null;
          return (
            <div key={group} className="activity-group">
              <div className="group-header">{group}</div>
              <div className="group-entries">
                {entries.map(renderEntry)}
              </div>
            </div>
          );
        })}

        {data.entries.length === 0 && (
          <div className="empty-state">
            <p>No activity yet. Developers will appear here when they start working.</p>
          </div>
        )}
      </div>

      <div className="activity-footer">
        <small>Total: {data.total_count} entries</small>
      </div>
    </div>
  );
}

export default ActivityFeed;
