import pytest


@pytest.mark.django_db
def test_openapi_schema_json(client):
    url = "/api/schema?format=openapi-json"
    resp = client.get(url)
    assert resp.status_code == 200
    data = resp.json()
    # Minimal OpenAPI shape checks
    assert "openapi" in data and isinstance(data["openapi"], str)
    assert data["openapi"].startswith("3.")
    assert "info" in data and isinstance(data["info"], dict)
    assert "title" in data["info"]
    assert "paths" in data and isinstance(data["paths"], dict)
