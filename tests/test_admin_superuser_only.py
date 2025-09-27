from django.contrib.auth.models import User
from django.urls import reverse
import pytest


@pytest.mark.django_db
class TestAdminSuperuserOnly:
    def test_staff_but_not_superuser_blocked(self, client):
        user = User.objects.create_user(
            username="staff", email="s@example.com", password="StrongPass!234"
        )
        user.is_staff = True
        user.is_superuser = False
        user.save()
        client.login(username="staff", password="StrongPass!234")
        resp = client.get(reverse("admin:index"))
        assert resp.status_code in (302, 403)

    def test_superuser_allowed(self, client):
        User.objects.create_superuser("root", "root@example.com", "StrongPass!234")
        client.login(username="root", password="StrongPass!234")
        resp = client.get(reverse("admin:index"))
        assert resp.status_code == 200
