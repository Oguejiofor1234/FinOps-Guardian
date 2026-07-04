class InjectionShield:
    """Guardrail to detect potential prompt injection attacks in user prompts."""

    def __init__(self):
        # A starter set of patterns commonly seen in adversarial prompts
        self.injection_keywords = [
            "ignore previous instructions",
            "system prompt",
            "you are now",
            "disregard",
            "override instructions",
            "jailbreak",
        ]

    def is_injection(self, text: str) -> bool:
        """Returns True if any potential prompt injection phrase is detected."""
        normalized_text = text.lower()
        for keyword in self.injection_keywords:
            if keyword in normalized_text:
                return True
        return False
