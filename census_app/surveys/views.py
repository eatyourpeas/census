from __future__ import annotations

import csv
import io
import json
import secrets
from pathlib import Path

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import Http404, HttpRequest, HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_http_methods
from django_ratelimit.decorators import ratelimit

from .color import hex_to_oklch
from .markdown_import import BulkParseError, parse_bulk_markdown_with_collections
from .models import (
    AuditLog,
    CollectionDefinition,
    CollectionItem,
    Organization,
    OrganizationMembership,
    QuestionGroup,
    Survey,
    SurveyAccessToken,
    SurveyMembership,
    SurveyQuestion,
    SurveyResponse,
)
from .permissions import (
    can_edit_survey,
    can_manage_org_users,
    can_manage_survey_users,
    can_view_survey,
    require_can_edit,
    require_can_view,
)
from .utils import verify_key

# Demographics field definitions: key -> display label
DEMOGRAPHIC_FIELD_DEFS: dict[str, str] = {
    "first_name": "First name",
    "surname": "Surname",
    "date_of_birth": "Date of birth",
    "ethnicity": "Ethnicity",
    "sex": "Sex",
    "gender": "Gender",
    "nhs_number": "NHS number",
    "hospital_number": "Hospital number",
    "post_code": "Post code",
    "address_first_line": "Address line 1",
    "address_second_line": "Address line 2",
    "city": "City",
    "country": "Country",
}


def _get_patient_group_and_fields(
    survey: Survey,
) -> tuple[QuestionGroup | None, list[str]]:
    group = survey.question_groups.filter(
        schema__template="patient_details_encrypted"
    ).first()
    if not group:
        return None, []
    raw = group.schema or {}
    sel = raw.get("fields") or []
    # sanitize selection
    fields = [k for k in sel if k in DEMOGRAPHIC_FIELD_DEFS]
    return group, fields


# Professional details (non-encrypted) field definitions
PROFESSIONAL_FIELD_DEFS: dict[str, str] = {
    "title": "Title",
    "first_name": "First name",
    "surname": "Surname",
    "job_title": "Job title",
    "employing_trust": "Employing Trust",
    "employing_health_board": "Employing Health Board",
    "integrated_care_board": "Integrated Care Board",
    "nhs_england_region": "NHS England region",
    "country": "Country",
    "gp_surgery": "GP surgery",
}

# Fields that can optionally include an ODS code alongside their text
PROFESSIONAL_ODS_FIELDS = {
    "employing_trust",
    "employing_health_board",
    "integrated_care_board",
    "gp_surgery",
}


def _get_professional_group_and_fields(
    survey: Survey,
) -> tuple[QuestionGroup | None, list[str], dict[str, bool]]:
    """Return the Professional details group, selected fields, and ODS toggles map.

    Schema example:
    {"template": "professional_details", "fields": [...], "ods": {field: bool}}
    """
    group = survey.question_groups.filter(
        schema__template="professional_details"
    ).first()
    if not group:
        return None, [], {}
    raw = group.schema or {}
    sel = raw.get("fields") or []
    fields = [k for k in sel if k in PROFESSIONAL_FIELD_DEFS]
    ods_map = raw.get("ods") or {}
    # sanitize ods map to only allowed fields
    ods_clean = {k: bool(ods_map.get(k)) for k in PROFESSIONAL_ODS_FIELDS}
    return group, fields, ods_clean


def _survey_collects_patient_data(survey: Survey) -> bool:
    grp, fields = _get_patient_group_and_fields(survey)
    return bool(grp and fields)


def _verify_captcha(request: HttpRequest) -> bool:
    """Server-side hCaptcha verification.

    Expects POST token in 'h-captcha-response'. Uses settings.HCAPTCHA_SECRET.
    Returns True if verification passes or if not configured (fails closed only when required upstream).
    """
    secret = getattr(settings, "HCAPTCHA_SECRET", None)
    if not secret:
        # Not configured; treat as pass. Enforcement happens in views based on survey.captcha_required.
        return True
    token = request.POST.get("h-captcha-response")
    if not token:
        return False
    try:
        import urllib.parse
        import urllib.request

        data = urllib.parse.urlencode(
            {
                "secret": secret,
                "response": token,
                "remoteip": request.META.get("REMOTE_ADDR", ""),
            }
        ).encode()
        req = urllib.request.Request("https://hcaptcha.com/siteverify", data=data)
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urllib.request.urlopen(req, timeout=5) as resp:  # nosec B310
            import json as _json

            payload = _json.loads(resp.read().decode("utf-8"))
            return bool(payload.get("success"))
    except Exception:
        return False


@login_required
def survey_list(request: HttpRequest) -> HttpResponse:
    # Creators/Viewers: only see surveys they created (owner)
    # Admins: see all surveys in their organization
    user = request.user
    surveys = Survey.objects.none()
    if user.is_authenticated:
        owned = Survey.objects.filter(owner=user)
        org_ids = user.org_memberships.values_list("organization_id", flat=True)
        if org_ids:
            org_surveys = Survey.objects.filter(organization_id__in=list(org_ids))
            # keep only those the user can view (admins of those orgs)
            org_surveys = [s for s in org_surveys if can_view_survey(user, s)]
            surveys = owned | Survey.objects.filter(id__in=[s.id for s in org_surveys])
        else:
            surveys = owned
    return render(request, "surveys/list.html", {"surveys": surveys})


class SurveyCreateForm(forms.ModelForm):
    slug = forms.SlugField(
        required=False, help_text="Leave blank to auto-generate from name"
    )

    class Meta:
        model = Survey
        fields = ["name", "slug", "description"]

    def clean_name(self):
        name = self.cleaned_data.get("name")
        if not name:
            raise forms.ValidationError("Name is required")
        return name

    def clean_slug(self):
        slug = self.cleaned_data.get("slug")
        name = self.cleaned_data.get("name", "")

        # If slug is not provided, generate it from name
        if not slug and name:
            # Clean the name: remove brackets, apostrophes, and other non-alphanumeric chars
            import re

            cleaned_name = re.sub(
                r"[^\w\s-]", "", name
            )  # Remove special chars except spaces and hyphens
            slug = slugify(cleaned_name)

        # If still no slug after generation, raise error
        if not slug:
            raise forms.ValidationError("Could not generate slug from name")

        # Check for uniqueness
        if Survey.objects.filter(slug=slug).exists():
            raise forms.ValidationError("Slug already in use")

        return slug


