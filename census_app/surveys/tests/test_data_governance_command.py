"""
Tests for the process_data_governance management command.

Tests email sending, deletion warnings, soft deletion, and hard deletion.
"""

from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from census_app.core.models import User
from census_app.surveys.models import LegalHold, Survey

TEST_PASSWORD = "x"


class ProcessDataGovernanceCommandTests(TestCase):
    """Test the process_data_governance management command."""

    def setUp(self):
        """Create test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password=TEST_PASSWORD
        )
        self.owner = User.objects.create_user(
            username="owner", email="owner@example.com", password=TEST_PASSWORD
        )

    def test_command_runs_successfully(self):
        """Test that the command runs without errors."""
        out = StringIO()
        call_command("process_data_governance", "--dry-run", stdout=out)

        output = out.getvalue()
        self.assertIn("Starting data governance processing", output)
        self.assertIn("Data governance processing completed", output)

    def test_dry_run_mode_makes_no_changes(self):
        """Test that dry-run mode doesn't actually delete anything."""
        # Create a survey that should be deleted
        survey = Survey.objects.create(
            name="Test Survey",
            slug="test-survey",
            owner=self.owner,
        )
        survey.close_survey(self.user)
        survey.deletion_date = timezone.now() - timedelta(days=1)
        survey.save()

        initial_count = Survey.objects.filter(deleted_at__isnull=True).count()

        # Run in dry-run mode
        call_command("process_data_governance", "--dry-run", verbosity=0)

        # Should not have deleted anything
        self.assertEqual(
            Survey.objects.filter(deleted_at__isnull=True).count(), initial_count
        )

    @patch(
        "census_app.surveys.services.retention_service.RetentionService.send_deletion_warning"
    )
    def test_deletion_warnings_sent_30_days(self, mock_send_warning):
        """Test that 30-day warnings are sent."""
        # Create survey due for deletion in 30 days
        survey = Survey.objects.create(
            name="Test Survey",
            slug="test-survey",
            owner=self.owner,
        )
        survey.close_survey(self.user)
        survey.deletion_date = timezone.now() + timedelta(days=30)
        survey.save()

        call_command("process_data_governance", verbosity=0)

        # Should have sent a warning
        self.assertTrue(mock_send_warning.called)
        mock_send_warning.assert_called_with(survey, 30)

    @patch(
        "census_app.surveys.services.retention_service.RetentionService.send_deletion_warning"
    )
    def test_deletion_warnings_sent_7_days(self, mock_send_warning):
        """Test that 7-day warnings are sent."""
        survey = Survey.objects.create(
            name="Test Survey",
            slug="test-survey-7",
            owner=self.owner,
        )
        survey.close_survey(self.user)
        survey.deletion_date = timezone.now() + timedelta(days=7)
        survey.save()

        call_command("process_data_governance", verbosity=0)

        self.assertTrue(mock_send_warning.called)
        mock_send_warning.assert_called_with(survey, 7)

    @patch(
        "census_app.surveys.services.retention_service.RetentionService.send_deletion_warning"
    )
    def test_deletion_warnings_sent_1_day(self, mock_send_warning):
        """Test that 1-day warnings are sent."""
        survey = Survey.objects.create(
            name="Test Survey",
            slug="test-survey-1",
            owner=self.owner,
        )
        survey.close_survey(self.user)
        survey.deletion_date = timezone.now() + timedelta(days=1)
        survey.save()

        call_command("process_data_governance", verbosity=0)

        self.assertTrue(mock_send_warning.called)
        mock_send_warning.assert_called_with(survey, 1)

    @patch("census_app.core.email_utils.send_branded_email")
    def test_deletion_warning_email_sent(self, mock_send_email):
        """Test that deletion warning emails are actually sent."""
        survey = Survey.objects.create(
            name="Test Survey",
            slug="test-survey-email",
            owner=self.owner,
        )
        survey.close_survey(self.user)
        survey.deletion_date = timezone.now() + timedelta(days=30)
        survey.save()

        # Call the command (not mocking send_deletion_warning this time)
        call_command("process_data_governance", verbosity=0)

        # Verify email was sent
        self.assertTrue(mock_send_email.called)
        call_args = mock_send_email.call_args

        # Check email recipient
        self.assertEqual(call_args.kwargs["to_email"], self.owner.email)

        # Check subject contains warning info
        self.assertIn("Survey Data Deletion Warning", call_args.kwargs["subject"])

    def test_soft_deletion_triggered(self):
        """Test that surveys are soft-deleted when retention expires."""
        survey = Survey.objects.create(
            name="Test Survey",
            slug="test-survey-soft",
            owner=self.owner,
        )
        survey.close_survey(self.user)
        survey.deletion_date = timezone.now() - timedelta(days=1)
        survey.save()

        self.assertIsNone(survey.deleted_at)

        call_command("process_data_governance", verbosity=0)

        survey.refresh_from_db()
        self.assertIsNotNone(survey.deleted_at)
        self.assertIsNotNone(survey.hard_deletion_date)

    def test_hard_deletion_triggered(self):
        """Test that surveys are hard-deleted after grace period."""
        survey = Survey.objects.create(
            name="Test Survey",
            slug="test-survey-hard",
            owner=self.owner,
        )
        survey.close_survey(self.user)
        survey.deleted_at = timezone.now() - timedelta(days=31)
        survey.hard_deletion_date = timezone.now() - timedelta(days=1)
        survey.save()

        survey_id = survey.id

        call_command("process_data_governance", verbosity=0)

        # Survey should be permanently deleted
        self.assertFalse(Survey.objects.filter(id=survey_id).exists())

    def test_legal_hold_prevents_deletion(self):
        """Test that surveys with legal holds are not deleted."""
        survey = Survey.objects.create(
            name="Test Survey",
            slug="test-survey-hold",
            owner=self.owner,
        )
        survey.close_survey(self.user)
        survey.deletion_date = timezone.now() - timedelta(days=1)
        survey.save()

        # Apply legal hold
        LegalHold.objects.create(
            survey=survey,
            placed_by=self.user,
            reason="Litigation in progress",
            authority="Court Order ABC-2024-001",
        )

        call_command("process_data_governance", verbosity=0)

        survey.refresh_from_db()
        # Should NOT be deleted
        self.assertIsNone(survey.deleted_at)

    def test_verbose_output(self):
        """Test that verbose mode provides detailed output."""
        survey = Survey.objects.create(
            name="Test Survey",
            slug="test-survey-verbose",
            owner=self.owner,
        )
        survey.close_survey(self.user)
        survey.deletion_date = timezone.now() + timedelta(days=30)
        survey.save()

        out = StringIO()
        call_command("process_data_governance", "--verbose", "--dry-run", stdout=out)

        output = out.getvalue()
        self.assertIn("30-day warnings:", output)
        self.assertIn("Test Survey", output)

    def test_command_reports_statistics(self):
        """Test that the command reports deletion statistics."""
        # Create a survey to soft delete
        survey = Survey.objects.create(
            name="Test Survey",
            slug="test-survey-stats",
            owner=self.owner,
        )
        survey.close_survey(self.user)
        survey.deletion_date = timezone.now() - timedelta(days=1)
        survey.save()

        out = StringIO()
        call_command("process_data_governance", stdout=out)

        output = out.getvalue()
        self.assertIn("Soft deleted: 1 surveys", output)

    @patch("census_app.core.email_utils.send_branded_email")
    def test_no_warnings_for_surveys_not_in_window(self, mock_send_email):
        """Test that warnings aren't sent for surveys outside warning windows."""
        # Create survey with deletion date not in any warning window
        survey = Survey.objects.create(
            name="Test Survey",
            slug="test-survey-no-warn",
            owner=self.owner,
        )
        survey.close_survey(self.user)
        # Set deletion date to 15 days (not 30, 7, or 1)
        survey.deletion_date = timezone.now() + timedelta(days=15)
        survey.save()

        call_command("process_data_governance", verbosity=0)

        # No emails should be sent
        self.assertFalse(mock_send_email.called)

    def test_multiple_surveys_processed(self):
        """Test that multiple surveys are processed in one run."""
        # Create multiple surveys at different stages
        survey1 = Survey.objects.create(
            name="Survey 30 Days",
            slug="survey-30",
            owner=self.owner,
        )
        survey1.close_survey(self.user)
        survey1.deletion_date = timezone.now() + timedelta(days=30)
        survey1.save()

        survey2 = Survey.objects.create(
            name="Survey 7 Days",
            slug="survey-7",
            owner=self.owner,
        )
        survey2.close_survey(self.user)
        survey2.deletion_date = timezone.now() + timedelta(days=7)
        survey2.save()

        survey3 = Survey.objects.create(
            name="Survey Expired",
            slug="survey-expired",
            owner=self.owner,
        )
        survey3.close_survey(self.user)
        survey3.deletion_date = timezone.now() - timedelta(days=1)
        survey3.save()

        out = StringIO()
        call_command("process_data_governance", stdout=out)

        output = out.getvalue()
        # Should process warnings for survey1 and survey2
        self.assertIn("30-day warnings: 1", output)
        self.assertIn("7-day warnings: 1", output)
        # Should soft delete survey3
        self.assertIn("Soft deleted: 1", output)
