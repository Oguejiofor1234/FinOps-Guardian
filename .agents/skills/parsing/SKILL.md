---
name: parsing
description: Guidelines for parsing raw corporate expense claim descriptions, dates, amounts, and metadata.
---

# Expense Claim Parsing Guidelines

This skill guides the agent or developer on how to extract structural parameters from a raw, unstructured corporate expense claim text.

## Extraction Fields
1. **Merchant / Vendor Name**: The business name where transaction took place.
2. **Claim Amount**: The numerical currency value.
3. **Transaction Date**: Calendar date (format: YYYY-MM-DD).
4. **Expense Category**: Map raw items to one of:
   - Meals & Entertainment
   - Travel & Lodging
   - Office Supplies
   - Software / SaaS
   - Other
