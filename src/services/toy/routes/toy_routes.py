"""Toy API routes."""
import logging
from typing import Annotated, Callable
from uuid import UUID

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

# Import shared auth module (assuming it's available in Python path)
import sys
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared"))

from auth.dependencies import create_auth_dependency, require_owner
from auth.models import AuthContext

from models import Toy, ToyCreate, ToyUpdate
from repositories import ToyRepository
from services import BlobService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/toy", tags=["Toy"])

# Dependency injection placeholders (will be set in main.py)
toy_repository: ToyRepository | None = None
blob_service: BlobService | None = None
get_auth_context: Callable | None = None


def initialize_auth(tenant_id: str, app_id_uri: str):
    """
    Initialize auth dependency with service settings.
    
    Called from main.py during startup.
    """
    global get_auth_context
    get_auth_context = create_auth_dependency(tenant_id, app_id_uri)
    logger.info(f"Auth initialized with tenant_id={tenant_id}, audience={app_id_uri}")


def get_toy_repo() -> ToyRepository:
    """Dependency to get toy repository instance."""
    if toy_repository is None:
        raise RuntimeError("ToyRepository not initialized")
    return toy_repository


def get_blob_svc() -> BlobService:
    """Dependency to get blob service instance."""
    if blob_service is None:
        raise RuntimeError("BlobService not initialized")
    return blob_service


# Auth dependency wrapper that uses the initialized function
def auth_dependency(authorization: str = Header(None)) -> AuthContext:
    """FastAPI dependency wrapper for auth context."""
    if get_auth_context is None:
        raise RuntimeError("Auth not initialized")
    # Call the initialized auth function
    return get_auth_context(authorization=authorization)


@router.post("", response_model=Toy, status_code=201)
async def create_toy(
    toy_data: ToyCreate,
    auth_ctx: AuthContext = Depends(auth_dependency),
    repo: ToyRepository = Depends(get_toy_repo),
) -> Toy:
    """
    Register a new toy.

    The owner_oid is automatically set from the authenticated user's token.
    """
    if not auth_ctx.is_user:
        raise HTTPException(status_code=403, detail="Only users can create toys")

    from auth.models import UserPrincipal

    user = auth_ctx.principal
    if not isinstance(user, UserPrincipal):
        raise HTTPException(status_code=403, detail="Invalid principal type")

    # Create toy with owner_oid from token
    toy = Toy(
        name=toy_data.name.strip(),
        description=toy_data.description.strip() if toy_data.description else None,
        owner_oid=user.oid,
    )

    created_toy = await repo.create(toy)
    logger.info(f"Created toy {created_toy.id} for owner {user.oid}")

    return created_toy


@router.get("", response_model=dict)
async def list_toys(
    owner_oid: str | None = None,
    limit: int = 20,
    offset: int = 0,
    auth_ctx: Annotated[AuthContext, Depends(auth_dependency)] = None,
    repo: Annotated[ToyRepository, Depends(get_toy_repo)] = None,
) -> dict:
    """
    List all toys with pagination.

    Optionally filter by owner_oid.
    """
    toys, total = await repo.list_all(owner_oid=owner_oid, limit=limit, offset=offset)

    # Convert to response format matching OpenAPI spec
    return {"items": [toy.model_dump(mode="json") for toy in toys], "total": total, "limit": limit, "offset": offset}


@router.get("/{toy_id}", response_model=Toy)
async def get_toy(
    toy_id: UUID,
    auth_ctx: Annotated[AuthContext, Depends(auth_dependency)],
    repo: Annotated[ToyRepository, Depends(get_toy_repo)],
) -> Toy:
    """Get toy details by ID."""
    toy = await repo.get_by_id(toy_id)
    if not toy:
        raise HTTPException(status_code=404, detail="Toy not found")

    return toy


@router.patch("/{toy_id}", response_model=Toy)
async def update_toy(
    toy_id: UUID,
    toy_update: ToyUpdate,
    auth_ctx: Annotated[AuthContext, Depends(auth_dependency)],
    repo: Annotated[ToyRepository, Depends(get_toy_repo)],
) -> Toy:
    """
    Update toy details (partial update).

    Only the owner can update their toy.
    """
    # Get existing toy
    toy = await repo.get_by_id(toy_id)
    if not toy:
        raise HTTPException(status_code=404, detail="Toy not found")

    # Check ownership
    require_owner(auth_ctx, toy.owner_oid)

    # Apply updates (only non-None fields)
    updates = toy_update.model_dump(exclude_unset=True, exclude_none=True)
    if not updates:
        return toy  # No changes

    updated_toy = await repo.update(toy_id, updates)
    if not updated_toy:
        raise HTTPException(status_code=404, detail="Toy not found")

    logger.info(f"Updated toy {toy_id}")
    return updated_toy


