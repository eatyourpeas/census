from __future__ import annotations

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from census_app.surveys.models import Organization, QuestionGroup, Survey


@pytest.mark.django_db
def test_groups_page_renders_with_counts(client):
    # Setup org, survey, owner
    owner = User.objects.create_user(username="owner", password="x")
    org = Organization.objects.create(name="Org", owner=owner)
    survey = Survey.objects.create(owner=owner, organization=org, name="S", slug="s")
    # Create groups and attach questions to count
    g1 = QuestionGroup.objects.create(name="G1", owner=owner)
    g2 = QuestionGroup.objects.create(name="G2", owner=owner)
    survey.question_groups.add(g1, g2)
    # Create minimal questions linked to survey and groups
    from census_app.surveys.models import SurveyQuestion

    SurveyQuestion.objects.create(
        survey=survey, group=g1, text="Q1", type=SurveyQuestion.Types.TEXT
    )
    SurveyQuestion.objects.create(
        survey=survey, group=g1, text="Q2", type=SurveyQuestion.Types.TEXT
    )
    SurveyQuestion.objects.create(
        survey=survey, group=g2, text="Q3", type=SurveyQuestion.Types.TEXT
    )

    # Owner should see the groups page with counts 2 and 1
    client.force_login(owner)
    res = client.get(reverse("surveys:groups", kwargs={"slug": survey.slug}))
    assert res.status_code == 200
    html = res.content.decode()
    assert "2 question" in html
    assert "1 question" in html
    # Ensure drag handle present for editor
    assert "drag-handle" in html
