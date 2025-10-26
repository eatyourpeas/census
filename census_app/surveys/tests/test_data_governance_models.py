"""
Tests for data governance models: Survey extensions, DataExport, LegalHold,
DataCustodian, and DataRetentionExtension.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.utils import timezone

from census_app.surveys.models import (
    DataCustodian,
    DataExport,
    DataRetentionExtension,
    LegalHold,
    Organization,
    Survey,
)


@pytest.fixture
def user(db):
    return User.objects.create_user(username="testuser", password="test123")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username="otheruser", password="test123")


@pytest.fixture
def org(db, user):
    return Organization.objects.create(name="Test Org", owner=user)


@pytest.fixture
def survey(db, user, org):
    return Survey.objects.create(
        owner=user,
        organization=org,
        name="Test Survey",
        slug="test-survey",
    )


@pytest.fixture
def closed_survey(db, user, org):
    """Survey that has been closed."""
    survey = Survey.objects.create(
        owner=user,
        organization=org,
        name="Closed Survey",
        slug="closed-survey",
    )
    survey.close_survey(user)
    return survey


# ============================================================================
# Survey Model Data Governance Extensions
# ============================================================================


class TestSurveyClosureAndRetention:
    """Test survey closure and retention period management."""

    def test_close_survey_sets_fields(self, survey, user):
        """Closing a survey should set closed_at, closed_by, and deletion_date."""
        assert survey.closed_at is None
        assert survey.closed_by is None
        assert survey.deletion_date is None

        survey.close_survey(user)

        assert survey.closed_at is not None
        assert survey.closed_by == user
        assert survey.deletion_date is not None
        assert survey.status == Survey.Status.CLOSED

    def test_close_survey_calculates_deletion_date(self, survey, user):
        """Deletion date should be retention_months * 30 days after closure."""
        survey.retention_months = 6
        survey.close_survey(user)

        expected_deletion = survey.closed_at + timedelta(days=180)  # 6 * 30
        assert survey.deletion_date == expected_deletion

    def test_extend_retention_updates_deletion_date(self, closed_survey, user):
        """Extending retention should update deletion_date."""
        original_deletion = closed_survey.deletion_date

        closed_survey.extend_retention(3, user, "Business need")

        assert closed_survey.deletion_date > original_deletion
        assert closed_survey.retention_months == 9  # 6 + 3

    def test_extend_retention_respects_24_month_limit(self, closed_survey, user):
        """Cannot extend retention beyond 24 months total."""
        # Already at 6 months, try to extend by 20 months (would be 26 total)
        with pytest.raises(ValueError, match="24 months"):
            closed_survey.extend_retention(20, user, "Too much")

    def test_extend_retention_fails_for_unclosed_survey(self, survey, user):
        """Cannot extend retention for survey that hasn't been closed."""
        with pytest.raises(ValueError, match="unclosed"):
            survey.extend_retention(3, user, "Too early")

    def test_can_extend_retention_property(self, closed_survey):
        """can_extend_retention should be True if under 24 months."""
        assert closed_survey.can_extend_retention is True

        # Max out retention
        closed_survey.retention_months = 24
        closed_survey.save()
        assert closed_survey.can_extend_retention is False

    def test_is_closed_property(self, survey, user):
        """is_closed should return True when survey is closed."""
        assert survey.is_closed is False

        survey.close_survey(user)
        assert survey.is_closed is True


class TestSurveySoftAndHardDeletion:
    """Test soft deletion (grace period) and hard deletion (permanent)."""

    def test_soft_delete_sets_timestamps(self, survey):
        """Soft delete should set deleted_at and hard_deletion_date."""
        survey.soft_delete()

        assert survey.deleted_at is not None
        assert survey.hard_deletion_date is not None

        # Hard deletion should be 30 days after soft delete
        expected_hard = survey.deleted_at + timedelta(days=30)
        assert survey.hard_deletion_date == expected_hard

    def test_days_until_deletion_calculates_correctly(self, closed_survey):
        """days_until_deletion should calculate remaining days."""
        # Set deletion date to 10 days from now
        closed_survey.deletion_date = timezone.now() + timedelta(days=10)
        closed_survey.save()

        days = closed_survey.days_until_deletion
        assert 9 <= days <= 10  # Allow for timing differences

    def test_days_until_deletion_returns_none_when_no_date(self, survey):
        """days_until_deletion should return None if no deletion_date."""
        assert survey.days_until_deletion is None

    def test_days_until_deletion_returns_none_when_deleted(self, survey):
        """days_until_deletion should return None if already deleted."""
        survey.soft_delete()
        assert survey.days_until_deletion is None