@router.delete("/{toy_id}", status_code=204)
async def delete_toy(
    toy_id: UUID,
    auth_ctx: Annotated[AuthContext, Depends(auth_dependency)],
    repo: Annotated[ToyRepository, Depends(get_toy_repo)],
    blob_svc: Annotated[BlobService, Depends(get_blob_svc)],
):
    """
    Delete a toy.

    Only the owner can delete their toy.
    """
    # Get existing toy
    toy = await repo.get_by_id(toy_id)
    if not toy:
        raise HTTPException(status_code=404, detail="Toy not found")

    # Check ownership
    require_owner(auth_ctx, toy.owner_oid)

    # Delete avatar if exists
    if toy.avatar_blob_name:
        await blob_svc.delete_avatar(toy.avatar_blob_name)

    # Delete toy from database
    deleted = await repo.delete(toy_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Toy not found")

    logger.info(f"Deleted toy {toy_id}")


# Avatar endpoints


@router.post("/{toy_id}/avatar", response_model=Toy)
async def upload_avatar(
    toy_id: UUID,
    file: Annotated[UploadFile, File(description="Avatar image (JPEG, PNG, or WebP)")],
    auth_ctx: Annotated[AuthContext, Depends(auth_dependency)],
    repo: Annotated[ToyRepository, Depends(get_toy_repo)],
    blob_svc: Annotated[BlobService, Depends(get_blob_svc)],
) -> Toy:
    """
    Upload avatar image for a toy.

    Only the owner can upload an avatar.
    """
    # Get existing toy
    toy = await repo.get_by_id(toy_id)
    if not toy:
        raise HTTPException(status_code=404, detail="Toy not found")

    # Check ownership
    require_owner(auth_ctx, toy.owner_oid)

    try:
        # Delete old avatar if exists
        if toy.avatar_blob_name:
            await blob_svc.delete_avatar(toy.avatar_blob_name)

        # Upload new avatar
        blob_name = await blob_svc.upload_avatar(file, str(toy_id))

        # Update toy with new avatar reference
        updated_toy = await repo.update(toy_id, {"avatar_blob_name": blob_name, "has_avatar": True})

        if not updated_toy:
            raise HTTPException(status_code=404, detail="Toy not found")

        logger.info(f"Uploaded avatar for toy {toy_id}")
        return updated_toy

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to upload avatar: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload avatar")


@router.get("/{toy_id}/avatar")
async def get_avatar(
    toy_id: UUID,
    auth_ctx: Annotated[AuthContext, Depends(auth_dependency)],
    repo: Annotated[ToyRepository, Depends(get_toy_repo)],
    blob_svc: Annotated[BlobService, Depends(get_blob_svc)],
) -> StreamingResponse:
    """
    Get avatar image for a toy.

    Streams the image from blob storage.
    """
    # Get toy
    toy = await repo.get_by_id(toy_id)
    if not toy or not toy.avatar_blob_name:
        raise HTTPException(status_code=404, detail="Toy has no avatar image")

    try:
        # Stream avatar from blob storage
        stream, content_type = await blob_svc.stream_avatar(toy.avatar_blob_name)

        return StreamingResponse(
            stream,
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=3600",  # 1 hour cache
            },
        )

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Avatar image not found")
    except Exception as e:
        logger.error(f"Failed to retrieve avatar: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve avatar")


@router.delete("/{toy_id}/avatar", status_code=204)
async def delete_avatar(
    toy_id: UUID,
    auth_ctx: Annotated[AuthContext, Depends(auth_dependency)],
    repo: Annotated[ToyRepository, Depends(get_toy_repo)],
    blob_svc: Annotated[BlobService, Depends(get_blob_svc)],
):
    """
    Delete avatar image for a toy.

    Only the owner can delete an avatar.
    """
    # Get toy
    toy = await repo.get_by_id(toy_id)
    if not toy:
        raise HTTPException(status_code=404, detail="Toy not found")

    # Check ownership
    require_owner(auth_ctx, toy.owner_oid)

    if not toy.avatar_blob_name:
        raise HTTPException(status_code=404, detail="Toy has no avatar")

    # Delete avatar from blob storage
    await blob_svc.delete_avatar(toy.avatar_blob_name)

    # Update toy to remove avatar reference
    await repo.update(toy_id, {"avatar_blob_name": None, "has_avatar": False})

    logger.info(f"Deleted avatar for toy {toy_id}")
