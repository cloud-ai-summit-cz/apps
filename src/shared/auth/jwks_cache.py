"""JWKS caching utilities.

Fetches and caches JWKS keys from Entra ID discovery endpoint. Uses an in-memory
cache; future improvement may add background refresh or redis layer.
"""
from __future__ import annotations

import time
from typing import Dict, Any, Optional
import httpx
from threading import RLock

_JWKS_CACHE: Dict[str, Any] = {}
_CACHE_EXPIRY: float = 0
_LOCK = RLock()
_DEFAULT_TTL_SECONDS = 60 * 60 * 24  # 24h


def _jwks_url(tenant_id: str) -> str:
    return f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"


def get_jwks(tenant_id: str, force_refresh: bool = False) -> Dict[str, Any]:
    """Return JWKS for given tenant, refreshing if expired or forced."""
    global _CACHE_EXPIRY
    with _LOCK:
        now = time.time()
        if force_refresh or not _JWKS_CACHE or now >= _CACHE_EXPIRY:
            resp = httpx.get(_jwks_url(tenant_id), timeout=10)
            resp.raise_for_status()
            data = resp.json()
            _JWKS_CACHE.clear()
            _JWKS_CACHE.update({k['kid']: k for k in data.get('keys', [])})
            _CACHE_EXPIRY = now + _DEFAULT_TTL_SECONDS
        return _JWKS_CACHE


def get_key(kid: str, tenant_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single JWK by kid, refreshing cache if missing."""
    keys = get_jwks(tenant_id)
    if kid not in keys:
        keys = get_jwks(tenant_id, force_refresh=True)
    return keys.get(kid)
