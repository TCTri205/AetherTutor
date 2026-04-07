"""
Unit tests for logging configuration.
"""
import pytest
import logging
import json
from app.logging_config import (
    JSONFormatter,
    CorrelationIdFilter,
    setup_logging,
    get_logger,
    correlation_filter,
    set_correlation_id,
    get_correlation_id,
)


class TestCorrelationIdContextVar:
    """Test correlation ID context variables."""

    def test_set_and_get_correlation_id(self):
        """Test setting and getting correlation ID."""
        set_correlation_id("test-123")
        assert get_correlation_id() == "test-123"

    def test_default_correlation_id(self):
        """Test default correlation ID is None."""
        # Reset to default
        set_correlation_id(None)
        assert get_correlation_id() is None


class TestCorrelationIdFilter:
    """Test correlation ID filter."""

    def test_filter_adds_correlation_id(self):
        """Test that filter adds correlation_id to record from ContextVar."""
        set_correlation_id("test-456")

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )

        result = correlation_filter.filter(record)

        assert result is True
        assert record.correlation_id == "test-456"

    def test_filter_default_correlation_id(self):
        """Test default correlation ID when not set."""
        set_correlation_id(None)

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )

        correlation_filter.filter(record)

        assert record.correlation_id == "no-correlation-id"


class TestJSONFormatter:
    """Test JSON log formatter."""
    
    def test_format_basic(self):
        """Test basic JSON formatting."""
        formatter = JSONFormatter()
        
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test log message",
            args=(),
            exc_info=None
        )
        record.correlation_id = "corr-789"
        record.funcName = "test_function"
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "test_logger"
        assert log_data["message"] == "Test log message"
        assert log_data["correlation_id"] == "corr-789"
        assert log_data["line"] == 42
        assert "timestamp" in log_data
    
    def test_format_with_exception(self):
        """Test JSON formatting with exception info."""
        formatter = JSONFormatter()
        
        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Error occurred",
            args=(),
            exc_info=(ValueError, ValueError("Test error"), None)
        )
        record.funcName = "test_function"
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert "exception" in log_data
        assert log_data["exception"]["type"] == "ValueError"
        assert log_data["exception"]["message"] == "Test error"
    
    def test_format_with_extra(self):
        """Test JSON formatting with extra fields."""
        formatter = JSONFormatter()

        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=5,
            msg="Test with extra",
            args=(),
            exc_info=None
        )
        record.funcName = "test_function"
        # Set extra fields directly on record (how logging.log(..., extra={}) works)
        record.doc_id = "123"
        record.user_id = "456"

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        # Extra fields should be nested under "extra" key
        assert "extra" in log_data
        assert log_data["extra"]["doc_id"] == "123"
        assert log_data["extra"]["user_id"] == "456"


class TestSetupLogging:
    """Test logging setup."""

    def setup_method(self):
        """Clear handlers and reset correlation context before each test."""
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        set_correlation_id(None)

    def test_setup_logging_info_level(self):
        """Test setup with INFO level."""
        setup_logging(level="INFO")

        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

    def test_setup_logging_debug_level(self):
        """Test setup with DEBUG level."""
        setup_logging(level="DEBUG")

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_setup_logging_json_format(self):
        """Test setup with JSON formatting."""
        # Ensure clean state so handler with JSONFormatter gets added
        root_logger = logging.getLogger()
        root_logger.handlers.clear()

        setup_logging(level="INFO", json_format=True)

        assert root_logger.level == logging.INFO
        # Check that at least one handler has JSONFormatter
        has_json_formatter = any(
            isinstance(h.formatter, JSONFormatter)
            for h in root_logger.handlers
            if hasattr(h, 'formatter') and h.formatter is not None
        )
        assert has_json_formatter, "No handler with JSONFormatter found"

    def test_setup_logging_is_idempotent(self):
        """Test that calling setup_logging multiple times doesn't add duplicate handlers."""
        setup_logging(level="INFO")
        handler_count_after_first = len(logging.getLogger().handlers)

        setup_logging(level="INFO")
        setup_logging(level="INFO")

        assert len(logging.getLogger().handlers) == handler_count_after_first


class TestGetLogger:
    """Test logger retrieval."""

    def test_get_logger_returns_logger(self):
        """Test that get_logger returns a standard Logger."""
        setup_logging(level="INFO")
        logger = get_logger("test_module")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"
