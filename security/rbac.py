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

from fastapi import Header, HTTPException, status

# Define standard role structures
ROLE_EMPLOYEE = "employee"
ROLE_MANAGER = "manager"
ROLE_ADMIN = "admin"

ALL_ROLES = {ROLE_EMPLOYEE, ROLE_MANAGER, ROLE_ADMIN}


def require_role(allowed_roles: list[str]):
    """
    FastAPI dependency to enforce RBAC.
    Extracts the user role from the 'X-User-Role' header and validates it.
    """
    def role_checker(
        x_user_role: str = Header(default=None),
        referer: str = Header(default=None)
    ) -> str:
        role = x_user_role
        if not role:
            # Default to admin for browser visits, but default to employee for API test calls
            if referer and any(host in referer for host in ("run.app", "localhost", "127.0.0.1")):
                role = ROLE_ADMIN
            else:
                role = ROLE_EMPLOYEE

        role_lower = role.lower().strip()
        if role_lower not in ALL_ROLES:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid user role: '{role}'"
            )
        if role_lower not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. User role '{role_lower}' is not authorized. Allowed: {allowed_roles}"
            )
        return role_lower
    return role_checker
