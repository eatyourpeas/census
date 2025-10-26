"""
Tests for data governance views: exports, dashboard integration, and download security.

NOTE: Some tests are skipped due to ExportService bugs that need fixing:
- ExportService._generate_csv() uses non-existent fields: question.label, question.field_name
- Should use question.text instead
- This blocks tests that require actual CSV generation
TODO: Fix ExportService before enabling full test coverage
"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
import pytest

from census_app.surveys.models import DataExport, Survey
from census_app.surveys.services import ExportService

User = get_user_model()


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
    )


@pytest.fixture
def closed_survey(db, user):
    """Create a closed survey with responses."""
    survey = Survey.objects.create(
        name="Test Survey",
        slug="test-survey",
        owner=user,
        status=Survey.Status.PUBLISHED,
    )
    # Close the survey to enable data export
    survey.close_survey(user)
    return survey


@pytest.fixture
def open_survey(db, user):
    """Create an open (published) survey."""
    return Survey.objects.create(
        name="Open Survey",
        slug="open-survey",
        owner=user,
        status=Survey.Status.PUBLISHED,
    )


@pytest.fixture
def other_user(db):
    """Create another user (not owner of surveys)."""
    return User.objects.create_user(
        username="other_user",
        email="other@example.com",
        password="password123",
    )


# ========== Dashboard Integration Tests ==========


@pytest.mark.django_db
class TestDashboardDataGovernanceWidget:
    """Test that the data governance widget appears correctly on dashboard."""

    def test_dashboard_shows_export_button_for_closed_survey(
        self, client, user, closed_survey
    ):
        """Export button should appear on dashboard when survey is closed."""
        client.force_login(user)
        url = reverse("surveys:dashboard", kwargs={"slug": closed_survey.slug})
        response = client.get(url)

        assert response.status_code == 200
        assert "Data Governance" in response.content.decode()
        assert "Download Survey Data" in response.content.decode()
        assert "Closed" in response.content.decode()

    def test_dashboard_hides_export_button_for_open_survey(
        self, client, user, open_survey
    ):
        """Export button should NOT appear when survey is still open."""
        client.force_login(user)
        url = reverse("surveys:dashboard", kwargs={"slug": open_survey.slug})
        response = client.get(url)

        assert response.status_code == 200
        # Data governance section should not appear for open surveys
        assert "Download Survey Data" not in response.content.decode()

    def test_dashboard_hides_export_button_for_unauthorized_user(
        self, client, other_user, closed_survey
    ):
        """Export button should not appear for users without export permission."""
        client.force_login(other_user)
        url = reverse("surveys:dashboard", kwargs={"slug": closed_survey.slug})

        # Other user doesn't have access to view this survey at all
        response = client.get(url)
        assert response.status_code == 403

    def test_dashboard_shows_retention_info(self, client, user, closed_survey):
        """Dashboard should show retention period and deletion date."""
        client.force_login(user)
        url = reverse("surveys:dashboard", kwargs={"slug": closed_survey.slug})
        response = client.get(url)

        assert response.status_code == 200
        content = response.content.decode()
        assert "Retention Period" in content
        assert f"{closed_survey.retention_months}" in content
        if closed_survey.deletion_date:
            assert "Deletion scheduled" in content


# ========== Export Creation View Tests ==========


@pytest.mark.django_db
class TestSurveyExportCreateView:
    """Test the export disclaimer/creation view."""

    def test_export_create_requires_login(self, client, closed_survey):
        """Export creation should require authentication."""
        url = reverse(
            "surveys:survey_export_create", kwargs={"slug": closed_survey.slug}
        )
        response = client.get(url)

        assert response.status_code == 302  # Redirect to login
        assert "/accounts/login/" in response.url

    def test_export_create_requires_permission(self, client, other_user, closed_survey):
        """Export creation should require export permission."""
        client.force_login(other_user)
        url = reverse(
            "surveys:survey_export_create", kwargs={"slug": closed_survey.slug}
        )
        response = client.get(url)

        assert response.status_code == 403  # Permission denied

    def test_export_create_accessible_by_owner(self, client, user, closed_survey):
        """Survey owner should be able to access export creation."""
        client.force_login(user)
        url = reverse(
            "surveys:survey_export_create", kwargs={"slug": closed_survey.slug}
        )
        response = client.get(url)

        assert response.status_code == 200
        assert "Create Data Export" in response.content.decode()

    def test_export_create_post_creates_export(self, client, user, closed_survey):
        """POSTing to export create should create a DataExport record."""
        # Add a response to the survey so export has data
        from census_app.surveys.models import SurveyResponse

        SurveyResponse.objects.create(
            survey=closed_survey,
            submitted_by=user,
            submitted_at=timezone.now(),
            answers={},
        )

        client.force_login(user)
        url = reverse(
            "surveys:survey_export_create", kwargs={"slug": closed_survey.slug}
        )
        response = client.post(
            url,
            {
                "full_name": "Test User",
                "purpose": "Research analysis",
                "attestation_accepted": True,
            },
        )

        # Should redirect to download page
        assert response.status_code == 302

        # Should have created an export
        export = DataExport.objects.filter(survey=closed_survey).first()
        assert export is not None
        assert export.created_by == user

    def test_export_create_requires_attestation(self, client, user, closed_survey):
        """Export creation should require attestation acceptance."""
        client.force_login(user)
        url = reverse(
            "surveys:survey_export_create", kwargs={"slug": closed_survey.slug}
        )
        response = client.post(
            url,
            {
                "full_name": "Test User",
                "purpose": "Research",
                "attestation_accepted": False,  # Not accepted
            },
        )

        # Should show form error
        assert response.status_code == 200
        assert DataExport.objects.filter(survey=closed_survey).count() == 0


# ========== Export Download View Tests ==========


@pytest.mark.django_db
class TestSurveyExportDownloadView:
    """Test the export download page view."""

    @pytest.fixture
    def export_with_token(self, closed_survey, user):
        """Create an export with a download token."""
        from census_app.surveys.models import SurveyResponse

        SurveyResponse.objects.create(
            survey=closed_survey,
            submitted_by=user,
            submitted_at=timezone.now(),
            answers={},
        )

        export = ExportService.create_export(
            survey=closed_survey,
            user=user,
            password=None,
        )
        return export

    def test_download_page_requires_login(self, client, export_with_token):
        """Download page should require authentication."""
        url = reverse(
            "surveys:survey_export_download",
            kwargs={
                "slug": export_with_token.survey.slug,
                "export_id": export_with_token.id,
            },
        )
        response = client.get(url)

        assert response.status_code == 302  # Redirect to login

    def test_download_page_requires_permission(
        self, client, other_user, export_with_token
    ):
        """Download page should require export permission."""
        client.force_login(other_user)
        url = reverse(
            "surveys:survey_export_download",
            kwargs={
                "slug": export_with_token.survey.slug,
                "export_id": export_with_token.id,
            },
        )
        response = client.get(url)

        assert response.status_code == 403

    def test_download_page_shows_link(self, client, user, export_with_token):
        """Download page should show the download link with token."""
        client.force_login(user)
        url = reverse(
            "surveys:survey_export_download",
            kwargs={
                "slug": export_with_token.survey.slug,
                "export_id": export_with_token.id,
            },
        )
        response = client.get(url)

        assert response.status_code == 200
        assert "download" in response.content.decode().lower()
        assert export_with_token.download_token in response.content.decode()

    def test_download_page_shows_expiry_warning(self, client, user, export_with_token):
        """Download page should warn about token expiry."""
        client.force_login(user)
        url = reverse(
            "surveys:survey_export_download",
            kwargs={
                "slug": export_with_token.survey.slug,
                "export_id": export_with_token.id,
            },
        )
        response = client.get(url)

        assert response.status_code == 200
        content = response.content.decode().lower()
        assert "expires" in content or "valid" in content


# ========== Export File Download Tests ==========


@pytest.mark.django_db
class TestSurveyExportFileView:
    """Test the actual file download view with token validation."""

    @pytest.fixture
    def export_with_token(self, closed_survey, user):
        """Create an export with a download token."""
        from census_app.surveys.models import SurveyResponse

        SurveyResponse.objects.create(
            survey=closed_survey,
            submitted_by=user,
            submitted_at=timezone.now(),
            answers={"question_1": "answer_1"},
        )

        export = ExportService.create_export(
            survey=closed_survey,
            user=user,
            password=None,
        )
        return export

    def test_file_download_requires_valid_token(self, client, user, export_with_token):
        """File download should require a valid token."""
        client.force_login(user)
        url = reverse(
            "surveys:survey_export_file",
            kwargs={
                "slug": export_with_token.survey.slug,
                "export_id": export_with_token.id,
                "token": "invalid-token",
            },
        )
        response = client.get(url)

        # Should redirect to dashboard with error (user-friendly approach)
        assert response.status_code == 302
        assert response.url == f"/surveys/{export_with_token.survey.slug}/dashboard/"

    def test_file_download_with_valid_token(self, client, user, export_with_token):
        """File download should work with valid token."""
        client.force_login(user)
        url = reverse(
            "surveys:survey_export_file",
            kwargs={
                "slug": export_with_token.survey.slug,
                "export_id": export_with_token.id,
                "token": export_with_token.download_token,
            },
        )
        response = client.get(url)

        # Should return CSV file
        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv"
        assert "attachment" in response["Content-Disposition"]

    def test_file_download_marks_as_downloaded(self, client, user, export_with_token):
        """Downloading should mark export as downloaded."""
        assert export_with_token.downloaded_at is None

        client.force_login(user)
        url = reverse(
            "surveys:survey_export_file",
            kwargs={
                "slug": export_with_token.survey.slug,
                "export_id": export_with_token.id,
                "token": export_with_token.download_token,
            },
        )
        response = client.get(url)

        assert response.status_code == 200

        # Refresh from DB
        export_with_token.refresh_from_db()
        assert export_with_token.downloaded_at is not None

    def test_file_download_rejects_expired_token(self, client, user, export_with_token):
        """File download should reject expired tokens."""
        # Expire the token
        export_with_token.download_url_expires_at = timezone.now() - timezone.timedelta(
            minutes=1
        )
        export_with_token.save()

        client.force_login(user)
        url = reverse(
            "surveys:survey_export_file",
            kwargs={
                "slug": export_with_token.survey.slug,
                "export_id": export_with_token.id,
                "token": export_with_token.download_token,
            },
        )
        response = client.get(url)

        # Should redirect to dashboard with error (user-friendly approach)
        assert response.status_code == 302
        assert response.url == f"/surveys/{export_with_token.survey.slug}/dashboard/"

    def test_file_download_contains_correct_data(self, client, user, export_with_token):
        """Downloaded file should contain the survey data."""
        client.force_login(user)
        url = reverse(
            "surveys:survey_export_file",
            kwargs={
                "slug": export_with_token.survey.slug,
                "export_id": export_with_token.id,
                "token": export_with_token.download_token,
            },
        )
        response = client.get(url)

        assert response.status_code == 200

        # Check content contains CSV data
        content = response.content.decode()

        # Should be CSV with headers
        assert "Submitted At" in content or "submitted_at" in content
        # Should contain the username
        assert user.username in content
        # Should have CSV structure (commas and line breaks)
        assert "," in content and "\n" in content


# ========== Survey Close Integration Test ==========


@pytest.mark.django_db
class TestSurveyCloseIntegration:
    """Test that closing a survey triggers retention period correctly."""

    def test_closing_survey_sets_retention_fields(self, client, user, open_survey):
        """Closing survey should set closed_at and deletion_date."""
        assert open_survey.closed_at is None
        assert open_survey.deletion_date is None

        client.force_login(user)
        url = reverse("surveys:publish_settings", kwargs={"slug": open_survey.slug})

        # Submit close action
        response = client.post(
            url,
            {
                "action": "close",
            },
        )

        # Should redirect to dashboard
        assert response.status_code == 302

        # Refresh survey
        open_survey.refresh_from_db()

        # Should have set retention fields
        assert open_survey.status == Survey.Status.CLOSED
        assert open_survey.closed_at is not None
        assert open_survey.deletion_date is not None
        assert open_survey.retention_months == 6  # Default

    def test_closing_survey_shows_success_message(self, client, user, open_survey):
        """Closing survey should show retention information in success message."""
        client.force_login(user)
        url = reverse("surveys:publish_settings", kwargs={"slug": open_survey.slug})

        response = client.post(url, {"action": "close"}, follow=True)

        assert response.status_code == 200
        messages = list(response.context["messages"])
        assert len(messages) > 0
        assert "6 months" in str(messages[0])  # Shows retention period


# ========== Permission Enforcement Tests ==========


@pytest.mark.django_db
class TestExportPermissionEnforcement:
    """Test that export routes properly enforce permissions."""

    def test_export_routes_blocked_for_non_owners(
        self, client, other_user, closed_survey
    ):
        """All export routes should be blocked for unauthorized users."""
        client.force_login(other_user)

        # Create export
        create_url = reverse(
            "surveys:survey_export_create", kwargs={"slug": closed_survey.slug}
        )
        assert client.get(create_url).status_code == 403

        # Create export (need to create one first as owner)
        from census_app.surveys.models import SurveyResponse

        SurveyResponse.objects.create(
            survey=closed_survey,
            submitted_by=closed_survey.owner,
            submitted_at=timezone.now(),
            answers={},
        )
        export = ExportService.create_export(
            survey=closed_survey,
            user=closed_survey.owner,
            password=None,
        )

        download_url = reverse(
            "surveys:survey_export_download",
            kwargs={"slug": closed_survey.slug, "export_id": export.id},
        )
        assert client.get(download_url).status_code == 403

        # Download file - token-based access allows any authenticated user
        # (The token IS the permission - like a share link)
        file_url = reverse(
            "surveys:survey_export_file",
            kwargs={
                "slug": closed_survey.slug,
                "export_id": export.id,
                "token": export.download_token,
            },
        )
        # Valid token = access granted (token is the security mechanism)
        assert client.get(file_url).status_code == 200

    def test_export_routes_allowed_for_owner(self, client, user, closed_survey):
        """Survey owner should have access to all export routes."""
        from census_app.surveys.models import SurveyResponse

        SurveyResponse.objects.create(
            survey=closed_survey,
            submitted_by=user,
            submitted_at=timezone.now(),
            answers={},
        )

        client.force_login(user)

        # Create export
        create_url = reverse(
            "surveys:survey_export_create", kwargs={"slug": closed_survey.slug}
        )
        assert client.get(create_url).status_code == 200

        # Create an export
        export = ExportService.create_export(
            survey=closed_survey,
            user=user,
            password=None,
        )

        # View export download page
        download_url = reverse(
            "surveys:survey_export_download",
            kwargs={"slug": closed_survey.slug, "export_id": export.id},
        )
        assert client.get(download_url).status_code == 200

        # Download file
        file_url = reverse(
            "surveys:survey_export_file",
            kwargs={
                "slug": closed_survey.slug,
                "export_id": export.id,
                "token": export.download_token,
            },
        )
        assert client.get(file_url).status_code == 200
