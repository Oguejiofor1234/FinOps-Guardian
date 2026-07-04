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
import re
import sys
from typing import Any

from observability.tracing import get_current_trace_id

# Regex for scrubbing Credit Cards and SSNs
CC_REGEX = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
SSN_REGEX = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


def scrub_pii(text: str) -> str:
    """Scrubs Credit Cards and SSNs from string messages."""
    if not isinstance(text, str):
        return text
    text = CC_REGEX.sub("[REDACTED_CC]", text)
    text = SSN_REGEX.sub("[REDACTED_SSN]", text)
    return text


class StructuredJsonFormatter(logging.Formatter):
    """Formats logs in structured JSON format with Trace IDs and PII scrubbing."""

    def format(self, record: logging.LogRecord) -> str:
        # Resolve trace ID from context
        trace_id = get_current_trace_id() or "no-trace"
        
        # Scrub message
        message = record.getMessage()
        message = scrub_pii(message)
        
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": message,
            "trace_id": trace_id,
            "filename": record.filename,
            "line_number": record.lineno,
        }
        
        # Handle extra parameters passed to logger
        if hasattr(record, "extra_data"):
            extra = getattr(record, "extra_data")
            if isinstance(extra, dict):
                # Scrub PII in dict extra values
                scrubbed_extra = {}
                for k, v in extra.items():
                    if isinstance(v, str):
                        scrubbed_extra[k] = scrub_pii(v)
                    else:
                        scrubbed_extra[k] = v
                log_data["extra"] = scrubbed_extra
                
        return json.dumps(log_data)


def get_logger(name: str) -> logging.Logger:
    """Initializes and returns a structured JSON logger."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    
    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = StructuredJsonFormatter()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    return logger
