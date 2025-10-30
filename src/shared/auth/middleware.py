"""FastAPI middleware to attach AuthContext to request.state for observability."""
from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from .dependencies import get_auth_context


class AuthContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            # Attempt extraction without forcing dependency injection chain
            auth_header = request.headers.get("Authorization")
            if auth_header:
                request.state.auth = get_auth_context(auth_header)
        except Exception:
            # Do not block request; dependency usage will raise proper HTTP errors
            request.state.auth = None
        return await call_next(request)
