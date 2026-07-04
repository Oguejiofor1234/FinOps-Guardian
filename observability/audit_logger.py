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
import os
from datetime import datetime, timezone
from typing import Any

from observability.logger import scrub_pii
from observability.tracing import get_current_trace_id

AUDIT_LOG_FILE = "audit_trail.jsonl"


def log_audit_event(event_type: str, actor: str, status: str, details: dict[str, Any] | None = None) -> None:
    """
    Appends a structured audit event to the audit_trail.jsonl log file.
    Automatically scrubs PII from the details.
    """
    trace_id = get_current_trace_id() or "no-trace"
    
    # Scrub details of PII
    scrubbed_details = {}
    if details:
        for k, v in details.items():
            if isinstance(v, str):
                scrubbed_details[k] = scrub_pii(v)
            else:
                scrubbed_details[k] = v

    audit_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "actor": actor,
        "status": status,
        "trace_id": trace_id,
        "details": scrubbed_details,
    }
    
    # Write JSON Line to file
    try:
        with open(AUDIT_LOG_FILE, "a") as f:
            f.write(json.dumps(audit_entry) + "\n")
    except Exception as e:
        # Fallback to stdout to prevent halting execution
        print(f"Failed to write to audit log: {e}")
