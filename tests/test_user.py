import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from census_app.surveys.models import Organization, OrganizationMembership


@pytest.mark.django_db
def test_signup_as_org_creates_org_and_shows_on_profile(client):
    email = "orgowner@example.com"
    password = "Passw0rd!Passw0rd!"

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
