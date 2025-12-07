"""REST API routes for story operations."""
import logging
from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel

from models.story import Story, StoryCreate
from repositories.story_repository import StoryRepository
from services.story_generation_service import StoryGenerationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stories", tags=["stories"])

# Global instances (injected at startup)
story_repository: StoryRepository | None = None
story_generation_service: StoryGenerationService | None = None
tracer = None
stories_generated_counter = None
stories_viewed_counter = None


def get_owner_id_from_token(authorization: str = Header(None)) -> str:
    """
    Extract owner ID from Authorization header.
    
    For now, this is a placeholder. In production, this should validate
    the JWT token and extract the owner ID (Entra OID).
    
    Args:
        authorization: Authorization header with Bearer token
        
    Returns:
        Owner ID (Entra OID)
        
    Raises:
        HTTPException: If token is missing or invalid
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization token")
    
    # TODO: Implement proper JWT validation and extract owner_id
    # For now, return a placeholder
    return "placeholder-owner-id"


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
    owner_id: str = Depends(get_owner_id_from_token),
):
    """
    Trigger story generation for a trip.
    
    This endpoint is idempotent per (tripId, storyDate) - if a story
    already exists for the date, it returns the existing story.
    
    Args:
        trip_id: Trip ID
        request: Generation request with optional story_date
        owner_id: Owner ID from authentication token
        
    Returns:
        Story generation response
    """
    if not story_repository or not story_generation_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

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

    # Generate story
    story = await story_generation_service.generate_story(
        owner_id=owner_id,
        trip_id=trip_id,
        story_date=story_date,
        owner_token=None,  # TODO: Pass actual token
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
    owner_id: str = Depends(get_owner_id_from_token),
):
    """
    List all stories for a trip.
    
    Args:
        trip_id: Trip ID
        owner_id: Owner ID from authentication token
        
    Returns:
        List of stories
    """
    if not story_repository:
        raise HTTPException(status_code=503, detail="Service not initialized")

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
    owner_id: str = Depends(get_owner_id_from_token),
):
    """
    Get a specific story.
    
    Args:
        trip_id: Trip ID
        story_id: Story ID
        owner_id: Owner ID from authentication token
        
    Returns:
        Story details
    """
    if not story_repository:
        raise HTTPException(status_code=503, detail="Service not initialized")

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
