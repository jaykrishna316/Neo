#!/usr/bin/env python3
"""
Neo Local Dashboard - Real-time web UI for Neo activity monitoring
Serves on http://localhost:5555
"""

import json
import time
from pathlib import Path
from flask import Flask, jsonify, render_template_string
from datetime import datetime, timedelta
import sys

sys.path.insert(0, str(Path(__file__).parent))

from core.activity_log import read_log, get_active_entries
from core.risk_classifier import classify_risk
from core.freshness import check_freshness
from core.impact_alerts import ImpactAlertManager

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Neo Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0a0e27; color: #e0e6ed; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; text-align: center; }
        .header h1 { font-size: 2em; margin-bottom: 5px; }
        .status { display: flex; gap: 20px; justify-content: center; flex-wrap: wrap; margin-top: 15px; }
        .stat { background: rgba(255,255,255,0.1); padding: 12px 20px; border-radius: 8px; }
        .stat .number { font-size: 1.8em; font-weight: bold; color: #667eea; }
        .stat .label { font-size: 0.85em; color: #9ca3af; margin-top: 5px; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(500px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .card { background: #111827; border: 1px solid #374151; border-radius: 12px; padding: 20px; }
        .card h2 { font-size: 1.2em; margin-bottom: 15px; color: #667eea; border-bottom: 1px solid #374151; padding-bottom: 10px; }
        .entry { background: #1f2937; padding: 15px; border-radius: 8px; margin-bottom: 12px; border-left: 3px solid #667eea; }
        .dev-name { font-weight: bold; color: #60a5fa; }
        .file-name { color: #34d399; font-family: monospace; font-size: 0.9em; }
        .intent { color: #a78bfa; font-size: 0.9em; margin: 8px 0; }
        .meta { display: flex; gap: 20px; flex-wrap: wrap; margin-top: 10px; font-size: 0.85em; color: #9ca3af; }
        .risk-low { color: #34d399; }
        .risk-medium { color: #fbbf24; }
        .risk-high { color: #f87171; }
        .freshness { padding: 8px 12px; border-radius: 6px; font-size: 0.85em; font-weight: 500; display: inline-block; }
        .freshness.current { background: rgba(52, 211, 153, 0.2); color: #34d399; }
        .freshness.stale { background: rgba(248, 113, 113, 0.2); color: #f87171; }
        .freshness.unverifiable { background: rgba(156, 163, 175, 0.2); color: #9ca3af; }
        .conflict { background: rgba(248, 113, 113, 0.1); border-left-color: #f87171 !important; }
        .conflict .label { color: #f87171; }
        .impact { background: rgba(34, 197, 94, 0.1); }
        .impact .label { color: #22c55e; }
        .timestamp { color: #6b7280; font-size: 0.8em; }
        .agent-meta { background: rgba(102, 126, 234, 0.1); padding: 10px; border-radius: 6px; margin-top: 10px; font-size: 0.85em; }
        .agent-meta div { margin: 4px 0; }
        .agents-section { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; }
        .agent-card { background: #1f2937; padding: 15px; border-radius: 8px; border: 1px solid #374151; }
        .agent-card .name { font-weight: bold; color: #60a5fa; margin-bottom: 10px; }
        .agent-card .activity { color: #9ca3af; font-size: 0.9em; }
        .refresh-info { text-align: center; color: #6b7280; font-size: 0.85em; margin-top: 20px; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th { background: #1f2937; padding: 12px; text-align: left; font-size: 0.9em; color: #9ca3af; border-bottom: 1px solid #374151; }
        td { padding: 12px; border-bottom: 1px solid #374151; }
        tr:hover { background: #1f2937; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 Neo Coordination Dashboard</h1>
        <p>Real-time multi-developer semantic conflict detection</p>
        <div class="status" id="status">
            <div class="stat">
                <div class="number" id="active-count">0</div>
                <div class="label">Active Developers</div>
            </div>
            <div class="stat">
                <div class="number" id="conflict-count">0</div>
                <div class="label">Conflicts Detected</div>
            </div>
            <div class="stat">
                <div class="number" id="stale-count">0</div>
                <div class="label">Stale Contexts</div>
            </div>
            <div class="stat">
                <div class="number" id="impact-count">0</div>
                <div class="label">Unresolved Impacts</div>
            </div>
        </div>
    </div>

    <div class="container">
        <div class="grid">
            <!-- Active Developers -->
            <div class="card">
                <h2>👥 Active Developers</h2>
                <div class="agents-section" id="developers"></div>
            </div>

            <!-- Activity Feed -->
            <div class="card">
                <h2>📊 Activity Feed</h2>
                <div id="activity"></div>
                <div class="refresh-info">Auto-refreshing every 2 seconds</div>
            </div>
        </div>

        <!-- Detailed Conflict Analysis -->
        <div class="card">
            <h2>🔬 Detailed Conflict Analysis</h2>
            <table>
                <thead>
                    <tr>
                        <th>Developer</th>
                        <th>File</th>
                        <th>Risk Level</th>
                        <th>Conflict Score</th>
                        <th>Semantic Layers</th>
                        <th>Coupling Status</th>
                        <th>Blockers</th>
                    </tr>
                </thead>
                <tbody id="analysis-table">
                </tbody>
            </table>
        </div>

        <!-- Detailed Metrics Table -->
        <div class="card">
            <h2>📈 Activity Metrics</h2>
            <table>
                <thead>
                    <tr>
                        <th>Developer</th>
                        <th>File</th>
                        <th>Intent</th>
                        <th>Conflict Risk</th>
                        <th>Context Status</th>
                        <th>Time</th>
                    </tr>
                </thead>
                <tbody id="metrics-table">
                </tbody>
            </table>
        </div>

        <!-- Data Points Reference -->
        <div class="card">
            <h2>📋 Data Points Being Captured</h2>
            <table>
                <thead>
                    <tr><th>Category</th><th>Data Points</th><th>Status</th></tr>
                </thead>
                <tbody>
                    <tr><td>Activity Logging</td><td>developer_id, file_path, intent, region, category, scope, timestamp, agent_metadata</td><td style="color: #34d399;">✅</td></tr>
                    <tr><td>Conflict Detection</td><td>risk_level, other_dev, reason, layers_triggered, detailed_score, coupling_analysis, dependency_blockers</td><td style="color: #34d399;">✅</td></tr>
                    <tr><td>Semantic Analysis</td><td>5 layers: syntactic, scope, semantic, type, data_flow with real AST analysis</td><td style="color: #34d399;">✅</td></tr>
                    <tr><td>Numerical Scoring</td><td>conflict_score (0-100), impact_factors, blockers, warnings, recommendations</td><td style="color: #34d399;">✅</td></tr>
                    <tr><td>Service Coupling</td><td>coupling_score, tight_coupling_detected, external_dependencies</td><td style="color: #34d399;">✅</td></tr>
                    <tr><td>Dependency Resolution</td><td>unresolved_blockers, blocking_services, breaking_changes</td><td style="color: #34d399;">✅</td></tr>
                    <tr><td>Context Staleness</td><td>status, stale, changed_symbols, needs_refresh</td><td style="color: #34d399;">✅</td></tr>
                    <tr><td>Impact Analysis</td><td>has_impacts, alert_count, upstream_sources, impact_reasons</td><td style="color: #34d399;">✅</td></tr>
                    <tr><td>Agent Execution</td><td>model, tokens_used, confidence, execution_time</td><td style="color: #34d399;">✅</td></tr>
                    <tr><td>Lock Management</td><td>state, holder, scope, queue_position, expires_in</td><td style="color: #fbbf24;">⚠️ Planned</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        function formatTime(ts) {
            const dt = new Date(ts * 1000);
            const now = new Date();
            const age = now - dt;
            if (age < 60000) return Math.floor(age/1000) + 's ago';
            if (age < 3600000) return Math.floor(age/60000) + 'm ago';
            return dt.toLocaleTimeString();
        }

        async function updateDashboard() {
            try {
                const response = await fetch('/api/dashboard');
                const data = await response.json();

                // Update stats
                document.getElementById('active-count').textContent = data.active_count;
                document.getElementById('conflict-count').textContent = data.conflict_count;
                document.getElementById('stale-count').textContent = data.stale_count;
                document.getElementById('impact-count').textContent = data.impact_count;

                // Update developers
                const devHtml = data.developers.map(dev => `
                    <div class="agent-card">
                        <div class="name">👤 ${dev.id}</div>
                        <div class="activity">📄 ${dev.file}</div>
                        <div class="timestamp">${dev.last_activity}</div>
                    </div>
                `).join('');
                document.getElementById('developers').innerHTML = devHtml;

                // Update activity
                const actHtml = data.activities.map(act => {
                    const riskClass = {
                        'HIGH': 'conflict',
                        'MEDIUM': 'conflict',
                        'LOW': 'impact'
                    }[act.risk] || '';
                    return `
                        <div class="entry ${riskClass}">
                            <div><span class="dev-name">${act.dev}</span> on <span class="file-name">${act.file}</span></div>
                            <div class="intent">${act.intent.substring(0, 80)}...</div>
                            <div class="meta">
                                <span class="risk-${act.risk.toLowerCase()}">${act.risk} Risk</span>
                                <span class="freshness ${act.freshness.toLowerCase()}">${act.freshness}</span>
                                <span class="timestamp">${act.time}</span>
                            </div>
                        </div>
                    `;
                }).join('');
                document.getElementById('activity').innerHTML = actHtml;

                // Update detailed analysis table
                const analysisHtml = data.analysis.map(a => `
                    <tr>
                        <td>${a.dev}</td>
                        <td><code>${a.file}</code></td>
                        <td><span class="risk-${a.risk.toLowerCase()}">${a.risk}</span></td>
                        <td>${a.score ? a.score.toFixed(1) + '/100 (' + a.score_category + ')' : 'N/A'}</td>
                        <td>${a.layers ? a.layers.join(', ') : 'N/A'}</td>
                        <td>${a.coupling ? (a.coupling ? '🔗 Tight' : '✓ Loose') : 'N/A'}</td>
                        <td>${a.blockers && a.blockers.length > 0 ? '⚠️ ' + a.blockers.length : '✓ None'}</td>
                    </tr>
                `).join('');
                document.getElementById('analysis-table').innerHTML = analysisHtml;

                // Update table
                const tableHtml = data.metrics.map(m => `
                    <tr>
                        <td>${m.dev}</td>
                        <td><code>${m.file}</code></td>
                        <td>${m.intent.substring(0, 40)}...</td>
                        <td><span class="risk-${m.risk.toLowerCase()}">${m.risk}</span></td>
                        <td><span class="freshness ${m.freshness.toLowerCase()}">${m.freshness}</span></td>
                        <td>${m.time}</td>
                    </tr>
                `).join('');
                document.getElementById('metrics-table').innerHTML = tableHtml;
            } catch (e) {
                console.error('Dashboard update failed:', e);
            }
        }

        // Initial load and auto-refresh
        updateDashboard();
        setInterval(updateDashboard, 2000);
    </script>
</body>
</html>
"""

@app.route('/')
def dashboard():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/dashboard')
def api_dashboard():
    """API endpoint returning dashboard data"""

    active = get_active_entries(expiry_minutes=30)
    all_entries = read_log()

    developers = {}
    conflict_count = 0
    stale_count = 0
    impact_count = 0

    activities = []
    metrics = []
    analysis = []

    for entry in active:
        dev_id = entry.get('developer_id', 'unknown')
        file_path = entry.get('file_path', 'unknown')
        intent = entry.get('intent', '')
        timestamp = entry.get('timestamp', time.time())

        # Track developers
        if dev_id not in developers:
            developers[dev_id] = {
                'id': dev_id,
                'file': file_path,
                'last_activity': formatTime(timestamp)
            }

        # Check freshness
        freshness = check_freshness(dev_id, file_path)
        if freshness == "STALE_SOURCE":
            stale_count += 1

        # Check conflicts with others and gather detailed analysis
        risk = "LOW"
        detailed_score = None
        score_category = "N/A"
        layers = []
        coupling = False
        blockers = []

        for other in active:
            if other['developer_id'] != dev_id and other['file_path'] == file_path:
                assessment = classify_risk(
                    dev_id, file_path, intent, entry.get('region'), other, use_staged_layers=True
                )
                risk = assessment.level.value
                conflict_count += 1

                # Extract detailed analysis data
                if assessment.detailed_score:
                    detailed_score = assessment.detailed_score.total_score
                    score_category = assessment.detailed_score.risk_category
                if assessment.layers_triggered:
                    layers = assessment.layers_triggered
                if assessment.coupling_analysis:
                    coupling = assessment.coupling_analysis.get('tight_coupling_detected', False)
                if assessment.dependency_blockers:
                    blockers = assessment.dependency_blockers
                break

        # Check impacts
        impact_mgr = ImpactAlertManager()
        impacts = impact_mgr.check_impacts_on_file(file_path)
        if impacts.get('has_impacts'):
            impact_count += impacts.get('alert_count', 0)

        activities.append({
            'dev': dev_id,
            'file': file_path,
            'intent': intent,
            'risk': risk,
            'freshness': freshness,
            'time': formatTime(timestamp)
        })

        metrics.append({
            'dev': dev_id,
            'file': file_path,
            'intent': intent,
            'risk': risk,
            'freshness': freshness,
            'time': formatTime(timestamp)
        })

        # Add detailed analysis
        analysis.append({
            'dev': dev_id,
            'file': file_path,
            'risk': risk,
            'score': detailed_score,
            'score_category': score_category if detailed_score else 'N/A',
            'layers': layers,
            'coupling': coupling,
            'blockers': blockers
        })

    return jsonify({
        'active_count': len(developers),
        'conflict_count': conflict_count,
        'stale_count': stale_count,
        'impact_count': impact_count,
        'developers': list(developers.values()),
        'activities': activities[:10],  # Latest 10
        'metrics': metrics[:20],  # Latest 20
        'analysis': analysis[:20]  # Latest 20 with detailed scoring
    })

def formatTime(ts):
    """Python-side time formatting"""
    now = time.time()
    age = now - ts
    if age < 60:
        return f"{int(age)}s ago"
    elif age < 3600:
        return f"{int(age/60)}m ago"
    else:
        return datetime.fromtimestamp(ts).strftime("%H:%M:%S")

if __name__ == '__main__':
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║  NEO LOCAL DASHBOARD                                           ║
    ║  Opening: http://localhost:5555                               ║
    ║  Real-time monitoring of multi-developer coordination          ║
    ╚════════════════════════════════════════════════════════════════╝
    """)
    app.run(host='localhost', port=5555, debug=False)
