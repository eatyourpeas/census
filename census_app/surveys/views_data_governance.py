"""
Data Governance Views

Handles data governance operations that extend existing survey functionality:
- Data exports with secure download tokens
- Retention period extensions
- Legal holds
- Data custodian management

Note: Survey closure and deletion are handled by existing views in views.py
"""

from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import (
    DataCustodian,
    DataExport,
    LegalHold,
    Survey,
)
from .permissions import (
    require_can_export_survey_data,
    require_can_extend_retention,
    require_can_manage_data_custodians,
    require_can_manage_legal_hold,
)
from .services import ExportService, RetentionService


# ============================================================================
# Data Export
# ============================================================================


@login_required
@transaction.atomic
def survey_export_create(request: HttpRequest, slug: str) -> HttpResponse:
    """Create a new data export with secure download link."""
    survey = get_object_or_404(Survey, slug=slug)
    require_can_export_survey_data(request.user, survey)
    
    if request.method == 'POST':
        password = request.POST.get('password', '').strip() or None
        attestation_accepted = request.POST.get('attestation_accepted') in ['true', 'True', True, '1', 1]
        
        # Validate attestation
        if not attestation_accepted:
            messages.error(
                request,
                "You must confirm that you are authorized to export this data."
            )
            # Return to form with error
            response_count = survey.responses.count()
            context = {
                'survey': survey,
                'response_count': response_count,
            }
            return render(request, 'surveys/data_governance/export_create.html', context)
        
        try:
            export = ExportService.create_export(survey, request.user, password)
            
            messages.success(
                request,
                f"Export created successfully. {export.response_count} responses exported."
            )
            
            return redirect('surveys:survey_export_download', slug=slug, export_id=export.id)
            
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('surveys:dashboard', slug=slug)
    
    # GET request - show export form
    response_count = survey.responses.count()
    
    context = {
        'survey': survey,
        'response_count': response_count,
    }
    
    return render(request, 'surveys/data_governance/export_create.html', context)


@login_required
def survey_export_download(
    request: HttpRequest, slug: str, export_id: str
) -> HttpResponse:
    """Display download link for an export."""
    survey = get_object_or_404(Survey, slug=slug)
    export = get_object_or_404(DataExport, id=export_id, survey=survey)
    
    require_can_export_survey_data(request.user, survey)
    
    # Generate download URL
    download_url = ExportService.get_download_url(export)
    
    context = {
        'survey': survey,
        'export': export,
        'download_url': download_url,
        'expires_at': export.download_url_expires_at,
    }
    
    return render(request, 'surveys/data_governance/export_download.html', context)


