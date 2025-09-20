from __future__ import annotations

from django.core.exceptions import PermissionDenied

from .models import Organization, OrganizationMembership, Survey


def is_org_admin(user, org: Organization | None) -> bool:
    if not user.is_authenticated or org is None:
        return False
    return OrganizationMembership.objects.filter(
        user=user, organization=org, role=OrganizationMembership.Role.ADMIN
    ).exists()


def can_view_survey(user, survey: Survey) -> bool:
    if not user.is_authenticated:
        return False
    if survey.owner_id == getattr(user, "id", None):
        return True
    if survey.organization_id and is_org_admin(user, survey.organization):
        return True
    return False


def can_edit_survey(user, survey: Survey) -> bool:
    # Same policy as view for now: owner or org admin
    return can_view_survey(user, survey)


def require_can_view(user, survey: Survey) -> None:
    if not can_view_survey(user, survey):
        raise PermissionDenied("You do not have permission to view this survey.")


def require_can_edit(user, survey: Survey) -> None:
    if not can_edit_survey(user, survey):
        raise PermissionDenied("You do not have permission to edit this survey.")


def user_has_org_membership(user) -> bool:
    if not user.is_authenticated:
        return False
    return OrganizationMembership.objects.filter(user=user).exists()
