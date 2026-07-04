import os
from datetime import datetime

from mcp.server.fastmcp import FastMCP

# Initialize FastMCP Server
mcp = FastMCP("notification_server")

# Path to the notification log file in the workspace
LOG_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "notification_logs.txt"
)


def log_notification(channel: str, recipient: str, subject: str, message: str) -> None:
    """Helper to log simulated Slack/Email notifications to a workspace text file."""
    timestamp = datetime.now().isoformat()
    log_entry = (
        f"[{timestamp}] Channel: {channel} | To: {recipient} | "
        f"Subject: {subject} | Message: {message}\n"
    )
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry)


@mcp.tool()
def send_manager_alert(
    session_id: str,
    title: str,
    amount: float,
    risk_level: str,
    reasons: str,
    channel: str = "#manager-approvals",
) -> str:
    """
    Sends a mock Slack notification to the finance/manager channel
    notifying them that an expense claim is pending manual review.
    """
    message = (
        f"Compliance Alert: Action Required. Risk Level: {risk_level}. "
        f"Claim: '{title}' (${amount:.2f}). Reasons: {reasons}. "
        f"Session: {session_id}"
    )
    log_notification(
        channel="SLACK",
        recipient=channel,
        subject="Pending Compliance Review",
        message=message,
    )
    return f"[Mock Slack Alert sent to {channel}]: {message}"


@mcp.tool()
def send_receipt_request(
    session_id: str, title: str, amount: float, recipient_email: str
) -> str:
    """
    Sends a mock Email notification to the employee requesting they
    upload a missing receipt for their claim.
    """
    subject = "Action Required: Upload Receipt for Expense Claim"
    message = (
        f"Your expense claim '{title}' (${amount:.2f}) requires a receipt. "
        f"Please upload it via your dashboard to complete validation. "
        f"Session: {session_id}"
    )
    log_notification(
        channel="EMAIL", recipient=recipient_email, subject=subject, message=message
    )
    return f"[Mock Email sent to {recipient_email}]: Subject: {subject} | Message: {message}"


@mcp.tool()
def send_approval_notice(
    session_id: str, title: str, amount: float, txn_id: str, recipient_email: str
) -> str:
    """
    Sends a mock Email notification to the employee informing them
    that their claim has been approved and committed to the ERP system.
    """
    subject = "Expense Claim Approved"
    message = (
        f"Good news! Your expense claim '{title}' (${amount:.2f}) has been approved "
        f"and committed to the ERP system under Transaction ID {txn_id}. "
        f"Session: {session_id}"
    )
    log_notification(
        channel="EMAIL", recipient=recipient_email, subject=subject, message=message
    )
    return f"[Mock Email sent to {recipient_email}]: Subject: {subject} | Message: {message}"


@mcp.tool()
def send_rejection_notice(
    session_id: str, title: str, amount: float, reason: str, recipient_email: str
) -> str:
    """
    Sends a mock Email notification to the employee informing them
    that their claim has been rejected.
    """
    subject = "Expense Claim Rejected"
    message = (
        f"We regret to inform you that your expense claim '{title}' (${amount:.2f}) "
        f"was rejected. Reason: {reason}. "
        f"Session: {session_id}"
    )
    log_notification(
        channel="EMAIL", recipient=recipient_email, subject=subject, message=message
    )
    return f"[Mock Email sent to {recipient_email}]: Subject: {subject} | Message: {message}"


if __name__ == "__main__":
    mcp.run()
