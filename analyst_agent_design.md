# Analyst Agent Design Report

This report summarizes the design, implementation, and verification of the Analyst Agent and the category mapping layer for **FinOps Guardian**.

---

## 1. Mappings Configuration

We created a structured mapping configuration in `category_mapping.json` that defines General Ledger (GL) accounts, department Cost Centers, and tax codes for approved categories:

| Category | GL Code | Cost Center | Tax Code | Description |
|---|---|---|---|---|
| **meals** | `6200` | `CC-MARKETING` | `ME-50` | Meals & Entertainment (50% corporate deduction) |
| **travel** | `6100` | `CC-SALES` | `TRV-100` | Travel & Lodging (100% deduction) |
| **office** | `6300` | `CC-OPS` | `OFF-100` | Office Supplies (100% deduction) |
| **software** | `6400` | `CC-ENG` | `SaaS-100` | Software / SaaS (100% deduction) |
| **training** | `6500` | `CC-HR` | `GEN-TAX` | Training & Development (standard review mapping) |
| **other** | `6900` | `CC-CORP` | `GEN-TAX` | General Expenses (standard review mapping) |

---

## 2. Analyst Agent & Logic Integration

- **Agent definition (`agents/analyst_agent.py`)**: Implements the ADK `Agent` wrapping the Gemini model. Utilizes a structured `AnalysisResult` output schema to dynamically yield cost-saving insights and tax deductibility explanations.
- **Workflow integration**: Refactored the `run_analyst` node in `agents/root_agent.py` to invoke the analyst's `analyze_expense` function. Updates the execution state with GL codes, cost centers, tax codes, deductibility rules, and savings insights.
- **Deductibility Documentation**: Detailed guidelines are recorded in the `tax_mapping_skill.md` file at the root of the workspace.

---

## 3. Automated Test Suite

We implemented dedicated unit tests in `tests/unit/test_analyst_agent.py` to assert correct parameter mapping for all five target categories (travel, meals, office supplies, software, and training), alongside checking dynamically generated insights.

---

## 4. Run & Test Status

All 39 unit and integration tests, as well as code quality linters, pass 100% cleanly:
```bash
All checks passed!
======================= 39 passed, 4 warnings in 14.68s ========================
```
