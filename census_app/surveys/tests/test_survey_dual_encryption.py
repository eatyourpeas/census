"""
Tests for Survey model Option 2 encryption methods.
"""

import os

import pytest
from django.contrib.auth import get_user_model

from census_app.surveys.models import Survey
from census_app.surveys.utils import generate_bip39_phrase

User = get_user_model()


@pytest.mark.django_db
class TestSurveyDualEncryption:
    """Test Survey model Option 2 encryption methods."""

    @pytest.fixture
    def user(self):
        """Create a test user."""
        return User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass"
        )

    @pytest.fixture
    def survey(self, user):
        """Create a test survey."""
        return Survey.objects.create(
            name="Test Survey",
            slug="test-survey",
            owner=user,
        )

    def test_set_dual_encryption(self, survey):
        """Should set up dual-path encryption."""
        kek = os.urandom(32)
        password = "MySecurePassword123"
        recovery_words = generate_bip39_phrase(12)

        survey.set_dual_encryption(kek, password, recovery_words)
        survey.refresh_from_db()

        # Check all fields are set
        assert survey.encrypted_kek_password is not None
        assert survey.encrypted_kek_recovery is not None
        assert survey.recovery_code_hint != ""
        assert survey.key_hash is not None  # Backward compatibility
        assert survey.key_salt is not None

        # Check hint format
        assert survey.recovery_code_hint.startswith(recovery_words[0])
        assert survey.recovery_code_hint.endswith(recovery_words[-1])

    def test_unlock_with_password_success(self, survey):
        """Should unlock survey with correct password."""
        kek = os.urandom(32)
        password = "CorrectPassword123"
        recovery_words = generate_bip39_phrase(12)

        survey.set_dual_encryption(kek, password, recovery_words)
        survey.save()

        # Unlock with password
        unlocked_kek = survey.unlock_with_password(password)

        assert unlocked_kek == kek

    def test_unlock_with_password_failure(self, survey):
        """Should fail to unlock with wrong password."""
        kek = os.urandom(32)
        correct_password = "CorrectPassword123"
        wrong_password = "WrongPassword456"
        recovery_words = generate_bip39_phrase(12)

        survey.set_dual_encryption(kek, correct_password, recovery_words)
        survey.save()

        # Try wrong password
        unlocked_kek = survey.unlock_with_password(wrong_password)

        assert unlocked_kek is None

    def test_unlock_with_recovery_success(self, survey):
        """Should unlock survey with correct recovery phrase."""
        kek = os.urandom(32)
        password = "Password123"
        recovery_words = generate_bip39_phrase(12)
        recovery_phrase = " ".join(recovery_words)

        survey.set_dual_encryption(kek, password, recovery_words)
        survey.save()

        # Unlock with recovery phrase
        unlocked_kek = survey.unlock_with_recovery(recovery_phrase)

        assert unlocked_kek == kek

    def test_unlock_with_recovery_failure(self, survey):
        """Should fail to unlock with wrong recovery phrase."""
        kek = os.urandom(32)
        password = "Password123"
        correct_recovery_words = generate_bip39_phrase(12)
        wrong_recovery_words = generate_bip39_phrase(12)

        survey.set_dual_encryption(kek, password, correct_recovery_words)
        survey.save()

        # Try wrong recovery phrase
        wrong_phrase = " ".join(wrong_recovery_words)
        unlocked_kek = survey.unlock_with_recovery(wrong_phrase)

        assert unlocked_kek is None

    def test_unlock_recovery_phrase_normalization(self, survey):
        """Should normalize whitespace and case in recovery phrase."""
        kek = os.urandom(32)
        password = "Password123"
        recovery_words = generate_bip39_phrase(12)
        recovery_phrase = " ".join(recovery_words)

        survey.set_dual_encryption(kek, password, recovery_words)
        survey.save()

        # Try with different formatting
        messy_phrase = "  ".join(w.upper() for w in recovery_words)
        unlocked_kek = survey.unlock_with_recovery(messy_phrase)

        assert unlocked_kek == kek

    def test_has_dual_encryption(self, survey):
        """Should correctly identify dual encryption status."""
        # Initially no dual encryption
        assert not survey.has_dual_encryption()

        # After setting up
        kek = os.urandom(32)
        password = "Password123"
        recovery_words = generate_bip39_phrase(12)

        survey.set_dual_encryption(kek, password, recovery_words)
        survey.save()

        assert survey.has_dual_encryption()

    def test_both_unlock_methods_work(self, survey):
        """Should be able to unlock with either password or recovery phrase."""
        kek = os.urandom(32)
        password = "MyPassword123"
        recovery_words = generate_bip39_phrase(12)
        recovery_phrase = " ".join(recovery_words)

        survey.set_dual_encryption(kek, password, recovery_words)
        survey.save()

        # Both methods should return the same KEK
        kek_via_password = survey.unlock_with_password(password)
        kek_via_recovery = survey.unlock_with_recovery(recovery_phrase)

        assert kek_via_password == kek
        assert kek_via_recovery == kek

    def test_unlock_without_dual_encryption(self, survey):
        """Should return None when trying to unlock survey without dual encryption."""
        password = "AnyPassword"
        recovery_phrase = "any recovery phrase"

        # Survey doesn't have dual encryption set up
        assert survey.unlock_with_password(password) is None
        assert survey.unlock_with_recovery(recovery_phrase) is None


@pytest.mark.django_db
class TestPasswordRecoveryScenario:
    """Test real-world password recovery scenarios."""

    @pytest.fixture
    def user(self):
        return User.objects.create_user(
            username="patient", email="patient@example.com", password="testpass"
        )

    @pytest.fixture
    def survey_with_encryption(self, user):
        """Create a survey with dual encryption set up."""
        survey = Survey.objects.create(
            name="Patient Survey",
            slug="patient-survey",
            owner=user,
        )

        kek = os.urandom(32)
        password = "ForgottenPassword123"
        recovery_words = generate_bip39_phrase(12)

        survey.set_dual_encryption(kek, password, recovery_words)
        survey.save()

        # Store recovery phrase for testing (in reality, user has this saved)
        survey._test_recovery_phrase = " ".join(recovery_words)
        survey._test_kek = kek

        return survey

    def test_user_forgets_password_uses_recovery(self, survey_with_encryption):
        """
        Simulate user forgetting password but having recovery phrase written down.
        """
        survey = survey_with_encryption

        # User tries wrong password - fails
        wrong_password = "WrongGuess456"
        result = survey.unlock_with_password(wrong_password)
        assert result is None

        # User finds their recovery phrase card
        recovery_phrase = survey._test_recovery_phrase

        # Uses recovery phrase - succeeds
        unlocked_kek = survey.unlock_with_recovery(recovery_phrase)
        assert unlocked_kek == survey._test_kek

    def test_recovery_hint_helps_user(self, survey_with_encryption):
        """
        Test that recovery hint helps user verify they have the right phrase.
        """
        survey = survey_with_encryption
        hint = survey.recovery_code_hint

        # Hint should contain first and last word
        recovery_words = survey._test_recovery_phrase.split()
        assert recovery_words[0] in hint
        assert recovery_words[-1] in hint

    def test_partial_recovery_phrase_fails(self, survey_with_encryption):
        """
        Verify that incomplete recovery phrase doesn't work.
        """
        survey = survey_with_encryption
        recovery_words = survey._test_recovery_phrase.split()

        # Try with only first 6 words
        partial_phrase = " ".join(recovery_words[:6])
        result = survey.unlock_with_recovery(partial_phrase)

        assert result is None
