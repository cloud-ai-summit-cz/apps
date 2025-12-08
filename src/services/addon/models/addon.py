"""Data models for addon orders."""
from datetime import datetime, UTC
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, field_serializer


class AddonOrderStatus(str, Enum):
    """Status of an addon order."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    FULFILLED = "fulfilled"
    FAILED = "failed"


class AddonType(str, Enum):
    """Types of addon items that can be ordered."""

    BERET = "beret"
    SUNGLASSES = "sunglasses"
    SCARF = "scarf"
    HAT = "hat"
    BACKPACK = "backpack"


class MediaReference(BaseModel):
    """Reference to media stored in blob storage."""

    type: str = Field(default="gallery", description="Type of media reference")
    blob_name: str = Field(..., description="Blob storage reference")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate media reference type."""
        if v not in ["gallery", "fulfillment"]:
            raise ValueError(f"Invalid media type: {v}")
        return v


class AddonOrderBase(BaseModel):
    """Base addon order model with common fields."""

    addon_type: AddonType = Field(..., description="Type of addon being ordered")
    notes: str | None = Field(None, max_length=500, description="Optional notes for fulfillment")

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: str | None) -> str | None:
        """Sanitize and validate notes."""
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None
        return v


class AddonOrderCreate(AddonOrderBase):
    """Model for creating a new addon order."""

    pass


class AddonOrder(AddonOrderBase):
    """Complete addon order model with all fields."""

    id: str = Field(default_factory=lambda: f"addon_{uuid4().hex[:12]}", description="Unique order identifier")
    owner_id: str = Field(..., description="Entra object ID of the toy owner")
    trip_id: UUID = Field(..., description="ID of the trip this order is for")
    status: AddonOrderStatus = Field(default=AddonOrderStatus.PENDING, description="Current order status")
    media_ref: MediaReference | None = Field(None, description="Reference to fulfillment media")
    idempotency_key: str | None = Field(None, description="Idempotency key for duplicate prevention")
    requested_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Order creation timestamp")
    fulfilled_at: datetime | None = Field(None, description="Fulfillment completion timestamp")
    error_message: str | None = Field(None, max_length=1000, description="Error message if order failed")

    @field_serializer('trip_id')
    def serialize_trip_id(self, value: UUID) -> str:
        """Serialize UUID to string."""
        return str(value)

    @field_serializer('requested_at', 'fulfilled_at')
    def serialize_datetime(self, value: datetime | None) -> str | None:
        """Serialize datetime to ISO format."""
        return value.isoformat() if value else None


class AddonOrderDocument(AddonOrder):
    """Addon order model for Cosmos DB storage (includes partition key fields)."""

    model_config = ConfigDict(
        populate_by_name=True,
    )

    # Hierarchical partition key fields
    # HPK: /ownerId/tripId for high cardinality and owner isolation
    # Note: Cosmos SDK expects these as separate fields in the document

    @field_validator('requested_at', 'fulfilled_at', mode='before')
    @classmethod
    def parse_datetime(cls, value):
        """Parse datetime strings from Cosmos DB."""
        if isinstance(value, str):
            if value.endswith('+00:00Z'):
                value = value[:-1]
            elif value.endswith('Z'):
                value = value[:-1] + '+00:00'
            return datetime.fromisoformat(value)
        return value

    @classmethod
    def from_order(cls, order: AddonOrder) -> "AddonOrderDocument":
        """Create a Cosmos DB document from an AddonOrder model."""
        data = order.model_dump()
        return cls(**data)

    def to_order(self) -> AddonOrder:
        """Convert Cosmos DB document to AddonOrder model."""
        data = self.model_dump()
        return AddonOrder(**data)


class FulfillmentMessage(BaseModel):
    """Message format for addon fulfillment queue."""

    owner_id: str = Field(..., description="Owner ID for partition key")
    trip_id: str = Field(..., description="Trip ID for partition key")
    order_id: str = Field(..., description="Order ID to fulfill")
    addon_type: str = Field(..., description="Type of addon to generate")
    media_style: str | None = Field(None, description="Optional style hint for media generation")
    correlation_id: str = Field(default_factory=lambda: uuid4().hex, description="Correlation ID for tracing")

    @field_validator('trip_id')
    @classmethod
    def validate_trip_id(cls, v: str) -> str:
        """Validate trip_id is a valid UUID string."""
        try:
            UUID(v)
        except ValueError:
            raise ValueError(f"Invalid UUID format for trip_id: {v}")
        return v
