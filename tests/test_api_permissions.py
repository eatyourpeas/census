import json
import pytest
from django.contrib.auth import get_user_model
from census_app.surveys.models import Organization, OrganizationMembership, Survey


User = get_user_model()


@pytest.mark.django_db
class TestAPIPermissions:
    def get_auth_header(self, client, username: str, password: str) -> dict:
        resp = client.post(
            "/api/token",
            data=json.dumps({"username": username, "password": password}),
            content_type="application/json",
        )
        assert resp.status_code == 200, resp.content
        access = resp.json()["access"]
        return {"HTTP_AUTHORIZATION": f"Bearer {access}"}

    def setup_users(self):
        owner = User.objects.create_user(username="owner", password="passw0rd-Owner!")
        admin = User.objects.create_user(username="admin", password="passw0rd-Admin!")
        creator = User.objects.create_user(username="creator", password="passw0rd-Creator!")
        viewer = User.objects.create_user(username="viewer", password="passw0rd-Viewer!")
        anon = None
        return owner, admin, creator, viewer, anon

    def setup_data(self):
        owner, admin, creator, viewer, _ = self.setup_users()
        org = Organization.objects.create(name="Org1", owner=owner)
        OrganizationMembership.objects.create(organization=org, user=admin, role=OrganizationMembership.Role.ADMIN)
        OrganizationMembership.objects.create(organization=org, user=creator, role=OrganizationMembership.Role.CREATOR)
        OrganizationMembership.objects.create(organization=org, user=viewer, role=OrganizationMembership.Role.VIEWER)
        s1 = Survey.objects.create(owner=owner, organization=org, name="S1", slug="s1")
        s2 = Survey.objects.create(owner=creator, organization=org, name="S2", slug="s2")
        s3 = Survey.objects.create(owner=viewer, organization=org, name="S3", slug="s3")
        return owner, admin, creator, viewer, org, [s1, s2, s3]

    def test_list_visibility(self, client):
        owner, admin, creator, viewer, org, surveys = self.setup_data()
        url = "/api/surveys/"

        # owner sees own surveys only
        hdrs = self.get_auth_header(client, "owner", "passw0rd-Owner!")
        resp = client.get(url, **hdrs)
        assert resp.status_code == 200
        slugs = {s["slug"] for s in resp.json()}
        assert slugs == {"s1"}

        # admin sees all org surveys (s1,s2,s3)
        hdrs = self.get_auth_header(client, "admin", "passw0rd-Admin!")
        resp = client.get(url, **hdrs)
        assert resp.status_code == 200
        slugs = {s["slug"] for s in resp.json()}
        assert slugs == {"s1", "s2", "s3"}

        # creator sees only their own (s2)
        hdrs = self.get_auth_header(client, "creator", "passw0rd-Creator!")
        resp = client.get(url, **hdrs)
        assert resp.status_code == 200
        slugs = {s["slug"] for s in resp.json()}
        assert slugs == {"s2"}

        # viewer sees only their own (s3)
        hdrs = self.get_auth_header(client, "viewer", "passw0rd-Viewer!")
        resp = client.get(url, **hdrs)
        assert resp.status_code == 200
        slugs = {s["slug"] for s in resp.json()}
        assert slugs == {"s3"}

        # anonymous sees empty
        resp = client.get(url)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_retrieve_permissions(self, client):
        owner, admin, creator, viewer, org, surveys = self.setup_data()
        s1, s2, s3 = surveys
        url_s2 = f"/api/surveys/{s2.id}/"

        # owner of s1 cannot fetch s2 (not admin) -> explicit 403
        hdrs = self.get_auth_header(client, "owner", "passw0rd-Owner!")
        resp = client.get(url_s2, **hdrs)
        assert resp.status_code == 403

        # admin can fetch any org survey
        hdrs = self.get_auth_header(client, "admin", "passw0rd-Admin!")
        resp = client.get(url_s2, **hdrs)
        assert resp.status_code == 200

        # creator can fetch their own
        hdrs = self.get_auth_header(client, "creator", "passw0rd-Creator!")
        resp = client.get(url_s2, **hdrs)
        assert resp.status_code == 200

        # viewer cannot fetch creator's survey (not their own)
        hdrs = self.get_auth_header(client, "viewer", "passw0rd-Viewer!")
        resp = client.get(url_s2, **hdrs)
        assert resp.status_code == 403

    def test_update_forbidden_without_rights(self, client):
        owner, admin, creator, viewer, org, surveys = self.setup_data()
        s2 = surveys[1]
        url_s2 = f"/api/surveys/{s2.id}/"

        # creator can update own
        hdrs = self.get_auth_header(client, "creator", "passw0rd-Creator!")
        resp = client.patch(url_s2, data=json.dumps({"description": "x"}), content_type="application/json", **hdrs)
        assert resp.status_code in (200, 202)

        # viewer cannot update creator's
        hdrs = self.get_auth_header(client, "viewer", "passw0rd-Viewer!")
        resp = client.patch(url_s2, data=json.dumps({"description": "x2"}), content_type="application/json", **hdrs)
        assert resp.status_code == 403

        # admin can update creator's
        hdrs = self.get_auth_header(client, "admin", "passw0rd-Admin!")
        resp = client.patch(url_s2, data=json.dumps({"description": "x3"}), content_type="application/json", **hdrs)
        assert resp.status_code in (200, 202)

        # anonymous cannot update (401)
        resp = client.patch(url_s2, data=json.dumps({"description": "x4"}), content_type="application/json")
        assert resp.status_code in (401, 403)

    def test_seed_action_permissions(self, client):
        owner, admin, creator, viewer, org, surveys = self.setup_data()
        s2 = surveys[1]  # owned by creator
        url_seed = f"/api/surveys/{s2.id}/seed/"
        payload = [{"text": "Q1", "type": "text", "order": 1}]

        # admin can seed creator's survey
        hdrs = self.get_auth_header(client, "admin", "passw0rd-Admin!")
        resp = client.post(url_seed, data=json.dumps(payload), content_type="application/json", **hdrs)
        assert resp.status_code == 200

        # viewer cannot seed creator's survey
        hdrs = self.get_auth_header(client, "viewer", "passw0rd-Viewer!")
        resp = client.post(url_seed, data=json.dumps(payload), content_type="application/json", **hdrs)
        assert resp.status_code == 403

    def test_create_returns_one_time_key(self, client):
        User.objects.create_user(username="make", password="passw0rd-Make!")
        hdrs = self.get_auth_header(client, "make", "passw0rd-Make!")
        resp = client.post(
            "/api/surveys/",
            data=json.dumps({"name": "New", "slug": "new"}),
            content_type="application/json",
            **hdrs,
        )
        assert resp.status_code in (201, 200)
        body = resp.json()
        assert "one_time_key_b64" in body and isinstance(body["one_time_key_b64"], str) and len(body["one_time_key_b64"]) > 0
