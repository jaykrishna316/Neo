#!/usr/bin/env python3
"""
Notification Service - Send emails and notifications

Depends on invoice-service for invoice data.
Downstream in the dependency chain.
"""

from typing import Dict, Optional, List
from datetime import datetime
import sys
from pathlib import Path

# Add invoice-service to path
sys.path.insert(0, str(Path(__file__).parent.parent / "invoice-service"))

try:
    from invoice_service import get_invoice_service
except ImportError:
    get_invoice_service = None


class NotificationService:
    """Email and notification management"""

    def __init__(self):
        self.sent_emails = {}
        self.email_queue = []

    def send_invoice_email(
        self,
        username: str,
        invoice_id: str,
        recipient_email: str
    ) -> Dict:
        """
        Send invoice via email.

        DEPENDS ON: invoice-service.generate_invoice()

        This is the deepest downstream service.
        If breaking changes cascade from auth → payment → invoice → notification,
        this function will fail!

        Args:
            username: User to send to
            invoice_id: Invoice to email
            recipient_email: Email address

        Returns:
            Email send result
        """
        if get_invoice_service is None:
            return {
                "success": False,
                "error": "Invoice service unavailable"
            }

        invoice_service = get_invoice_service()
        invoice = invoice_service.invoices.get(invoice_id)

        if invoice is None:
            return {
                "success": False,
                "error": "Invoice not found"
            }

        # Format and send email
        html_content = invoice_service.format_invoice_html(invoice_id)

        email_id = f"EMAIL-{len(self.sent_emails) + 1}"
        self.sent_emails[email_id] = {
            "email_id": email_id,
            "recipient": recipient_email,
            "invoice_id": invoice_id,
            "username": username,
            "subject": f"Invoice {invoice_id} for {invoice['amount']} {invoice['currency']}",
            "status": "sent",
            "sent_at": datetime.utcnow().isoformat(),
            "html_content": html_content
        }

        # Queue for delivery (simplified)
        self.email_queue.append(email_id)

        return {
            "success": True,
            "email_id": email_id,
            "recipient": recipient_email,
            "invoice_id": invoice_id,
            "status": "sent",
            "timestamp": datetime.utcnow().isoformat()
        }

    def log_event(self, event_type: str, message: str, metadata: Optional[Dict] = None) -> Dict:
        """
        Log system event.

        Args:
            event_type: Type of event
            message: Event message
            metadata: Additional metadata

        Returns:
            Log entry
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": event_type,
            "message": message,
            "metadata": metadata or {}
        }

        return log_entry

    def get_email_status(self, email_id: str) -> Optional[Dict]:
        """Get email status"""
        return self.sent_emails.get(email_id)

    def get_all_emails(self) -> Dict:
        """Get all sent emails"""
        return self.sent_emails


# Global service instance
_notification_service = NotificationService()


def get_notification_service() -> NotificationService:
    """Get global notification service instance"""
    return _notification_service


def send_invoice_email(username: str, invoice_id: str, recipient_email: str) -> Dict:
    """Convenience function to send invoice email"""
    return _notification_service.send_invoice_email(username, invoice_id, recipient_email)