# ============================================================================
# DataExport Model
# ============================================================================


class TestDataExport:
    """Test data export tracking and download management."""

    def test_create_export(self, survey, user):
        """Can create a data export with all required fields."""
        export = DataExport.objects.create(
            survey=survey,
            created_by=user,
            download_token="test-token-12345",
            download_url_expires_at=timezone.now() + timedelta(days=7),
            response_count=10,
        )

        assert export.id is not None  # UUID should be generated
        assert export.survey == survey
        assert export.created_by == user
        assert export.download_count == 0
        assert export.downloaded_at is None
        assert export.is_encrypted is True  # Default

    def test_export_has_uuid_primary_key(self, survey, user):
        """Export should use UUID as primary key (not sequential integer)."""
        export = DataExport.objects.create(
            survey=survey,
            created_by=user,
            download_token="test-token",
            download_url_expires_at=timezone.now() + timedelta(days=7),
            response_count=5,
        )

        # UUID should be a string representation
        assert isinstance(str(export.id), str)
        assert len(str(export.id)) == 36  # UUID format

    def test_is_download_url_expired(self, survey, user):
        """Should correctly identify expired download URLs."""
        # Create export that expires in the past
        export = DataExport.objects.create(
            survey=survey,
            created_by=user,
            download_token="expired-token",
            download_url_expires_at=timezone.now() - timedelta(days=1),
            response_count=5,
        )

        assert export.is_download_url_expired is True

        # Create export that expires in the future
        export2 = DataExport.objects.create(
            survey=survey,
            created_by=user,
            download_token="valid-token",
            download_url_expires_at=timezone.now() + timedelta(days=7),
            response_count=5,
        )

        assert export2.is_download_url_expired is False

    def test_mark_downloaded(self, survey, user):
        """mark_downloaded should update download tracking fields."""
        export = DataExport.objects.create(
            survey=survey,
            created_by=user,
            download_token="test-token",
            download_url_expires_at=timezone.now() + timedelta(days=7),
            response_count=5,
        )

        assert export.downloaded_at is None
        assert export.download_count == 0

        export.mark_downloaded()

        assert export.downloaded_at is not None
        assert export.download_count == 1

        # Second download
        export.mark_downloaded()
        assert export.download_count == 2


# ============================================================================
# LegalHold Model
# ============================================================================


class TestLegalHold:
    """Test legal hold functionality."""

    def test_create_legal_hold(self, survey, user):
        """Can create a legal hold on a survey."""
        hold = LegalHold.objects.create(
            survey=survey,
            placed_by=user,
            reason="Ongoing litigation",
            authority="Court Order #12345",
        )

        assert hold.survey == survey
        assert hold.placed_by == user
        assert hold.placed_at is not None
        assert hold.removed_at is None
        assert hold.is_active is True

    def test_legal_hold_is_one_to_one(self, survey, user):
        """Only one legal hold per survey (OneToOne relationship)."""
        LegalHold.objects.create(
            survey=survey,
            placed_by=user,
            reason="First hold",
            authority="Court Order #1",
        )

        # Attempting to create another should fail
        with pytest.raises(Exception):  # IntegrityError
            LegalHold.objects.create(
                survey=survey,
                placed_by=user,
                reason="Second hold",
                authority="Court Order #2",
            )

    def test_remove_legal_hold(self, survey, user, other_user):
        """Can remove a legal hold."""
        hold = LegalHold.objects.create(
            survey=survey,
            placed_by=user,
            reason="Investigation",
            authority="Internal Audit",
        )

        assert hold.is_active is True

        hold.remove(other_user, "Investigation complete")

        assert hold.is_active is False
        assert hold.removed_by == other_user
        assert hold.removed_at is not None
        assert hold.removal_reason == "Investigation complete"

    def test_is_active_property(self, survey, user):
        """is_active should be False after removal."""
        hold = LegalHold.objects.create(
            survey=survey,
            placed_by=user,
            reason="Test",
            authority="Test Authority",
        )

        assert hold.is_active is True

        hold.remove(user, "Done")

        assert hold.is_active is False


# ============================================================================
# DataCustodian Model
# ============================================================================


