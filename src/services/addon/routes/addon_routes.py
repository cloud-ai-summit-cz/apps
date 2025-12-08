"""Addon order API routes."""
import logging
from typing import Annotated, Callable
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
import httpx

import sys
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared"))

from shared.auth.dependencies import create_auth_dependency, require_owner
from shared.auth.models import AuthContext, UserPrincipal

from models import (
    AddonOrder,
    AddonOrderCreate,
    AddonOrderStatus,
    FulfillmentMessage,
)
from repositories import AddonRepository
from services import QueueService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/addon", tags=["Addon"])

# Dependency injection placeholders (will be set in main.py)
addon_repository: AddonRepository | None = None
queue_service: QueueService | None = None
get_auth_context: Callable | None = None
trip_service_url: str | None = None
toy_service_url: str | None = None
tracer = None
addons_ordered_counter = None
addon_fulfillment_duration_histogram = None


def initialize_auth(tenant_id: str, app_id_uri: str):
    """
    Initialize auth dependency with service settings.

    Called from main.py during startup.
    """
    global get_auth_context
    get_auth_context = create_auth_dependency(tenant_id, app_id_uri)
    logger.info(f"Auth initialized with tenant_id={tenant_id}, audience={app_id_uri}")


def set_service_urls(trip_url: str, toy_url: str):
    """Set the service URLs for inter-service calls."""
    global trip_service_url, toy_service_url
    trip_service_url = trip_url
    toy_service_url = toy_url
    logger.info(f"Service URLs set - trip: {trip_url}, toy: {toy_url}")


def get_addon_repo() -> AddonRepository:
    """Dependency to get addon repository instance."""
    if addon_repository is None:
        raise RuntimeError("AddonRepository not initialized")
    return addon_repository


def get_queue_svc() -> QueueService:
    """Dependency to get queue service instance."""
    if queue_service is None:
        raise RuntimeError("QueueService not initialized")
    return queue_service


def auth_dependency(authorization: str = Header(None)) -> AuthContext:
    """FastAPI dependency wrapper for auth context."""
    if get_auth_context is None:
        raise RuntimeError("Auth not initialized")
    return get_auth_context(authorization=authorization)


async def verify_trip_ownership(trip_id: UUID, auth_ctx: AuthContext, token: str) -> tuple[str, str]:
    """
    Verify that the authenticated user owns the trip (via toy ownership).

    Args:
        trip_id: UUID of the trip
        auth_ctx: Authentication context
        token: Raw JWT token for forwarding to trip service

    Returns:
        Tuple of (owner_oid, toy_id)

    Raises:
        HTTPException: 404 if trip not found, 403 if not owner, 503 if services unavailable
    """
    if not auth_ctx.is_user:
        raise HTTPException(status_code=403, detail="Only users can create addon orders")

    user = auth_ctx.principal
    if not isinstance(user, UserPrincipal):
        raise HTTPException(status_code=403, detail="Invalid principal type")

    # Call trip service to get trip and verify ownership
    if not trip_service_url:
        raise HTTPException(status_code=503, detail="Trip service not configured")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{trip_service_url}/trip/{trip_id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0,
            )

            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="Trip not found")

            if response.status_code != 200:
                logger.error(f"Trip service returned {response.status_code}: {response.text}")
                raise HTTPException(status_code=503, detail="Failed to verify trip ownership")

            trip_data = response.json()
            owner_oid = trip_data.get("owner_oid")
            toy_id = trip_data.get("toy_id")

            if owner_oid != user.oid:
                raise HTTPException(status_code=403, detail="You don't own this trip")

            return owner_oid, toy_id

    except httpx.RequestError as e:
        logger.error(f"Failed to reach trip service: {e}")
        raise HTTPException(status_code=503, detail="Trip service unavailable")


