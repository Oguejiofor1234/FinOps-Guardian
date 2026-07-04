---
name: duplicate-detection
description: Guidelines to detect double submissions and duplicate expense fraud patterns.
---

# Duplicate Expense Detection Guidelines

Guidelines to prevent expense double-dipping:

- **Matching Properties**: Flag if user, merchant name, and amount match exactly.
- **Window**: Limit scan to claims submitted within a 48-hour range.
- **Fraud Escalation**: If double-dipping is identified, immediately label it as high risk, skip HITL, and route straight to security alerts.
