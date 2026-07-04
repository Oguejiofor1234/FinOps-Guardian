from typing import Any

import policy_rules


def calculate_risk(
    claim: dict[str, Any], history: list[dict[str, Any]]
) -> tuple[str, list[str], str, float]:
    """
    Computes the risk level, flags violations, recommends actions, and assigns confidence
    based on corporate expense compliance policies.

    Returns:
        tuple of (risk_level, reasons, recommended_action, confidence)
    """
    reasons = []
    max_score = 0.0

    amount = claim.get("amount", 0.0)
    category = claim.get("category", "")
    title = claim.get("title", "")
    expense_date = claim.get("expense_date", "")
    has_receipt = claim.get("has_receipt", False)

    # 1. Duplicate check (HIGH RISK)
    is_duplicate, duplicate_msg = policy_rules.check_duplicate_claims(claim, history)
    if is_duplicate:
        reasons.append(f"Suspected duplicate transaction: {duplicate_msg}")
        max_score = max(max_score, 1.0)

    # 2. Suspicious description / prompt injection check (HIGH RISK)
    suspicious_terms = policy_rules.check_suspicious_description(title)
    if suspicious_terms:
        reasons.append(
            f"Suspicious keyword(s) in description: {', '.join(suspicious_terms)}"
        )
        max_score = max(max_score, 1.0)

    # 3. Category authorization check (MEDIUM RISK)
    if not policy_rules.check_category_authorized(category):
        reasons.append(f"Unauthorized category: '{category}'")
        max_score = max(max_score, 0.7)

    # 4. Over limit checks (MEDIUM RISK)
    is_over, limit = policy_rules.check_over_limit(category, amount)
    if is_over:
        reasons.append(
            f"{category.capitalize()} category limit exceeded: Spent ${amount:.2f} (Limit is ${limit:.2f})"
        )
        max_score = max(max_score, 0.6)

    # 5. Weekend checks (MEDIUM RISK)
    if policy_rules.check_weekend(expense_date):
        # Allow if travel itinerary exists (flagged in context)
        has_itinerary = claim.get("has_itinerary", False)
        if not has_itinerary:
            reasons.append(
                f"Weekend transaction on {expense_date} without associated travel itinerary"
            )
            max_score = max(max_score, 0.4)

    # 6. Receipt checks (MEDIUM RISK)
    if policy_rules.check_receipt_required(amount, has_receipt):
        reasons.append(
            f"Missing receipt for transaction exceeding $25.00 (Spent ${amount:.2f})"
        )
        max_score = max(max_score, 0.5)

    # Resolve risk level and recommended actions
    if max_score >= 0.9:
        risk_level = "HIGH"
        recommended_action = "REJECT"
    elif max_score >= 0.4:
        risk_level = "MEDIUM"
        recommended_action = "REVIEW"
    else:
        risk_level = "LOW"
        recommended_action = "APPROVE"

    # Standard rule engine confidence is extremely high (1.0)
    # If the description has suspicious keywords, lower it slightly to account for semantic variations
    confidence = 1.0
    if suspicious_terms and not is_duplicate:
        confidence = 0.95

    return risk_level, reasons, recommended_action, confidence
