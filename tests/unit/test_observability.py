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

import json
import logging
import os
import pytest

from observability.logger import StructuredJsonFormatter, scrub_pii
from observability.tracing import start_trace, get_current_trace_id
from observability.audit_logger import log_audit_event, AUDIT_LOG_FILE
from observability.metrics import TelemetryMetrics


def test_pii_scrubbing() -> None:
    """Verifies that credit cards and SSNs are masked correctly."""
    cc_msg = "Card number 4111-2222-3333-4444 should not be logged."
    ssn_msg = "SSN number 999-12-3456 is private."
    
    assert "4111" not in scrub_pii(cc_msg)
    assert "[REDACTED_CC]" in scrub_pii(cc_msg)
    
    assert "999-12" not in scrub_pii(ssn_msg)
    assert "[REDACTED_SSN]" in scrub_pii(ssn_msg)


def test_structured_json_logger() -> None:
    """Verifies that the structured JSON logger formats messages and includes trace IDs."""
    formatter = StructuredJsonFormatter()
    
    with start_trace("test-trace-123") as (trace_id, span_id):
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test_file.py",
            lineno=42,
            msg="Purchase Uber for 4111 2222 3333 4444",
            args=(),
            exc_info=None,
        )
        # Attach extra data
        record.extra_data = {"credit_card": "4111-2222-3333-4444", "user": "alice"}
        
        formatted_str = formatter.format(record)
        log_json = json.loads(formatted_str)
        
        # Verify JSON properties
        assert log_json["level"] == "INFO"
        assert log_json["trace_id"] == "test-trace-123"
        assert "4111" not in log_json["message"]
        assert "[REDACTED_CC]" in log_json["message"]
        assert "4111" not in log_json["extra"]["credit_card"]
        assert log_json["extra"]["user"] == "alice"


def test_tracing_context_propagation() -> None:
    """Verifies start_trace propagates trace context properly."""
    assert get_current_trace_id() is None
    
    with start_trace("custom-trace-id"):
        assert get_current_trace_id() == "custom-trace-id"
        
    assert get_current_trace_id() is None


def test_audit_logger_redaction() -> None:
    """Verifies that audit logging scrubs PII and writes JSON lines successfully."""
    # Ensure fresh file
    if os.path.exists(AUDIT_LOG_FILE):
        os.remove(AUDIT_LOG_FILE)
        
    with start_trace("audit-trace-456"):
        log_audit_event(
            event_type="LEDGER_COMMIT",
            actor="analyst_agent",
            status="SUCCESS",
            details={"card": "4111-2222-3333-4444", "amount": 120.50}
        )
        
    assert os.path.exists(AUDIT_LOG_FILE)
    
    with open(AUDIT_LOG_FILE, "r") as f:
        lines = f.readlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        
        assert entry["event_type"] == "LEDGER_COMMIT"
        assert entry["trace_id"] == "audit-trace-456"
        assert "4111" not in entry["details"]["card"]
        assert entry["details"]["card"] == "[REDACTED_CC]"
        assert entry["details"]["amount"] == 120.50

    # Cleanup
    os.remove(AUDIT_LOG_FILE)


def test_telemetry_metrics_and_cost() -> None:
    """Verifies metric counting and token pricing logic."""
    metrics = TelemetryMetrics()
    
    metrics.increment_claims(risk_level="HIGH", status="completed")
    metrics.increment_claims(risk_level="MEDIUM", status="paused")
    
    # Verify risk/status breakdowns
    snapshot = metrics.get_snapshot()
    assert snapshot["total_claims"] == 2
    assert snapshot["risk_counts"]["HIGH"] == 1
    assert snapshot["risk_counts"]["MEDIUM"] == 1
    assert snapshot["risk_counts"]["LOW"] == 0
    assert snapshot["status_counts"]["completed"] == 1
    assert snapshot["status_counts"]["paused"] == 1

    # Record 1M input tokens & 500k output tokens
    metrics.record_token_usage(input_tokens=1000000, output_tokens=500000)
    
    # Expected cost = 1.0 * $0.075 + 0.5 * $0.30 = $0.075 + $0.15 = $0.225
    snapshot = metrics.get_snapshot()
    assert abs(snapshot["total_cost_usd"] - 0.225) < 0.0001
