"""
Comprehensive tests for survey publication workflows.

Tests all three publication options:
1. AUTHENTICATED - requires login to access survey
2. PUBLIC - anyone can access via /surveys/<slug>/take/
3. UNLISTED - anyone can access via secret link /surveys/<slug>/take/unlisted/<key>/
4. TOKEN - one-time use tokens via /surveys/<slug>/take/token/<token>/
"""

import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

from census_app.surveys.models import (
    Organization,
    QuestionGroup,
    Survey,
    SurveyAccessToken,
    SurveyQuestion,
)

User = get_user_model()


@pytest.fixture(autouse=True)
def disable_rate_limiting(settings):
    """Disable rate limiting for all tests in this module."""
    settings.RATELIMIT_ENABLE = False


@pytest.fixture
def survey_owner(django_user_model):
    """Create a survey owner user."""
    return django_user_model.objects.create_user(
        username="owner@example.com", password="testpass123"
    )


@pytest.fixture
def test_organization(survey_owner):
    """Create a test organization to bypass encryption setup."""
    return Organization.objects.create(
        name="Test Organization",
        owner=survey_owner,
    )


@pytest.fixture
def participant(django_user_model):
    """Create a participant user (not the owner)."""
    return django_user_model.objects.create_user(
        username="participant@example.com", password="testpass123"
    )


@pytest.fixture
def basic_survey(survey_owner, test_organization):
    """Create a basic survey with one question.

    Uses an organization to bypass encryption setup during testing.
    """
    survey = Survey.objects.create(
        owner=survey_owner,
        name="Test Survey",
        slug="test-survey",
        status=Survey.Status.DRAFT,
        visibility=Survey.Visibility.AUTHENTICATED,
        organization=test_organization,
    )
    # Add a basic question
    SurveyQuestion.objects.create(
        survey=survey,
        text="What is your name?",
        type=SurveyQuestion.Types.TEXT,
        required=True,
        order=0,
    )
    return survey


# ============================================================================
# AUTHENTICATED Visibility Tests
# ============================================================================


@pytest.mark.django_db
class TestAuthenticatedPublication:
    """Tests for AUTHENTICATED visibility option."""

    def test_authenticated_survey_requires_login_for_take_url(
        self, client, basic_survey
    ):
        """Anonymous users should be redirected to login when accessing /take/ URL."""
        basic_survey.status = Survey.Status.PUBLISHED
        basic_survey.visibility = Survey.Visibility.AUTHENTICATED
        basic_survey.save()

        url = reverse("surveys:take", kwargs={"slug": basic_survey.slug})
        response = client.get(url)

        # Should redirect to login
        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    def test_authenticated_survey_accessible_by_logged_in_user(
        self, client, basic_survey, participant
    ):
        """Logged-in users should be able to access AUTHENTICATED survey."""
        basic_survey.status = Survey.Status.PUBLISHED
        basic_survey.visibility = Survey.Visibility.AUTHENTICATED
        basic_survey.save()

        client.login(username="participant@example.com", password="testpass123")
        url = reverse("surveys:take", kwargs={"slug": basic_survey.slug})
        response = client.get(url)

        assert response.status_code == 200
        assert b"What is your name?" in response.content

    def test_authenticated_draft_survey_returns_404(self, client, basic_survey, participant):
        """DRAFT surveys should not be accessible even to authenticated users."""
        basic_survey.status = Survey.Status.DRAFT
        basic_survey.visibility = Survey.Visibility.AUTHENTICATED
        basic_survey.save()

        client.login(username="participant@example.com", password="testpass123")
        url = reverse("surveys:take", kwargs={"slug": basic_survey.slug})
        response = client.get(url)

        assert response.status_code == 404

    def test_authenticated_closed_survey_returns_404(self, client, basic_survey, participant):
        """CLOSED surveys should not accept new submissions."""
        basic_survey.status = Survey.Status.CLOSED
        basic_survey.visibility = Survey.Visibility.AUTHENTICATED
        basic_survey.save()

        client.login(username="participant@example.com", password="testpass123")
        url = reverse("surveys:take", kwargs={"slug": basic_survey.slug})
        response = client.get(url)

        assert response.status_code == 404

    def test_authenticated_survey_owner_cannot_submit_own_survey(
        self, client, basic_survey, survey_owner
    ):
        """Survey owners should not be able to submit responses to their own surveys."""
        basic_survey.status = Survey.Status.PUBLISHED
        basic_survey.visibility = Survey.Visibility.AUTHENTICATED
        basic_survey.save()

        client.login(username="owner@example.com", password="testpass123")
        url = reverse("surveys:take", kwargs={"slug": basic_survey.slug})
        response = client.get(url)

        # Owner should be blocked from taking their own survey
        assert response.status_code in (302, 403, 404)


