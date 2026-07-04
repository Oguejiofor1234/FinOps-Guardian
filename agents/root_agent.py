import json
from datetime import date
from typing import Any

from google.adk.agents.context import Context
from google.adk.events.event import Event
from google.adk.events.request_input import RequestInput
from google.adk.workflow import Workflow, node
from pydantic import BaseModel, ValidationError

from agents.analyst_agent import analyze_expense
from guardrails.pii_guardrail import PIIGuardrail
from guardrails.prompt_injection_guardrail import PromptInjectionGuardrail
from guardrails.safe_logger import SafeLogger
from guardrails.secret_guardrail import SecretGuardrail
from mcp_servers.erp_server import check_duplicate_claim, write_expense
from mcp_servers.notification_server import (
    send_approval_notice,
    send_rejection_notice,
)
from schemas.expense import ExpenseReport
from workflows.approval_node import run_approval


class FinOpsState(BaseModel):
    """Pydantic model representing the workflow execution state of FinOps Guardian."""

    raw_input: str | None = None
    title: str | None = None
    amount: float | None = None
    category: str | None = None
    expense_date: str | None = None
    has_receipt: bool | None = None
    has_itinerary: bool = False

    # Compliance & audit outcomes
    sanitized_title: str | None = None
    risk_level: str | None = None
    validation_error: str | None = None
    security_threat_detected: bool = False
    is_duplicate: bool = False
    tax_code: str | None = None
    gl_code: str | None = None
    cost_center: str | None = None
    saving_insight: str | None = None
    tax_deductibility: str | None = None
    audit_logged: bool = False
    committed_to_erp: bool = False
    txn_id: str | None = None
    notified: bool = False
    approval_status: str | None = None
    manager_decision: str | None = None
    escalation_level: str | None = None


# --- Routing & Graph Decision Nodes ---


def run_guardrails(ctx: Context, node_input: Any) -> Event:
    """Detects prompt injection and sanitizes PII/secrets."""
    logger = SafeLogger()

    # Extract string content from node_input (which can be str, dict, or Content)
    text = ""
    if isinstance(node_input, str):
        text = node_input
    elif isinstance(node_input, dict):
        text = node_input.get("title", "") + " " + str(node_input.get("amount", ""))
    else:
        try:
            text = node_input.parts[0].text
        except Exception:
            text = str(node_input)

    logger.info("Guardrails: Scanning input text...")

    # 1. Check for prompt injection
    injection_guard = PromptInjectionGuardrail()
    if injection_guard.is_injection(text):
        logger.warning(f"Guardrails: Threat detected in input: {text}")
        return Event(
            route="SECURITY_THREAT",
            state={
                "security_threat_detected": True,
                "raw_input": text,
                "risk_level": "HIGH",
                "validation_error": "Prompt injection threat detected",
            },
        )

    # 2. Redact secrets and PII
    pii_guard = PIIGuardrail()
    secret_guard = SecretGuardrail()
    sanitized = secret_guard.redact(text)
    sanitized = pii_guard.redact(sanitized)

    return Event(
        route="SAFE",
        output=sanitized,
        state={"raw_input": text, "sanitized_title": sanitized},
    )


def run_validation(ctx: Context, node_input: Any) -> Event:
    """Validates raw input against ExpenseReport Pydantic schema."""
    logger = SafeLogger()
    title = ctx.state.get("title")
    amount = ctx.state.get("amount")

    if title is not None and amount is not None:
        data = {
            "title": title,
            "amount": amount,
            "category": ctx.state.get("category", "other"),
            "expense_date": ctx.state.get("expense_date"),
            "has_receipt": ctx.state.get("has_receipt", False),
            "has_itinerary": ctx.state.get("has_itinerary", False),
        }
    else:
        raw_input = ctx.state.get("raw_input", "")
        data = None
        if isinstance(raw_input, str):
            try:
                data = json.loads(raw_input)
            except json.JSONDecodeError:
                # If not JSON format, mock a dict for custom error trigger
                data = {
                    "title": raw_input,
                    "amount": -1.0,  # Forces validation error
                    "category": "other",
                    "expense_date": str(date.today()),
                    "has_receipt": False,
                }
        elif isinstance(raw_input, dict):
            data = raw_input

    try:
        report = ExpenseReport(**data)
        logger.info("Validation: Schema checks passed.")
        return Event(
            route="VALID",
            output=report.model_dump(),
            state={
                "title": report.title,
                "amount": report.amount,
                "category": report.category,
                "expense_date": str(report.expense_date),
                "has_receipt": report.has_receipt,
                "has_itinerary": report.has_itinerary,
            },
        )
    except ValidationError as e:
        err_msg = str(e)
        if "requires a receipt for any expense exceeding" in err_msg:
            logger.info(
                "Validation: Bypassing strict receipt check in validation to audit/HITL."
            )
            payload = {
                "title": data.get("title", ""),
                "amount": float(data.get("amount", 0)),
                "category": data.get("category", "other"),
                "expense_date": str(data.get("expense_date", date.today())),
                "has_receipt": False,
                "has_itinerary": data.get("has_itinerary", False),
            }
            return Event(route="VALID", output=payload, state=payload)
        logger.error(f"Validation: Schema checks failed: {err_msg}")
        return Event(route="INVALID", state={"validation_error": err_msg})


