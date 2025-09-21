from __future__ import annotations

import pytest
from django.urls import reverse
from django.contrib.auth.models import User

from census_app.surveys.models import Organization, OrganizationMembership, Survey, QuestionGroup, SurveyMembership


@pytest.fixture
@pytest.mark.django_db
def users(db):
    owner = User.objects.create_user(username="owner", password="x")
    org_admin = User.objects.create_user(username="orgadmin", password="x")
    viewer = User.objects.create_user(username="viewer", password="x")
    outsider = User.objects.create_user(username="outsider", password="x")
    return owner, org_admin, viewer, outsider


@pytest.fixture
@pytest.mark.django_db
def org(db, users):
    owner, org_admin, viewer, outsider = users
    org = Organization.objects.create(name="Org", owner=owner)
    OrganizationMembership.objects.create(organization=org, user=org_admin, role=OrganizationMembership.Role.ADMIN)
    return org


@pytest.fixture
@pytest.mark.django_db
def survey_with_groups(db, users, org):
    owner, org_admin, viewer, outsider = users
    survey = Survey.objects.create(owner=owner, organization=org, name="My Survey", slug="mysurvey")
    # Assign viewer to survey as VIEWER role to ensure cannot edit
    SurveyMembership.objects.create(user=viewer, survey=survey, role=SurveyMembership.Role.VIEWER)
    g1 = QuestionGroup.objects.create(name="G1", owner=owner)
    g2 = QuestionGroup.objects.create(name="G2", owner=owner)
    g3 = QuestionGroup.objects.create(name="G3", owner=owner)
    survey.question_groups.add(g1, g2, g3)
    return survey, [g1, g2, g3]


def _post_order(client, survey, order_ids):
    url = reverse("surveys:survey_groups_reorder", kwargs={"slug": survey.slug})
    return client.post(url, data={"order": ",".join(str(i) for i in order_ids)})


@pytest.mark.django_db
def test_anonymous_cannot_reorder(client, survey_with_groups):
    survey, groups = survey_with_groups
    res = _post_order(client, survey, [g.id for g in groups])
    # login_required redirects anonymous
    assert res.status_code in (302, 401, 403)


@pytest.mark.django_db
def test_outsider_cannot_reorder(client, users, survey_with_groups):
    owner, org_admin, viewer, outsider = users
    survey, groups = survey_with_groups
    client.force_login(outsider)
    res = _post_order(client, survey, [g.id for g in groups])
    assert res.status_code == 403


@pytest.mark.django_db
def test_viewer_cannot_reorder(client, users, survey_with_groups):
    owner, org_admin, viewer, outsider = users
    survey, groups = survey_with_groups
    client.force_login(viewer)
    res = _post_order(client, survey, [g.id for g in groups])
    assert res.status_code == 403


@pytest.mark.django_db
def test_owner_can_reorder_and_persists(client, users, survey_with_groups):
    owner, org_admin, viewer, outsider = users
    survey, groups = survey_with_groups
    client.force_login(owner)
    new_order = [groups[2].id, groups[0].id, groups[1].id]
    res = _post_order(client, survey, new_order)
    # View redirects back to groups on success
    assert res.status_code in (302, 200)
    survey.refresh_from_db()
    assert (survey.style or {}).get("group_order") == new_order


@pytest.mark.django_db
def test_org_admin_can_reorder(client, users, survey_with_groups, org):
    owner, org_admin, viewer, outsider = users
    survey, groups = survey_with_groups
    client.force_login(org_admin)
    new_order = [groups[1].id, groups[2].id, groups[0].id]
    res = _post_order(client, survey, new_order)
    assert res.status_code in (302, 200)
    survey.refresh_from_db()
    assert (survey.style or {}).get("group_order") == new_order


@pytest.mark.django_db
def test_invalid_ids_are_ignored(client, users, survey_with_groups):
    owner, org_admin, viewer, outsider = users
    survey, groups = survey_with_groups
    client.force_login(owner)
    bogus = 999999
    res = _post_order(client, survey, [bogus, groups[1].id, groups[0].id])
    assert res.status_code in (302, 200)
    survey.refresh_from_db()
    # Only valid ids are stored, and order preserved for valid subset
    assert (survey.style or {}).get("group_order") == [groups[1].id, groups[0].id]
