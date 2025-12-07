"""Data models for the story service."""
from datetime import datetime, UTC
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, field_serializer


class StoryStatus(str, Enum):
    """Story generation status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class StorySection(BaseModel):
    """Section within a story."""

    title: str = Field(..., max_length=100, description="Section title")
    content: str = Field(..., max_length=2000, description="Section content")


class StoryBase(BaseModel):
    """Base story model with common fields."""

    trip_id: UUID = Field(..., description="ID of the trip this story belongs to")
    story_date: str = Field(..., description="Date of the story (YYYY-MM-DD)")
    summary: str = Field(..., max_length=1000, description="Story summary")
    sections: list[StorySection] = Field(default_factory=list, description="Story sections")


class StoryCreate(StoryBase):
    """Model for creating a new story."""

    pass


class Story(StoryBase):
    """Complete story model with all fields."""

    id: str = Field(..., description="Unique story identifier (story_{date})")
    owner_id: str = Field(..., description="Entra object ID of the toy owner")
    status: StoryStatus = Field(default=StoryStatus.PENDING, description="Story generation status")
    context_version: str = Field(default="v1", description="Version of context used")
    prompt_version: str = Field(default="v1", description="Version of prompt used")
    model: str = Field(default="gpt-4o-mini", description="Model used for generation")
    error_message: str | None = Field(None, description="Error message if generation failed")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Creation timestamp")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Last modification timestamp")

    @field_serializer('trip_id')
    def serialize_trip_id(self, value: UUID) -> str:
        """Serialize UUID to string."""
        return str(value)

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime to ISO format."""
        return value.isoformat() if value else None


class StoryDocument(Story):
    """Story model for Cosmos DB storage (includes partition key fields)."""

    model_config = ConfigDict(
        populate_by_name=True,
    )

    @field_validator('created_at', 'updated_at', mode='before')
    @classmethod
    def parse_datetime(cls, value):
        """Parse datetime strings from Cosmos DB, handling various formats."""
        if isinstance(value, str):
            # Handle strings with Z suffix and timezone offset
            if value.endswith('+00:00Z'):
                value = value[:-1]  # Remove the 'Z' suffix
            elif value.endswith('Z'):
                # Replace Z with +00:00 for proper timezone parsing
                value = value[:-1] + '+00:00'

            # Parse the string back to datetime
            return datetime.fromisoformat(value)
        return value

    @classmethod
    def from_story(cls, story: Story) -> "StoryDocument":
        """Create a Cosmos DB document from a Story model."""
        data = {
            "id": story.id,
            "owner_id": story.owner_id,
            "trip_id": str(story.trip_id),
            "story_date": story.story_date,
            "status": story.status,
            "summary": story.summary,
            "sections": [s.model_dump() for s in story.sections],
            "context_version": story.context_version,
            "prompt_version": story.prompt_version,
            "model": story.model,
            "error_message": story.error_message,
            "created_at": story.created_at,
            "updated_at": story.updated_at,
        }
        return cls(**data)

    def to_story(self) -> Story:
        """Convert Cosmos DB document to Story model."""
        data = self.model_dump()
        return Story(**data)


class StoryJobMessage(BaseModel):
    """Message for story generation job queue."""

    owner_id: str = Field(..., description="Owner ID")
    trip_id: str = Field(..., description="Trip ID")
    story_date: str = Field(..., description="Story date (YYYY-MM-DD)")
    correlation_id: str | None = Field(None, description="Correlation ID for tracking")
