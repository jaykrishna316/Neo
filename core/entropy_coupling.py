#!/usr/bin/env python3
"""
Entropy-Based Coupling Detection

Uses information theory (mutual information) to discover which services
are implicitly coupled - they change together even if they don't import each other.

Finds architectural problems that traditional dependency analysis misses:
- Services that move together but should be independent
- Hidden cohesion (services that belong together)
- Architectural misalignment (what is vs. what should be)
"""

import math
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict


@dataclass
class EntropyCouplingScore:
    """Entropy-based coupling score between two services."""
    service_a: str
    service_b: str
    mutual_information: float  # 0.0 to 1.0
    joint_probability: float  # P(A and B change together)
    conditional_prob_a_given_b: float  # P(A | B)
    conditional_prob_b_given_a: float  # P(B | A)
    change_correlation: float  # How often they change together vs. separately
    surprise_reduction: float  # How much knowing A changed reduces uncertainty about B


@dataclass
class ServiceCluster:
    """A cluster of services with high mutual coupling."""
    services: List[str]
    internal_coupling: float  # Average coupling within cluster
    external_coupling: float  # Average coupling to services outside
    cohesion_score: float  # Higher = more cohesive (should be together)
    size: int


@dataclass
class ArchitecturalMisalignment:
    """Identifies when actual structure doesn't match natural structure."""
    service_a: str
    service_b: str
    mutual_information: float
    imports_each_other: bool
    misalignment_type: str  # "hidden_coupling" or "unnecessary_separation"
    severity: str  # "low", "medium", "high"
    recommendation: str


class EntropyCalculator:
    """Calculate information-theoretic metrics."""

    @staticmethod
    def entropy(probabilities: List[float]) -> float:
        """
        Calculate Shannon entropy.

        H(X) = -Σ p(x) * log2(p(x))

        High entropy = high uncertainty
        Low entropy = low uncertainty (very predictable)
        """
        entropy = 0.0
        for p in probabilities:
            if p > 0:
                entropy -= p * math.log2(p)
        return entropy

    @staticmethod
    def joint_entropy(joint_probs: Dict[Tuple[bool, bool], float]) -> float:
        """Calculate joint entropy H(X, Y)."""
        return EntropyCalculator.entropy(list(joint_probs.values()))

    @staticmethod
    def mutual_information(
        p_a: float,
        p_b: float,
        p_both: float
    ) -> float:
        """
        Calculate mutual information I(A; B).

        I(A; B) = H(A) + H(B) - H(A, B)

        Or equivalently:
        I(A; B) = Σ Σ p(a,b) * log2(p(a,b) / (p(a) * p(b)))

        High MI = services are tightly coupled
        Low MI = services are independent
        """
        if p_a == 0 or p_b == 0 or p_both == 0:
            return 0.0

        # Avoid log(0)
        p_both = max(p_both, 1e-10)
        p_a = max(p_a, 1e-10)
        p_b = max(p_b, 1e-10)

        mi = 0.0

        # Both change
        mi += p_both * math.log2(p_both / (p_a * p_b))

        # A changes, B doesn't
        p_a_not_b = p_a - p_both
        if p_a_not_b > 0:
            mi += p_a_not_b * math.log2(p_a_not_b / (p_a * (1 - p_b)))

        # B changes, A doesn't
        p_b_not_a = p_b - p_both
        if p_b_not_a > 0:
            mi += p_b_not_a * math.log2(p_b_not_a / ((1 - p_a) * p_b))

        # Neither changes
        p_neither = 1 - p_a - p_b + p_both
        if p_neither > 0:
            mi += p_neither * math.log2(p_neither / ((1 - p_a) * (1 - p_b)))

        return max(0, mi)  # Clamp to non-negative


