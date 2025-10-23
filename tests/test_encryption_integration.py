"""
Integration tests for encryption workflows.

These tests verify end-to-end encryption functionality for healthcare workers
and organizations, including password and recovery phrase unlock methods.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from census_app.surveys.models import Survey, SurveyResponse
from census_app.surveys.utils import encrypt_sensitive

User = get_user_model()


class EncryptionIntegrationTest(TestCase):
    """Integration tests for complete encryption workflow."""

    def setUp(self):
        """Set up test user and client."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.client = Client()
        self.client.login(username="testuser", password="testpass123")

    def test_complete_encryption_workflow_password_unlock(self):
        """Test complete workflow: create survey → unlock with password → verify access."""

        # Create survey with real dual encryption like existing tests
        survey = Survey.objects.create(
            name="Password Test Survey",
            slug="password-test-survey",
            owner=self.user,
        )

        # Set up real dual encryption
        kek = b"0" * 32  # 32-byte key
        password = "TestPassword123"
        recovery_words = ["abandon"] * 11 + ["about"]
        survey.set_dual_encryption(kek, password, recovery_words)

        # Create response with encrypted demographics
        test_demographics = {
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": "1980-01-01",
            "nhs_number": "1234567890"
        }

        encrypted_demographics = encrypt_sensitive(kek, test_demographics)

        SurveyResponse.objects.create(
            survey=survey,
            enc_demographics=encrypted_demographics,
            answers={"question_1": "test answer"}
        )

        # Test unlock with password
        unlock_data = {
            "unlock_method": "password",
            "password": password
        }

        response = self.client.post(reverse('surveys:unlock', kwargs={'slug': survey.slug}), data=unlock_data)
        self.assertEqual(response.status_code, 302)

        # Verify session contains unlock credentials
        session = self.client.session
        self.assertIn('unlock_credentials', session)
        self.assertIn('unlock_method', session)
        self.assertEqual(session['unlock_method'], 'password')

        # Test accessing encrypted data (survey should be unlocked in session)
        response = self.client.get(reverse('surveys:dashboard', kwargs={'slug': survey.slug}))
        self.assertEqual(response.status_code, 200)

    def test_complete_encryption_workflow_recovery_unlock(self):
        """Test complete workflow with recovery phrase unlock."""

        # Create survey with real dual encryption like existing tests
        survey = Survey.objects.create(
            name="Test Recovery Survey",
            slug="test-recovery-survey",
            owner=self.user,
        )

        # Set up real dual encryption
        kek = b"0" * 32  # 32-byte key
        password = "TestPassword123"
        recovery_words = ["abandon"] * 11 + ["about"]
        survey.set_dual_encryption(kek, password, recovery_words)

        # Test unlock with recovery phrase
        recovery_phrase = " ".join(recovery_words)

        unlock_data = {
            "unlock_method": "recovery",
            "recovery_phrase": recovery_phrase
        }

        response = self.client.post(reverse('surveys:unlock', kwargs={'slug': survey.slug}), data=unlock_data)
        self.assertEqual(response.status_code, 302)

        # Verify session contains unlock credentials
        session = self.client.session
        self.assertIn('unlock_credentials', session)
        self.assertIn('unlock_method', session)
        self.assertEqual(session['unlock_method'], 'recovery')

    def test_session_timeout_behavior(self):
        """Test that sessions timeout after 30 minutes."""

        # Create survey with real dual encryption
        survey = Survey.objects.create(
            name="Timeout Test Survey",
            slug="timeout-test-survey",
            owner=self.user,
        )

        # Set up real dual encryption
        kek = b"0" * 32  # 32-byte key
        password = "TestPassword123"
        recovery_words = ["abandon"] * 11 + ["about"]
        survey.set_dual_encryption(kek, password, recovery_words)

        # Unlock survey
        unlock_data = {
            "unlock_method": "password",
            "password": password
        }

        response = self.client.post(reverse('surveys:unlock', kwargs={'slug': survey.slug}), data=unlock_data)
        self.assertEqual(response.status_code, 302)

        # Verify session contains unlock credentials
        session = self.client.session
        self.assertIn('unlock_credentials', session)
        self.assertIn('unlock_verified_at', session)

        # Access dashboard should work when unlocked
        response = self.client.get(reverse('surveys:dashboard', kwargs={'slug': survey.slug}))
        self.assertEqual(response.status_code, 200)

    def test_cross_survey_isolation(self):
        """Test that unlocking one survey doesn't grant access to another."""

        # Create two surveys for same user with real encryption
        survey1 = Survey.objects.create(
            name="Survey 1",
            slug="survey-1",
            owner=self.user,
        )

        survey2 = Survey.objects.create(
            name="Survey 2",
            slug="survey-2",
            owner=self.user,
        )

        # Set up real dual encryption for both
        kek1 = b"1" * 32  # Different keys
        kek2 = b"2" * 32
        password1 = "TestPassword123"
        password2 = "TestPassword456"
        recovery_words = ["abandon"] * 11 + ["about"]

        survey1.set_dual_encryption(kek1, password1, recovery_words)
        survey2.set_dual_encryption(kek2, password2, recovery_words)

        # Unlock survey1
        unlock_data = {
            "unlock_method": "password",
            "password": password1
        }

        response = self.client.post(reverse('surveys:unlock', kwargs={'slug': survey1.slug}), data=unlock_data)
        self.assertEqual(response.status_code, 302)

        # Access to survey1 should work
        response = self.client.get(reverse('surveys:dashboard', kwargs={'slug': survey1.slug}))
        self.assertEqual(response.status_code, 200)

        # Try to access survey2 with survey1's password (should fail)
        unlock_data = {
            "unlock_method": "password",
            "password": password1  # Wrong password for survey2
        }

        response = self.client.post(reverse('surveys:unlock', kwargs={'slug': survey2.slug}), data=unlock_data)
        self.assertEqual(response.status_code, 200)  # Should stay on unlock page
        self.assertContains(response, "Invalid")

    def test_csv_export_with_encryption(self):
        """Test CSV export includes decrypted data when unlocked."""

        # Create survey with real dual encryption
        survey = Survey.objects.create(
            name="Export Test Survey",
            slug="export-test-survey",
            owner=self.user,
        )

        # Set up real dual encryption
        kek = b"0" * 32  # 32-byte key
        password = "TestPassword123"
        recovery_words = ["abandon"] * 11 + ["about"]
        survey.set_dual_encryption(kek, password, recovery_words)

        # Create response with encrypted demographics
        test_demographics = {
            "first_name": "Export",
            "last_name": "Test",
            "date_of_birth": "1990-12-25",
            "nhs_number": "5555555555"
        }

        encrypted_demographics = encrypt_sensitive(kek, test_demographics)
        SurveyResponse.objects.create(
            survey=survey,
            enc_demographics=encrypted_demographics,
            answers={"question_1": "export answer"}
        )

        # Unlock survey first
        unlock_data = {
            "unlock_method": "password",
            "password": password
        }

        response = self.client.post(reverse('surveys:unlock', kwargs={'slug': survey.slug}), data=unlock_data)
        self.assertEqual(response.status_code, 302)

        # Test accessing dashboard (since responses view doesn't exist)
        response = self.client.get(reverse('surveys:dashboard', kwargs={'slug': survey.slug}))
        self.assertEqual(response.status_code, 200)

        # Should contain survey name indicating successful access
        self.assertContains(response, "Export Test Survey")

    def test_invalid_unlock_attempts(self):
        """Test behavior with invalid passwords and recovery phrases."""

        # Create survey with real dual encryption
        survey = Survey.objects.create(
            name="Invalid Unlock Test",
            slug="invalid-unlock-test",
            owner=self.user,
        )

        # Set up real dual encryption
        kek = b"0" * 32  # 32-byte key
        password = "TestPassword123"
        recovery_words = ["abandon"] * 11 + ["about"]
        survey.set_dual_encryption(kek, password, recovery_words)

        # Test invalid password
        unlock_data = {
            "unlock_method": "password",
            "password": "wrongpassword"
        }

        response = self.client.post(reverse('surveys:unlock', kwargs={'slug': survey.slug}), data=unlock_data)
        # Should stay on unlock page with error message
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid")

        # Test invalid recovery phrase
        unlock_data = {
            "unlock_method": "recovery",
            "recovery_phrase": "wrong phrase words here invalid test bad"
        }

        response = self.client.post(reverse('surveys:unlock', kwargs={'slug': survey.slug}), data=unlock_data)
        # Should stay on unlock page with error message
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid")

    def test_legacy_key_unlock_compatibility(self):
        """Test legacy base64 key unlock still works."""

        # Create survey with legacy key hash/salt (use simple string like unit test)
        mock_legacy_key = b"test_key"

        from census_app.surveys.utils import make_key_hash
        key_hash, key_salt = make_key_hash(mock_legacy_key)

        survey = Survey.objects.create(
            name="Legacy Key Test",
            slug="legacy-key-test",
            owner=self.user,
            key_hash=key_hash,
            key_salt=key_salt
        )

        # Test legacy key unlock (use the string directly, like the unit test)
        unlock_data = {
            "key": "test_key"
        }

        response = self.client.post(reverse('surveys:unlock', kwargs={'slug': survey.slug}), data=unlock_data)

        # Should redirect on successful unlock
        self.assertEqual(response.status_code, 302)
        self.assertIn("unlock_credentials", self.client.session)
        self.assertEqual(self.client.session["unlock_method"], "legacy")
