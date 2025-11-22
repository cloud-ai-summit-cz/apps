"""FastAPI middleware to attach AuthContext to request.state for observability."""
from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from opentelemetry import trace, baggage, context
from .dependencies import get_auth_context


class AuthContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        token = None
        auth_ctx = None
        
        # 1. Extract Auth Context
        try:
            auth_header = request.headers.get("Authorization")
            if auth_header:
                # We use the dependency logic manually here
                # Note: This duplicates some logic but avoids dependency injection complexity in middleware
                if auth_header.lower().startswith("bearer "):
                    token = auth_header.split(" ", 1)[1]
                    # We need a way to validate without the full dependency overhead if possible,
                    # or just use the dependency function.
                    # Since get_auth_context is a closure returning a function, we can't easily call it.
                    # Let's assume we can use the helper if we had the tenant/audience.
                    # For now, we'll try to parse if we can, or rely on the route dependency to fail.
                    # BUT, for observability, we want this info even if the route doesn't require auth.
                    # So we should try to validate.
                    # However, we don't have tenant_id/audience here easily without config.
                    # Let's rely on the fact that if the route uses the dependency, it will validate.
                    # But we want to set baggage BEFORE the route.
                    
                    # Ideally, we should inject the validator or config.
                    # For this fix, let's try to decode unverified or use a shared validator if available.
                    # The user wants "user_id, user_role, is_admin".
                    # Let's try to get it from request.state if it was already set? No, middleware runs before.
                    
                    # Let's import the validator directly if we can.
                    from .token_validation import validate_token_unverified_claims
                    # We can decode unverified to get the claims for observability (low security risk for tracing)
                    # The actual security check happens in the route dependency.
                    claims = validate_token_unverified_claims(token)
                    
                    # Map to baggage keys
                    user_id = claims.get("oid") or claims.get("sub")
                    roles = claims.get("roles", [])
                    is_admin = "Admin.FullAccess" in roles
                    
                    # 2. Set OpenTelemetry Context (Baggage)
                    ctx = context.get_current()
                    if user_id:
                        ctx = baggage.set_baggage("user_id", user_id, context=ctx)
                    if roles:
                        ctx = baggage.set_baggage("user_role", ",".join(roles), context=ctx)
                    ctx = baggage.set_baggage("is_admin", str(is_admin).lower(), context=ctx)
                    
                    # Attach context for the duration of the request
                    token_handle = context.attach(ctx)
                    
                    # 3. Set Span Attributes on current server span
                    span = trace.get_current_span()
                    if span.is_recording():
                        if user_id:
                            span.set_attribute("user_id", user_id)
                        if roles:
                            span.set_attribute("user_role", roles)
                        span.set_attribute("is_admin", is_admin)
                        
                    try:
                        response = await call_next(request)
                        return response
                    finally:
                        context.detach(token_handle)
                        
        except Exception:
            # If anything fails in observability logic, don't block the request
            pass

        return await call_next(request)
