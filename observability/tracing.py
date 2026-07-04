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

import contextvars
import uuid
from collections.abc import Generator
from contextlib import contextmanager

# ContextVars to store active trace and span IDs
_trace_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("trace_id", default=None)
_span_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("span_id", default=None)


def get_current_trace_id() -> str | None:
    """Returns the active trace ID or None."""
    return _trace_id_var.get()


def get_current_span_id() -> str | None:
    """Returns the active span ID or None."""
    return _span_id_var.get()


@contextmanager
def start_trace(trace_id: str | None = None) -> Generator[tuple[str, str], None, None]:
    """
    Context manager to start a new trace context.
    Generates a new trace ID if none is provided, along with a parent span ID.
    """
    t_id = trace_id or f"tr-{uuid.uuid4()}"
    s_id = f"sp-{uuid.uuid4()}"
    
    t_token = _trace_id_var.set(t_id)
    s_token = _span_id_var.set(s_id)
    
    try:
        yield t_id, s_id
    finally:
        _trace_id_var.reset(t_token)
        _span_id_var.reset(s_token)


@contextmanager
def start_span() -> Generator[str, None, None]:
    """Context manager to spawn a child span ID under the current trace."""
    s_id = f"sp-{uuid.uuid4()}"
    s_token = _span_id_var.set(s_id)
    
    try:
        yield s_id
    finally:
        _span_id_var.reset(s_token)
