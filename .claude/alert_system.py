"""
Neo 3.0 Alert System

Real-time alerting for conflict prevention, understanding, and resolution.
"""

from datetime import datetime
from typing import List, Callable, Dict
from conflict_models import ConflictAlert, AlertSeverity, AlertType


class AlertSystem:
    """Central alert management system"""

    def __init__(self):
        self.active_alerts: List[ConflictAlert] = []
        self.alert_history: List[ConflictAlert] = []
        self.subscribers: Dict[AlertType, List[Callable]] = {}
        self.severity_thresholds = {
            AlertSeverity.LOW: 0.3,
            AlertSeverity.MEDIUM: 0.6,
            AlertSeverity.HIGH: 0.8,
            AlertSeverity.CRITICAL: 0.95
        }

    def subscribe(self, alert_type: AlertType, callback: Callable):
        """Subscribe to alerts of a specific type"""
        if alert_type not in self.subscribers:
            self.subscribers[alert_type] = []
        self.subscribers[alert_type].append(callback)

    def emit_alert(self, alert: ConflictAlert):
        """Emit an alert to all subscribers"""
        self.active_alerts.append(alert)
        self.alert_history.append(alert)

        # Notify subscribers
        if alert.alert_type in self.subscribers:
            for callback in self.subscribers[alert.alert_type]:
                try:
                    callback(alert)
                except Exception as e:
                    print(f"Error calling subscriber: {e}")

    def resolve_alert(self, alert_id: int, resolution: str):
        """Mark an alert as resolved"""
        if 0 <= alert_id < len(self.active_alerts):
            alert = self.active_alerts.pop(alert_id)
            return True
        return False

    def get_active_alerts(self, severity: AlertSeverity = None) -> List[ConflictAlert]:
        """Get all active alerts, optionally filtered by severity"""
        if severity is None:
            return self.active_alerts.copy()
        return [a for a in self.active_alerts if a.severity == severity]

    def get_alerts_for_developer(self, developer: str) -> List[ConflictAlert]:
        """Get all active alerts involving a specific developer"""
        return [a for a in self.active_alerts
                if a.developer_1 == developer or a.developer_2 == developer]

    def get_alerts_for_resource(self, resource: str) -> List[ConflictAlert]:
        """Get all active alerts for a specific resource"""
        return [a for a in self.active_alerts if a.resource == resource]

    def format_alert_for_display(self, alert: ConflictAlert) -> str:
        """Format an alert for human-readable display"""
        severity_emoji = {
            AlertSeverity.LOW: "⚠️",
            AlertSeverity.MEDIUM: "⚡",
            AlertSeverity.HIGH: "🔴",
            AlertSeverity.CRITICAL: "🚨"
        }

        alert_type_names = {
            AlertType.INTENT_OVERLAP: "Intent Overlap",
            AlertType.CONCURRENT_WORK: "Concurrent Work",
            AlertType.TEMPORAL_PREDICT: "Temporal Conflict",
            AlertType.SEMANTIC_VIOLATION: "Semantic Violation",
            AlertType.KNOWLEDGE_GAP: "Knowledge Gap"
        }

        return f"""{severity_emoji.get(alert.severity, '⚠️')} {alert_type_names.get(alert.alert_type, 'Alert')}

Developer 1: {alert.developer_1}
Developer 2: {alert.developer_2}
Resource: {alert.resource}

Reason: {alert.reason}
Suggested Action: {alert.suggested_action}

Timestamp: {alert.timestamp}
"""

    def print_active_alerts(self):
        """Print all active alerts to console"""
        if not self.active_alerts:
            print("✓ No active alerts")
            return

        print(f"\n📊 Active Alerts ({len(self.active_alerts)}):\n")
        for i, alert in enumerate(self.active_alerts):
            print(f"{i+1}. {self.format_alert_for_display(alert)}")

    def get_alert_statistics(self) -> Dict:
        """Get statistics about alerts"""
        return {
            'total_active': len(self.active_alerts),
            'total_historical': len(self.alert_history),
            'by_severity': {
                severity.value: len([a for a in self.active_alerts if a.severity == severity])
                for severity in AlertSeverity
            },
            'by_type': {
                alert_type.value: len([a for a in self.active_alerts if a.alert_type == alert_type])
                for alert_type in AlertType
            },
            'critical_alerts': len([a for a in self.active_alerts if a.severity == AlertSeverity.CRITICAL]),
            'high_alerts': len([a for a in self.active_alerts if a.severity == AlertSeverity.HIGH])
        }


class AlertBuilder:
    """Builder for creating alerts with fluent API"""

    def __init__(self):
        self.alert_type: AlertType = None
        self.severity: AlertSeverity = AlertSeverity.MEDIUM
        self.developer_1: str = None
        self.developer_2: str = None
        self.resource: str = None
        self.reason: str = None
        self.suggested_action: str = None
        self.metadata: Dict = {}

    def with_type(self, alert_type: AlertType) -> 'AlertBuilder':
        self.alert_type = alert_type
        return self

    def with_severity(self, severity: AlertSeverity) -> 'AlertBuilder':
        self.severity = severity
        return self

    def with_developers(self, dev1: str, dev2: str) -> 'AlertBuilder':
        self.developer_1 = dev1
        self.developer_2 = dev2
        return self

    def with_resource(self, resource: str) -> 'AlertBuilder':
        self.resource = resource
        return self

    def with_reason(self, reason: str) -> 'AlertBuilder':
        self.reason = reason
        return self

    def with_suggestion(self, action: str) -> 'AlertBuilder':
        self.suggested_action = action
        return self

    def with_metadata(self, key: str, value) -> 'AlertBuilder':
        self.metadata[key] = value
        return self

    def build(self) -> ConflictAlert:
        """Build the alert"""
        return ConflictAlert(
            alert_type=self.alert_type,
            severity=self.severity,
            developer_1=self.developer_1,
            developer_2=self.developer_2,
            resource=self.resource,
            reason=self.reason,
            timestamp=datetime.now(),
            suggested_action=self.suggested_action,
            metadata=self.metadata
        )
