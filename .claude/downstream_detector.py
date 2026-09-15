"""
Downstream Impact Detector - Finds functions that depend on conflicting changes
Helps identify secondary impacts of PRIMARY conflicts
"""

import json
import re
from pathlib import Path
from typing import List, Dict


class DownstreamDetector:
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)

    def find_dependent_functions(self, file_path: str, function_name: str) -> List[Dict]:
        """
        Find all functions that call the conflicting function
        Returns list of dependent functions and their locations
        """

        dependents = []

        # Search for calls to this function in Python files
        pattern = rf"\b{function_name}\s*\("

        for py_file in self.repo_path.glob("**/*.py"):
            # Skip .claude and .activity_log directories
            if ".claude" in str(py_file) or ".activity_log" in str(py_file):
                continue

            try:
                content = py_file.read_text()
                lines = content.split('\n')

                for line_num, line in enumerate(lines, 1):
                    if re.search(pattern, line) and not line.strip().startswith("#"):
                        # Extract function name from this line context
                        caller_func = self._find_enclosing_function(lines, line_num)

                        if caller_func and caller_func != function_name:
                            dependents.append({
                                "file": str(py_file.relative_to(self.repo_path)),
                                "function": caller_func,
                                "line": line_num,
                                "code": line.strip(),
                                "severity": "medium"  # Dependent functions are medium impact
                            })
            except Exception as e:
                continue

        # Deduplicate
        seen = set()
        unique_dependents = []
        for dep in dependents:
            key = (dep["file"], dep["function"])
            if key not in seen:
                seen.add(key)
                unique_dependents.append(dep)

        return unique_dependents

    def flag_downstream_impacts(self, file_path: str, function_name: str,
                               change_description: str) -> Dict:
        """
        Flag downstream impacts of a change
        Returns warning if critical functions are affected
        """

        dependents = self.find_dependent_functions(file_path, function_name)

        critical_functions = [
            "login", "authenticate", "validate", "verify", "process_payment",
            "charge", "transaction", "authorization", "security"
        ]

        critical_impacts = [d for d in dependents
                          if any(crit in d["function"].lower() for crit in critical_functions)]

        return {
            "primary_function": function_name,
            "total_dependents": len(dependents),
            "critical_impacts": critical_impacts,
            "all_dependents": dependents,
            "warning_level": "high" if critical_impacts else "low",
            "recommendation": self._get_recommendation(critical_impacts)
        }

    def _find_enclosing_function(self, lines: List[str], line_num: int) -> str:
        """Find the function name that contains this line"""

        for i in range(line_num - 1, -1, -1):
            line = lines[i]
            # Look for def function_name( or async def
            match = re.search(r"^\s*(?:async\s+)?def\s+(\w+)\s*\(", line)
            if match:
                return match.group(1)

        return None

    def _get_recommendation(self, critical_impacts: List[Dict]) -> str:
        """Generate recommendation based on impacts"""

        if not critical_impacts:
            return "✅ No critical functions affected. Safe to merge."

        if len(critical_impacts) == 1:
            return f"⚠️ WARNING: {critical_impacts[0]['function']} depends on this. Requires extra testing."

        return f"🔴 CRITICAL: {len(critical_impacts)} critical functions affected. Requires approval + full test suite."


class DependencyGraph:
    """Build and visualize function dependency graph"""

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.graph = {}

    def build_graph(self) -> Dict:
        """Build function call graph for entire repo"""

        for py_file in self.repo_path.glob("**/*.py"):
            if ".claude" in str(py_file) or ".activity_log" in str(py_file):
                continue

            try:
                content = py_file.read_text()
                functions = self._extract_functions(content)

                for func_name in functions:
                    if func_name not in self.graph:
                        self.graph[func_name] = {
                            "file": str(py_file.relative_to(self.repo_path)),
                            "calls": [],
                            "called_by": []
                        }
            except:
                continue

        # Build call relationships
        for py_file in self.repo_path.glob("**/*.py"):
            if ".claude" in str(py_file) or ".activity_log" in str(py_file):
                continue

            try:
                content = py_file.read_text()
                functions = self._extract_functions(content)

                for func_name in functions:
                    calls = self._extract_calls(content, func_name)
                    if func_name in self.graph:
                        self.graph[func_name]["calls"] = calls

                        # Update called_by
                        for called_func in calls:
                            if called_func in self.graph:
                                if func_name not in self.graph[called_func]["called_by"]:
                                    self.graph[called_func]["called_by"].append(func_name)
            except:
                continue

        return self.graph

    def _extract_functions(self, content: str) -> List[str]:
        """Extract all function names from Python code"""
        matches = re.findall(r"^\s*(?:async\s+)?def\s+(\w+)\s*\(", content, re.MULTILINE)
        return matches

    def _extract_calls(self, content: str, function_name: str) -> List[str]:
        """Extract functions called within a function"""
        # Simplified: find function def, then extract calls until next def
        pattern = rf"^\s*(?:async\s+)?def\s+{function_name}\s*\("

        match = re.search(pattern, content, re.MULTILINE)
        if not match:
            return []

        start = match.end()
        # Find next function definition
        rest = content[start:]
        next_def = re.search(r"^\s*(?:async\s+)?def\s+", rest, re.MULTILINE)

        if next_def:
            func_body = rest[:next_def.start()]
        else:
            func_body = rest

        # Find all function calls
        calls = re.findall(r"\b(\w+)\s*\(", func_body)
        return [c for c in calls if c not in ["if", "for", "while", "return", "print"]]
