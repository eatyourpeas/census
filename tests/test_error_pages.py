"""Test error page templates."""

import pytest


@pytest.mark.django_db
def test_403_error_page(client):
    """Test that 403 error page renders with styling."""
    # Access a survey the user doesn't have permission to view
    from census_app.surveys.models import Organization, Survey
    from django.contrib.auth import get_user_model

    User = get_user_model()
    owner = User.objects.create_user(username="owner", password="pass")
    org = Organization.objects.create(name="Test Org", owner=owner)
    survey = Survey.objects.create(
        owner=owner, organization=org, name="Private Survey", slug="private"
    )

    # Try to access as different user without permission
    other_user = User.objects.create_user(username="other", password="pass")
    client.force_login(other_user)

    resp = client.get(f"/surveys/{survey.slug}/preview/")
    assert resp.status_code == 403
    assert b"Access Denied" in resp.content
    assert b"403" in resp.content


@pytest.mark.django_db
def test_error_templates_exist():
    """Test that all error templates exist and can be loaded."""
    from django.template.loader import get_template

    templates = ["403.html", "404.html", "405.html", "500.html", "403_lockout.html"]

    for template_name in templates:
        # Just verify templates can be loaded without syntax errors
        template = get_template(template_name)
        assert template is not None
