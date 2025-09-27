from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse
import pytest


@pytest.mark.django_db
def test_admin_branding_header_for_superuser(client):
    # Create superuser and login
    User.objects.create_superuser(
        username="brandadmin", email="brandadmin@example.com", password="StrongPass!234"
    )
    assert client.login(username="brandadmin", password="StrongPass!234")

    # Hit admin index
    resp = client.get(reverse("admin:index"))
    assert resp.status_code == 200

    # Validate branding appears without relying on contiguous text (markup may split spans)
    content = resp.content.decode("utf-8", errors="ignore")
    brand_title = getattr(settings, "BRAND_TITLE", "Census")
    # 1) Page contains brand title somewhere
    assert brand_title in content
    # 2) Page contains the word Admin/admin somewhere (header span or title tag)
    assert (" Admin" in content) or (" admin" in content)
    # 3) Site header element exists
    assert 'id="site-name"' in content
