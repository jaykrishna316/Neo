#!/usr/bin/env python3
"""
Invoice Service - Generate and manage invoices

Depends on payment-service for transaction data.
Vulnerable to downstream breaking changes.
"""

from typing import Dict, Optional, List
from datetime import datetime
import sys
from pathlib import Path

# Add payment-service to path
sys.path.insert(0, str(Path(__file__).parent.parent / "payment-service"))

try:
    from payment_service import get_payment_service
except ImportError:
    get_payment_service = None


class InvoiceService:
    """Invoice generation and management"""

    def __init__(self):
        self.invoices = {}
        self.templates = {}

    def generate_invoice(self, transaction_id: str) -> Optional[Dict]:
        """
        Generate invoice from payment transaction.

        DEPENDS ON: payment-service.get_payment_service()

        This service depends on payment-service which depends on auth-service.
        If auth-service breaking change breaks payment-service,
        this function will fail!

        Args:
            transaction_id: Transaction to invoice

        Returns:
            Invoice data
        """
        if get_payment_service is None:
            return None

        payment_service = get_payment_service()
        transaction = payment_service.get_transaction(transaction_id)

        if transaction is None:
            return None

        # Generate invoice
        invoice_id = f"INV-{len(self.invoices) + 1}"

        invoice = {
            "invoice_id": invoice_id,
            "transaction_id": transaction_id,
            "username": transaction["username"],
            "amount": transaction["amount"],
            "currency": transaction["currency"],
            "status": "sent",
            "generated_at": datetime.utcnow().isoformat(),
            "due_date": "30 days from now"
        }

        self.invoices[invoice_id] = invoice
        return invoice

    def format_invoice_html(self, invoice_id: str) -> Optional[str]:
        """
        Format invoice as HTML for email.

        Args:
            invoice_id: Invoice to format

        Returns:
            HTML representation
        """
        invoice = self.invoices.get(invoice_id)

        if invoice is None:
            return None

        html = f"""
        <html>
            <body>
                <h1>Invoice {invoice['invoice_id']}</h1>
                <p>Transaction: {invoice['transaction_id']}</p>
                <p>Customer: {invoice['username']}</p>
                <p>Amount: {invoice['amount']} {invoice['currency']}</p>
                <p>Generated: {invoice['generated_at']}</p>
                <p>Due Date: {invoice['due_date']}</p>
            </body>
        </html>
        """

        return html

    def get_invoices_for_user(self, username: str) -> List[Dict]:
        """Get all invoices for a user"""
        return [
            inv for inv in self.invoices.values()
            if inv["username"] == username
        ]

    def mark_invoice_sent(self, invoice_id: str) -> bool:
        """Mark invoice as sent"""
        if invoice_id in self.invoices:
            self.invoices[invoice_id]["status"] = "sent"
            return True
        return False


# Global service instance
_invoice_service = InvoiceService()


def get_invoice_service() -> InvoiceService:
    """Get global invoice service instance"""
    return _invoice_service


def generate_invoice(transaction_id: str) -> Optional[Dict]:
    """Convenience function to generate invoice"""
    return _invoice_service.generate_invoice(transaction_id)