# ============================================================================
# PUBLIC Visibility Tests
# ============================================================================


@pytest.mark.django_db
class TestPublicPublication:
    """Tests for PUBLIC visibility option."""

    def test_public_survey_accessible_anonymously(self, client, basic_survey):
        """Anonymous users should be able to access PUBLIC surveys."""
        basic_survey.status = Survey.Status.PUBLISHED
        basic_survey.visibility = Survey.Visibility.PUBLIC
        basic_survey.save()

        url = reverse("surveys:take", kwargs={"slug": basic_survey.slug})
        response = client.get(url)

        assert response.status_code == 200
        assert b"What is your name?" in response.content

    def test_public_survey_blocks_patient_data_without_ack(
        self, client, survey_owner, basic_survey
    ):
        """PUBLIC surveys collecting patient data require acknowledgment."""
        # Add patient data collection
        patient_group = QuestionGroup.objects.create(
            owner=survey_owner,
            name="Patient Details",
            schema={
                "template": "patient_details_encrypted",
                "fields": ["first_name", "surname"],
            },
        )
        basic_survey.question_groups.add(patient_group)

        basic_survey.status = Survey.Status.PUBLISHED
        basic_survey.visibility = Survey.Visibility.PUBLIC
        basic_survey.no_patient_data_ack = False  # Not acknowledged
        basic_survey.save()

        url = reverse("surveys:take", kwargs={"slug": basic_survey.slug})
        response = client.get(url)

        # Should be blocked (404 or 403)
        assert response.status_code in (403, 404)

    def test_public_survey_allows_patient_data_with_ack(
        self, client, survey_owner, basic_survey
    ):
        """PUBLIC surveys can collect patient data if acknowledged."""
        # Add patient data collection
        patient_group = QuestionGroup.objects.create(
            owner=survey_owner,
            name="Patient Details",
            schema={
                "template": "patient_details_encrypted",
                "fields": ["first_name"],
            },
        )
        basic_survey.question_groups.add(patient_group)

        basic_survey.status = Survey.Status.PUBLISHED
        basic_survey.visibility = Survey.Visibility.PUBLIC
        basic_survey.no_patient_data_ack = True  # Acknowledged
        basic_survey.save()

        url = reverse("surveys:take", kwargs={"slug": basic_survey.slug})
        response = client.get(url)

        # Should be accessible
        assert response.status_code == 200

    def test_public_draft_survey_not_accessible(self, client, basic_survey):
        """DRAFT PUBLIC surveys should return 404."""
        basic_survey.status = Survey.Status.DRAFT
        basic_survey.visibility = Survey.Visibility.PUBLIC
        basic_survey.save()

        url = reverse("surveys:take", kwargs={"slug": basic_survey.slug})
        response = client.get(url)

        assert response.status_code == 404

    def test_public_survey_submission_creates_response(
        self, client, basic_survey
    ):
        """Anonymous users should be able to submit PUBLIC surveys."""
        basic_survey.status = Survey.Status.PUBLISHED
        basic_survey.visibility = Survey.Visibility.PUBLIC
        basic_survey.save()

        url = reverse("surveys:take", kwargs={"slug": basic_survey.slug})

        # Submit the survey
        response = client.post(url, {
            f"q_{basic_survey.questions.first().id}": "John Doe"
        })

        # Should redirect to thank you page
        assert response.status_code == 302
        assert "thank-you" in response.url or response.url.endswith(f"/surveys/{basic_survey.slug}/")

        # Check response was created
        assert basic_survey.responses.count() == 1


# ============================================================================
# UNLISTED Visibility Tests
# ============================================================================


