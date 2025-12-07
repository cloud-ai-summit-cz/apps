"""REST API routes for story operations."""
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, List
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared"))

from shared.auth.dependencies import create_auth_dependency
from shared.auth.models import AuthContext

from models.story import Story, StoryCreate
from repositories.story_repository import StoryRepository
from services.story_generation_service import StoryGenerationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/story", tags=["Story"])

# Global instances (injected at startup)
story_repository: StoryRepository | None = None
story_generation_service: StoryGenerationService | None = None
get_auth_context: Callable | None = None
tracer = None
stories_generated_counter = None
stories_viewed_counter = None


def initialize_auth(tenant_id: str, app_id_uri: str):
    """
    Initialize auth dependency with service settings.

    Called from main.py during startup.
    """
    global get_auth_context
    get_auth_context = create_auth_dependency(tenant_id, app_id_uri)
    logger.info(f"Auth initialized with tenant_id={tenant_id}, audience={app_id_uri}")


def auth_dependency(authorization: str = Header(None)) -> AuthContext:
    """FastAPI dependency wrapper for auth context."""
    if get_auth_context is None:
        raise RuntimeError("Auth not initialized")
    return get_auth_context(authorization=authorization)


class GenerateStoryRequest(BaseModel):
    """Request model for generating a story."""

    story_date: str | None = None  # Optional, defaults to today


class GenerateStoryResponse(BaseModel):
    """Response model for story generation."""

    story_id: str
    status: str
    message: str


@router.post("/{trip_id}/generate", response_model=GenerateStoryResponse)
async def generate_story(
    trip_id: UUID,
    request: GenerateStoryRequest | None = None,
    auth_ctx: AuthContext = Depends(auth_dependency),
    authorization: str = Header(None),
):
    """
    Trigger story generation for a trip.
    
    This endpoint is idempotent per (tripId, storyDate) - if a story
    already exists for the date, it returns the existing story.
    
    Args:
        trip_id: Trip ID
        request: Generation request with optional story_date
        auth_ctx: Authentication context
        authorization: Authorization header for token extraction
        
    Returns:
        Story generation response
    """
    if not story_repository or not story_generation_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    # Only users can generate stories
    if not auth_ctx.is_user:
        raise HTTPException(status_code=403, detail="Only users can generate stories")

    from shared.auth.models import UserPrincipal
    user = auth_ctx.principal
    if not isinstance(user, UserPrincipal):
        raise HTTPException(status_code=403, detail="Invalid principal type")

    owner_id = user.subject_id

    # Default to today if not specified
    story_date = request.story_date if request else None
    if not story_date:
        story_date = datetime.now().strftime("%Y-%m-%d")

    story_id = f"story_{story_date}"

    logger.info(
        "Story generation requested",
        extra={
            "trip_id": str(trip_id),
            "story_date": story_date,
            "owner_id": owner_id,
        },
    )

    # Check if story already exists (idempotency)
    existing_story = story_repository.get_story(
        story_id=story_id,
        owner_id=owner_id,
        trip_id=str(trip_id),
    )

    if existing_story:
        logger.info("Story already exists", extra={"story_id": story_id})
        return GenerateStoryResponse(
            story_id=story_id,
            status=existing_story.status.value,
            message="Story already exists",
        )

    # Extract token for context fetching
    token = authorization.split(" ", 1)[1] if authorization and authorization.startswith("Bearer ") else None

    # Generate story
    story = await story_generation_service.generate_story(
        owner_id=owner_id,
        trip_id=trip_id,
        story_date=story_date,
        owner_token=token,
    )

    # Persist story
    story_repository.create_story(story)

    # Update metrics
    if stories_generated_counter:
        stories_generated_counter.add(
            1,
            {"status": story.status.value, "model": story.model},
        )

    logger.info(
        "Story generation completed",
        extra={
            "story_id": story_id,
            "status": story.status.value,
        },
    )

    return GenerateStoryResponse(
        story_id=story_id,
        status=story.status.value,
        message="Story generated successfully" if story.status.value == "completed" else "Story generation failed",
    )


@router.get("/{trip_id}", response_model=List[Story])
async def list_stories(
    trip_id: UUID,
    auth_ctx: AuthContext = Depends(auth_dependency),
):
    """
    List all stories for a trip.
    
    Args:
        trip_id: Trip ID
        auth_ctx: Authentication context
        
    Returns:
        List of stories
    """
    if not story_repository:
        raise HTTPException(status_code=503, detail="Service not initialized")

    # Only users can list stories
    if not auth_ctx.is_user:
        raise HTTPException(status_code=403, detail="Only users can list stories")

    from shared.auth.models import UserPrincipal
    user = auth_ctx.principal
    if not isinstance(user, UserPrincipal):
        raise HTTPException(status_code=403, detail="Invalid principal type")

    owner_id = user.subject_id

    logger.info(
        "Listing stories",
        extra={
            "trip_id": str(trip_id),
            "owner_id": owner_id,
        },
    )

    stories = story_repository.list_stories_by_trip(
        owner_id=owner_id,
        trip_id=str(trip_id),
    )

    # Update metrics
    if stories_viewed_counter:
        stories_viewed_counter.add(len(stories))

    return stories


@router.get("/{trip_id}/{story_id}", response_model=Story)
async def get_story(
    trip_id: UUID,
    story_id: str,
    auth_ctx: AuthContext = Depends(auth_dependency),
):
    """
    Get a specific story.
    
    Args:
        trip_id: Trip ID
        story_id: Story ID
        auth_ctx: Authentication context
        
    Returns:
        Story details
    """
    if not story_repository:
        raise HTTPException(status_code=503, detail="Service not initialized")

    # Only users can get stories
    if not auth_ctx.is_user:
        raise HTTPException(status_code=403, detail="Only users can get stories")

    from shared.auth.models import UserPrincipal
    user = auth_ctx.principal
    if not isinstance(user, UserPrincipal):
        raise HTTPException(status_code=403, detail="Invalid principal type")

    owner_id = user.subject_id

    logger.info(
        "Fetching story",
        extra={
            "trip_id": str(trip_id),
            "story_id": story_id,
            "owner_id": owner_id,
        },
    )

    story = story_repository.get_story(
        story_id=story_id,
        owner_id=owner_id,
        trip_id=str(trip_id),
    )

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    # Update metrics
    if stories_viewed_counter:
        stories_viewed_counter.add(1)

    return story