@login_required
@require_http_methods(["GET", "POST"])
def survey_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = SurveyCreateForm(request.POST)
        if form.is_valid():
            survey: Survey = form.save(commit=False)
            survey.owner = request.user
            survey.save()
            return redirect("surveys:groups", slug=survey.slug)
    else:
        form = SurveyCreateForm()
    return render(request, "surveys/create.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
@ratelimit(key="ip", rate="10/m", block=True)
def survey_detail(request: HttpRequest, slug: str) -> HttpResponse:
    survey = get_object_or_404(Survey, slug=slug)
    # Only authenticated users with view permission may access any survey
    require_can_view(request.user, survey)

    # Prevent the survey owner from submitting responses directly in the live view
    if request.user.is_authenticated and survey.owner_id == request.user.id:
        messages.info(
            request,
            "You are the owner. Use Groups to manage questions or Preview to see the participant view.",
        )
        return redirect("surveys:groups", slug=slug)

    # Determine demographics and professional configuration upfront
    patient_group, demographics_fields = _get_patient_group_and_fields(survey)
    prof_group, professional_fields, professional_ods = (
        _get_professional_group_and_fields(survey)
    )

    if request.method == "POST":
        answers = {}
        for q in survey.questions.all():
            key = f"q_{q.id}"
            value = (
                request.POST.getlist(key)
                if q.type in {"mc_multi", "orderable"}
                else request.POST.get(key)
            )
            answers[str(q.id)] = value

        # Collect professional details (non-encrypted)
        professional_payload = {}
        for field in professional_fields:
            val = request.POST.get(f"prof_{field}")
            if val:
                professional_payload[field] = val
            # Optional ODS code for certain fields
            if professional_ods.get(field):
                ods_val = request.POST.get(f"prof_{field}_ods")
                if ods_val:
                    professional_payload[f"{field}_ods"] = ods_val

        resp = SurveyResponse(
            survey=survey,
            answers={
                **answers,
                **(
                    {"professional": professional_payload}
                    if professional_payload
                    else {}
                ),
            },
            submitted_by=request.user if request.user.is_authenticated else None,
        )
        # Optionally store demographics if provided under special keys
        demo = {}
        for field in demographics_fields:
            val = request.POST.get(field)
            if val:
                demo[field] = val
        if demo and request.session.get("survey_key"):
            resp.store_demographics(request.session["survey_key"], demo)
        try:
            resp.save()
        except Exception:
            messages.error(request, "You have already submitted this survey.")
            return redirect("surveys:detail", slug=slug)

        # Also write to filesystem as JSON, excluding enc demographics
        out_dir = Path(settings.DATA_ROOT) / f"survey_{survey.id}"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"response_{resp.id}.json"
        out_file.write_text(
            json.dumps(
                {"answers": answers, "submitted_at": resp.submitted_at.isoformat()},
                indent=2,
            )
        )

        messages.success(request, "Thank you for your response.")
        return redirect("surveys:detail", slug=slug)

    _prepare_question_rendering(survey)
    # Prepare ordered questions and attach a global index for numbering in templates
    qs = list(survey.questions.select_related("group").all())
    for i, q in enumerate(qs, start=1):
        setattr(q, "idx", i)
        prev_gid = qs[i - 2].group_id if i - 2 >= 0 else None
        next_gid = qs[i].group_id if i < len(qs) else None
        curr_gid = q.group_id
        setattr(q, "group_start", bool(curr_gid and curr_gid != prev_gid))
        setattr(q, "group_end", bool(curr_gid and curr_gid != next_gid))
    show_patient_details = patient_group is not None
    show_professional_details = prof_group is not None
    # Style overrides
    style = survey.style or {}
    brand_overrides = {
        "title": style.get("title"),
        "icon_url": style.get("icon_url"),
        "theme_name": style.get("theme_name"),
        "font_heading": style.get("font_heading"),
        "font_body": style.get("font_body"),
        "primary_hex": style.get("primary_color"),
        "font_css_url": style.get("font_css_url"),
    }
    ctx = {
        "survey": survey,
        "questions": qs,
        "show_patient_details": show_patient_details,
        "demographics_fields": demographics_fields,
        "demographic_defs": DEMOGRAPHIC_FIELD_DEFS,
        "demographics_fields_with_labels": [
            (k, DEMOGRAPHIC_FIELD_DEFS[k]) for k in demographics_fields
        ],
        "show_professional_details": show_professional_details,
        "professional_fields": professional_fields,
        "professional_defs": PROFESSIONAL_FIELD_DEFS,
        "professional_ods": professional_ods,
    }
    if any(
        v for k, v in brand_overrides.items() if k != "primary_hex"
    ) or brand_overrides.get("primary_hex"):
        # Only override if any per-survey style is set; otherwise use context processor defaults
        ctx["brand"] = {
            "title": brand_overrides.get("title")
            or getattr(settings, "BRAND_TITLE", "Census"),
            "icon_url": brand_overrides.get("icon_url")
            or getattr(settings, "BRAND_ICON_URL", "/static/favicon.ico"),
            "theme_name": brand_overrides.get("theme_name")
            or getattr(settings, "BRAND_THEME", "census"),
            "font_heading": brand_overrides.get("font_heading")
            or getattr(
                settings,
                "BRAND_FONT_HEADING",
                "'IBM Plex Sans', ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, 'Apple Color Emoji', 'Segoe UI Emoji'",
            ),
            "font_body": brand_overrides.get("font_body")
            or getattr(
                settings,
                "BRAND_FONT_BODY",
                "Merriweather, ui-serif, Georgia, Cambria, 'Times New Roman', Times, serif",
            ),
            "font_css_url": brand_overrides.get("font_css_url")
            or getattr(
                settings,
                "BRAND_FONT_CSS_URL",
                "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600;700&family=Merriweather:wght@300;400;700&display=swap",
            ),
            "primary": hex_to_oklch(brand_overrides.get("primary_hex") or ""),
        }
    return render(
        request,
        "surveys/detail.html",
        ctx,
    )


@login_required
@require_http_methods(["GET"])
def survey_preview(request: HttpRequest, slug: str) -> HttpResponse:
    survey = get_object_or_404(Survey, slug=slug)
    require_can_view(request.user, survey)
    # Render the same detail template but never accept POST here
    _prepare_question_rendering(survey)
    qs = list(survey.questions.select_related("group").all())
    for i, q in enumerate(qs, start=1):
        setattr(q, "idx", i)
        prev_gid = qs[i - 2].group_id if i - 2 >= 0 else None
        next_gid = qs[i].group_id if i < len(qs) else None
        curr_gid = q.group_id
        setattr(q, "group_start", bool(curr_gid and curr_gid != prev_gid))
        setattr(q, "group_end", bool(curr_gid and curr_gid != next_gid))
    patient_group, demographics_fields = _get_patient_group_and_fields(survey)
    prof_group, professional_fields, professional_ods = (
        _get_professional_group_and_fields(survey)
    )
    show_patient_details = patient_group is not None
    show_professional_details = prof_group is not None
    style = survey.style or {}
    brand_overrides = {
        "title": style.get("title"),
        "icon_url": style.get("icon_url"),
        "theme_name": style.get("theme_name"),
        "font_heading": style.get("font_heading"),
        "font_body": style.get("font_body"),
        "primary_hex": style.get("primary_color"),
        "font_css_url": style.get("font_css_url"),
    }
    ctx = {
        "survey": survey,
        "questions": qs,
        "show_patient_details": show_patient_details,
        "demographics_fields": demographics_fields,
        "demographic_defs": DEMOGRAPHIC_FIELD_DEFS,
        "demographics_fields_with_labels": [
            (k, DEMOGRAPHIC_FIELD_DEFS[k]) for k in demographics_fields
        ],
        "show_professional_details": show_professional_details,
        "professional_fields": professional_fields,
        "professional_defs": PROFESSIONAL_FIELD_DEFS,
        "professional_ods": professional_ods,
    }
    if any(
        v for k, v in brand_overrides.items() if k != "primary_hex"
    ) or brand_overrides.get("primary_hex"):
        ctx["brand"] = {
            "title": brand_overrides.get("title")
            or getattr(settings, "BRAND_TITLE", "Census"),
            "icon_url": brand_overrides.get("icon_url")
            or getattr(settings, "BRAND_ICON_URL", "/static/favicon.ico"),
            "theme_name": brand_overrides.get("theme_name")
            or getattr(settings, "BRAND_THEME", "census"),
            "font_heading": brand_overrides.get("font_heading")
            or getattr(
                settings,
                "BRAND_FONT_HEADING",
                "'IBM Plex Sans', ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, 'Apple Color Emoji', 'Segoe UI Emoji'",
            ),
            "font_body": brand_overrides.get("font_body")
            or getattr(
                settings,
                "BRAND_FONT_BODY",
                "Merriweather, ui-serif, Georgia, Cambria, 'Times New Roman', Times, serif",
            ),
            "font_css_url": brand_overrides.get("font_css_url")
            or getattr(
                settings,
                "BRAND_FONT_CSS_URL",
                "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600;700&family=Merriweather:wght@300;400;700&display=swap",
            ),
            "primary": hex_to_oklch(brand_overrides.get("primary_hex") or ""),
        }
    return render(
        request,
        "surveys/detail.html",
        ctx,
    )


def _prepare_question_rendering(survey: Survey) -> None:
    """Attach view-only helper attributes for template rendering.
    Currently sets num_scale_values for likert number-scale questions.
    """
    try:
        questions = survey.questions.all()
    except Exception:
        return
    for q in questions:
        try:
            if (
                q.type == "likert"
                and isinstance(q.options, list)
                and q.options
                and isinstance(q.options[0], dict)
                and q.options[0].get("type") == "number-scale"
            ):
                meta = q.options[0]
                minv = int(meta.get("min", 1))
                maxv = int(meta.get("max", 5))
                if maxv < minv:
                    minv, maxv = maxv, minv
                setattr(q, "num_scale_values", list(range(minv, maxv + 1)))
            else:
                setattr(q, "num_scale_values", None)
        except Exception:
            setattr(q, "num_scale_values", None)


@login_required
def survey_dashboard(request: HttpRequest, slug: str) -> HttpResponse:
    survey = get_object_or_404(Survey, slug=slug)
    require_can_view(request.user, survey)
    total = survey.responses.count()
    # Simple analytics
    now = timezone.now()
    start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    last7 = now - timezone.timedelta(days=7)
    today_count = survey.responses.filter(submitted_at__gte=start_today).count()
    last7_count = survey.responses.filter(submitted_at__gte=last7).count()
    # Sparkline data: last 14 full days (oldest -> newest)
    from collections import OrderedDict

    start_14 = start_today - timezone.timedelta(days=13)
    day_counts = OrderedDict()
    for i in range(14):
        day = start_14 + timezone.timedelta(days=i)
        next_day = day + timezone.timedelta(days=1)
        day_counts[day.date().isoformat()] = survey.responses.filter(
            submitted_at__gte=day, submitted_at__lt=next_day
        ).count()
    # Build sparkline polyline points (0..100 width, 0..24 height)
    values = list(day_counts.values())
    spark_points = ""
    if values:
        max_v = max(values) or 1
        n = len(values)
        width = 100.0
        height = 24.0
        dx = width / (n - 1) if n > 1 else width
        pts = []
        for i, v in enumerate(values):
            x = dx * i
            y = height - (float(v) / float(max_v)) * height
            pts.append(f"{x:.1f},{y:.1f}")
        spark_points = " ".join(pts)
    # Derived status
    is_live = survey.is_live()
    visible = (
        survey.get_visibility_display()
        if hasattr(survey, "get_visibility_display")
        else "Authenticated"
    )
    groups = (
        survey.question_groups.filter(owner=request.user)
        .annotate(
            q_count=models.Count(
                "surveyquestion", filter=models.Q(surveyquestion__survey=survey)
            )
        )
        .order_by("name")
    )
    # Per-survey style overrides for branding on dashboard
    style = survey.style or {}
    brand_overrides = {
        "title": style.get("title"),
        "icon_url": style.get("icon_url"),
        "theme_name": style.get("theme_name"),
        "font_heading": style.get("font_heading"),
        "font_body": style.get("font_body"),
        "primary_hex": style.get("primary_color"),
        "font_css_url": style.get("font_css_url"),
    }
    ctx = {
        "survey": survey,
        "total": total,
        "groups": groups,
        "is_live": is_live,
        "visible": visible,
        "today_count": today_count,
        "last7_count": last7_count,
        "day_counts": list(day_counts.values()),
        "spark_points": spark_points,
    }
    if any(
        v for k, v in brand_overrides.items() if k != "primary_hex"
    ) or brand_overrides.get("primary_hex"):
        ctx["brand"] = {
            "title": brand_overrides.get("title")
            or getattr(settings, "BRAND_TITLE", "Census"),
            "icon_url": brand_overrides.get("icon_url")
            or getattr(settings, "BRAND_ICON_URL", "/static/favicon.ico"),
            "theme_name": brand_overrides.get("theme_name")
            or getattr(settings, "BRAND_THEME", "census"),
            "font_heading": brand_overrides.get("font_heading")
            or getattr(
                settings,
                "BRAND_FONT_HEADING",
                "'IBM Plex Sans', ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, 'Apple Color Emoji', 'Segoe UI Emoji'",
            ),
            "font_body": brand_overrides.get("font_body")
            or getattr(
                settings,
                "BRAND_FONT_BODY",
                "Merriweather, ui-serif, Georgia, Cambria, 'Times New Roman', Times, serif",
            ),
            "font_css_url": brand_overrides.get("font_css_url")
            or getattr(
                settings,
                "BRAND_FONT_CSS_URL",
                "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600;700&family=Merriweather:wght@300;400;700&display=swap",
            ),
            "primary": hex_to_oklch(brand_overrides.get("primary_hex") or ""),
        }
    return render(request, "surveys/dashboard.html", ctx)


@login_required
@require_http_methods(["POST"])
def survey_publish_update(request: HttpRequest, slug: str) -> HttpResponse:
    survey = get_object_or_404(Survey, slug=slug)
    require_can_edit(request.user, survey)
    # Parse fields
    status = request.POST.get("status") or survey.status
    visibility = request.POST.get("visibility") or survey.visibility
    start_at = request.POST.get("start_at") or None
    end_at = request.POST.get("end_at") or None
    max_responses = request.POST.get("max_responses") or None
    captcha_required = bool(request.POST.get("captcha_required"))
    no_patient_data_ack = bool(request.POST.get("no_patient_data_ack"))

    # Coerce types
    from django.utils.dateparse import parse_datetime

    if start_at:
        start_at = parse_datetime(start_at)
    if end_at:
        end_at = parse_datetime(end_at)
    if max_responses:
        try:
            max_responses = int(max_responses)
            if max_responses <= 0:
                max_responses = None
        except Exception:
            max_responses = None

    # Enforce patient-data + non-auth visibility disclaimer
    collects_patient = _survey_collects_patient_data(survey)
    if (
        visibility
        in {
            Survey.Visibility.PUBLIC,
            Survey.Visibility.UNLISTED,
            Survey.Visibility.TOKEN,
        }
        and collects_patient
    ):
        if not no_patient_data_ack and visibility != Survey.Visibility.AUTHENTICATED:
            messages.error(
                request,
                "To use public, unlisted, or tokenized visibility, confirm that no patient data is collected.",
            )
            return redirect("surveys:dashboard", slug=slug)

    # Apply changes
    prev_status = survey.status
    survey.status = status
    survey.visibility = visibility
    survey.start_at = start_at
    survey.end_at = end_at
    survey.max_responses = max_responses
    survey.captcha_required = captcha_required
    survey.no_patient_data_ack = no_patient_data_ack
    # On first publish, set published_at
    if (
        prev_status != Survey.Status.PUBLISHED
        and status == Survey.Status.PUBLISHED
        and not survey.published_at
    ):
        survey.published_at = timezone.now()
    # Generate unlisted key if needed
    if survey.visibility == Survey.Visibility.UNLISTED and not survey.unlisted_key:
        survey.unlisted_key = secrets.token_urlsafe(24)
    survey.save()
    messages.success(request, "Publish settings updated.")
    return redirect("surveys:dashboard", slug=slug)


@require_http_methods(["GET", "POST"])
@ratelimit(key="ip", rate="10/m", block=True)
def survey_take(request: HttpRequest, slug: str) -> HttpResponse:
    """Participant-facing endpoint. Supports AUTHENTICATED and PUBLIC visibility here.
    UNLISTED and TOKEN have dedicated routes.
    """
    survey = get_object_or_404(Survey, slug=slug)
    if not survey.is_live():
        raise Http404()
    if survey.visibility == Survey.Visibility.UNLISTED:
        raise Http404()
    if survey.visibility == Survey.Visibility.TOKEN:
        # Redirect to generic info page or 404
        raise Http404()
    if (
        survey.visibility == Survey.Visibility.AUTHENTICATED
        and not request.user.is_authenticated
    ):
        # Enforce login
        messages.info(request, "Please sign in to take this survey.")
        return redirect("/accounts/login/?next=" + request.path)

    # If survey requires CAPTCHA for anonymous users
    if (
        request.method == "POST"
        and not request.user.is_authenticated
        and survey.captcha_required
    ):
        if not _verify_captcha(request):
            messages.error(request, "CAPTCHA verification failed.")
            return redirect("surveys:take", slug=slug)

    return _handle_participant_submission(request, survey, token_obj=None)


@require_http_methods(["GET", "POST"])
@ratelimit(key="ip", rate="10/m", block=True)
def survey_take_unlisted(request: HttpRequest, slug: str, key: str) -> HttpResponse:
    survey = get_object_or_404(Survey, slug=slug)
    if (
        not survey.is_live()
        or survey.visibility != Survey.Visibility.UNLISTED
        or survey.unlisted_key != key
    ):
        raise Http404()
    if (
        request.method == "POST"
        and not request.user.is_authenticated
        and survey.captcha_required
    ):
        if not _verify_captcha(request):
            messages.error(request, "CAPTCHA verification failed.")
            return redirect("surveys:take_unlisted", slug=slug, key=key)
    return _handle_participant_submission(request, survey, token_obj=None)


@require_http_methods(["GET", "POST"])
@ratelimit(key="ip", rate="10/m", block=True)
def survey_take_token(request: HttpRequest, slug: str, token: str) -> HttpResponse:
    survey = get_object_or_404(Survey, slug=slug)
    if not survey.is_live() or survey.visibility != Survey.Visibility.TOKEN:
        raise Http404()
    tok = get_object_or_404(SurveyAccessToken, survey=survey, token=token)
    if not tok.is_valid():
        messages.error(request, "This invite link has expired or already been used.")
        raise Http404()
    if (
        request.method == "POST"
        and not request.user.is_authenticated
        and survey.captcha_required
    ):
        if not _verify_captcha(request):
            messages.error(request, "CAPTCHA verification failed.")
            return redirect("surveys:take_token", slug=slug, token=token)
    return _handle_participant_submission(request, survey, token_obj=tok)


def _handle_participant_submission(
    request: HttpRequest, survey: Survey, token_obj: SurveyAccessToken | None
) -> HttpResponse:
    # Disallow collecting patient data on non-authenticated visibilities unless explicitly acknowledged at publish.
    collects_patient = _survey_collects_patient_data(survey)
    if (
        collects_patient
        and survey.visibility != Survey.Visibility.AUTHENTICATED
        and not survey.no_patient_data_ack
    ):
        messages.error(
            request,
            "This survey cannot be taken without authentication due to patient data.",
        )
        raise Http404()

    if request.method == "POST":
        # Prevent duplicate submission for tokenized link
        if token_obj and SurveyResponse.objects.filter(access_token=token_obj).exists():
            messages.error(request, "This invite link was already used.")
            raise Http404()

        answers = {}
        for q in survey.questions.all():
            key = f"q_{q.id}"
            value = (
                request.POST.getlist(key)
                if q.type in {"mc_multi", "orderable"}
                else request.POST.get(key)
            )
            answers[str(q.id)] = value

        # Professional details (non-encrypted)
        _, professional_fields, professional_ods = _get_professional_group_and_fields(
            survey
        )
        professional_payload = {}
        for field in professional_fields:
            val = request.POST.get(f"prof_{field}")
            if val:
                professional_payload[field] = val
            if professional_ods.get(field):
                ods_val = request.POST.get(f"prof_{field}_ods")
                if ods_val:
                    professional_payload[f"{field}_ods"] = ods_val

        resp = SurveyResponse(
            survey=survey,
            answers={
                **answers,
                **(
                    {"professional": professional_payload}
                    if professional_payload
                    else {}
                ),
            },
            submitted_by=request.user if request.user.is_authenticated else None,
            access_token=token_obj if token_obj else None,
        )
        # Demographics: only store if authenticated and key in session
        patient_group, demographics_fields = _get_patient_group_and_fields(survey)
        demo = {}
        for field in demographics_fields:
            val = request.POST.get(field)
            if val:
                demo[field] = val
        if demo and request.session.get("survey_key"):
            resp.store_demographics(request.session["survey_key"], demo)

        try:
            resp.save()
        except Exception:
            messages.error(request, "You have already submitted this survey.")
            return redirect("surveys:take", slug=survey.slug)

        # Mark token as used
        if token_obj:
            token_obj.used_at = timezone.now()
            if request.user.is_authenticated:
                token_obj.used_by = request.user
            token_obj.save(update_fields=["used_at", "used_by"])

        # Also mirror to filesystem as per authenticated detail view
        out_dir = Path(settings.DATA_ROOT) / f"survey_{survey.id}"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"response_{resp.id}.json"
        out_file.write_text(
            json.dumps(
                {"answers": answers, "submitted_at": resp.submitted_at.isoformat()},
                indent=2,
            )
        )

    messages.success(request, "Thank you for your response.")
    # Redirect to thank-you page
    return redirect("surveys:thank_you", slug=survey.slug)

    # GET: render using existing detail template
    _prepare_question_rendering(survey)
    qs = list(survey.questions.select_related("group").all())
    for i, q in enumerate(qs, start=1):
        setattr(q, "idx", i)
        prev_gid = qs[i - 2].group_id if i - 2 >= 0 else None
        next_gid = qs[i].group_id if i < len(qs) else None
        curr_gid = q.group_id
        setattr(q, "group_start", bool(curr_gid and curr_gid != prev_gid))
        setattr(q, "group_end", bool(curr_gid and curr_gid != next_gid))
    patient_group, demographics_fields = _get_patient_group_and_fields(survey)
    prof_group, professional_fields, professional_ods = (
        _get_professional_group_and_fields(survey)
    )
    show_patient_details = patient_group is not None
    show_professional_details = prof_group is not None
    ctx = {
        "survey": survey,
        "questions": qs,
        "show_patient_details": show_patient_details,
        "demographics_fields": demographics_fields,
        "demographic_defs": DEMOGRAPHIC_FIELD_DEFS,
        "demographics_fields_with_labels": [
            (k, DEMOGRAPHIC_FIELD_DEFS[k]) for k in demographics_fields
        ],
        "show_professional_details": show_professional_details,
        "professional_fields": professional_fields,
        "professional_defs": PROFESSIONAL_FIELD_DEFS,
        "professional_ods": professional_ods,
    }
    return render(request, "surveys/detail.html", ctx)


@require_http_methods(["GET"])
def survey_thank_you(request: HttpRequest, slug: str) -> HttpResponse:
    """Simple post-submission landing page for participants.

    Does not leak whether a survey exists beyond being reachable from a valid submission.
    """
    survey = Survey.objects.filter(slug=slug).first()
    # Render generic thank you even if survey missing to avoid information leakage
    return render(request, "surveys/thank_you.html", {"survey": survey})


@login_required
@require_http_methods(["GET", "POST"])
def survey_tokens(request: HttpRequest, slug: str) -> HttpResponse:
    survey = get_object_or_404(Survey, slug=slug)
    require_can_edit(request.user, survey)
    if request.method == "POST":
        try:
            count = int(request.POST.get("count", "0"))
        except ValueError:
            count = 0
        note = (request.POST.get("note") or "").strip()
        from django.utils.dateparse import parse_datetime

        expires_raw = request.POST.get("expires_at")
        expires_at = parse_datetime(expires_raw) if expires_raw else None
        created = []
        for _ in range(max(0, min(count, 1000))):
            t = SurveyAccessToken(
                survey=survey,
                token=secrets.token_urlsafe(24),
                created_by=request.user,
                expires_at=expires_at,
                note=note,
            )
            t.save()
            created.append(t)
        messages.success(request, f"Created {len(created)} tokens.")
        return redirect("surveys:tokens", slug=slug)
    tokens = survey.access_tokens.order_by("-created_at")[:500]
    return render(request, "surveys/tokens.html", {"survey": survey, "tokens": tokens})


@login_required
def survey_tokens_export_csv(request: HttpRequest, slug: str) -> HttpResponse:
    survey = get_object_or_404(Survey, slug=slug)
    require_can_edit(request.user, survey)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["token", "created_at", "expires_at", "used_at", "used_by", "note"])
    for t in survey.access_tokens.all():
        writer.writerow(
            [
                t.token,
                t.created_at.isoformat(),
                t.expires_at.isoformat() if t.expires_at else "",
                t.used_at.isoformat() if t.used_at else "",
                (t.used_by_id or ""),
                t.note,
            ]
        )
    resp = HttpResponse(output.getvalue(), content_type="text/csv")
    resp["Content-Disposition"] = f"attachment; filename=survey_{survey.id}_tokens.csv"
    return resp


