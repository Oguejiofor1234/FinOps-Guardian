import json
import re
from datetime import date
from typing import Any

from google.adk.agents import Agent
from google.adk.agents.context import Context
from google.adk.events.event import Event
from google.adk.models import Gemini
from google.adk.workflow import Workflow, node
from google.genai import types
from pydantic import BaseModel, Field

from agents.root_agent import (
    FinOpsState,
    commit_to_ledger,
    handle_rejection,
    handle_validation_error,
    run_analyst,
    run_approval,
    run_audit,
    run_guardrails,
    run_validation,
    send_notifications,
)
from guardrails.safe_logger import SafeLogger

# --- Structured Parsing Schema ---


class ParsedExpense(BaseModel):
    title: str = Field(
        description="The merchant or vendor name extracted from the text."
    )
    amount: float = Field(description="The transaction amount in USD.")
    category: str = Field(
        description="Expense category. Must be one of: meals, travel, office, software, training, other."
    )
    expense_date: str = Field(
        description="The date of the transaction (YYYY-MM-DD). If not mentioned, use the current date."
    )
    has_receipt: bool = Field(
        default=False, description="Whether a receipt is mentioned or attached."
    )
    has_itinerary: bool = Field(
        default=False, description="Whether a travel itinerary is mentioned."
    )


# --- Parser Agent ---

parser_agent = Agent(
    name="parser_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=(
        "You are the Expense Parser Agent. Parse the raw expense description text into structured JSON fields:\n"
        "- title: Merchant / vendor name.\n"
        "- amount: Number value.\n"
        "- category: One of meals, travel, office, software, training, other.\n"
        "- expense_date: YYYY-MM-DD format (use current date if not specified).\n"
        "- has_receipt: True if receipt is mentioned as attached/present.\n"
        "- has_itinerary: True if travel itinerary is mentioned as attached/present."
    ),
    description="Parses unstructured expense descriptions into a structured schema.",
    output_schema=ParsedExpense,
)


@node(rerun_on_resume=True)
async def run_parser(ctx: Context, node_input: Any) -> Event:
    """
    Parses raw text or JSON dictionary input into structured state.
    Utilizes LLM parsing with automatic fallback and retries.
    """
    logger = SafeLogger()
    text = ""

    if isinstance(node_input, str):
        text = node_input
    elif isinstance(node_input, dict):
        logger.info("Parser: Input is already structured. Bypassing extraction.")
        return Event(state=node_input)
    else:
        try:
            text = node_input.parts[0].text
        except Exception:
            text = str(node_input)

    # If it looks like JSON, decode directly
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            logger.info("Parser: Parsed JSON dictionary directly from input string.")
            return Event(state=data)
    except json.JSONDecodeError:
        pass

    try:
        client = parser_agent.model.api_client
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=text,
            config=types.GenerateContentConfig(
                system_instruction=parser_agent.instruction,
                response_mime_type="application/json",
                response_schema=ParsedExpense,
            ),
        )
        parsed = ParsedExpense.model_validate_json(response.text)
        payload = parsed.model_dump()
        payload["expense_date"] = str(payload.get("expense_date", date.today()))
        logger.info(f"Parser: Successfully parsed structural fields: {payload}")
        return Event(state=payload)
    except Exception as e:
        logger.warning(
            f"Parser: LLM parsing failed: {e}. Running regex fallback parser."
        )

        # Regex parsing fallback
        text_lower = text.lower()
        amount = -1.0
        amount_match = re.search(r"(?:\$|usd\s*)(\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\d+(?:\.\d{2})?)", text, re.IGNORECASE)
        if amount_match:
            amount = float(amount_match.group(1).replace(",", ""))

        date_str = str(date.today())
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
        if date_match:
            date_str = date_match.group(1)
        else:
            # Try to parse standard dates like "July 2, 2026"
            months = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december",
                      "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
            months_pattern = "|".join(months)
            month_match = re.search(rf"({months_pattern})\s+(\d{{1,2}})[,\s]+(\d{{4}})", text, re.IGNORECASE)
            if month_match:
                m_name = month_match.group(1).lower()[:3]
                d_val = int(month_match.group(2))
                y_val = int(month_match.group(3))
                month_map = {
                    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
                    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
                }
                m_val = month_map.get(m_name, 1)
                try:
                    date_str = str(date(y_val, m_val, d_val))
                except ValueError:
                    pass

        category = "other"
        if "meals" in text_lower or "lunch" in text_lower or "dinner" in text_lower or "restaurant" in text_lower or "cafe" in text_lower:
            category = "meals"
        elif "travel" in text_lower or "flight" in text_lower or "hotel" in text_lower or "uber" in text_lower or "taxi" in text_lower or "retreat" in text_lower or "resort" in text_lower:
            category = "travel"
        elif (
            "office" in text_lower or "supplies" in text_lower or "paper" in text_lower or "monitors" in text_lower
        ):
            category = "office"
        elif (
            "software" in text_lower
            or "license" in text_lower
            or "saas" in text_lower
            or "github" in text_lower
        ):
            category = "software"
        elif "training" in text_lower or "course" in text_lower:
            category = "training"

        has_receipt = (
            "receipt" in text_lower or "attached" in text_lower or "receipt is attached" in text_lower
        ) and "no receipt" not in text_lower
        has_itinerary = "itinerary" in text_lower

        title = "Expense Claim"
        # Match common vendors in text
        vendors = ["uber", "cafe oasis", "github", "staples", "hotel", "airline", "taxi", "resort"]
        found_vendor = None
        for v in vendors:
            if v in text_lower:
                found_vendor = v
                break
        if found_vendor:
            title = found_vendor.title()
        elif " at " in text_lower:
            parts = text.split(" at ")
            if len(parts) > 1:
                title = parts[1].split(" on")[0].split(".")[0].strip()
        elif " for " in text_lower:
            parts = text.split(" for ")
            if len(parts) > 1:
                title = parts[1].split(" on")[0].split(".")[0].strip()

        if not title or title.strip() == "":
            title = "Expense Claim"

        payload = {
            "title": title,
            "amount": amount,
            "category": category,
            "expense_date": date_str,
            "has_receipt": has_receipt,
            "has_itinerary": has_itinerary,
        }
        logger.info(f"Parser: Fallback parser resolved: {payload}")
        return Event(state=payload)


# --- Fully Connected FinOps Guardian Workflow Graph ---

edges = [
    ("START", run_guardrails),
    (run_guardrails, {"SECURITY_THREAT": run_approval, "SAFE": run_parser}),
    (run_parser, run_validation),
    (run_validation, {"INVALID": handle_validation_error, "VALID": run_audit}),
    (run_audit, {"APPROVAL": run_approval, "LOW_RISK": run_analyst}),
    (run_approval, {"APPROVED": run_analyst, "REJECTED": handle_rejection}),
    (run_analyst, commit_to_ledger),
    (commit_to_ledger, send_notifications),
]

finops_workflow = Workflow(
    name="finops_workflow",
    edges=edges,
    state_schema=FinOpsState,
    description="Ties expense parsing, security guardrails, root coordinator, auditor, human-in-the-loop approvals, tax analysis, ERP commits, and notifications into a single secure pipeline.",
)
