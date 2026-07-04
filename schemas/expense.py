from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

# Allowed categories defined in the expense policy
ExpenseCategory = Literal["meals", "travel", "office", "software", "other"]


class ExpenseReport(BaseModel):
    """Pydantic model representing a corporate expense claim with built-in validation rules."""

    title: str = Field(
        min_length=1,
        description="The name of the merchant or description of the purchase.",
    )
    amount: float = Field(
        description="The value of the expense in USD. Must be greater than 0."
    )
    category: ExpenseCategory = Field(
        description="The category of the expense. Must be: meals, travel, office, software, or other."
    )
    expense_date: date = Field(
        description="The date of the transaction (format: YYYY-MM-DD)."
    )
    has_receipt: bool = Field(
        description="Flag indicating if a receipt has been uploaded."
    )
    has_itinerary: bool = Field(
        default=False,
        description="Optional flag indicating if a travel itinerary is attached (for weekend audits).",
    )

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: float) -> float:
        """Ensures that the expense amount is strictly positive."""
        if value <= 0:
            raise ValueError("Expense amount must be greater than zero.")
        return value

    @model_validator(mode="after")
    def validate_receipt_requirement(self) -> "ExpenseReport":
        """Corporate policy rule: Any expense greater than $25.00 must have a receipt."""
        if self.amount > 25.00 and not self.has_receipt:
            raise ValueError(
                "Corporate policy requires a receipt for any expense exceeding $25.00."
            )
        return self
