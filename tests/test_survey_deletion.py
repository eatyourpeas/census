"""
Tests for survey deletion functionality.

Ensures only authorized users (owner or org admin) can delete surveys via API and webapp.
"""

import json

from django.contrib.auth import get_user_model
import pytest

from census_app.surveys.models import (
    AuditLog,
    Organization,
    OrganizationMembership,
    Survey,
)

User = get_user_model()
TEST_PASSWORD = "test-pass"


def get_auth_header(client, username: str, password: str) -> dict:
    """Helper to get JWT auth header."""
    resp = client.post(
        "/api/token",
        data=json.dumps({"username": username, "password": password}),
        content_type="application/json",
    )
    assert resp.status_code == 200, resp.content
    access = resp.json()["access"]
    return {"HTTP_AUTHORIZATION": f"Bearer {access}"}


@pytest.mark.django_db
class TestSurveyDeletionAPI:
    """Test survey deletion via REST API."""

    def setup_test_data(self):
        """Create test users, org, and surveys."""
        owner = User.objects.create_user(username="owner", password=TEST_PASSWORD)
        admin = User.objects.create_user(username="admin", password=TEST_PASSWORD)
        creator = User.objects.create_user(username="creator", password=TEST_PASSWORD)
        viewer = User.objects.create_user(username="viewer", password=TEST_PASSWORD)
        outsider = User.objects.create_user(username="outsider", password=TEST_PASSWORD)

        org = Organization.objects.create(name="Test Org", owner=owner)
        OrganizationMembership.objects.create(
            organization=org, user=admin, role=OrganizationMembership.Role.ADMIN
        )
        OrganizationMembership.objects.create(
            organization=org, user=creator, role=OrganizationMembership.Role.CREATOR
        )
        OrganizationMembership.objects.create(
            organization=org, user=viewer, role=OrganizationMembership.Role.VIEWER
        )

        survey = Survey.objects.create(
            owner=owner, organization=org, name="Test Survey", slug="test-survey"
        )

        return {
            "owner": owner,
            "admin": admin,
            "creator": creator,
            "viewer": viewer,
            "outsider": outsider,
            "org": org,
            "survey": survey,
        }

    def test_owner_can_delete_survey(self, client):
        """Survey owner can delete their survey."""
        data = self.setup_test_data()
        survey = data["survey"]
        url = f"/api/surveys/{survey.pk}/"

        hdrs = get_auth_header(client, "owner", TEST_PASSWORD)
        resp = client.delete(url, **hdrs)

        assert resp.status_code == 204
        assert not Survey.objects.filter(pk=survey.pk).exists()

        # Check audit log
        log = AuditLog.objects.filter(
            action=AuditLog.Action.REMOVE, scope=AuditLog.Scope.SURVEY
        ).first()
        assert log is not None
        assert log.actor == data["owner"]
        assert log.metadata["survey_name"] == "Test Survey"
        assert log.metadata["survey_slug"] == "test-survey"

    def test_org_admin_can_delete_survey(self, client):
        """Org admin can delete surveys in their org."""
        data = self.setup_test_data()
        survey = data["survey"]
        url = f"/api/surveys/{survey.pk}/"

        hdrs = get_auth_header(client, "admin", TEST_PASSWORD)
        resp = client.delete(url, **hdrs)

        assert resp.status_code == 204
        assert not Survey.objects.filter(pk=survey.pk).exists()

    def test_creator_cannot_delete_others_survey(self, client):
        """Creator role cannot delete surveys they don't own."""
        data = self.setup_test_data()
        survey = data["survey"]
        url = f"/api/surveys/{survey.pk}/"

        hdrs = get_auth_header(client, "creator", TEST_PASSWORD)
        resp = client.delete(url, **hdrs)

        assert resp.status_code == 403
        assert Survey.objects.filter(pk=survey.pk).exists()

    def test_viewer_cannot_delete_survey(self, client):
        """Viewer role cannot delete surveys."""
        data = self.setup_test_data()
        survey = data["survey"]
        url = f"/api/surveys/{survey.pk}/"

        hdrs = get_auth_header(client, "viewer", TEST_PASSWORD)
        resp = client.delete(url, **hdrs)

        assert resp.status_code == 403
        assert Survey.objects.filter(pk=survey.pk).exists()

    def test_outsider_cannot_delete_survey(self, client):
        """User not in org cannot delete survey."""
        data = self.setup_test_data()
        survey = data["survey"]
        url = f"/api/surveys/{survey.pk}/"

        hdrs = get_auth_header(client, "outsider", TEST_PASSWORD)
        resp = client.delete(url, **hdrs)

        assert resp.status_code == 403
        assert Survey.objects.filter(pk=survey.pk).exists()

    def test_unauthenticated_cannot_delete_survey(self, client):
        """Unauthenticated users cannot delete surveys."""
        data = self.setup_test_data()
        survey = data["survey"]
        url = f"/api/surveys/{survey.pk}/"

        resp = client.delete(url)

        assert resp.status_code in (401, 403)
        assert Survey.objects.filter(pk=survey.pk).exists()

    def test_creator_can_delete_own_survey(self, client):
        """Creator can delete their own survey."""
        data = self.setup_test_data()
        creator = data["creator"]
        org = data["org"]

        # Create survey owned by creator
        survey = Survey.objects.create(
            owner=creator, organization=org, name="Creator Survey", slug="creator-survey"
        )

        url = f"/api/surveys/{survey.pk}/"
        hdrs = get_auth_header(client, "creator", TEST_PASSWORD)
        resp = client.delete(url, **hdrs)

        assert resp.status_code == 204
        assert not Survey.objects.filter(pk=survey.pk).exists()


