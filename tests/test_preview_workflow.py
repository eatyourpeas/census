"""Test preview workflow functionality."""

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from census_app.surveys.models import Organization, Survey, SurveyResponse


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(username="testuser", password="testpass")


@pytest.fixture
def survey(db, user):
    """Create a test survey."""
    org = Organization.objects.create(name="Test Org", owner=user)
    return Survey.objects.create(
        owner=user,
        organization=org,
        name="Test Survey",
        slug="test-survey"
    )


@pytest.mark.django_db
def test_preview_mode_displays_alert(client, user, survey):
    """Test that preview mode shows the warning alert."""
    client.force_login(user)

    resp = client.get(reverse("surveys:preview", kwargs={"slug": survey.slug}))
    assert resp.status_code == 200
    assert b"Preview Mode" in resp.content
    assert b"no data will be saved" in resp.content


@pytest.mark.django_db
def test_preview_submit_redirects_to_preview_thank_you(client, user, survey):
    """Test that submitting in preview mode redirects to preview thank you page."""
    client.force_login(user)

    resp = client.post(
        reverse("surveys:preview", kwargs={"slug": survey.slug}),
        {},
        follow=True
    )
    assert resp.status_code == 200
    # Should redirect to preview thank you page
    assert b"Preview Complete" in resp.content
    assert b"no data was saved" in resp.content


@pytest.mark.django_db
def test_preview_thank_you_page_accessible(client, user, survey):
    """Test that preview thank you page is accessible."""
    client.force_login(user)

    resp = client.get(reverse("surveys:preview_thank_you", kwargs={"slug": survey.slug}))
    assert resp.status_code == 200
    assert b"Preview Complete" in resp.content
    assert b"Preview Again" in resp.content
    assert b"Back to Dashboard" in resp.content


@pytest.mark.django_db
def test_preview_does_not_save_responses(client, user, survey):
    """Test that preview mode does not create survey responses."""
    client.force_login(user)

    initial_count = SurveyResponse.objects.filter(survey=survey).count()

    # Submit in preview mode
    client.post(
        reverse("surveys:preview", kwargs={"slug": survey.slug}),
        {},
    )

    # Verify no new responses were created
    final_count = SurveyResponse.objects.filter(survey=survey).count()
    assert final_count == initial_count