@login_required
@require_http_methods(["POST"])
def survey_style_update(request: HttpRequest, slug: str) -> HttpResponse:
    survey = get_object_or_404(Survey, slug=slug)
    require_can_edit(request.user, survey)
    style = survey.style or {}
    # Accept simple fields; ignore if blank to allow fallback to platform defaults
    for key in (
        "title",
        "icon_url",
        "theme_name",
        "font_heading",
        "font_body",
        "primary_color",
        "font_css_url",
    ):
        val = (request.POST.get(key) or "").strip()
        if val:
            style[key] = val
        elif key in style:
            # allow clearing by leaving blank
            style.pop(key)
    survey.style = style
    survey.save(update_fields=["style"])
    messages.success(request, "Style updated.")
    return redirect("surveys:dashboard", slug=slug)


"""
Deprecated Collections SSR views were removed. Repeats are created and managed
from the Groups UI and bulk upload. Collections remain as backend entities only.
"""


@login_required
def survey_groups(request: HttpRequest, slug: str) -> HttpResponse:
    survey = get_object_or_404(Survey, slug=slug)
    require_can_view(request.user, survey)
    can_edit = can_edit_survey(request.user, survey)
    groups_qs = survey.question_groups.annotate(
        q_count=models.Count(
            "surveyquestion", filter=models.Q(surveyquestion__survey=survey)
        )
    )
    # Apply explicit saved order if present in survey.style
    order_ids = []
    style = survey.style or {}
    if isinstance(style.get("group_order"), list):
        order_ids = [int(gid) for gid in style["group_order"] if str(gid).isdigit()]
    groups_map = {g.id: g for g in groups_qs}
    ordered = [groups_map[g_id] for g_id in order_ids if g_id in groups_map]
    remaining = [g for g in groups_qs if g.id not in order_ids]
    groups = ordered + sorted(remaining, key=lambda g: g.name.lower())
    # Apply style overrides so navigation reflects survey branding while managing groups
    style = survey.style or {}
    brand_overrides = {
        "title": style.get("title"),
        "icon_url": style.get("icon_url"),
        "theme_name": style.get("theme_name"),
        "font_heading": style.get("font_heading"),
        "font_body": style.get("font_body"),
        "primary_hex": style.get("primary_color"),
        "font_css_url": style.get("font_css_url"),
    }
    # Map groups to any repeats (collections) they participate in
    group_repeat_map: dict[int, list[CollectionDefinition]] = {}
    for item in CollectionItem.objects.select_related("collection", "group").filter(
        collection__survey=survey, group__isnull=False
    ):
        group_repeat_map.setdefault(item.group_id, []).append(item.collection)

    # Prepare display info for repeats
    repeat_info: dict[int, dict] = {}
    for g in groups:
        cols = group_repeat_map.get(g.id, [])
        if cols:
            info_list = []
            for c in cols:
                cap = (
                    "Unlimited"
                    if (c.max_count is None or int(c.max_count) <= 0)
                    else str(c.max_count)
                )
                parent_note = f" (child of {c.parent.name})" if c.parent_id else ""
                info_list.append(f"{c.name} — max {cap}{parent_note}")
            repeat_info[g.id] = {"is_repeated": True, "tooltip": "; ".join(info_list)}
        else:
            repeat_info[g.id] = {"is_repeated": False, "tooltip": ""}

    existing_repeats = list(
        CollectionDefinition.objects.filter(survey=survey).order_by("name")
    )
    ctx = {
        "survey": survey,
        "groups": groups,
        "can_edit": can_edit,
        "repeat_info": repeat_info,
        "existing_repeats": existing_repeats,
    }
    if any(
        v for k, v in brand_overrides.items() if k != "primary_hex"
    ) or brand_overrides.get("primary_hex"):
        ctx["brand"] = {
            "title": brand_overrides.get("title")
            or getattr(settings, "BRAND_TITLE", "Census"),
            "icon_url": brand_overrides.get("icon_url")
            or getattr(settings, "BRAND_ICON_URL", "/static/favicon.ico"),
            "theme_name": brand_overrides.get("theme_name")
            or getattr(settings, "BRAND_THEME", "census"),
            "font_heading": brand_overrides.get("font_heading")
            or getattr(
                settings,
                "BRAND_FONT_HEADING",
                "'IBM Plex Sans', ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, 'Apple Color Emoji', 'Segoe UI Emoji'",
            ),
            "font_body": brand_overrides.get("font_body")
            or getattr(
                settings,
                "BRAND_FONT_BODY",
                "Merriweather, ui-serif, Georgia, Cambria, 'Times New Roman', Times, serif",
            ),
            "font_css_url": brand_overrides.get("font_css_url")
            or getattr(
                settings,
                "BRAND_FONT_CSS_URL",
                "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600;700&family=Merriweather:wght@300;400;700&display=swap",
            ),
            "primary": hex_to_oklch(brand_overrides.get("primary_hex") or ""),
        }
    return render(request, "surveys/groups.html", ctx)


