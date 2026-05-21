"""
Custom Middleware for G-Brain API

Implements request tracking, logging, error handling, and cross-cutting concerns.
"""

import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Add unique request ID to each request for tracing.

    Adds X-Request-ID header if not present, enabling end-to-end request tracking.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with request ID."""
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))

        # Store in request state for use in handlers
        request.state.request_id = request_id
        request.state.start_time = time.time()

        # Process request
        response = await call_next(request)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Log all incoming requests and responses.

    Logs request method, path, status code, and processing time.
    """

    EXCLUDED_PATHS = {"/health", "/healthz", "/docs", "/openapi.json"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response."""
        # Skip logging for certain paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        start_time = time.time()
        request_id = getattr(request.state, "request_id", "unknown")

        # Log request
        logger.info(
            f"[{request_id}] {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_string": request.url.query,
            },
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate processing time
            process_time = time.time() - start_time

            # Log response
            logger.info(
                f"[{request_id}] {request.method} {request.url.path} "
                f"completed with status {response.status_code} "
                f"(took {process_time:.2f}s)",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "process_time": process_time,
                },
            )

            # Add processing time header
            response.headers["X-Process-Time"] = str(process_time)

            return response

        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"[{request_id}] {request.method} {request.url.path} "
                f"failed after {process_time:.2f}s: {str(e)}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "process_time": process_time,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Centralized error handling middleware.

    Catches unhandled exceptions and returns proper error responses.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle errors during request processing."""
        try:
            response = await call_next(request)
            return response

        except Exception as e:
            request_id = getattr(request.state, "request_id", "unknown")

            logger.error(
                f"[{request_id}] Unhandled exception in {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                },
                exc_info=True,
            )

            # Return error response
            return Response(
                content='{"detail": "Internal server error"}',
                status_code=500,
                media_type="application/json",
                headers={"X-Request-ID": request_id},
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using sliding window counter.

    Tracks requests per client and enforces rate limits.
    """

    def __init__(self, app: ASGIApp, requests: int, window_seconds: int):
        """
        Initialize rate limiting middleware.

        Args:
            app: ASGI app
            requests: Number of allowed requests per window
            window_seconds: Time window in seconds
        """
        super().__init__(app)
        self.requests = requests
        self.window_seconds = window_seconds
        self.clients: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting."""
        # Get client identifier
        client_ip = request.client.host if request.client else "unknown"

        # Initialize client tracking if needed
        if client_ip not in self.clients:
            self.clients[client_ip] = []

        # Get current time
        now = time.time()

        # Remove old requests outside the window
        self.clients[client_ip] = [
            req_time
            for req_time in self.clients[client_ip]
            if now - req_time < self.window_seconds
        ]

        # Check rate limit
        if len(self.clients[client_ip]) >= self.requests:
            return Response(
                content='{"detail": "Rate limit exceeded"}',
                status_code=429,
                media_type="application/json",
                headers={
                    "X-RateLimit-Limit": str(self.requests),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": str(self.window_seconds),
                },
            )

        # Record this request
        self.clients[client_ip].append(now)

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        remaining = self.requests - len(self.clients[client_ip])
        response.headers["X-RateLimit-Limit"] = str(self.requests)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.

    Implements HSTS, CSP, X-Frame-Options, etc.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers."""
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; img-src 'self' data: https:"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response
