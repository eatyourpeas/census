from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User

from census_app.surveys.models import (
    Survey,
    Organization,
    OrganizationMembership,
    QuestionGroup,
    CollectionDefinition,
    CollectionItem,
)


@pytest.fixture
def baseline(db):
    owner = User.objects.create_user(username="owner", password="x")
    org = Organization.objects.create(name="Org", owner=owner)
    OrganizationMembership.objects.create(organization=org, user=owner, role=OrganizationMembership.Role.ADMIN)
    survey = Survey.objects.create(owner=owner, organization=org, name="S1", slug="s1")
    g1 = QuestionGroup.objects.create(name="Demographics", owner=owner, schema={})
    g2 = QuestionGroup.objects.create(name="Allergies", owner=owner, schema={})
    survey.question_groups.add(g1, g2)
    return owner, org, survey, g1, g2


def test_collection_definition_depth_cap_and_key_uniqueness(baseline):
    owner, org, survey, g1, g2 = baseline
    parent = CollectionDefinition.objects.create(survey=survey, key="patient", name="Patient")
    child = CollectionDefinition.objects.create(survey=survey, key="visit", name="Visit", parent=parent)
    # A grandchild should be invalid (depth > 2)
    with pytest.raises(ValidationError):
        gchild = CollectionDefinition(survey=survey, key="treatment", name="Treatment", parent=child)
        gchild.clean()
    # Duplicate key per survey
    with pytest.raises(Exception):
        CollectionDefinition.objects.create(survey=survey, key="patient", name="X")


def test_collection_item_requires_correct_target_and_same_survey(baseline):
    owner, org, survey, g1, g2 = baseline
    parent = CollectionDefinition.objects.create(survey=survey, key="patient", name="Patient")
    # Item must have either group or child_collection
    ci = CollectionItem(collection=parent, item_type=CollectionItem.ItemType.GROUP)
    with pytest.raises(ValidationError):
        ci.clean()
    # Group must be attached to survey
    # Create another survey; not used directly here but ensures cross-survey constraints elsewhere
    Survey.objects.create(owner=owner, organization=org, name="S2", slug="s2")
    g_other = QuestionGroup.objects.create(name="Other", owner=owner, schema={})
    # Not attached to this survey -> invalid
    ci2 = CollectionItem(collection=parent, item_type=CollectionItem.ItemType.GROUP, group=g_other, order=0)
    with pytest.raises(ValidationError):
        ci2.clean()
    # Attach and validate
    survey.question_groups.add(g1)
    ci3 = CollectionItem(collection=parent, item_type=CollectionItem.ItemType.GROUP, group=g1, order=0)
    ci3.clean()


def test_collection_item_child_collection_must_point_back_to_parent(baseline):
    owner, org, survey, g1, g2 = baseline
    parent = CollectionDefinition.objects.create(survey=survey, key="patient", name="Patient")
    child = CollectionDefinition.objects.create(survey=survey, key="visit", name="Visit", parent=parent)
    # Invalid: child_collection's parent must be the current collection
    wrong_parent = CollectionDefinition.objects.create(survey=survey, key="other", name="Other")
    ci = CollectionItem(collection=wrong_parent, item_type=CollectionItem.ItemType.COLLECTION, child_collection=child, order=0)
    with pytest.raises(ValidationError):
        ci.clean()
    # Valid when wired correctly
    ci2 = CollectionItem(collection=parent, item_type=CollectionItem.ItemType.COLLECTION, child_collection=child, order=0)
    ci2.clean()
