import json

from django.contrib.auth import get_user_model
import pytest

from census_app.surveys.models import (
    Organization,
    OrganizationMembership,
    Survey,
    SurveyMembership,
)

User = get_user_model()
TEST_PASSWORD = "test-pass"


def auth_hdr(client, username: str, password: str) -> dict:
    resp = client.post(
        "/api/token",
        data=json.dumps({"username": username, "password": password}),
        content_type="application/json",
    )
    assert resp.status_code == 200, resp.content
    return {"HTTP_AUTHORIZATION": f"Bearer {resp.json()['access']}"}


@pytest.mark.django_db
def test_org_memberships_anonymous_blocked(client):
    resp = client.get("/api/org-memberships/")
    assert resp.status_code in (401, 403)


@pytest.mark.django_db
def test_org_memberships_non_admin_forbidden_on_mutations(client):
    admin = User.objects.create_user(username="adminx", password=TEST_PASSWORD)
    User.objects.create_user(username="userx", password=TEST_PASSWORD)  # nonadmin
    target = User.objects.create_user(username="targetx", password=TEST_PASSWORD)
    org = Organization.objects.create(name="OrgX", owner=admin)
    # Only admin membership
    OrganizationMembership.objects.create(
        organization=org, user=admin, role=OrganizationMembership.Role.ADMIN
    )

    # Non-admin cannot create/update/delete memberships
    hdrs = auth_hdr(client, "userx", TEST_PASSWORD)
    # Create
    resp = client.post(
        "/api/org-memberships/",
        data=json.dumps({"organization": org.id, "user": target.id, "role": "viewer"}),
        content_type="application/json",
        **hdrs,
    )
    assert resp.status_code == 403

    # Prepare an existing membership (viewer) to try update/delete
    mem = OrganizationMembership.objects.create(
        organization=org, user=target, role=OrganizationMembership.Role.VIEWER
    )
    # Update
    resp = client.patch(
        f"/api/org-memberships/{mem.id}/",
        data=json.dumps({"role": "admin"}),
        content_type="application/json",
        **hdrs,
    )
    assert resp.status_code in (403, 404)
    # Delete
    resp = client.delete(f"/api/org-memberships/{mem.id}/", **hdrs)
    assert resp.status_code in (403, 404)


@pytest.mark.django_db
def test_survey_memberships_anonymous_blocked(client):
    resp = client.get("/api/survey-memberships/")
    assert resp.status_code in (401, 403)


@pytest.mark.django_db
def test_survey_memberships_non_manager_forbidden_on_mutations(client):
    owner = User.objects.create_user(username="ownerx", password=TEST_PASSWORD)
    User.objects.create_user(username="otherx", password=TEST_PASSWORD)  # other
    target = User.objects.create_user(username="targy", password=TEST_PASSWORD)
    org = Organization.objects.create(name="OrgY", owner=owner)
    survey = Survey.objects.create(owner=owner, organization=org, name="Sx", slug="sx")

    hdrs = auth_hdr(client, "otherx", TEST_PASSWORD)
    # Create membership (should be forbidden)
    resp = client.post(
        "/api/survey-memberships/",
        data=json.dumps({"survey": survey.id, "user": target.id, "role": "viewer"}),
        content_type="application/json",
        **hdrs,
    )
    assert resp.status_code == 403

    # Prepare an existing membership to attempt update/delete
    mem = SurveyMembership.objects.create(
        survey=survey, user=target, role=SurveyMembership.Role.VIEWER
    )
    # Update
    resp = client.patch(
        f"/api/survey-memberships/{mem.id}/",
        data=json.dumps({"role": "creator"}),
        content_type="application/json",
        **hdrs,
    )
    assert resp.status_code in (403, 404)
    # Delete
    resp = client.delete(f"/api/survey-memberships/{mem.id}/", **hdrs)
    assert resp.status_code in (403, 404)


@pytest.mark.django_db
def test_scoped_user_create_org_permissions(client):
    admin = User.objects.create_user(username="adminz", password=TEST_PASSWORD)
    User.objects.create_user(username="plainz", password=TEST_PASSWORD)  # nonadmin
    org = Organization.objects.create(name="OrgZ", owner=admin)
    OrganizationMembership.objects.create(
        organization=org, user=admin, role=OrganizationMembership.Role.ADMIN
    )

    # anonymous 401
    resp = client.post(
        f"/api/scoped-users/org/{org.id}/create/",
        data=json.dumps({"username": "newu", "password": TEST_PASSWORD}),
        content_type="application/json",
    )
    assert resp.status_code in (401, 403)

    # non-admin 403
    hdrs = auth_hdr(client, "plainz", TEST_PASSWORD)
    resp = client.post(
        f"/api/scoped-users/org/{org.id}/create/",
        data=json.dumps({"username": "newu2", "password": TEST_PASSWORD}),
        content_type="application/json",
        **hdrs,
    )
    assert resp.status_code == 403

    # admin 200
    hdrs = auth_hdr(client, "adminz", TEST_PASSWORD)
    resp = client.post(
        f"/api/scoped-users/org/{org.id}/create/",
        data=json.dumps({"username": "newu3", "password": TEST_PASSWORD}),
        content_type="application/json",
        **hdrs,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_scoped_user_create_survey_permissions(client):
    owner = User.objects.create_user(username="ownera", password=TEST_PASSWORD)
    User.objects.create_user(username="othra", password=TEST_PASSWORD)  # other
    org = Organization.objects.create(name="OrgA1", owner=owner)
    survey = Survey.objects.create(owner=owner, organization=org, name="S1", slug="s1a")

    # anonymous 401
    resp = client.post(
        f"/api/scoped-users/survey/{survey.id}/create/",
        data=json.dumps({"username": "svnu", "password": TEST_PASSWORD}),
        content_type="application/json",
    )
    assert resp.status_code in (401, 403)

    # non-manager 403
    hdrs = auth_hdr(client, "othra", TEST_PASSWORD)
    resp = client.post(
        f"/api/scoped-users/survey/{survey.id}/create/",
        data=json.dumps({"username": "svnu2", "password": TEST_PASSWORD}),
        content_type="application/json",
        **hdrs,
    )
    assert resp.status_code == 403

    # owner 200
    hdrs = auth_hdr(client, "ownera", TEST_PASSWORD)
    resp = client.post(
        f"/api/scoped-users/survey/{survey.id}/create/",
        data=json.dumps({"username": "svnu3", "password": TEST_PASSWORD}),
        content_type="application/json",
        **hdrs,
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_healthcheck_public(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json().get("status") == "ok"
