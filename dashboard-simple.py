#!/usr/bin/env python3
"""
Neo Local Dashboard - Lightweight version using built-in HTTP server
Serves on http://localhost:5555
"""

import json
import time
import sys
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from core.activity_log import read_log, get_active_entries
from core.risk_classifier import classify_risk
from core.freshness import check_freshness
from core.impact_alerts import ImpactAlertManager
from core.lock_management import get_lock_manager
from core.team_coordination import get_coordinator
from core.service_coupling import get_analyzer
from core.code_quality import get_quality_analyzer
from core.error_tracking import get_error_tracker
from core.deployment_tracking import get_deployment_tracker
from core.timeline import get_timeline_tracker
from core.audit_compliance import get_compliance_tracker

class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP handler for Neo dashboard"""

    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode('utf-8'))

        elif self.path == '/api/dashboard':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            data = self.get_dashboard_data()
            self.wfile.write(json.dumps(data).encode('utf-8'))

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Suppress verbose logging"""
        pass

    @staticmethod
    def format_time(ts):
        """Format timestamp as relative time"""
        now = time.time()
        age = now - ts
        if age < 60:
            return f"{int(age)}s ago"
        elif age < 3600:
            return f"{int(age/60)}m ago"
        else:
            return datetime.fromtimestamp(ts).strftime("%H:%M:%S")

    @staticmethod
    def get_dashboard_data():
        """Get dashboard data from Neo"""

        active = get_active_entries(expiry_minutes=30)

        developers = {}
        conflict_count = 0
        stale_count = 0
        impact_count = 0

        activities = []
        metrics = []

        # Collect metrics from all modules
        lock_metrics = get_lock_manager().get_lock_metrics()
        team_metrics = get_coordinator().get_team_metrics(active or [])
        service_metrics = get_analyzer().get_service_metrics()
        error_metrics = get_error_tracker().get_error_metrics()
        deployment_metrics = get_deployment_tracker().get_deployment_metrics()
        timeline_metrics = get_timeline_tracker().get_timeline_metrics()
        audit_metrics = get_compliance_tracker().get_audit_metrics()

        for entry in active:
            dev_id = entry.get('developer_id', 'unknown')
            file_path = entry.get('file_path', 'unknown')
            intent = entry.get('intent', '')
            timestamp = entry.get('timestamp', time.time())
            region = entry.get('region', '')

            # Track developers
            if dev_id not in developers:
                developers[dev_id] = {
                    'id': dev_id,
                    'file': file_path,
                    'last_activity': DashboardHandler.format_time(timestamp)
                }

            # Check freshness
            freshness = check_freshness(dev_id, file_path)
            if freshness == "STALE_SOURCE":
                stale_count += 1

            # Check conflicts with others
            risk = "LOW"
            for other in active:
                if other['developer_id'] != dev_id and other['file_path'] == file_path:
                    try:
                        assessment = classify_risk(
                            dev_id, file_path, intent, region, other
                        )
                        risk = assessment.level.value
                        conflict_count += 1
                    except:
                        pass
                    break

            # Check impacts
            try:
                impact_mgr = ImpactAlertManager()
                impacts = impact_mgr.check_impacts_on_file(file_path)
                if impacts.get('has_impacts'):
                    impact_count += impacts.get('alert_count', 0)
            except:
                pass

            activities.append({
                'dev': dev_id,
                'file': file_path,
                'intent': intent[:80],
                'risk': risk,
                'freshness': freshness,
                'lock_status': 'locked' if file_path in get_lock_manager().locks else 'available',
                'time': DashboardHandler.format_time(timestamp)
            })

            metrics.append({
                'dev': dev_id,
                'file': file_path,
                'intent': intent[:80],
                'risk': risk,
                'freshness': freshness,
                'time': DashboardHandler.format_time(timestamp)
            })

        return {
            'active_count': len(developers),
            'conflict_count': conflict_count,
            'stale_count': stale_count,
            'impact_count': impact_count,
            'developers': list(developers.values()),
            'activities': activities[:10],
            'metrics': metrics[:20],
            'locks': lock_metrics,
            'team': team_metrics,
            'services': service_metrics,
            'errors': error_metrics,
            'deployments': deployment_metrics,
            'timeline': timeline_metrics,
            'audit': audit_metrics
        }

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Neo Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', monospace; background: #0a0e27; color: #e0e6ed; line-height: 1.6; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 25px 20px; text-align: center; box-shadow: 0 4px 20px rgba(102, 126, 234, 0.3); }
        .header h1 { font-size: 2.2em; margin-bottom: 8px; letter-spacing: 0.5px; }
        .header p { opacity: 0.9; font-size: 0.95em; }
        .status { display: flex; gap: 20px; justify-content: center; flex-wrap: wrap; margin-top: 20px; }
        .stat { background: rgba(0,0,0,0.2); padding: 15px 25px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1); }
        .stat .number { font-size: 2em; font-weight: bold; color: #60a5fa; }
        .stat .label { font-size: 0.85em; color: #cbd5e1; margin-top: 8px; }
        .container { max-width: 1600px; margin: 0 auto; padding: 25px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(550px, 1fr)); gap: 25px; margin-bottom: 30px; }
        .card { background: #111827; border: 1px solid #374151; border-radius: 12px; padding: 25px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
        .card h2 { font-size: 1.3em; margin-bottom: 20px; color: #60a5fa; border-bottom: 2px solid #374151; padding-bottom: 12px; }
        .entry { background: #1f2937; padding: 16px; border-radius: 8px; margin-bottom: 12px; border-left: 4px solid #667eea; transition: all 0.3s; }
        .entry:hover { background: #2a3f5f; transform: translateX(4px); }
        .dev-name { font-weight: bold; color: #60a5fa; }
        .file-name { color: #34d399; font-family: monospace; font-size: 0.9em; }
        .intent { color: #a78bfa; font-size: 0.9em; margin: 10px 0; }
        .meta { display: flex; gap: 20px; flex-wrap: wrap; margin-top: 10px; font-size: 0.85em; }
        .risk-low { color: #34d399; font-weight: 600; }
        .risk-medium { color: #fbbf24; font-weight: 600; }
        .risk-high { color: #f87171; font-weight: 600; }
        .freshness { padding: 6px 12px; border-radius: 6px; font-size: 0.8em; font-weight: 600; display: inline-block; }
        .freshness.current { background: rgba(52, 211, 153, 0.2); color: #34d399; }
        .freshness.stale_source { background: rgba(248, 113, 113, 0.2); color: #f87171; }
        .freshness.unverifiable { background: rgba(156, 163, 175, 0.2); color: #9ca3af; }
        .timestamp { color: #6b7280; font-size: 0.8em; }
        .agents-section { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
        .agent-card { background: #1f2937; padding: 15px; border-radius: 8px; border: 1px solid #374151; }
        .agent-card .name { font-weight: bold; color: #60a5fa; margin-bottom: 10px; font-size: 0.95em; }
        .agent-card .activity { color: #9ca3af; font-size: 0.85em; }
        .refresh-info { text-align: center; color: #6b7280; font-size: 0.85em; margin-top: 20px; font-style: italic; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th { background: #1f2937; padding: 12px; text-align: left; font-size: 0.9em; color: #a0aec0; border-bottom: 2px solid #374151; font-weight: 600; }
        td { padding: 12px; border-bottom: 1px solid #374151; font-size: 0.9em; }
        tr:hover { background: #1f2937; }
        code { background: #0f1419; padding: 2px 6px; border-radius: 4px; font-size: 0.85em; }
        .status-ok { color: #34d399; }
        .status-warn { color: #fbbf24; }
        .footer { text-align: center; color: #6b7280; font-size: 0.85em; padding: 20px; border-top: 1px solid #374151; margin-top: 40px; }
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
                <div class="label">Conflicts</div>
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
            <div class="card">
                <h2>👥 Active Developers</h2>
                <div class="agents-section" id="developers"></div>
            </div>

            <div class="card">
                <h2>📊 Activity Feed (Latest)</h2>
                <div id="activity"></div>
                <div class="refresh-info">⟳ Auto-refreshing every 2 seconds</div>
            </div>
        </div>

        <div class="card">
            <h2>📈 Detailed Metrics</h2>
            <table>
                <thead>
                    <tr>
                        <th>Developer</th>
                        <th>File</th>
                        <th>Intent</th>
                        <th>Conflict Risk</th>
                        <th>Context</th>
                        <th>Time</th>
                    </tr>
                </thead>
                <tbody id="metrics-table"></tbody>
            </table>
        </div>

        <div class="card">
            <h2>🔒 Lock Management</h2>
            <table>
                <thead><tr><th>Metric</th><th>Value</th></tr></thead>
                <tbody id="locks-table"></tbody>
            </table>
        </div>

        <div class="card">
            <h2>👥 Team Coordination</h2>
            <table>
                <thead><tr><th>Metric</th><th>Value</th></tr></thead>
                <tbody id="team-table"></tbody>
            </table>
        </div>

        <div class="card">
            <h2>🏗️ Service Coupling</h2>
            <table>
                <thead><tr><th>Metric</th><th>Value</th></tr></thead>
                <tbody id="services-table"></tbody>
            </table>
        </div>

        <div class="card">
            <h2>🐛 Error Tracking</h2>
            <table>
                <thead><tr><th>Metric</th><th>Value</th></tr></thead>
                <tbody id="errors-table"></tbody>
            </table>
        </div>

        <div class="card">
            <h2>🚀 Deployment Metrics</h2>
            <table>
                <thead><tr><th>Metric</th><th>Value</th></tr></thead>
                <tbody id="deployment-table"></tbody>
            </table>
        </div>

        <div class="card">
            <h2>⏱️ Timeline Metrics</h2>
            <table>
                <thead><tr><th>Metric</th><th>Value</th></tr></thead>
                <tbody id="timeline-table"></tbody>
            </table>
        </div>

        <div class="card">
            <h2>✅ Audit & Compliance</h2>
            <table>
                <thead><tr><th>Metric</th><th>Value</th></tr></thead>
                <tbody id="audit-table"></tbody>
            </table>
        </div>

        <div class="card">
            <h2>📋 Neo Data Points Coverage (127 KPIs)</h2>
            <table>
                <thead><tr><th style="width: 200px;">Category</th><th>Data Points</th><th style="width: 80px;">Status</th></tr></thead>
                <tbody>
                    <tr><td>Activity Logging</td><td>developer_id, file_path, intent, region, category, scope, timestamp, agent_metadata</td><td class="status-ok">✅ Ready</td></tr>
                    <tr><td>Conflict Detection</td><td>risk_level, other_dev, reason, layers_triggered, regions_overlap</td><td class="status-ok">✅ Ready</td></tr>
                    <tr><td>Context Staleness</td><td>status, stale, changed_symbols, needs_refresh</td><td class="status-ok">✅ Ready</td></tr>
                    <tr><td>Impact Analysis</td><td>has_impacts, alert_count, upstream_sources, impact_reasons</td><td class="status-ok">✅ Ready</td></tr>
                    <tr><td>Semantic Analysis</td><td>symbol_count, symbols, dependencies, dependency_types</td><td class="status-ok">✅ Ready</td></tr>
                    <tr><td>Agent Execution</td><td>model, tokens_used, confidence, execution_time</td><td class="status-ok">✅ Ready</td></tr>
                    <tr><td>Lock Management</td><td>state, holder, scope, queue_position, expires_in</td><td class="status-ok">✅ Ready</td></tr>
                    <tr><td>Team Coordination</td><td>concurrent_developers, collaboration_frequency, conflict_rate</td><td class="status-ok">✅ Ready</td></tr>
                    <tr><td>Service Coupling</td><td>coupling_score, tight_coupling_pairs, circular_dependencies</td><td class="status-ok">✅ Ready</td></tr>
                    <tr><td>Code Quality</td><td>cyclomatic_complexity, code_smells, test_coverage</td><td class="status-ok">✅ Ready</td></tr>
                    <tr><td>Error Tracking</td><td>error_count, test_failures, exception_coverage</td><td class="status-ok">✅ Ready</td></tr>
                    <tr><td>Deployment</td><td>release_version, deployment_readiness, rollback_risk</td><td class="status-ok">✅ Ready</td></tr>
                    <tr><td>Timeline</td><td>activity_start_time, activity_duration, work_phase</td><td class="status-ok">✅ Ready</td></tr>
                    <tr><td>Audit & Compliance</td><td>code_review_status, security_scan_result, compliance_passed</td><td class="status-ok">✅ Ready</td></tr>
                </tbody>
            </table>
        </div>

        <div class="footer">
            <p>Neo Local Dashboard | Monitoring .devsync/activity-log.json | <a href="javascript:location.reload()" style="color: #667eea; text-decoration: none;">Refresh Page</a></p>
        </div>
    </div>

    <script>
        async function updateDashboard() {
            try {
                const response = await fetch('/api/dashboard');
                const data = await response.json();

                document.getElementById('active-count').textContent = data.active_count;
                document.getElementById('conflict-count').textContent = data.conflict_count;
                document.getElementById('stale-count').textContent = data.stale_count;
                document.getElementById('impact-count').textContent = data.impact_count;

                const devHtml = data.developers.map(dev => `
                    <div class="agent-card">
                        <div class="name">👤 ${dev.id}</div>
                        <div class="activity">📄 ${dev.file}</div>
                        <div class="timestamp">${dev.last_activity}</div>
                    </div>
                `).join('') || '<p style="color: #6b7280;">No active developers</p>';
                document.getElementById('developers').innerHTML = devHtml;

                const actHtml = data.activities.map(act => {
                    const riskClass = ['HIGH', 'MEDIUM'].includes(act.risk) ? 'conflict' : '';
                    return `
                        <div class="entry">
                            <div><span class="dev-name">${act.dev}</span> on <span class="file-name">${act.file}</span></div>
                            <div class="intent">${act.intent}</div>
                            <div class="meta">
                                <span class="risk-${act.risk.toLowerCase()}">${act.risk} Risk</span>
                                <span class="freshness ${act.freshness.toLowerCase()}">${act.freshness}</span>
                                <span class="timestamp">${act.time}</span>
                            </div>
                        </div>
                    `;
                }).join('') || '<p style="color: #6b7280;">No activities yet</p>';
                document.getElementById('activity').innerHTML = actHtml;

                const tableHtml = data.metrics.map(m => `
                    <tr>
                        <td>${m.dev}</td>
                        <td><code>${m.file}</code></td>
                        <td>${m.intent}</td>
                        <td><span class="risk-${m.risk.toLowerCase()}">${m.risk}</span></td>
                        <td><span class="freshness ${m.freshness.toLowerCase()}">${m.freshness}</span></td>
                        <td>${m.time}</td>
                    </tr>
                `).join('') || '<tr><td colspan="6" style="text-align: center; color: #6b7280;">No data yet</td></tr>';
                document.getElementById('metrics-table').innerHTML = tableHtml;

                // Lock metrics
                const locksHtml = data.locks ? `
                    <tr><td>Active Locks</td><td>${data.locks.active_locks || 0}</td></tr>
                    <tr><td>Waiters</td><td>${data.locks.total_waiters || 0}</td></tr>
                    <tr><td>Queued Files</td><td>${data.locks.queued_files || 0}</td></tr>
                    <tr><td>Avg Wait Time</td><td>${(data.locks.average_wait_time || 0).toFixed(1)}s</td></tr>
                    <tr><td>Max Queue Length</td><td>${data.locks.max_queue_length || 0}</td></tr>
                ` : '<tr><td colspan="2">No data</td></tr>';
                document.getElementById('locks-table').innerHTML = locksHtml;

                // Team metrics
                const teamHtml = data.team ? `
                    <tr><td>Concurrent Developers</td><td>${data.team.concurrent_developers || 0}</td></tr>
                    <tr><td>Collaboration Freq</td><td>${(data.team.collaboration_frequency || 0).toFixed(2)}</td></tr>
                    <tr><td>Conflict Rate</td><td>${(data.team.conflict_rate || 0).toFixed(1)}%</td></tr>
                    <tr><td>Avg Resolution Time</td><td>${(data.team.average_resolution_time || 0).toFixed(1)}s</td></tr>
                    <tr><td>Coordination Score</td><td>${(data.team.team_coordination_score || 0).toFixed(0)}/100</td></tr>
                ` : '<tr><td colspan="2">No data</td></tr>';
                document.getElementById('team-table').innerHTML = teamHtml;

                // Service metrics
                const servicesHtml = data.services ? `
                    <tr><td>Service Count</td><td>${data.services.service_count || 0}</td></tr>
                    <tr><td>Coupling Score</td><td>${(data.services.overall_coupling_score || 0).toFixed(2)}</td></tr>
                    <tr><td>Tightly Coupled</td><td>${data.services.tightly_coupled_pairs || 0}</td></tr>
                    <tr><td>Circular Deps</td><td>${data.services.circular_dependencies || 0}</td></tr>
                ` : '<tr><td colspan="2">No data</td></tr>';
                document.getElementById('services-table').innerHTML = servicesHtml;

                // Error metrics
                const errorsHtml = data.errors ? `
                    <tr><td>Total Errors</td><td>${data.errors.error_count || 0}</td></tr>
                    <tr><td>Test Failures</td><td>${data.errors.test_failures || 0}</td></tr>
                    <tr><td>Failure Rate</td><td>${(data.errors.test_failure_rate || 0).toFixed(1)}%</td></tr>
                    <tr><td>Flaky Tests</td><td>${data.errors.flaky_tests || 0}</td></tr>
                    <tr><td>Exceptions</td><td>${data.errors.unhandled_exceptions || 0}</td></tr>
                ` : '<tr><td colspan="2">No data</td></tr>';
                document.getElementById('errors-table').innerHTML = errorsHtml;

                // Deployment metrics
                const deploymentHtml = data.deployments ? `
                    <tr><td>Total Releases</td><td>${data.deployments.release_count || 0}</td></tr>
                    <tr><td>Completed</td><td>${data.deployments.completed_deployments || 0}</td></tr>
                    <tr><td>Checklist Items</td><td>${data.deployments.checklist_items_total || 0}</td></tr>
                    <tr><td>Monitoring Alerts</td><td>${data.deployments.monitoring_alerts || 0}</td></tr>
                    <tr><td>Avg Deploy Time</td><td>${(data.deployments.avg_deployment_time || 0).toFixed(0)}s</td></tr>
                ` : '<tr><td colspan="2">No data</td></tr>';
                document.getElementById('deployment-table').innerHTML = deploymentHtml;

                // Timeline metrics
                const timelineHtml = data.timeline ? `
                    <tr><td>Total Activities</td><td>${data.timeline.total_activities || 0}</td></tr>
                    <tr><td>Completed</td><td>${data.timeline.completed_activities || 0}</td></tr>
                    <tr><td>Active</td><td>${data.timeline.active_activities || 0}</td></tr>
                    <tr><td>Total Time</td><td>${((data.timeline.total_time_spent || 0) / 3600).toFixed(1)}h</td></tr>
                    <tr><td>Current Phase</td><td>${data.timeline.current_phase || 'unknown'}</td></tr>
                ` : '<tr><td colspan="2">No data</td></tr>';
                document.getElementById('timeline-table').innerHTML = timelineHtml;

                // Audit metrics
                const auditHtml = data.audit ? `
                    <tr><td>Reviews</td><td>${data.audit.review_count || 0}</td></tr>
                    <tr><td>Comments</td><td>${data.audit.review_comments || 0}</td></tr>
                    <tr><td>Security Scans</td><td>${data.audit.security_scan_count || 0}</td></tr>
                    <tr><td>Compliance Checks</td><td>${data.audit.compliance_checks || 0}</td></tr>
                    <tr><td>Violations</td><td>${data.audit.violations || 0}</td></tr>
                ` : '<tr><td colspan="2">No data</td></tr>';
                document.getElementById('audit-table').innerHTML = auditHtml;
            } catch (e) {
                console.error('Update failed:', e);
            }
        }

        updateDashboard();
        setInterval(updateDashboard, 2000);
    </script>
</body>
</html>
"""

def run_server():
    server_address = ('localhost', 5555)
    httpd = HTTPServer(server_address, DashboardHandler)
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║  🔍 NEO LOCAL DASHBOARD                                           ║
║  URL: http://localhost:5555                                       ║
║  Real-time monitoring of multi-developer coordination              ║
║  Press Ctrl+C to stop                                             ║
╚═══════════════════════════════════════════════════════════════════╝
    """)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n✅ Dashboard stopped")
        httpd.server_close()

if __name__ == '__main__':
    run_server()
