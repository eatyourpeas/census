import pytest


@pytest.mark.django_db
def test_swagger_ui_page_renders(client):
    resp = client.get("/api/docs")
    assert resp.status_code == 200
    # Verify a key marker from the template to avoid brittle CDN/script checks
    assert b"API Explorer" in resp.content


@pytest.mark.django_db
def test_redoc_page_renders(client):
    resp = client.get("/api/redoc")
    assert resp.status_code == 200
    assert b"API Reference (ReDoc)" in resp.content
