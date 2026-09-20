#!/usr/bin/env python3
"""
Notification Manager - Handles notifications for workflow state changes
Supports: Webhooks, Email, Slack, and in-app polling
"""

import json
import requests
from typing import Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum


class NotificationType(Enum):
    """Types of notifications"""
    LOCK_ACQUIRED = "lock_acquired"
    LOCK_BLOCKED = "lock_blocked"
    LOCK_RELEASED = "lock_released"
    REVIEW_REQUESTED = "review_requested"
    APPROVAL_NEEDED = "approval_needed"
    APPROVED = "approved"
    READY_TO_MERGE = "ready_to_merge"
    MERGED = "merged"
    ROLLBACK = "rollback"


class NotificationChannel(Enum):
    """Notification delivery channels"""
    WEBHOOK = "webhook"
    EMAIL = "email"
    SLACK = "slack"
    POLLING = "polling"  # Developer polls for updates


class NotificationManager:
    """Manages notifications across multiple channels"""

    def __init__(self):
        self.subscriptions: Dict[str, List[Dict]] = {}  # developer -> [channels]
        self.notification_queue = []
        self.notification_history = []

    def subscribe(
        self,
        developer: str,
        channel: NotificationChannel,
        endpoint: str,
        notify_on: Optional[List[NotificationType]] = None,
    ) -> Dict:
        """
        Developer subscribes to notifications

        Args:
            developer: Developer username/ID
            channel: Notification channel (webhook, email, slack)
            endpoint: URL/email/slack-webhook for delivery
            notify_on: List of notification types to receive (None = all)
        """
        if developer not in self.subscriptions:
            self.subscriptions[developer] = []

        subscription = {
            "developer": developer,
            "channel": channel.value,
            "endpoint": endpoint,
            "notify_on": [n.value for n in (notify_on or [])] or "all",
            "created_at": datetime.now().isoformat(),
            "active": True,
        }

        self.subscriptions[developer].append(subscription)

        return {
            "success": True,
            "message": f"{developer} subscribed to {channel.value}",
            "subscription": subscription,
        }

    def unsubscribe(self, developer: str, channel: NotificationChannel) -> Dict:
        """Unsubscribe from notifications"""
        if developer in self.subscriptions:
            self.subscriptions[developer] = [
                s for s in self.subscriptions[developer] if s["channel"] != channel.value
            ]

        return {"success": True, "message": f"{developer} unsubscribed from {channel.value}"}

    def notify(
        self,
        developer: str,
        notification_type: NotificationType,
        data: Dict,
        file_path: str = None,
        function_name: str = None,
    ) -> Dict:
        """
        Send notification to developer(s)

        Args:
            developer: Target developer (or "all" for broadcast)
            notification_type: Type of notification
            data: Notification payload
            file_path: Code file involved
            function_name: Function involved
        """
        notification = {
            "id": datetime.now().isoformat(),
            "type": notification_type.value,
            "developer": developer,
            "file": file_path,
            "function": function_name,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }

        self.notification_queue.append(notification)
        self.notification_history.append(notification)

        # Get target developers
        targets = (
            list(self.subscriptions.keys())
            if developer == "all"
            else [developer]
        )

        results = {"success": True, "delivered": [], "failed": []}

        for target in targets:
            if target not in self.subscriptions:
                continue

            for subscription in self.subscriptions[target]:
                # Check if this subscription handles this notification type
                if (
                    subscription["notify_on"] != "all"
                    and notification_type.value not in subscription["notify_on"]
                ):
                    continue

                try:
                    if subscription["channel"] == NotificationChannel.WEBHOOK.value:
                        self._send_webhook(subscription["endpoint"], notification)
                        results["delivered"].append((target, "webhook"))
                    elif subscription["channel"] == NotificationChannel.EMAIL.value:
                        self._send_email(subscription["endpoint"], notification)
                        results["delivered"].append((target, "email"))
                    elif subscription["channel"] == NotificationChannel.SLACK.value:
                        self._send_slack(subscription["endpoint"], notification)
                        results["delivered"].append((target, "slack"))
                    # POLLING channel doesn't "send" - developer polls later

                except Exception as e:
                    results["failed"].append((target, str(e)))

        return results

    def get_notifications(self, developer: str, since: Optional[str] = None) -> List[Dict]:
        """
        Poll for notifications (used by developers polling for updates)

        Args:
            developer: Developer requesting notifications
            since: ISO timestamp - only return notifications after this
        """
        notifications = []

        for notif in self.notification_history:
            if notif["developer"] == developer or notif["developer"] == "all":
                if since is None or notif["timestamp"] > since:
                    notifications.append(notif)

        return notifications

    def mark_as_read(self, notification_id: str) -> Dict:
        """Mark notification as read (for polling)"""
        for notif in self.notification_history:
            if notif["id"] == notification_id:
                notif["read"] = True
                return {"success": True}

        return {"success": False, "error": "Notification not found"}

    def _send_webhook(self, endpoint: str, notification: Dict):
        """Send webhook notification"""
        try:
            payload = {
                "notification_type": notification["type"],
                "developer": notification["developer"],
                "file": notification["file"],
                "function": notification["function"],
                "data": notification["data"],
                "timestamp": notification["timestamp"],
            }

            response = requests.post(
                endpoint, json=payload, timeout=5, headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
        except Exception as e:
            raise Exception(f"Webhook failed: {e}")

    def _send_email(self, email: str, notification: Dict):
        """Send email notification"""
        # Stub for email implementation
        # In production, use sendgrid, aws-ses, etc.
        subject = f"Neo Activity: {notification['type']}"
        body = f"""
Notification Type: {notification['type']}
File: {notification['file']}
Function: {notification['function']}
Time: {notification['timestamp']}

Details:
{json.dumps(notification['data'], indent=2)}
"""
        # print(f"📧 Email to {email}: {subject}")
        # In real implementation: send_email(email, subject, body)

    def _send_slack(self, webhook_url: str, notification: Dict):
        """Send Slack notification"""
        try:
            message = {
                "text": f"*{notification['type'].upper()}*",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*{notification['type'].upper()}*\n"
                            f"Developer: {notification['developer']}\n"
                            f"File: `{notification['file']}`\n"
                            f"Function: `{notification['function']}`",
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"```{json.dumps(notification['data'], indent=2)}```",
                        },
                    },
                ],
            }

            response = requests.post(webhook_url, json=message, timeout=5)
            response.raise_for_status()
        except Exception as e:
            raise Exception(f"Slack failed: {e}")

    def get_stats(self) -> Dict:
        """Get notification stats"""
        return {
            "total_subscriptions": sum(len(subs) for subs in self.subscriptions.values()),
            "active_developers": len(self.subscriptions),
            "total_notifications_sent": len(self.notification_history),
            "notification_types": list(set(n["type"] for n in self.notification_history)),
            "channels": list(
                set(
                    sub["channel"]
                    for subs in self.subscriptions.values()
                    for sub in subs
                )
            ),
        }

    def get_subscription_info(self, developer: str) -> Dict:
        """Get subscription info for developer"""
        if developer not in self.subscriptions:
            return {"developer": developer, "subscriptions": [], "message": "No subscriptions"}

        return {
            "developer": developer,
            "subscriptions": self.subscriptions[developer],
            "notification_count": len(self.notification_history),
        }
