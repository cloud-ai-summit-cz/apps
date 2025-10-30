"""Permission helper functions for domain actions."""
from __future__ import annotations

from .models import Principal, UserPrincipal, SystemPrincipal


def can_read_global(principal: Principal) -> bool:
    return True  # MVP global read allowed


def can_write_toy_owned(principal: Principal, owner_oid: str | None) -> bool:
    if isinstance(principal, SystemPrincipal):
        return True
    if isinstance(principal, UserPrincipal) and owner_oid:
        return principal.oid == owner_oid
    return False


def can_live_track(principal: Principal, owner_oid: str | None) -> bool:
    return can_write_toy_owned(principal, owner_oid)
