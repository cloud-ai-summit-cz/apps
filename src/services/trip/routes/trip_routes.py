"""Trip API routes."""
import logging
from typing import Annotated, Callable
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile, Query
from fastapi.responses import StreamingResponse
import httpx

# Import shared auth module
import sys
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared"))

from auth.dependencies import create_auth_dependency, require_owner
from auth.models import AuthContext

from models import Trip, TripCreate, TripUpdate, GalleryImage
from repositories import TripRepository
from services import GalleryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trip", tags=["Trip"])

# Dependency injection placeholders (will be set in main.py)
trip_repository: TripRepository | None = None
gallery_service: GalleryService | None = None
get_auth_context: Callable | None = None
toy_service_url: str | None = None


def initialize_auth(tenant_id: str, app_id_uri: str):
    """
    Initialize auth dependency with service settings.

    Called from main.py during startup.
    """
    global get_auth_context
    get_auth_context = create_auth_dependency(tenant_id, app_id_uri)
    logger.info(f"Auth initialized with tenant_id={tenant_id}, audience={app_id_uri}")


def set_toy_service_url(url: str):
    """Set the toy service URL for inter-service calls."""
    global toy_service_url
    toy_service_url = url
    logger.info(f"Toy service URL set to: {url}")


def get_trip_repo() -> TripRepository:
    """Dependency to get trip repository instance."""
    if trip_repository is None:
        raise RuntimeError("TripRepository not initialized")
    return trip_repository


def get_gallery_svc() -> GalleryService:
    """Dependency to get gallery service instance."""
    if gallery_service is None:
        raise RuntimeError("GalleryService not initialized")
    return gallery_service


# Auth dependency wrapper
def auth_dependency(authorization: str = Header(None)) -> AuthContext:
    """FastAPI dependency wrapper for auth context."""
    if get_auth_context is None:
        raise RuntimeError("Auth not initialized")
    return get_auth_context(authorization=authorization)


async def verify_toy_ownership(toy_id: UUID, auth_ctx: AuthContext, token: str) -> str:
    """
    Verify that the authenticated user owns the specified toy.

    Args:
        toy_id: UUID of the toy
        auth_ctx: Authentication context
        token: Raw JWT token for forwarding to toy service

    Returns:
        owner_oid from the toy

    Raises:
        HTTPException: 404 if toy not found, 403 if not owner, 503 if toy service unavailable
    """
    if not auth_ctx.is_user:
        raise HTTPException(status_code=403, detail="Only users can create trips")

    from auth.models import UserPrincipal

    user = auth_ctx.principal
    if not isinstance(user, UserPrincipal):
        raise HTTPException(status_code=403, detail="Invalid principal type")

    # Call toy service to verify ownership
    if not toy_service_url:
        raise HTTPException(status_code=503, detail="Toy service not configured")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{toy_service_url}/toy/{toy_id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0,
            )

            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="Toy not found")

            if response.status_code != 200:
                logger.error(f"Toy service returned {response.status_code}: {response.text}")
                raise HTTPException(status_code=503, detail="Failed to verify toy ownership")

            toy_data = response.json()
            owner_oid = toy_data.get("owner_oid")

            if owner_oid != user.oid:
                raise HTTPException(status_code=403, detail="You don't own this toy")

            return owner_oid

    except httpx.RequestError as e:
        logger.error(f"Failed to reach toy service: {e}")
        raise HTTPException(status_code=503, detail="Toy service unavailable")


@router.post("", response_model=Trip, status_code=201)
async def create_trip(
    trip_data: TripCreate,
    authorization: str = Header(None),
    auth_ctx: AuthContext = Depends(auth_dependency),
    repo: TripRepository = Depends(get_trip_repo),
) -> Trip:
    """
    Create a new trip for a toy.

    User must own the toy to create a trip.
    """
    # Extract token for forwarding to toy service
    token = authorization.split(" ", 1)[1] if authorization and " " in authorization else ""
    
    # Verify toy ownership (this also ensures user is authenticated properly)
    owner_oid = await verify_toy_ownership(trip_data.toy_id, auth_ctx, token)

    # Create trip with owner_oid denormalized for fast auth checks
    trip = Trip(
        title=trip_data.title.strip(),
        description=trip_data.description.strip() if trip_data.description else None,
        location_name=trip_data.location_name.strip(),
        country_code=trip_data.country_code,
        toy_id=trip_data.toy_id,
        owner_oid=owner_oid,
        public_tracking_enabled=trip_data.public_tracking_enabled,
    )

    created_trip = await repo.create(trip)
    logger.info(f"Created trip {created_trip.id} for toy {trip_data.toy_id}")

    return created_trip


