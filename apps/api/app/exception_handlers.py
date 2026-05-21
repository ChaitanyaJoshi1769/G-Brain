"""
Global Exception Handlers

Centralized exception handling for API responses with proper error formatting,
logging, and HTTP status codes.
"""

import logging
from typing import Union

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class APIException(Exception):
    """Base exception for API errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_code: str = "UNKNOWN_ERROR",
        details: dict = None,
    ):
        """
        Initialize API exception.

        Args:
            message: Error message
            status_code: HTTP status code
            error_code: Error code for client identification
            details: Additional error details
        """
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationException(APIException):
    """Validation error."""

    def __init__(self, message: str, details: dict = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class AuthenticationException(APIException):
    """Authentication error."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTHENTICATION_ERROR",
        )


class AuthorizationException(APIException):
    """Authorization error."""

    def __init__(self, message: str = "Access forbidden"):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="AUTHORIZATION_ERROR",
        )


class ResourceNotFoundException(APIException):
    """Resource not found."""

    def __init__(self, resource: str, identifier: str = None):
        message = f"{resource} not found"
        if identifier:
            message += f" (ID: {identifier})"

        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="RESOURCE_NOT_FOUND",
            details={"resource": resource, "identifier": identifier},
        )


class ConflictException(APIException):
    """Resource conflict."""

    def __init__(self, message: str = "Resource conflict"):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="CONFLICT_ERROR",
        )


class RateLimitException(APIException):
    """Rate limit exceeded."""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_ERROR",
        )


class ExternalServiceException(APIException):
    """External service error."""

    def __init__(self, service: str, message: str = None):
        error_message = f"External service error: {service}"
        if message:
            error_message += f" - {message}"

        super().__init__(
            message=error_message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="EXTERNAL_SERVICE_ERROR",
            details={"service": service},
        )


def setup_exception_handlers(app: FastAPI) -> None:
    """
    Setup exception handlers for the FastAPI application.

    Args:
        app: FastAPI application instance
    """

    @app.exception_handler(APIException)
    async def api_exception_handler(request: Request, exc: APIException):
        """Handle custom API exceptions."""
        request_id = getattr(request.state, "request_id", "unknown")

        logger.error(
            f"[{request_id}] API Exception: {exc.error_code} - {exc.message}",
            extra={
                "request_id": request_id,
                "error_code": exc.error_code,
                "status_code": exc.status_code,
                "details": exc.details,
            },
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "details": exc.details,
                    "request_id": request_id,
                },
            },
            headers={"X-Request-ID": request_id},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        """Handle Pydantic validation errors."""
        request_id = getattr(request.state, "request_id", "unknown")

        logger.warning(
            f"[{request_id}] Validation error in {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "errors": exc.errors(),
            },
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": {
                        "errors": [
                            {
                                "loc": error["loc"],
                                "msg": error["msg"],
                                "type": error["type"],
                            }
                            for error in exc.errors()
                        ]
                    },
                    "request_id": request_id,
                },
            },
            headers={"X-Request-ID": request_id},
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
        """Handle database errors."""
        request_id = getattr(request.state, "request_id", "unknown")

        logger.error(
            f"[{request_id}] Database error: {str(exc)}",
            extra={
                "request_id": request_id,
                "error": str(exc),
            },
            exc_info=True,
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": "An error occurred while accessing the database",
                    "request_id": request_id,
                },
            },
            headers={"X-Request-ID": request_id},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle all other exceptions."""
        request_id = getattr(request.state, "request_id", "unknown")

        logger.error(
            f"[{request_id}] Unhandled exception: {str(exc)}",
            extra={
                "request_id": request_id,
                "error": str(exc),
                "type": type(exc).__name__,
            },
            exc_info=True,
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred",
                    "request_id": request_id,
                },
            },
            headers={"X-Request-ID": request_id},
        )
