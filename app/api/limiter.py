"""
Shared rate limiter instance.
Imported by main.py and API routers to avoid circular imports.
Uses X-Forwarded-For header for correct client IP behind reverse proxy (nginx, ALB, etc.).
"""
from slowapi import Limiter


def get_client_ip(request) -> str:
    """
    Extract real client IP from X-Forwarded-For header when behind a reverse proxy.
    Falls back to request.client.host if header is not present.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # X-Forwarded-For can have multiple IPs: client, proxy1, proxy2
        return forwarded.split(",")[0].strip()
    return request.client.host or "unknown"


limiter = Limiter(key_func=get_client_ip)