@login_required
@require_http_methods(["POST"])
def survey_groups_repeat_create(request: HttpRequest, slug: str) -> HttpResponse:
    """
    Create a repeat (CollectionDefinition) from selected groups.
    Optional parent_id nests this repeat one level under an existing repeat.
    """
    survey = get_object_or_404(Survey, slug=slug)
    require_can_edit(request.user, survey)

    name = (request.POST.get("name") or "").strip()
    if not name:
        messages.error(request, "Please provide a name for the repeat.")
        return redirect("surveys:groups", slug=slug)
    min_count = request.POST.get("min_count") or "0"
    max_count_raw = (request.POST.get("max_count") or "").strip().lower()
    max_count: int | None
    if max_count_raw in ("", "unlimited", "-1"):
        max_count = None
    else:
        try:
            max_count = int(max_count_raw)
            if max_count < 1:
                max_count = None
        except Exception:
            max_count = None
    # Cardinality: one iff max_count == 1
    cardinality = (
        CollectionDefinition.Cardinality.ONE
        if (max_count == 1)
        else CollectionDefinition.Cardinality.MANY
    )

    # Parse group ids
    gids_csv = request.POST.get("group_ids", "")
    gid_list = [int(x) for x in gids_csv.split(",") if x.isdigit()]
    # Keep only those attached to this survey
    valid_ids = set(
        survey.question_groups.filter(id__in=gid_list).values_list("id", flat=True)
    )
    gid_list = [g for g in gid_list if g in valid_ids]
    if not gid_list:
        messages.error(request, "Select at least one group to include in the repeat.")
        return redirect("surveys:groups", slug=slug)

    # Ensure unique key per survey
    def _unique_key(base: str) -> str:
        k = slugify(base)
        if not k:
            k = "repeat"
        cand = k
        i = 2
        while CollectionDefinition.objects.filter(survey=survey, key=cand).exists():
            cand = f"{k}-{i}"
            i += 1
        return cand

    cd = CollectionDefinition(
        survey=survey,
        key=_unique_key(name),
        name=name,
        cardinality=cardinality,
        min_count=int(min_count) if str(min_count).isdigit() else 0,
        max_count=max_count,
    )
    # Optional parent
    parent_id = request.POST.get("parent_id")
    if parent_id and str(parent_id).isdigit():
        parent = CollectionDefinition.objects.filter(
            id=int(parent_id), survey=survey
        ).first()
        if parent:
            cd.parent = parent
    try:
        cd.full_clean()
    except Exception as e:
        messages.error(request, f"Invalid repeat configuration: {e}")
        return redirect("surveys:groups", slug=slug)
    cd.save()

    # Create items in the order provided
    # Keep current ordering of groups in the survey where possible
    order_index = 0
    for gid in gid_list:
        grp = survey.question_groups.filter(id=gid).first()
        if not grp:
            continue
        CollectionItem.objects.create(
            collection=cd,
            item_type=CollectionItem.ItemType.GROUP,
            group=grp,
            order=order_index,
        )
        order_index += 1

    # If we set a parent, add this as a child item under the parent
    if cd.parent_id:
        max_item_order = (
            CollectionItem.objects.filter(collection=cd.parent)
            .order_by("-order")
            .values_list("order", flat=True)
            .first()
        )
        next_idx = (max_item_order + 1) if max_item_order is not None else 0
        CollectionItem.objects.create(
            collection=cd.parent,
            item_type=CollectionItem.ItemType.COLLECTION,
            child_collection=cd,
            order=next_idx,
        )

    messages.success(request, "Repeat created and groups added.")
    return redirect("surveys:groups", slug=slug)


