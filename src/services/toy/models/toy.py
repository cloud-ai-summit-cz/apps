"""Data models for the toy service."""
from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ToyBase(BaseModel):
    """Base toy model with common fields."""

    name: str = Field(..., min_length=1, max_length=100, description="Display name of the toy")
    description: str | None = Field(None, max_length=500, description="Toy description or backstory")


class ToyCreate(ToyBase):
    """Model for creating a new toy."""

    pass


class ToyUpdate(BaseModel):
    """Model for updating a toy (partial update)."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)

    @field_validator("name")
    @classmethod
    def validate_name_not_empty(cls, v: str | None) -> str | None:
        """Ensure name is not just whitespace if provided."""
        if v is not None and not v.strip():
            raise ValueError("Name cannot be empty or whitespace only")
        return v.strip() if v else None


class Toy(ToyBase):
    """Complete toy model with all fields."""

    model_config = ConfigDict(
        json_encoders={
            UUID: str,
            datetime: lambda v: v.isoformat() + "Z" if v else None,
        }
    )

    id: UUID = Field(default_factory=uuid4, description="Unique toy identifier")
    owner_oid: str = Field(..., description="Entra object ID of the owner")
    avatar_blob_name: str | None = Field(None, description="Internal blob storage reference")
    has_avatar: bool = Field(False, description="Indicates if toy has an avatar image")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Registration timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last modification timestamp")


class ToyDocument(Toy):
    """Toy model for Cosmos DB storage (includes partition key field)."""

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            UUID: str,
            datetime: lambda v: v.isoformat() + "Z" if v else None,
        },
    )

    # Cosmos DB fields
    toy_id: str = Field(alias="id", description="Partition key (same as id)")

    @classmethod
    def from_toy(cls, toy: Toy) -> "ToyDocument":
        """Create a Cosmos DB document from a Toy model."""
        data = toy.model_dump()
        data["id"] = str(toy.id)  # Convert UUID to string for Pydantic validation
        data["toy_id"] = str(toy.id)
        return cls(**data)

    def to_toy(self) -> Toy:
        """Convert Cosmos DB document to Toy model."""
        data = self.model_dump(exclude={"toy_id"})
        return Toy(**data)
