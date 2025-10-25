from django.urls import reverse
import pytest

from census_app.surveys.models import QuestionGroup, Survey, SurveyAccessToken


@pytest.mark.django_db
def test_authenticated_required_when_patient_data(client, django_user_model):
    owner = django_user_model.objects.create_user(username="owner", password="p")
    participant = django_user_model.objects.create_user(username="participant", password="p")
    s = Survey.objects.create(owner=owner, name="S", slug="s")
    # Attach a patient details group with fields
    g = QuestionGroup.objects.create(
        owner=owner,
        name="Patient details",
        schema={"template": "patient_details_encrypted", "fields": ["first_name"]},
    )
    s.question_groups.add(g)

    s.status = Survey.Status.PUBLISHED
    s.visibility = Survey.Visibility.PUBLIC
    s.no_patient_data_ack = False
    s.save()

    # Login as participant (not owner)
    client.login(username="participant", password="p")
    # Public take should 404 due to patient data and no ack
    resp = client.get(reverse("surveys:take", kwargs={"slug": s.slug}))
    assert resp.status_code == 404


@pytest.mark.django_db
def test_unlisted_link_flow(client, django_user_model):
    user = django_user_model.objects.create_user(username="u2", password="p")
    client.login(username="u2", password="p")
    s = Survey.objects.create(
        owner=user,
        name="S2",
        slug="s2",
        status=Survey.Status.PUBLISHED,
        visibility=Survey.Visibility.UNLISTED,
    )
    s.unlisted_key = "abc123"
    s.save()
    resp = client.get(
        reverse("surveys:take_unlisted", kwargs={"slug": s.slug, "key": s.unlisted_key})
    )
    assert resp.status_code in (200, 302)


@pytest.mark.django_db
def test_token_one_time_use(client, django_user_model):
    user = django_user_model.objects.create_user(username="u3", password="p")
    s = Survey.objects.create(
        owner=user,
        name="S3",
        slug="s3",
        status=Survey.Status.PUBLISHED,
        visibility=Survey.Visibility.TOKEN,
    )
    tok = SurveyAccessToken.objects.create(survey=s, token="tok123", created_by=user)

    # First GET loads
    resp = client.get(
        reverse("surveys:take_token", kwargs={"slug": s.slug, "token": tok.token})
    )
    assert resp.status_code in (200, 302)

    # Simulate a submit (no fields)
    resp = client.post(
        reverse("surveys:take_token", kwargs={"slug": s.slug, "token": tok.token}), {}
    )
    assert resp.status_code in (302,)

    tok.refresh_from_db()
    assert tok.used_at is not None

    # Second submit should redirect to closed page
    resp = client.post(
        reverse("surveys:take_token", kwargs={"slug": s.slug, "token": tok.token}), {}
    )
    assert resp.status_code == 302
    assert "/closed/" in resp.url
    assert "reason=token_used" in resp.url
