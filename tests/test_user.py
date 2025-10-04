from django.contrib.auth import get_user_model
from django.urls import reverse
import pytest

from census_app.surveys.models import Organization, OrganizationMembership

TEST_PASSWORD = "ComplexTestPassword123!"


@pytest.mark.django_db
def test_signup_as_org_creates_org_and_shows_on_profile(client):
    email = "orgowner@example.com"
    password = TEST_PASSWORD

    # Submit signup form choosing an organisation account
    resp = client.post(
        reverse("core:signup"),
        data={
            "email": email,
            "password1": password,
            "password2": password,
            "account_type": "org",
            "org_name": "Acme Health",
        },
        follow=True,
    )

    # Should finish with a 200 after following redirects (to org users page)
    assert resp.status_code == 200

    User = get_user_model()
    user = User.objects.get(email=email)

    # Organisation created and owned by the new user
    org = Organization.objects.get(owner=user)
    assert org.name == "Acme Health"

    # Membership created with ADMIN role
    mem = OrganizationMembership.objects.get(user=user, organization=org)
    assert mem.role == OrganizationMembership.Role.ADMIN

    # Profile page should display the organisation name
    profile = client.get(reverse("core:profile"))
    assert profile.status_code == 200
    html = profile.content.decode("utf-8")
    assert "Your organisation" in html
    assert "Acme Health" in html


@pytest.mark.django_db
def test_signup_as_simple_user(client):
    """Test that signing up as a simple user doesn't create an organization."""
    email = "simpleuser@example.com"
    password = TEST_PASSWORD

    resp = client.post(
        reverse("core:signup"),
        data={
            "email": email,
            "password1": password,
            "password2": password,
            "account_type": "simple",
        },
        follow=True,
    )

    assert resp.status_code == 200

    User = get_user_model()
    user = User.objects.get(email=email)

    # No organization should be created
    assert Organization.objects.filter(owner=user).count() == 0
    assert OrganizationMembership.objects.filter(user=user).count() == 0


@pytest.mark.django_db
def test_multiple_users_can_create_orgs_with_same_name(client):
    """
    Test that multiple users can create organizations with the same name.
    This is allowed because organizations are scoped by owner, not globally unique.
    Each user owns their own separate organization instance.
    """
    password = TEST_PASSWORD
    org_name = "Acme Health"

    # First user creates an org
    client.post(
        reverse("core:signup"),
        data={
            "email": "user1@example.com",
            "password1": password,
            "password2": password,
            "account_type": "org",
            "org_name": org_name,
        },
    )

    # Log out first user
    client.logout()

    # Second user creates an org with the same name
    resp = client.post(
        reverse("core:signup"),
        data={
            "email": "user2@example.com",
            "password1": password,
            "password2": password,
            "account_type": "org",
            "org_name": org_name,
        },
        follow=True,
    )

    # Should succeed
    assert resp.status_code == 200

    # Both organizations should exist
    User = get_user_model()
    user1 = User.objects.get(email="user1@example.com")
    user2 = User.objects.get(email="user2@example.com")

    org1 = Organization.objects.get(owner=user1)
    org2 = Organization.objects.get(owner=user2)

    # Same name but different instances
    assert org1.name == org_name
    assert org2.name == org_name
    assert org1.id != org2.id

    # Each user is admin of their own org only
    assert OrganizationMembership.objects.filter(
        user=user1, organization=org1, role=OrganizationMembership.Role.ADMIN
    ).exists()
    assert OrganizationMembership.objects.filter(
        user=user2, organization=org2, role=OrganizationMembership.Role.ADMIN
    ).exists()

    # user1 should NOT be a member of user2's org
    assert not OrganizationMembership.objects.filter(
        user=user1, organization=org2
    ).exists()
    # user2 should NOT be a member of user1's org
    assert not OrganizationMembership.objects.filter(
        user=user2, organization=org1
    ).exists()


@pytest.mark.django_db
def test_user_cannot_upgrade_to_admin_by_creating_org_with_existing_name(client):
    """
    Security test: A user cannot gain admin access to someone else's organization
    by creating a new organization with the same name. Each org is separate.
    """
    password = TEST_PASSWORD
    org_name = "Existing Corp"

    User = get_user_model()

    # Create first user with an organization
    user1 = User.objects.create_user(
        username="owner@example.com", email="owner@example.com", password=password
    )
    org1 = Organization.objects.create(name=org_name, owner=user1)
    OrganizationMembership.objects.create(
        organization=org1, user=user1, role=OrganizationMembership.Role.ADMIN
    )

    # Malicious user tries to create org with same name
    resp = client.post(
        reverse("core:signup"),
        data={
            "email": "attacker@example.com",
            "password1": password,
            "password2": password,
            "account_type": "org",
            "org_name": org_name,  # Same name as existing org
        },
        follow=True,
    )

    assert resp.status_code == 200

    attacker = User.objects.get(email="attacker@example.com")

    # Attacker should have their own separate organization
    attacker_org = Organization.objects.get(owner=attacker)
    assert attacker_org.name == org_name
    assert attacker_org.id != org1.id  # Different org instance

    # Attacker should be admin of their own org
    assert OrganizationMembership.objects.filter(
        user=attacker, organization=attacker_org, role=OrganizationMembership.Role.ADMIN
    ).exists()

    # Attacker should NOT have any access to the original organization
    assert not OrganizationMembership.objects.filter(
        user=attacker, organization=org1
    ).exists()

    # Original owner should still only be admin of their own org
    assert OrganizationMembership.objects.filter(
        user=user1, organization=org1
    ).count() == 1
    assert not OrganizationMembership.objects.filter(
        user=user1, organization=attacker_org
    ).exists()


@pytest.mark.django_db
def test_signup_with_duplicate_email_fails(client):
    """Test that signing up with an email that already exists fails."""
    email = "existing@example.com"
    password = TEST_PASSWORD

    User = get_user_model()
    User.objects.create_user(username=email, email=email, password=password)

    # Try to sign up again with same email
    resp = client.post(
        reverse("core:signup"),
        data={
            "email": email,
            "password1": password,
            "password2": password,
            "account_type": "simple",
        },
    )

    # Should show form with error, not redirect
    assert resp.status_code == 200
    assert b"already exists" in resp.content or b"already" in resp.content.lower()

    # Should still only be one user
    assert User.objects.filter(email=email).count() == 1


@pytest.mark.django_db
def test_org_name_defaults_to_username_when_empty(client):
    """Test that organization name defaults to username when not provided."""
    email = "testuser@example.com"
    password = TEST_PASSWORD

    resp = client.post(
        reverse("core:signup"),
        data={
            "email": email,
            "password1": password,
            "password2": password,
            "account_type": "org",
            "org_name": "",  # Empty org name
        },
        follow=True,
    )

    assert resp.status_code == 200

    User = get_user_model()
    user = User.objects.get(email=email)
    org = Organization.objects.get(owner=user)

    # Should use default: "{username}'s Organisation"
    assert org.name == "testuser@example.com's Organisation"