def run_audit(ctx: Context, node_input: Any) -> Event:
    """Specialist Auditor Agent: validates compliance policies and scores risk."""
    logger = SafeLogger()
    import risk_score

    # Check database duplicates via the MCP server tool
    dup_res = check_duplicate_claim(
        title=node_input.get("title", ""),
        amount=float(node_input.get("amount", 0.0)),
        category=node_input.get("category", ""),
        expense_date=str(node_input.get("expense_date", "")),
    )
    logger.info(f"Auditor: duplicate check returned: '{dup_res}'")
    is_duplicate = "Duplicate claim detected" in dup_res

    # Retrieve past claims list if present in state
    history = ctx.state.get("history") or []
    if is_duplicate:
        history.append(node_input)

    # Run the risk scoring engine
    risk_level, reasons, _recommended_action, _confidence = risk_score.calculate_risk(
        node_input, history
    )

    state_update = {
        "risk_level": risk_level,
        "validation_error": f"Policy violations: {', '.join(reasons)}"
        if reasons
        else None,
    }

    if risk_level == "HIGH":
        logger.error("Audit Vault: Logging high-risk duplicate event.")
        state_update["is_duplicate"] = True
        return Event(route="APPROVAL", state=state_update)
    elif risk_level == "MEDIUM":
        logger.warning(f"Auditor: Policy violations flagged: {', '.join(reasons)}")
        return Event(route="APPROVAL", state=state_update)
    else:
        logger.info("Auditor: Claim complies with policy.")
        return Event(route="LOW_RISK", state=state_update)


def handle_security_threat(ctx: Context, node_input: Any) -> Event:
    """Handles prompt injection violations by logging security threat."""
    logger = SafeLogger()
    logger.error("Security Vault: Logging injection threat event.")
    event = Event(
        state={"audit_logged": True},
        output="Security Alert: Security threat detected and logged.",
    )
    event.message = "Security Alert: Security threat detected and logged."
    return event


def handle_validation_error(ctx: Context, node_input: Any) -> Event:
    """Handles schema validation errors by rejecting claim."""
    logger = SafeLogger()
    err = ctx.state.get("validation_error", "Unknown validation error")
    logger.error("Validation Handler: Claim rejected.")
    event = Event(output=f"Validation failed: {err}")
    event.message = f"Validation failed: {err}"
    return event


def handle_high_risk(ctx: Context, node_input: Any) -> Event:
    """Handles high compliance/fraud risks by logging event."""
    logger = SafeLogger()
    logger.error("Audit Vault: Logging high-risk duplicate event.")
    event = Event(
        state={"audit_logged": True},
        output="Rejected: High compliance risk / suspected duplicate claim detected.",
    )
    event.message = (
        "Rejected: High compliance risk / suspected duplicate claim detected."
    )
    return event


@node(rerun_on_resume=True)
async def handle_medium_risk(ctx: Context, node_input: Any):
    """Applies HITL routing, pausing for manager approval."""
    logger = SafeLogger()
    if not ctx.resume_inputs or "manager_action" not in ctx.resume_inputs:
        logger.info("HITL Portal: Pausing execution for manager approval.")
        yield RequestInput(
            interrupt_id="manager_action",
            message="Expense violates policy. Approve or Reject?",
        )
        return

    decision = ctx.resume_inputs["manager_action"]
    if isinstance(decision, dict):
        decision = (
            decision.get("manager_action")
            or decision.get("decision")
            or decision.get("value")
        )
    logger.info(f"HITL Portal: Decision received: {decision}")

    if decision == "APPROVE":
        yield Event(route="APPROVED", state={"approval_status": "APPROVED"})
    else:
        yield Event(route="REJECTED", state={"approval_status": "REJECTED"})


