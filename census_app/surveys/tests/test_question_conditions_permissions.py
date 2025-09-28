from __future__ import annotations

from django.contrib.auth.models import User
from django.urls import reverse
import pytest

from census_app.surveys.models import (
    Organization,
    OrganizationMembership,
    QuestionGroup,
    Survey,
    SurveyMembership,
    SurveyQuestion,
    SurveyQuestionCondition,
)


@pytest.fixture
def survey_bundle(db):
    owner = User.objects.create_user(username="owner", password="x")
    org_admin = User.objects.create_user(username="org-admin", password="x")
    collaborator = User.objects.create_user(username="collaborator", password="x")
    viewer = User.objects.create_user(username="viewer", password="x")
    outsider = User.objects.create_user(username="outsider", password="x")

    org = Organization.objects.create(name="Org", owner=owner)
    OrganizationMembership.objects.create(
        organization=org, user=owner, role=OrganizationMembership.Role.ADMIN
    )
    OrganizationMembership.objects.create(
        organization=org, user=org_admin, role=OrganizationMembership.Role.ADMIN
    )

    survey = Survey.objects.create(
        owner=owner,
        organization=org,
        name="Conditional",
        slug="conditional",
    )

    group = QuestionGroup.objects.create(name="Main", owner=owner)
    survey.question_groups.add(group)

    question = SurveyQuestion.objects.create(
        survey=survey,
        group=group,
        text="Do you smoke?",
        type=SurveyQuestion.Types.YESNO,
        options=[],
        required=False,
        order=1,
    )

    follow_up = SurveyQuestion.objects.create(
        survey=survey,
        group=group,
        text="How many per day?",
        type=SurveyQuestion.Types.TEXT,
        options=[{"type": "text", "format": "free"}],
        required=False,
        order=2,
    )

    SurveyMembership.objects.create(
        survey=survey,
        user=collaborator,
        role=SurveyMembership.Role.CREATOR,
    )
    SurveyMembership.objects.create(
        survey=survey,
        user=viewer,
        role=SurveyMembership.Role.VIEWER,
    )

    return {
        "survey": survey,
        "question": question,
        "follow_up": follow_up,
        "group": group,
        "owner": owner,
        "org_admin": org_admin,
        "collaborator": collaborator,
        "viewer": viewer,
        "outsider": outsider,
    }


@pytest.mark.django_db
def test_condition_create_requires_login(client, survey_bundle):
    survey = survey_bundle["survey"]
    question = survey_bundle["question"]
    follow_up = survey_bundle["follow_up"]
    url = reverse(
        "surveys:builder_question_condition_create",
        kwargs={"slug": survey.slug, "qid": question.id},
    )
    initial = SurveyQuestionCondition.objects.count()
    response = client.post(
        url,
        {
            "operator": SurveyQuestionCondition.Operator.EQUALS,
            "value": "yes",
            "target_question": follow_up.id,
            "action": SurveyQuestionCondition.Action.JUMP_TO,
        },
    )
    assert response.status_code in (302, 401)
    assert SurveyQuestionCondition.objects.count() == initial


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("user_key", "expected_status"),
    [
        ("owner", 200),
        ("org_admin", 200),
        ("collaborator", 200),
        ("viewer", 403),
        ("outsider", 403),
    ],
)
def test_condition_create_permission_matrix(client, survey_bundle, user_key, expected_status):
    survey = survey_bundle["survey"]
    question = survey_bundle["question"]
    follow_up = survey_bundle["follow_up"]
    user = survey_bundle[user_key]

    client.force_login(user)
    url = reverse(
        "surveys:builder_question_condition_create",
        kwargs={"slug": survey.slug, "qid": question.id},
    )
    response = client.post(
        url,
        {
            "operator": SurveyQuestionCondition.Operator.EQUALS,
            "value": "yes",
            "target_question": follow_up.id,
            "action": SurveyQuestionCondition.Action.JUMP_TO,
        },
    )

    assert response.status_code == expected_status
    if expected_status == 200:
        assert SurveyQuestionCondition.objects.filter(question=question).exists()
    else:
        assert not SurveyQuestionCondition.objects.filter(question=question).exists()


@pytest.fixture
def existing_condition(survey_bundle):
    condition = SurveyQuestionCondition.objects.create(
        question=survey_bundle["question"],
        operator=SurveyQuestionCondition.Operator.EQUALS,
        value="yes",
        target_question=survey_bundle["follow_up"],
        action=SurveyQuestionCondition.Action.JUMP_TO,
        order=0,
        description="Initial",
    )
    return condition


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("user_key", "expected_status", "new_value"),
    [
        ("owner", 200, "no"),
        ("org_admin", 200, "no"),
        ("collaborator", 200, "no"),
        ("viewer", 403, "maybe"),
        ("outsider", 403, "maybe"),
    ],
)
def test_condition_update_permission_matrix(
    client, survey_bundle, existing_condition, user_key, expected_status, new_value
):
    survey = survey_bundle["survey"]
    question = survey_bundle["question"]
    user = survey_bundle[user_key]
    condition = existing_condition

    client.force_login(user)
    url = reverse(
        "surveys:builder_question_condition_update",
        kwargs={
            "slug": survey.slug,
            "qid": question.id,
            "cid": condition.id,
        },
    )
    response = client.post(url, {"value": new_value})
    assert response.status_code == expected_status

    condition.refresh_from_db()
    if expected_status == 200:
        assert condition.value == new_value
    else:
        assert condition.value == "yes"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("user_key", "expected_status"),
    [
        ("owner", 200),
        ("org_admin", 200),
        ("collaborator", 200),
        ("viewer", 403),
        ("outsider", 403),
    ],
)
def test_condition_delete_permission_matrix(
    client, survey_bundle, user_key, expected_status
):
    survey = survey_bundle["survey"]
    question = survey_bundle["question"]
    follow_up = survey_bundle["follow_up"]
    user = survey_bundle[user_key]

    condition = SurveyQuestionCondition.objects.create(
        question=question,
        operator=SurveyQuestionCondition.Operator.EQUALS,
        value="yes",
        target_question=follow_up,
        action=SurveyQuestionCondition.Action.JUMP_TO,
        order=0,
    )

    client.force_login(user)
    url = reverse(
        "surveys:builder_question_condition_delete",
        kwargs={
            "slug": survey.slug,
            "qid": question.id,
            "cid": condition.id,
        },
    )
    response = client.post(url)
    assert response.status_code == expected_status

    exists = SurveyQuestionCondition.objects.filter(id=condition.id).exists()
    if expected_status == 200:
        assert not exists
    else:
        assert exists
