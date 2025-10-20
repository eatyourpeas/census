"""Tests for the enhanced survey unlock view with dual-path encryption."""

import pytest
from django.urls import reverse
from django.test import Client
from census_app.core.models import User
from census_app.surveys.models import Survey, AuditLog


@pytest.mark.django_db(transaction=True)
class TestSurveyUnlockView:
    """Test the survey unlock view with password and recovery phrase support."""

    @pytest.fixture
    def user(self):
        """Create a test user."""
        return User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass"
        )

    @pytest.fixture
    def client_logged_in(self, user):
        """Create an authenticated client."""
        client = Client()
        client.login(username="testuser", password="testpass")
        return client

    @pytest.fixture
    def dual_encrypted_survey(self, user):
        """Create a survey with dual encryption (password + recovery phrase)."""
        survey = Survey.objects.create(
            name="Test Encrypted Survey",
            slug="test-encrypted",
            owner=user,
        )
        # Set up dual encryption
        kek = b"0" * 32  # 32-byte key
        password = "TestPassword123"
        recovery_words = ["abandon"] * 11 + ["about"]
        survey.set_dual_encryption(kek, password, recovery_words)

        # Set custom recovery hint for test
        survey.recovery_code_hint = "test hint"
        survey.save()

        return survey

    @pytest.fixture
    def legacy_encrypted_survey(self, user):
        """Create a survey with legacy key_hash encryption."""
        from census_app.surveys.utils import make_key_hash

        survey = Survey.objects.create(
            name="Test Legacy Survey",
            slug="test-legacy",
            owner=user,
        )
        # Set up legacy encryption
        key = b"test_key"
        key_hash, key_salt = make_key_hash(key)
        survey.key_hash = key_hash
        survey.key_salt = key_salt
        survey.save(update_fields=["key_hash", "key_salt"])
        return survey

    def test_unlock_view_displays_dual_encryption_tabs(
        self, client_logged_in, dual_encrypted_survey
    ):
        """Test that unlock view shows tabs for password and recovery phrase."""
        response = client_logged_in.get(
            reverse("surveys:unlock", args=[dual_encrypted_survey.slug])
        )
        assert response.status_code == 200
        assert b"has_dual_encryption" in response.content or "unlock_method" in str(response.content)
        assert "Password" in str(response.content)
        assert "Recovery Phrase" in str(response.content)

    def test_unlock_view_displays_recovery_hint(
        self, client_logged_in, dual_encrypted_survey
    ):
        """Test that recovery hint is displayed in unlock view."""
        response = client_logged_in.get(
            reverse("surveys:unlock", args=[dual_encrypted_survey.slug])
        )
        assert response.status_code == 200
        assert "test hint" in str(response.content)

    def test_unlock_with_password_success(
        self, client_logged_in, dual_encrypted_survey
    ):
        """Test successful unlock with password."""
        # Verify survey has dual encryption
        assert dual_encrypted_survey.has_dual_encryption()
        assert dual_encrypted_survey.encrypted_kek_password

        response = client_logged_in.post(
            reverse("surveys:unlock", args=[dual_encrypted_survey.slug]),
            {"unlock_method": "password", "password": "TestPassword123"},
        )

        assert response.status_code == 302
        # Option 4: Check for stored credentials, not survey_key
        assert "unlock_credentials" in client_logged_in.session
        assert "unlock_method" in client_logged_in.session
        assert client_logged_in.session["unlock_method"] == "password"
        assert "unlock_verified_at" in client_logged_in.session
        assert "unlock_survey_slug" in client_logged_in.session

    def test_unlock_with_password_failure(
        self, client_logged_in, dual_encrypted_survey
    ):
        """Test unlock failure with wrong password."""
        response = client_logged_in.post(
            reverse("surveys:unlock", args=[dual_encrypted_survey.slug]),
            {"unlock_method": "password", "password": "WrongPassword"},
        )
        assert response.status_code == 200  # Stay on unlock page
        assert "Invalid password" in str(response.content)
        assert "survey_key" not in client_logged_in.session

    def test_unlock_with_recovery_phrase_success(
        self, client_logged_in, dual_encrypted_survey
    ):
        """Test successful unlock with recovery phrase."""
        response = client_logged_in.post(
            reverse("surveys:unlock", args=[dual_encrypted_survey.slug]),
            {
                "unlock_method": "recovery",
                "recovery_phrase": "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about",
            },
        )
        assert response.status_code == 302  # Redirect to dashboard
        # Option 4: Check for stored credentials, not survey_key
        assert "unlock_credentials" in client_logged_in.session
        assert "unlock_method" in client_logged_in.session
        assert client_logged_in.session["unlock_method"] == "recovery"

    def test_unlock_with_recovery_phrase_normalization(
        self, client_logged_in, dual_encrypted_survey
    ):
        """Test that recovery phrase unlock works with different spacing/caps."""
        response = client_logged_in.post(
            reverse("surveys:unlock", args=[dual_encrypted_survey.slug]),
            {
                "unlock_method": "recovery",
                "recovery_phrase": "  ABANDON  abandon   ABANDON abandon abandon abandon abandon abandon abandon abandon abandon about  ",
            },
        )
        assert response.status_code == 302  # Redirect to dashboard
        # Option 4: Check for stored credentials, not survey_key
        assert "unlock_credentials" in client_logged_in.session
        assert "unlock_method" in client_logged_in.session
        assert client_logged_in.session["unlock_method"] == "recovery"

    def test_unlock_with_recovery_phrase_failure(
        self, client_logged_in, dual_encrypted_survey
    ):
        """Test unlock failure with wrong recovery phrase."""
        response = client_logged_in.post(
            reverse("surveys:unlock", args=[dual_encrypted_survey.slug]),
            {
                "unlock_method": "recovery",
                "recovery_phrase": "wrong wrong wrong wrong wrong wrong wrong wrong wrong wrong wrong wrong",
            },
        )
        assert response.status_code == 200  # Stay on unlock page
        assert "Invalid recovery phrase" in str(response.content)
        assert "survey_key" not in client_logged_in.session

    def test_unlock_recovery_phrase_creates_audit_log(
        self, client_logged_in, dual_encrypted_survey
    ):
        """Test that using recovery phrase creates an audit log entry."""
        initial_count = AuditLog.objects.filter(survey=dual_encrypted_survey).count()

        client_logged_in.post(
            reverse("surveys:unlock", args=[dual_encrypted_survey.slug]),
            {
                "unlock_method": "recovery",
                "recovery_phrase": "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about",
            },
        )

        final_count = AuditLog.objects.filter(survey=dual_encrypted_survey).count()
        assert final_count == initial_count + 1

        # Check that an audit log entry was created
        assert AuditLog.objects.filter(survey=dual_encrypted_survey).count() == initial_count + 1
        latest_log = AuditLog.objects.filter(survey=dual_encrypted_survey).latest("created_at")
        assert latest_log.metadata.get("unlock_method") == "recovery_phrase"

    def test_unlock_password_creates_audit_log(
        self, client_logged_in, dual_encrypted_survey
    ):
        """Test that using password creates an audit log entry."""
        initial_count = AuditLog.objects.filter(survey=dual_encrypted_survey).count()

        client_logged_in.post(
            reverse("surveys:unlock", args=[dual_encrypted_survey.slug]),
            {"unlock_method": "password", "password": "TestPassword123"},
        )

        final_count = AuditLog.objects.filter(survey=dual_encrypted_survey).count()
        assert final_count == initial_count + 1

        # Check that audit log has correct details
        latest_log = AuditLog.objects.filter(survey=dual_encrypted_survey).latest("created_at")
        assert latest_log.metadata.get("unlock_method") == "password"

    def test_unlock_legacy_survey_with_key(
        self, client_logged_in, legacy_encrypted_survey
    ):
        """Test that legacy surveys still work with key_hash verification."""
        response = client_logged_in.post(
            reverse("surveys:unlock", args=[legacy_encrypted_survey.slug]),
            {"key": "test_key"},
        )
        assert response.status_code == 302  # Redirect to dashboard
        # Option 4: Check for stored credentials, not survey_key
        assert "unlock_credentials" in client_logged_in.session
        assert "unlock_method" in client_logged_in.session
        assert client_logged_in.session["unlock_method"] == "legacy"

    def test_unlock_legacy_survey_shows_legacy_notice(
        self, client_logged_in, legacy_encrypted_survey
    ):
        """Test that legacy surveys show upgrade notice."""
        response = client_logged_in.get(
            reverse("surveys:unlock", args=[legacy_encrypted_survey.slug])
        )
        assert response.status_code == 200
        assert "legacy encryption" in str(response.content).lower()
        assert "upgrading" in str(response.content).lower() or "upgrade" in str(response.content).lower()

    def test_unlock_view_requires_authentication(self, dual_encrypted_survey):
        """Test that unlock view requires user to be logged in."""
        client = Client()  # Not logged in
        response = client.get(
            reverse("surveys:unlock", args=[dual_encrypted_survey.slug])
        )
        # Should redirect to login
        assert response.status_code == 302
        assert "/login" in response.url or "login" in response.url

    def test_unlock_view_requires_ownership(self, client_logged_in, user):
        """Test that unlock view requires user to own the survey."""
        # Create survey owned by different user
        other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="otherpass"
        )
        other_survey = Survey.objects.create(
            name="Other Survey",
            slug="other-survey",
            owner=other_user,
        )

        response = client_logged_in.get(reverse("surveys:unlock", args=[other_survey.slug]))
        assert response.status_code == 404  # get_object_or_404 returns 404

    # Option 4 specific tests
    def test_option4_kek_re_derivation(self, client_logged_in, dual_encrypted_survey):
        """Test that KEK is re-derived from stored credentials on each request."""
        from census_app.surveys.views import get_survey_key_from_session

        # First unlock
        client_logged_in.post(
            reverse("surveys:unlock", args=[dual_encrypted_survey.slug]),
            {"unlock_method": "password", "password": "TestPassword123"},
        )

        # Verify credentials are stored, not the key itself
        assert "unlock_credentials" in client_logged_in.session
        assert "survey_key" not in client_logged_in.session

        # Create a mock request to test re-derivation
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get("/")
        request.session = client_logged_in.session
        request.user = client_logged_in.cookies

        # Re-derive KEK
        kek1 = get_survey_key_from_session(request, dual_encrypted_survey.slug)
        kek2 = get_survey_key_from_session(request, dual_encrypted_survey.slug)

        # Both derivations should succeed and return same key
        assert kek1 is not None
        assert kek2 is not None
        assert kek1 == kek2

    def test_option4_session_timeout(self, client_logged_in, dual_encrypted_survey):
        """Test that session expires after 30 minutes."""
        from census_app.surveys.views import get_survey_key_from_session
        from django.utils import timezone
        from datetime import timedelta

        # Unlock survey
        client_logged_in.post(
            reverse("surveys:unlock", args=[dual_encrypted_survey.slug]),
            {"unlock_method": "password", "password": "TestPassword123"},
        )

        # Manually set timestamp to 31 minutes ago
        old_time = (timezone.now() - timedelta(minutes=31)).isoformat()
        session = client_logged_in.session
        session["unlock_verified_at"] = old_time
        session.save()

        # Force session reload to ensure changes are persisted
        session_key = session.session_key
        from django.contrib.sessions.backends.db import SessionStore
        fresh_session = SessionStore(session_key=session_key)

        # Create mock request with fresh session
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get("/")
        request.session = fresh_session

        # Attempt to get KEK - should fail due to timeout
        kek = get_survey_key_from_session(request, dual_encrypted_survey.slug)
        assert kek is None

        # Session should be cleared
        assert "unlock_credentials" not in request.session

    def test_option4_wrong_survey_slug(self, client_logged_in, dual_encrypted_survey, user):
        """Test that credentials only work for the correct survey."""
        from census_app.surveys.views import get_survey_key_from_session

        # Create another survey
        other_survey = Survey.objects.create(
            name="Other Survey",
            slug="other-survey",
            owner=user,
        )

        # Unlock first survey
        client_logged_in.post(
            reverse("surveys:unlock", args=[dual_encrypted_survey.slug]),
            {"unlock_method": "password", "password": "TestPassword123"},
        )

        # Create mock request
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get("/")
        request.session = client_logged_in.session

        # Try to get KEK for different survey - should fail
        kek = get_survey_key_from_session(request, other_survey.slug)
        assert kek is None
