import json
from django.urls import reverse
from census_app.surveys.utils import encrypt_sensitive, decrypt_sensitive


def test_encrypt_roundtrip():
    key = b"secret-passphrase"
    data = {"name": "Alice", "dob": "2000-01-01"}
    blob = encrypt_sensitive(key, data)
    out = decrypt_sensitive(key, blob)
    assert out == data


def test_healthcheck(client):
    url = "/api/health"
    res = client.get(url)
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
