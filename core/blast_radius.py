#!/usr/bin/env python3
"""
Blast Radius with Cost Estimation

Calculates the impact scope and estimated cost (dev-hours + tokens) of a change.
Helps developers make informed decisions before generation.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import json


@dataclass
class FileCostEstimate:
    """Cost estimate for fixing one dependent file."""
    file_path: str
    complexity: str  # "easy", "medium", "hard"
    estimated_minutes: float
    token_estimate: int
    fix_type: str  # "syntactic", "type", "semantic"
    reason: str


@dataclass
class BlastRadiusReport:
    """Complete blast radius analysis for a change."""
    source_file: str
    total_dependents: int
    easy_fixes: int
    medium_fixes: int
    hard_fixes: int
    total_estimated_hours: float
    total_token_cost: int
    details: List[FileCostEstimate]

    def to_dict(self) -> Dict:
        return {
            "source_file": self.source_file,
            "total_dependents": self.total_dependents,
            "easy_fixes": self.easy_fixes,
            "medium_fixes": self.medium_fixes,
            "hard_fixes": self.hard_fixes,
            "total_estimated_hours": round(self.total_estimated_hours, 1),
            "total_token_cost": self.total_token_cost,
            "details": [
                {
                    "file": d.file_path,
                    "complexity": d.complexity,
                    "minutes": d.estimated_minutes,
                    "tokens": d.token_estimate,
                    "type": d.fix_type,
                    "reason": d.reason
                }
                for d in self.details
            ]
        }


class ComplexityScorer:
    """Score file complexity based on file type and size."""

    # Complexity score by file extension
    EXTENSION_SCORES = {
        ".py": 1.0,
        ".js": 1.1,
        ".ts": 1.2,
        ".go": 1.0,
        ".java": 1.3,
        ".cpp": 1.4,
        ".c": 1.3,
        ".rb": 0.9,
        ".rs": 1.2,
    }

    # Base minutes to fix by complexity level
    COMPLEXITY_MINUTES = {
        "easy": 2,      # Syntactic only (1-2 min)
        "medium": 7,    # Type system (5-10 min)
        "hard": 45,     # Semantic/logic (30-60 min)
    }

    @staticmethod
    def get_file_extension(file_path: str) -> str:
        """Get file extension."""
        return Path(file_path).suffix.lower()

    @staticmethod
    def score_file(file_path: str) -> float:
        """Score file by extension."""
        ext = ComplexityScorer.get_file_extension(file_path)
        return ComplexityScorer.EXTENSION_SCORES.get(ext, 1.0)

    @staticmethod
    def score_lines(file_path: str) -> float:
        """Score file by number of lines (scale factor)."""
        try:
            path = Path(file_path)
            if not path.exists():
                return 1.0

            lines = len(path.read_text().split('\n'))

            # Linear scaling: more lines = proportionally more work
            # 500 lines = 1.0x, 1000 lines = 1.5x, 2000 lines = 2.0x
            if lines < 500:
                return 0.8
            elif lines < 1000:
                return 1.0
            elif lines < 2000:
                return 1.5
            else:
                return 2.0
        except:
            return 1.0


class TokenEstimator:
    """Estimate token cost for fixing code."""

    # Token cost constants
    TOKENS_PER_MINUTE = 50  # Approximate tokens generated per minute of coding
    TOKENS_PER_FIX_TYPE = {
        "syntactic": 100,       # Import fix, simple rename
        "type": 300,            # Type signature fix
        "semantic": 1000,       # Logic fix, algorithm change
    }

    @staticmethod
    def estimate_for_complexity(complexity: str, estimated_minutes: float) -> int:
        """Estimate tokens based on fix complexity and time."""
        base_tokens = TokenEstimator.TOKENS_PER_FIX_TYPE.get(complexity, 100)
        # Add proportional tokens for time spent
        time_tokens = int(estimated_minutes * TokenEstimator.TOKENS_PER_MINUTE)
        return base_tokens + time_tokens


class BlastRadiusCalculator:
    """Calculate blast radius for a change."""

    def __init__(self, dependencies: Optional[Dict[str, List[str]]] = None):
        """
        Initialize with optional dependency map.

        Args:
            dependencies: Dict mapping file_path -> [dependent_files]
        """
        self.dependencies = dependencies or {}

    def set_dependencies(self, dependencies: Dict[str, List[str]]) -> None:
        """Set the dependency map."""
        self.dependencies = dependencies

    def calculate(self, source_file: str, change_type: str = "general") -> BlastRadiusReport:
        """
        Calculate blast radius for a change.

        Args:
            source_file: File that changed
            change_type: Type of change ("signature", "logic", "refactor", "general")

        Returns:
            BlastRadiusReport with full cost analysis
        """
        dependents = self.dependencies.get(source_file, [])

        details = []
        easy_count = 0
        medium_count = 0
        hard_count = 0
        total_hours = 0.0
        total_tokens = 0

        for dependent in dependents:
            estimate = self._estimate_file_fix(dependent, source_file, change_type)
            details.append(estimate)

            total_hours += estimate.estimated_minutes / 60.0
            total_tokens += estimate.token_estimate

            if estimate.complexity == "easy":
                easy_count += 1
            elif estimate.complexity == "medium":
                medium_count += 1
            else:
                hard_count += 1

        return BlastRadiusReport(
            source_file=source_file,
            total_dependents=len(dependents),
            easy_fixes=easy_count,
            medium_fixes=medium_count,
            hard_fixes=hard_count,
            total_estimated_hours=total_hours,
            total_token_cost=total_tokens,
            details=details
        )

    def _estimate_file_fix(
        self,
        dependent_file: str,
        source_file: str,
        change_type: str
    ) -> FileCostEstimate:
        """Estimate cost to fix one dependent file."""

        # Determine fix type based on change type
        if change_type == "signature":
            fix_type = "type"
            complexity = "medium"
            reason = "API/signature change requires update"
        elif change_type == "logic":
            fix_type = "semantic"
            complexity = "hard"
            reason = "Logic change requires semantic analysis"
        elif change_type == "refactor":
            fix_type = "semantic"
            complexity = "hard"
            reason = "Refactoring may require large-scale updates"
        else:
            # General change - classify as "easy" unless it's a major file
            fix_type = "syntactic"
            complexity = "easy"
            reason = "Syntax/import updates likely"

        # Score complexity by file characteristics
        ext_score = ComplexityScorer.score_file(dependent_file)
        line_score = ComplexityScorer.score_lines(dependent_file)
        base_minutes = ComplexityScorer.COMPLEXITY_MINUTES[complexity]

        estimated_minutes = base_minutes * ext_score * line_score
        token_estimate = TokenEstimator.estimate_for_complexity(complexity, estimated_minutes)

        return FileCostEstimate(
            file_path=dependent_file,
            complexity=complexity,
            estimated_minutes=estimated_minutes,
            token_estimate=token_estimate,
            fix_type=fix_type,
            reason=reason
        )

    def format_report(self, report: BlastRadiusReport) -> str:
        """Format report for display."""
        lines = []
        lines.append("=" * 80)
        lines.append(f"BLAST RADIUS ANALYSIS: {report.source_file}")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"Total affected files: {report.total_dependents}")
        lines.append("")

        lines.append("Fix difficulty breakdown:")
        lines.append(f"  🟢 Easy fixes (syntactic):  {report.easy_fixes} files (1-2 min each)")
        lines.append(f"  🟡 Medium fixes (type):     {report.medium_fixes} files (5-10 min each)")
        lines.append(f"  🔴 Hard fixes (semantic):   {report.hard_fixes} files (30-60 min each)")
        lines.append("")

        lines.append(f"Estimated cost:")
        lines.append(f"  Developer time: {report.total_estimated_hours:.1f} hours")
        lines.append(f"  Token cost: ${report.total_token_cost * 0.0001:.2f} (~{report.total_token_cost} tokens)")
        lines.append("")

        if report.total_dependents > 0 and report.total_dependents <= 10:
            lines.append("Affected files:")
            for detail in report.details:
                lines.append(f"  • {detail.file_path} ({detail.complexity}, {detail.estimated_minutes:.0f}m, {detail.token_estimate}T)")
        elif report.total_dependents > 10:
            lines.append(f"(Showing first 10 of {report.total_dependents} affected files)")
            for detail in report.details[:10]:
                lines.append(f"  • {detail.file_path} ({detail.complexity}, {detail.estimated_minutes:.0f}m, {detail.token_estimate}T)")

        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)
