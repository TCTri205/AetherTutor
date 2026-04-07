"""
Custom exception hierarchy for standardized error handling.
"""
from typing import Optional
from http import HTTPStatus


class AppError(Exception):
    """
    Base application error with error code and details.
    All custom exceptions should inherit from this class.
    """
    def __init__(
        self,
        message: str,
        error_code: str = "APP_ERROR",
        status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR,
        details: Optional[dict] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}


class BusinessLogicError(AppError):
    """
    Errors related to business logic violations.
    Examples: Invalid state, duplicate entry, resource not found.
    """
    pass


class ValidationError(BusinessLogicError):
    """
    Input validation errors.
    Examples: Invalid file type, missing required field, out of range value.
    """
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=HTTPStatus.BAD_REQUEST,
            details=details
        )


class ResourceNotFoundError(BusinessLogicError):
    """
    Resource not found errors.
    """
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            message=f"{resource} not found: {identifier}",
            error_code="RESOURCE_NOT_FOUND",
            status_code=HTTPStatus.NOT_FOUND,
            details={"resource": resource, "identifier": identifier}
        )


class DuplicateResourceError(BusinessLogicError):
    """
    Duplicate resource errors.
    """
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(
            message=message,
            error_code="DUPLICATE_RESOURCE",
            status_code=HTTPStatus.CONFLICT,
            details=details
        )


class PermanentProcessingError(AppError):
    """
    Non-recoverable errors during document processing.
    Examples: Corrupt PDF, encrypted file, unsupported format.
    Worker will NOT retry when this error is raised.
    """
    def __init__(self, message: str):
        super().__init__(
            message=message,
            error_code="PERMANENT_PROCESSING_ERROR",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY
        )


class InfrastructureError(AppError):
    """
    External service/infrastructure failures.
    Examples: Database connection lost, Redis down, LLM service unavailable.
    These errors MAY be retried depending on the context.
    """
    def __init__(self, message: str, service: str, details: Optional[dict] = None):
        super().__init__(
            message=message,
            error_code="INFRASTRUCTURE_ERROR",
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            details={"service": service, **(details or {})}
        )


class RateLimitError(BusinessLogicError):
    """
    Rate limit exceeded errors.
    """
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=HTTPStatus.TOO_MANY_REQUESTS
        )
