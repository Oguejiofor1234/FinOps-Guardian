import re


class PIIGuardrail:
    """Security guardrail to detect and redact Personally Identifiable Information (PII)."""

    def __init__(self):
        # Regexes for common PII types
        self.cc_pattern = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
        self.email_pattern = re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        )
        self.phone_pattern = re.compile(
            r"\b(?:\+?\d{1,3}[- ]?)?\(?\d{3}\)?[- ]?\d{3}[- ]?\d{4}\b"
        )
        self.ssn_pattern = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

    def redact(self, text: str) -> str:
        """Redacts credit card numbers, emails, phone numbers, and SSNs from text."""
        if not text:
            return text

        redacted = self.cc_pattern.sub("[REDACTED_CC]", text)
        redacted = self.email_pattern.sub("[REDACTED_EMAIL]", redacted)
        redacted = self.phone_pattern.sub("[REDACTED_PHONE]", redacted)
        redacted = self.ssn_pattern.sub("[REDACTED_SSN]", redacted)
        return redacted

    def contains_pii(self, text: str) -> bool:
        """Returns True if any raw PII is found in the text."""
        if not text:
            return False

        return bool(
            self.cc_pattern.search(text)
            or self.email_pattern.search(text)
            or self.phone_pattern.search(text)
            or self.ssn_pattern.search(text)
        )
