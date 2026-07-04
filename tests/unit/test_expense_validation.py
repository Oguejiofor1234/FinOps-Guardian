import json
import pathlib

import pytest
from pydantic import ValidationError

from schemas.expense import ExpenseReport

SAMPLES_DIR = pathlib.Path(__file__).parent.parent / "samples"


def load_sample(filename: str) -> dict:
    """Loads a sample JSON file from the tests/samples/ directory."""
    with open(SAMPLES_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


def test_valid_expense() -> None:
    """Verifies that a valid expense is parsed correctly by the ExpenseReport model."""
    data = load_sample("valid_expense.json")
    report = ExpenseReport(**data)
    assert report.title == "Uber Trip to Client Office"
    assert report.amount == 42.50
    assert report.category == "travel"
    assert report.has_receipt is True


def test_invalid_amount() -> None:
    """Verifies that a negative amount triggers a validation error."""
    data = load_sample("invalid_amount.json")
    with pytest.raises(ValidationError) as excinfo:
        ExpenseReport(**data)
    assert "amount" in str(excinfo.value)
    assert "greater than zero" in str(excinfo.value)


def test_invalid_date() -> None:
    """Verifies that an invalid date string triggers a parsing validation error."""
    data = load_sample("invalid_date.json")
    with pytest.raises(ValidationError) as excinfo:
        ExpenseReport(**data)
    assert "expense_date" in str(excinfo.value)


def test_missing_receipt_above_threshold() -> None:
    """Verifies that an expense greater than $25.00 without a receipt is rejected."""
    data = load_sample("missing_receipt.json")
    with pytest.raises(ValidationError) as excinfo:
        ExpenseReport(**data)
    assert "requires a receipt for any expense exceeding $25.00" in str(excinfo.value)


def test_invalid_category() -> None:
    """Verifies that an unsupported category triggers a validation error."""
    data = load_sample("invalid_category.json")
    with pytest.raises(ValidationError) as excinfo:
        ExpenseReport(**data)
    assert "category" in str(excinfo.value)


def test_missing_required_amount() -> None:
    """Verifies that a completely missing amount triggers a validation error."""
    data = load_sample("valid_expense.json")
    del data["amount"]  # Remove amount
    with pytest.raises(ValidationError) as excinfo:
        ExpenseReport(**data)
    assert "amount" in str(excinfo.value)
    assert "Field required" in str(excinfo.value)