@login_required
@require_http_methods(["POST"])
def survey_group_repeat_remove(
    request: HttpRequest, slug: str, gid: int
) -> HttpResponse:
    """Remove the given group from any repeats (collections) in this survey.

    If a collection becomes empty after removal, delete it as well. This provides
    a simple toggle-like UX from the Groups page to undo a repeat association.
    """
    survey = get_object_or_404(Survey, slug=slug)
    require_can_edit(request.user, survey)
    group = get_object_or_404(QuestionGroup, id=gid)
    # Only allow removing if the group is attached to this survey
    if not survey.question_groups.filter(id=group.id).exists():
        return HttpResponse(status=404)

    # Remove items linking this group within this survey's collections
    items_qs = CollectionItem.objects.filter(
        collection__survey=survey, item_type=CollectionItem.ItemType.GROUP, group=group
    )
    affected_collections = set(items_qs.values_list("collection_id", flat=True))
    deleted, _ = items_qs.delete()

    # Re-number remaining items per affected collection and delete empties
    for cid in affected_collections:
        col = CollectionDefinition.objects.filter(id=cid, survey=survey).first()
        if not col:
            continue
        remaining = list(col.items.order_by("order", "id"))
        if not remaining:
            # If this collection is a child of a parent collection, remove its link too
            CollectionItem.objects.filter(child_collection=col).delete()
            col.delete()
            continue
        # Compact orders
        for idx, it in enumerate(remaining):
            if it.order != idx:
                it.order = idx
                it.save(update_fields=["order"])

    if deleted:
        messages.success(request, "Group removed from repeat.")
    else:
        messages.info(request, "This group was not part of a repeat.")
    return redirect("surveys:groups", slug=slug)


@login_required
@require_http_methods(["POST"])
def survey_groups_reorder(request: HttpRequest, slug: str) -> HttpResponse:
    survey = get_object_or_404(Survey, slug=slug)
    require_can_edit(request.user, survey)
    order_csv = request.POST.get("order", "")
    ids = [int(i) for i in order_csv.split(",") if i.isdigit()]
    # Filter to ids that belong to this survey
    # Only allow reordering groups that belong to this survey (owner may differ; permission handled above)
    valid_ids = set(
        survey.question_groups.filter(id__in=ids).values_list("id", flat=True)
    )
    ids = [i for i in ids if i in valid_ids]
    style = survey.style or {}
    style["group_order"] = ids
    survey.style = style
    survey.save(update_fields=["style"])
    messages.success(request, "Group order updated.")
    return redirect("surveys:groups", slug=slug)


@login_required
@require_http_methods(["GET", "POST"])
def org_users(request: HttpRequest, org_id: int) -> HttpResponse:
    User = get_user_model()
    org = get_object_or_404(Organization, id=org_id)
    if not can_manage_org_users(request.user, org):
        raise Http404
    # Admin can list and edit memberships (promote/demote within org, but not self-promote to superuser etc.)
    if request.method == "POST":
        action = request.POST.get("action")
        user_id = request.POST.get("user_id")
        email = (request.POST.get("email") or "").strip().lower()
        target_user = None
        if email:
            target_user = User.objects.filter(email__iexact=email).first()
        if not target_user and user_id:
            target_user = get_object_or_404(User, id=user_id)
        role = request.POST.get("role")
        if action == "add" and target_user:
            mem, created = OrganizationMembership.objects.update_or_create(
                organization=org,
                user=target_user,
                defaults={"role": role or OrganizationMembership.Role.VIEWER},
            )
            AuditLog.objects.create(
                actor=request.user,
                scope=AuditLog.Scope.ORGANIZATION,
                organization=org,
                action=AuditLog.Action.ADD if created else AuditLog.Action.UPDATE,
                target_user=target_user,
                metadata={"role": mem.role},
            )
            messages.success(request, "User added/updated in organization.")
        elif action == "update":
            mem = get_object_or_404(
                OrganizationMembership, organization=org, user=target_user
            )
            # Prevent self-demotion lockout: allow but warn (optional). For simplicity, allow update.
            if role in dict(OrganizationMembership.Role.choices):
                mem.role = role
                mem.save(update_fields=["role"])
                AuditLog.objects.create(
                    actor=request.user,
                    scope=AuditLog.Scope.ORGANIZATION,
                    organization=org,
                    action=AuditLog.Action.UPDATE,
                    target_user=mem.user,
                    metadata={"role": mem.role},
                )
                messages.success(request, "Membership updated.")
        elif action == "remove":
            mem = get_object_or_404(
                OrganizationMembership, organization=org, user=target_user
            )
            # Prevent self-removal if this is the last admin
            if (
                mem.user_id == request.user.id
                and mem.role == OrganizationMembership.Role.ADMIN
            ):
                messages.error(
                    request, "You cannot remove yourself as an organization admin."
                )
                return redirect("surveys:org_users", org_id=org.id)
            mem.delete()
            AuditLog.objects.create(
                actor=request.user,
                scope=AuditLog.Scope.ORGANIZATION,
                organization=org,
                action=AuditLog.Action.REMOVE,
                target_user=mem.user,
                metadata={"role": mem.role},
            )
            messages.success(request, "User removed from organization.")
        return redirect("surveys:org_users", org_id=org.id)

    members = (
        OrganizationMembership.objects.select_related("user")
        .filter(organization=org)
        .order_by("user__username")
    )
    return render(request, "surveys/org_users.html", {"org": org, "members": members})


@login_required
@require_http_methods(["GET", "POST"])
def survey_users(request: HttpRequest, slug: str) -> HttpResponse:
    User = get_user_model()
    survey = get_object_or_404(Survey, slug=slug)
    # Creator, org admin, or owner can manage; viewers can only view
    can_manage = can_manage_survey_users(request.user, survey)
    if not can_manage and not can_view_survey(request.user, survey):
        raise Http404

    if request.method == "POST":
        if not can_manage:
            return HttpResponse(status=403)
        action = request.POST.get("action")
        user_id = request.POST.get("user_id")
        email = (request.POST.get("email") or "").strip().lower()
        target_user = None
        if email:
            target_user = User.objects.filter(email__iexact=email).first()
        if not target_user and user_id:
            target_user = get_object_or_404(User, id=user_id)
        role = request.POST.get("role")
        if role and role not in dict(SurveyMembership.Role.choices):
            return HttpResponse(status=400)
        if action == "add" and target_user:
            smem, created = SurveyMembership.objects.update_or_create(
                survey=survey,
                user=target_user,
                defaults={"role": role or SurveyMembership.Role.VIEWER},
            )
            AuditLog.objects.create(
                actor=request.user,
                scope=AuditLog.Scope.SURVEY,
                survey=survey,
                action=AuditLog.Action.ADD if created else AuditLog.Action.UPDATE,
                target_user=target_user,
                metadata={"role": smem.role},
            )
            messages.success(request, "User added to survey.")
        elif action == "update":
            mem = get_object_or_404(SurveyMembership, survey=survey, user=target_user)
            # creators cannot promote to org admin here; only role is creator/viewer at survey level
            mem.role = role or SurveyMembership.Role.VIEWER
            mem.save(update_fields=["role"])
            AuditLog.objects.create(
                actor=request.user,
                scope=AuditLog.Scope.SURVEY,
                survey=survey,
                action=AuditLog.Action.UPDATE,
                target_user=mem.user,
                metadata={"role": mem.role},
            )
            messages.success(request, "Membership updated.")
        elif action == "remove":
            mem = get_object_or_404(SurveyMembership, survey=survey, user=target_user)
            mem.delete()
            AuditLog.objects.create(
                actor=request.user,
                scope=AuditLog.Scope.SURVEY,
                survey=survey,
                action=AuditLog.Action.REMOVE,
                target_user=mem.user,
                metadata={"role": mem.role},
            )
            messages.success(request, "User removed from survey.")
        return redirect("surveys:survey_users", slug=survey.slug)

    memberships = (
        SurveyMembership.objects.select_related("user")
        .filter(survey=survey)
        .order_by("user__username")
    )
    return render(
        request,
        "surveys/survey_users.html",
        {"survey": survey, "memberships": memberships, "can_manage": can_manage},
    )


