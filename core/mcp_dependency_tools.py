"""
MCP tools for Neo dependency tracking
Provides neo_* tools for checking and managing cross-repo dependencies
"""

from core.dependency_tracker import DependencyTracker
from typing import Dict, List, Any


class NeoDependencyTools:
    """MCP tool implementations for dependency management"""

    def __init__(self, repo_path: str = "."):
        self.tracker = DependencyTracker(repo_path)

    def neo_check_dependent_repos(self,
                                   changed_files: List[str],
                                   repo: str = "neo") -> Dict[str, Any]:
        """
        Check which dependent repos are impacted by code changes

        MCP Tool: neo_check_dependent_repos
        Input: {changed_files: [list of file paths], repo: string}
        Output: {impacted_repos: [list], summary: {count, risk_levels}}
        """
        impacted = self.tracker.check_dependent_repos(changed_files)

        if not impacted:
            return {
                "status": "success",
                "impacted_repos": [],
                "summary": {
                    "total": 0,
                    "critical": 0,
                    "high_risk": 0
                }
            }

        critical_count = sum(1 for r in impacted if r.get("critical"))
        high_risk_count = sum(1 for r in impacted if r.get("risk_level") == "HIGH")

        return {
            "status": "success",
            "impacted_repos": impacted,
            "summary": {
                "total": len(impacted),
                "critical": critical_count,
                "high_risk": high_risk_count,
                "message": f"Found {len(impacted)} impacted repos ({critical_count} critical)"
            }
        }

    def neo_log_dependency_change(self,
                                   pr_number: int,
                                   changed_files: List[str],
                                   changed_by: str,
                                   repo: str = "neo") -> Dict[str, Any]:
        """
        Log a code change and identify dependent repos

        MCP Tool: neo_log_dependency_change
        Input: {pr_number: int, changed_files: [list], changed_by: string}
        Output: {logged: bool, dependencies: [list], pr: int}
        """
        change = self.tracker.log_dependency_change(
            pr_number=pr_number,
            changed_files=changed_files,
            changed_by=changed_by,
            repo=repo
        )

        return {
            "status": "logged",
            "pr": pr_number,
            "changed_files": len(change.changed_files),
            "dependent_repos": len(change.dependent_repos or []),
            "dependencies": change.dependent_repos or [],
            "message": f"Logged {len(change.dependent_repos or [])} dependencies for PR #{pr_number}"
        }

    def neo_add_test_result(self,
                           pr_number: int,
                           repo: str,
                           passed: bool,
                           message: str = "",
                           logs: str = "") -> Dict[str, Any]:
        """
        Record test results from a dependent repo

        MCP Tool: neo_add_test_result
        Input: {pr_number: int, repo: string, passed: bool, message: string}
        Output: {recorded: bool, pr: int, repo: string}
        """
        self.tracker.add_test_result(
            pr_number=pr_number,
            repo=repo,
            test_result={
                "passed": passed,
                "message": message,
                "logs": logs
            }
        )

        return {
            "status": "recorded",
            "pr": pr_number,
            "repo": repo,
            "passed": passed,
            "message": f"Test result recorded for {repo}"
        }

    def neo_get_dependency_status(self, pr_number: int) -> Dict[str, Any]:
        """
        Get dependency status and test results for a PR

        MCP Tool: neo_get_dependency_status
        Input: {pr_number: int}
        Output: {dependencies: [list], tests: [results], summary: {stats}}
        """
        status = self.tracker.get_dependency_status(pr_number)
        return {
            "status": "retrieved",
            "pr": pr_number,
            **status
        }

    def neo_generate_pr_comment(self, pr_number: int) -> Dict[str, Any]:
        """
        Generate markdown comment for PR dependencies

        MCP Tool: neo_generate_pr_comment
        Input: {pr_number: int}
        Output: {comment: markdown_string}
        """
        comment = self.tracker.generate_pr_comment(pr_number)

        return {
            "status": "generated",
            "pr": pr_number,
            "comment": comment,
            "ready_to_post": True
        }


# Initialize tools for MCP server integration
def get_mcp_tools() -> List[Dict]:
    """Get tool definitions for MCP server"""
    return [
        {
            "name": "neo_check_dependent_repos",
            "description": "Check which dependent repos are impacted by code changes",
            "input": {
                "type": "object",
                "properties": {
                    "changed_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of file paths changed in this PR"
                    },
                    "repo": {
                        "type": "string",
                        "description": "Repository name (default: neo)"
                    }
                },
                "required": ["changed_files"]
            }
        },
        {
            "name": "neo_log_dependency_change",
            "description": "Log a code change and identify dependent repos",
            "input": {
                "type": "object",
                "properties": {
                    "pr_number": {
                        "type": "integer",
                        "description": "PR number"
                    },
                    "changed_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Files changed"
                    },
                    "changed_by": {
                        "type": "string",
                        "description": "Developer/agent name"
                    },
                    "repo": {
                        "type": "string",
                        "description": "Repository name"
                    }
                },
                "required": ["pr_number", "changed_files", "changed_by"]
            }
        },
        {
            "name": "neo_add_test_result",
            "description": "Record test results from a dependent repo",
            "input": {
                "type": "object",
                "properties": {
                    "pr_number": {
                        "type": "integer",
                        "description": "PR number"
                    },
                    "repo": {
                        "type": "string",
                        "description": "Dependent repo name"
                    },
                    "passed": {
                        "type": "boolean",
                        "description": "Whether tests passed"
                    },
                    "message": {
                        "type": "string",
                        "description": "Test result message"
                    },
                    "logs": {
                        "type": "string",
                        "description": "Test logs (optional)"
                    }
                },
                "required": ["pr_number", "repo", "passed"]
            }
        },
        {
            "name": "neo_get_dependency_status",
            "description": "Get dependency status and test results for a PR",
            "input": {
                "type": "object",
                "properties": {
                    "pr_number": {
                        "type": "integer",
                        "description": "PR number"
                    }
                },
                "required": ["pr_number"]
            }
        },
        {
            "name": "neo_generate_pr_comment",
            "description": "Generate markdown comment with dependency status for PR",
            "input": {
                "type": "object",
                "properties": {
                    "pr_number": {
                        "type": "integer",
                        "description": "PR number"
                    }
                },
                "required": ["pr_number"]
            }
        }
    ]
