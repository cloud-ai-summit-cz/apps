# Shared Auth Module

Provides:
* Principal & AuthContext Pydantic models
* JWKS caching (Entra ID)
* Token validation utilities
* FastAPI dependency & middleware
* Permission helper functions

## Configuration
Environment variables (recommended) should supply:
* `TENANT_ID`
* `APP_ID_URI` (audience)

## Usage (Example)
```python
from fastapi import APIRouter, Depends
from shared.auth.dependencies import get_auth_context, require_owner

router = APIRouter()

@router.post("/addon/order")
def order_addon(req: OrderRequest, auth = Depends(get_auth_context)):
    toy_owner_oid = "..."  # lookup from toy entity
    require_owner(auth, toy_owner_oid)
    return {"status": "ok"}
```

## Notes
* Global read allowed by design (MVP).
* Replace placeholder tenant/audience constants before production.
* Future: Add caching layer & telemetry instrumentation.
