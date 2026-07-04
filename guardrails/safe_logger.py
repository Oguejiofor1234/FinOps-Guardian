import logging

from guardrails.pii_guardrail import PIIGuardrail
from guardrails.secret_guardrail import SecretGuardrail


class SafeLogger:
    """A wrapper around Python's standard logger that enforces redaction of PII and secrets before writing to logs."""

    def __init__(self, logger_name: str = "finops_guardian"):
        self.logger = logging.getLogger(logger_name)
        # Ensure handlers are outputting logs to console/file
        if not self.logger.handlers:
            self.logger.setLevel(logging.INFO)
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self.pii_guard = PIIGuardrail()
        self.secret_guard = SecretGuardrail()

    def _sanitize(self, message: str) -> str:
        """Sanitizes raw log messages by redacting both secrets and PII."""
        if not isinstance(message, str):
            return message
        sanitized = self.secret_guard.redact(message)
        sanitized = self.pii_guard.redact(sanitized)
        return sanitized

    def info(self, msg: str, *args, **kwargs):
        self.logger.info(self._sanitize(msg), *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        self.logger.warning(self._sanitize(msg), *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        self.logger.error(self._sanitize(msg), *args, **kwargs)

    def debug(self, msg: str, *args, **kwargs):
        self.logger.debug(self._sanitize(msg), *args, **kwargs)
