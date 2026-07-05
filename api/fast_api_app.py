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

import contextlib
import os
from collections.abc import AsyncIterator
from datetime import date, datetime

import google.auth
from a2a.server.tasks import InMemoryTaskStore
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from security.rbac import require_role, ROLE_EMPLOYEE, ROLE_MANAGER, ROLE_ADMIN
from security.middleware import RateLimitingMiddleware, ContentSanitizationMiddleware, verify_env_security

# Verify environmental security guidelines
verify_env_security()
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.runners import Runner
from google.cloud import logging as google_cloud_logging
from google.genai import types
from pydantic import BaseModel, Field

from app.app_utils import services
from app.app_utils.a2a import attach_a2a_routes
from app.app_utils.telemetry import setup_telemetry
from app.app_utils.typing import Feedback

load_dotenv()
setup_telemetry()

try:
    _, project_id = google.auth.default()
    logging_client = google_cloud_logging.Client()
    logger = logging_client.logger(__name__)
except Exception:
    import logging

    logger = logging.getLogger(__name__)

allow_origins = (
    os.getenv("ALLOW_ORIGINS", "").split(",") if os.getenv("ALLOW_ORIGINS") else None
)

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    from app.agent import app as adk_app
    from app.agent import root_agent

    runner = Runner(
        app=adk_app,
        session_service=services.get_session_service(),
        artifact_service=services.get_artifact_service(),
        auto_create_session=True,
    )
    app.state.runner = runner
    app.state.agent_app_name = adk_app.name
    await attach_a2a_routes(
        app,
        agent=root_agent,
        runner=runner,
        task_store=InMemoryTaskStore(),
        rpc_path=f"/a2a/{adk_app.name}",
    )
    yield


app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    artifact_service_uri=services.ARTIFACT_SERVICE_URI,
    allow_origins=allow_origins,
    session_service_uri=services.SESSION_SERVICE_URI,
    otel_to_cloud=False,
    lifespan=lifespan,
)
app.title = "FinOps Guardian API"
app.description = "API for submitting expenses, checking status, approving/rejecting claims, and viewing compliance metrics."

# Mount static folder containing HTML/CSS/JS dashboard
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Register security middlewares
app.add_middleware(RateLimitingMiddleware)
app.add_middleware(ContentSanitizationMiddleware)


@app.get("/", response_class=HTMLResponse)
def read_root():
    index_path = os.path.join("frontend", "index.html")
    if os.path.exists(index_path):
        with open(index_path) as f:
            return HTMLResponse(content=f.read(), status_code=200)
    return HTMLResponse(
        content="<h1>Dashboard index.html not found</h1>", status_code=404
    )

# Prioritize our custom root route over default ADK playground routes
our_route = None
for r in app.routes:
    if getattr(r, "endpoint", None) == read_root:
        our_route = r
        break
if our_route:
    app.routes.remove(our_route)
    app.routes.insert(0, our_route)


# --- Request / Response Schemas ---


class ExpenseSubmission(BaseModel):
    user_id: str = Field(
        ..., description="Unique ID of the employee submitting the expense claim."
    )
    text: str = Field(..., description="Raw description of the expense claim.")


class ManagerDecisionRequest(BaseModel):
    user_id: str = Field(..., description="Unique ID of the manager.")
    decision: str = Field(
        ...,
        description="Manager action. Must be one of: APPROVE, REJECT, REQUEST_RECEIPT.",
    )
    notes: str | None = Field(None, description="Optional manager feedback notes.")
    interrupt_id: str = "manager_decision"


class ReceiptUploadRequest(BaseModel):
    user_id: str = Field(..., description="Unique ID of the employee.")
    receipt_path: str = Field(
        ..., description="URI or local path to the uploaded receipt image/pdf."
    )


# --- REST Routes ---


@app.post("/feedback")
def collect_feedback(feedback: Feedback) -> dict[str, str]:
    """Collect and log feedback."""
    try:
        logger.log_struct(feedback.model_dump(), severity="INFO")
    except Exception:
        pass
    return {"status": "success"}


COMPLIANCE_STREAM_LOGS = [
    {"time": "System", "text": "FinOps Guardian App initialized. Standby for submissions.", "type": "info"}
]

