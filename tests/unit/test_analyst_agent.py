from agents.analyst_agent import analyze_expense


def test_travel_mapping() -> None:
    """Verifies travel expense maps to GL 6100, Cost Center CC-SALES, and Tax Code TRV-100."""
    expense = {
        "title": "Hotel stay for sales meeting",
        "amount": 250.00,
        "category": "travel",
        "expense_date": "2026-06-30",
        "has_receipt": True,
    }
    result = analyze_expense(expense)
    assert result.category == "travel"
    assert result.gl_code == "6100"
    assert result.cost_center == "CC-SALES"
    assert result.tax_code == "TRV-100"
    assert result.tax_deductibility is not None
    assert result.saving_insight is not None


def test_meals_mapping() -> None:
    """Verifies meals expense maps to GL 6200, Cost Center CC-MARKETING, and Tax Code ME-50."""
    expense = {
        "title": "Business client dinner",
        "amount": 85.00,
        "category": "meals",
        "expense_date": "2026-06-30",
        "has_receipt": True,
    }
    result = analyze_expense(expense)
    assert result.category == "meals"
    assert result.gl_code == "6200"
    assert result.cost_center == "CC-MARKETING"
    assert result.tax_code == "ME-50"
    assert "50%" in result.tax_deductibility
    assert result.saving_insight is not None


def test_office_supplies_mapping() -> None:
    """Verifies office supplies category maps to GL 6300, Cost Center CC-OPS, and Tax Code OFF-100."""
    expense = {
        "title": "Printer paper and ink cartridges",
        "amount": 120.00,
        "category": "office supplies",
        "expense_date": "2026-06-30",
        "has_receipt": True,
    }
    result = analyze_expense(expense)
    assert result.category == "office"
    assert result.gl_code == "6300"
    assert result.cost_center == "CC-OPS"
    assert result.tax_code == "OFF-100"
    assert result.saving_insight is not None


def test_software_mapping() -> None:
    """Verifies software expense maps to GL 6400, Cost Center CC-ENG, and Tax Code SaaS-100."""
    expense = {
        "title": "GitHub Copilot licenses",
        "amount": 380.00,
        "category": "software",
        "expense_date": "2026-06-30",
        "has_receipt": True,
    }
    result = analyze_expense(expense)
    assert result.category == "software"
    assert result.gl_code == "6400"
    assert result.cost_center == "CC-ENG"
    assert result.tax_code == "SaaS-100"
    assert result.saving_insight is not None


def test_training_mapping() -> None:
    """Verifies training courses map to GL 6500, Cost Center CC-HR, and Tax Code GEN-TAX."""
    expense = {
        "title": "AWS Cloud Architect Training Course",
        "amount": 1500.00,
        "category": "training",
        "expense_date": "2026-06-30",
        "has_receipt": True,
    }
    result = analyze_expense(expense)
    assert result.category == "training"
    assert result.gl_code == "6500"
    assert result.cost_center == "CC-HR"
    assert result.tax_code == "GEN-TAX"
    assert result.saving_insight is not None
