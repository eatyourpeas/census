"""
Tests for organization-level encryption (Option 1: Key Escrow).

This tests the implementation of organization master key encryption
where organization owners/admins can recover surveys from their members.
"""

import os

from django.contrib.auth import get_user_model
import pytest

from census_app.surveys.models import (
    AuditLog,
    Organization,
    OrganizationMembership,
    Survey,
)
from census_app.surveys.utils import decrypt_kek_with_org_key, encrypt_kek_with_org_key

User = get_user_model()


@pytest.fixture
def org_with_master_key():
    """Create an organization with a master key."""
    owner = User.objects.create_user(username="org_owner", email="owner@example.com")
    org = Organization.objects.create(name="Test Org", owner=owner)
    # Generate a 32-byte master key for the organization
    org.encrypted_master_key = os.urandom(32)
    org.save()
    return org


@pytest.fixture
def member_user(org_with_master_key):
    """Create a regular member of the organization."""
    user = User.objects.create_user(username="member", email="member@example.com")
    OrganizationMembership.objects.create(
        organization=org_with_master_key,
        user=user,
        role=OrganizationMembership.Role.CREATOR,
    )
    return user


@pytest.fixture
def admin_user(org_with_master_key):
    """Create an admin member of the organization."""
    user = User.objects.create_user(username="admin", email="admin@example.com")
    OrganizationMembership.objects.create(
        organization=org_with_master_key,
        user=user,
        role=OrganizationMembership.Role.ADMIN,
    )
    return user


@pytest.fixture
def non_member_user():
    """Create a user who is NOT a member of the organization."""
    return User.objects.create_user(username="outsider", email="outsider@example.com")


@pytest.mark.django_db
class TestOrganizationEncryptionUtils:
    """Test organization encryption utility functions."""

    def test_encrypt_and_decrypt_with_org_key(self):
        """Test round-trip encryption/decryption with organization key."""
        # Generate test KEK and organization master key
        kek = os.urandom(32)
        org_key = os.urandom(32)

        # Encrypt KEK with organization key
        encrypted_blob = encrypt_kek_with_org_key(kek, org_key)

        # Verify it's different from original
        assert encrypted_blob != kek
        assert len(encrypted_blob) > 32  # Should include nonce + ciphertext

        # Decrypt and verify we get the original KEK back
        decrypted_kek = decrypt_kek_with_org_key(encrypted_blob, org_key)
        assert decrypted_kek == kek

    def test_decrypt_with_wrong_org_key_fails(self):
        """Test that decryption fails with wrong organization key."""
        from cryptography.exceptions import InvalidTag

        kek = os.urandom(32)
        org_key = os.urandom(32)
        wrong_key = os.urandom(32)

        encrypted_blob = encrypt_kek_with_org_key(kek, org_key)

        with pytest.raises(InvalidTag):
            decrypt_kek_with_org_key(encrypted_blob, wrong_key)

    def test_org_key_must_be_32_bytes(self):
        """Test that organization key must be exactly 32 bytes."""
        kek = os.urandom(32)
        short_key = os.urandom(16)  # Too short

        with pytest.raises(ValueError, match="must be 32 bytes"):
            encrypt_kek_with_org_key(kek, short_key)


@pytest.mark.django_db
class TestSurveyOrganizationEncryption:
    """Test Survey model organization encryption methods."""

    def test_set_org_encryption(self, org_with_master_key, member_user):
        """Test setting up organization encryption on a survey."""
        # Create a survey belonging to the organization
        survey = Survey.objects.create(
            owner=member_user,
            organization=org_with_master_key,
            name="Member Survey",
            slug="member-survey",
        )

        # Generate a KEK
        kek = os.urandom(32)

        # Set up organization encryption
        survey.set_org_encryption(kek, org_with_master_key)

        # Verify encrypted_kek_org is set
        assert survey.encrypted_kek_org is not None
        assert len(survey.encrypted_kek_org) > 32  # nonce + ciphertext

        # Verify it's encrypted (not the same as original KEK)
        assert bytes(survey.encrypted_kek_org) != kek

    def test_set_org_encryption_requires_master_key(self, member_user):
        """Test that organization must have a master key."""
        # Create organization without master key
        owner = User.objects.create_user(
            username="no_key_owner", email="nokey@example.com"
        )
        org_no_key = Organization.objects.create(name="No Key Org", owner=owner)

        survey = Survey.objects.create(
            owner=member_user,
            organization=org_no_key,
            name="Test Survey",
            slug="test-survey",
        )

        kek = os.urandom(32)

        with pytest.raises(ValueError, match="does not have a master key"):
            survey.set_org_encryption(kek, org_no_key)

    def test_has_org_encryption(self, org_with_master_key, member_user):
        """Test has_org_encryption() method."""
        survey = Survey.objects.create(
            owner=member_user,
            organization=org_with_master_key,
            name="Test Survey",
            slug="test-survey",
        )

        # Initially should be False
        assert survey.has_org_encryption() is False

        # After setting up encryption
        kek = os.urandom(32)
        survey.set_org_encryption(kek, org_with_master_key)

        assert survey.has_org_encryption() is True

    def test_unlock_with_org_key(self, org_with_master_key, member_user):
        """Test unlocking survey with organization master key."""
        survey = Survey.objects.create(
            owner=member_user,
            organization=org_with_master_key,
            name="Test Survey",
            slug="test-survey",
        )

        # Set up encryption
        kek = os.urandom(32)
        survey.set_org_encryption(kek, org_with_master_key)

        # Unlock with organization key
        unlocked_kek = survey.unlock_with_org_key(org_with_master_key)

        # Verify we got the original KEK back
        assert unlocked_kek == kek

    def test_unlock_with_org_key_wrong_organization(
        self, org_with_master_key, member_user
    ):
        """Test that unlock fails if survey doesn't belong to organization."""
        # Create survey in org_with_master_key
        survey = Survey.objects.create(
            owner=member_user,
            organization=org_with_master_key,
            name="Test Survey",
            slug="test-survey",
        )

        kek = os.urandom(32)
        survey.set_org_encryption(kek, org_with_master_key)

        # Create a different organization
        other_owner = User.objects.create_user(
            username="other_owner", email="other@example.com"
        )
        other_org = Organization.objects.create(name="Other Org", owner=other_owner)
        other_org.encrypted_master_key = os.urandom(32)
        other_org.save()

        # Try to unlock with wrong organization
        unlocked_kek = survey.unlock_with_org_key(other_org)

        # Should return None
        assert unlocked_kek is None

    def test_unlock_without_org_encryption_returns_none(
        self, org_with_master_key, member_user
    ):
        """Test that unlock returns None if survey has no org encryption."""
        survey = Survey.objects.create(
            owner=member_user,
            organization=org_with_master_key,
            name="Test Survey",
            slug="test-survey",
        )

        # Don't set up org encryption

        # Try to unlock
        unlocked_kek = survey.unlock_with_org_key(org_with_master_key)

        assert unlocked_kek is None