@router.post("/trips/{trip_id}/addons", response_model=AddonOrder, status_code=201)
async def create_addon_order(
    trip_id: UUID,
    order_data: AddonOrderCreate,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    authorization: str = Header(None),
    auth_ctx: AuthContext = Depends(auth_dependency),
    repo: AddonRepository = Depends(get_addon_repo),
    queue_svc: QueueService = Depends(get_queue_svc),
) -> AddonOrder:
    """
    Create a new addon order for a trip.

    User must own the trip to create an order.
    Supports idempotent creation via Idempotency-Key header.
    """
    # Extract token for forwarding to trip service
    token = authorization.split(" ", 1)[1] if authorization and " " in authorization else ""
    
    with tracer.start_as_current_span("addon.order.create") as span:
        # Verify trip ownership
        owner_oid, toy_id = await verify_trip_ownership(trip_id, auth_ctx, token)

        # Check for existing order with same idempotency key
        if idempotency_key:
            existing_order = await repo.get_by_idempotency_key(idempotency_key, owner_oid, trip_id)
            if existing_order:
                logger.info(f"Returning existing order {existing_order.id} for idempotency key {idempotency_key}")
                span.set_attribute("idempotent", True)
                span.set_attribute("order_id", existing_order.id)
                return existing_order

        # Create new order
        order = AddonOrder(
            owner_id=owner_oid,
            trip_id=trip_id,
            addon_type=order_data.addon_type,
            notes=order_data.notes,
            idempotency_key=idempotency_key,
            status=AddonOrderStatus.PENDING,
        )

        created_order = await repo.create(order)
        
        # Enqueue fulfillment message
        fulfillment_msg = FulfillmentMessage(
            owner_id=owner_oid,
            trip_id=str(trip_id),
            order_id=created_order.id,
            addon_type=created_order.addon_type.value,
            media_style=None,
        )
        
        await queue_svc.enqueue_fulfillment(fulfillment_msg)
        
        # Add span attributes
        span.set_attribute("order_id", created_order.id)
        span.set_attribute("trip_id", str(trip_id))
        span.set_attribute("user_id", owner_oid)
        span.set_attribute("addon_type", order_data.addon_type.value)
        span.set_attribute("success", True)
        
        # Increment metric counter
        addons_ordered_counter.add(1, {
            "addon_type": order_data.addon_type.value,
            "status": "pending"
        })
        
        logger.info(f"Created addon order {created_order.id} for trip {trip_id}")

        return created_order


@router.get("/trips/{trip_id}/addons", response_model=dict)
async def list_addon_orders(
    trip_id: UUID,
    auth_ctx: AuthContext = Depends(auth_dependency),
    repo: AddonRepository = Depends(get_addon_repo),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
) -> dict:
    """
    List addon orders for a trip.

    Owner-scoped access only.
    """
    # For listing, we need to verify ownership first
    # We'll need to get the trip to verify ownership
    # For now, require user context and use their OID
    if not auth_ctx.is_user:
        raise HTTPException(status_code=403, detail="Only users can list addon orders")

    user = auth_ctx.principal
    if not isinstance(user, UserPrincipal):
        raise HTTPException(status_code=403, detail="Invalid principal type")

    owner_oid = user.oid

    # List orders (repository will use HPK with owner_oid and trip_id)
    orders, total = await repo.list_by_trip(trip_id, owner_oid, limit, offset)

    logger.debug(f"Listed {len(orders)} addon orders for trip {trip_id} (total: {total})")

    return {
        "items": orders,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/addons/{order_id}", response_model=AddonOrder)
async def get_addon_order(
    order_id: str,
    trip_id: UUID = Query(..., description="Trip ID (required for partition key)"),
    auth_ctx: AuthContext = Depends(auth_dependency),
    repo: AddonRepository = Depends(get_addon_repo),
) -> AddonOrder:
    """
    Get a single addon order by ID.

    Owner-scoped access only.
    """
    if not auth_ctx.is_user:
        raise HTTPException(status_code=403, detail="Only users can access addon orders")

    user = auth_ctx.principal
    if not isinstance(user, UserPrincipal):
        raise HTTPException(status_code=403, detail="Invalid principal type")

    owner_oid = user.oid

    # Get order (using HPK with owner_oid and trip_id)
    order = await repo.get_by_id(order_id, owner_oid, trip_id)
    if not order:
        raise HTTPException(status_code=404, detail="Addon order not found")

    logger.debug(f"Retrieved addon order {order_id}")
    return order
