"""Tests for addon models."""
import pytest
from uuid import UUID, uuid4
from datetime import datetime, UTC

from models import (
    AddonOrder,
    AddonOrderCreate,
    AddonOrderStatus,
    AddonType,
    MediaReference,
    FulfillmentMessage,
)


def test_addon_order_create():
    """Test creating an AddonOrderCreate model."""
    order_data = AddonOrderCreate(
        addon_type=AddonType.BERET,
        notes="Make it red"
    )
    
    assert order_data.addon_type == AddonType.BERET
    assert order_data.notes == "Make it red"


def test_addon_order_create_strips_whitespace():
    """Test that notes are stripped of whitespace."""
    order_data = AddonOrderCreate(
        addon_type=AddonType.SUNGLASSES,
        notes="  Some notes  "
    )
    
    assert order_data.notes == "Some notes"


def test_addon_order_create_empty_notes():
    """Test that empty notes become None."""
    order_data = AddonOrderCreate(
        addon_type=AddonType.HAT,
        notes="   "
    )
    
    assert order_data.notes is None


def test_addon_order_full():
    """Test creating a full AddonOrder model."""
    trip_id = uuid4()
    order = AddonOrder(
        owner_id="owner-123",
        trip_id=trip_id,
        addon_type=AddonType.SCARF,
        notes="Blue scarf please",
        status=AddonOrderStatus.PENDING,
        idempotency_key="test-key-123"
    )
    
    assert order.owner_id == "owner-123"
    assert order.trip_id == trip_id
    assert order.addon_type == AddonType.SCARF
    assert order.notes == "Blue scarf please"
    assert order.status == AddonOrderStatus.PENDING
    assert order.idempotency_key == "test-key-123"
    assert order.requested_at is not None
    assert order.fulfilled_at is None
    assert order.error_message is None
    assert order.media_ref is None


def test_addon_order_default_id():
    """Test that ID is auto-generated."""
    order = AddonOrder(
        owner_id="owner-123",
        trip_id=uuid4(),
        addon_type=AddonType.BERET
    )
    
    assert order.id is not None
    assert order.id.startswith("addon_")


def test_media_reference():
    """Test MediaReference model."""
    media_ref = MediaReference(
        type="gallery",
        blob_name="gallery/trip-123/addon-456_beret.png"
    )
    
    assert media_ref.type == "gallery"
    assert media_ref.blob_name == "gallery/trip-123/addon-456_beret.png"


def test_media_reference_invalid_type():
    """Test that invalid media type raises error."""
    with pytest.raises(ValueError, match="Invalid media type"):
        MediaReference(
            type="invalid",
            blob_name="some-blob"
        )


def test_fulfillment_message():
    """Test FulfillmentMessage model."""
    trip_id = str(uuid4())
    msg = FulfillmentMessage(
        owner_id="owner-123",
        trip_id=trip_id,
        order_id="addon_abc123",
        addon_type="beret",
        media_style="french"
    )
    
    assert msg.owner_id == "owner-123"
    assert msg.trip_id == trip_id
    assert msg.order_id == "addon_abc123"
    assert msg.addon_type == "beret"
    assert msg.media_style == "french"
    assert msg.correlation_id is not None


def test_fulfillment_message_invalid_trip_id():
    """Test that invalid trip_id raises error."""
    with pytest.raises(ValueError, match="Invalid UUID format"):
        FulfillmentMessage(
            owner_id="owner-123",
            trip_id="not-a-uuid",
            order_id="addon_abc123",
            addon_type="beret"
        )


def test_addon_order_status_transitions():
    """Test that all status values are valid."""
    assert AddonOrderStatus.PENDING == "pending"
    assert AddonOrderStatus.IN_PROGRESS == "in_progress"
    assert AddonOrderStatus.FULFILLED == "fulfilled"
    assert AddonOrderStatus.FAILED == "failed"


def test_addon_types():
    """Test that all addon types are valid."""
    assert AddonType.BERET == "beret"
    assert AddonType.SUNGLASSES == "sunglasses"
    assert AddonType.SCARF == "scarf"
    assert AddonType.HAT == "hat"
    assert AddonType.BACKPACK == "backpack"
