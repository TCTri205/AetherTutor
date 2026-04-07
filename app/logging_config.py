"""
Logging configuration with structured logging and correlation IDs.
Uses contextvars for thread-safe/async-safe per-request correlation tracking.
"""
import logging
import uuid
import json
from contextvars import ContextVar
from typing import Any, Dict, Optional
from datetime import datetime, timezone


# ContextVar for async-safe, thread-safe per-request correlation ID
_correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID from context."""
    return _correlation_id.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID for the current context."""
    _correlation_id.set(correlation_id)


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.
    Adds correlation_id, timestamp, and extra context.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add correlation ID from context
        corr_id = getattr(record, "correlation_id", None)
        if corr_id:
            log_data["correlation_id"] = corr_id

        # Add exception info if present
        if record.exc_info and record.exc_info[0] is not None:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
            }

        # Add extra fields (excluding standard ones)
        extra_fields = {
            k: v for k, v in record.__dict__.items()
            if k not in {
                "name", "msg", "args", "created", "relativeCreated",
                "exc_info", "exc_text", "stack_info", "levelname",
                "levelno", "pathname", "filename", "module", "funcName",
                "lineno", "thread", "threadName", "process", "processName",
                "message", "correlation_id", "extra",
            }
        }
        if extra_fields:
            log_data["extra"] = extra_fields

        return json.dumps(log_data, default=str)


class CorrelationIdFilter(logging.Filter):
    """
    Logging filter that adds correlation_id from ContextVar to log records.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id() or "no-correlation-id"
        return True


# Create global filter instance
correlation_filter = CorrelationIdFilter()


def setup_logging(level: str = "INFO", json_format: bool = False) -> None:
    """
    Configure application-wide logging. Idempotent - safe to call multiple times.
    Always sets the root logger level, but only adds handler once.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: If True, use JSON formatting for production
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    root_logger = logging.getLogger()

    # Always update the root logger level
    root_logger.setLevel(log_level)

    # Only add handler once - use a flag on the logger instead of checking handler types.
    # Also re-check if handlers were cleared externally (e.g., in tests).
    if getattr(root_logger, "_aethertutor_logging_configured", False) and root_logger.handlers:
        return

    # Create handler
    handler = logging.StreamHandler()
    handler.setLevel(log_level)

    # Add correlation ID filter
    handler.addFilter(correlation_filter)

    # Set formatter based on environment
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s | correlation_id=%(correlation_id)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Mark as configured to prevent duplicate handlers on subsequent calls
    root_logger._aethertutor_logging_configured = True

    # Configure third-party loggers
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("arq").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """
    Get a standard logger. Correlation ID is automatically added via
    CorrelationIdFilter on the handler (reads from ContextVar).

    Usage:
        logger = get_logger(__name__)
        logger.info("Processing document", extra={"doc_id": "123"})
    """
    return logging.getLogger(name)