@login_required
def survey_export_file(
    request: HttpRequest, slug: str, export_id: str, token: str
) -> HttpResponse:
    """Download the actual export file (validates token)."""
    survey = get_object_or_404(Survey, slug=slug)
    export = get_object_or_404(DataExport, id=export_id, survey=survey)
    
    # Validate download token
    if not ExportService.validate_download_token(export, token):
        messages.error(request, "Invalid or expired download link.")
        return redirect('surveys:dashboard', slug=slug)
    
    # TODO: Retrieve CSV from object storage
    # For now, generate on-the-fly
    csv_data = ExportService._generate_csv(survey)
    
    # Record download
    ExportService.record_download(export)
    
    # Return CSV file
    response = HttpResponse(csv_data, content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="survey_{slug}_export.csv"'
    
    return response


# ============================================================================
# Retention Management
# ============================================================================


@login_required
@transaction.atomic
def survey_extend_retention(request: HttpRequest, slug: str) -> HttpResponse:
    """Extend retention period for a survey."""
    survey = get_object_or_404(Survey, slug=slug)
    require_can_extend_retention(request.user, survey)
    
    if request.method == 'POST':
        months = int(request.POST.get('months', 0))
        reason = request.POST.get('reason', '').strip()
        
        if not reason:
            messages.error(request, "Please provide a reason for extending retention.")
            return redirect('survey_extend_retention', slug=slug)
        
        if months < 1:
            messages.error(request, "Please specify a valid number of months.")
            return redirect('survey_extend_retention', slug=slug)
        
        try:
            RetentionService.extend_retention(survey, months, request.user, reason)
            
            messages.success(
                request,
                f"Retention extended by {months} months. "
                f"New deletion date: {survey.deletion_date.strftime('%Y-%m-%d')}"
            )
            
            return redirect('surveys:dashboard', slug=slug)
            
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('survey_extend_retention', slug=slug)
    
    # GET request - show extension form
    context = {
        'survey': survey,
        'current_retention': survey.retention_months,
        'max_extension': 24 - survey.retention_months,
        'deletion_date': survey.deletion_date,
    }
    
    return render(request, 'surveys/data_governance/extend_retention.html', context)


# ============================================================================
# Legal Holds
# ============================================================================


@login_required
@transaction.atomic
def survey_legal_hold_place(request: HttpRequest, slug: str) -> HttpResponse:
    """Place a legal hold on a survey."""
    survey = get_object_or_404(Survey, slug=slug)
    require_can_manage_legal_hold(request.user, survey)
    
    # Check if already has active legal hold
    if hasattr(survey, 'legal_hold') and survey.legal_hold.is_active:
        messages.warning(request, "This survey already has an active legal hold.")
        return redirect('surveys:dashboard', slug=slug)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        authority = request.POST.get('authority', '').strip()
        
        if not reason or not authority:
            messages.error(request, "Please provide both reason and authority.")
            return redirect('survey_legal_hold_place', slug=slug)
        
        LegalHold.objects.create(
            survey=survey,
            placed_by=request.user,
            reason=reason,
            authority=authority,
        )
        
        messages.success(request, "Legal hold placed successfully. Survey cannot be deleted.")
        return redirect('surveys:dashboard', slug=slug)
    
    # GET request - show form
    context = {
        'survey': survey,
    }
    
    return render(request, 'surveys/data_governance/legal_hold_place.html', context)


@login_required
@transaction.atomic
def survey_legal_hold_remove(request: HttpRequest, slug: str) -> HttpResponse:
    """Remove a legal hold from a survey."""
    survey = get_object_or_404(Survey, slug=slug)
    require_can_manage_legal_hold(request.user, survey)
    
    if not hasattr(survey, 'legal_hold') or not survey.legal_hold.is_active:
        messages.warning(request, "This survey does not have an active legal hold.")
        return redirect('surveys:dashboard', slug=slug)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        
        if not reason:
            messages.error(request, "Please provide a reason for removing the legal hold.")
            return redirect('survey_legal_hold_remove', slug=slug)
        
        survey.legal_hold.remove(request.user, reason)
        
        messages.success(request, "Legal hold removed.")
        return redirect('surveys:dashboard', slug=slug)
    
    # GET request - show confirmation
    context = {
        'survey': survey,
        'legal_hold': survey.legal_hold,
    }
    
    return render(request, 'surveys/data_governance/legal_hold_remove.html', context)


# ============================================================================
# Data Custodians
# ============================================================================


@login_required
@transaction.atomic
def survey_custodian_grant(request: HttpRequest, slug: str) -> HttpResponse:
    """Grant data custodian access to a user."""
    survey = get_object_or_404(Survey, slug=slug)
    require_can_manage_data_custodians(request.user, survey)
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        reason = request.POST.get('reason', '').strip()
        duration_days = request.POST.get('duration_days', '').strip()
        
        if not user_id or not reason:
            messages.error(request, "Please provide both user and reason.")
            return redirect('survey_custodian_grant', slug=slug)
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            messages.error(request, "User not found.")
            return redirect('survey_custodian_grant', slug=slug)
        
        # Check if user already has active custodian access
        existing = DataCustodian.objects.filter(
            survey=survey,
            user=user,
            revoked_at__isnull=True,
        ).first()
        
        if existing:
            messages.warning(request, f"{user.username} already has active custodian access.")
            return redirect('surveys:dashboard', slug=slug)
        
        # Create custodian grant
        expires_at = None
        if duration_days:
            try:
                days = int(duration_days)
                expires_at = timezone.now() + timedelta(days=days)
            except ValueError:
                messages.error(request, "Invalid duration.")
                return redirect('survey_custodian_grant', slug=slug)
        
        DataCustodian.objects.create(
            survey=survey,
            user=user,
            granted_by=request.user,
            reason=reason,
            expires_at=expires_at,
        )
        
        messages.success(
            request,
            f"Data custodian access granted to {user.username}."
        )
        
        return redirect('surveys:dashboard', slug=slug)
    
    # GET request - show form
    # Get organization members as potential custodians
    potential_custodians = User.objects.none()
    if survey.organization:
        potential_custodians = User.objects.filter(
            organization_memberships__organization=survey.organization
        ).exclude(id=request.user.id).distinct()
    
    context = {
        'survey': survey,
        'potential_custodians': potential_custodians,
    }
    
    return render(request, 'surveys/data_governance/custodian_grant.html', context)


@login_required
@transaction.atomic
def survey_custodian_revoke(
    request: HttpRequest, slug: str, custodian_id: int
) -> HttpResponse:
    """Revoke data custodian access."""
    survey = get_object_or_404(Survey, slug=slug)
    custodian = get_object_or_404(
        DataCustodian, id=custodian_id, survey=survey, revoked_at__isnull=True
    )
    
    require_can_manage_data_custodians(request.user, survey)
    
    if request.method == 'POST':
        custodian.revoke(request.user)
        
        messages.success(
            request,
            f"Data custodian access revoked for {custodian.user.username}."
        )
        
        return redirect('surveys:dashboard', slug=slug)
    
    # GET request - show confirmation
    context = {
        'survey': survey,
        'custodian': custodian,
    }
    
    return render(request, 'surveys/data_governance/custodian_revoke.html', context)

