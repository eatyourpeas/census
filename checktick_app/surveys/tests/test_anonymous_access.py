from __future__ import annotations

from django.urls import reverse
from django.utils import timezone
import pytest

from checktick_app.surveys.models import Organization, OrganizationMembership, Survey

TEST_PASSWORD = "test-pass"


@pytest.mark.django_db
def test_anon_sees_no_surveys_in_list(client):
    # Setup minimal data
    owner = Organization._meta.apps.get_model("auth", "User").objects.create_user(
        username="owner_anon", password=TEST_PASSWORD
    )
    org = Organization.objects.create(name="OrgAnon", owner=owner)
    OrganizationMembership.objects.create(
        organization=org, user=owner, role=OrganizationMembership.Role.ADMIN
    )
    Survey.objects.create(owner=owner, organization=org, name="S1", slug="s1")

    resp = client.get(reverse("surveys:list"))
    # login_required should redirect anonymous users away from SSR list
    assert resp.status_code in (302, 401, 403)


@pytest.mark.django_db
def test_anon_cannot_access_management_pages(client):
    owner = Organization._meta.apps.get_model("auth", "User").objects.create_user(
        username="owner_manage", password=TEST_PASSWORD
    )
    org = Organization.objects.create(name="OrgManage", owner=owner)
    OrganizationMembership.objects.create(
        organization=org, user=owner, role=OrganizationMembership.Role.ADMIN
    )
    survey = Survey.objects.create(owner=owner, organization=org, name="S2", slug="s2")

    # Management endpoints must redirect unauthenticated users to login
    urls = [
        reverse("surveys:dashboard", kwargs={"slug": survey.slug}),
        reverse("surveys:groups", kwargs={"slug": survey.slug}),
        reverse("surveys:groups", kwargs={"slug": survey.slug}),
        reverse("surveys:preview", kwargs={"slug": survey.slug}),
    ]
    for url in urls:
        resp = client.get(url)
        assert resp.status_code in (302, 401, 403)


@pytest.mark.django_db
def test_anon_cannot_view_non_live_survey_detail(client):
    owner = Organization._meta.apps.get_model("auth", "User").objects.create_user(
        username="owner_nonlive", password=TEST_PASSWORD
    )
    org = Organization.objects.create(name="OrgNonLive", owner=owner)
    OrganizationMembership.objects.create(
        organization=org, user=owner, role=OrganizationMembership.Role.ADMIN
    )
    # Make survey not live yet
    future = timezone.now() + timezone.timedelta(days=1)
    survey = Survey.objects.create(
        owner=owner, organization=org, name="S3", slug="s3", start_at=future
    )

    resp = client.get(reverse("surveys:detail", kwargs={"slug": survey.slug}))
    # All surveys require authentication (redirect/unauthorized/forbidden for anon)
    assert resp.status_code in (302, 401, 403)
