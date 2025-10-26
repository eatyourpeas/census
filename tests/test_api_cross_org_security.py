"""
Test JWT-based API security: verify users cannot access surveys/data from other organizations.

This ensures that JWT authentication properly scopes access and prevents cross-organization
data leakage.
"""

import json

from django.contrib.auth import get_user_model
import pytest

from census_app.surveys.models import Organization, OrganizationMembership, Survey

User = get_user_model()
TEST_PASSWORD = "test-pass"


def get_jwt_token(client, username: str, password: str) -> str:
    """Obtain JWT access token for a user."""
    resp = client.post(
        "/api/token",
        data=json.dumps({"username": username, "password": password}),
        content_type="application/json",
    )
    assert resp.status_code == 200, resp.content
    return resp.json()["access"]


def auth_header(token: str) -> dict:
    """Build authorization header with JWT token."""
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


@pytest.mark.django_db
class TestCrossOrganizationSecurity:
    """Verify JWT tokens are properly scoped to prevent cross-organization access."""

    def test_user_cannot_list_other_org_surveys(self, client):
        """User with JWT should not see surveys from organizations they don't belong to."""
        # Org A
        owner_a = User.objects.create_user(username="owner_a", password=TEST_PASSWORD)
        org_a = Organization.objects.create(name="Org A", owner=owner_a)
        survey_a = Survey.objects.create(
            owner=owner_a, organization=org_a, name="Survey A", slug="survey-a"
        )

        # Org B
        owner_b = User.objects.create_user(username="owner_b", password=TEST_PASSWORD)
        org_b = Organization.objects.create(name="Org B", owner=owner_b)
        survey_b = Survey.objects.create(
            owner=owner_b, organization=org_b, name="Survey B", slug="survey-b"
        )

        # Owner A gets JWT and lists surveys
        token_a = get_jwt_token(client, "owner_a", TEST_PASSWORD)
        resp = client.get("/api/surveys/", **auth_header(token_a))
        assert resp.status_code == 200
        slugs = {s["slug"] for s in resp.json()}
        assert "survey-a" in slugs
        assert "survey-b" not in slugs  # Should NOT see Org B's survey

        # Owner B gets JWT and lists surveys
        token_b = get_jwt_token(client, "owner_b", TEST_PASSWORD)
        resp = client.get("/api/surveys/", **auth_header(token_b))
        assert resp.status_code == 200
        slugs = {s["slug"] for s in resp.json()}
        assert "survey-b" in slugs
        assert "survey-a" not in slugs  # Should NOT see Org A's survey

    def test_user_cannot_retrieve_other_org_survey(self, client):
        """User should get 403 when trying to retrieve survey from another org."""
        # Org A
        owner_a = User.objects.create_user(username="owner_a2", password=TEST_PASSWORD)
        org_a = Organization.objects.create(name="Org A2", owner=owner_a)
        survey_a = Survey.objects.create(
            owner=owner_a, organization=org_a, name="Survey A2", slug="survey-a2"
        )

        # Org B
        owner_b = User.objects.create_user(username="owner_b2", password=TEST_PASSWORD)
        org_b = Organization.objects.create(name="Org B2", owner=owner_b)

        # Owner B tries to access Org A's survey
        token_b = get_jwt_token(client, "owner_b2", TEST_PASSWORD)
        resp = client.get(f"/api/surveys/{survey_a.id}/", **auth_header(token_b))
        assert resp.status_code == 403  # Forbidden, not 404

    def test_user_cannot_update_other_org_survey(self, client):
        """User should not be able to modify surveys in another organization."""
        # Org A
        owner_a = User.objects.create_user(username="owner_a3", password=TEST_PASSWORD)
        org_a = Organization.objects.create(name="Org A3", owner=owner_a)
        survey_a = Survey.objects.create(
            owner=owner_a, organization=org_a, name="Survey A3", slug="survey-a3"
        )

        # Org B
        owner_b = User.objects.create_user(username="owner_b3", password=TEST_PASSWORD)
        org_b = Organization.objects.create(name="Org B3", owner=owner_b)

        # Owner B tries to update Org A's survey
        token_b = get_jwt_token(client, "owner_b3", TEST_PASSWORD)
        resp = client.patch(
            f"/api/surveys/{survey_a.id}/",
            data=json.dumps({"description": "Malicious update"}),
            content_type="application/json",
            **auth_header(token_b),
        )
        assert resp.status_code == 403

        # Verify survey was not modified
        survey_a.refresh_from_db()
        assert survey_a.description != "Malicious update"

    def test_user_cannot_publish_other_org_survey(self, client):
        """User should not be able to publish surveys in another organization."""
        # Org A
        owner_a = User.objects.create_user(username="owner_a4", password=TEST_PASSWORD)
        org_a = Organization.objects.create(name="Org A4", owner=owner_a)
        survey_a = Survey.objects.create(
            owner=owner_a, organization=org_a, name="Survey A4", slug="survey-a4"
        )

        # Org B
        owner_b = User.objects.create_user(username="owner_b4", password=TEST_PASSWORD)
        org_b = Organization.objects.create(name="Org B4", owner=owner_b)

        # Owner B tries to publish Org A's survey
        token_b = get_jwt_token(client, "owner_b4", TEST_PASSWORD)
        resp = client.put(
            f"/api/surveys/{survey_a.id}/publish/",
            data=json.dumps({"status": "published", "visibility": "authenticated"}),
            content_type="application/json",
            **auth_header(token_b),
        )
        assert resp.status_code == 403

        # Verify survey was not published
        survey_a.refresh_from_db()
        assert survey_a.status == Survey.Status.DRAFT

    def test_org_admin_cannot_access_other_org_surveys(self, client):
        """Org admin in one org should not access surveys in a different org."""
        # Org A with admin
        owner_a = User.objects.create_user(username="owner_a5", password=TEST_PASSWORD)
        admin_a = User.objects.create_user(username="admin_a5", password=TEST_PASSWORD)
        org_a = Organization.objects.create(name="Org A5", owner=owner_a)
        OrganizationMembership.objects.create(
            organization=org_a, user=admin_a, role=OrganizationMembership.Role.ADMIN
        )
        survey_a = Survey.objects.create(
            owner=owner_a, organization=org_a, name="Survey A5", slug="survey-a5"
        )

        # Org B with admin
        owner_b = User.objects.create_user(username="owner_b5", password=TEST_PASSWORD)
        admin_b = User.objects.create_user(username="admin_b5", password=TEST_PASSWORD)
        org_b = Organization.objects.create(name="Org B5", owner=owner_b)
        OrganizationMembership.objects.create(
            organization=org_b, user=admin_b, role=OrganizationMembership.Role.ADMIN
        )

        # Admin B tries to access Org A's survey
        token_admin_b = get_jwt_token(client, "admin_b5", TEST_PASSWORD)
        resp = client.get(f"/api/surveys/{survey_a.id}/", **auth_header(token_admin_b))
        assert resp.status_code == 403

        # Admin B tries to list - should not see Org A's surveys
        resp = client.get("/api/surveys/", **auth_header(token_admin_b))
        assert resp.status_code == 200
        slugs = {s["slug"] for s in resp.json()}
        assert "survey-a5" not in slugs

    def test_jwt_token_user_identity_properly_scoped(self, client):
        """Verify JWT contains correct user identity and cannot be used for other users."""
        user1 = User.objects.create_user(username="user1", password=TEST_PASSWORD)
        user2 = User.objects.create_user(username="user2", password=TEST_PASSWORD)

        # Create survey for user1
        survey1 = Survey.objects.create(
            owner=user1, name="User 1 Survey", slug="user1-survey"
        )

        # User2 gets their own JWT
        token2 = get_jwt_token(client, "user2", TEST_PASSWORD)

        # User2 tries to access user1's survey (no org involved)
        resp = client.get(f"/api/surveys/{survey1.id}/", **auth_header(token2))
        assert resp.status_code == 403

        # User2 lists surveys - should not see user1's
        resp = client.get("/api/surveys/", **auth_header(token2))
        assert resp.status_code == 200
        slugs = {s["slug"] for s in resp.json()}
        assert "user1-survey" not in slugs
