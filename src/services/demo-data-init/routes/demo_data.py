"""API endpoints for demo data import orchestration."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable

from fastapi import APIRouter, Depends, Header, HTTPException, status

from models import ImportRequest, ImportResponse
from services.importer import DemoDataImportService

# Shared auth module (added to sys.path in main.py)
from auth.dependencies import create_auth_dependency
from auth.models import AuthContext

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/demo-data", tags=["Demo Data"])

import_service: DemoDataImportService | None = None
get_auth_context: Callable | None = None
required_role: str = "Admin.FullAccess"


def configure_router(*, importer: DemoDataImportService, tenant_id: str, audience: str, role_value: str) -> None:
    """Wire up auth dependency and import service singleton (called from main)."""

    global import_service, get_auth_context, required_role
    import_service = importer
    get_auth_context = create_auth_dependency(tenant_id, audience)
    required_role = role_value
    logger.info("Demo data router configured (role=%s)", role_value)


def auth_dependency(authorization: str = Header(None)) -> AuthContext:
    if get_auth_context is None:
        raise RuntimeError("Auth dependency not initialized")
    return get_auth_context(authorization=authorization)


def _extract_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return authorization.split(" ", 1)[1]


def _require_admin_role(auth_ctx: AuthContext) -> None:
    principal = auth_ctx.principal
    if required_role not in principal.roles:
        raise HTTPException(status_code=403, detail="Demo data admin role required")


def _get_import_service() -> DemoDataImportService:
    if import_service is None:
        raise HTTPException(status_code=503, detail="Import service not initialized")
    return import_service


@router.post("/import", response_model=ImportResponse, status_code=status.HTTP_200_OK)
async def trigger_import(
    request: ImportRequest,
    authorization: str = Header(None),
    auth_ctx: AuthContext = Depends(auth_dependency),
) -> ImportResponse:
    """Run a synchronous import if caller has the required role."""
    _require_admin_role(auth_ctx)
    try:
        request.ensure_valid()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    token = _extract_token(authorization)
    importer = _get_import_service()
    started_at = datetime.now(timezone.utc)
    try:
        summary = await importer.import_data(
            include_toys=request.include_toys,
            include_trips=request.include_trips,
            token=token,
        )
    except Exception as exc:  # pragma: no cover - surfaced as HTTP error
        logger.exception("Demo data import failed")
        raise HTTPException(status_code=502, detail="Demo data import failed") from exc

    duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
    return ImportResponse(
        include_toys=request.include_toys,
        include_trips=request.include_trips,
        summary=summary,
        duration_ms=duration_ms,
    )
