#!/usr/bin/env python3
"""
Approval Manager - Phase 5 Implementation
Manages approval workflow for multi-developer coordination
Tracks approvals from all associated developers, requires 2-3 minimum to merge
"""

from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum


class ApprovalStatus(Enum):
    """Status of a developer's approval"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"


@dataclass
class DeveloperApproval:
    """Tracks approval status for one developer"""
    developer: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    timestamp: str = ""
    comment: str = ""

    def to_dict(self) -> Dict:
        return {
            "developer": self.developer,
            "status": self.status.value,
            "timestamp": self.timestamp,
            "comment": self.comment
        }


@dataclass
class ApprovalWorkflow:
    """Tracks approval workflow for a file/PR"""
    file: str
    pr_number: int
    all_developers: List[str]
    min_approvals_required: int = 2
    approvals: Dict[str, DeveloperApproval] = field(default_factory=dict)
    created_at: str = ""

    def __post_init__(self):
        """Initialize approval tracking for all developers"""
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

        if not self.approvals:
            for dev in self.all_developers:
                self.approvals[dev] = DeveloperApproval(
                    developer=dev,
                    status=ApprovalStatus.PENDING,
                    timestamp=""
                )

    def get_approval_status(self, developer: str) -> ApprovalStatus:
        """Get approval status for a developer"""
        if developer not in self.approvals:
            raise ValueError(f"Developer {developer} not in approval workflow")
        return self.approvals[developer].status

    def record_approval(self, developer: str, approved: bool, comment: str = "") -> bool:
        """Record developer's approval decision"""
        if developer not in self.approvals:
            raise ValueError(f"Developer {developer} not in approval workflow")

        self.approvals[developer].status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        self.approvals[developer].timestamp = datetime.now().isoformat()
        self.approvals[developer].comment = comment

        return self.is_approved()

    def record_changes_requested(self, developer: str, comment: str = "") -> None:
        """Record that developer has requested changes"""
        if developer not in self.approvals:
            raise ValueError(f"Developer {developer} not in approval workflow")

        self.approvals[developer].status = ApprovalStatus.CHANGES_REQUESTED
        self.approvals[developer].timestamp = datetime.now().isoformat()
        self.approvals[developer].comment = comment

    def is_approved(self) -> bool:
        """Check if workflow has enough approvals to merge"""
        approved_count = sum(
            1 for approval in self.approvals.values()
            if approval.status == ApprovalStatus.APPROVED
        )
        return approved_count >= self.min_approvals_required

    def has_rejections(self) -> bool:
        """Check if any developer rejected"""
        return any(
            approval.status == ApprovalStatus.REJECTED
            for approval in self.approvals.values()
        )

    def has_changes_requested(self) -> bool:
        """Check if any developer requested changes"""
        return any(
            approval.status == ApprovalStatus.CHANGES_REQUESTED
            for approval in self.approvals.values()
        )

    def can_merge(self) -> bool:
        """Check if PR is ready to merge (approved + no rejections + no changes requested)"""
        return self.is_approved() and not self.has_rejections() and not self.has_changes_requested()

    def get_summary(self) -> Dict:
        """Get summary of approval status"""
        approved = sum(
            1 for a in self.approvals.values()
            if a.status == ApprovalStatus.APPROVED
        )
        rejected = sum(
            1 for a in self.approvals.values()
            if a.status == ApprovalStatus.REJECTED
        )
        changes_requested = sum(
            1 for a in self.approvals.values()
            if a.status == ApprovalStatus.CHANGES_REQUESTED
        )
        pending = sum(
            1 for a in self.approvals.values()
            if a.status == ApprovalStatus.PENDING
        )

        return {
            "file": self.file,
            "pr_number": self.pr_number,
            "total_developers": len(self.all_developers),
            "min_approvals_required": self.min_approvals_required,
            "approved": approved,
            "rejected": rejected,
            "changes_requested": changes_requested,
            "pending": pending,
            "is_approved": self.is_approved(),
            "can_merge": self.can_merge(),
            "approvals": {dev: approval.to_dict() for dev, approval in self.approvals.items()}
        }


class ApprovalManager:
    """Manages approval workflows for all files"""

    def __init__(self):
        self.workflows: Dict[str, ApprovalWorkflow] = {}  # pr_id -> workflow
        self.pr_counter = 0

    def create_approval_workflow(self, file: str, all_developers: List[str],
                                min_approvals: int = 2) -> ApprovalWorkflow:
        """Create approval workflow when PR is raised"""
        self.pr_counter += 1
        pr_number = self.pr_counter

        workflow = ApprovalWorkflow(
            file=file,
            pr_number=pr_number,
            all_developers=all_developers,
            min_approvals_required=min_approvals
        )

        self.workflows[pr_number] = workflow
        return workflow

    def get_workflow(self, pr_number: int) -> ApprovalWorkflow:
        """Get approval workflow for a PR"""
        if pr_number not in self.workflows:
            raise ValueError(f"No workflow for PR #{pr_number}")
        return self.workflows[pr_number]

    def record_approval(self, pr_number: int, developer: str, approved: bool,
                       comment: str = "") -> bool:
        """Record a developer's approval"""
        workflow = self.get_workflow(pr_number)
        return workflow.record_approval(developer, approved, comment)

    def record_changes_requested(self, pr_number: int, developer: str,
                                comment: str = "") -> None:
        """Record that developer requested changes"""
        workflow = self.get_workflow(pr_number)
        workflow.record_changes_requested(developer, comment)

    def can_merge(self, pr_number: int) -> bool:
        """Check if PR is ready to merge"""
        workflow = self.get_workflow(pr_number)
        return workflow.can_merge()

    def get_summary(self, pr_number: int) -> Dict:
        """Get approval summary for a PR"""
        workflow = self.get_workflow(pr_number)
        return workflow.get_summary()
