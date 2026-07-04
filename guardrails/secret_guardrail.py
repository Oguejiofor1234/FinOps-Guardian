import re


class SecretGuardrail:
    """Security guardrail to redact credentials, API keys, and passwords from text."""

    def __init__(self):
        # Patterns for API keys and passwords
        # 1. Google API keys: AIzaSy followed by 33-35 alphanumeric/underscore/dash chars
        self.gcp_key_pattern = re.compile(r"\bAIzaSy[A-Za-z0-9_-]{33,35}\b")
        # 2. Generic API keys (e.g. sk-proj-... or bearer tokens)
        self.generic_key_pattern = re.compile(
            r"\b(?:sk-[a-zA-Z0-9_-]{15,})|(?:bearer\s+[a-zA-Z0-9_\-\.]{15,})\b",
            re.IGNORECASE,
        )
        # 3. Passwords in configuration strings (e.g. password="...", secret="...")
        self.pwd_config_pattern = re.compile(
            r'\b(password|pwd|secret|api_key|token)\s*=\s*["\']([^"\']+)["\']',
            re.IGNORECASE,
        )

    def redact(self, text: str) -> str:
        """Redacts secrets, API keys, and password patterns from text."""
        if not text:
            return text

        # Redact GCP keys
        redacted = self.gcp_key_pattern.sub("[REDACTED_GCP_KEY]", text)
        # Redact generic/OpenAI keys
        redacted = self.generic_key_pattern.sub("[REDACTED_API_KEY]", redacted)
        # Redact configuration assignment passwords
        redacted = self.pwd_config_pattern.sub(r'\1="[REDACTED_SECRET]"', redacted)

        return redacted

    def contains_secrets(self, text: str) -> bool:
        """Returns True if any credentials or secret keys are found."""
        if not text:
            return False

        return bool(
            self.gcp_key_pattern.search(text)
            or self.generic_key_pattern.search(text)
            or self.pwd_config_pattern.search(text)
        )
