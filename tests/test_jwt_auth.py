import json
import pytest
from django.contrib.auth import get_user_model
from census_app.surveys.models import Organization, Survey


User = get_user_model()
TEST_PASSWORD = "test-pass"


@pytest.mark.django_db
class TestJWTEnforcement:
    def setup_data(self):
        owner = User.objects.create_user(username="owner2", password=TEST_PASSWORD)
        org = Organization.objects.create(name="Org-JWT", owner=owner)
        survey = Survey.objects.create(owner=owner, organization=org, name="Jwt S", slug="jwt-s")
        return owner, org, survey

    def get_auth_header(self, client, username: str, password: str) -> dict:
        resp = client.post(
            "/api/token",
            data=json.dumps({"username": username, "password": password}),
            content_type="application/json",
        )
        assert resp.status_code == 200, resp.content
        access = resp.json()["access"]
        return {"HTTP_AUTHORIZATION": f"Bearer {access}"}

    def test_missing_token_behaviour(self, client):
        _, _, survey = self.setup_data() # ower, org, survey

        # List: requires authentication (anonymous should be denied)
        resp = client.get("/api/surveys/")
        assert resp.status_code in (401, 403)

        # Detail GET without token: denied (401 or 403 depending on evaluation order)
        resp = client.get(f"/api/surveys/{survey.id}/")
        assert resp.status_code in (401, 403)

        # Create without token: unsafe method should be 401 (not authenticated)
        resp = client.post(
            "/api/surveys/",
            data=json.dumps({"name": "New", "slug": "jwt-new"}),
            content_type="application/json",
        )
        assert resp.status_code in (401, 403)

        # Update without token: unsafe method should be 401 (not authenticated)
        resp = client.patch(
            f"/api/surveys/{survey.id}/",
            data=json.dumps({"description": "update"}),
            content_type="application/json",
        )
        assert resp.status_code in (401, 403)

    def test_invalid_token_returns_401(self, client):
        _, _, survey = self.setup_data()
        invalid_hdrs = {"HTTP_AUTHORIZATION": "Bearer invalid.token.here"}

        # With an invalid token, authentication should fail hard with 401
        resp = client.get("/api/surveys/", **invalid_hdrs)
        assert resp.status_code == 401

        resp = client.get(f"/api/surveys/{survey.id}/", **invalid_hdrs)
        assert resp.status_code == 401

        resp = client.post(
            "/api/surveys/",
            data=json.dumps({"name": "New2", "slug": "jwt-new2"}),
            content_type="application/json",
            **invalid_hdrs,
        )
        assert resp.status_code == 401

        resp = client.patch(
            f"/api/surveys/{survey.id}/",
            data=json.dumps({"description": "update2"}),
            content_type="application/json",
            **invalid_hdrs,
        )
        assert resp.status_code == 401

    def test_refresh_flow(self, client):
        """Basic happy-path for JWT obtain and refresh."""
        User.objects.create_user(username="jwtuser", password=TEST_PASSWORD)

        # Obtain
        obtain = client.post(
            "/api/token",
            data=json.dumps({"username": "jwtuser", "password": TEST_PASSWORD}),
            content_type="application/json",
        )
        assert obtain.status_code == 200
        tokens = obtain.json()
        assert "access" in tokens and "refresh" in tokens

        # Use access
        hdrs = {"HTTP_AUTHORIZATION": f"Bearer {tokens['access']}"}
        resp = client.get("/api/surveys/", **hdrs)
        assert resp.status_code == 200

        # Refresh
        refresh = client.post(
            "/api/token/refresh",
            data=json.dumps({"refresh": tokens["refresh"]}),
            content_type="application/json",
        )
        assert refresh.status_code == 200
        new_access = refresh.json()["access"]
        hdrs2 = {"HTTP_AUTHORIZATION": f"Bearer {new_access}"}
        resp2 = client.get("/api/surveys/", **hdrs2)
        assert resp2.status_code == 200

    def test_token_wrong_credentials_returns_401(self, client):
        """Wrong password should yield 401 Unauthorized from /api/token."""
        User.objects.create_user(username="baduser", password=TEST_PASSWORD)
        resp = client.post(
            "/api/token",
            data=json.dumps({"username": "baduser", "password": "wrong-password"}),
            content_type="application/json",
        )
        assert resp.status_code == 401
