"""
MCP tools for Neo dependency tracking
Provides neo_* tools for checking and managing cross-repo dependencies
Includes Phases 1-4: Detection, Test Triggering, Auto-Comments, Merge Gates
Plus Impact Alerts: Unresolved dependency impact tracking
"""

from core.dependency_tracker import DependencyTracker
from core.test_triggering import TestTrigger
from core.github_pr_integration import GitHubPRIntegration
from core.merge_gate import MergeGate
from core.impact_alerts import ImpactAlertManager
from typing import Dict, List, Any
import os


class NeoDependencyTools:
    """MCP tool implementations for dependency management (Phases 1-4 + Impact Alerts)"""

    def __init__(self, repo_path: str = "."):
        self.tracker = DependencyTracker(repo_path)
        self.test_trigger = TestTrigger(repo_path)
        self.github_integration = GitHubPRIntegration(repo_path)
        self.merge_gate = MergeGate(repo_path)
        self.impact_alerts = ImpactAlertManager(repo_path)

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

    # Phase 2: Test Triggering
    def neo_trigger_dependent_repo_tests(self,
                                        pr_number: int,
                                        repo_name: str,
                                        ci_trigger_url: str,
                                        changed_files: List[str],
                                        test_command: str) -> Dict[str, Any]:
        """
        Trigger tests in dependent repository via CI webhook

        MCP Tool: neo_trigger_dependent_repo_tests
        Input: {pr_number, repo_name, ci_trigger_url, changed_files, test_command}
        Output: {status, repo, timestamp}
        """
        return self.test_trigger.trigger_dependent_repo_tests(
            pr_number=pr_number,
            repo_name=repo_name,
            ci_trigger_url=ci_trigger_url,
            changed_files=changed_files,
            test_command=test_command
        )

    def neo_trigger_github_actions(self,
                                  repo_owner: str,
                                  repo_name: str,
                                  workflow_file: str,
                                  ref: str = "main",
                                  inputs: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Trigger GitHub Actions workflow in dependent repo

        MCP Tool: neo_trigger_github_actions
        Input: {repo_owner, repo_name, workflow_file, ref, inputs}
        Output: {status, workflow, timestamp}
        """
        return self.test_trigger.trigger_github_actions(
            repo_owner=repo_owner,
            repo_name=repo_name,
            workflow_file=workflow_file,
            ref=ref,
            github_token=os.getenv("GITHUB_TOKEN"),
            inputs=inputs
        )

    # Phase 3: GitHub PR Auto-Comments
    def neo_post_pr_comment(self,
                           owner: str,
                           repo: str,
                           pr_number: int,
                           comment_body: str) -> Dict[str, Any]:
        """
        Post or update comment on PR with dependency status

        MCP Tool: neo_post_pr_comment
        Input: {owner, repo, pr_number, comment_body}
        Output: {status, comment_id, url}
        """
        return self.github_integration.post_dependency_comment(
            owner=owner,
            repo=repo,
            pr_number=pr_number,
            comment_body=comment_body
        )

    def neo_request_pr_review(self,
                             owner: str,
                             repo: str,
                             pr_number: int,
                             reviewers: List[str]) -> Dict[str, Any]:
        """
        Request review from specific users on PR

        MCP Tool: neo_request_pr_review
        Input: {owner, repo, pr_number, reviewers}
        Output: {status, reviewers_added}
        """
        return self.github_integration.request_review(
            owner=owner,
            repo=repo,
            pr_number=pr_number,
            reviewers=reviewers
        )

    # Phase 4: Merge Gate
    def neo_check_merge_gate(self, pr_number: int) -> Dict[str, Any]:
        """
        Check if PR can merge based on dependency test results

        MCP Tool: neo_check_merge_gate
        Input: {pr_number: int}
        Output: {can_merge: bool, blocking_issues, warnings}
        """
        can_merge, details = self.merge_gate.can_merge_to_main(pr_number)
        return {
            "status": "checked",
            "pr": pr_number,
            "can_merge": can_merge,
            **details
        }

    def neo_get_merge_status(self, pr_number: int) -> Dict[str, Any]:
        """
        Get detailed merge gate status for a PR

        MCP Tool: neo_get_merge_status
        Input: {pr_number: int}
        Output: {status, can_merge, blocking_issues}
        """
        return self.merge_gate.get_merge_status(pr_number)

    def neo_generate_merge_comment(self, pr_number: int) -> Dict[str, Any]:
        """
        Generate merge gate status comment for PR

        MCP Tool: neo_generate_merge_comment
        Input: {pr_number: int}
        Output: {comment: markdown_string}
        """
        comment = self.merge_gate.generate_merge_gate_comment(pr_number)
        return {
            "status": "generated",
            "pr": pr_number,
            "comment": comment,
            "ready_to_post": True
        }

    # Impact Alerts - Track unresolved dependency impacts
    def neo_check_impact_alerts(self, file_path: str) -> Dict[str, Any]:
        """
        Check for unresolved impact alerts on a file

        Called when developer declares intent to edit a file
        Returns any upstream changes that impact this file

        MCP Tool: neo_check_impact_alerts
        Input: {file_path: string}
        Output: {has_impacts: bool, alerts: [{...}]}
        """
        result = self.impact_alerts.check_impacts_on_file(file_path)
        return result

    def neo_create_impact_alert(self,
                               source_file: str,
                               target_file: str,
                               changed_by: str,
                               change_summary: str,
                               impact_reason: str,
                               pr_number: int = None) -> Dict[str, Any]:
        """
        Create an impact alert for unresolved dependency

        Called when a change impacts another file that hasn't addressed it yet

        MCP Tool: neo_create_impact_alert
        Input: {source_file, target_file, changed_by, change_summary, impact_reason, pr_number}
        Output: {status, alert_id}
        """
        return self.impact_alerts.create_alert(
            source_file=source_file,
            target_file=target_file,
            changed_by=changed_by,
            change_summary=change_summary,
            impact_reason=impact_reason,
            pr_number=pr_number
        )

    def neo_resolve_impact_alert(self,
                                target_file: str,
                                resolved_by: str,
                                resolution_notes: str = "") -> Dict[str, Any]:
        """
        Resolve an impact alert

        Called when a developer addresses the unresolved impact

        MCP Tool: neo_resolve_impact_alert
        Input: {target_file, resolved_by, resolution_notes}
        Output: {status, resolved_at}
        """
        return self.impact_alerts.resolve_alert(
            target_file=target_file,
            resolved_by=resolved_by,
            resolution_notes=resolution_notes
        )

    def neo_get_impact_summary(self, file_path: str) -> Dict[str, Any]:
        """
        Get human-readable summary of impact alerts

        MCP Tool: neo_get_impact_summary
        Input: {file_path: string}
        Output: {summary: markdown_string}
        """
        summary = self.impact_alerts.get_alert_summary(file_path)
        return {
            "status": "generated",
            "file": file_path,
            "summary": summary,
            "has_alerts": bool(summary)
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
        },
        # Phase 2: Test Triggering
        {
            "name": "neo_trigger_dependent_repo_tests",
            "description": "Trigger tests in dependent repository via CI webhook",
            "input": {
                "type": "object",
                "properties": {
                    "pr_number": {
                        "type": "integer",
                        "description": "PR number that triggered this"
                    },
                    "repo_name": {
                        "type": "string",
                        "description": "Dependent repo name"
                    },
                    "ci_trigger_url": {
                        "type": "string",
                        "description": "Webhook URL for CI trigger"
                    },
                    "changed_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Files changed in parent repo"
                    },
                    "test_command": {
                        "type": "string",
                        "description": "Command to run tests"
                    }
                },
                "required": ["pr_number", "repo_name", "ci_trigger_url", "changed_files", "test_command"]
            }
        },
        {
            "name": "neo_trigger_github_actions",
            "description": "Trigger GitHub Actions workflow in dependent repo",
            "input": {
                "type": "object",
                "properties": {
                    "repo_owner": {
                        "type": "string",
                        "description": "Repository owner"
                    },
                    "repo_name": {
                        "type": "string",
                        "description": "Repository name"
                    },
                    "workflow_file": {
                        "type": "string",
                        "description": "GitHub Actions workflow filename"
                    },
                    "ref": {
                        "type": "string",
                        "description": "Branch/tag to trigger on (default: main)"
                    },
                    "inputs": {
                        "type": "object",
                        "description": "Workflow input parameters"
                    }
                },
                "required": ["repo_owner", "repo_name", "workflow_file"]
            }
        },
        # Phase 3: GitHub PR Auto-Comments
        {
            "name": "neo_post_pr_comment",
            "description": "Post or update comment on PR with dependency status",
            "input": {
                "type": "object",
                "properties": {
                    "owner": {
                        "type": "string",
                        "description": "Repository owner"
                    },
                    "repo": {
                        "type": "string",
                        "description": "Repository name"
                    },
                    "pr_number": {
                        "type": "integer",
                        "description": "PR number"
                    },
                    "comment_body": {
                        "type": "string",
                        "description": "Markdown comment body"
                    }
                },
                "required": ["owner", "repo", "pr_number", "comment_body"]
            }
        },
        {
            "name": "neo_request_pr_review",
            "description": "Request review from specific users on PR",
            "input": {
                "type": "object",
                "properties": {
                    "owner": {
                        "type": "string",
                        "description": "Repository owner"
                    },
                    "repo": {
                        "type": "string",
                        "description": "Repository name"
                    },
                    "pr_number": {
                        "type": "integer",
                        "description": "PR number"
                    },
                    "reviewers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "GitHub usernames to request review from"
                    }
                },
                "required": ["owner", "repo", "pr_number", "reviewers"]
            }
        },
        # Phase 4: Merge Gate
        {
            "name": "neo_check_merge_gate",
            "description": "Check if PR can merge based on dependency test results",
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
            "name": "neo_get_merge_status",
            "description": "Get detailed merge gate status for a PR",
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
            "name": "neo_generate_merge_comment",
            "description": "Generate merge gate status comment for PR",
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
        # Impact Alerts
        {
            "name": "neo_check_impact_alerts",
            "description": "Check for unresolved impact alerts on a file when developer declares intent to edit",
            "input": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "File path to check for impact alerts"
                    }
                },
                "required": ["file_path"]
            }
        },
        {
            "name": "neo_create_impact_alert",
            "description": "Create an impact alert for unresolved dependency impacts",
            "input": {
                "type": "object",
                "properties": {
                    "source_file": {
                        "type": "string",
                        "description": "File that was changed"
                    },
                    "target_file": {
                        "type": "string",
                        "description": "File that is impacted by the change"
                    },
                    "changed_by": {
                        "type": "string",
                        "description": "Developer who made the change"
                    },
                    "change_summary": {
                        "type": "string",
                        "description": "Summary of what changed"
                    },
                    "impact_reason": {
                        "type": "string",
                        "description": "Why this change impacts the target file"
                    },
                    "pr_number": {
                        "type": "integer",
                        "description": "Optional PR number"
                    }
                },
                "required": ["source_file", "target_file", "changed_by", "change_summary", "impact_reason"]
            }
        },
        {
            "name": "neo_resolve_impact_alert",
            "description": "Resolve an impact alert when dependency impact is addressed",
            "input": {
                "type": "object",
                "properties": {
                    "target_file": {
                        "type": "string",
                        "description": "File where impact was resolved"
                    },
                    "resolved_by": {
                        "type": "string",
                        "description": "Developer who resolved the impact"
                    },
                    "resolution_notes": {
                        "type": "string",
                        "description": "Notes about how the impact was resolved"
                    }
                },
                "required": ["target_file", "resolved_by"]
            }
        },
        {
            "name": "neo_get_impact_summary",
            "description": "Get human-readable summary of impact alerts for a file",
            "input": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "File path to get impact summary for"
                    }
                },
                "required": ["file_path"]
            }
        }
    ]