class TestDataCustodian:
    """Test data custodian (external auditor) access."""

    def test_create_data_custodian(self, survey, user, other_user):
        """Can grant custodian access to a user."""
        custodian = DataCustodian.objects.create(
            user=other_user,
            survey=survey,
            granted_by=user,
            reason="External audit requirement",
        )

        assert custodian.user == other_user
        assert custodian.survey == survey
        assert custodian.granted_by == user
        assert custodian.granted_at is not None
        assert custodian.is_active is True

    def test_custodian_with_expiration(self, survey, user, other_user):
        """Custodian access can have an expiration date."""
        custodian = DataCustodian.objects.create(
            user=other_user,
            survey=survey,
            granted_by=user,
            expires_at=timezone.now() + timedelta(days=30),
            reason="30-day audit",
        )

        assert custodian.is_active is True

        # Set expiration to the past
        custodian.expires_at = timezone.now() - timedelta(days=1)
        custodian.save()

        assert custodian.is_active is False

    def test_revoke_custodian_access(self, survey, user, other_user):
        """Can revoke custodian access."""
        custodian = DataCustodian.objects.create(
            user=other_user,
            survey=survey,
            granted_by=user,
            reason="Audit",
        )

        assert custodian.is_active is True

        custodian.revoke(user)

        assert custodian.is_active is False
        assert custodian.revoked_by == user
        assert custodian.revoked_at is not None

    def test_unique_active_custodian_per_user_survey(self, survey, user, other_user):
        """Cannot have multiple active custodian assignments for same user/survey."""
        DataCustodian.objects.create(
            user=other_user,
            survey=survey,
            granted_by=user,
            reason="First assignment",
        )

        # Attempting to create another active assignment should fail
        with pytest.raises(Exception):  # IntegrityError
            DataCustodian.objects.create(
                user=other_user,
                survey=survey,
                granted_by=user,
                reason="Second assignment",
            )

    def test_can_create_new_custodian_after_revocation(self, survey, user, other_user):
        """Can create new custodian assignment after revoking previous one."""
        custodian1 = DataCustodian.objects.create(
            user=other_user,
            survey=survey,
            granted_by=user,
            reason="First audit",
        )

        custodian1.revoke(user)

        # Should be able to create a new one now
        custodian2 = DataCustodian.objects.create(
            user=other_user,
            survey=survey,
            granted_by=user,
            reason="Second audit",
        )

        assert custodian2.is_active is True


# ============================================================================
# DataRetentionExtension Model
# ============================================================================


class TestDataRetentionExtension:
    """Test retention extension audit trail."""

    def test_create_retention_extension(self, closed_survey, user):
        """Can create a retention extension record."""
        previous_date = closed_survey.deletion_date
        new_date = previous_date + timedelta(days=90)

        extension = DataRetentionExtension.objects.create(
            survey=closed_survey,
            requested_by=user,
            previous_deletion_date=previous_date,
            new_deletion_date=new_date,
            months_extended=3,
            reason="Business requirement",
        )

        assert extension.survey == closed_survey
        assert extension.requested_by == user
        assert extension.months_extended == 3
        assert extension.is_approved is False  # Not yet approved

    def test_approve_retention_extension(self, closed_survey, user, other_user):
        """Can approve a retention extension."""
        extension = DataRetentionExtension.objects.create(
            survey=closed_survey,
            requested_by=user,
            previous_deletion_date=closed_survey.deletion_date,
            new_deletion_date=closed_survey.deletion_date + timedelta(days=90),
            months_extended=3,
            reason="Need more time",
        )

        assert extension.is_approved is False

        extension.approved_by = other_user
        extension.approved_at = timezone.now()
        extension.save()

        assert extension.is_approved is True
        assert extension.approved_by == other_user

    def test_days_extended_property(self, closed_survey, user):
        """days_extended should calculate the difference in days."""
        previous_date = timezone.now()
        new_date = previous_date + timedelta(days=45)

        extension = DataRetentionExtension.objects.create(
            survey=closed_survey,
            requested_by=user,
            previous_deletion_date=previous_date,
            new_deletion_date=new_date,
            months_extended=2,
            reason="Extension",
        )

        assert extension.days_extended == 45

    def test_extension_audit_trail(self, closed_survey, user):
        """Multiple extensions should create an audit trail."""
        # First extension
        ext1 = DataRetentionExtension.objects.create(
            survey=closed_survey,
            requested_by=user,
            previous_deletion_date=closed_survey.deletion_date,
            new_deletion_date=closed_survey.deletion_date + timedelta(days=90),
            months_extended=3,
            reason="First extension",
        )

        # Second extension
        new_date = ext1.new_deletion_date
        ext2 = DataRetentionExtension.objects.create(
            survey=closed_survey,
            requested_by=user,
            previous_deletion_date=new_date,
            new_deletion_date=new_date + timedelta(days=90),
            months_extended=3,
            reason="Second extension",
        )

        # Should have 2 extension records
        extensions = DataRetentionExtension.objects.filter(survey=closed_survey)
        assert extensions.count() == 2
