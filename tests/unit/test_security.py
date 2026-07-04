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

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.fast_api_app import app
from security.rbac import require_role, ROLE_EMPLOYEE, ROLE_MANAGER, ROLE_ADMIN
from security.middleware import verify_env_security


def test_rbac_require_role_dependency() -> None:
    """Tests require_role dependency logic directly."""
    employee_checker = require_role([ROLE_EMPLOYEE])
    manager_checker = require_role([ROLE_MANAGER, ROLE_ADMIN])
    
    # 1. Valid role matches
    assert employee_checker("employee") == "employee"
    assert manager_checker("manager") == "manager"
    assert manager_checker("admin") == "admin"
    
    # 2. Unauthorized roles raise HTTP 403
    with pytest.raises(HTTPException) as exc:
        employee_checker("manager")
    assert exc.value.status_code == 403
    
    with pytest.raises(HTTPException) as exc:
        manager_checker("employee")
    assert exc.value.status_code == 403
    
    # 3. Invalid role types raise HTTP 401
    with pytest.raises(HTTPException) as exc:
        employee_checker("guest")
    assert exc.value.status_code == 401


def test_api_rbac_enforcement() -> None:
    """Verifies RBAC rules are enforced at Fast API endpoints using headers."""
    with TestClient(app) as client:
        # 1. Accessing audit logs without headers defaults to employee -> 403 Forbidden
        resp = client.get("/audit-logs")
        assert resp.status_code == 403
        
        # 2. Accessing audit logs with employee header -> 403 Forbidden
        resp = client.get("/audit-logs", headers={"X-User-Role": "employee"})
        assert resp.status_code == 403
        
        # 3. Accessing audit logs with invalid header -> 401 Unauthorized
        resp = client.get("/audit-logs", headers={"X-User-Role": "invalid_role"})
        assert resp.status_code == 401

        # 4. Accessing audit logs with admin header -> 200 OK
        resp = client.get("/audit-logs", headers={"X-User-Role": "admin"})
        assert resp.status_code == 200


def test_xss_input_sanitization_blocking() -> None:
    """Verifies that script injections and XSS payloads are intercepted with 400 Bad Request."""
    with TestClient(app) as client:
        payload = {
            "user_id": "attacker",
            "text": "<script>alert('XSS')</script> Log this expense.",
        }
        resp = client.post("/expenses/submit", json=payload, headers={"X-User-Role": "employee"})
        assert resp.status_code == 400
        assert "Malicious payload detected" in resp.json()["detail"]


def test_rate_limiting_middleware() -> None:
    """Tests that a flood of requests from an IP results in 429 Too Many Requests."""
    from security.middleware import REQUEST_HISTORY, MAX_REQUESTS_PER_WINDOW
    import time
    
    client_ip = "testclient"
    now = time.time()
    # Inject maximum requests into the history to trigger rate limiting
    REQUEST_HISTORY[client_ip] = [now] * MAX_REQUESTS_PER_WINDOW
    
    with TestClient(app) as client:
        resp = client.get("/", headers={"X-User-Role": "admin"})
        assert resp.status_code == 429
        assert "Rate limit exceeded" in resp.json()["detail"]
        
    # Clean up
    REQUEST_HISTORY.clear()


def test_env_security_defaults() -> None:
    """Verifies that verify_env_security raises error on weak default configurations."""
    import os
    original_db = os.environ.get("DATABASE_URL")
    
    # 1. Inject insecure connection string
    os.environ["DATABASE_URL"] = "postgresql://admin:password@127.0.0.1/db"
    with pytest.raises(ValueError) as exc:
        verify_env_security()
    assert "uses weak admin password defaults" in str(exc.value)
    
    # Restore
    if original_db:
        os.environ["DATABASE_URL"] = original_db
    else:
        del os.environ["DATABASE_URL"]