@pytest.mark.django_db
class TestOrganizationEncryptionIntegration:
    """Integration tests for organization encryption in survey creation."""

    def test_survey_creation_with_org_encryption(
        self, org_with_master_key, member_user, client
    ):
        """Test that surveys get organization encryption on creation."""
        # Log in as member
        client.force_login(member_user)

        # Create a survey with encryption
        from census_app.surveys.utils import generate_bip39_phrase

        kek = os.urandom(32)
        password = "test_password_123"
        recovery_words = generate_bip39_phrase(12)

        survey = Survey.objects.create(
            owner=member_user,
            organization=org_with_master_key,
            name="Member Survey",
            slug="member-survey",
        )

        # Set up dual encryption (simulating survey creation)
        survey.set_dual_encryption(kek, password, recovery_words)

        # Set up organization encryption
        survey.set_org_encryption(kek, org_with_master_key)

        # Verify all three encryption methods are set
        assert survey.has_dual_encryption() is True
        assert survey.has_org_encryption() is True

        # Verify organization owner can unlock
        unlocked_kek = survey.unlock_with_org_key(org_with_master_key)
        assert unlocked_kek == kek

        # Verify member can unlock with password
        password_unlocked = survey.unlock_with_password(password)
        assert password_unlocked == kek

        # Verify member can unlock with recovery phrase
        recovery_phrase = " ".join(recovery_words)
        recovery_unlocked = survey.unlock_with_recovery(recovery_phrase)
        assert recovery_unlocked == kek

    def test_multiple_surveys_in_same_org(self, org_with_master_key, member_user):
        """Test that multiple surveys can use the same org master key."""
        kek1 = os.urandom(32)
        kek2 = os.urandom(32)

        survey1 = Survey.objects.create(
            owner=member_user,
            organization=org_with_master_key,
            name="Survey 1",
            slug="survey-1",
        )
        survey1.set_org_encryption(kek1, org_with_master_key)

        survey2 = Survey.objects.create(
            owner=member_user,
            organization=org_with_master_key,
            name="Survey 2",
            slug="survey-2",
        )
        survey2.set_org_encryption(kek2, org_with_master_key)

        # Both should be unlockable with org key
        assert survey1.unlock_with_org_key(org_with_master_key) == kek1
        assert survey2.unlock_with_org_key(org_with_master_key) == kek2

        # Each should unlock to its own KEK
        assert kek1 != kek2


@pytest.mark.django_db
class TestOrganizationMasterKeyFields:
    """Test the new Survey model fields for organization encryption."""

    def test_survey_has_org_encryption_fields(self):
        """Test that Survey model has the new organization encryption fields."""
        owner = User.objects.create_user(username="owner", email="owner@example.com")
        survey = Survey.objects.create(
            owner=owner,
            name="Test Survey",
            slug="test-survey",
        )

        # Check that all fields exist and are None/blank by default
        assert hasattr(survey, "encrypted_kek_org")
        assert hasattr(survey, "recovery_threshold")
        assert hasattr(survey, "recovery_shares_count")

        assert survey.encrypted_kek_org is None
        assert survey.recovery_threshold is None
        assert survey.recovery_shares_count is None

    def test_organization_has_master_key_field(self):
        """Test that Organization model has encrypted_master_key field."""
        owner = User.objects.create_user(username="owner", email="owner@example.com")
        org = Organization.objects.create(name="Test Org", owner=owner)

        assert hasattr(org, "encrypted_master_key")
        assert org.encrypted_master_key is None

        # Set a master key
        org.encrypted_master_key = os.urandom(32)
        org.save()

        # Reload and verify it persisted
        org.refresh_from_db()
        assert org.encrypted_master_key is not None
        assert len(org.encrypted_master_key) == 32


@pytest.mark.django_db
class TestAuditLogKeyRecovery:
    """Test audit logging for organization key recovery."""

    def test_audit_log_has_key_recovery_action(self):
        """Test that AuditLog.Action has KEY_RECOVERY option."""
        assert hasattr(AuditLog.Action, "KEY_RECOVERY")
        assert AuditLog.Action.KEY_RECOVERY == "key_recovery"
