from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from census_app.surveys.models import Organization, OrganizationMembership, Survey


@pytest.fixture
def users(db):
    admin = User.objects.create_user(username="admin", password="x")
    creator = User.objects.create_user(username="creator", password="x")
    viewer = User.objects.create_user(username="viewer", password="x")
    outsider = User.objects.create_user(username="outsider", password="x")
    participant = User.objects.create_user(username="participant", password="x")
    return admin, creator, viewer, outsider, participant


@pytest.fixture
def org(db, users):
    admin, creator, viewer, outsider, participant = users
    org = Organization.objects.create(name="Org", owner=admin)
    OrganizationMembership.objects.create(organization=org, user=admin, role=OrganizationMembership.Role.ADMIN)
    OrganizationMembership.objects.create(organization=org, user=creator, role=OrganizationMembership.Role.CREATOR)
    OrganizationMembership.objects.create(organization=org, user=viewer, role=OrganizationMembership.Role.VIEWER)
    return org


@pytest.fixture
def surveys(db, org, users):
    admin, creator, viewer, outsider, participant = users
    s1 = Survey.objects.create(owner=creator, organization=org, name="S1", slug="s1")
    s2 = Survey.objects.create(owner=admin, organization=org, name="S2", slug="s2")
    return s1, s2


def login(client, user):
    client.force_login(user)


@pytest.mark.django_db
def test_creator_sees_only_own_surveys(client, users, org, surveys):
    admin, creator, viewer, outsider, participant = users
    s1, s2 = surveys
    login(client, creator)
    res = client.get(reverse("surveys:list"))
    assert res.status_code == 200
    names = {s.name for s in res.context["surveys"]}
    assert names == {"S1"}


@pytest.mark.django_db
def test_admin_sees_all_org_surveys(client, users, org, surveys):
    admin, creator, viewer, outsider, participant = users
    s1, s2 = surveys
    login(client, admin)
    res = client.get(reverse("surveys:list"))
    assert res.status_code == 200
    names = {s.name for s in res.context["surveys"]}
    assert names == {"S1", "S2"}


@pytest.mark.django_db
def test_viewer_sees_only_own_surveys(client, users, org, surveys):
    admin, creator, viewer, outsider, participant = users
    s1, s2 = surveys
    login(client, viewer)
    res = client.get(reverse("surveys:list"))
    assert res.status_code == 200
    names = {s.name for s in res.context["surveys"]}
    assert names == set()


@pytest.mark.django_db
def test_creator_cannot_edit_others_survey(client, users, org, surveys):
    admin, creator, viewer, outsider, participant = users
    s1, s2 = surveys
    login(client, creator)
    res = client.get(reverse("surveys:builder", kwargs={"slug": s2.slug}))
    assert res.status_code == 403


@pytest.mark.django_db
def test_admin_can_edit_any_in_org(client, users, org, surveys):
    admin, creator, viewer, outsider, participant = users
    s1, s2 = surveys
    login(client, admin)
    res = client.get(reverse("surveys:builder", kwargs={"slug": s1.slug}))
    assert res.status_code == 200


@pytest.mark.django_db
def test_participant_cannot_access_builder(client, users, org, surveys):
    admin, creator, viewer, outsider, participant = users
    s1, s2 = surveys
    # Simulate a participant (non-org) user
    login(client, participant)
    res = client.get(reverse("surveys:builder", kwargs={"slug": s1.slug}))
    assert res.status_code == 403


@pytest.mark.django_db
def test_public_detail_access_for_live_survey(client, users, org, surveys, settings):
    admin, creator, viewer, outsider, participant = users
    s1, s2 = surveys
    # Unauthenticated user can see detail if survey is live (default is live without date bounds)
    res = client.get(reverse("surveys:detail", kwargs={"slug": s1.slug}))
    assert res.status_code == 200


@pytest.mark.django_db
def test_preview_requires_permission(client, users, org, surveys):
    admin, creator, viewer, outsider, participant = users
    s1, s2 = surveys
    # Creator can preview their own
    login(client, creator)
    assert client.get(reverse("surveys:preview", kwargs={"slug": s1.slug})).status_code == 200
    # But not others
    assert client.get(reverse("surveys:preview", kwargs={"slug": s2.slug})).status_code == 403