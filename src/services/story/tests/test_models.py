"""Tests for story models."""
from datetime import datetime, UTC
from uuid import uuid4

import pytest

from models.story import Story, StoryDocument, StorySection, StoryStatus


def test_story_model_creation():
    """Test creating a Story model."""
    trip_id = uuid4()
    owner_id = "test-owner-123"
    story_date = "2025-12-07"

    story = Story(
        id=f"story_{story_date}",
        owner_id=owner_id,
        trip_id=trip_id,
        story_date=story_date,
        status=StoryStatus.COMPLETED,
        summary="A wonderful day in Prague",
        sections=[
            StorySection(title="Morning", content="Explored the Old Town"),
            StorySection(title="Evening", content="Enjoyed Czech cuisine"),
        ],
    )

    assert story.id == f"story_{story_date}"
    assert story.owner_id == owner_id
    assert story.trip_id == trip_id
    assert story.story_date == story_date
    assert story.status == StoryStatus.COMPLETED
    assert len(story.sections) == 2
    assert story.sections[0].title == "Morning"


def test_story_document_from_story():
    """Test converting Story to StoryDocument."""
    trip_id = uuid4()
    story = Story(
        id="story_2025-12-07",
        owner_id="owner-123",
        trip_id=trip_id,
        story_date="2025-12-07",
        status=StoryStatus.COMPLETED,
        summary="Test summary",
        sections=[],
    )

    doc = StoryDocument.from_story(story)

    assert doc.id == story.id
    assert doc.owner_id == story.owner_id
    assert str(doc.trip_id) == str(trip_id)
    assert doc.story_date == story.story_date


def test_story_document_to_story():
    """Test converting StoryDocument to Story."""
    trip_id = uuid4()
    doc = StoryDocument(
        id="story_2025-12-07",
        owner_id="owner-123",
        trip_id=trip_id,
        story_date="2025-12-07",
        status=StoryStatus.COMPLETED,
        summary="Test summary",
        sections=[],
    )

    story = doc.to_story()

    assert story.id == doc.id
    assert story.owner_id == doc.owner_id
    assert str(story.trip_id) == str(doc.trip_id)
    assert story.story_date == doc.story_date


def test_story_status_enum():
    """Test StoryStatus enum values."""
    assert StoryStatus.PENDING.value == "pending"
    assert StoryStatus.IN_PROGRESS.value == "in_progress"
    assert StoryStatus.COMPLETED.value == "completed"
    assert StoryStatus.FAILED.value == "failed"


def test_story_section_validation():
    """Test StorySection validation."""
    section = StorySection(
        title="Morning Adventure",
        content="Fluffy explored the city streets",
    )

    assert section.title == "Morning Adventure"
    assert section.content == "Fluffy explored the city streets"


def test_story_with_error_message():
    """Test Story with error status and message."""
    story = Story(
        id="story_2025-12-07",
        owner_id="owner-123",
        trip_id=uuid4(),
        story_date="2025-12-07",
        status=StoryStatus.FAILED,
        summary="",
        sections=[],
        error_message="OpenAI API rate limit exceeded",
    )

    assert story.status == StoryStatus.FAILED
    assert story.error_message == "OpenAI API rate limit exceeded"
