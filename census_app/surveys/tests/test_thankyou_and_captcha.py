from django.urls import reverse
import pytest

from census_app.surveys.models import Survey


@pytest.mark.django_db
def test_thank_you_route(client, settings, django_user_model):
    user = django_user_model.objects.create_user(username="u", password="p")
    s = Survey.objects.create(
        owner=user,
        name="S",
        slug="s",
        status=Survey.Status.PUBLISHED,
        visibility=Survey.Visibility.PUBLIC,
    )
    resp = client.get(reverse("surveys:thank_you", kwargs={"slug": s.slug}))
    assert resp.status_code == 200
    assert b"Thank you" in resp.content


@pytest.mark.django_db
def test_captcha_required_blocks_without_token(client, settings, django_user_model):
    # Configure hCaptcha secret to force server-side check
    settings.HCAPTCHA_SECRET = "dummy"
    user = django_user_model.objects.create_user(username="u2", password="p")
    s = Survey.objects.create(
        owner=user,
        name="S2",
        slug="s2",
        status=Survey.Status.PUBLISHED,
        visibility=Survey.Visibility.PUBLIC,
        captcha_required=True,
    )
    # POST without h-captcha-response should be rejected and redirect back
    resp = client.post(reverse("surveys:take", kwargs={"slug": s.slug}), data={})
    assert resp.status_code in (302,)
