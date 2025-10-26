"""
Tests for data governance permissions.

Tests role-based access control for:
- Survey closure
- Data export
- Retention extension
- Legal holds
- Data custodian management
- Soft/hard deletion
"""

from __future__ import annotations

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
import pytest

from census_app.surveys.models import (
    DataCustodian,
    Organization,
    OrganizationMembership,
    Survey,
)
from census_app.surveys.permissions import (
    can_close_survey,
    can_export_survey_data,
    can_extend_retention,
    can_hard_delete_survey,
    can_manage_data_custodians,
    can_manage_legal_hold,
    can_soft_delete_survey,
    require_can_export_survey_data,
)

TEST_PASSWORD = "x"


@pytest.fixture
def users(db):
    """Create test users."""
    owner = User.objects.create_user(username="owner", password=TEST_PASSWORD)
    org_owner = User.objects.create_user(username="org_owner", password=TEST_PASSWORD)
    org_admin = User.objects.create_user(username="org_admin", password=TEST_PASSWORD)
    custodian = User.objects.create_user(username="custodian", password=TEST_PASSWORD)
    outsider = User.objects.create_user(username="outsider", password=TEST_PASSWORD)
    return {
        "owner": owner,
        "org_owner": org_owner,
        "org_admin": org_admin,
        "custodian": custodian,
        "outsider": outsider,
    }


@pytest.fixture
def org(db, users):
    """Create organization with memberships."""
    org = Organization.objects.create(name="Test Org", owner=users["org_owner"])

    OrganizationMembership.objects.create(
        organization=org,
        user=users["org_admin"],
        role=OrganizationMembership.Role.ADMIN,
    )

    return org


@pytest.fixture
def survey(db, users, org):
    """Create survey owned by 'owner' user in the organization."""
    return Survey.objects.create(
        owner=users["owner"],
        organization=org,
        name="Test Survey",
        slug="test-survey",
    )


@pytest.fixture
def survey_with_custodian(db, survey, users):
    """Survey with an active data custodian."""
    DataCustodian.objects.create(
        user=users["custodian"],
        survey=survey,
        granted_by=users["org_owner"],
        reason="External audit",
    )
    return survey


# ============================================================================
# Test Survey Closure Permissions
# ============================================================================


class TestCloseSurveyPermissions:
    """Test who can close a survey."""

    def test_survey_owner_can_close(self, survey, users):
        """Survey owner can close their survey."""
        assert can_close_survey(users["owner"], survey) is True

    def test_org_owner_can_close(self, survey, users):
        """Organization owner can close any survey in their org."""
        assert can_close_survey(users["org_owner"], survey) is True

    def test_org_admin_cannot_close(self, survey, users):
        """Organization admin cannot close surveys."""
        assert can_close_survey(users["org_admin"], survey) is False

    def test_outsider_cannot_close(self, survey, users):
        """Non-member cannot close survey."""
        assert can_close_survey(users["outsider"], survey) is False

    def test_unauthenticated_cannot_close(self, survey, db):
        """Unauthenticated user cannot close survey."""
        anon = User()  # Not saved to DB
        assert can_close_survey(anon, survey) is False


# ============================================================================
# Test Data Export Permissions
# ============================================================================


class TestExportSurveyDataPermissions:
    """Test who can export survey data."""

    def test_survey_owner_can_export(self, survey, users):
        """Survey owner can export their survey data."""
        assert can_export_survey_data(users["owner"], survey) is True

    def test_org_owner_can_export(self, survey, users):
        """Organization owner can export all surveys in their org."""
        assert can_export_survey_data(users["org_owner"], survey) is True

    def test_org_admin_can_export(self, survey, users):
        """Organization admin can export survey data."""
        assert can_export_survey_data(users["org_admin"], survey) is True

    def test_data_custodian_can_export(self, survey_with_custodian, users):
        """Active data custodian can export survey data."""
        assert can_export_survey_data(users["custodian"], survey_with_custodian) is True

    def test_revoked_custodian_cannot_export(self, survey_with_custodian, users):
        """Revoked data custodian cannot export."""
        custodian = DataCustodian.objects.get(user=users["custodian"])
        custodian.revoke(users["org_owner"])

        assert (
            can_export_survey_data(users["custodian"], survey_with_custodian) is False
        )

    def test_outsider_cannot_export(self, survey, users):
        """Non-member cannot export survey data."""
        assert can_export_survey_data(users["outsider"], survey) is False

    def test_require_can_export_raises_permission_denied(self, survey, users):
        """require_can_export should raise PermissionDenied for unauthorized users."""
        with pytest.raises(PermissionDenied, match="permission to export"):
            require_can_export_survey_data(users["outsider"], survey)