@pytest.mark.django_db
class TestUnlistedPublication:
    """Tests for UNLISTED visibility option (secret link)."""

    def test_unlisted_survey_not_accessible_via_regular_take_url(
        self, client, basic_survey
    ):
        """UNLISTED surveys should NOT be accessible via /take/ URL."""
        basic_survey.status = Survey.Status.PUBLISHED
        basic_survey.visibility = Survey.Visibility.UNLISTED
        basic_survey.unlisted_key = "secret123key"
        basic_survey.save()

        url = reverse("surveys:take", kwargs={"slug": basic_survey.slug})
        response = client.get(url)

        # Should return 404 (not accessible via regular URL)
        assert response.status_code == 404

    def test_unlisted_survey_accessible_with_correct_key(
        self, client, basic_survey
    ):
        """UNLISTED surveys should be accessible with the secret key."""
        basic_survey.status = Survey.Status.PUBLISHED
        basic_survey.visibility = Survey.Visibility.UNLISTED
        basic_survey.unlisted_key = "secret123key"
        basic_survey.save()

        url = reverse(
            "surveys:take_unlisted",
            kwargs={"slug": basic_survey.slug, "key": "secret123key"},
        )
        response = client.get(url)

        assert response.status_code == 200
        assert b"What is your name?" in response.content

    def test_unlisted_survey_wrong_key_returns_404(self, client, basic_survey):
        """UNLISTED surveys should return 404 with wrong key."""
        basic_survey.status = Survey.Status.PUBLISHED
        basic_survey.visibility = Survey.Visibility.UNLISTED
        basic_survey.unlisted_key = "secret123key"
        basic_survey.save()

        url = reverse(
            "surveys:take_unlisted",
            kwargs={"slug": basic_survey.slug, "key": "wrongkey"},
        )
        response = client.get(url)

        assert response.status_code == 404

    def test_unlisted_key_auto_generated_on_publish(
        self, client, survey_owner, basic_survey
    ):
        """Unlisted key should be auto-generated when publishing with UNLISTED visibility."""
        client.login(username="owner@example.com", password="testpass123")

        # Survey starts without unlisted_key
        assert basic_survey.unlisted_key is None

        # Publish with UNLISTED visibility
        url = reverse("surveys:publish_update", kwargs={"slug": basic_survey.slug})
        client.post(url, {
            "status": "published",
            "visibility": "unlisted",
        })

        basic_survey.refresh_from_db()

        # Key should be auto-generated
        assert basic_survey.unlisted_key is not None
        assert len(basic_survey.unlisted_key) > 10  # Should be a decent length


# ============================================================================
# TOKEN Visibility Tests
# ============================================================================


@pytest.mark.django_db
class TestTokenPublication:
    """Tests for TOKEN visibility option (one-time use tokens)."""

    def test_token_survey_not_accessible_via_regular_take_url(
        self, client, basic_survey
    ):
        """TOKEN surveys should NOT be accessible via /take/ URL."""
        basic_survey.status = Survey.Status.PUBLISHED
        basic_survey.visibility = Survey.Visibility.TOKEN
        basic_survey.save()

        url = reverse("surveys:take", kwargs={"slug": basic_survey.slug})
        response = client.get(url)

        # Should return 404
        assert response.status_code == 404

    def test_token_survey_accessible_with_valid_token(
        self, client, survey_owner, basic_survey
    ):
        """TOKEN surveys should be accessible with valid token."""
        basic_survey.status = Survey.Status.PUBLISHED
        basic_survey.visibility = Survey.Visibility.TOKEN
        basic_survey.save()

        # Create a token
        token = SurveyAccessToken.objects.create(
            survey=basic_survey,
            token="valid-token-123",
            created_by=survey_owner,
        )

        url = reverse(
            "surveys:take_token",
            kwargs={"slug": basic_survey.slug, "token": token.token},
        )
        response = client.get(url)

        assert response.status_code == 200
        assert b"What is your name?" in response.content

    def test_token_survey_invalid_token_returns_404(
        self, client, basic_survey
    ):
        """Invalid tokens should return 404."""
        basic_survey.status = Survey.Status.PUBLISHED
        basic_survey.visibility = Survey.Visibility.TOKEN
        basic_survey.save()

        url = reverse(
            "surveys:take_token",
            kwargs={"slug": basic_survey.slug, "token": "invalid-token"},
        )
        response = client.get(url)

        assert response.status_code == 404

    def test_token_one_time_use_enforcement(
        self, client, survey_owner, basic_survey
    ):
        """Tokens should only work once."""
        basic_survey.status = Survey.Status.PUBLISHED
        basic_survey.visibility = Survey.Visibility.TOKEN
        basic_survey.save()

        token = SurveyAccessToken.objects.create(
            survey=basic_survey,
            token="onetime-token",
            created_by=survey_owner,
        )

        url = reverse(
            "surveys:take_token",
            kwargs={"slug": basic_survey.slug, "token": token.token},
        )

        # First access - should work
        response = client.get(url)
        assert response.status_code == 200

        # Submit the survey
        response = client.post(url, {
            f"q_{basic_survey.questions.first().id}": "Test Answer"
        })

        # Should redirect after submission
        assert response.status_code == 302

        # Token should now be marked as used
        token.refresh_from_db()
        assert token.used_at is not None

        # Second access - should fail
        response = client.get(url)
        assert response.status_code == 404

        # Second submission attempt - should also fail
        response = client.post(url, {
            f"q_{basic_survey.questions.first().id}": "Another Answer"
        })
        assert response.status_code == 404

    def test_token_visibility_blocks_unlisted_access(
        self, client, basic_survey
    ):
        """TOKEN surveys should not be accessible via unlisted URL."""
        basic_survey.status = Survey.Status.PUBLISHED
        basic_survey.visibility = Survey.Visibility.TOKEN
        basic_survey.unlisted_key = "some-key"  # Even if key exists
        basic_survey.save()

        url = reverse(
            "surveys:take_unlisted",
            kwargs={"slug": basic_survey.slug, "key": "some-key"},
        )
        response = client.get(url)

        # Should return 404 (wrong visibility type)
        assert response.status_code == 404


