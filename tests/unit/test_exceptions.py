"""
Unit tests for custom exceptions.
"""
import pytest
from http import HTTPStatus
from app.core.exceptions import (
    AppError,
    BusinessLogicError,
    ValidationError,
    ResourceNotFoundError,
    DuplicateResourceError,
    PermanentProcessingError,
    InfrastructureError,
    RateLimitError
)


class TestCustomExceptions:
    """Test custom exception hierarchy."""
    
    def test_app_error_defaults(self):
        """Test AppError with default values."""
        error = AppError("Test error")
        
        assert error.message == "Test error"
        assert error.error_code == "APP_ERROR"
        assert error.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        assert error.details == {}
    
    def test_app_error_with_details(self):
        """Test AppError with custom details."""
        error = AppError(
            "Test error",
            error_code="CUSTOM_ERROR",
            status_code=HTTPStatus.BAD_REQUEST,
            details={"field": "value"}
        )
        
        assert error.message == "Test error"
        assert error.error_code == "CUSTOM_ERROR"
        assert error.status_code == HTTPStatus.BAD_REQUEST
        assert error.details == {"field": "value"}
    
    def test_validation_error(self):
        """Test ValidationError."""
        error = ValidationError("Invalid input", details={"field": "email"})
        
        assert error.message == "Invalid input"
        assert error.error_code == "VALIDATION_ERROR"
        assert error.status_code == HTTPStatus.BAD_REQUEST
        assert error.details == {"field": "email"}
    
    def test_resource_not_found_error(self):
        """Test ResourceNotFoundError."""
        error = ResourceNotFoundError("Document", "123")
        
        assert "Document not found: 123" in error.message
        assert error.error_code == "RESOURCE_NOT_FOUND"
        assert error.status_code == HTTPStatus.NOT_FOUND
        assert error.details == {"resource": "Document", "identifier": "123"}
    
    def test_duplicate_resource_error(self):
        """Test DuplicateResourceError."""
        error = DuplicateResourceError("Document already exists")
        
        assert error.message == "Document already exists"
        assert error.error_code == "DUPLICATE_RESOURCE"
        assert error.status_code == HTTPStatus.CONFLICT
    
    def test_permanent_processing_error(self):
        """Test PermanentProcessingError."""
        error = PermanentProcessingError("Corrupt PDF file")
        
        assert error.message == "Corrupt PDF file"
        assert error.error_code == "PERMANENT_PROCESSING_ERROR"
        assert error.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    
    def test_infrastructure_error(self):
        """Test InfrastructureError."""
        error = InfrastructureError("Connection failed", "redis")
        
        assert error.message == "Connection failed"
        assert error.error_code == "INFRASTRUCTURE_ERROR"
        assert error.status_code == HTTPStatus.SERVICE_UNAVAILABLE
        assert error.details == {"service": "redis"}
    
    def test_rate_limit_error(self):
        """Test RateLimitError."""
        error = RateLimitError()
        
        assert error.message == "Rate limit exceeded"
        assert error.error_code == "RATE_LIMIT_EXCEEDED"
        assert error.status_code == HTTPStatus.TOO_MANY_REQUESTS
    
    def test_exception_inheritance(self):
        """Test that all exceptions inherit from Exception."""
        errors = [
            AppError("test"),
            ValidationError("test"),
            ResourceNotFoundError("test", "123"),
            DuplicateResourceError("test"),
            PermanentProcessingError("test"),
            InfrastructureError("test", "redis"),
            RateLimitError()
        ]
        
        for error in errors:
            assert isinstance(error, Exception)
            assert isinstance(error, AppError)
    
    def test_business_logic_error_inheritance(self):
        """Test business logic errors inherit from AppError."""
        errors = [
            ValidationError("test"),
            ResourceNotFoundError("test", "123"),
            DuplicateResourceError("test"),
            RateLimitError()
        ]
        
        for error in errors:
            assert isinstance(error, BusinessLogicError)
