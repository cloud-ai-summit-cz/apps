"""Authentication data models.

Defines Pydantic models representing principals (user/system) and per-request
authentication context.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel


class Principal(BaseModel):
    """Base authenticated principal.

    Attributes:
        subject_id: Canonical identifier for principal (user oid or app id).
        is_system: True if system/workload identity.
        roles: Application roles present in token.
        scopes: OAuth scopes from the token (scp claim).
        issued_at: Token issued-at timestamp.
        expires_at: Token expiration timestamp.
    """
    subject_id: str
    is_system: bool = False
    roles: List[str] = []
    scopes: List[str] = []
    issued_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    def has_role(self, role: str) -> bool:
        return role in self.roles

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes


class UserPrincipal(Principal):
    """Interactive user principal backed by Entra ID."""
    oid: str
    display_name: Optional[str] = None


class SystemPrincipal(Principal):
    """Background/service principal using managed identity."""
    app_id: Optional[str] = None


class AuthContext(BaseModel):
    """Per-request resolved authentication context."""
    principal: Principal
    raw_claims: Dict[str, Any] = {}  # JWT claims can be str, int, list, etc.
    token_id: Optional[str] = None

    @property
    def is_user(self) -> bool:
        return isinstance(self.principal, UserPrincipal)

    @property
    def is_system(self) -> bool:
        return isinstance(self.principal, SystemPrincipal) or self.principal.is_system

    @property
    def is_admin(self) -> bool:
        return "Admin.FullAccess" in self.principal.roles