class EntropyCouplingDetector:
    """Detect coupling using entropy/information theory."""

    def __init__(self, history_file: str = ".devsync/coupling/coupling_history.jsonl"):
        """Initialize with change history."""
        self.history_file = Path(history_file)
        self.changes = []
        self._load_history()

    def _load_history(self) -> None:
        """Load change history from file."""
        if not self.history_file.exists():
            return

        with open(self.history_file) as f:
            for line in f:
                try:
                    self.changes.append(json.loads(line))
                except:
                    continue

    def compute_service_probabilities(self) -> Dict[str, float]:
        """
        Compute probability that each service changed in a random changeset.

        P(service_i) = (# of changes including service_i) / (total changes)
        """
        if not self.changes:
            return {}

        service_counts = defaultdict(int)

        for change in self.changes:
            services = change.get("services_changed", [])
            for service in services:
                service_counts[service] += 1

        total = len(self.changes)
        return {service: count / total for service, count in service_counts.items()}

    def compute_coupling_matrix(self) -> Dict[Tuple[str, str], EntropyCouplingScore]:
        """
        Compute entropy-based coupling between all services.

        Returns dict mapping (service_a, service_b) -> EntropyCouplingScore
        """
        if not self.changes:
            return {}

        service_probs = self.compute_service_probabilities()
        services = list(service_probs.keys())

        coupling_matrix = {}
        total_changes = len(self.changes)

        for i, svc_a in enumerate(services):
            for svc_b in services[i+1:]:
                # Count occurrences
                count_a = sum(1 for c in self.changes if svc_a in c.get("services_changed", []))
                count_b = sum(1 for c in self.changes if svc_b in c.get("services_changed", []))
                count_both = sum(
                    1 for c in self.changes
                    if svc_a in c.get("services_changed", [])
                    and svc_b in c.get("services_changed", [])
                )

                p_a = count_a / total_changes
                p_b = count_b / total_changes
                p_both = count_both / total_changes

                # Calculate metrics
                mi = EntropyCalculator.mutual_information(p_a, p_b, p_both)

                # Normalize MI to 0-1 range using max possible MI
                max_mi = min(
                    EntropyCalculator.entropy([p_a, 1-p_a]),
                    EntropyCalculator.entropy([p_b, 1-p_b])
                )
                normalized_mi = mi / max_mi if max_mi > 0 else 0.0

                # Conditional probabilities
                p_a_given_b = p_both / p_b if p_b > 0 else 0
                p_b_given_a = p_both / p_a if p_a > 0 else 0

                # Change correlation (0-1)
                # How much more likely to change together vs. independently
                independent_prob = p_a * p_b
                correlation = (p_both / independent_prob) if independent_prob > 0 else 0
                correlation = min(correlation / 5, 1.0)  # Normalize

                key = tuple(sorted([svc_a, svc_b]))
                coupling_matrix[key] = EntropyCouplingScore(
                    service_a=svc_a,
                    service_b=svc_b,
                    mutual_information=normalized_mi,
                    joint_probability=p_both,
                    conditional_prob_a_given_b=p_a_given_b,
                    conditional_prob_b_given_a=p_b_given_a,
                    change_correlation=correlation,
                    surprise_reduction=mi
                )

        return coupling_matrix

    def cluster_services(self, coupling_matrix: Dict) -> List[ServiceCluster]:
        """
        Cluster services by entropy coupling.

        Uses hierarchical clustering based on MI distances.
        Services with high MI are grouped together.
        """
        if not coupling_matrix:
            return []

        # Build distance matrix (inverse of MI)
        all_services = set()
        for (a, b), score in coupling_matrix.items():
            all_services.add(a)
            all_services.add(b)

        services = sorted(list(all_services))
        distances = defaultdict(lambda: 1.0)  # Default to max distance

        for (a, b), score in coupling_matrix.items():
            # Distance = 1 - MI (high MI = low distance)
            distance = 1.0 - score.mutual_information
            distances[(a, b)] = distance
            distances[(b, a)] = distance

        # Simple clustering: services with MI > 0.6 are clustered
        high_coupling_pairs = [
            (a, b) for (a, b), score in coupling_matrix.items()
            if score.mutual_information > 0.6
        ]

        # Build clusters greedily
        clusters_dict = {s: {s} for s in services}

        for a, b in high_coupling_pairs:
            if clusters_dict[a] != clusters_dict[b]:
                # Merge clusters
                new_cluster = clusters_dict[a] | clusters_dict[b]
                for service in new_cluster:
                    clusters_dict[service] = new_cluster

        # Convert to list of unique clusters
        seen = set()
        clusters = []
        for cluster_set in clusters_dict.values():
            cluster_key = frozenset(cluster_set)
            if cluster_key not in seen:
                seen.add(cluster_key)

                # Calculate cluster metrics
                cluster_list = sorted(list(cluster_set))
                internal_coupling_scores = []

                for i, a in enumerate(cluster_list):
                    for b in cluster_list[i+1:]:
                        key = tuple(sorted([a, b]))
                        if key in coupling_matrix:
                            internal_coupling_scores.append(
                                coupling_matrix[key].mutual_information
                            )

                internal_coupling = (
                    sum(internal_coupling_scores) / len(internal_coupling_scores)
                    if internal_coupling_scores else 0.0
                )

                # External coupling (to services outside cluster)
                external_scores = []
                for service in cluster_list:
                    for other in services:
                        if other not in cluster_set:
                            key = tuple(sorted([service, other]))
                            if key in coupling_matrix:
                                external_scores.append(
                                    coupling_matrix[key].mutual_information
                                )

                external_coupling = (
                    sum(external_scores) / len(external_scores)
                    if external_scores else 0.0
                )

                # Cohesion = internal - external (higher = more cohesive)
                cohesion = internal_coupling - external_coupling

                clusters.append(ServiceCluster(
                    services=cluster_list,
                    internal_coupling=internal_coupling,
                    external_coupling=external_coupling,
                    cohesion_score=cohesion,
                    size=len(cluster_list)
                ))

        return sorted(clusters, key=lambda c: c.cohesion_score, reverse=True)

    def detect_misalignments(
        self,
        coupling_matrix: Dict,
        actual_imports: Optional[Dict[str, List[str]]] = None
    ) -> List[ArchitecturalMisalignment]:
        """
        Detect architectural misalignments.

        Types:
        1. Hidden coupling: High MI but don't import
        2. Unnecessary separation: Low MI but import
        """
        misalignments = []

        for (svc_a, svc_b), score in coupling_matrix.items():
            # Check if they import each other
            imports = False
            if actual_imports:
                imports = (
                    (svc_a in actual_imports.get(svc_b, []))
                    or (svc_b in actual_imports.get(svc_a, []))
                )

            # Hidden coupling: High MI but no imports
            if score.mutual_information > 0.7 and not imports:
                severity = "high" if score.mutual_information > 0.85 else "medium"
                misalignments.append(ArchitecturalMisalignment(
                    service_a=svc_a,
                    service_b=svc_b,
                    mutual_information=score.mutual_information,
                    imports_each_other=imports,
                    misalignment_type="hidden_coupling",
                    severity=severity,
                    recommendation=f"Services {svc_a} and {svc_b} change together {score.change_correlation:.1%} of the time but don't import. Consider merging or defining explicit interface."
                ))

            # Unnecessary separation: Low MI but imports
            elif score.mutual_information < 0.3 and imports:
                misalignments.append(ArchitecturalMisalignment(
                    service_a=svc_a,
                    service_b=svc_b,
                    mutual_information=score.mutual_information,
                    imports_each_other=imports,
                    misalignment_type="unnecessary_separation",
                    severity="low",
                    recommendation=f"Services {svc_a} and {svc_b} import but rarely change together. May indicate unnecessary coupling or one-way dependency."
                ))

        return sorted(misalignments, key=lambda m: m.mutual_information, reverse=True)

    def format_report(
        self,
        coupling_matrix: Dict,
        clusters: List[ServiceCluster],
        misalignments: List[ArchitecturalMisalignment]
    ) -> str:
        """Format entropy coupling analysis for display."""
        lines = []
        lines.append("=" * 80)
        lines.append("ENTROPY-BASED COUPLING ANALYSIS")
        lines.append("=" * 80)
        lines.append("")

        if not coupling_matrix:
            lines.append("No coupling data available yet.")
            lines.append("Collecting change history will enable analysis in 3-6 months.")
            return "\n".join(lines)

        # Coupling matrix summary
        high_coupling = sorted(
            [(k, v) for k, v in coupling_matrix.items() if v.mutual_information > 0.6],
            key=lambda x: x[1].mutual_information,
            reverse=True
        )

        lines.append("HIGH COUPLING (MI > 0.6):")
        lines.append("")
        for (a, b), score in high_coupling[:10]:
            lines.append(f"  {a} ↔ {b}: MI={score.mutual_information:.2f}")
            lines.append(f"    They change together {score.change_correlation:.1%} of the time")
            lines.append(f"    If {a} changes, {b} has {score.conditional_prob_b_given_a:.1%} chance of changing")
        lines.append("")

        # Service clusters
        if clusters:
            lines.append("SERVICE CLUSTERS (Cohesive groups):")
            lines.append("")
            for i, cluster in enumerate(clusters[:5], 1):
                lines.append(f"  Cluster {i}: {', '.join(cluster.services)}")
                lines.append(f"    Internal coupling: {cluster.internal_coupling:.2f}")
                lines.append(f"    External coupling: {cluster.external_coupling:.2f}")
                lines.append(f"    Cohesion score: {cluster.cohesion_score:.2f}")
            lines.append("")

        # Architectural misalignments
        if misalignments:
            lines.append("ARCHITECTURAL MISALIGNMENTS:")
            lines.append("")

            hidden = [m for m in misalignments if m.misalignment_type == "hidden_coupling"]
            unnecessary = [m for m in misalignments if m.misalignment_type == "unnecessary_separation"]

            if hidden:
                lines.append("⚠️  HIDDEN COUPLING (changing together, not importing):")
                for m in hidden[:5]:
                    lines.append(f"  {m.service_a} ↔ {m.service_b} (MI={m.mutual_information:.2f})")
                    lines.append(f"    {m.recommendation}")
                lines.append("")

            if unnecessary:
                lines.append("ℹ️  UNNECESSARY SEPARATION (importing, rarely changing together):")
                for m in unnecessary[:5]:
                    lines.append(f"  {m.service_a} ↔ {m.service_b} (MI={m.mutual_information:.2f})")
                    lines.append(f"    {m.recommendation}")
                lines.append("")

        lines.append("=" * 80)
        lines.append("Note: Analysis requires 3-6 months of change history for meaningful results")
        lines.append("=" * 80)

        return "\n".join(lines)