# ============================================================================
# Test Retention Extension Permissions
# ============================================================================


class TestExtendRetentionPermissions:
    """Test who can extend retention periods."""

    def test_org_owner_can_extend_retention(self, survey, users):
        """Organization owner can extend retention."""
        assert can_extend_retention(users["org_owner"], survey) is True

    def test_survey_owner_cannot_extend_if_has_org(self, survey, users):
        """Survey owner cannot extend if survey has organization."""
        assert can_extend_retention(users["owner"], survey) is False

    def test_survey_owner_can_extend_without_org(self, db, users):
        """Survey owner can extend if survey has no organization."""
        survey = Survey.objects.create(
            owner=users["owner"],
            organization=None,
            name="No Org Survey",
            slug="no-org",
        )
        assert can_extend_retention(users["owner"], survey) is True

    def test_org_admin_cannot_extend_retention(self, survey, users):
        """Organization admin cannot extend retention."""
        assert can_extend_retention(users["org_admin"], survey) is False

    def test_outsider_cannot_extend_retention(self, survey, users):
        """Non-member cannot extend retention."""
        assert can_extend_retention(users["outsider"], survey) is False


# ============================================================================
# Test Legal Hold Permissions
# ============================================================================


class TestLegalHoldPermissions:
    """Test who can place/remove legal holds."""

    def test_org_owner_can_manage_legal_hold(self, survey, users):
        """Organization owner can manage legal holds."""
        assert can_manage_legal_hold(users["org_owner"], survey) is True

    def test_survey_owner_cannot_manage_hold_if_has_org(self, survey, users):
        """Survey owner cannot manage hold if survey has organization."""
        assert can_manage_legal_hold(users["owner"], survey) is False

    def test_survey_owner_can_manage_hold_without_org(self, db, users):
        """Survey owner can manage hold if survey has no organization."""
        survey = Survey.objects.create(
            owner=users["owner"],
            organization=None,
            name="No Org Survey",
            slug="no-org",
        )
        assert can_manage_legal_hold(users["owner"], survey) is True

    def test_org_admin_cannot_manage_legal_hold(self, survey, users):
        """Organization admin cannot manage legal holds."""
        assert can_manage_legal_hold(users["org_admin"], survey) is False

    def test_outsider_cannot_manage_legal_hold(self, survey, users):
        """Non-member cannot manage legal holds."""
        assert can_manage_legal_hold(users["outsider"], survey) is False


# ============================================================================
# Test Data Custodian Management Permissions
# ============================================================================


class TestManageDataCustodiansPermissions:
    """Test who can grant/revoke data custodian access."""

    def test_org_owner_can_manage_custodians(self, survey, users):
        """Organization owner can manage data custodians."""
        assert can_manage_data_custodians(users["org_owner"], survey) is True

    def test_survey_owner_cannot_manage_custodians_if_has_org(self, survey, users):
        """Survey owner cannot delegate custodian access for security."""
        assert can_manage_data_custodians(users["owner"], survey) is False

    def test_survey_owner_can_manage_custodians_without_org(self, db, users):
        """Survey owner can manage custodians if no organization."""
        survey = Survey.objects.create(
            owner=users["owner"],
            organization=None,
            name="No Org Survey",
            slug="no-org",
        )
        assert can_manage_data_custodians(users["owner"], survey) is True

    def test_org_admin_cannot_manage_custodians(self, survey, users):
        """Organization admin cannot manage custodians."""
        assert can_manage_data_custodians(users["org_admin"], survey) is False


# ============================================================================
# Test Soft Deletion Permissions
# ============================================================================


class TestSoftDeletePermissions:
    """Test who can soft delete surveys."""

    def test_survey_owner_can_soft_delete(self, survey, users):
        """Survey owner can soft delete their survey."""
        assert can_soft_delete_survey(users["owner"], survey) is True

    def test_org_owner_can_soft_delete(self, survey, users):
        """Organization owner can soft delete any survey."""
        assert can_soft_delete_survey(users["org_owner"], survey) is True

    def test_org_admin_cannot_soft_delete(self, survey, users):
        """Organization admin cannot soft delete."""
        assert can_soft_delete_survey(users["org_admin"], survey) is False

    def test_outsider_cannot_soft_delete(self, survey, users):
        """Non-member cannot soft delete."""
        assert can_soft_delete_survey(users["outsider"], survey) is False


