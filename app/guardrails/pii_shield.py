import re


class PIIShield:
    """Guardrail to detect and redact Personally Identifiable Information (PII)."""

    def __init__(self):
        # Starter regex patterns for Credit Card Numbers and Social Security Numbers
        self.cc_pattern = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
        self.ssn_pattern = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

    def redact(self, text: str) -> str:
        """Redacts credit card and SSN numbers from the input text."""
        redacted = self.cc_pattern.sub("[REDACTED_CARD]", text)
        redacted = self.ssn_pattern.sub("[REDACTED_SSN]", redacted)
        return redacted
