import json

from django.contrib.auth import get_user_model
import pytest

from census_app.surveys.models import Survey, SurveyMembership

User = get_user_model()
TEST_PASSWORD = "test-pass"


def auth_hdr(client, username: str, password: str) -> dict:
    resp = client.post(
        "/api/token",
        data=json.dumps({"username": username, "password": password}),
        content_type="application/json",
    )
    assert resp.status_code == 200, resp.content
    return {"HTTP_AUTHORIZATION": f"Bearer {resp.json()['access']}"}


@pytest.mark.django_db
def test_api_survey_list_includes_membership_surveys(client):
    """Test that API survey list includes surveys user has membership to."""
    # Create users
    creator = User.objects.create_user(
        username="creator@test.com", password=TEST_PASSWORD
    )
    editor = User.objects.create_user(
        username="editor@test.com", password=TEST_PASSWORD
    )
    viewer = User.objects.create_user(
        username="viewer@test.com", password=TEST_PASSWORD
    )
    User.objects.create_user(
        username="outsider@test.com", password=TEST_PASSWORD
    )  # outsider

    # Create survey
    survey = Survey.objects.create(
        owner=creator, name="Test Survey", slug="test-survey"
    )

    # Add memberships
    SurveyMembership.objects.create(
        survey=survey, user=editor, role=SurveyMembership.Role.EDITOR
    )
    SurveyMembership.objects.create(
        survey=survey, user=viewer, role=SurveyMembership.Role.VIEWER
    )

    # Test creator can see survey
    hdrs = auth_hdr(client, "creator@test.com", TEST_PASSWORD)
    resp = client.get("/api/surveys/", **hdrs)
    assert resp.status_code == 200
    surveys = resp.json()
    assert len(surveys) == 1
    assert surveys[0]["slug"] == "test-survey"

    # Test editor can see survey via membership
    hdrs = auth_hdr(client, "editor@test.com", TEST_PASSWORD)
    resp = client.get("/api/surveys/", **hdrs)
    assert resp.status_code == 200
    surveys = resp.json()
    assert len(surveys) == 1
    assert surveys[0]["slug"] == "test-survey"

    # Test viewer can see survey via membership
    hdrs = auth_hdr(client, "viewer@test.com", TEST_PASSWORD)
    resp = client.get("/api/surveys/", **hdrs)
    assert resp.status_code == 200
    surveys = resp.json()
    assert len(surveys) == 1
    assert surveys[0]["slug"] == "test-survey"

    # Test outsider cannot see survey
    hdrs = auth_hdr(client, "outsider@test.com", TEST_PASSWORD)
    resp = client.get("/api/surveys/", **hdrs)
    assert resp.status_code == 200
    surveys = resp.json()
    assert len(surveys) == 0


@pytest.mark.django_db
def test_api_editor_permissions(client):
    """Test that EDITOR role can access and edit surveys via API."""
    # Create users
    creator = User.objects.create_user(
        username="creator@test.com", password=TEST_PASSWORD
    )
    editor = User.objects.create_user(
        username="editor@test.com", password=TEST_PASSWORD
    )

    # Create survey
    survey = Survey.objects.create(
        owner=creator, name="Test Survey", slug="test-survey"
    )

    # Add editor as EDITOR
    SurveyMembership.objects.create(
        survey=survey, user=editor, role=SurveyMembership.Role.EDITOR
    )

    # Test editor can retrieve survey
    hdrs = auth_hdr(client, "editor@test.com", TEST_PASSWORD)
    resp = client.get(f"/api/surveys/{survey.id}/", **hdrs)
    assert resp.status_code == 200

    # Test editor can update survey (PATCH)
    resp = client.patch(
        f"/api/surveys/{survey.id}/",
        data=json.dumps({"description": "Updated by editor"}),
        content_type="application/json",
        **hdrs,
    )
    assert resp.status_code == 200

    # Verify the update
    survey.refresh_from_db()
    assert survey.description == "Updated by editor"


@pytest.mark.django_db
def test_api_viewer_permissions(client):
    """Test that VIEWER role can only read surveys via API."""
    # Create users
    creator = User.objects.create_user(
        username="creator@test.com", password=TEST_PASSWORD
    )
    viewer = User.objects.create_user(
        username="viewer@test.com", password=TEST_PASSWORD
    )

    # Create survey
    survey = Survey.objects.create(
        owner=creator, name="Test Survey", slug="test-survey"
    )

    # Add viewer as VIEWER
    SurveyMembership.objects.create(
        survey=survey, user=viewer, role=SurveyMembership.Role.VIEWER
    )

    # Test viewer can retrieve survey
    hdrs = auth_hdr(client, "viewer@test.com", TEST_PASSWORD)
    resp = client.get(f"/api/surveys/{survey.id}/", **hdrs)
    assert resp.status_code == 200

    # Test viewer cannot update survey (should be forbidden)
    resp = client.patch(
        f"/api/surveys/{survey.id}/",
        data=json.dumps({"description": "Attempted update by viewer"}),
        content_type="application/json",
        **hdrs,
    )
    assert resp.status_code == 403