@login_required
def user_management_hub(request: HttpRequest) -> HttpResponse:
    # Single organisation model: pick the organisation where user is ADMIN (or None)
    org = (
        Organization.objects.filter(
            memberships__user=request.user,
            memberships__role=OrganizationMembership.Role.ADMIN,
        )
        .select_related("owner")
        .first()
    )

    if request.method == "POST":
        # HTMX quick add flows
        scope = request.POST.get("scope")
        email = (request.POST.get("email") or "").strip().lower()
        role = request.POST.get("role")
        User = get_user_model()
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return HttpResponse("User not found by email", status=400)
        if scope == "org":
            if not org or not can_manage_org_users(request.user, org):
                return HttpResponse(status=403)
            mem, created = OrganizationMembership.objects.update_or_create(
                organization=org,
                user=user,
                defaults={"role": role or OrganizationMembership.Role.VIEWER},
            )
            AuditLog.objects.create(
                actor=request.user,
                scope=AuditLog.Scope.ORGANIZATION,
                organization=org,
                action=AuditLog.Action.ADD if created else AuditLog.Action.UPDATE,
                target_user=user,
                metadata={"role": mem.role},
            )
            return HttpResponse("Added/updated in org", status=200)
        elif scope == "survey":
            slug = request.POST.get("slug") or ""
            survey = get_object_or_404(Survey, slug=slug)
            if not can_manage_survey_users(request.user, survey):
                return HttpResponse(status=403)
            smem, created = SurveyMembership.objects.update_or_create(
                survey=survey,
                user=user,
                defaults={"role": role or SurveyMembership.Role.VIEWER},
            )
            AuditLog.objects.create(
                actor=request.user,
                scope=AuditLog.Scope.SURVEY,
                survey=survey,
                action=AuditLog.Action.ADD if created else AuditLog.Action.UPDATE,
                target_user=user,
                metadata={"role": smem.role},
            )
            return HttpResponse("Added/updated in survey", status=200)
    # Build users grouped by surveys for this organisation
    grouped = []
    manageable_surveys = Survey.objects.none()
    members = OrganizationMembership.objects.none()
    if org:
        members = (
            OrganizationMembership.objects.select_related("user")
            .filter(organization=org)
            .order_by("user__username")
        )
        manageable_surveys = (
            Survey.objects.filter(organization=org)
            .select_related("organization")
            .order_by("name")
        )
        for sv in manageable_surveys:
            sv_members = (
                SurveyMembership.objects.select_related("user")
                .filter(survey=sv)
                .order_by("user__username")
            )
            grouped.append({"survey": sv, "members": sv_members})

    return render(
        request,
        "surveys/user_management_hub.html",
        {"org": org, "members": members, "grouped": grouped},
    )


@login_required
@require_http_methods(["POST"])
def survey_group_create(request: HttpRequest, slug: str) -> HttpResponse:
    survey = get_object_or_404(Survey, slug=slug)
    require_can_edit(request.user, survey)
    name = request.POST.get("name", "").strip() or "New Group"
    g = QuestionGroup.objects.create(name=name, owner=request.user)
    survey.question_groups.add(g)
    messages.success(request, "Group created.")
    return redirect("surveys:dashboard", slug=slug)


@login_required
@require_http_methods(["POST"])
def survey_group_edit(request: HttpRequest, slug: str, gid: int) -> HttpResponse:
    survey = get_object_or_404(Survey, slug=slug)
    require_can_edit(request.user, survey)
    group = get_object_or_404(QuestionGroup, id=gid, surveys=survey)
    group.name = request.POST.get("name", group.name)
    group.description = request.POST.get("description", group.description)
    group.save(update_fields=["name", "description"])
    messages.success(request, "Group updated.")
    return redirect("surveys:dashboard", slug=slug)


@login_required
@require_http_methods(["POST"])
def survey_group_delete(request: HttpRequest, slug: str, gid: int) -> HttpResponse:
    survey = get_object_or_404(Survey, slug=slug)
    require_can_edit(request.user, survey)
    group = get_object_or_404(QuestionGroup, id=gid, surveys=survey)
    # Detach from this survey; optionally delete the group if not used elsewhere
    survey.question_groups.remove(group)
    if not group.surveys.exists():
        group.delete()
    messages.success(request, "Group deleted.")
    return redirect("surveys:dashboard", slug=slug)


@login_required
@require_http_methods(["POST"])
def survey_group_create_from_template(request: HttpRequest, slug: str) -> HttpResponse:
    survey = get_object_or_404(Survey, slug=slug)
    require_can_edit(request.user, survey)
    template = request.POST.get("template")
    if template == "patient_details_encrypted":
        g = QuestionGroup.objects.create(
            name="Patient details (encrypted)",
            description="Optional demographics captured securely.",
            owner=request.user,
            schema={
                "template": "patient_details_encrypted",
                # default initial selection per spec
                "fields": [
                    "first_name",
                    "surname",
                    "hospital_number",
                    "date_of_birth",
                ],
            },
        )
        survey.question_groups.add(g)
        messages.success(
            request,
            "Patient details group created. These fields will appear at the bottom of the participant form.",
        )
    elif template == "professional_details":
        g = QuestionGroup.objects.create(
            name="Professional details",
            description="Information about the professional.",
            owner=request.user,
            schema={
                "template": "professional_details",
                "fields": [
                    "title",
                    "first_name",
                    "surname",
                    "job_title",
                    "employing_trust",
                    "employing_health_board",
                    "integrated_care_board",
                    "nhs_england_region",
                    "country",
                    "gp_surgery",
                ],
                # ODS toggles per field
                "ods": {
                    "employing_trust": False,
                    "employing_health_board": False,
                    "integrated_care_board": False,
                    "gp_surgery": False,
                },
            },
        )
        survey.question_groups.add(g)
        messages.success(request, "Professional details group created.")
    else:
        messages.error(request, "Unknown template.")
    return redirect("surveys:groups", slug=slug)


@login_required
@require_http_methods(["GET", "POST"])
def survey_unlock(request: HttpRequest, slug: str) -> HttpResponse:
    survey = get_object_or_404(Survey, slug=slug, owner=request.user)
    if request.method == "POST":
        key = request.POST.get("key", "").encode("utf-8")
        if (
            survey.key_hash
            and survey.key_salt
            and verify_key(key, bytes(survey.key_hash), bytes(survey.key_salt))
        ):
            request.session["survey_key"] = key
            messages.success(request, "Survey unlocked for this session.")
            return redirect("surveys:dashboard", slug=slug)
        messages.error(request, "Invalid key.")
    return render(request, "surveys/unlock.html", {"survey": survey})


@login_required
def survey_export_csv(request: HttpRequest, slug: str) -> HttpResponse:
    survey = get_object_or_404(Survey, slug=slug, owner=request.user)
    if not request.session.get("survey_key"):
        messages.error(request, "Unlock survey first.")
        return redirect("surveys:unlock", slug=slug)

    def generate():
        import csv
        from io import StringIO

        header = ["id", "submitted_at", "answers"]
        s = StringIO()
        writer = csv.writer(s)
        writer.writerow(header)
        yield s.getvalue()
        s.seek(0)
        s.truncate(0)
        for r in survey.responses.iterator():
            writer.writerow([r.id, r.submitted_at.isoformat(), json.dumps(r.answers)])
            yield s.getvalue()
            s.seek(0)
            s.truncate(0)

    resp = StreamingHttpResponse(generate(), content_type="text/csv")
    resp["Content-Disposition"] = f"attachment; filename={slug}-responses.csv"
    return resp


# -------------------- Builder (HTMX/SSR) --------------------


@login_required
def group_builder(request: HttpRequest, slug: str, gid: int) -> HttpResponse:
    survey = get_object_or_404(Survey, slug=slug)
    require_can_edit(request.user, survey)
    group = get_object_or_404(QuestionGroup, id=gid, surveys=survey)
    questions = survey.questions.select_related("group").filter(group=group)
    _prepare_question_rendering(survey)
    patient_group, demographics_fields = _get_patient_group_and_fields(survey)
    show_patient_details = patient_group is not None
    include_imd = (
        bool((patient_group.schema or {}).get("include_imd"))
        if patient_group
        else False
    )
    prof_group, professional_fields, professional_ods = (
        _get_professional_group_and_fields(survey)
    )
    show_professional_details = prof_group is not None
    professional_ods_on = [k for k, v in (professional_ods or {}).items() if v]
    professional_ods_pairs = [
        {"key": k, "label": PROFESSIONAL_FIELD_DEFS[k], "on": bool(v)}
        for k, v in (professional_ods or {}).items()
    ]
    style = survey.style or {}
    brand_overrides = {
        "title": style.get("title"),
        "icon_url": style.get("icon_url"),
        "theme_name": style.get("theme_name"),
        "font_heading": style.get("font_heading"),
        "font_body": style.get("font_body"),
        "primary": style.get("primary_color"),
    }
    ctx = {
        "survey": survey,
        "group": group,
        "questions": questions,
        "show_patient_details": show_patient_details,
        "demographics_fields": demographics_fields,
        "demographic_defs": DEMOGRAPHIC_FIELD_DEFS,
        "demographics_fields_with_labels": [
            (k, DEMOGRAPHIC_FIELD_DEFS[k]) for k in demographics_fields
        ],
        "include_imd": include_imd,
        "show_professional_details": show_professional_details,
        "professional_fields": professional_fields,
        "professional_defs": PROFESSIONAL_FIELD_DEFS,
        "professional_ods": professional_ods,
        "professional_ods_on": professional_ods_on,
        "professional_ods_pairs": professional_ods_pairs,
    }
    if any(brand_overrides.values()):
        ctx["brand"] = {
            "title": brand_overrides.get("title")
            or getattr(settings, "BRAND_TITLE", "Census"),
            "icon_url": brand_overrides.get("icon_url")
            or getattr(settings, "BRAND_ICON_URL", "/static/favicon.ico"),
            "theme_name": brand_overrides.get("theme_name")
            or getattr(settings, "BRAND_THEME", "census"),
            "font_heading": brand_overrides.get("font_heading")
            or getattr(
                settings,
                "BRAND_FONT_HEADING",
                "'IBM Plex Sans', ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, 'Apple Color Emoji', 'Segoe UI Emoji'",
            ),
            "font_body": brand_overrides.get("font_body")
            or getattr(
                settings,
                "BRAND_FONT_BODY",
                "Merriweather, ui-serif, Georgia, Cambria, 'Times New Roman', Times, serif",
            ),
            "font_css_url": getattr(
                settings,
                "BRAND_FONT_CSS_URL",
                "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600;700&family=Merriweather:wght@300;400;700&display=swap",
            ),
            "primary": brand_overrides.get("primary"),
        }
    return render(
        request,
        "surveys/group_builder.html",
        ctx,
    )


