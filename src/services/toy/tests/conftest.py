"""Pytest configuration and fixtures."""
import os
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from dotenv import load_dotenv

# Load .env file before any tests run
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared"))

from auth.models import AuthContext, UserPrincipal, SystemPrincipal


@pytest.fixture
def test_user_principal() -> UserPrincipal:
    """Create a mock user principal for testing."""
    return UserPrincipal(
        subject_id="test-user-oid",
        oid="test-user-oid",
        display_name="Test User",
        is_system=False,
        roles=[],
        scopes=["App.Access"],
    )


@pytest.fixture
def test_system_principal() -> SystemPrincipal:
    """Create a mock system principal for testing."""
    return SystemPrincipal(
        subject_id="test-system-app-id",
        app_id="test-system-app-id",
        is_system=True,
        roles=["System.Service"],
        scopes=[],
    )


@pytest.fixture
def test_auth_context(test_user_principal) -> AuthContext:
    """Create a mock auth context for testing."""
    return AuthContext(
        principal=test_user_principal,
        raw_claims={"oid": "test-user-oid", "scp": "App.Access"},
        token_id="test-token-id",
    )


@pytest.fixture
def mock_auth_dependency(test_auth_context):
    """
    Override FastAPI auth dependency to inject mock auth context.

    Usage in test:
        app.dependency_overrides[get_auth_context] = mock_auth_dependency
    """

    def _get_mock_auth():
        return test_auth_context

    return _get_mock_auth


@pytest.fixture
def another_user_principal() -> UserPrincipal:
    """Create a different user principal for ownership tests."""
    return UserPrincipal(
        subject_id="another-user-oid",
        oid="another-user-oid",
        display_name="Another User",
        is_system=False,
        roles=[],
        scopes=["App.Access"],
    )


@pytest.fixture
def another_user_auth_context(another_user_principal) -> AuthContext:
    """Create auth context for another user."""
    return AuthContext(
        principal=another_user_principal,
        raw_claims={"oid": "another-user-oid", "scp": "App.Access"},
        token_id="another-token-id",
    )


# Environment checks
@pytest.fixture(scope="session")
def check_azure_credentials():
    """
    Check if Azure credentials are available for integration tests.

    Integration tests will be skipped if credentials are not available.
    """
    required_vars = ["COSMOS_ENDPOINT", "STORAGE_ACCOUNT_URL"]
    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        pytest.skip(f"Integration tests require environment variables: {', '.join(missing)}")


@pytest.fixture
def integration_test_marker(check_azure_credentials):
    """
    Marker for tests that require real Azure resources.

    Use with: @pytest.mark.usefixtures("integration_test_marker")
    """
    pass
