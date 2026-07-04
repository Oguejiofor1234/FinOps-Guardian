# Auditor Agent Design Report

This report summarizes the design, policy logic, risk scoring matrix, and structured outcomes of the **Auditor Agent** in the **FinOps Guardian** workspace.

---

## 1. Responsibilities & Architecture

The Auditor Agent is a specialized sub-agent invoked by the Root Compliance Coordinator during the `run_audit` step. It performs deep compliance checks and calculates a risk score using a hybrid model: deterministic rule calculations combined with LLM analysis.

---

## 2. Policy Rule Checkers (`policy_rules.py`)

Compliance checks are defined deterministically in `policy_rules.py` to ensure complete accuracy:

1. **Daily Meals Limit**: Flags meal expenses exceeding **$75.00**.
2. **Software Transaction Limit**: Flags software purchases exceeding **$500.00**.
3. **Weekend Transactions**: Flags expenses occurring on Saturday or Sunday unless `has_itinerary` is `True`.
4. **Missing Receipts**: Flags any transaction exceeding **$25.00** where `has_receipt` is `False`.
5. **Unauthorized Categories**: Flags categories other than `meals`, `travel`, `office`, or `software`.
6. **Duplicate Claims**: Scans historical claims within a **48-hour window**. Flags as a duplicate if the title, amount, and category match a past claim.
7. **Suspicious Keyword Check**: Scans description for terms associated with rules bypass (e.g., "ignore instructions", "gift card").

---

## 3. Risk Scoring & Recommendations (`risk_score.py`)

The scoring engine aggregates policy violations into risk scores:

| Risk Level | Recommended Action | Condition / Trigger |
|---|---|---|
| **LOW** | `APPROVE` | Zero policy violations. |
| **MEDIUM** | `REVIEW` | Missing receipt, weekend transaction, or over-limit meals/software. |
| **HIGH** | `REJECT` | Duplicate claims, suspicious keywords, or prompt injection threats. |

---

## 4. Structured Output (`AuditResult`)

The Auditor Agent returns structured outputs matching the `AuditResult` Pydantic schema:

- `risk_level`: The computed risk level (`LOW`, `MEDIUM`, or `HIGH`).
- `reasons`: List of strings explaining each violation found.
- `recommended_action`: Action recommended (`APPROVE`, `REVIEW`, or `REJECT`).
- `confidence`: Confidence score between `0.0` and `1.0`.