@login_required
@require_http_methods(["POST"])
def builder_demographics_update(request: HttpRequest, slug: str) -> HttpResponse:
    survey = get_object_or_404(Survey, slug=slug)
    require_can_edit(request.user, survey)
    group = survey.question_groups.filter(
        schema__template="patient_details_encrypted"
    ).first()
    if not group:
        raise Http404
    selected = request.POST.getlist("fields")
    allowed = [k for k in selected if k in DEMOGRAPHIC_FIELD_DEFS]
    schema = group.schema or {}
    schema["fields"] = allowed
    # include_imd only applies when post_code is selected
    include_imd_flag = request.POST.get("include_imd") in ("on", "true", "1")
    if "post_code" in allowed:
        schema["include_imd"] = bool(include_imd_flag)
    else:
        schema["include_imd"] = False
    group.schema = schema
    group.save(update_fields=["schema"])

    # Re-render the partial for the builder preview
    _, demographics_fields = _get_patient_group_and_fields(survey)
    include_imd = bool((group.schema or {}).get("include_imd"))
    return render(
        request,
        "surveys/partials/demographics_builder.html",
        {
            "survey": survey,
            "show_patient_details": True,
            "demographics_fields": demographics_fields,
            "demographic_defs": DEMOGRAPHIC_FIELD_DEFS,
            "include_imd": include_imd,
        },
    )


@login_required
@require_http_methods(["POST"])
def builder_professional_update(request: HttpRequest, slug: str) -> HttpResponse:
    survey = get_object_or_404(Survey, slug=slug)
    require_can_edit(request.user, survey)
    group = survey.question_groups.filter(
        schema__template="professional_details"
    ).first()
    if not group:
        raise Http404
    selected = request.POST.getlist("fields")
    allowed = [k for k in selected if k in PROFESSIONAL_FIELD_DEFS]
    schema = group.schema or {}
    schema["fields"] = allowed
    # ODS toggles per field
    new_ods: dict[str, bool] = {}
    for k in PROFESSIONAL_ODS_FIELDS:
        if k in allowed:
            new_ods[k] = request.POST.get(f"ods_{k}") in ("on", "true", "1")
        else:
            new_ods[k] = False
    schema["ods"] = new_ods
    group.schema = schema
    group.save(update_fields=["schema"])

    # Re-render the partial for the builder preview
    _, professional_fields, professional_ods = _get_professional_group_and_fields(
        survey
    )
    professional_ods_on = [k for k, v in (professional_ods or {}).items() if v]
    professional_ods_pairs = [
        {"key": k, "label": PROFESSIONAL_FIELD_DEFS[k], "on": bool(v)}
        for k, v in (professional_ods or {}).items()
    ]
    return render(
        request,
        "surveys/partials/professional_builder.html",
        {
            "survey": survey,
            "show_professional_details": True,
            "professional_fields": professional_fields,
            "professional_defs": PROFESSIONAL_FIELD_DEFS,
            "professional_ods": professional_ods,
            "professional_ods_on": professional_ods_on,
            "professional_ods_pairs": professional_ods_pairs,
        },
    )


@login_required
@require_http_methods(["POST"])
def builder_question_create(request: HttpRequest, slug: str) -> HttpResponse:
    survey = get_object_or_404(Survey, slug=slug)
    require_can_edit(request.user, survey)
    text = request.POST.get("text", "").strip()
    qtype = request.POST.get("type", "text")
    required = request.POST.get("required") == "on"
    options_raw = request.POST.get("options", "").strip()
    group_id = request.POST.get("group_id")
    group = (
        QuestionGroup.objects.filter(id=group_id, owner=request.user).first()
        if group_id
        else None
    )
    options: list[str] = []
    # Process per-type extra fields
    if qtype in {"mc_single", "mc_multi", "dropdown", "orderable", "image"}:
        options = (
            [o.strip() for o in options_raw.splitlines() if o.strip()]
            if options_raw
            else []
        )
    elif qtype == "likert":
        likert_mode = request.POST.get("likert_mode", "categories")
        if likert_mode == "categories":
            cats_raw = request.POST.get("likert_categories", "").strip()
            options = (
                [o.strip() for o in cats_raw.splitlines() if o.strip()]
                if cats_raw
                else []
            )
        else:
            # number scale captured as [min, max, left_label, right_label]
            try:
                min_v = int(request.POST.get("likert_min", "1"))
                max_v = int(request.POST.get("likert_max", "5"))
            except ValueError:
                min_v, max_v = 1, 5
            left_label = request.POST.get("likert_left_label", "")
            right_label = request.POST.get("likert_right_label", "")
            options = [
                {
                    "type": "number-scale",
                    "min": min_v,
                    "max": max_v,
                    "left": left_label,
                    "right": right_label,
                }
            ]
    elif qtype == "text":
        # store text format hint in options for downstream rendering
        text_format = request.POST.get("text_format", "free")
        options = [{"type": "text", "format": text_format}]
    order = (survey.questions.aggregate(models.Max("order")).get("order__max") or 0) + 1
    SurveyQuestion.objects.create(
        survey=survey,
        group=group,
        text=text or "Untitled",
        type=qtype,
        options=options,
        required=required,
        order=order,
    )
    questions = survey.questions.select_related("group").all()
    _prepare_question_rendering(survey)
    groups = survey.question_groups.filter(owner=request.user)
    return render(
        request,
        "surveys/partials/questions_list.html",
        {
            "survey": survey,
            "questions": questions,
            "groups": groups,
            "message": "Question created.",
        },
    )


@login_required
@require_http_methods(["POST"])
def builder_group_question_create(
    request: HttpRequest, slug: str, gid: int
) -> HttpResponse:
    survey = get_object_or_404(Survey, slug=slug)
    require_can_edit(request.user, survey)
    group = get_object_or_404(QuestionGroup, id=gid, surveys=survey)
    text = request.POST.get("text", "").strip()
    qtype = request.POST.get("type", "text")
    required = request.POST.get("required") == "on"
    options_raw = request.POST.get("options", "").strip()
    options: list[str] = []
    if qtype in {"mc_single", "mc_multi", "dropdown", "orderable", "image"}:
        options = (
            [o.strip() for o in options_raw.splitlines() if o.strip()]
            if options_raw
            else []
        )
    elif qtype == "likert":
        likert_mode = request.POST.get("likert_mode", "categories")
        if likert_mode == "categories":
            cats_raw = request.POST.get("likert_categories", "").strip()
            options = (
                [o.strip() for o in cats_raw.splitlines() if o.strip()]
                if cats_raw
                else []
            )
        else:
            try:
                min_v = int(request.POST.get("likert_min", "1"))
                max_v = int(request.POST.get("likert_max", "5"))
            except ValueError:
                min_v, max_v = 1, 5
            left_label = request.POST.get("likert_left_label", "")
            right_label = request.POST.get("likert_right_label", "")
            options = [
                {
                    "type": "number-scale",
                    "min": min_v,
                    "max": max_v,
                    "left": left_label,
                    "right": right_label,
                }
            ]
    elif qtype == "text":
        text_format = request.POST.get("text_format", "free")
        options = [{"type": "text", "format": text_format}]
    order = (survey.questions.aggregate(models.Max("order")).get("order__max") or 0) + 1
    SurveyQuestion.objects.create(
        survey=survey,
        group=group,
        text=text or "Untitled",
        type=qtype,
        options=options,
        required=required,
        order=order,
    )
    questions = survey.questions.select_related("group").filter(group=group)
    _prepare_question_rendering(survey)
    return render(
        request,
        "surveys/partials/questions_list_group.html",
        {
            "survey": survey,
            "group": group,
            "questions": questions,
            "message": "Question created.",
        },
    )


@login_required
@require_http_methods(["POST"])
def builder_question_edit(request: HttpRequest, slug: str, qid: int) -> HttpResponse:
    survey = get_object_or_404(Survey, slug=slug)
    require_can_edit(request.user, survey)
    q = get_object_or_404(SurveyQuestion, id=qid, survey=survey)
    q.text = request.POST.get("text", q.text)
    q.type = request.POST.get("type", q.type)
    q.required = request.POST.get("required") == "on"
    options_raw = request.POST.get("options", "").strip()
    q.options = (
        [o.strip() for o in options_raw.splitlines() if o.strip()]
        if options_raw
        else []
    )
    group_id = request.POST.get("group_id")
    q.group = (
        QuestionGroup.objects.filter(id=group_id, owner=request.user).first()
        if group_id
        else None
    )
    q.save()
    # Refresh and prepare rendering helpers
    _prepare_question_rendering(survey)
    groups = QuestionGroup.objects.filter(owner=request.user)
    return render(
        request, "surveys/partials/question_row.html", {"q": q, "groups": groups}
    )


