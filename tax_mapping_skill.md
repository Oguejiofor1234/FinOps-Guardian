# Tax Mapping Skill Documentation

This skill maps approved corporate expense categories to standard General Ledger (GL) accounts, department cost centers, and tax deductibility codes.

## 1. Mappings Overview

| Category | GL Code | Cost Center | Tax Code | Deductibility Description |
|---|---|---|---|---|
| **meals** | `6200` | `CC-MARKETING` | `ME-50` | Meals & Entertainment (50% corporate tax deduction) |
| **travel** | `6100` | `CC-SALES` | `TRV-100` | Travel & Lodging (100% deduction) |
| **office** / **office supplies** | `6300` | `CC-OPS` | `OFF-100` | Office Supplies (100% deduction) |
| **software** | `6400` | `CC-ENG` | `SaaS-100` | Software / SaaS (100% deduction) |
| **training** | `6500` | `CC-HR` | `GEN-TAX` | Training & Development (standard review mapping) |
| **other** / **uncategorized** | `6900` | `CC-CORP` | `GEN-TAX` | General corporate expenses (standard review mapping) |

---

## 2. Tax Deductibility Codes

1. **`ME-50`**: Maps to corporate Meals & Entertainment. Only 50% is tax-deductible under standard IRS rules.
2. **`TRV-100`**: Maps to employee travel, business trips, and lodging. 100% tax-deductible.
3. **`OFF-100`**: Maps to office supplies, equipment, and consumables. 100% tax-deductible.
4. **`SaaS-100`**: Maps to software subscriptions, hosting, and cloud computing licenses. 100% tax-deductible.
5. **`GEN-TAX`**: General or uncategorized corporate expenses. Placed on standard review.
