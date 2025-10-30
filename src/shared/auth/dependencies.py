"""FastAPI dependency for resolving current principal from Authorization header."""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from typing import Optional

from .token_validation import validate_token
from .models import AuthContext

# Runtime config placeholders (could be injected via environment or settings module)
TENANT_ID = "<tenant-id>"  # TODO: replace with real tenant id from env
AUDIENCE = "api://<app-id>"  # TODO: replace with real Application ID URI


def get_auth_context(authorization: Optional[str] = Header(None)) -> AuthContext:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        return validate_token(token, TENANT_ID, AUDIENCE)
    except Exception as exc:  # broad catch to map to 401/403
        detail = str(exc)
        status = 401 if "scope" in detail.lower() or "expired" in detail.lower() or "invalid" in detail.lower() else 403
        # Simplified mapping; refine with explicit exception types later
        raise HTTPException(status_code=status, detail=detail)


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
