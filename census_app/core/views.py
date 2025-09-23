from pathlib import Path

import markdown as mdlib
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect, render

from census_app.surveys.models import (
    Organization,
    OrganizationMembership,
    QuestionGroup,
    Survey,
    SurveyAccessToken,
    SurveyMembership,
    SurveyResponse,
)

from .forms import SignupForm

try:
    from .models import SiteBranding
except ImportError:
    SiteBranding = None

try:
    from .theme_utils import normalize_daisyui_builder_css
except ImportError:

    def normalize_daisyui_builder_css(s: str) -> str:
        """No-op fallback if theme utils or migrations are unavailable."""
        return s


def home(request):
    return render(request, "core/home.html")


@login_required
def profile(request):
    sb = None
    if request.method == "POST" and request.POST.get("action") == "upgrade_to_org":
        # Create a new organisation owned by this user, and make them ADMIN
        with transaction.atomic():
            org_name = (
                request.POST.get("org_name")
                or f"{request.user.username}'s Organisation"
            )
            org = Organization.objects.create(name=org_name, owner=request.user)
            OrganizationMembership.objects.get_or_create(
                organization=org,
                user=request.user,
                defaults={"role": OrganizationMembership.Role.ADMIN},
            )
        messages.success(
            request,
            "Organisation created. You are now an organisation admin and can host surveys and build a team.",
        )
        return redirect("surveys:org_users", org_id=org.id)
    if request.method == "POST" and request.POST.get("action") == "update_branding":
        if not request.user.is_superuser:
            return redirect("core:profile")
        if SiteBranding is not None:
            sb, _ = SiteBranding.objects.get_or_create(pk=1)
            sb.default_theme = request.POST.get("default_theme") or sb.default_theme
            sb.icon_url = (request.POST.get("icon_url") or "").strip()
            if request.FILES.get("icon_file"):
                sb.icon_file = request.FILES["icon_file"]
            # Dark icon fields
            sb.icon_url_dark = (request.POST.get("icon_url_dark") or "").strip()
            if request.FILES.get("icon_file_dark"):
                sb.icon_file_dark = request.FILES["icon_file_dark"]
            sb.font_heading = (request.POST.get("font_heading") or "").strip()
            sb.font_body = (request.POST.get("font_body") or "").strip()
            sb.font_css_url = (request.POST.get("font_css_url") or "").strip()
            raw_light = request.POST.get("theme_light_css") or ""
            raw_dark = request.POST.get("theme_dark_css") or ""
            sb.theme_light_css = normalize_daisyui_builder_css(raw_light)
            sb.theme_dark_css = normalize_daisyui_builder_css(raw_dark)
            sb.save()
            messages.success(request, "Project theme saved.")
        return redirect("core:profile")
    if SiteBranding is not None and sb is None:
        try:
            sb = SiteBranding.objects.first()
        except Exception:
            sb = None
    # Lightweight stats for badges
    user = request.user
    # Pick a primary organisation if present: prefer one the user owns; else first membership
    primary_owned_org = Organization.objects.filter(owner=user).first()
    first_membership = (
        OrganizationMembership.objects.filter(user=user)
        .select_related("organization")
        .first()
    )
    org = primary_owned_org or (
        first_membership.organization if first_membership else None
    )
    stats = {
        "is_superuser": getattr(user, "is_superuser", False),
        "is_staff": getattr(user, "is_staff", False),
        "orgs_owned": Organization.objects.filter(owner=user).count(),
        "org_admin_count": OrganizationMembership.objects.filter(
            user=user, role=OrganizationMembership.Role.ADMIN
        ).count(),
        "org_memberships": OrganizationMembership.objects.filter(user=user).count(),
        "surveys_owned": Survey.objects.filter(owner=user).count(),
        "survey_creator_count": SurveyMembership.objects.filter(
            user=user, role=SurveyMembership.Role.CREATOR
        ).count(),
        "survey_viewer_count": SurveyMembership.objects.filter(
            user=user, role=SurveyMembership.Role.VIEWER
        ).count(),
        "groups_owned": QuestionGroup.objects.filter(owner=user).count(),
        "responses_submitted": SurveyResponse.objects.filter(submitted_by=user).count(),
        "tokens_created": SurveyAccessToken.objects.filter(created_by=user).count(),
    }
    return render(request, "core/profile.html", {"sb": sb, "stats": stats, "org": org})


def signup(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            account_type = request.POST.get("account_type")
            if account_type == "org":
                with transaction.atomic():
                    org_name = (
                        request.POST.get("org_name")
                        or f"{user.username}'s Organisation"
                    )
                    org = Organization.objects.create(name=org_name, owner=user)
                    OrganizationMembership.objects.create(
                        organization=org,
                        user=user,
                        role=OrganizationMembership.Role.ADMIN,
                    )
                messages.success(
                    request, "Organisation created. You are an organisation admin."
                )
                return redirect("surveys:org_users", org_id=org.id)
            return redirect("core:home")
    else:
        form = SignupForm()
    return render(request, "registration/signup.html", {"form": form})


# --- Documentation views ---
DOCS_DIR = Path(__file__).resolve().parent.parent.parent / "docs"

DOC_PAGES = {
    "index": "README.md",
    "getting-started": "getting-started.md",
    "getting-started-api": "getting-started-api.md",
    "authentication-and-permissions": "authentication-and-permissions.md",
    "api": "api.md",
    "branding-and-theme-settings": "branding-and-theme-settings.md",
    "themes": "themes.md",
    "surveys": "surveys.md",
    "publish-and-collection": "publish-and-collection.md",
    "user-management": "user-management.md",
    "collections": "collections.md",
    "groups-view": "groups-view.md",
    "releases": "releases.md",
}


def _doc_title(slug: str) -> str:
    # Convert slug to Title Case words (e.g., "getting-started" -> "Getting Started")
    return " ".join(part.capitalize() for part in slug.replace("_", "-").split("-"))


def _nav_pages():
    return [
        {"slug": s, "title": _doc_title(s)} for s in DOC_PAGES.keys() if s != "index"
    ]


def docs_index(request):
    """Render docs index from docs/README.md with a simple TOC."""
    index_file = DOCS_DIR / DOC_PAGES["index"]
    if not index_file.exists():
        raise Http404("Documentation not found")
    html = mdlib.markdown(
        index_file.read_text(encoding="utf-8"),
        extensions=["fenced_code", "tables", "toc"],
    )
    return render(
        request,
        "core/docs.html",
        {"html": html, "active_slug": "index", "pages": _nav_pages()},
    )


def docs_page(request, slug: str):
    """Render a specific documentation page by slug mapped to a whitelisted file."""
    if slug not in DOC_PAGES:
        raise Http404("Page not found")
    file_path = DOCS_DIR / DOC_PAGES[slug]
    if not file_path.exists():
        raise Http404("Page not found")
    html = mdlib.markdown(
        file_path.read_text(encoding="utf-8"),
        extensions=["fenced_code", "tables", "toc"],
    )
    return render(
        request,
        "core/docs.html",
        {"html": html, "active_slug": slug, "pages": _nav_pages()},
    )