# ============================================================================
# Test Hard Deletion Permissions
# ============================================================================


class TestHardDeletePermissions:
    """Test who can permanently delete surveys."""

    def test_org_owner_can_hard_delete(self, survey, users):
        """Organization owner can hard delete surveys."""
        assert can_hard_delete_survey(users["org_owner"], survey) is True

    def test_survey_owner_cannot_hard_delete_if_has_org(self, survey, users):
        """Survey owner cannot hard delete if survey has organization."""
        assert can_hard_delete_survey(users["owner"], survey) is False

    def test_survey_owner_can_hard_delete_without_org(self, db, users):
        """Survey owner can hard delete if no organization."""
        survey = Survey.objects.create(
            owner=users["owner"],
            organization=None,
            name="No Org Survey",
            slug="no-org",
        )
        assert can_hard_delete_survey(users["owner"], survey) is True

    def test_org_admin_cannot_hard_delete(self, survey, users):
        """Organization admin cannot hard delete."""
        assert can_hard_delete_survey(users["org_admin"], survey) is False

    def test_outsider_cannot_hard_delete(self, survey, users):
        """Non-member cannot hard delete."""
        assert can_hard_delete_survey(users["outsider"], survey) is False


# ============================================================================
# Test Permission Hierarchy
# ============================================================================


class TestPermissionHierarchy:
    """Test that permission hierarchy is correctly enforced."""

    def test_org_owner_has_most_permissions(self, survey, users):
        """Organization owner should have all permissions."""
        org_owner = users["org_owner"]

        assert can_close_survey(org_owner, survey) is True
        assert can_export_survey_data(org_owner, survey) is True
        assert can_extend_retention(org_owner, survey) is True
        assert can_manage_legal_hold(org_owner, survey) is True
        assert can_manage_data_custodians(org_owner, survey) is True
        assert can_soft_delete_survey(org_owner, survey) is True
        assert can_hard_delete_survey(org_owner, survey) is True

    def test_survey_owner_limited_permissions_with_org(self, survey, users):
        """Survey owner has limited permissions when survey has org."""
        owner = users["owner"]

        # Can do basic operations
        assert can_close_survey(owner, survey) is True
        assert can_export_survey_data(owner, survey) is True
        assert can_soft_delete_survey(owner, survey) is True

        # Cannot do privileged operations (org owner only)
        assert can_extend_retention(owner, survey) is False
        assert can_manage_legal_hold(owner, survey) is False
        assert can_manage_data_custodians(owner, survey) is False
        assert can_hard_delete_survey(owner, survey) is False

    def test_org_admin_export_only(self, survey, users):
        """Organization admin can only export data."""
        admin = users["org_admin"]

        # Can export
        assert can_export_survey_data(admin, survey) is True

        # Cannot do other operations
        assert can_close_survey(admin, survey) is False
        assert can_extend_retention(admin, survey) is False
        assert can_manage_legal_hold(admin, survey) is False
        assert can_manage_data_custodians(admin, survey) is False
        assert can_soft_delete_survey(admin, survey) is False
        assert can_hard_delete_survey(admin, survey) is False

    def test_custodian_export_only(self, survey_with_custodian, users):
        """Data custodian can only export data."""
        custodian = users["custodian"]
        survey = survey_with_custodian

        # Can export
        assert can_export_survey_data(custodian, survey) is True

        # Cannot do anything else
        assert can_close_survey(custodian, survey) is False
        assert can_extend_retention(custodian, survey) is False
        assert can_manage_legal_hold(custodian, survey) is False
        assert can_manage_data_custodians(custodian, survey) is False
        assert can_soft_delete_survey(custodian, survey) is False
        assert can_hard_delete_survey(custodian, survey) is False

    def test_outsider_no_permissions(self, survey, users):
        """Outsider should have no permissions."""
        outsider = users["outsider"]

        assert can_close_survey(outsider, survey) is False
        assert can_export_survey_data(outsider, survey) is False
        assert can_extend_retention(outsider, survey) is False
        assert can_manage_legal_hold(outsider, survey) is False
        assert can_manage_data_custodians(outsider, survey) is False
        assert can_soft_delete_survey(outsider, survey) is False
        assert can_hard_delete_survey(outsider, survey) is False