def add_compliance_stream_log(text: str, type: str = "info"):
    from datetime import datetime
    time_str = datetime.now().strftime("%H:%M:%S")
    COMPLIANCE_STREAM_LOGS.append({"time": time_str, "text": text, "type": type})
    # Limit list size to avoid memory growth
    if len(COMPLIANCE_STREAM_LOGS) > 100:
        COMPLIANCE_STREAM_LOGS.pop(1)  # Keep the initial log at index 0

@app.get("/compliance-stream", dependencies=[Depends(require_role([ROLE_MANAGER, ROLE_ADMIN]))])
def get_compliance_stream():
    """
    Returns the real-time compliance operations log stream.
    """
    return {"logs": COMPLIANCE_STREAM_LOGS}


@app.get("/demo-settings")
def get_demo_settings():
    """
    Returns whether DEMO_MODE is active based on the environment flag.
    """
    import os
    demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"
    return {"demo_mode": demo_mode}


@app.post("/expenses/submit", dependencies=[Depends(require_role([ROLE_EMPLOYEE, ROLE_MANAGER, ROLE_ADMIN]))])
async def submit_expense(submission: ExpenseSubmission):
    """
    Submits a new unstructured expense claim, runs the guardrails, parsing,
    and policy engine, and returns if the transaction is completed or paused for review.
    """
    session_service = services.get_session_service()
    runner = app.state.runner
    app_name = app.state.agent_app_name

    add_compliance_stream_log(f"Ingesting claim: \"{submission.text}\"", "info")
    add_compliance_stream_log("Guardrails active: Scanning input text for sensitive data...", "info")

    session = await session_service.create_session(
        app_name=app_name, user_id=submission.user_id
    )

    message = types.Content(
        role="user", parts=[types.Part.from_text(text=submission.text)]
    )

    events = []
    async for event in runner.run_async(
        user_id=submission.user_id, session_id=session.id, new_message=message
    ):
        events.append(event)

    session = await session_service.get_session(
        app_name=app_name, user_id=submission.user_id, session_id=session.id
    )

    # Check if there is an active interrupt (Manager Input)
    required_input = None
    for event in reversed(events):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if (
                    part.function_call
                    and part.function_call.name == "adk_request_input"
                ):
                    required_input = part.function_call.args.get("interruptId")
                    break
            if required_input:
                break

    status = "paused" if required_input else "completed"
    final_output = next(
        (e.output for e in reversed(events) if e.output is not None), None
    )

    # Log parsing/validation/audit steps to compliance stream
    state = session.state or {}
    security_threat = state.get("security_threat_detected")
    if security_threat:
        add_compliance_stream_log("Security Alert: Security threat detected (Prompt Injection)!", "error")
    else:
        add_compliance_stream_log("PII Shield & Prompt Injection checks: Clean.", "success")
        
    title = state.get("title")
    amount = state.get("amount")
    if title and amount:
        add_compliance_stream_log(f"Parsed parameters: Merchant: \"{title}\", Amount: ${amount:.2f}, Category: \"{state.get('category')}\", Date: {state.get('expense_date')}", "success")
        
    val_err = state.get("validation_error")
    risk_level = state.get("risk_level")
    if val_err:
        add_compliance_stream_log(f"Compliance Auditor: Flags detected: {val_err}", "warning")
    elif risk_level:
        add_compliance_stream_log("Compliance Auditor: Policy checks passed.", "success")
        
    gl_code = state.get("gl_code")
    if gl_code:
        add_compliance_stream_log(f"Analyst Agent: Auto-mapped to GL Code: {gl_code}, CC: {state.get('cost_center')}, Tax: {state.get('tax_code')}", "success")
        if state.get("saving_insight"):
            add_compliance_stream_log(f"Analyst Insight: \"{state.get('saving_insight')}\"", "info")

    if status == "completed":
        if state.get("committed_to_erp"):
            add_compliance_stream_log(f"Ledger MCP: Database write success. Committed to ledger.", "success")
            add_compliance_stream_log("Notification MCP: Posted confirmation alert to Slack & Email.", "success")
        else:
            add_compliance_stream_log(f"Claim finalized. Output: \"{final_output}\"", "info")
    elif status == "paused":
        add_compliance_stream_log(f"Compliance Auditor: Claim flagged. Routing to Manager HITL Queue. Awaiting: {required_input}", "warning")
        add_compliance_stream_log("Notification MCP: Posted alert notice to Slack.", "warning")

    return {
        "session_id": session.id,
        "status": status,
        "required_input": required_input,
        "state": state,
        "final_output": final_output,
    }


