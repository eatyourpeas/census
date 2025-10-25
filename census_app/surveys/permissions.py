from __future__ import annotations

from django.core.exceptions import PermissionDenied

from .models import Organization, OrganizationMembership, Survey, SurveyMembership


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
    # creators and viewers of the specific survey can view it
    if SurveyMembership.objects.filter(user=user, survey=survey).exists():
        return True
    return False


def can_edit_survey(user, survey: Survey) -> bool:
    # Edit requires: owner, org admin, or survey-level creator/editor
    if not user.is_authenticated:
        return False
    if survey.owner_id == getattr(user, "id", None):
        return True
    if survey.organization_id and is_org_admin(user, survey.organization):
        return True
    return SurveyMembership.objects.filter(
        user=user,
        survey=survey,
        role__in=[SurveyMembership.Role.CREATOR, SurveyMembership.Role.EDITOR]
    ).exists()


def can_manage_org_users(user, org: Organization) -> bool:
    return is_org_admin(user, org)


def can_manage_survey_users(user, survey: Survey) -> bool:
    # Only survey creators (not editors), org admins, or owner can manage users on a survey
    if survey.organization_id and is_org_admin(user, survey.organization):
        return True
    if survey.owner_id == getattr(user, "id", None):
        return True
    # Only CREATOR role can manage users, EDITOR cannot
    return SurveyMembership.objects.filter(
        user=user, survey=survey, role=SurveyMembership.Role.CREATOR
    ).exists()


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
