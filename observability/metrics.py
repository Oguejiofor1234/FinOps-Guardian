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

import threading
from typing import Any

# Pricing parameters for Gemini model
INPUT_TOKEN_PRICE_PER_M = 0.075  # $0.075 per 1M input tokens
OUTPUT_TOKEN_PRICE_PER_M = 0.30  # $0.30 per 1M output tokens

class TelemetryMetrics:
    """Thread-safe storage for application monitoring telemetry and cost tracking."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.total_claims = 0
        self.risk_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
        self.status_counts = {"completed": 0, "paused": 0, "rejected": 0}
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_cost_usd = 0.0

    def increment_claims(self, risk_level: str, status: str) -> None:
        """Increments processed claims count by risk and execution status."""
        with self._lock:
            self.total_claims += 1
            risk_upper = risk_level.upper()
            if risk_upper in self.risk_counts:
                self.risk_counts[risk_upper] += 1
            if status in self.status_counts:
                self.status_counts[status] += 1

    def record_token_usage(self, input_tokens: int, output_tokens: int) -> None:
        """Records model input/output token usage and calculates cost in USD."""
        with self._lock:
            self.input_tokens += input_tokens
            self.output_tokens += output_tokens
            
            # Compute cost
            in_cost = (input_tokens * INPUT_TOKEN_PRICE_PER_M) / 1000000.0
            out_cost = (output_tokens * OUTPUT_TOKEN_PRICE_PER_M) / 1000000.0
            self.total_cost_usd += (in_cost + out_cost)

    def get_snapshot(self) -> dict[str, Any]:
        """Returns a snapshot of the current metrics."""
        with self._lock:
            return {
                "total_claims": self.total_claims,
                "risk_counts": dict(self.risk_counts),
                "status_counts": dict(self.status_counts),
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "total_cost_usd": self.total_cost_usd,
            }


# Process-wide metrics instance
_metrics_instance = TelemetryMetrics()


def get_metrics() -> dict[str, Any]:
    """Returns a copy of the current metrics snapshot."""
    return _metrics_instance.get_snapshot()


def record_claim(risk_level: str, status: str) -> None:
    """Tracks a newly evaluated claim transaction."""
    _metrics_instance.increment_claims(risk_level, status)


def record_tokens(input_tokens: int, output_tokens: int) -> None:
    """Tracks LLM token usage."""
    _metrics_instance.record_token_usage(input_tokens, output_tokens)
