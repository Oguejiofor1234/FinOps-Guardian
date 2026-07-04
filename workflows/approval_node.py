from typing import Any

from google.adk.agents.context import Context
from google.adk.events.event import Event
from google.adk.events.request_input import RequestInput
from google.adk.workflow import node

from guardrails.safe_logger import SafeLogger
from mcp_servers.notification_server import send_manager_alert, send_receipt_request


@node(rerun_on_resume=True)
async def run_approval(ctx: Context, node_input: Any):
    """
    Human-in-the-Loop approval node handling compliance decisions statelessly.
    Reconstructs the current phase by inspecting active inputs in `ctx.resume_inputs`.
    """
    logger = SafeLogger()
    risk_level = ctx.state.get("risk_level", "UNKNOWN")
    val_err = ctx.state.get("validation_error", "")

    # Phase 0: First execution (no inputs at all) - pause and request manager decision
    if not ctx.resume_inputs:
        logger.info(f"Approval Node: Pausing for manager decision. Risk: {risk_level}")
        send_manager_alert(
            session_id=ctx.session,
            title=ctx.state.get("title", ""),
            amount=ctx.state.get("amount", 0.0),
            risk_level=risk_level,
            reasons=val_err or "None",
        )
        yield RequestInput(
            interrupt_id="manager_decision",
            message=f"Human approval required. Risk: {risk_level}. Violation(s): {val_err or 'None'}",
        )
        return

    # Extract inputs and support nested payloads
    manager_dec = ctx.resume_inputs.get("manager_decision")
    if isinstance(manager_dec, dict):
        manager_dec = (
            manager_dec.get("manager_decision")
            or manager_dec.get("decision")
            or manager_dec.get("value")
        )

    receipt_up = ctx.resume_inputs.get("receipt_upload")

    senior_dec = ctx.resume_inputs.get("senior_manager_decision")
    if isinstance(senior_dec, dict):
        senior_dec = senior_dec.get("senior_manager_decision") or senior_dec.get(
            "decision"
        )

    # Phase 3: Senior Manager Escalation decision
    if manager_dec == "ESCALATE":
        if senior_dec is None:
            logger.warning(
                "Approval Node: Escalation active, awaiting senior manager decision."
            )
            yield RequestInput(
                interrupt_id="senior_manager_decision",
                message=f"Escalated high-risk audit required. Violation: {val_err}. Approve or Reject?",
            )
            return

        if senior_dec == "APPROVE":
            logger.info("Approval Node: Escalation approved by senior manager.")
            yield Event(
                route="APPROVED",
                state={
                    "approval_status": "APPROVED",
                    "manager_decision": "APPROVE",
                    "escalation_level": "SENIOR_MANAGER",
                },
            )
        else:
            logger.warning("Approval Node: Escalation rejected by senior manager.")
            yield Event(
                route="REJECTED",
                state={
                    "approval_status": "REJECTED",
                    "manager_decision": "REJECT",
                    "escalation_level": "SENIOR_MANAGER",
                },
            )
        return

    # Phase 2: Receipt upload loop
    if manager_dec == "REQUEST_RECEIPT":
        if receipt_up is None:
            logger.info("Approval Node: Awaiting user receipt upload.")
            send_receipt_request(
                session_id=ctx.session,
                title=ctx.state.get("title", ""),
                amount=ctx.state.get("amount", 0.0),
                recipient_email=ctx.state.get("manager_decision_email")
                or "employee@company.com",
            )
            yield RequestInput(
                interrupt_id="receipt_upload",
                message="Your claim requires a receipt. Please upload the receipt image or document path.",
            )
            return

        logger.info(
            f"Approval Node: User uploaded receipt: {receipt_up}. Requesting final manager decision."
        )
        yield RequestInput(
            interrupt_id="manager_decision",
            message=f"Receipt uploaded at: {receipt_up}. Final decision: Approve or Reject?",
        )
        return

    # Phase 1: Direct manager decision (APPROVE / REJECT)
    if manager_dec == "APPROVE":
        logger.info(
            "Approval Node: Claim approved by manager. Routing to success ledger."
        )
        has_receipt = True if receipt_up else ctx.state.get("has_receipt", False)
        yield Event(
            route="APPROVED",
            state={
                "approval_status": "APPROVED",
                "manager_decision": "APPROVE",
                "has_receipt": has_receipt,
            },
        )
    elif manager_dec == "REJECT":
        logger.warning(
            "Approval Node: Claim rejected by manager. Routing to rejection notification."
        )
        yield Event(
            route="REJECTED",
            state={"approval_status": "REJECTED", "manager_decision": "REJECT"},
        )
    else:
        logger.error(
            f"Approval Node: Unknown manager decision '{manager_dec}'. Rejecting by default."
        )
        yield Event(
            route="REJECTED",
            state={"approval_status": "REJECTED", "manager_decision": "REJECT"},
        )
