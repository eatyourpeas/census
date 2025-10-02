"""
Tests for external dataset API endpoints.

These tests verify authentication, permissions, caching, error handling,
and response formats for the dataset endpoints.

Permission Model:
- Dataset endpoints require authentication (IsAuthenticated)
- They do NOT require survey-specific or organization-specific permissions
- This is intentional: datasets are reference data (hospitals, trusts) that
  any authenticated user might need when building surveys
- The actual survey editing is protected by survey-level permissions
"""
import json
from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.core.cache import cache
import pytest
import requests
from rest_framework.test import APIClient

from census_app.surveys.external_datasets import (
    DatasetFetchError,
    AVAILABLE_DATASETS,
)
from census_app.surveys.models import Organization, OrganizationMembership

User = get_user_model()
TEST_PASSWORD = "test-pass"


def auth_hdr(client, username: str, password: str) -> dict:
    """Helper to get JWT auth header."""
    resp = client.post(
        "/api/token",
        data=json.dumps({"username": username, "password": password}),
        content_type="application/json",
    )
    assert resp.status_code == 200, resp.content
    return {"HTTP_AUTHORIZATION": f"Bearer {resp.json()['access']}"}


@pytest.fixture
def authenticated_user(django_user_model):
    """Create and return an authenticated user."""
    return django_user_model.objects.create_user(
        username="testuser", password=TEST_PASSWORD
    )


@pytest.fixture
def api_client():
    """Return a fresh API client."""
    return APIClient()


@pytest.fixture(autouse=True)
def clear_cache_between_tests():
    """Clear cache before each test."""
    cache.clear()
    yield
    cache.clear()


# ============================================================================
# Authentication Tests
# ============================================================================


@pytest.mark.django_db
def test_list_datasets_requires_authentication(client):
    """Anonymous users cannot list datasets."""
    resp = client.get("/api/datasets/")
    assert resp.status_code in (401, 403)


@pytest.mark.django_db
def test_get_dataset_requires_authentication(client):
    """Anonymous users cannot get dataset details."""
    resp = client.get("/api/datasets/hospitals_england/")
    assert resp.status_code in (401, 403)