@app.post("/sessions/{session_id}/decide", dependencies=[Depends(require_role([ROLE_MANAGER, ROLE_ADMIN]))])
async def manager_decide(session_id: str, request: ManagerDecisionRequest):
    """
    Resumes a paused compliance workflow with a manager decision (APPROVE, REJECT, or REQUEST_RECEIPT).
    """
    runner = app.state.runner
    app_name = app.state.agent_app_name
    session_service = services.get_session_service()

    message = types.Content(
        role="user",
        parts=[
            types.Part(
                function_response=types.FunctionResponse(
                    name="adk_request_input",
                    response={
                        "manager_decision": request.decision,
                        "notes": request.notes,
                    },
                    id=request.interrupt_id,
                )
            )
        ],
    )

    add_compliance_stream_log(f"HITL Manager Decision: Sending action \"{request.decision}\" for session {session_id}...", "info")

    events = []
    async for event in runner.run_async(
        user_id=request.user_id, session_id=session_id, new_message=message
    ):
        events.append(event)

    session = await session_service.get_session(
        app_name=app_name, user_id=request.user_id, session_id=session_id
    )

    required_input = None
    for event in reversed(events):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if (
                    part.function_call
                    and part.function_call.name == "adk_request_input"
                ):
                    required_input = part.function_call.args.get("interruptId")
                    break
            if required_input:
                break

    status = "paused" if required_input else "completed"
    final_output = next(
        (e.output for e in reversed(events) if e.output is not None), None
    )

    # Log outcomes to compliance stream
    state = session.state or {}
    gl_code = state.get("gl_code")
    if gl_code:
        add_compliance_stream_log(f"Analyst Agent: Auto-mapped to GL Code: {gl_code}, CC: {state.get('cost_center')}, Tax: {state.get('tax_code')}", "success")
        if state.get("saving_insight"):
            add_compliance_stream_log(f"Analyst Insight: \"{state.get('saving_insight')}\"", "info")

    if status == "completed":
        app_status = state.get("approval_status")
        if app_status == "APPROVED":
            add_compliance_stream_log(f"Ledger MCP: Database write success. Committed to ledger.", "success")
            add_compliance_stream_log("Notification MCP: Posted confirmation alert to Slack & Email.", "success")
        else:
            add_compliance_stream_log("Compliance Rejection: Claim rejected by manager.", "error")
            add_compliance_stream_log("Notification MCP: Posted rejection notice to Employee Email.", "error")
    elif status == "paused":
        add_compliance_stream_log(f"Compliance Auditor: Resumed and paused again. Awaiting: {required_input}", "warning")

    return {
        "status": "success",
        "session_status": status,
        "required_input": required_input,
        "state": state,
        "final_output": final_output,
    }


@app.post("/sessions/{session_id}/receipt", dependencies=[Depends(require_role([ROLE_EMPLOYEE, ROLE_MANAGER, ROLE_ADMIN]))])
async def upload_receipt(session_id: str, request: ReceiptUploadRequest):
    """
    Resumes a paused compliance workflow with a receipt upload path.
    """
    runner = app.state.runner
    app_name = app.state.agent_app_name
    session_service = services.get_session_service()

    message = types.Content(
        role="user",
        parts=[
            types.Part(
                function_response=types.FunctionResponse(
                    name="adk_request_input",
                    response={
                        "receipt_upload": request.receipt_path,
                    },
                    id="receipt_upload",
                )
            )
        ],
    )

    add_compliance_stream_log(f"HITL User Receipt Upload: Resuming session {session_id} with receipt path \"{request.receipt_path}\"...", "info")

    events = []
    async for event in runner.run_async(
        user_id=request.user_id, session_id=session_id, new_message=message
    ):
        events.append(event)

    session = await session_service.get_session(
        app_name=app_name, user_id=request.user_id, session_id=session_id
    )

    required_input = None
    for event in reversed(events):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if (
                    part.function_call
                    and part.function_call.name == "adk_request_input"
                ):
                    required_input = part.function_call.args.get("interruptId")
                    break
            if required_input:
                break

    status = "paused" if required_input else "completed"
    final_output = next(
        (e.output for e in reversed(events) if e.output is not None), None
    )

    # Log outcomes to compliance stream
    state = session.state or {}
    gl_code = state.get("gl_code")
    if gl_code:
        add_compliance_stream_log(f"Analyst Agent: Auto-mapped to GL Code: {gl_code}, CC: {state.get('cost_center')}, Tax: {state.get('tax_code')}", "success")
        if state.get("saving_insight"):
            add_compliance_stream_log(f"Analyst Insight: \"{state.get('saving_insight')}\"", "info")

    if status == "completed":
        app_status = state.get("approval_status")
        if app_status == "APPROVED":
            add_compliance_stream_log(f"Ledger MCP: Database write success. Committed to ledger.", "success")
            add_compliance_stream_log("Notification MCP: Posted confirmation alert to Slack & Email.", "success")
        else:
            add_compliance_stream_log("Compliance Rejection: Claim rejected by manager.", "error")
            add_compliance_stream_log("Notification MCP: Posted rejection notice to Employee Email.", "error")
    elif status == "paused":
        add_compliance_stream_log(f"Compliance Auditor: Resumed and paused again. Awaiting: {required_input}", "warning")

    return {
        "status": "success",
        "session_status": status,
        "required_input": required_input,
        "state": state,
        "final_output": final_output,
    }


