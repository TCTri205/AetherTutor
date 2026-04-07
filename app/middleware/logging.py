"""
Middleware for request logging and correlation IDs.

Implemented as a pure ASGI middleware to avoid buffering responses.
BaseHTTPMiddleware from Starlette buffers the entire response before
sending it to the client, which breaks StreamingResponse (SSE).
"""
import uuid
import time
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from ..logging_config import set_correlation_id, get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware:
    """
    ASGI middleware that:
    1. Generates a unique correlation_id for each request
    2. Logs request start and end with timing
    3. Adds correlation_id to response headers

    Unlike BaseHTTPMiddleware, this does NOT buffer responses,
    so StreamingResponse (SSE) works correctly.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Generate correlation ID (16 hex chars = 2^64 space, negligible collision risk)
        correlation_id = str(uuid.uuid4()).replace("-", "")[:16]

        # Set in contextvar (async-safe, per-request)
        set_correlation_id(correlation_id)

        request = Request(scope)

        # Log request start
        logger.info(
            f"{request.method} {request.url.path} started",
            extra={
                "method": request.method,
                "path": request.url.path,
                "client_host": request.client.host if request.client else None,
            }
        )

        start_time = time.time()

        # Wrap send to inject correlation header without buffering
        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-correlation-id", correlation_id.encode()))
                message = dict(message)
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"{request.method} {request.url.path} failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                    "duration_ms": round(duration * 1000, 2),
                },
                exc_info=True,
            )
            raise
        else:
            duration = time.time() - start_time
            logger.info(
                f"{request.method} {request.url.path} completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration * 1000, 2),
                }
            )
