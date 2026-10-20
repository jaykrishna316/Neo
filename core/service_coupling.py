"""
Service Coupling Analysis - Track inter-service dependencies and coupling
"""

import json
from pathlib import Path
from typing import Dict, List, Set
from core.semantic_conflict_detector import SemanticAnalyzer


class ServiceCouplingAnalyzer:
    """Analyze coupling between services/modules"""

    def __init__(self, state_dir: str = ".neo_state"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.services_file = self.state_dir / "services.json"
        self.services = self._load_services()

    def _load_services(self) -> Dict:
        if self.services_file.exists():
            return json.loads(self.services_file.read_text())
        return {}

    def _save_services(self) -> None:
        self.services_file.write_text(json.dumps(self.services, indent=2))

    def analyze_file_coupling(self, file_path: str) -> Dict:
        """Analyze coupling score for a file"""
        try:
            analyzer = SemanticAnalyzer(file_path)
            symbols = analyzer.extract_symbols()
            deps = analyzer.analyze_dependencies()

            # Coupling score: based on external dependencies
            external_deps = len([d for d in deps if self._is_external(d)])
            total_deps = len(deps)

            coupling_score = (external_deps / total_deps) if total_deps > 0 else 0

            return {
                "file": file_path,
                "coupling_score": min(1.0, coupling_score),
                "external_dependencies": external_deps,
                "internal_dependencies": total_deps - external_deps,
                "total_dependencies": total_deps,
                "tightly_coupled": coupling_score > 0.7
            }
        except:
            return {"file": file_path, "coupling_score": 0.5, "error": "analysis failed"}

    def _is_external(self, dep: str) -> bool:
        """Check if dependency is external (not internal to repo)"""
        internal_prefixes = ["src/", "lib/", "./", "../"]
        return not any(dep.startswith(prefix) for prefix in internal_prefixes)

    def register_service(self, service_name: str, files: List[str]) -> Dict:
        """Register a service with its files"""
        self.services[service_name] = {
            "files": files,
            "dependencies": [],
            "dependents": []
        }
        self._save_services()
        return {"status": "registered", "service": service_name, "files": len(files)}

    def add_service_dependency(self, from_service: str, to_service: str) -> Dict:
        """Record dependency between services"""
        if from_service not in self.services:
            self.services[from_service] = {"files": [], "dependencies": [], "dependents": []}

        if to_service not in self.services:
            self.services[to_service] = {"files": [], "dependencies": [], "dependents": []}

        if to_service not in self.services[from_service]["dependencies"]:
            self.services[from_service]["dependencies"].append(to_service)

        if from_service not in self.services[to_service]["dependents"]:
            self.services[to_service]["dependents"].append(from_service)

        self._save_services()

        return {
            "status": "added",
            "from": from_service,
            "to": to_service
        }

    def get_service_count(self) -> int:
        """Total number of services"""
        return len(self.services)

    def get_service_dependencies(self, service: str) -> List[str]:
        """Get services that a service depends on"""
        if service in self.services:
            return self.services[service].get("dependencies", [])
        return []

    def get_dependent_services(self, service: str) -> List[str]:
        """Get services that depend on a service"""
        if service in self.services:
            return self.services[service].get("dependents", [])
        return []

    def get_coupling_score(self) -> float:
        """Overall system coupling score (0-1)"""
        if not self.services:
            return 0.0

        total_possible_dependencies = len(self.services) * (len(self.services) - 1)
        total_actual_dependencies = sum(
            len(svc.get("dependencies", [])) for svc in self.services.values()
        )

        return (total_actual_dependencies / total_possible_dependencies) if total_possible_dependencies > 0 else 0

    def get_tightly_coupled_pairs(self) -> List[Dict]:
        """Find services with high coupling"""
        pairs = []
        for service, info in self.services.items():
            for dep in info.get("dependencies", []):
                # Bidirectional dependency = tight coupling
                if service in self.services.get(dep, {}).get("dependencies", []):
                    pairs.append({
                        "services": [service, dep],
                        "bidirectional": True,
                        "risk": "HIGH"
                    })
        return pairs

    def get_circular_dependencies(self) -> List[List[str]]:
        """Detect circular service dependencies"""
        cycles = []

        def find_cycle(start: str, current: str, path: List[str], visited: Set[str]) -> bool:
            if current in visited:
                if current == start and len(path) > 1:
                    cycles.append(path.copy())
                return True

            visited.add(current)
            for dep in self.services.get(current, {}).get("dependencies", []):
                path.append(dep)
                find_cycle(start, dep, path, visited.copy())
                path.pop()

            return False

        for service in self.services:
            find_cycle(service, service, [service], set())

        # Deduplicate cycles
        unique_cycles = []
        for cycle in cycles:
            normalized = tuple(sorted(cycle[:-1]))
            if normalized not in [tuple(sorted(c[:-1])) for c in unique_cycles]:
                unique_cycles.append(cycle)

        return unique_cycles

    def get_service_metrics(self) -> Dict:
        """Get all service coupling metrics"""
        return {
            "service_count": self.get_service_count(),
            "overall_coupling_score": self.get_coupling_score(),
            "tightly_coupled_pairs": len(self.get_tightly_coupled_pairs()),
            "circular_dependencies": len(self.get_circular_dependencies()),
            "services": list(self.services.keys())
        }


# Global instance
_analyzer = None


def get_analyzer():
    global _analyzer
    if not _analyzer:
        _analyzer = ServiceCouplingAnalyzer()
    return _analyzer


def analyze_file_coupling(file_path: str):
    return get_analyzer().analyze_file_coupling(file_path)


def get_service_metrics():
    return get_analyzer().get_service_metrics()
