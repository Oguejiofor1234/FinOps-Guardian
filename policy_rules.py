from datetime import date, datetime
from typing import Any

# Authorized expense categories
AUTHORIZED_CATEGORIES = {"meals", "travel", "office", "software"}

# Daily/transaction policy limits
CATEGORY_LIMITS = {"meals": 75.00, "software": 500.00}

# Suspicious keywords that signal high compliance risk or fraud
SUSPICIOUS_KEYWORDS = {
    "cash back",
    "gift card",
    "bribe",
    "personal fee",
    "kickback",
    "lobbying",
    "override",
    "ignore rules",
    "ignore instructions",
}


def check_weekend(expense_date_str: Any) -> bool:
    """Returns True if the expense date falls on a weekend (Saturday or Sunday)."""
    if not expense_date_str:
        return False
    try:
        if isinstance(expense_date_str, (date, datetime)):
            dt = expense_date_str
        else:
            date_part = str(expense_date_str).split(" ")[0].split("T")[0]
            y, m, d = map(int, date_part.split("-"))
            dt = date(y, m, d)
        return dt.weekday() in (5, 6)  # 5=Saturday, 6=Sunday
    except Exception:
        return False


def check_receipt_required(amount: float, has_receipt: bool) -> bool:
    """Returns True if the amount is greater than $25.00 and no receipt is attached."""
    return amount > 25.00 and not has_receipt


def check_category_authorized(category: str) -> bool:
    """Returns True if the category is authorized under company policy."""
    return category.lower() in AUTHORIZED_CATEGORIES


def check_over_limit(category: str, amount: float) -> tuple[bool, float]:
    """Returns (is_over_limit, limit_amount) for the given category."""
    cat_lower = category.lower()
    if cat_lower in CATEGORY_LIMITS:
        limit = CATEGORY_LIMITS[cat_lower]
        return amount > limit, limit
    return False, 0.0


def check_suspicious_description(title: str) -> list[str]:
    """Checks the description/title for suspicious keywords and returns matched words."""
    if not title:
        return []
    title_lower = title.lower()
    matches = []
    for keyword in SUSPICIOUS_KEYWORDS:
        if keyword in title_lower:
            matches.append(keyword)
    return matches


def check_duplicate_claims(
    current_claim: dict[str, Any], history: list[dict[str, Any]]
) -> tuple[bool, str | None]:
    """
    Scans historical claims for duplicate submissions within a 48-hour window.
    A duplicate is defined as having the same user, merchant/title, and amount.
    """
    current_title = current_claim.get("title", "").strip().lower()
    current_amount = current_claim.get("amount", 0.0)
    current_date = current_claim.get("expense_date", "")

    if "duplicate" in current_title:
        return True, "Suspected duplicate keyword in title"

    if not current_date:
        return False, None

    try:
        if isinstance(current_date, (date, datetime)):
            current_dt = datetime(
                current_date.year, current_date.month, current_date.day
            )
        else:
            date_part = str(current_date).split(" ")[0].split("T")[0]
            current_dt = datetime.strptime(date_part, "%Y-%m-%d")
    except Exception:
        return False, None

    for past_claim in history:
        past_title = past_claim.get("title", "").strip().lower()
        past_amount = past_claim.get("amount", 0.0)
        past_date = past_claim.get("expense_date", "")

        if not past_date:
            continue

        try:
            if isinstance(past_date, (date, datetime)):
                past_dt = datetime(past_date.year, past_date.month, past_date.day)
            else:
                date_part = str(past_date).split(" ")[0].split("T")[0]
                past_dt = datetime.strptime(date_part, "%Y-%m-%d")
        except Exception:
            continue

        # Check if title and amount match exactly
        if current_title == past_title and abs(current_amount - past_amount) < 0.01:
            # Check if within 48-hour window (172800 seconds)
            time_diff = abs((current_dt - past_dt).total_seconds())
            if time_diff <= 172800:
                return (
                    True,
                    f"Matches past claim on {past_date} for ${past_amount:.2f}",
                )

    return False, None
