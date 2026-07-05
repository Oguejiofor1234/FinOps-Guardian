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

import time
from collections import defaultdict
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

# Simple in-memory rate limiter: tracks timestamps of requests per IP
RATE_LIMIT_WINDOW_SEC = 60
MAX_REQUESTS_PER_WINDOW = 1000

REQUEST_HISTORY = defaultdict(list)


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Protects endpoints against brute force and DDoS using client IP rate limiting."""

    def __init__(self, app) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip rate limiting for static assets and favicon to save quota
        path = request.url.path
        if path.startswith("/static/") or path == "/favicon.ico":
            return await call_next(request)

        # Resolve real client IP behind proxy (e.g. Cloud Run GFE)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
            
        now = time.time()
        
        # Filter request history to current window
        history = REQUEST_HISTORY[client_ip]
        history = [t for t in history if now - t < RATE_LIMIT_WINDOW_SEC]
        REQUEST_HISTORY[client_ip] = history
        
        if len(history) >= MAX_REQUESTS_PER_WINDOW:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many requests. Rate limit exceeded."}
            )
            
        REQUEST_HISTORY[client_ip].append(now)
        return await call_next(request)



class ContentSanitizationMiddleware(BaseHTTPMiddleware):
    """Scans incoming request payloads for malicious scripts (XSS prevention)."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Check for scripting injections in query params
        for value in request.query_params.values():
            if "<script" in value.lower() or "javascript:" in value.lower():
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Malicious payload detected: Script tags are prohibited."}
                )
                
        # Check body for script tags if request is JSON
        if request.headers.get("content-type") == "application/json":
            try:
                # Read body while keeping it available for subsequent route handlers
                body_bytes = await request.body()
                body_str = body_bytes.decode("utf-8", errors="ignore")
                
                # Check for XSS signatures
                if "<script" in body_str.lower() or "javascript:" in body_str.lower():
                    return JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content={"detail": "Malicious payload detected: Script tags are prohibited."}
                    )
            except Exception:
                pass
                
        return await call_next(request)


def verify_env_security() -> None:
    """Verifies that sensitive environmental variables do not contain default weak configurations."""
    import os
    db_url = os.getenv("DATABASE_URL")
    if db_url and "password" in db_url.lower() and "admin" in db_url.lower():
        raise ValueError("Security Violation: Database URL uses weak admin password defaults.")
