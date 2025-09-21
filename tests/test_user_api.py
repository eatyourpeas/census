import json
import pytest
from django.contrib.auth import get_user_model
from census_app.surveys.models import Organization, OrganizationMembership, Survey, SurveyMembership


User = get_user_model()


@pytest.mark.django_db
class TestUserAPI:
    def auth(self, client, username, password):
        r = client.post(
            "/api/token",
            data=json.dumps({"username": username, "password": password}),
            content_type="application/json",
        )
        assert r.status_code == 200
        return {"HTTP_AUTHORIZATION": f"Bearer {r.json()['access']}"}

    def test_org_admin_can_manage_org_memberships(self, client):
        admin = User.objects.create_user(username="adminx", password="Passw0rd-Adminx!")
        u2 = User.objects.create_user(username="u2", password="Passw0rd-u2!")
        org = Organization.objects.create(name="OrgAPI", owner=admin)
        OrganizationMembership.objects.create(organization=org, user=admin, role=OrganizationMembership.Role.ADMIN)
        hdrs = self.auth(client, "adminx", "Passw0rd-Adminx!")

        # create membership
        r = client.post(
            "/api/org-memberships/",
            data=json.dumps({"organization": org.id, "user": u2.id, "role": "creator"}),
            content_type="application/json",
            **hdrs,
        )
        assert r.status_code in (201, 200)

        # list shows it
        r = client.get("/api/org-memberships/", **hdrs)
        assert any(m["user"] == u2.id for m in r.json())

    def test_non_admin_cannot_manage_org_memberships(self, client):
        owner = User.objects.create_user(username="ownery", password="Passw0rd-Ownery!")
        other = User.objects.create_user(username="othery", password="Passw0rd-Othery!")
        org = Organization.objects.create(name="OrgAPI2", owner=owner)
        hdrs = self.auth(client, "othery", "Passw0rd-Othery!")
        r = client.post(
            "/api/org-memberships/",
            data=json.dumps({"organization": org.id, "user": owner.id, "role": "admin"}),
            content_type="application/json",
            **hdrs,
        )
        assert r.status_code in (403, 401)

    def test_survey_creator_can_manage_survey_memberships(self, client):
        creator = User.objects.create_user(username="creatorx", password="Passw0rd-Creatorx!")
        viewer = User.objects.create_user(username="viewerx", password="Passw0rd-Viewerx!")
        org = Organization.objects.create(name="OrgAPI3", owner=creator)
        OrganizationMembership.objects.create(organization=org, user=creator, role=OrganizationMembership.Role.CREATOR)
        survey = Survey.objects.create(owner=creator, organization=org, name="SS", slug="ss")
        hdrs = self.auth(client, "creatorx", "Passw0rd-Creatorx!")

        r = client.post(
            "/api/survey-memberships/",
            data=json.dumps({"survey": survey.id, "user": viewer.id, "role": "viewer"}),
            content_type="application/json",
            **hdrs,
        )
        assert r.status_code in (201, 200)
        assert SurveyMembership.objects.filter(survey=survey, user=viewer).exists()

    def test_viewer_cannot_manage_survey_memberships(self, client):
        owner = User.objects.create_user(username="ownerz", password="Passw0rd-Ownerz!")
        viewer = User.objects.create_user(username="viewerzz", password="Passw0rd-Viewerzz!")
        org = Organization.objects.create(name="OrgAPI4", owner=owner)
        survey = Survey.objects.create(owner=owner, organization=org, name="SZ", slug="sz")
        SurveyMembership.objects.create(survey=survey, user=viewer, role=SurveyMembership.Role.VIEWER)
        hdrs = self.auth(client, "viewerzz", "Passw0rd-Viewerzz!")
        r = client.post(
            "/api/survey-memberships/",
            data=json.dumps({"survey": survey.id, "user": owner.id, "role": "viewer"}),
            content_type="application/json",
            **hdrs,
        )
        assert r.status_code in (403, 401)

    def test_org_admin_can_create_user_in_org(self, client):
        admin = User.objects.create_user(username="adminc", password="Passw0rd-Adminc!")
        org = Organization.objects.create(name="OrgAPI5", owner=admin)
        OrganizationMembership.objects.create(organization=org, user=admin, role=OrganizationMembership.Role.ADMIN)
        hdrs = self.auth(client, "adminc", "Passw0rd-Adminc!")
        r = client.post(
            f"/api/scoped-users/org/{org.id}/create/",
            data=json.dumps({"username": "neworguser", "password": "Passw0rd-New!"}),
            content_type="application/json",
            **hdrs,
        )
        assert r.status_code in (200, 201)
        assert User.objects.filter(username="neworguser").exists()

    def test_creator_can_create_user_in_survey(self, client):
        creator = User.objects.create_user(username="creatorc", password="Passw0rd-Creatorc!")
        org = Organization.objects.create(name="OrgAPI6", owner=creator)
        OrganizationMembership.objects.create(organization=org, user=creator, role=OrganizationMembership.Role.CREATOR)
        survey = Survey.objects.create(owner=creator, organization=org, name="SC", slug="sc")
        hdrs = self.auth(client, "creatorc", "Passw0rd-Creatorc!")
        r = client.post(
            f"/api/scoped-users/survey/{survey.id}/create/",
            data=json.dumps({"username": "newsurveyuser", "password": "Passw0rd-New!"}),
            content_type="application/json",
            **hdrs,
        )
        assert r.status_code in (200, 201)
        assert User.objects.filter(username="newsurveyuser").exists()

    def test_viewer_cannot_create_user_in_survey(self, client):
        owner = User.objects.create_user(username="owneru", password="Passw0rd-Owneru!")
        viewer = User.objects.create_user(username="vieweru", password="Passw0rd-Vieweru!")
        org = Organization.objects.create(name="OrgAPI7", owner=owner)
        survey = Survey.objects.create(owner=owner, organization=org, name="SV", slug="sv")
        SurveyMembership.objects.create(survey=survey, user=viewer, role=SurveyMembership.Role.VIEWER)
        hdrs = self.auth(client, "vieweru", "Passw0rd-Vieweru!")
        r = client.post(
            f"/api/scoped-users/survey/{survey.id}/create/",
            data=json.dumps({"username": "baduser", "password": "Passw0rd-Bad!"}),
            content_type="application/json",
            **hdrs,
        )
        assert r.status_code in (403, 401)