@pytest.mark.django_db
def test_list_datasets_authenticated_allowed(client, authenticated_user):
    """Authenticated users can list datasets."""
    hdrs = auth_hdr(client, "testuser", TEST_PASSWORD)
    resp = client.get("/api/datasets/", **hdrs)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_get_dataset_authenticated_allowed(client, authenticated_user):
    """Authenticated users can get dataset details."""
    hdrs = auth_hdr(client, "testuser", TEST_PASSWORD)

    # Mock the external API call
    mock_options = ["Hospital A", "Hospital B", "Hospital C"]
    with patch("census_app.surveys.external_datasets.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"options": mock_options}
        mock_get.return_value = mock_response

        resp = client.get("/api/datasets/hospitals_england/", **hdrs)
        assert resp.status_code == 200


# ============================================================================
# List Datasets Tests
# ============================================================================


@pytest.mark.django_db
def test_list_datasets_returns_all_datasets(client, authenticated_user):
    """List endpoint returns all available datasets."""
    hdrs = auth_hdr(client, "testuser", TEST_PASSWORD)
    resp = client.get("/api/datasets/", **hdrs)

    assert resp.status_code == 200
    data = resp.json()
    assert "datasets" in data
    assert isinstance(data["datasets"], list)
    assert len(data["datasets"]) == len(AVAILABLE_DATASETS)

    # Verify each dataset has required fields
    for dataset in data["datasets"]:
        assert "key" in dataset
        assert "name" in dataset
        assert dataset["key"] in AVAILABLE_DATASETS
        assert dataset["name"] == AVAILABLE_DATASETS[dataset["key"]]


# ============================================================================
# Get Dataset Tests - Success Cases
# ============================================================================


@pytest.mark.django_db
def test_get_dataset_returns_options(client, authenticated_user):
    """Get dataset endpoint returns options from external API."""
    hdrs = auth_hdr(client, "testuser", TEST_PASSWORD)
    mock_options = ["Royal Free Hospital", "St Mary's Hospital", "Guy's Hospital"]

    with patch("census_app.surveys.external_datasets.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"options": mock_options}
        mock_get.return_value = mock_response

        resp = client.get("/api/datasets/hospitals_england/", **hdrs)

        assert resp.status_code == 200
        data = resp.json()
        assert data["dataset_key"] == "hospitals_england"
        assert data["options"] == mock_options
        assert len(data["options"]) == 3


@pytest.mark.django_db
def test_get_dataset_handles_list_response_format(client, authenticated_user):
    """Get dataset handles response that is a direct list."""
    hdrs = auth_hdr(client, "testuser", TEST_PASSWORD)
    mock_options = ["Trust A", "Trust B"]

    with patch("census_app.surveys.external_datasets.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_options  # Direct list, not wrapped
        mock_get.return_value = mock_response

        resp = client.get("/api/datasets/nhs_trusts/", **hdrs)

        assert resp.status_code == 200
        data = resp.json()
        assert data["options"] == mock_options


# ============================================================================
# Get Dataset Tests - Error Cases
# ============================================================================


@pytest.mark.django_db
def test_get_dataset_invalid_key_returns_400(client, authenticated_user):
    """Invalid dataset key returns 400."""
    hdrs = auth_hdr(client, "testuser", TEST_PASSWORD)
    resp = client.get("/api/datasets/invalid_key/", **hdrs)

    assert resp.status_code == 400
    data = resp.json()
    assert "error" in data
    assert "invalid_key" in data["error"].lower() or "unknown" in data["error"].lower()


@pytest.mark.django_db
def test_get_dataset_external_api_failure_returns_502(client, authenticated_user):
    """External API failure returns 502."""
    hdrs = auth_hdr(client, "testuser", TEST_PASSWORD)

    with patch("census_app.surveys.external_datasets.requests.get") as mock_get:
        mock_get.side_effect = requests.RequestException("Connection timeout")

        resp = client.get("/api/datasets/hospitals_wales/", **hdrs)

        assert resp.status_code == 502
        data = resp.json()
        assert "error" in data


@pytest.mark.django_db
def test_get_dataset_invalid_response_format_returns_502(client, authenticated_user):
    """Invalid response format from external API returns 502."""
    hdrs = auth_hdr(client, "testuser", TEST_PASSWORD)

    with patch("census_app.surveys.external_datasets.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"unexpected": "format"}  # Invalid structure
        mock_get.return_value = mock_response

        resp = client.get("/api/datasets/welsh_lhbs/", **hdrs)

        assert resp.status_code == 502
        data = resp.json()
        assert "error" in data


@pytest.mark.django_db
def test_get_dataset_non_string_options_returns_502(client, authenticated_user):
    """Non-string options in response returns 502."""
    hdrs = auth_hdr(client, "testuser", TEST_PASSWORD)

    with patch("census_app.surveys.external_datasets.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Options contain non-string values
        mock_response.json.return_value = {"options": [123, 456, "valid"]}
        mock_get.return_value = mock_response

        resp = client.get("/api/datasets/hospitals_england/", **hdrs)

        assert resp.status_code == 502
        data = resp.json()
        assert "error" in data


# ============================================================================
# Caching Tests
# ============================================================================


@pytest.mark.django_db
def test_get_dataset_caches_result(client, authenticated_user):
    """Successful dataset fetch is cached."""
    hdrs = auth_hdr(client, "testuser", TEST_PASSWORD)
    mock_options = ["Hospital 1", "Hospital 2"]

    with patch("census_app.surveys.external_datasets.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"options": mock_options}
        mock_get.return_value = mock_response

        # First call
        resp1 = client.get("/api/datasets/hospitals_england_wales/", **hdrs)
        assert resp1.status_code == 200
        assert mock_get.call_count == 1

        # Second call should use cache
        resp2 = client.get("/api/datasets/hospitals_england_wales/", **hdrs)
        assert resp2.status_code == 200
        assert mock_get.call_count == 1  # Still only 1 call

        # Both responses should be identical
        assert resp1.json() == resp2.json()


@pytest.mark.django_db
def test_get_dataset_cache_key_isolation(client, authenticated_user):
    """Different dataset keys have isolated caches."""
    hdrs = auth_hdr(client, "testuser", TEST_PASSWORD)

    with patch("census_app.surveys.external_datasets.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"options": ["A", "B"]}
        mock_get.return_value = mock_response

        # Fetch two different datasets
        client.get("/api/datasets/hospitals_england/", **hdrs)
        client.get("/api/datasets/nhs_trusts/", **hdrs)

        # Should have made 2 separate API calls
        assert mock_get.call_count == 2


@pytest.mark.django_db
def test_get_dataset_cache_survives_authentication_changes(
    client, django_user_model
):
    """Cached data is shared across users."""
    # Create two users
    user1 = django_user_model.objects.create_user(username="user1", password="pass1")
    user2 = django_user_model.objects.create_user(username="user2", password="pass2")

    mock_options = ["Shared Hospital"]

    with patch("census_app.surveys.external_datasets.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"options": mock_options}
        mock_get.return_value = mock_response

        # User 1 fetches dataset
        hdrs1 = auth_hdr(client, "user1", "pass1")
        resp1 = client.get("/api/datasets/hospitals_wales/", **hdrs1)
        assert resp1.status_code == 200
        assert mock_get.call_count == 1

        # User 2 fetches same dataset - should use cache
        hdrs2 = auth_hdr(client, "user2", "pass2")
        resp2 = client.get("/api/datasets/hospitals_wales/", **hdrs2)
        assert resp2.status_code == 200
        assert mock_get.call_count == 1  # No additional call

        assert resp1.json() == resp2.json()


# ============================================================================
# API Client Tests (force_authenticate)
# ============================================================================


@pytest.mark.django_db
def test_list_datasets_with_force_authenticate(api_client, authenticated_user):
    """Test list datasets using APIClient with force_authenticate."""
    api_client.force_authenticate(authenticated_user)
    resp = api_client.get("/api/datasets/")

    assert resp.status_code == 200
    assert "datasets" in resp.data


@pytest.mark.django_db
def test_get_dataset_with_force_authenticate(api_client, authenticated_user):
    """Test get dataset using APIClient with force_authenticate."""
    api_client.force_authenticate(authenticated_user)

    mock_options = ["Option 1", "Option 2"]
    with patch("census_app.surveys.external_datasets.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"options": mock_options}
        mock_get.return_value = mock_response

        resp = api_client.get("/api/datasets/nhs_trusts/")

        assert resp.status_code == 200
        assert resp.data["options"] == mock_options


# ============================================================================
# External API Configuration Tests
# ============================================================================


@pytest.mark.django_db
def test_external_api_receives_auth_header_when_configured(
    client, authenticated_user, settings
):
    """External API call includes auth header when API key is configured."""
    settings.EXTERNAL_DATASET_API_KEY = "test-api-key-123"
    hdrs = auth_hdr(client, "testuser", TEST_PASSWORD)

    with patch("census_app.surveys.external_datasets.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"options": ["A"]}
        mock_get.return_value = mock_response

        client.get("/api/datasets/hospitals_england/", **hdrs)

        # Verify the call was made with auth header
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert "headers" in call_kwargs
        assert "Authorization" in call_kwargs["headers"]
        assert call_kwargs["headers"]["Authorization"] == "Bearer test-api-key-123"


@pytest.mark.django_db
def test_external_api_url_is_configurable(client, authenticated_user, settings):
    """External API URL can be configured via settings."""
    custom_url = "https://custom.api.com/data"
    settings.EXTERNAL_DATASET_API_URL = custom_url
    hdrs = auth_hdr(client, "testuser", TEST_PASSWORD)

    with patch("census_app.surveys.external_datasets.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = ["Option"]
        mock_get.return_value = mock_response

        client.get("/api/datasets/nhs_trusts/", **hdrs)

        # Verify the custom URL was used
        mock_get.assert_called_once()
        call_args = mock_get.call_args[0]
        assert call_args[0].startswith(custom_url)


# ============================================================================
# Response Format Tests
# ============================================================================


@pytest.mark.django_db
def test_list_datasets_response_structure(client, authenticated_user):
    """List datasets returns correctly structured response."""
    hdrs = auth_hdr(client, "testuser", TEST_PASSWORD)
    resp = client.get("/api/datasets/", **hdrs)

    data = resp.json()
    assert isinstance(data, dict)
    assert "datasets" in data
    assert isinstance(data["datasets"], list)

    # Check first dataset structure
    dataset = data["datasets"][0]
    assert "key" in dataset
    assert "name" in dataset
    assert isinstance(dataset["key"], str)
    assert isinstance(dataset["name"], str)


@pytest.mark.django_db
def test_get_dataset_response_structure(client, authenticated_user):
    """Get dataset returns correctly structured response."""
    hdrs = auth_hdr(client, "testuser", TEST_PASSWORD)

    with patch("census_app.surveys.external_datasets.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"options": ["A", "B"]}
        mock_get.return_value = mock_response

        resp = client.get("/api/datasets/hospitals_england/", **hdrs)

        data = resp.json()
        assert isinstance(data, dict)
        assert "dataset_key" in data
        assert "options" in data
        assert data["dataset_key"] == "hospitals_england"
        assert isinstance(data["options"], list)
        assert all(isinstance(opt, str) for opt in data["options"])


# ============================================================================
# Organization Permission Tests
# ============================================================================


@pytest.mark.django_db
def test_org_admin_can_access_datasets(client, django_user_model):
    """Organization admins can access datasets."""
    admin = django_user_model.objects.create_user(username="admin", password="pass")
    org = Organization.objects.create(name="Test Org", owner=admin)
    OrganizationMembership.objects.create(
        organization=org, user=admin, role=OrganizationMembership.Role.ADMIN
    )

    hdrs = auth_hdr(client, "admin", "pass")

    with patch("census_app.surveys.external_datasets.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"options": ["Option 1"]}
        mock_get.return_value = mock_response

        # List datasets
        resp = client.get("/api/datasets/", **hdrs)
        assert resp.status_code == 200

        # Get specific dataset
        resp = client.get("/api/datasets/hospitals_england/", **hdrs)
        assert resp.status_code == 200


@pytest.mark.django_db
def test_org_creator_can_access_datasets(client, django_user_model):
    """Organization creators can access datasets."""
    admin = django_user_model.objects.create_user(username="admin", password="pass")
    creator = django_user_model.objects.create_user(
        username="creator", password="pass"
    )
    org = Organization.objects.create(name="Test Org", owner=admin)
    OrganizationMembership.objects.create(
        organization=org, user=creator, role=OrganizationMembership.Role.CREATOR
    )

    hdrs = auth_hdr(client, "creator", "pass")

    with patch("census_app.surveys.external_datasets.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"options": ["Option 1"]}
        mock_get.return_value = mock_response

        # List datasets
        resp = client.get("/api/datasets/", **hdrs)
        assert resp.status_code == 200

        # Get specific dataset
        resp = client.get("/api/datasets/hospitals_england/", **hdrs)
        assert resp.status_code == 200


@pytest.mark.django_db
def test_org_viewer_can_access_datasets(client, django_user_model):
    """Organization viewers can access datasets (reference data is not restricted)."""
    admin = django_user_model.objects.create_user(username="admin", password="pass")
    viewer = django_user_model.objects.create_user(username="viewer", password="pass")
    org = Organization.objects.create(name="Test Org", owner=admin)
    OrganizationMembership.objects.create(
        organization=org, user=viewer, role=OrganizationMembership.Role.VIEWER
    )

    hdrs = auth_hdr(client, "viewer", "pass")

    with patch("census_app.surveys.external_datasets.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"options": ["Option 1"]}
        mock_get.return_value = mock_response

        # List datasets
        resp = client.get("/api/datasets/", **hdrs)
        assert resp.status_code == 200

        # Get specific dataset
        resp = client.get("/api/datasets/hospitals_england/", **hdrs)
        assert resp.status_code == 200


@pytest.mark.django_db
def test_user_without_org_membership_can_access_datasets(client, django_user_model):
    """Users without org membership can still access datasets.

    Datasets are reference data (hospitals, trusts, etc.) that any authenticated
    user might need. The restriction happens at the survey editing level, not
    at the dataset access level.
    """
    user = django_user_model.objects.create_user(username="user", password="pass")

    hdrs = auth_hdr(client, "user", "pass")

    with patch("census_app.surveys.external_datasets.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"options": ["Option 1"]}
        mock_get.return_value = mock_response

        # List datasets
        resp = client.get("/api/datasets/", **hdrs)
        assert resp.status_code == 200

        # Get specific dataset
        resp = client.get("/api/datasets/hospitals_england/", **hdrs)
        assert resp.status_code == 200
