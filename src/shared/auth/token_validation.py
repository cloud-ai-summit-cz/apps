"""Token validation logic.

Verifies JWTs issued by Entra ID, classifies principal, and returns AuthContext.
"""
from __future__ import annotations

import base64
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Optional
from jose import jwt
from jose.exceptions import JWTError
from pydantic import ValidationError

from .jwks_cache import get_key
from .models import UserPrincipal, SystemPrincipal, Principal, AuthContext

CLOCK_SKEW = timedelta(minutes=2)
REQUIRED_SCOPE = "App.Access"
SYSTEM_ROLE = "System.Service"


def _b64url_decode(segment: str) -> bytes:
    padding = '=' * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def _extract_header(token: str) -> dict:
    parts = token.split('.')
    if len(parts) < 2:
        raise ValueError("Invalid JWT structure")
    header_bytes = _b64url_decode(parts[0])
    return json.loads(header_bytes.decode())


def validate_token(token: str, tenant_id: str, audience: str) -> AuthContext:
    """Validate JWT and return AuthContext or raise ValueError/JWTError.

    Raises:
        ValueError: Structural or claim validation error.
        JWTError: Signature or cryptographic validation error.
    """
    if not token:
        raise ValueError("Empty token")

    header = _extract_header(token)
    kid = header.get("kid")
    if not kid:
        raise ValueError("Missing kid in header")

    key = get_key(kid, tenant_id)
    if not key:
        raise ValueError("JWKS key not found")

    # Validate signature & basic claims
    claims = jwt.decode(
        token,
        key,
        algorithms=[header.get("alg", "RS256")],
        audience=audience,
        issuer=f"https://login.microsoftonline.com/{tenant_id}/v2.0",
        options={"verify_aud": True, "verify_iss": True},
    )

    now = datetime.now(timezone.utc)
    exp = datetime.fromtimestamp(claims.get("exp", 0), tz=timezone.utc)
    nbf_ts = claims.get("nbf")
    if nbf_ts is not None:
        nbf = datetime.fromtimestamp(nbf_ts, tz=timezone.utc)
        if nbf - CLOCK_SKEW > now:
            raise ValueError("Token not yet valid")
    if exp + CLOCK_SKEW < now:
        raise ValueError("Token expired")

    scopes = claims.get("scp", "").split() if claims.get("scp") else []
    roles = claims.get("roles", [])
    if isinstance(roles, str):
        roles = [roles]

    # Permission baseline: need scope OR role
    if REQUIRED_SCOPE not in scopes and not roles:
        raise ValueError("Missing required scope or role")

    principal: Principal
    if "oid" in claims:  # user token
        principal = UserPrincipal(
            subject_id=claims["oid"],
            oid=claims["oid"],
            display_name=claims.get("preferred_username") or claims.get("name"),
            scopes=scopes,
            roles=roles,
            issued_at=datetime.fromtimestamp(claims.get("iat", 0), tz=timezone.utc),
            expires_at=exp,
        )
    else:
        principal = SystemPrincipal(
            subject_id=claims.get("appid") or claims.get("azp") or "unknown",
            is_system=True,
            app_id=claims.get("appid") or claims.get("azp"),
            scopes=scopes,
            roles=roles,
            issued_at=datetime.fromtimestamp(claims.get("iat", 0), tz=timezone.utc),
            expires_at=exp,
        )

    try:
        auth_ctx = AuthContext(principal=principal, raw_claims=claims, token_id=claims.get("jti"))
    except ValidationError as exc:
        raise ValueError(f"Auth context validation failed: {exc}") from exc
    return auth_ctx


def classify_authorization(principal: Principal, toy_owner_oid: Optional[str]) -> bool:
    """Return True if principal can perform owner-only action on provided toy.

    System principal always allowed. User principal must match owner oid.
    """
    if principal.is_system or isinstance(principal, SystemPrincipal):
        return True
    if isinstance(principal, UserPrincipal) and toy_owner_oid:
        return principal.oid == toy_owner_oid
    return False
