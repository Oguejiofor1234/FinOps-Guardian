# Notification MCP Server Design Report

This report summarizes the design, mock implementation, notification logging, and integration testing of the **Notification Model Context Protocol (MCP) Server** for **FinOps Guardian**.

---

## 1. Notification Tools & Templates (`mcp_servers/notification_server.py`)

Using the Anthropic Python MCP `FastMCP` framework, the notification server exposes mock communication channels tailored for compliance events:

1. **`send_manager_alert`**: Dispatches compliance warnings to Slack (e.g. `#manager-approvals`) for transactions requiring manager review.
2. **`send_receipt_request`**: Dispatches email alerts to employees when a claim requires a missing receipt.
3. **`send_approval_notice`**: Dispatches email success alerts containing the committed ERP Transaction ID.
4. **`send_rejection_notice`**: Dispatches email rejection alerts detailing the specific policy violation reasons.

---

## 2. Notification Logging (`notification_logs.txt`)

To record all notification dispatches during demo simulations and tests, every tool call writes a structured, timestamped log line to `notification_logs.txt` in the workspace root:

```text
[2026-07-02T18:14:36.216892] Channel: EMAIL | To: employee@company.com | Subject: Expense Claim Approved | Message: Good news! Your expense claim 'Meals' ($45.00) has been approved and committed under Transaction ID TXN-POSTGRES-0006.
```

---

## 3. Workflow Integration

We updated the compliance agent flow nodes to consume these notification tools:
- **`run_approval`**: Sends a manager alert on initialization (Slack) and a receipt request (Email) if missing receipts are flagged.
- **`handle_rejection`**: Sends a rejection email alert explaining policy violations.
- **`send_notifications`**: Sends an approval email alert containing the real PostgreSQL committed transaction ID.

---

## 4. Integration Verification

- **Isolated Tests (`tests/integration/test_notification_server.py`)**: Tests formatting and verify log assertions for Slack alerts, receipt requests, approval notifications, and rejection messages.
- **Test Status**: All 52 tests are passing cleanly.
