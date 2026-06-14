"""
Authentication middleware for JWT token validation.
"""

import logging
from typing import Callable

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.security import verify_token

logger = logging.getLogger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware to validate JWT tokens."""

    def __init__(self, app, exclude_paths: list = None):
        """Initialize middleware."""
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/",
            "/health",
            "/api/docs",
            "/api/openapi.json",
            "/api/v1/auth/register",
            "/api/v1/auth/login",
            "/api/v1/auth/refresh",
        ]

    async def dispatch(self, request: Request, call_next: Callable):
        """Process request."""
        # Skip authentication for excluded paths
        if request.url.path in self.exclude_paths or request.url.path.startswith("/api/docs"):
            return await call_next(request)

        # Skip for OPTIONS requests (CORS)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Get token from header
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            logger.warning(f"Missing auth header for {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing authorization header"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                raise ValueError("Invalid authentication scheme")
        except (ValueError, IndexError):
            logger.warning(f"Invalid auth header format for {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid authorization header format"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verify token
        token_data = verify_token(token)

        if not token_data:
            logger.warning(f"Invalid/expired token for {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or expired token"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Add user info to request state
        request.state.user_id = token_data.user_id
        request.state.username = token_data.username
        request.state.role = token_data.role

        return await call_next(request)