def analyze_entropy_coupling(
    history_file: str = ".devsync/coupling/coupling_history.jsonl",
    actual_imports: Optional[Dict[str, List[str]]] = None
) -> Dict:
    """
    Convenience function to run full entropy coupling analysis.

    Args:
        history_file: Path to change history
        actual_imports: Optional import graph (service -> [imports])

    Returns:
        {
            "success": boolean,
            "coupling_matrix": dict,
            "clusters": list,
            "misalignments": list,
            "report": formatted string
        }
    """
    try:
        detector = EntropyCouplingDetector(history_file)
        coupling_matrix = detector.compute_coupling_matrix()
        clusters = detector.cluster_services(coupling_matrix)
        misalignments = detector.detect_misalignments(coupling_matrix, actual_imports)

        return {
            "success": True,
            "coupling_matrix": {
                f"{k[0]},{k[1]}": {
                    "mutual_information": v.mutual_information,
                    "joint_probability": v.joint_probability,
                    "conditional_a_given_b": v.conditional_prob_a_given_b,
                    "conditional_b_given_a": v.conditional_prob_b_given_a,
                    "change_correlation": v.change_correlation
                }
                for k, v in coupling_matrix.items()
            },
            "clusters": [
                {
                    "services": c.services,
                    "internal_coupling": round(c.internal_coupling, 2),
                    "external_coupling": round(c.external_coupling, 2),
                    "cohesion": round(c.cohesion_score, 2),
                    "size": c.size
                }
                for c in clusters
            ],
            "misalignments": [
                {
                    "services": [m.service_a, m.service_b],
                    "type": m.misalignment_type,
                    "severity": m.severity,
                    "coupling": round(m.mutual_information, 2),
                    "recommendation": m.recommendation
                }
                for m in misalignments
            ],
            "report": detector.format_report(coupling_matrix, clusters, misalignments)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
