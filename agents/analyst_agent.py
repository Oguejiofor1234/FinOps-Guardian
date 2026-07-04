import json
import os
from typing import Any

from google.adk.agents import Agent
from google.adk.models import Gemini
from google.genai import types
from pydantic import BaseModel, Field


class AnalysisResult(BaseModel):
    """Structured analysis results from the Analyst Agent."""

    category: str = Field(
        description="The mapped category (meals, travel, office, software, training, other)."
    )
    gl_code: str = Field(description="The general ledger (GL) account code.")
    cost_center: str = Field(description="The department cost center code.")
    tax_code: str = Field(
        description="The tax deductibility code (ME-50, TRV-100, OFF-100, SaaS-100, GEN-TAX)."
    )
    tax_deductibility: str = Field(
        description="Brief explanation of the tax deductibility."
    )
    saving_insight: str = Field(
        description="An actionable cost-saving insight for this type of expense."
    )


# Analyst Agent definition conforming to ADK Agent requirements
analyst_agent = Agent(
    name="analyst_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=(
        "You are the Analyst Agent. Your responsibility is to map approved corporate expenses to accounting parameters and generate savings insights.\n"
        "Approved categories and standard codes:\n"
        "- meals: GL 6200, Cost Center CC-MARKETING, Tax Code ME-50\n"
        "- travel: GL 6100, Cost Center CC-SALES, Tax Code TRV-100\n"
        "- office: GL 6300, Cost Center CC-OPS, Tax Code OFF-100\n"
        "- software: GL 6400, Cost Center CC-ENG, Tax Code SaaS-100\n"
        "- training: GL 6500, Cost Center CC-HR, Tax Code GEN-TAX\n"
        "- other: GL 6900, Cost Center CC-CORP, Tax Code GEN-TAX\n\n"
        "Return the mapped category, GL code, cost center, tax code, tax deductibility explanation, and a custom, actionable cost-saving recommendation (e.g. suggesting vendor consolidation, SaaS audits, or discount options) based on the expense title/details."
    ),
    description="Maps approved expenses to GL/tax codes and generates cost-saving insights.",
    output_schema=AnalysisResult,
)


def analyze_expense(expense: dict[str, Any]) -> AnalysisResult:
    """
    Analyzes an approved expense report by mapping category/codes deterministically
    and invoking the Analyst LLM to generate custom tax explanations and savings insights.
    """
    # Load mappings from category_mapping.json
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    mapping_path = os.path.join(base_dir, "category_mapping.json")

    mapping = {}
    if os.path.exists(mapping_path):
        with open(mapping_path, encoding="utf-8") as f:
            mapping = json.load(f)

    cat = str(expense.get("category", "other")).lower()

    # Normalize synonyms
    if "suppl" in cat or "office" in cat:
        cat = "office"
    elif "train" in cat or "course" in cat or "learn" in cat:
        cat = "training"

    if cat not in mapping:
        cat = "other"

    mapping_data = mapping.get(cat, mapping.get("other"))

    try:
        # Prompt LLM for savings recommendations and deductibility insights
        prompt = f"Analyze this expense claim for insights: Title: {expense.get('title')}, Amount: {expense.get('amount')}, Category: {cat}"

        client = analyst_agent.model.api_client
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=analyst_agent.instruction,
                response_mime_type="application/json",
                response_schema=AnalysisResult,
            ),
        )
        result = AnalysisResult.model_validate_json(response.text)

        return AnalysisResult(
            category=cat,
            gl_code=mapping_data["gl_code"],
            cost_center=mapping_data["cost_center"],
            tax_code=mapping_data["tax_code"],
            tax_deductibility=result.tax_deductibility or mapping_data["description"],
            saving_insight=result.saving_insight
            or "Monitor department spend and negotiate vendor contracts.",
        )
    except Exception:
        # Fallback to deterministic configuration if LLM invocation fails
        return AnalysisResult(
            category=cat,
            gl_code=mapping_data["gl_code"],
            cost_center=mapping_data["cost_center"],
            tax_code=mapping_data["tax_code"],
            tax_deductibility=mapping_data["description"],
            saving_insight="Standard monitoring. Consider vendor volume discount opportunities.",
        )
