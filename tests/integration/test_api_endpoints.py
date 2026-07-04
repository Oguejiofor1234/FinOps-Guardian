# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

import psycopg
import pytest
from fastapi.testclient import TestClient

from api.fast_api_app import app


@pytest.fixture(autouse=True)
def clean_database():
    """Cleans the expenses database and session memory before each test run."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        pytest.skip("DATABASE_URL is not set.")

    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE expenses RESTART IDENTITY CASCADE;")
        conn.commit()

    # Clear in-memory session store for test isolation
    if hasattr(app, "state") and hasattr(app.state, "runner") and app.state.runner:
        session_service = app.state.runner.session_service
        if hasattr(session_service, "sessions"):
            session_service.sessions.clear()


def test_api_submit_low_risk_expense() -> None:
    """Verifies that unstructured submission of low-risk claims succeeds end-to-end."""
    with TestClient(app) as client:
        payload = {
            "user_id": "test_api_user",
            "text": "I spent $45.20 on a client lunch at Cafe Oasis on 2026-06-30. The receipt is attached.",
        }

        response = client.post("/expenses/submit", json=payload, headers={"X-User-Role": "employee"})
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["status"] == "completed"
        assert data["state"]["risk_level"] == "LOW"
        assert data["state"]["committed_to_erp"] is True
        assert "Approved" in data["final_output"]


def test_api_submit_missing_receipt_and_hitl_flow() -> None:
    """Verifies that submitting expense with missing receipt pauses, accepts receipt, and decides."""
    with TestClient(app) as client:
        # Step 1: Submit meal claim > $25 without receipt -> Pauses
        submit_payload = {
            "user_id": "test_api_user",
            "text": "Corporate meals expense for $45.00 on 2026-06-30. No receipt.",
        }
        response = client.post("/expenses/submit", json=submit_payload, headers={"X-User-Role": "employee"})
        assert response.status_code == 200
        data = response.json()
        session_id = data["session_id"]
        assert data["status"] == "paused"
        assert data["required_input"] == "manager_decision"
        assert data["state"]["risk_level"] == "MEDIUM"

        # Step 2: Get status
        status_resp = client.get(f"/sessions/{session_id}/status?user_id=test_api_user", headers={"X-User-Role": "employee"})
        assert status_resp.status_code == 200
        assert status_resp.json()["status"] == "paused"

        # Step 3: Manager requests receipt -> Pauses for receipt upload
        decide_payload = {
            "user_id": "test_api_user",
            "decision": "REQUEST_RECEIPT",
            "notes": "Please provide receipt.",
        }
        decide_resp = client.post(f"/sessions/{session_id}/decide", json=decide_payload, headers={"X-User-Role": "manager"})
        assert decide_resp.status_code == 200
        decide_data = decide_resp.json()
        assert decide_data["session_status"] == "paused"
        assert decide_data["required_input"] == "receipt_upload"

        # Step 4: User uploads receipt -> Pauses for final manager decision
        receipt_payload = {
            "user_id": "test_api_user",
            "receipt_path": "/path/to/receipt.jpg",
        }
        receipt_resp = client.post(
            f"/sessions/{session_id}/receipt", json=receipt_payload, headers={"X-User-Role": "employee"}
        )
        assert receipt_resp.status_code == 200
        receipt_data = receipt_resp.json()
        assert receipt_data["session_status"] == "paused"
        assert receipt_data["required_input"] == "manager_decision"

        # Step 5: Manager approves -> Completes
        approve_payload = {
            "user_id": "test_api_user",
            "decision": "APPROVE",
            "notes": "Looks good now.",
        }
        approve_resp = client.post(
            f"/sessions/{session_id}/decide", json=approve_payload, headers={"X-User-Role": "manager"}
        )
        assert approve_resp.status_code == 200
        approve_data = approve_resp.json()
        assert approve_data["session_status"] == "completed"
        assert approve_data["state"]["committed_to_erp"] is True


def test_api_audit_logs_and_metrics() -> None:
    """Verifies that audit logs and dashboard metrics endpoints return valid statistics."""
    with TestClient(app) as client:
        # Submit an expense to populate database
        payload = {
            "user_id": "test_api_user",
            "text": "Standard software license for Github at $350.00 on 2026-06-30. Here is the receipt.",
        }
        client.post("/expenses/submit", json=payload, headers={"X-User-Role": "employee"})

        # 1. Fetch Audit Logs
        logs_resp = client.get("/audit-logs", headers={"X-User-Role": "admin"})
        assert logs_resp.status_code == 200
        logs_data = logs_resp.json()
        assert "logs" in logs_data
        assert len(logs_data["logs"]) > 0
        assert logs_data["logs"][0]["title"] == "Github"
        assert float(logs_data["logs"][0]["amount"]) == 350.0

        # 2. Fetch Metrics
        metrics_resp = client.get("/metrics", headers={"X-User-Role": "admin"})
        assert metrics_resp.status_code == 200
        metrics_data = metrics_resp.json()
        assert metrics_data["approved_count"] == 1
        assert metrics_data["total_approved_amount"] == 350.0
        assert metrics_data["risk_breakdown"]["LOW"] == 1
        assert "software" in metrics_data["category_breakdown"]