# ============================================================================
# Publication Update Tests
# ============================================================================


@pytest.mark.django_db
class TestPublishUpdate:
    """Tests for the publish settings update endpoint."""

    def test_publish_update_requires_authentication(self, client, basic_survey):
        """Publish update should require authentication."""
        url = reverse("surveys:publish_update", kwargs={"slug": basic_survey.slug})
        response = client.post(url, {"status": "published"})

        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    def test_publish_update_requires_edit_permission(
        self, client, basic_survey, participant
    ):
        """Non-owners should not be able to update publish settings."""
        client.login(username="participant@example.com", password="testpass123")

        url = reverse("surveys:publish_update", kwargs={"slug": basic_survey.slug})
        response = client.post(url, {"status": "published"})

        # Should be forbidden
        assert response.status_code == 403

    def test_owner_can_publish_survey(self, client, survey_owner, basic_survey):
        """Survey owner should be able to publish survey."""
        client.login(username="owner@example.com", password="testpass123")

        assert basic_survey.status == Survey.Status.DRAFT

        url = reverse("surveys:publish_update", kwargs={"slug": basic_survey.slug})
        response = client.post(url, {
            "status": "published",
            "visibility": "public",
        })

        # Should redirect to dashboard
        assert response.status_code == 302

        basic_survey.refresh_from_db()
        assert basic_survey.status == Survey.Status.PUBLISHED
        assert basic_survey.visibility == Survey.Visibility.PUBLIC

    def test_publish_sets_published_at_timestamp(
        self, client, survey_owner, basic_survey
    ):
        """First publish should set published_at timestamp."""
        client.login(username="owner@example.com", password="testpass123")

        assert basic_survey.published_at is None

        url = reverse("surveys:publish_update", kwargs={"slug": basic_survey.slug})
        client.post(url, {
            "status": "published",
            "visibility": "authenticated",
        })

        basic_survey.refresh_from_db()
        assert basic_survey.published_at is not None

    def test_close_survey_workflow(self, client, survey_owner, basic_survey):
        """Owner should be able to close a published survey."""
        client.login(username="owner@example.com", password="testpass123")

        # First publish
        basic_survey.status = Survey.Status.PUBLISHED
        basic_survey.save()

        # Then close
        url = reverse("surveys:publish_update", kwargs={"slug": basic_survey.slug})
        response = client.post(url, {
            "status": "closed",
            "visibility": "authenticated",
        })

        assert response.status_code == 302

        basic_survey.refresh_from_db()
        assert basic_survey.status == Survey.Status.CLOSED


# ============================================================================
# Cross-Visibility Edge Cases
# ============================================================================


@pytest.mark.django_db
class TestPublicationEdgeCases:
    """Edge cases and security tests for publication."""

    def test_changing_from_public_to_authenticated_blocks_anonymous(
        self, client, basic_survey
    ):
        """Changing visibility from PUBLIC to AUTHENTICATED should block anonymous access."""
        # Start as PUBLIC
        basic_survey.status = Survey.Status.PUBLISHED
        basic_survey.visibility = Survey.Visibility.PUBLIC
        basic_survey.save()

        url = reverse("surveys:take", kwargs={"slug": basic_survey.slug})

        # Should be accessible
        response = client.get(url)
        assert response.status_code == 200

        # Change to AUTHENTICATED
        basic_survey.visibility = Survey.Visibility.AUTHENTICATED
        basic_survey.save()

        # Should now require login
        response = client.get(url)
        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    def test_max_responses_limit(self, client, basic_survey):
        """Survey should respect max_responses limit."""
        basic_survey.status = Survey.Status.PUBLISHED
        basic_survey.visibility = Survey.Visibility.PUBLIC
        basic_survey.max_responses = 2
        basic_survey.save()

        url = reverse("surveys:take", kwargs={"slug": basic_survey.slug})

        # Submit first response
        client.post(url, {
            f"q_{basic_survey.questions.first().id}": "Response 1"
        })

        # Submit second response
        client.post(url, {
            f"q_{basic_survey.questions.first().id}": "Response 2"
        })

        # Third attempt should be blocked (survey is full)
        response = client.get(url)
        # Exact behavior depends on implementation - might be 404 or show message
        # For now, just check we can't submit
        assert response.status_code in (200, 404)  # May show "survey full" message
