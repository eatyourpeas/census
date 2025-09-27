from django.contrib.auth.models import User
from django.urls import reverse
import pytest


@pytest.mark.django_db
class TestAdminAccess:
    def test_admin_requires_superuser(self, client):
        # Anonymous redirected to login (Django admin uses its own /admin/login/)
        resp = client.get(reverse("admin:index"))
        assert resp.status_code in (302, 301)
        assert ("/admin/login/" in resp.url) or (reverse("login") in resp.url)

        # Regular user cannot access admin index
        User.objects.create_user(
            username="u1", email="u1@example.com", password="StrongPass!234"
        )
        client.login(username="u1", password="StrongPass!234")
        resp2 = client.get(reverse("admin:index"))
        # Django returns 302 to login with next or 403 depending on settings; allow both
        assert resp2.status_code in (302, 403)

    def test_superuser_can_access_admin(self, client):
        User.objects.create_superuser(
            username="admin", email="admin@example.com", password="StrongPass!234"
        )
        client.login(username="admin", password="StrongPass!234")
        resp = client.get(reverse("admin:index"))
        assert resp.status_code == 200
        assert b"/admin/" in resp.content
