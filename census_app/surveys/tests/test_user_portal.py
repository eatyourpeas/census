import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from census_app.surveys.models import Organization, OrganizationMembership, Survey, SurveyMembership


User = get_user_model()
TEST_PASSWORD = "test-pass"


@pytest.mark.django_db
def test_org_admin_can_access_org_users(client):
    admin = User.objects.create_user(username="admin1", password=TEST_PASSWORD)
    org = Organization.objects.create(name="OrgX", owner=admin)
    OrganizationMembership.objects.create(organization=org, user=admin, role=OrganizationMembership.Role.ADMIN)
    client.login(username="admin1", password=TEST_PASSWORD)
    resp = client.get(reverse("surveys:org_users", args=[org.id]))
    assert resp.status_code == 200


@pytest.mark.django_db
def test_non_admin_cannot_access_org_users(client):
    owner = User.objects.create_user(username="owner1", password=TEST_PASSWORD)
    other = User.objects.create_user(username="other", password=TEST_PASSWORD)
    org = Organization.objects.create(name="OrgY", owner=owner)
    client.login(username="other", password=TEST_PASSWORD)
    resp = client.get(reverse("surveys:org_users", args=[org.id]))
    assert resp.status_code in (302, 404)


@pytest.mark.django_db
def test_survey_creator_can_manage_survey_users(client):
    creator = User.objects.create_user(username="creator1", password=TEST_PASSWORD)
    org = Organization.objects.create(name="OrgZ", owner=creator)
    OrganizationMembership.objects.create(organization=org, user=creator, role=OrganizationMembership.Role.CREATOR)
    survey = Survey.objects.create(owner=creator, organization=org, name="S", slug="s")

    client.login(username="creator1", password=TEST_PASSWORD)
    url = reverse("surveys:survey_users", args=[survey.slug])
    resp = client.get(url)
    assert resp.status_code == 200

    # Add a viewer
    viewer = User.objects.create_user(username="viewer1", password=TEST_PASSWORD)
    resp = client.post(url, data={"action": "add", "user_id": viewer.id, "role": "viewer"})
    assert resp.status_code in (302, 200)
    assert SurveyMembership.objects.filter(survey=survey, user=viewer, role=SurveyMembership.Role.VIEWER).exists()


@pytest.mark.django_db
def test_viewer_cannot_manage_survey_users(client):
    owner = User.objects.create_user(username="owner2", password=TEST_PASSWORD)
    viewer = User.objects.create_user(username="viewer2", password=TEST_PASSWORD)
    org = Organization.objects.create(name="OrgA", owner=owner)
    survey = Survey.objects.create(owner=owner, organization=org, name="S2", slug="s2")
    SurveyMembership.objects.create(survey=survey, user=viewer, role=SurveyMembership.Role.VIEWER)
    client.login(username="viewer2", password=TEST_PASSWORD)
    url = reverse("surveys:survey_users", args=[survey.slug])
    resp = client.post(url, data={"action": "add", "user_id": owner.id, "role": "viewer"})
    assert resp.status_code == 403