def handle_rejection(ctx: Context, node_input: Any) -> Event:
    """Handles manager rejected claims by logging outcome."""
    logger = SafeLogger()
    logger.info("Notification: Dispatching claim rejection notification.")
    title = ctx.state.get("title", "")
    amount = ctx.state.get("amount", 0.0)
    val_err = ctx.state.get("validation_error", "Policy violation")

    res = send_rejection_notice(
        session_id=ctx.session,
        title=title,
        amount=amount,
        reason=val_err,
        recipient_email=ctx.state.get("manager_decision_email")
        or "employee@company.com",
    )
    logger.info(f"Notification MCP: {res}")

    event = Event(
        state={"notified": True}, output="Rejected: Claim rejected by manager."
    )
    event.message = "Rejected: Claim rejected by manager."
    return event


def run_analyst(ctx: Context, node_input: Any) -> Event:
    """Specialist Analyst Agent: maps expense to standard accounting and tax parameters."""
    logger = SafeLogger()
    expense = {
        "title": ctx.state.get("title"),
        "amount": ctx.state.get("amount"),
        "category": ctx.state.get("category"),
        "expense_date": ctx.state.get("expense_date"),
        "has_receipt": ctx.state.get("has_receipt"),
        "has_itinerary": ctx.state.get("has_itinerary"),
    }

    result = analyze_expense(expense)
    logger.info(
        f"Analyst: Mapped category {result.category} to GL {result.gl_code}, CC {result.cost_center}, Tax {result.tax_code}."
    )

    return Event(
        state={
            "category": result.category,
            "gl_code": result.gl_code,
            "cost_center": result.cost_center,
            "tax_code": result.tax_code,
            "tax_deductibility": result.tax_deductibility,
            "saving_insight": result.saving_insight,
        },
        output=result.model_dump(),
    )


def commit_to_ledger(ctx: Context, node_input: Any) -> Event:
    """Specialist Ledger Agent: commits transaction to PostgreSQL ledger."""
    logger = SafeLogger()
    title = ctx.state.get("title", "")
    amount = ctx.state.get("amount", 0.0)

    # Write to database through the MCP server write_expense tool
    res = write_expense(
        title=title,
        amount=amount,
        category=ctx.state.get("category", "other"),
        expense_date=ctx.state.get("expense_date", str(date.today())),
        has_receipt=ctx.state.get("has_receipt", False),
        has_itinerary=ctx.state.get("has_itinerary", False),
        risk_level=ctx.state.get("risk_level", "LOW"),
        tax_code=ctx.state.get("tax_code", "GEN-TAX"),
        gl_code=ctx.state.get("gl_code", "6900"),
        cost_center=ctx.state.get("cost_center", "CC-CORP"),
        saving_insight=ctx.state.get("saving_insight", ""),
        tax_deductibility=ctx.state.get("tax_deductibility", ""),
        manager_decision=ctx.state.get("manager_decision") or "APPROVE",
        approval_status=ctx.state.get("approval_status") or "APPROVED",
    )

    txn_id = "TXN-POSTGRES-MOCK"
    if "transaction" in res:
        parts = res.split("transaction ")
        if len(parts) > 1:
            txn_id = parts[1].split(" ")[0]

    logger.info(f"Ledger MCP: {res}")
    return Event(state={"committed_to_erp": True, "txn_id": txn_id, "approval_status": "APPROVED"})


def send_notifications(ctx: Context, node_input: Any) -> Event:
    """Notification Agent: posts final notification alerts."""
    logger = SafeLogger()
    logger.info("Notification MCP: Posting success alert to Slack channel.")

    title = ctx.state.get("title", "")
    amount = ctx.state.get("amount", 0.0)
    txn_id = ctx.state.get("txn_id", "TXN-POSTGRES-MOCK")

    res = send_approval_notice(
        session_id=ctx.session,
        title=title,
        amount=amount,
        txn_id=txn_id,
        recipient_email=ctx.state.get("manager_decision_email")
        or "employee@company.com",
    )
    logger.info(f"Notification MCP: {res}")

    event = Event(
        state={"notified": True},
        output="Approved: Expense compliance audit completed successfully.",
    )
    event.message = "Approved: Expense compliance audit completed successfully."
    return event


# --- Define Root Compliance Agent Workflow ---

edges = [
    ("START", run_guardrails),
    (run_guardrails, {"SECURITY_THREAT": run_approval, "SAFE": run_validation}),
    (run_validation, {"INVALID": handle_validation_error, "VALID": run_audit}),
    (run_audit, {"APPROVAL": run_approval, "LOW_RISK": run_analyst}),
    (run_approval, {"APPROVED": run_analyst, "REJECTED": handle_rejection}),
    (run_analyst, commit_to_ledger),
    (commit_to_ledger, send_notifications),
]

root_agent = Workflow(
    name="root_compliance_agent",
    edges=edges,
    state_schema=FinOpsState,
    description="Orchestrates compliance checking, guardrail validation, and routing of corporate expense claims.",
)
