"""Integration tests for toy service with mocked auth."""
import os
from io import BytesIO
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from auth.dependencies import get_auth_context
from auth.models import AuthContext
from config import settings
from main import app
from repositories import ToyRepository
from services import BlobService
import routes.toy_routes as toy_routes


@pytest.fixture(scope="module")
def toy_repo():
    """Create a toy repository for integration tests."""
    repo = ToyRepository(
        cosmos_endpoint=settings.cosmos_endpoint,
        database_name=settings.cosmos_database_name,
        container_name=settings.cosmos_container_name,
    )
    return repo


@pytest.fixture(scope="module")
def blob_svc():
    """Create a blob service for integration tests."""
    svc = BlobService(
        storage_account_url=settings.storage_account_url,
        container_name=settings.blob_container_avatars,
    )
    yield svc
    svc.close()


@pytest.fixture(scope="module")
def test_client(toy_repo, blob_svc):
    """Create a test client for the FastAPI app with initialized dependencies."""
    # Inject the real repository and service instances for testing
    toy_routes.toy_repository = toy_repo
    toy_routes.blob_service = blob_svc
    
    yield TestClient(app)
    
    # Cleanup
    toy_routes.toy_repository = None
    toy_routes.blob_service = None


@pytest.fixture
def override_auth(test_auth_context):
    """Override auth dependency with mock."""

    def _mock_auth():
        return test_auth_context

    app.dependency_overrides[get_auth_context] = _mock_auth
    yield
    app.dependency_overrides.clear()


@pytest.mark.usefixtures("integration_test_marker")
class TestToyIntegration:
    """Integration tests for toy service (real DB/Blob, mocked auth)."""

    def test_create_and_get_toy(self, test_client, override_auth):
        """Test creating and retrieving a toy."""
        toy_id = None
        try:
            # Create toy
            toy_data = {"name": "Test Teddy", "description": "A test teddy bear"}
            response = test_client.post("/toy", json=toy_data)

            assert response.status_code == 201
            toy = response.json()
            assert toy["name"] == "Test Teddy"
            assert toy["owner_oid"] == "test-user-oid"
            assert toy["has_avatar"] is False

            toy_id = toy["id"]

            # Get toy
            response = test_client.get(f"/toy/{toy_id}")
            assert response.status_code == 200
            retrieved_toy = response.json()
            assert retrieved_toy["id"] == toy_id
            assert retrieved_toy["name"] == "Test Teddy"
        finally:
            # Cleanup
            if toy_id:
                test_client.delete(f"/toy/{toy_id}")

    def test_update_toy(self, test_client, override_auth):
        """Test updating a toy."""
        toy_id = None
        try:
            # Create toy
            toy_data = {"name": "Original Name"}
            response = test_client.post("/toy", json=toy_data)
            toy_id = response.json()["id"]

            # Update toy
            update_data = {"name": "Updated Name", "description": "New description"}
            response = test_client.patch(f"/toy/{toy_id}", json=update_data)

            assert response.status_code == 200
            updated_toy = response.json()
            assert updated_toy["name"] == "Updated Name"
            assert updated_toy["description"] == "New description"
        finally:
            # Cleanup
            if toy_id:
                test_client.delete(f"/toy/{toy_id}")

    def test_list_toys(self, test_client, override_auth):
        """Test listing toys."""
        toy_ids = []
        try:
            # Create a few toys
            for i in range(3):
                response = test_client.post("/toy", json={"name": f"Toy {i}"})
                toy_ids.append(response.json()["id"])

            # List toys
            response = test_client.get("/toy")
            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert "total" in data
            assert len(data["items"]) >= 3

            # Filter by owner
            response = test_client.get("/toy?owner_oid=test-user-oid")
            assert response.status_code == 200
            data = response.json()
            assert all(toy["owner_oid"] == "test-user-oid" for toy in data["items"])
        finally:
            # Cleanup
            for toy_id in toy_ids:
                test_client.delete(f"/toy/{toy_id}")

    def test_delete_toy(self, test_client, override_auth):
        """Test deleting a toy."""
        # Create toy
        response = test_client.post("/toy", json={"name": "To Delete"})
        toy_id = response.json()["id"]

        # Delete toy
        response = test_client.delete(f"/toy/{toy_id}")
        assert response.status_code == 204

        # Verify deleted
        response = test_client.get(f"/toy/{toy_id}")
        assert response.status_code == 404

    def test_upload_and_get_avatar(self, test_client, override_auth):
        """Test uploading and retrieving an avatar."""
        toy_id = None
        try:
            # Create toy
            response = test_client.post("/toy", json={"name": "Avatar Toy"})
            toy_id = response.json()["id"]

            # Create a fake image file
            fake_image = BytesIO(b"fake image content")
            fake_image.name = "avatar.jpg"

            # Upload avatar
            response = test_client.post(
                f"/toy/{toy_id}/avatar", files={"file": ("avatar.jpg", fake_image, "image/jpeg")}
            )

            assert response.status_code == 200
            updated_toy = response.json()
            assert updated_toy["has_avatar"] is True
            assert updated_toy["avatar_blob_name"] is not None

            # Get avatar
            response = test_client.get(f"/toy/{toy_id}/avatar")
            assert response.status_code == 200
            assert response.headers["content-type"] == "image/jpeg"
            assert "cache-control" in response.headers
        finally:
            # Cleanup
            if toy_id:
                test_client.delete(f"/toy/{toy_id}")

    def test_delete_avatar(self, test_client, override_auth):
        """Test deleting an avatar."""
        toy_id = None
        try:
            # Create toy with avatar
            response = test_client.post("/toy", json={"name": "Avatar Delete Test"})
            toy_id = response.json()["id"]

            fake_image = BytesIO(b"fake image")
            test_client.post(f"/toy/{toy_id}/avatar", files={"file": ("avatar.jpg", fake_image, "image/jpeg")})

            # Delete avatar
            response = test_client.delete(f"/toy/{toy_id}/avatar")
            assert response.status_code == 204

            # Verify avatar deleted
            response = test_client.get(f"/toy/{toy_id}")
            toy = response.json()
            assert toy["has_avatar"] is False
        finally:
            # Cleanup
            if toy_id:
                test_client.delete(f"/toy/{toy_id}")

    def test_ownership_check(self, test_client, test_auth_context, another_user_auth_context):
        """Test that non-owners cannot modify toys."""
        toy_id = None
        try:
            # Create toy as first user
            app.dependency_overrides[get_auth_context] = lambda: test_auth_context

            response = test_client.post("/toy", json={"name": "Owner Test"})
            toy_id = response.json()["id"]

            # Try to update as different user
            app.dependency_overrides[get_auth_context] = lambda: another_user_auth_context

            response = test_client.patch(f"/toy/{toy_id}", json={"name": "Hacked Name"})
            assert response.status_code == 403

            # Try to delete as different user
            response = test_client.delete(f"/toy/{toy_id}")
            assert response.status_code == 403
        finally:
            # Cleanup (as original owner)
            if toy_id:
                app.dependency_overrides[get_auth_context] = lambda: test_auth_context
                test_client.delete(f"/toy/{toy_id}")
            app.dependency_overrides.clear()