@router.get("/{trip_id}", response_model=Trip)
async def get_trip(
    trip_id: UUID,
    auth_ctx: AuthContext = Depends(auth_dependency),
    repo: TripRepository = Depends(get_trip_repo),
) -> Trip:
    """
    Get trip details including gallery.

    Global read access.
    """
    trip = await repo.get_by_id(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    logger.debug(f"Retrieved trip {trip_id}")
    return trip


@router.get("", response_model=dict)
async def list_trips(
    auth_ctx: AuthContext = Depends(auth_dependency),
    repo: TripRepository = Depends(get_trip_repo),
    toy_id: UUID | None = Query(None, description="Filter by toy ID"),
    owner_oid: str | None = Query(None, description="Filter by owner OID"),
    limit: int = Query(20, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
) -> dict:
    """
    List trips with optional filtering.

    Global read access.
    """
    if toy_id:
        trips, total = await repo.list_by_toy(toy_id, limit, offset)
    elif owner_oid:
        trips, total = await repo.list_by_owner(owner_oid, limit, offset)
    else:
        # For now, require at least one filter to prevent full table scan
        raise HTTPException(status_code=400, detail="Must specify toy_id or owner_oid filter")

    logger.debug(f"Listed {len(trips)} trips (total: {total})")

    return {
        "items": trips,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.patch("/{trip_id}", response_model=Trip)
async def update_trip(
    trip_id: UUID,
    trip_update: TripUpdate,
    auth_ctx: AuthContext = Depends(auth_dependency),
    repo: TripRepository = Depends(get_trip_repo),
) -> Trip:
    """
    Update trip details.

    Only the owner can update their trip.
    """
    # Get existing trip
    trip = await repo.get_by_id(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Check ownership
    require_owner(auth_ctx, trip.owner_oid)

    # Apply updates (only non-None fields)
    updates = trip_update.model_dump(exclude_unset=True, exclude_none=True)
    if not updates:
        return trip  # No changes

    updated_trip = await repo.update(trip_id, updates)
    if not updated_trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    logger.info(f"Updated trip {trip_id}")
    return updated_trip


@router.delete("/{trip_id}", status_code=204)
async def delete_trip(
    trip_id: UUID,
    auth_ctx: Annotated[AuthContext, Depends(auth_dependency)],
    repo: Annotated[TripRepository, Depends(get_trip_repo)],
    gallery_svc: Annotated[GalleryService, Depends(get_gallery_svc)],
):
    """
    Delete a trip.

    Only the owner can delete their trip.
    """
    # Get existing trip
    trip = await repo.get_by_id(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Check ownership
    require_owner(auth_ctx, trip.owner_oid)

    # Delete all gallery images
    for image in trip.gallery:
        await gallery_svc.delete_image(image.blob_name)

    # Delete trip from database
    deleted = await repo.delete(trip_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Trip not found")

    logger.info(f"Deleted trip {trip_id}")


# Gallery endpoints


@router.post("/{trip_id}/gallery", response_model=Trip)
async def upload_gallery_image(
    trip_id: UUID,
    landmark: str | None = Query(None, max_length=200, description="Optional landmark name"),
    caption: str | None = Query(None, max_length=500, description="Optional image caption"),
    file: UploadFile = File(..., description="Gallery image (JPEG, PNG, or WebP)"),
    auth_ctx: AuthContext = Depends(auth_dependency),
    repo: TripRepository = Depends(get_trip_repo),
    gallery_svc: GalleryService = Depends(get_gallery_svc),
) -> Trip:
    """
    Upload a gallery image for a trip.

    Can optionally associate with a landmark.
    Only the owner can upload images.
    """
    # Get existing trip
    trip = await repo.get_by_id(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Check ownership
    require_owner(auth_ctx, trip.owner_oid)

    try:
        # Upload image to blob storage
        blob_name = await gallery_svc.upload_image(file, str(trip_id))

        # Create gallery image metadata
        image = GalleryImage(
            landmark=landmark,
            blob_name=blob_name,
            caption=caption,
            source="user",
        )

        # Add to trip gallery
        updated_trip = await repo.add_gallery_image(trip_id, image)
        if not updated_trip:
            raise HTTPException(status_code=404, detail="Trip not found")

        logger.info(f"Uploaded gallery image for trip {trip_id}, landmark {landmark}")
        return updated_trip

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to upload gallery image: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload gallery image")


@router.get("/{trip_id}/gallery/{image_id}")
async def get_gallery_image(
    trip_id: UUID,
    image_id: UUID,
    auth_ctx: AuthContext = Depends(auth_dependency),
    repo: TripRepository = Depends(get_trip_repo),
    gallery_svc: GalleryService = Depends(get_gallery_svc),
):
    """
    Download a gallery image.

    Global read access.
    """
    # Get trip to verify image exists
    trip = await repo.get_by_id(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Find image in gallery
    image = next((img for img in trip.gallery if str(img.image_id) == str(image_id)), None)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found in gallery")

    try:
        # Stream image from blob storage
        stream, content_type = await gallery_svc.stream_image(image.blob_name)

        return StreamingResponse(
            stream,
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=3600",  # 1 hour cache
                "Content-Disposition": f'inline; filename="gallery-{image_id}.jpg"',
            },
        )

    except FileNotFoundError:
        logger.error(f"Blob not found for image {image_id}: {image.blob_name}")
        raise HTTPException(status_code=404, detail="Image file not found")
    except Exception as e:
        logger.error(f"Failed to retrieve gallery image: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve image")


@router.delete("/{trip_id}/gallery/{image_id}", status_code=204)
async def delete_gallery_image(
    trip_id: UUID,
    image_id: UUID,
    auth_ctx: Annotated[AuthContext, Depends(auth_dependency)],
    repo: Annotated[TripRepository, Depends(get_trip_repo)],
    gallery_svc: Annotated[GalleryService, Depends(get_gallery_svc)],
):
    """
    Delete a gallery image.

    Only the owner can delete images.
    """
    # Get existing trip
    trip = await repo.get_by_id(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Check ownership
    require_owner(auth_ctx, trip.owner_oid)

    # Find image in gallery
    image = next((img for img in trip.gallery if str(img.image_id) == str(image_id)), None)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found in gallery")

    # Delete blob from storage
    await gallery_svc.delete_image(image.blob_name)

    # Remove from trip gallery
    updated_trip = await repo.remove_gallery_image(trip_id, image_id)
    if not updated_trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    logger.info(f"Deleted gallery image {image_id} from trip {trip_id}")



