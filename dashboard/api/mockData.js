// Realistic Neo Mission Control mock data

const mockData = {
  overview: {
    status: {
      status: 'ok',
      message: 'All systems operational',
      lastCheck: new Date().toISOString()
    },
    conflict_summary: {
      total_conflicts: 12,
      high_risk_files: 3,
      risk_level: 'MEDIUM'
    },
    activity_summary: {
      total_entries: 156,
      active_developers: 4,
      last_activity: new Date(Date.now() - 5 * 60000).toISOString()
    },
    entropy_summary: {
      current_entropy: 0.72,
      threshold: 0.65,
      meaningful_data_percent: 94,
      architectural_issues: 8,
      data_window_days: 90,
      last_update: new Date().toISOString()
    }
  },

  graph: {
    nodes: [
      { id: 'dashboard', label: 'Dashboard UI', type: 'service', size: 30 },
      { id: 'api', label: 'API Server', type: 'service', size: 28 },
      { id: 'core', label: 'Neo Core', type: 'service', size: 32 },
      { id: 'cache', label: 'Redis Cache', type: 'service', size: 20 },
      { id: 'activity', label: 'Activity Log', type: 'service', size: 22 },
      { id: 'auth', label: 'Auth Service', type: 'service', size: 18 }
    ],
    links: [
      { source: 'dashboard', target: 'api', value: 0.85, label: 'REST API' },
      { source: 'api', target: 'core', value: 0.92, label: 'Conflict Detection' },
      { source: 'api', target: 'cache', value: 0.78, label: 'Query Cache' },
      { source: 'core', target: 'activity', value: 0.88, label: 'Log Activity' },
      { source: 'dashboard', target: 'cache', value: 0.65, label: 'Real-time Data' },
      { source: 'api', target: 'auth', value: 0.71, label: 'Authorization' }
    ]
  },

  activity: {
    entries: [
      {
        timestamp: new Date(Date.now() - 1 * 60000).toISOString(),
        agent_id: 'claude-haiku-frontend',
        file_path: 'dashboard/ui/src/components/Dashboard.jsx',
        intent: 'Add real-time WebSocket support',
        intent_category: 'modification'
      },
      {
        timestamp: new Date(Date.now() - 3 * 60000).toISOString(),
        agent_id: 'claude-opus-backend',
        file_path: 'dashboard/api/services/neoClient.js',
        intent: 'Optimize conflict detection response time',
        intent_category: 'modification'
      },
      {
        timestamp: new Date(Date.now() - 7 * 60000).toISOString(),
        agent_id: 'claude-sonnet-data',
        file_path: 'core/analysis/entropy.py',
        intent: 'Implement 90-day rolling window analysis',
        intent_category: 'modification'
      },
      {
        timestamp: new Date(Date.now() - 15 * 60000).toISOString(),
        agent_id: 'claude-haiku-frontend',
        file_path: 'dashboard/ui/src/components/BlastRadiusExplorer.jsx',
        intent: 'Create impact visualization component',
        intent_category: 'creation'
      },
      {
        timestamp: new Date(Date.now() - 32 * 60000).toISOString(),
        agent_id: 'claude-opus-backend',
        file_path: 'dashboard/api/routes/services.routes.js',
        intent: 'Add blast radius estimation endpoint',
        intent_category: 'creation'
      },
      {
        timestamp: new Date(Date.now() - 1 * 3600000).toISOString(),
        agent_id: 'claude-sonnet-data',
        file_path: 'core/models/service_graph.py',
        intent: 'Refactor coupling calculation algorithm',
        intent_category: 'modification'
      },
      {
        timestamp: new Date(Date.now() - 2 * 3600000).toISOString(),
        agent_id: 'human-developer',
        file_path: 'dashboard/api/services/cacheService.js',
        intent: 'Fix Redis timeout handling',
        intent_category: 'modification'
      },
      {
        timestamp: new Date(Date.now() - 4 * 3600000).toISOString(),
        agent_id: 'claude-haiku-frontend',
        file_path: 'dashboard/ui/src/styles/modals.css',
        intent: 'Add modal animations and styling',
        intent_category: 'creation'
      }
    ]
  },

  heatmap: {
    stats: {
      high_risk_files: 3,
      medium_risk_files: 8,
      low_risk_files: 24
    },
    heatmap: [
      {
        file: 'dashboard/ui/src/pages/Dashboard.jsx',
        service: 'dashboard',
        risk_level: 'HIGH',
        conflict_count: 4,
        developers: ['claude-haiku-frontend', 'human-reviewer'],
        last_modified: new Date(Date.now() - 5 * 60000).toISOString()
      },
      {
        file: 'core/conflict_detection.py',
        service: 'core',
        risk_level: 'HIGH',
        conflict_count: 3,
        developers: ['claude-opus-backend', 'claude-sonnet-data'],
        last_modified: new Date(Date.now() - 20 * 60000).toISOString()
      },
      {
        file: 'dashboard/api/services/neoClient.js',
        service: 'api',
        risk_level: 'HIGH',
        conflict_count: 2,
        developers: ['claude-opus-backend'],
        last_modified: new Date(Date.now() - 45 * 60000).toISOString()
      },
      {
        file: 'dashboard/api/services/aggregator.js',
        service: 'api',
        risk_level: 'MEDIUM',
        conflict_count: 1,
        developers: ['claude-opus-backend', 'human-developer'],
        last_modified: new Date(Date.now() - 2 * 3600000).toISOString()
      },
      {
        file: 'core/analysis/entropy.py',
        service: 'core',
        risk_level: 'MEDIUM',
        conflict_count: 1,
        developers: ['claude-sonnet-data'],
        last_modified: new Date(Date.now() - 1 * 3600000).toISOString()
      },
      {
        file: 'dashboard/ui/src/components/ActivityFeed.jsx',
        service: 'dashboard',
        risk_level: 'MEDIUM',
        conflict_count: 0,
        developers: ['claude-haiku-frontend'],
        last_modified: new Date(Date.now() - 4 * 3600000).toISOString()
      },
      {
        file: 'dashboard/api/routes/activity.routes.js',
        service: 'api',
        risk_level: 'MEDIUM',
        conflict_count: 0,
        developers: ['claude-opus-backend'],
        last_modified: new Date(Date.now() - 6 * 3600000).toISOString()
      },
      {
        file: 'dashboard/ui/src/components/ServiceNetwork.jsx',
        service: 'dashboard',
        risk_level: 'LOW',
        conflict_count: 0,
        developers: ['claude-haiku-frontend'],
        last_modified: new Date(Date.now() - 8 * 3600000).toISOString()
      },
      {
        file: 'dashboard/ui/src/components/EntropyDeepDive.jsx',
        service: 'dashboard',
        risk_level: 'LOW',
        conflict_count: 0,
        developers: ['claude-haiku-frontend'],
        last_modified: new Date(Date.now() - 12 * 3600000).toISOString()
      },
      {
        file: 'dashboard/ui/src/components/BlastRadiusExplorer.jsx',
        service: 'dashboard',
        risk_level: 'LOW',
        conflict_count: 0,
        developers: ['claude-haiku-frontend'],
        last_modified: new Date(Date.now() - 10 * 3600000).toISOString()
      }
    ]
  },

  // Extended mock data for Phase 2 drill-down components
  entropy: {
    window_days: 90,
    services: [
      {
        name: 'core',
        entropy: 0.78,
        coupled_services: 4,
        stability: '82%',
        issues: [
          { severity: 'critical', message: 'Circular dependency: core ↔ api' },
          { severity: 'high', message: 'High coupling with activity log (0.88)' },
          { severity: 'warning', message: 'Entropy increasing 2% per week' }
        ]
      },
      {
        name: 'api',
        entropy: 0.65,
        coupled_services: 3,
        stability: '89%',
        issues: [
          { severity: 'high', message: 'Tightly coupled to cache service (0.78)' },
          { severity: 'warning', message: 'Multiple responsibility concerns' }
        ]
      },
      {
        name: 'dashboard',
        entropy: 0.52,
        coupled_services: 2,
        stability: '94%',
        issues: []
      },
      {
        name: 'cache',
        entropy: 0.38,
        coupled_services: 1,
        stability: '97%',
        issues: []
      }
    ]
  },

  blastRadius: {
    file: 'core/conflict_detection.py',
    changeType: 'modification',
    impact: {
      complexity: 'hard',
      affectedFiles: 12,
      devHours: 16,
      tokenCost: 4200
    },
    affectedFiles: [
      { file: 'dashboard/api/services/neoClient.js', impact: 'HIGH', dependents: 3 },
      { file: 'dashboard/api/routes/dashboard.routes.js', impact: 'MEDIUM', dependents: 2 },
      { file: 'core/analysis/entropy.py', impact: 'MEDIUM', dependents: 1 },
      { file: 'core/analysis/blast_radius.py', impact: 'HIGH', dependents: 4 },
      { file: 'dashboard/api/services/aggregator.js', impact: 'LOW', dependents: 0 }
    ],
    risks: {
      cascadeImpact: 0.72,
      testCoverage: 0.65,
      conflictProbability: 0.48
    },
    recommendations: [
      { priority: 'critical', text: 'Add integration tests for neoClient impact' },
      { priority: 'high', text: 'Update blast_radius.py algorithm documentation' },
      { priority: 'medium', text: 'Review coupling strength assumptions' }
    ]
  },

  trends: {
    file: 'dashboard/api/services/aggregator.js',
    window_days: 90,
    summary: {
      velocity: '2.3 changes/week',
      direction: 'down',
      stability: '87%',
      regressionRisk: 'LOW'
    },
    couplings: [
      {
        service: 'api',
        current: 0.78,
        change30d: -0.08,
        trend: 'improving',
        points: [0.92, 0.89, 0.86, 0.82, 0.78]
      },
      {
        service: 'cache',
        current: 0.65,
        change30d: +0.05,
        trend: 'degrading',
        points: [0.58, 0.60, 0.62, 0.64, 0.65]
      },
      {
        service: 'core',
        current: 0.72,
        change30d: -0.02,
        trend: 'stable',
        points: [0.74, 0.73, 0.73, 0.72, 0.72]
      }
    ],
    insights: [
      { icon: '📈', text: 'Decoupling from core service showing positive trend' },
      { icon: '⚠️', text: 'Cache coupling increased 5% in last 30 days' },
      { icon: '✅', text: 'Overall architecture stability remains strong at 87%' },
      { icon: '🔮', text: '30-day forecast: stable with slight improvement expected' }
    ],
    forecast: {
      expectedVelocity: '2.1 changes/week',
      direction: 'down',
      confidence: '78%'
    }
  }
};

module.exports = mockData;