@pytest.mark.django_db
class TestSurveyDeletionWebApp:
    """Test survey deletion via web interface."""

    def setup_test_data(self):
        """Create test users, org, and surveys."""
        owner = User.objects.create_user(username="owner", password=TEST_PASSWORD)
        admin = User.objects.create_user(username="admin", password=TEST_PASSWORD)
        creator = User.objects.create_user(username="creator", password=TEST_PASSWORD)

        org = Organization.objects.create(name="Test Org", owner=owner)
        OrganizationMembership.objects.create(
            organization=org, user=admin, role=OrganizationMembership.Role.ADMIN
        )
        OrganizationMembership.objects.create(
            organization=org, user=creator, role=OrganizationMembership.Role.CREATOR
        )

        survey = Survey.objects.create(
            owner=owner, organization=org, name="Test Survey", slug="test-survey"
        )

        return {
            "owner": owner,
            "admin": admin,
            "creator": creator,
            "org": org,
            "survey": survey,
        }

    def test_delete_without_confirmation_fails(self, client):
        """Delete without name confirmation should fail."""
        data = self.setup_test_data()
        survey = data["survey"]

        client.login(username="owner", password=TEST_PASSWORD)
        url = f"/surveys/{survey.slug}/delete/"

        # POST without confirmation name
        resp = client.post(url, {})

        assert resp.status_code == 400
        assert Survey.objects.filter(pk=survey.pk).exists()

    def test_delete_with_wrong_name_fails(self, client):
        """Delete with incorrect name confirmation should fail."""
        data = self.setup_test_data()
        survey = data["survey"]

        client.login(username="owner", password=TEST_PASSWORD)
        url = f"/surveys/{survey.slug}/delete/"

        # POST with wrong name
        resp = client.post(url, {"confirm_name": "Wrong Name"})

        assert resp.status_code == 400
        assert Survey.objects.filter(pk=survey.pk).exists()

    def test_owner_can_delete_with_confirmation(self, client):
        """Owner can delete survey with correct name confirmation."""
        data = self.setup_test_data()
        survey = data["survey"]

        client.login(username="owner", password=TEST_PASSWORD)
        url = f"/surveys/{survey.slug}/delete/"

        # POST with correct name
        resp = client.post(url, {"confirm_name": "Test Survey"})

        assert resp.status_code == 302  # Redirect after success
        assert not Survey.objects.filter(pk=survey.pk).exists()

    def test_admin_can_delete_with_confirmation(self, client):
        """Org admin can delete survey with correct name confirmation."""
        data = self.setup_test_data()
        survey = data["survey"]

        client.login(username="admin", password=TEST_PASSWORD)
        url = f"/surveys/{survey.slug}/delete/"

        # POST with correct name
        resp = client.post(url, {"confirm_name": "Test Survey"})

        assert resp.status_code == 302
        assert not Survey.objects.filter(pk=survey.pk).exists()

    def test_creator_cannot_delete_others_survey(self, client):
        """Creator cannot delete survey they don't own."""
        data = self.setup_test_data()
        survey = data["survey"]

        client.login(username="creator", password=TEST_PASSWORD)
        url = f"/surveys/{survey.slug}/delete/"

        # POST with correct name but no permission
        resp = client.post(url, {"confirm_name": "Test Survey"})

        assert resp.status_code == 403
        assert Survey.objects.filter(pk=survey.pk).exists()

    def test_unauthenticated_redirects_to_login(self, client):
        """Unauthenticated users are redirected to login."""
        data = self.setup_test_data()
        survey = data["survey"]

        url = f"/surveys/{survey.slug}/delete/"
        resp = client.post(url, {"confirm_name": "Test Survey"})

        assert resp.status_code == 302
        assert "/login/" in resp.url
        assert Survey.objects.filter(pk=survey.pk).exists()
