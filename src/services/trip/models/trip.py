"""Data models for the trip service."""
from datetime import datetime, UTC
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, field_serializer


class LegStatus(str, Enum):
    """Status of a trip leg."""

    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class TripStatus(str, Enum):
    """Overall trip status."""

    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Leg(BaseModel):
    """A single leg/segment within a trip."""

    leg_number: int = Field(..., ge=1, description="Sequential leg number (1-indexed)")
    location_name: str = Field(..., min_length=1, max_length=200, description="Location name (city, landmark)")
    country_code: str = Field(..., min_length=2, max_length=2, description="ISO 3166-1 alpha-2 country code")
    planned_arrival: datetime | None = Field(None, description="Planned arrival time (optional)")
    actual_arrival: datetime | None = Field(None, description="Actual arrival time")
    status: LegStatus = Field(default=LegStatus.PLANNED, description="Leg status")
    notes: str | None = Field(None, max_length=1000, description="Optional notes about the leg")

    @field_validator("country_code")
    @classmethod
    def validate_country_code(cls, v: str) -> str:
        """Ensure country code is uppercase."""
        return v.upper()

    @field_serializer('planned_arrival', 'actual_arrival')
    def serialize_datetime(self, value: datetime | None) -> str | None:
        """Serialize datetime to ISO format."""
        return value.isoformat() if value else None


class GalleryImage(BaseModel):
    """Gallery image metadata."""

    image_id: UUID = Field(default_factory=uuid4, description="Unique image identifier")
    leg_number: int = Field(..., ge=1, description="Associated leg number")
    blob_name: str = Field(..., description="Internal blob storage reference")
    caption: str | None = Field(None, max_length=500, description="Optional image caption")
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Upload timestamp")
    source: str = Field(default="user", description="Image source (user, addon, generated)")

    @field_serializer('image_id')
    def serialize_image_id(self, value: UUID) -> str:
        """Serialize UUID to string."""
        return str(value)

    @field_serializer('uploaded_at')
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime to ISO format."""
        return value.isoformat() if value else None


class TripBase(BaseModel):
    """Base trip model with common fields."""

    title: str = Field(..., min_length=1, max_length=200, description="Trip title")
    description: str | None = Field(None, max_length=1000, description="Trip description")
    public_tracking_enabled: bool = Field(default=False, description="Enable public location sharing")


class TripCreate(TripBase):
    """Model for creating a new trip."""

    toy_id: UUID = Field(..., description="ID of the toy taking this trip")
    legs: list[Leg] = Field(..., min_length=1, description="Ordered list of trip legs (at least one required)")

    @field_validator("legs")
    @classmethod
    def validate_leg_numbers(cls, v: list[Leg]) -> list[Leg]:
        """Ensure leg numbers are sequential starting from 1."""
        if not v:
            raise ValueError("At least one leg is required")

        leg_numbers = [leg.leg_number for leg in v]
        expected = list(range(1, len(v) + 1))

        if sorted(leg_numbers) != expected:
            raise ValueError(f"Leg numbers must be sequential from 1 to {len(v)}")

        if len(set(leg_numbers)) != len(leg_numbers):
            raise ValueError("Leg numbers must be unique")

        return v


class TripUpdate(BaseModel):
    """Model for updating a trip (partial update)."""

    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=1000)
    public_tracking_enabled: bool | None = None
    status: TripStatus | None = None

    @field_validator("title")
    @classmethod
    def validate_title_not_empty(cls, v: str | None) -> str | None:
        """Ensure title is not just whitespace if provided."""
        if v is not None and not v.strip():
            raise ValueError("Title cannot be empty or whitespace only")
        return v.strip() if v else None


class Trip(TripBase):
    """Complete trip model with all fields."""

    id: UUID = Field(default_factory=uuid4, description="Unique trip identifier")
    toy_id: UUID = Field(..., description="ID of the toy taking this trip")
    owner_oid: str = Field(..., description="Entra object ID of the toy owner (denormalized for fast auth)")
    status: TripStatus = Field(default=TripStatus.PLANNED, description="Overall trip status")
    legs: list[Leg] = Field(default_factory=list, description="Ordered list of trip legs")
    gallery: list[GalleryImage] = Field(default_factory=list, description="Gallery images")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Creation timestamp")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Last modification timestamp")

    @field_serializer('id', 'toy_id')
    def serialize_id(self, value: UUID) -> str:
        """Serialize UUID to string."""
        return str(value)

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime to ISO format."""
        return value.isoformat() if value else None


class TripDocument(Trip):
    """Trip model for Cosmos DB storage (includes partition key field)."""

    model_config = ConfigDict(
        populate_by_name=True,
    )

    # Cosmos DB fields
    trip_id: str = Field(alias="id", description="Partition key (same as id)")

    @field_serializer('trip_id')
    def serialize_trip_id(self, value: UUID | str) -> str:
        """Serialize trip_id field to string."""
        return str(value)

    @field_validator('created_at', 'updated_at', mode='before')
    @classmethod
    def parse_datetime(cls, value):
        """Parse datetime strings from Cosmos DB, handling various formats."""
        if isinstance(value, str):
            # Handle strings with Z suffix and timezone offset (invalid format from old data)
            if value.endswith('+00:00Z'):
                value = value[:-1]  # Remove the 'Z' suffix, keep the timezone offset
            elif value.endswith('Z'):
                # Replace Z with +00:00 for proper timezone parsing
                value = value[:-1] + '+00:00'

            # Parse the string back to datetime
            return datetime.fromisoformat(value)
        return value

    @classmethod
    def from_trip(cls, trip: Trip) -> "TripDocument":
        """Create a Cosmos DB document from a Trip model."""
        # Extract data without using model_dump to avoid serialization issues
        data = {
            "title": trip.title,
            "description": trip.description,
            "public_tracking_enabled": trip.public_tracking_enabled,
            "id": str(trip.id),
            "trip_id": str(trip.id),
            "toy_id": str(trip.toy_id),
            "owner_oid": trip.owner_oid,
            "status": trip.status,
            "legs": [leg.model_dump() for leg in trip.legs],
            "gallery": [img.model_dump() for img in trip.gallery],
            "created_at": trip.created_at,
            "updated_at": trip.updated_at,
        }
        return cls(**data)

    def to_trip(self) -> Trip:
        """Convert Cosmos DB document to Trip model."""
        data = self.model_dump(exclude={"trip_id"})
        return Trip(**data)
