"""FastAPI dependency for resolving current principal from Authorization header."""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from typing import Optional, Callable

from .token_validation import validate_token
from .models import AuthContext


def create_auth_dependency(tenant_id: str, audience: str) -> Callable:
    """
    Factory function to create an auth dependency with specific tenant and audience.
    
    Services should call this with their settings values:
        from config import settings
        get_auth_context = create_auth_dependency(settings.azure_tenant_id, settings.app_id_uri)
    
    Args:
        tenant_id: Entra ID tenant ID
        audience: Expected audience claim (e.g., api://<app-id>)
    
    Returns:
        FastAPI dependency function
    """
    def get_auth_context(authorization: Optional[str] = Header(None)) -> AuthContext:
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail="Missing bearer token")
        token = authorization.split(" ", 1)[1]
        try:
            return validate_token(token, tenant_id, audience)
        except Exception as exc:  # broad catch to map to 401/403
            detail = str(exc)
            status = 401 if "scope" in detail.lower() or "expired" in detail.lower() or "invalid" in detail.lower() else 403
            # Simplified mapping; refine with explicit exception types later
            raise HTTPException(status_code=status, detail=detail)
    
    return get_auth_context


def require_owner(auth_ctx: AuthContext, toy_owner_oid: str | None) -> None:
    principal = auth_ctx.principal
    from .token_validation import classify_authorization  # local import to avoid cycle
    if not classify_authorization(principal, toy_owner_oid):
        raise HTTPException(status_code=403, detail="Forbidden: not owner")


# Example usage in router:
# @router.post("/addon/order")
# def order_addon(req: OrderRequest, auth: AuthContext = Depends(get_auth_context)):
#     require_owner(auth, toy_owner_oid)
#     ...
