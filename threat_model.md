# FinOps Guardian — Enterprise Threat Model

This document outlines the threat modeling, asset definitions, and security mitigations for **FinOps Guardian** using the industry-standard **STRIDE** methodology.

## 📦 Asset Classification

1. **PostgreSQL Expense Ledger**: Trusted source of truth for approved expense claims.
2. **active Session Store**: Context memory containing active compliance states, parsing logs, and paused manual approvals.
3. **Audit Log Trail**: Chronological file containing actors and events for compliance audits.
4. **LLM Prompts & Configuration**: Base configurations directing the Root, Auditor, and Analyst agents.

---

## 🛡️ STRIDE Threat Assessment

### 1. Spoofing (Identity)
* **Threat**: An attacker impersonates a manager to approve their own or other high-risk claims.
* **Mitigation**: Strict header-based RBAC authentication dependency on the `/sessions/{session_id}/decide` route. Regular users are blocked with HTTP 403.

### 2. Tampering (Data Integrity)
* **Threat**: A user sends malicious scripts or SQL injection parameters within claims to corrupt databases or extract data.
* **Mitigation**: `ContentSanitizationMiddleware` checks both URL parameters and JSON payloads for `<script>` structures and blockages. Expense fields are typed and validated using Pydantic schemas.

### 3. Repudiation
* **Threat**: A manager approves an invalid expense and denies taking the action.
* **Mitigation**: Critical event triggers append structured details (actor, timestamp, session ID, and status) to `audit_trail.jsonl` immediately upon receipt of decisions, creating a non-repudiable log.

### 4. Information Disclosure
* **Threat**: Developers or support staff read application log traces and extract credit card numbers, SSNs, or other employee PII.
* **Mitigation**: `StructuredJsonFormatter` and `log_audit_event` pass all logging payloads through regex-based masking filters, replacing credit cards and SSNs with redaction tokens before writing.

### 5. Denial of Service (DoS)
* **Threat**: An attacker floods submission endpoints with thousands of requests, crashing the FastAPI server or incurring massive Gemini API usage costs.
* **Mitigation**: `RateLimitingMiddleware` tracks request histories per client IP, instantly rejecting clients with HTTP 429 once they exceed `100` requests within a 60-second window.

### 6. Elevation of Privilege
* **Threat**: An employee changes their role header or overrides internal compliance validation logic.
* **Mitigation**: Internal state transitions are locked within the ADK graph workflow. Enforced dependencies check `X-User-Role` against an authorized static enumeration (`admin`, `manager`, `employee`).
