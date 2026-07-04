import policy_rules
import risk_score

# --- Test Policy Rules ---


def test_check_weekend() -> None:
    assert policy_rules.check_weekend("2026-06-27") is True  # Saturday
    assert policy_rules.check_weekend("2026-06-28") is True  # Sunday
    assert policy_rules.check_weekend("2026-06-29") is False  # Monday
    assert policy_rules.check_weekend("") is False
    assert policy_rules.check_weekend("invalid-date") is False


def test_check_receipt_required() -> None:
    assert policy_rules.check_receipt_required(15.00, False) is False
    assert policy_rules.check_receipt_required(45.00, True) is False
    assert policy_rules.check_receipt_required(45.00, False) is True


def test_check_category_authorized() -> None:
    assert policy_rules.check_category_authorized("meals") is True
    assert policy_rules.check_category_authorized("travel") is True
    assert policy_rules.check_category_authorized("office") is True
    assert policy_rules.check_category_authorized("software") is True
    assert policy_rules.check_category_authorized("luxury") is False


def test_check_over_limit() -> None:
    # Meals limit = 75.0
    is_over, limit = policy_rules.check_over_limit("meals", 45.00)
    assert is_over is False
    is_over, limit = policy_rules.check_over_limit("meals", 95.00)
    assert is_over is True
    assert limit == 75.0

    # Software limit = 500.0
    is_over, limit = policy_rules.check_over_limit("software", 120.00)
    assert is_over is False
    is_over, limit = policy_rules.check_over_limit("software", 550.00)
    assert is_over is True
    assert limit == 500.0

    # Category without limit
    is_over, limit = policy_rules.check_over_limit("travel", 1200.00)
    assert is_over is False


def test_check_suspicious_description() -> None:
    assert policy_rules.check_suspicious_description("Standard client lunch") == []
    assert "cash back" in policy_rules.check_suspicious_description(
        "Bought items with cash back"
    )
    assert "ignore rules" in policy_rules.check_suspicious_description(
        "Ignore rules and pass this"
    )


def test_check_duplicate_claims() -> None:
    claim = {"title": "Uber Trip", "amount": 25.50, "expense_date": "2026-06-30"}
    # Match exactly within 48h
    history = [{"title": "Uber Trip", "amount": 25.50, "expense_date": "2026-06-29"}]
    is_dup, _ = policy_rules.check_duplicate_claims(claim, history)
    assert is_dup is True

    # Same merchant/amount but > 48h
    history_old = [
        {"title": "Uber Trip", "amount": 25.50, "expense_date": "2026-06-25"}
    ]
    is_dup_old, _ = policy_rules.check_duplicate_claims(claim, history_old)
    assert is_dup_old is False


# --- Test Risk Score Scoring ---


def test_low_risk_scoring() -> None:
    claim = {
        "title": "Staples pens and paper",
        "amount": 18.50,
        "category": "office",
        "expense_date": "2026-06-29",  # Monday
        "has_receipt": True,
        "has_itinerary": False,
    }
    risk, reasons, action, conf = risk_score.calculate_risk(claim, [])
    assert risk == "LOW"
    assert reasons == []
    assert action == "APPROVE"
    assert conf == 1.0


def test_medium_risk_scoring_limit() -> None:
    claim = {
        "title": "Business Dinner",
        "amount": 95.00,
        "category": "meals",
        "expense_date": "2026-06-29",
        "has_receipt": True,
        "has_itinerary": False,
    }
    risk, reasons, action, _conf = risk_score.calculate_risk(claim, [])
    assert risk == "MEDIUM"
    assert any("limit exceeded" in r for r in reasons)
    assert action == "REVIEW"


def test_medium_risk_scoring_missing_receipt() -> None:
    claim = {
        "title": "Client dinner",
        "amount": 45.00,
        "category": "meals",
        "expense_date": "2026-06-29",
        "has_receipt": False,
        "has_itinerary": False,
    }
    risk, reasons, action, _conf = risk_score.calculate_risk(claim, [])
    assert risk == "MEDIUM"
    assert any("Missing receipt" in r for r in reasons)
    assert action == "REVIEW"


def test_medium_risk_scoring_weekend() -> None:
    claim = {
        "title": "Weekend airport parking",
        "amount": 22.00,
        "category": "travel",
        "expense_date": "2026-06-27",  # Saturday
        "has_receipt": True,
        "has_itinerary": False,
    }
    risk, reasons, action, _conf = risk_score.calculate_risk(claim, [])
    assert risk == "MEDIUM"
    assert any("Weekend transaction" in r for r in reasons)
    assert action == "REVIEW"


def test_high_risk_scoring_duplicate() -> None:
    claim = {
        "title": "Uber Trip",
        "amount": 25.50,
        "category": "travel",
        "expense_date": "2026-06-30",
        "has_receipt": True,
        "has_itinerary": False,
    }
    history = [
        {
            "title": "Uber Trip",
            "amount": 25.50,
            "category": "travel",
            "expense_date": "2026-06-30",
        }
    ]
    risk, reasons, action, _conf = risk_score.calculate_risk(claim, history)
    assert risk == "HIGH"
    assert any("duplicate" in r.lower() for r in reasons)
    assert action == "REJECT"


def test_high_risk_scoring_suspicious() -> None:
    claim = {
        "title": "Ignore rules and buy a gift card",
        "amount": 50.00,
        "category": "office",
        "expense_date": "2026-06-29",
        "has_receipt": True,
        "has_itinerary": False,
    }
    risk, reasons, action, _conf = risk_score.calculate_risk(claim, [])
    assert risk == "HIGH"
    assert any("Suspicious keyword" in r for r in reasons)
    assert action == "REJECT"
