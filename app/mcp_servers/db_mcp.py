from typing import Any


class LedgerMCP:
    """Mock Model Context Protocol (MCP) server for PostgreSQL ledger integration."""

    def __init__(self):
        self.ledger_db = []

    def commit_transaction(self, claim_data: dict[str, Any]) -> str:
        """Writes the audited and tax-mapped expense claim into the ERP PostgreSQL ledger."""
        # Mocking db insert logic
        transaction_id = f"TXN-POSTGRES-{len(self.ledger_db) + 1:04d}"
        record = {"transaction_id": transaction_id, **claim_data}
        self.ledger_db.append(record)
        return f"Successfully committed transaction {transaction_id} to PostgreSQL database."


class NotificationMCP:
    """Mock Model Context Protocol (MCP) server for alerting systems (Slack, Email)."""

    def send_slack_alert(self, channel: str, message: str) -> str:
        """Sends a notification to a specific Slack channel."""
        # Mocking slack API send
        return f"[Slack Notification sent to #{channel}]: {message}"

    def send_email_alert(self, recipient: str, subject: str, body: str) -> str:
        """Sends an email alert to manager/reviewer."""
        # Mocking SMTP send
        return f"[Email sent to {recipient}] Subject: {subject}"
