"""Structured logging module for SightSense API.

Outputs JSON formatted logs for CloudWatch ingestion with automatic redaction
of sensitive parameters, authentication tokens, and private user visual payloads.
"""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any


class JSONFormatter(logging.Formatter):
    """Formats log records as structured JSON dictionaries."""

    SENSITIVE_KEYS = {
        "password",
        "secret",
        "token",
        "access_key",
        "secret_key",
        "authorization",
        "raw_image",
        "image_bytes",
        "base64_data",
    }

    def format(self, record: logging.LogRecord) -> str:
        log_payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Include custom extra context
        if hasattr(record, "request_id"):
            log_payload["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_payload["user_id"] = record.user_id
        if hasattr(record, "session_id"):
            log_payload["session_id"] = record.session_id
        if hasattr(record, "route"):
            log_payload["route"] = record.route
        if hasattr(record, "status_code"):
            log_payload["status_code"] = record.status_code
        if hasattr(record, "duration_ms"):
            log_payload["duration_ms"] = record.duration_ms
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            # Sanitize extra fields
            sanitized = {}
            for k, v in record.extra_data.items():
                if any(sens in k.lower() for sens in self.SENSITIVE_KEYS):
                    sanitized[k] = "[REDACTED]"
                else:
                    sanitized[k] = v
            log_payload["context"] = sanitized

        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_payload)


def configure_logging(level: str = "INFO") -> None:
    """Configure root logger with structured JSON handler."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level.upper())

    # Remove existing handlers
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)

    # Silence overly verbose external loggers
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return configured logger instance."""
    return logging.getLogger(name)