@login_required
@require_http_methods(["POST"])
def builder_group_question_edit(
    request: HttpRequest, slug: str, gid: int, qid: int
) -> HttpResponse:
    survey = get_object_or_404(Survey, slug=slug)
    require_can_edit(request.user, survey)
    group = get_object_or_404(QuestionGroup, id=gid, surveys=survey)
    q = get_object_or_404(SurveyQuestion, id=qid, survey=survey, group=group)
    q.text = request.POST.get("text", q.text)
    q.type = request.POST.get("type", q.type)
    q.required = request.POST.get("required") == "on"
    options_raw = request.POST.get("options", "").strip()
    q.options = (
        [o.strip() for o in options_raw.splitlines() if o.strip()]
        if options_raw
        else []
    )
    q.save()
    _prepare_question_rendering(survey)
    return render(request, "surveys/partials/question_row.html", {"q": q})


@login_required
@require_http_methods(["POST"])
def builder_question_delete(request: HttpRequest, slug: str, qid: int) -> HttpResponse:
    survey = get_object_or_404(Survey, slug=slug)
    require_can_edit(request.user, survey)
    q = get_object_or_404(SurveyQuestion, id=qid, survey=survey)
    q.delete()
    questions = survey.questions.select_related("group").all()
    _prepare_question_rendering(survey)
    groups = survey.question_groups.filter(owner=request.user)
    return render(
        request,
        "surveys/partials/questions_list.html",
        {
            "survey": survey,
            "questions": questions,
            "groups": groups,
            "message": "Question deleted.",
        },
    )


@login_required
@require_http_methods(["POST"])
def builder_group_question_delete(
    request: HttpRequest, slug: str, gid: int, qid: int
) -> HttpResponse:
    survey = get_object_or_404(Survey, slug=slug)
    require_can_edit(request.user, survey)
    group = get_object_or_404(QuestionGroup, id=gid, surveys=survey)
    q = get_object_or_404(SurveyQuestion, id=qid, survey=survey, group=group)
    q.delete()
    questions = survey.questions.select_related("group").filter(group=group)
    _prepare_question_rendering(survey)
    return render(
        request,
        "surveys/partials/questions_list_group.html",
        {
            "survey": survey,
            "group": group,
            "questions": questions,
            "message": "Question deleted.",
        },
    )


@login_required
@require_http_methods(["POST"])
def builder_questions_reorder(request: HttpRequest, slug: str) -> HttpResponse:
    survey = get_object_or_404(Survey, slug=slug)
    require_can_edit(request.user, survey)
    order_csv = request.POST.get("order", "")  # expects comma-separated ids
    ids = [int(i) for i in order_csv.split(",") if i.isdigit()]
    for idx, qid in enumerate(ids):
        SurveyQuestion.objects.filter(id=qid, survey=survey).update(order=idx)
    questions = survey.questions.select_related("group").all()
    _prepare_question_rendering(survey)
    groups = survey.question_groups.filter(owner=request.user)
    return render(
        request,
        "surveys/partials/questions_list.html",
        {
            "survey": survey,
            "questions": questions,
            "groups": groups,
            "message": "Order updated.",
        },
    )


@login_required
@require_http_methods(["POST"])
def builder_group_questions_reorder(
    request: HttpRequest, slug: str, gid: int
) -> HttpResponse:
    survey = get_object_or_404(Survey, slug=slug)
    require_can_edit(request.user, survey)
    group = get_object_or_404(QuestionGroup, id=gid, surveys=survey)
    order_csv = request.POST.get("order", "")
    ids = [int(i) for i in order_csv.split(",") if i.isdigit()]
    for idx, qid in enumerate(ids):
        SurveyQuestion.objects.filter(id=qid, survey=survey, group=group).update(
            order=idx
        )
    questions = survey.questions.select_related("group").filter(group=group)
    _prepare_question_rendering(survey)
    return render(
        request,
        "surveys/partials/questions_list_group.html",
        {
            "survey": survey,
            "group": group,
            "questions": questions,
            "message": "Order updated.",
        },
    )


@login_required
@require_http_methods(["POST"])
def builder_group_create(request: HttpRequest, slug: str) -> HttpResponse:
    survey = get_object_or_404(Survey, slug=slug)
    require_can_edit(request.user, survey)
    name = request.POST.get("name", "").strip() or "New Group"
    g = QuestionGroup.objects.create(name=name, owner=request.user)
    questions = survey.questions.select_related("group").all()
    _prepare_question_rendering(survey)
    survey.question_groups.add(g)
    groups = survey.question_groups.filter(owner=request.user)
    return render(
        request,
        "surveys/partials/questions_list.html",
        {"survey": survey, "questions": questions, "groups": groups},
    )


@login_required
def bulk_upload(request: HttpRequest, slug: str) -> HttpResponse:
    survey = get_object_or_404(Survey, slug=slug)
    require_can_edit(request.user, survey)
    context = {"survey": survey, "example": _bulk_upload_example_md()}
    if request.method == "POST":
        md = request.POST.get("markdown", "")
        try:
            parsed = parse_bulk_markdown_with_collections(md)
        except BulkParseError as e:
            context["error"] = str(e)
            context["markdown"] = md
            return render(request, "surveys/bulk_upload.html", context)

        # Create groups and questions
        max_order = (
            survey.questions.aggregate(models.Max("order")).get("order__max") or 0
        )
        next_order = max_order + 1
        created_groups_in_order: list[QuestionGroup] = []
        for g in parsed["groups"]:
            grp = QuestionGroup.objects.create(
                name=g["name"], description=g.get("description", ""), owner=request.user
            )
            survey.question_groups.add(grp)
            created_groups_in_order.append(grp)
            for q in g["questions"]:
                SurveyQuestion.objects.create(
                    survey=survey,
                    group=grp,
                    text=q["title"],
                    type=q["final_type"],
                    options=q["final_options"],
                    required=False,
                    order=next_order,
                )
                next_order += 1

        # Build collections from simple REPEAT markers
        repeats = parsed.get("repeats") or []
        created_collections = 0
        created_items = 0

        # Helper to ensure unique key per survey
        def _unique_key(base: str) -> str:
            k = slugify(base)
            if not k:
                k = "collection"
            candidate = k
            i = 2
            while CollectionDefinition.objects.filter(
                survey=survey, key=candidate
            ).exists():
                candidate = f"{k}-{i}"
                i += 1
            return candidate

        defs_by_group_index: dict[int, CollectionDefinition] = {}
        for rep in repeats:
            gi = int(rep.get("group_index"))
            max_count = rep.get("max_count")
            name = (
                created_groups_in_order[gi].name
                if gi < len(created_groups_in_order)
                else parsed["groups"][gi]["name"]
            )
            key = _unique_key(name)
            cardinality = (
                CollectionDefinition.Cardinality.ONE
                if (isinstance(max_count, int) and max_count == 1)
                else CollectionDefinition.Cardinality.MANY
            )
            cd = CollectionDefinition.objects.create(
                survey=survey,
                key=key,
                name=name,
                cardinality=cardinality,
                max_count=max_count,
            )
            defs_by_group_index[gi] = cd
            created_collections += 1

        # Link parents now that all defs exist
        for rep in repeats:
            gi = int(rep.get("group_index"))
            parent_index = rep.get("parent_index")
            if parent_index is not None:
                child_cd = defs_by_group_index.get(gi)
                parent_cd = defs_by_group_index.get(int(parent_index))
                if child_cd and parent_cd and child_cd.parent_id != parent_cd.id:
                    child_cd.parent = parent_cd
                    child_cd.full_clean()
                    child_cd.save(update_fields=["parent"])

        # Create items for each collection: its own group first, then any direct child collections
        # Preserve child order according to appearance in repeats
        for gi, cd in defs_by_group_index.items():
            order = 0
            if gi < len(created_groups_in_order):
                grp = created_groups_in_order[gi]
                CollectionItem.objects.create(
                    collection=cd,
                    item_type=CollectionItem.ItemType.GROUP,
                    group=grp,
                    order=order,
                )
                created_items += 1
                order += 1
            # children
            for rep in repeats:
                if rep.get("parent_index") == gi:
                    child_cd = defs_by_group_index.get(int(rep["group_index"]))
                    if child_cd:
                        # Ensure the parent/child relation is set
                        if child_cd.parent_id != cd.id:
                            child_cd.parent = cd
                            child_cd.full_clean()
                            child_cd.save(update_fields=["parent"])
                        CollectionItem.objects.create(
                            collection=cd,
                            item_type=CollectionItem.ItemType.COLLECTION,
                            child_collection=child_cd,
                            order=order,
                        )
                        created_items += 1
                        order += 1

        messages.success(
            request,
            (
                f"Bulk upload successful: added {len(parsed['groups'])} group(s) and questions."
                + (
                    f" Also created {created_collections} collection(s) and {created_items} item(s)."
                    if repeats
                    else ""
                )
            ),
        )
        return redirect("surveys:dashboard", slug=survey.slug)
    return render(request, "surveys/bulk_upload.html", context)


def _bulk_upload_example_md() -> str:
    return (
        "REPEAT-5\n"
        "# Patient\n"
        "Basic info about respondents\n\n"
        "## Age\n"
        "Age in years\n"
        "(text number)\n\n"
        "## Gender\n"
        "Self-described gender\n"
        "(mc_single)\n"
        "- Female\n"
        "- Male\n"
        "- Non-binary\n"
        "- Prefer not to say\n\n"
        "> REPEAT\n"
        "> # Visit\n"
        "> Details about each visit\n\n"
        "> ## Date of visit\n"
        "> (text)\n\n"
        "# Satisfaction\n"
        "About the service\n\n"
        "## Overall satisfaction\n"
        "Rate from 1 to 5\n"
        "(likert number)\n"
        "min: 1\n"
        "max: 5\n"
        "left: Very poor\n"
        "right: Excellent\n\n"
        "## Recommend to a friend\n"
        "Likelihood to recommend\n"
        "(likert categories)\n"
        "- Very unlikely\n"
        "- Unlikely\n"
        "- Neutral\n"
        "- Likely\n"
        "- Very likely\n"
    )
