import time
import uuid
import logging
from typing import Dict
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger("severus.middleware")

# Simple in-memory sliding window rate limiter: {ip: [timestamps...]}
RATE_LIMIT_STORE: Dict[str, list] = {}
RATE_LIMIT_MAX_REQUESTS = 120 # max 120 requests
RATE_LIMIT_WINDOW_SECONDS = 60 # per 60 seconds


class SecurityAndMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Production Security, Structured Logging, Correlation Tracking,
    and Rate-Limiting Middleware for Severus AI.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.time()

        # 1. Request Correlation ID
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())

        # 2. Basic Rate Limiting
        client_ip = request.client.host if request.client else "127.0.0.1"
        now = time.time()
        
        # Cleanup old timestamps for IP
        if client_ip in RATE_LIMIT_STORE:
            RATE_LIMIT_STORE[client_ip] = [
                ts for ts in RATE_LIMIT_STORE[client_ip] if now - ts < RATE_LIMIT_WINDOW_SECONDS
            ]
        else:
            RATE_LIMIT_STORE[client_ip] = []

        if len(RATE_LIMIT_STORE[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
            logger.warning(f"Rate limit exceeded for IP {client_ip}")
            return Response(
                content='{"detail":"Rate limit exceeded. Please slow down your requests."}',
                status_code=429,
                media_type="application/json"
            )

        RATE_LIMIT_STORE[client_ip].append(now)

        # 3. Execute Downstream
        try:
            response = await call_next(request)
        except Exception as exc:
            duration = round((time.time() - start_time) * 1000, 2)
            logger.error(f"[{correlation_id}] {request.method} {request.url.path} Failed ({duration}ms): {str(exc)}")
            raise exc

        duration = round((time.time() - start_time) * 1000, 2)

        # 4. Attach Security Headers & Correlation ID
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        logger.info(f"[{correlation_id}] {request.method} {request.url.path} -> {response.status_code} ({duration}ms)")

        return response
