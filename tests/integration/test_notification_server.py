import os

import pytest

from mcp_servers.notification_server import (
    LOG_FILE,
    send_approval_notice,
    send_manager_alert,
    send_receipt_request,
    send_rejection_notice,
)


@pytest.fixture(autouse=True)
def clean_logs():
    """Removes or clears the notification log file before each test run."""
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)


def test_manager_alert_tool():
    """Verifies that manager alerts are correctly formatted and logged."""
    res = send_manager_alert(
        session_id="session-123",
        title="Excessive Client Dinner",
        amount=150.00,
        risk_level="MEDIUM",
        reasons="Daily meals limit exceeded",
    )
    assert "[Mock Slack Alert sent to #manager-approvals]" in res
    assert "session-123" in res

    # Check log file
    assert os.path.exists(LOG_FILE)
    with open(LOG_FILE, encoding="utf-8") as f:
        logs = f.read()
        assert "Channel: SLACK" in logs
        assert "To: #manager-approvals" in logs
        assert "Compliance Alert: Action Required. Risk Level: MEDIUM" in logs


def test_receipt_request_tool():
    """Verifies that receipt requests are correctly formatted and logged."""
    res = send_receipt_request(
        session_id="session-456",
        title="SaaS License",
        amount=45.00,
        recipient_email="employee@company.com",
    )
    assert "[Mock Email sent to employee@company.com]" in res
    assert "Action Required: Upload Receipt" in res

    # Check log file
    with open(LOG_FILE, encoding="utf-8") as f:
        logs = f.read()
        assert "Channel: EMAIL" in logs
        assert "To: employee@company.com" in logs
        assert "Subject: Action Required: Upload Receipt for Expense Claim" in logs


def test_approval_notice_tool():
    """Verifies that approval notices are correctly formatted and logged."""
    res = send_approval_notice(
        session_id="session-789",
        title="Software Subscription",
        amount=499.00,
        txn_id="TXN-POSTGRES-0001",
        recipient_email="employee@company.com",
    )
    assert "[Mock Email sent to employee@company.com]" in res
    assert "TXN-POSTGRES-0001" in res

    # Check log file
    with open(LOG_FILE, encoding="utf-8") as f:
        logs = f.read()
        assert "Channel: EMAIL" in logs
        assert "Subject: Expense Claim Approved" in logs
        assert "TXN-POSTGRES-0001" in logs


def test_rejection_notice_tool():
    """Verifies that rejection notices are correctly formatted and logged."""
    res = send_rejection_notice(
        session_id="session-999",
        title="Duplicate Flight Ticket",
        amount=600.00,
        reason="Suspected duplicate transaction",
        recipient_email="employee@company.com",
    )
    assert "[Mock Email sent to employee@company.com]" in res
    assert "rejected" in res.lower()

    # Check log file
    with open(LOG_FILE, encoding="utf-8") as f:
        logs = f.read()
        assert "Channel: EMAIL" in logs
        assert "Subject: Expense Claim Rejected" in logs
        assert "Suspected duplicate transaction" in logs
