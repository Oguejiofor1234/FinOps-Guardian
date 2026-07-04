---
name: pii-sanitization
description: Directives and best practices for sanitizing Personally Identifiable Information (PII) like credit cards and SSNs.
---

# PII Sanitization Guidelines

Guidelines for filtering out sensitive user data before database storage or LLM routing:

1. **Credit Cards**: Match any 13-16 digit patterns separated by spaces or dashes, and replace with `[REDACTED_CARD]`.
2. **Social Security Numbers (SSNs)**: Match format `XXX-XX-XXXX` and replace with `[REDACTED_SSN]`.
3. **Personal Emails & Phone Numbers**: Sanitize where appropriate if the merchant is a personal contact.
