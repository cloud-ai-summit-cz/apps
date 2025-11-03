# Shared Auth Module

Provides:
* Principal & AuthContext Pydantic models
* JWKS caching (Entra ID)
* Token validation utilities
* FastAPI dependency & middleware
* Permission helper functions (ownership + role-based)

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
    require_owner(auth, toy_owner_oid)  # Allows: owner, Admin.FullAccess role, or System.Service
    return {"status": "ok"}
```

## Authorization Model

### App Roles
- **Toy.ReadWrite**: Standard user access (scope-based, delegated)
- **Admin.FullAccess**: Admin access to all resources regardless of ownership
- **System.Service**: Background service access (application-level)

### Ownership Checks
The `require_owner()` function allows access if:
1. System principal (has `System.Service` role) - for background operations
2. User principal with `Admin.FullAccess` role - for admin operations
3. User principal with matching `oid` - for owner operations

### Role Assignment
See `tools/identity/ADMIN_ROLE_SETUP.md` for how to configure and assign the `Admin.FullAccess` role in Entra ID.

## Notes
* Global read allowed by design (MVP).
* Replace placeholder tenant/audience constants before production.
* Future: Add caching layer & telemetry instrumentation.
