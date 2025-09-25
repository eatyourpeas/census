from __future__ import annotations

from django.contrib.auth.models import User
from django.urls import reverse
import pytest

from census_app.surveys.models import (
    CollectionDefinition,
    CollectionItem,
    Organization,
    OrganizationMembership,
    QuestionGroup,
    Survey,
)


def _setup_survey_with_groups():
    owner = User.objects.create_user(username="owner", password="x")
    org = Organization.objects.create(name="Org", owner=owner)
    # Make owner an org admin explicitly (owner implies admin, but be explicit)
    OrganizationMembership.objects.create(
        organization=org, user=owner, role=OrganizationMembership.Role.ADMIN
    )
    survey = Survey.objects.create(owner=owner, organization=org, name="S", slug="s")
    g1 = QuestionGroup.objects.create(name="G1", owner=owner)
    g2 = QuestionGroup.objects.create(name="G2", owner=owner)
    survey.question_groups.add(g1, g2)
    return owner, org, survey, g1, g2


@pytest.mark.django_db
def test_repeat_create_permissions(client):
    owner, org, survey, g1, g2 = _setup_survey_with_groups()
    outsider = User.objects.create_user(username="outsider", password="x")

    url = reverse("surveys:survey_groups_repeat_create", kwargs={"slug": survey.slug})
    payload = {
        "name": "People",
        "min_count": 0,
        "max_count": "2",
        "group_ids": f"{g1.id},{g2.id}",
    }

    # Anonymous should redirect to login (or 403, depending on settings)
    res = client.post(url, data=payload)
    assert res.status_code in (302, 403)

    # Outsider logged in should be forbidden
    client.force_login(outsider)
    res2 = client.post(url, data=payload)
    assert res2.status_code == 403

    # Owner can create
    client.force_login(owner)
    res3 = client.post(url, data=payload, follow=True)
    assert res3.status_code in (200, 302)

    cd = CollectionDefinition.objects.filter(survey=survey, name="People").first()
    assert cd is not None
    assert cd.min_count == 0
    # max_count=2 should result in MANY cardinality
    assert cd.max_count == 2
    assert cd.cardinality == CollectionDefinition.Cardinality.MANY

    # Items created for g1 then g2 in order
    items = list(CollectionItem.objects.filter(collection=cd).order_by("order", "id"))
    assert len(items) == 2
    assert (
        items[0].item_type == CollectionItem.ItemType.GROUP
        and items[0].group_id == g1.id
        and items[0].order == 0
    )
    assert (
        items[1].item_type == CollectionItem.ItemType.GROUP
        and items[1].group_id == g2.id
        and items[1].order == 1
    )


@pytest.mark.django_db
def test_repeat_create_nested_under_parent(client):
    owner, org, survey, g1, g2 = _setup_survey_with_groups()
    client.force_login(owner)

    # First create a parent repeat
    url = reverse("surveys:survey_groups_repeat_create", kwargs={"slug": survey.slug})
    res_parent = client.post(
        url,
        data={
            "name": "Patient",
            "min_count": 0,
            "max_count": "",
            "group_ids": f"{g1.id}",
        },
        follow=True,
    )
    assert res_parent.status_code in (200, 302)
    parent = CollectionDefinition.objects.get(survey=survey, name="Patient")
    assert parent.max_count is None  # unlimited

    # Now create a child repeat nested under parent
    res_child = client.post(
        url,
        data={
            "name": "Visit",
            "min_count": 0,
            "max_count": "3",
            "group_ids": f"{g2.id}",
            "parent_id": str(parent.id),
        },
        follow=True,
    )
    assert res_child.status_code in (200, 302)

    child = CollectionDefinition.objects.get(survey=survey, name="Visit")
    assert child.parent_id == parent.id
    assert child.max_count == 3

    # Parent should have a CollectionItem pointing to the child collection
    parent_items = list(
        CollectionItem.objects.filter(collection=parent).order_by("order", "id")
    )
    assert any(
        it.item_type == CollectionItem.ItemType.COLLECTION
        and it.child_collection_id == child.id
        for it in parent_items
    )


@pytest.mark.django_db
def test_repeat_create_cardinality_one_when_max_one(client):
    owner, org, survey, g1, g2 = _setup_survey_with_groups()
    client.force_login(owner)
    url = reverse("surveys:survey_groups_repeat_create", kwargs={"slug": survey.slug})
    res = client.post(
        url,
        data={
            "name": "Single",
            "min_count": 0,
            "max_count": "1",
            "group_ids": f"{g1.id}",
        },
        follow=True,
    )
    assert res.status_code in (200, 302)
    cd = CollectionDefinition.objects.get(survey=survey, name="Single")
    assert cd.cardinality == CollectionDefinition.Cardinality.ONE
    assert cd.max_count == 1


@pytest.mark.django_db
def test_repeat_create_ignores_invalid_parent_id(client):
    owner, org, survey, g1, g2 = _setup_survey_with_groups()
    # Create another survey and a repeat there to simulate foreign parent id
    other = Survey.objects.create(
        owner=owner, organization=org, name="Other", slug="other"
    )
    foreign_parent = CollectionDefinition.objects.create(
        survey=other, key="foreign", name="Foreign"
    )
    client.force_login(owner)
    url = reverse("surveys:survey_groups_repeat_create", kwargs={"slug": survey.slug})
    res = client.post(
        url,
        data={
            "name": "Child",
            "min_count": 0,
            "max_count": "2",
            "group_ids": f"{g1.id}",
            "parent_id": str(foreign_parent.id),
        },
        follow=True,
    )
    assert res.status_code in (200, 302)
    child = CollectionDefinition.objects.get(survey=survey, name="Child")
    assert child.parent_id is None
    # No item should exist under the foreign parent because surveys mismatch
    assert not CollectionItem.objects.filter(
        collection=foreign_parent, child_collection=child
    ).exists()


@pytest.mark.django_db
def test_repeat_create_requires_group_selection(client):
    owner, org, survey, g1, g2 = _setup_survey_with_groups()
    client.force_login(owner)
    url = reverse("surveys:survey_groups_repeat_create", kwargs={"slug": survey.slug})
    res = client.post(
        url, data={"name": "Empty", "min_count": 0, "max_count": ""}, follow=True
    )
    # Should redirect back with an error and not create anything
    assert res.status_code in (200, 302)
    assert not CollectionDefinition.objects.filter(survey=survey, name="Empty").exists()
