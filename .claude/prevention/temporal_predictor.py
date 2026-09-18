"""
1C: Temporal Conflict Prediction
Predict conflicts before they happen based on time and context invalidation.
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class TemporalRisk:
    """Represents temporal risk of conflict"""
    resource: str
    developer_1: str
    developer_2: str
    risk_score: float  # 0-1
    time_until_conflict: timedelta
    factors: List[str]  # contributing factors


class TemporalPredictor:
    """Predicts conflicts based on temporal patterns and context invalidation"""

    def __init__(self):
        self.predictions: List[TemporalRisk] = []
        self.conflict_history: Dict[str, List[datetime]] = {}  # resource -> timestamps
        self.context_invalidation_map: Dict[str, datetime] = {}  # resource -> when invalidated

    def record_context_invalidation(self, resource: str):
        """Record when context becomes invalidated for a resource"""
        self.context_invalidation_map[resource] = datetime.now()

    def record_developer_activity(self, developer: str, resource: str, timestamp: datetime):
        """Record developer activity on a resource"""
        if resource not in self.conflict_history:
            self.conflict_history[resource] = []
        self.conflict_history[resource].append(timestamp)

    def predict_conflict(self, dev1: str, dev2: str, resource: str,
                        lookhead_minutes: int = 120) -> Optional[TemporalRisk]:
        """
        Predict if a conflict will occur between dev1 and dev2 on resource.

        Factors considered:
        - Context invalidation in the resource
        - Both developers recently active on the resource
        - Time since last conflict on this resource
        """
        risk_score = 0.0
        factors = []

        # Factor 1: Context invalidation
        if resource in self.context_invalidation_map:
            time_since_invalidation = datetime.now() - self.context_invalidation_map[resource]

            # Higher risk if recently invalidated
            if time_since_invalidation < timedelta(minutes=lookhead_minutes):
                invalidation_factor = 1.0 - (time_since_invalidation.total_seconds() /
                                             timedelta(minutes=lookhead_minutes).total_seconds())
                risk_score += invalidation_factor * 0.4
                factors.append(f"Context invalidated {time_since_invalidation} ago")

        # Factor 2: Recent concurrent activity
        if resource in self.conflict_history and len(self.conflict_history[resource]) >= 2:
            recent_activities = [t for t in self.conflict_history[resource]
                               if datetime.now() - t < timedelta(minutes=lookhead_minutes)]

            if len(recent_activities) >= 2:
                activity_factor = min(0.5, len(recent_activities) * 0.1)
                risk_score += activity_factor
                factors.append(f"{len(recent_activities)} activities in last {lookhead_minutes} mins")

        # Factor 3: High conflict resource history
        if resource in self.conflict_history:
            num_past_conflicts = len(self.conflict_history[resource])
            if num_past_conflicts > 3:
                history_factor = min(0.3, num_past_conflicts * 0.05)
                risk_score += history_factor
                factors.append(f"High-conflict resource ({num_past_conflicts} past conflicts)")

        if risk_score > 0.3:  # Threshold for prediction
            time_until = timedelta(minutes=lookhead_minutes)
            prediction = TemporalRisk(
                resource=resource,
                developer_1=dev1,
                developer_2=dev2,
                risk_score=min(1.0, risk_score),
                time_until_conflict=time_until,
                factors=factors
            )

            self.predictions.append(prediction)
            return prediction

        return None

    def get_high_risk_conflicts(self, threshold: float = 0.7) -> List[TemporalRisk]:
        """Get all high-risk conflict predictions"""
        return [p for p in self.predictions if p.risk_score >= threshold]

    def get_predictions_for_resource(self, resource: str) -> List[TemporalRisk]:
        """Get all predictions for a specific resource"""
        return [p for p in self.predictions if p.resource == resource]

    def get_predictions_for_developer(self, developer: str) -> List[TemporalRisk]:
        """Get all predictions involving a specific developer"""
        return [p for p in self.predictions
                if p.developer_1 == developer or p.developer_2 == developer]

    def get_resource_conflict_frequency(self, resource: str) -> Dict:
        """Get conflict frequency statistics for a resource"""
        if resource not in self.conflict_history:
            return {'frequency': 0, 'trend': 'stable'}

        activities = self.conflict_history[resource]

        # Check recent trend (last 7 days)
        now = datetime.now()
        recent = len([t for t in activities if now - t < timedelta(days=7)])
        total = len(activities)

        return {
            'total_activities': total,
            'recent_activities_7d': recent,
            'activity_rate': recent / 7 if total > 0 else 0,
            'trend': 'increasing' if recent > total / 2 else 'stable'
        }

    def cleanup_old_predictions(self, days: int = 7):
        """Remove predictions older than N days"""
        cutoff = datetime.now() - timedelta(days=days)
        self.predictions = [p for p in self.predictions
                           if datetime.now() - p.time_until_conflict < timedelta(days=days)]

    def print_status(self):
        """Print temporal prediction status"""
        print("\n⏱️ Temporal Conflict Prediction Status")
        print("=" * 60)

        high_risk = self.get_high_risk_conflicts(threshold=0.7)
        medium_risk = [p for p in self.predictions if 0.5 <= p.risk_score < 0.7]

        print(f"Active Predictions: {len(self.predictions)}")
        print(f"  🔴 High Risk (>0.7): {len(high_risk)}")
        print(f"  🟠 Medium Risk (0.5-0.7): {len(medium_risk)}")

        if high_risk:
            print(f"\nHigh-Risk Conflicts:")
            for pred in high_risk[:5]:  # Top 5
                print(f"  {pred.developer_1} ↔ {pred.developer_2} on {pred.resource}")
                print(f"    Risk: {pred.risk_score:.0%}")
                print(f"    Factors: {', '.join(pred.factors[:2])}")

        print("=" * 60)