@app.get("/sessions/{session_id}/status", dependencies=[Depends(require_role([ROLE_EMPLOYEE, ROLE_MANAGER, ROLE_ADMIN]))])
async def get_session_status(session_id: str, user_id: str):
    """
    Returns the current state and status of a compliance check session.
    """
    session_service = services.get_session_service()
    app_name = app.state.agent_app_name

    session = await session_service.get_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    status = (
        "completed"
        if session.state.get("committed_to_erp")
        or session.state.get("approval_status") == "REJECTED"
        else "paused"
    )

    return {"session_id": session_id, "status": status, "state": session.state}


@app.get("/audit-logs", dependencies=[Depends(require_role([ROLE_MANAGER, ROLE_ADMIN]))])
async def get_audit_logs():
    """
    Fetches the list of all committed transactions from the PostgreSQL ledger.
    Falls back to mock data merged with live session updates if the database is offline.
    """
    db_url = os.getenv("DATABASE_URL")
    import psycopg

    mock_logs = []

    # Query the sessions service to dynamically find live approved/rejected claims
    session_logs = []
    try:
        session_service = services.get_session_service()
        app_name = app.state.agent_app_name
        sessions_resp = await session_service.list_sessions(app_name=app_name)
        sessions = sessions_resp.sessions or []
        for s in sessions:
            state = s.state or {}
            app_status = state.get("approval_status")
            if app_status in ("APPROVED", "REJECTED"):
                session_logs.append({
                    "id": len(mock_logs) + len(session_logs) + 1,
                    "transaction_id": state.get("txn_id") or f"TXN-{s.session_id[:6].upper()}",
                    "title": state.get("title") or "Unparsed Expense",
                    "amount": float(state.get("amount") or 0.0),
                    "category": state.get("category") or "other",
                    "expense_date": state.get("expense_date") or "2026-07-03",
                    "has_receipt": state.get("has_receipt") or False,
                    "has_itinerary": state.get("has_itinerary") or False,
                    "risk_level": state.get("risk_level") or "LOW",
                    "tax_code": state.get("tax_code") or "N/A",
                    "gl_code": state.get("gl_code") or "N/A",
                    "cost_center": state.get("cost_center") or "N/A",
                    "saving_insight": state.get("saving_insight") or "N/A",
                    "tax_deductibility": state.get("tax_deductibility") or "N/A",
                    "manager_decision": state.get("manager_decision") or app_status,
                    "approval_status": app_status,
                    "created_at": state.get("created_at") or "2026-07-03 12:00:00"
                })
    except Exception:
        pass

    if not db_url:
        return {"logs": session_logs + mock_logs}

    try:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, transaction_id, title, amount, category, expense_date,
                           has_receipt, has_itinerary, risk_level, tax_code, gl_code,
                           cost_center, saving_insight, tax_deductibility, manager_decision,
                           approval_status, created_at
                    FROM expenses
                    ORDER BY created_at DESC;
                    """
                )
                rows = cur.fetchall()
                colnames = [desc[0] for desc in cur.description]

                results = []
                for row in rows:
                    row_dict = dict(zip(colnames, row, strict=False))
                    # Format dates/datetimes to string for JSON serialization
                    for key, val in row_dict.items():
                        if isinstance(val, (date, datetime)):
                            row_dict[key] = str(val)
                    results.append(row_dict)
                return {"logs": results}
    except Exception:
        # Fallback to mock data merged with live session updates
        return {"logs": session_logs + mock_logs}


@app.get("/metrics", dependencies=[Depends(require_role([ROLE_MANAGER, ROLE_ADMIN]))])
async def get_dashboard_metrics():
    """
    Calculates and returns aggregated dashboard statistics from the PostgreSQL ledger and session memory.
    """
    session_service = services.get_session_service()
    app_name = app.state.agent_app_name
    
    # 1. Fetch sessions for real-time compliance state
    sessions_resp = await session_service.list_sessions(app_name=app_name)
    sessions = sessions_resp.sessions or []
    
    pending_count = 0
    rejected_count = 0
    risk_breakdown = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    
    # We will also compute approved sessions stats to dynamically add to the base mock stats!
    session_approved_count = 0
    session_approved_amount = 0.0
    session_category_breakdown = {}

    for s in sessions:
        rl = s.state.get("risk_level")
        if rl in risk_breakdown:
            risk_breakdown[rl] += 1
            
        app_status = s.state.get("approval_status")
        if rl in ("HIGH", "MEDIUM") and not app_status:
            pending_count += 1
        elif app_status == "REJECTED":
            rejected_count += 1
        elif app_status == "APPROVED":
            session_approved_count += 1
            amt = float(s.state.get("amount") or 0.0)
            session_approved_amount += amt
            cat = s.state.get("category") or "other"
            if cat not in session_category_breakdown:
                session_category_breakdown[cat] = {"count": 0, "amount": 0.0}
            session_category_breakdown[cat]["count"] += 1
            session_category_breakdown[cat]["amount"] += amt

    # 2. Fetch approved database stats
    db_url = os.getenv("DATABASE_URL")
    import psycopg

    # Base mock metrics
    base_approved_count = 0
    base_approved_amount = 0.0
    category_breakdown = {}

    # Add values from live approved sessions for the fallback metrics
    total_approved_count = base_approved_count + session_approved_count
    total_approved_amount = base_approved_amount + session_approved_amount
    for cat, val in session_category_breakdown.items():
        if cat not in category_breakdown:
            category_breakdown[cat] = {"count": 0, "amount": 0.0}
        category_breakdown[cat]["count"] += val["count"]
        category_breakdown[cat]["amount"] += val["amount"]

    mock_metrics = {
        "approved_count": total_approved_count,
        "total_approved_amount": total_approved_amount,
        "pending_review_count": pending_count,
        "rejected_count": rejected_count,
        "risk_breakdown": risk_breakdown,
        "category_breakdown": category_breakdown
    }

    if not db_url:
        return mock_metrics

    try:
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*), COALESCE(SUM(amount), 0.0) 
                    FROM expenses 
                    WHERE approval_status = 'APPROVED';
                    """
                )
                approved_count, total_amount = cur.fetchone()
                
                cur.execute(
                    """
                    SELECT category, COUNT(*), COALESCE(SUM(amount), 0.0) 
                    FROM expenses 
                    GROUP BY category;
                    """
                )
                cat_rows = cur.fetchall()
                category_breakdown_db = {}
                for cat, count, amt in cat_rows:
                    category_breakdown_db[cat] = {"count": count, "amount": float(amt)}
                    
                return {
                    "approved_count": approved_count,
                    "total_approved_amount": float(total_amount),
                    "pending_review_count": pending_count,
                    "rejected_count": rejected_count,
                    "risk_breakdown": risk_breakdown,
                    "category_breakdown": category_breakdown_db
                }
    except Exception:
        # Fallback to dynamic mock data
        return mock_metrics


@app.get("/sessions/pending", dependencies=[Depends(require_role([ROLE_MANAGER, ROLE_ADMIN]))])
async def get_pending_sessions():
    """
    Returns all paused sessions that are currently awaiting a manager decision or user receipt upload.
    """
    session_service = services.get_session_service()
    app_name = app.state.agent_app_name
    sessions_resp = await session_service.list_sessions(app_name=app_name)
    sessions = sessions_resp.sessions or []
    
    pending = []
    for s in sessions:
        rl = s.state.get("risk_level")
        app_status = s.state.get("approval_status")
        if rl in ("HIGH", "MEDIUM") and not app_status:
            required_input = "manager_decision"
            # If manager requested receipt, and user has not uploaded it yet
            if s.state.get("manager_decision") == "REQUEST_RECEIPT" and not s.state.get("receipt_upload"):
                required_input = "receipt_upload"
            
            pending.append({
                "session_id": s.id,
                "state": s.state,
                "required_input": required_input
            })
    return {"pending": pending}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
