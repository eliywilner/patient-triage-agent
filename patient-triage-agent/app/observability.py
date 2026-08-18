"""Observability, Structured JSON Logging, OpenTelemetry Tracing, and PII Redaction Module.

This module provides enterprise-grade observability for the Patient Triage Agent,
including structured JSON log formatting, intent vs. outcome logging,
OpenTelemetry distributed tracing, and automated PII redaction.
"""

import json
import logging
import re
from typing import Any, Dict, Optional

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

    provider = TracerProvider()
    processor = BatchSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer("patient-triage-agent")
except Exception:
    tracer = None


class PIIRedactor(logging.Filter):
    """Filter that redacts personally identifiable information (PII) from log records."""

    SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
    PHONE_PATTERN = re.compile(r"\b(\+\d{1,2}\s?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b")
    EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")

    def redact(self, text: str) -> str:
        """Redacts sensitive PII fields from text string.

        Args:
            text (str): Input text containing potential PII.

        Returns:
            str: Text with PII patterns replaced by [REDACTED].
        """
        if not isinstance(text, str):
            return text
        text = self.SSN_PATTERN.sub("[REDACTED_SSN]", text)
        text = self.PHONE_PATTERN.sub("[REDACTED_PHONE]", text)
        text = self.EMAIL_PATTERN.sub("[REDACTED_EMAIL]", text)
        return text

    def filter(self, record: logging.LogRecord) -> bool:
        """Applies PII redaction filter to a log record.

        Args:
            record (logging.LogRecord): Log record to filter.

        Returns:
            bool: Always True (modifies record in place).
        """
        if isinstance(record.msg, str):
            record.msg = self.redact(record.msg)
        if hasattr(record, "args") and isinstance(record.args, dict):
            record.args = {k: self.redact(v) if isinstance(v, str) else v for k, v in record.args.items()}
        return True


class JSONFormatter(logging.Formatter):
    """Custom formatter emitting logs as structured JSON strings."""

    def format(self, record: logging.LogRecord) -> str:
        """Formats log record as a structured JSON object.

        Args:
            record (logging.LogRecord): Log event.

        Returns:
            str: JSON string with structured fields.
        """
        log_entry: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if hasattr(record, "intent"):
            log_entry["intent"] = getattr(record, "intent")
        if hasattr(record, "outcome"):
            log_entry["outcome"] = getattr(record, "outcome")
        if hasattr(record, "session_id"):
            log_entry["session_id"] = getattr(record, "session_id")
        if hasattr(record, "trace_id"):
            log_entry["trace_id"] = getattr(record, "trace_id")

        return json.dumps(log_entry)


def get_structured_logger(name: str = "patient_triage") -> logging.Logger:
    """Configures and returns a structured JSON logger with PII redaction.

    Args:
        name (str): Logger name identifier.

    Returns:
        logging.Logger: Configured structured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        handler.addFilter(PIIRedactor())
        logger.addHandler(handler)
    return logger


structured_logger = get_structured_logger()


def log_intent_vs_outcome(intent: str, outcome: str, session_id: Optional[str] = None) -> None:
    """Logs the captured intent vs. final agent outcome.

    Args:
        intent (str): The user/patient's intent or query text.
        outcome (str): The agent's clinical triage outcome decision.
        session_id (Optional[str]): Active ADK session identifier.
    """
    extra = {
        "intent": intent,
        "outcome": outcome,
        "session_id": session_id or "unknown-session",
    }
    structured_logger.info("Captured Intent vs. Outcome event", extra=extra)

