import re


class PromptInjectionGuardrail:
    """Security guardrail to block prompt injection and jailbreak attempts."""

    def __init__(self):
        # Common phrases used in prompt injection attacks
        self.injection_keywords = [
            "ignore previous rules",
            "ignore previous instructions",
            "ignore compliance rules",
            "disregard policy",
            "override instructions",
            "you are now an",
            "jailbreak",
            "system prompt",
            "output only '[bypassed]'",
            "bypass compliance",
        ]

        # Build regex for case-insensitive keyword matching
        pattern_str = "|".join(re.escape(k) for k in self.injection_keywords)
        self.injection_regex = re.compile(rf"\b(?:{pattern_str})\b", re.IGNORECASE)

    def is_injection(self, text: str) -> bool:
        """Checks if the user text contains any known prompt injection keywords or bypass attempts."""
        if not text:
            return False

        # Check standard keyword list
        if self.injection_regex.search(text):
            return True

        # Additional heuristic: checking if user tells the model to output specific keywords like '[bypassed]'
        if "[bypassed]" in text.lower() or (
            "bypassed" in text.lower() and "ignore" in text.lower()
        ):
            return True

        return False
