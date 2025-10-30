"""Shared authentication package providing token validation, principal modeling,
FastAPI dependencies, permission helpers, and lightweight middleware.
"""
from .models import Principal, UserPrincipal, SystemPrincipal, AuthContext  # noqa: F401