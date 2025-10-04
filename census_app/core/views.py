from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, views as auth_views
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
import markdown as mdlib

from census_app.surveys.models import (
    Organization,
    OrganizationMembership,
    QuestionGroup,
    Survey,
    SurveyAccessToken,
    SurveyMembership,
    SurveyResponse,
)

from .forms import SignupForm, UserEmailPreferencesForm

try:
    from .models import SiteBranding, UserEmailPreferences
except ImportError:
    SiteBranding = None
    UserEmailPreferences = None

try:
    from .theme_utils import normalize_daisyui_builder_css
except ImportError:

    def normalize_daisyui_builder_css(s: str) -> str:
        """No-op fallback if theme utils or migrations are unavailable."""
        return s


def home(request):
    return render(request, "core/home.html")


def healthz(request):
    """Lightweight health endpoint for load balancers and readiness probes.
    Returns 200 OK without auth or redirects.
    """
    return HttpResponse("ok", content_type="text/plain")


@login_required
def profile(request):
    sb = None
    # Handle email preferences form submission
    if request.method == "POST" and request.POST.get("action") == "update_email_prefs":
        if UserEmailPreferences is not None:
            prefs = UserEmailPreferences.get_or_create_for_user(request.user)
            form = UserEmailPreferencesForm(request.POST, instance=prefs)
            if form.is_valid():
                form.save()
                messages.success(request, "Email preferences updated successfully.")
            else:
                messages.error(
                    request, "There was an error updating your email preferences."
                )
        return redirect("core:profile")
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
    # Prepare email preferences form
    email_prefs_form = None
    if UserEmailPreferences is not None:
        prefs = UserEmailPreferences.get_or_create_for_user(user)
        email_prefs_form = UserEmailPreferencesForm(instance=prefs)
    return render(
        request,
        "core/profile.html",
        {
            "sb": sb,
            "stats": stats,
            "org": org,
            "email_prefs_form": email_prefs_form,
        },
    )


def signup(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            # With multiple AUTHENTICATION_BACKENDS configured (e.g., ModelBackend + Axes),
            # login() requires an explicit backend unless the user was authenticated via authenticate().
            # Since we just created the user, log them in using the default ModelBackend.
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")

            # Send welcome email
            try:
                from .email_utils import send_welcome_email
                send_welcome_email(user)
            except Exception as e:
                # Don't block signup if email fails
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send welcome email to {user.username}: {e}")

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
# Resolve project root (repository root). In some production builds the module path
# can point into site-packages; prefer settings.BASE_DIR (project/census_app) and
# then step up one directory to reach the repo root containing manage.py and docs/.
def _resolve_repo_root() -> Path:
    candidates = [
        Path(getattr(settings, "BASE_DIR", Path(__file__).resolve().parent.parent))
    ]
    # Prefer the parent of BASE_DIR as the repository root (where manage.py lives)
    candidates.append(candidates[0].parent)
    # Also consider the path derived from this file (source tree execution)
    candidates.append(Path(__file__).resolve().parent.parent.parent)
    # Pick the first candidate that contains a docs directory or a manage.py file
    for c in candidates:
        if (c / "docs").is_dir() or (c / "manage.py").exists():
            return c
    # Fallback to the first candidate
    return candidates[0]


REPO_ROOT = _resolve_repo_root()
DOCS_DIR = REPO_ROOT / "docs"


def _doc_title(slug: str) -> str:
    """Convert slug to Title Case words (e.g., 'getting-started' -> 'Getting Started')."""
    return " ".join(part.capitalize() for part in slug.replace("_", "-").split("-"))


# Category definitions for organizing documentation
# Each category can have an optional icon and display order
DOC_CATEGORIES = {
    "getting-started": {
        "title": "Getting Started",
        "order": 1,
        "icon": "📚",
    },
    "features": {
        "title": "Features",
        "order": 2,
        "icon": "✨",
    },
    "configuration": {
        "title": "Configuration",
        "order": 3,
        "icon": "⚙️",
    },
    "api": {
        "title": "API & Development",
        "order": 4,
        "icon": "🔧",
    },
    "advanced": {
        "title": "Advanced Topics",
        "order": 5,
        "icon": "🚀",
    },
    "other": {
        "title": "Other",
        "order": 99,
        "icon": "📄",
    },
}

# Manual overrides for specific files (optional)
# If a file isn't listed here, it will be auto-discovered
# Format: "slug": {"file": "filename.md", "category": "category-key", "title": "Custom Title"}
DOC_PAGE_OVERRIDES = {
    "index": {"file": "README.md", "category": None},  # Special: index page
    "contributing": {"file": REPO_ROOT / "CONTRIBUTING.md", "category": "other"},
}


def _discover_doc_pages():
    """
    Auto-discover all markdown files in docs/ directory and organize by category.

    Returns a dict mapping slug -> file path, and a categorized structure for navigation.
    """
    pages = {}
    categorized = {cat: [] for cat in DOC_CATEGORIES.keys()}

    # First, add manual overrides
    for slug, config in DOC_PAGE_OVERRIDES.items():
        file_path = config["file"]
        if isinstance(file_path, str):
            file_path = DOCS_DIR / file_path
        pages[slug] = file_path

        # Add to category if specified
        category = config.get("category")
        if category and category in categorized:
            categorized[category].append(
                {
                    "slug": slug,
                    "title": config.get("title") or _doc_title(slug),
                    "file": file_path,
                }
            )

    # Auto-discover markdown files in docs/
    if DOCS_DIR.exists():
        for md_file in sorted(DOCS_DIR.glob("*.md")):
            # Skip README.md as it's the index
            if md_file.name == "README.md":
                continue

            # Generate slug from filename
            slug = md_file.stem

            # Skip if already manually configured
            if slug in pages:
                continue

            # Determine category by filename patterns
            category = _infer_category(slug)

            # Extract title from file (first H1) or use slug
            title = _extract_title_from_file(md_file) or _doc_title(slug)

            pages[slug] = md_file
            categorized[category].append(
                {
                    "slug": slug,
                    "title": title,
                    "file": md_file,
                }
            )

    return pages, categorized


def _infer_category(slug: str) -> str:
    """Infer category from slug/filename patterns."""
    slug_lower = slug.lower()

    # Getting Started
    if any(x in slug_lower for x in ["getting-started", "quickstart", "setup"]):
        return "getting-started"

    # Features
    if any(
        x in slug_lower
        for x in ["surveys", "collections", "groups", "import", "publish"]
    ):
        return "features"

    # Configuration
    if any(
        x in slug_lower
        for x in [
            "branding",
            "theme",
            "user-management",
            "prefilled-datasets-setup",
            "email",
            "notifications",
        ]
    ):
        return "configuration"

    # API & Development
    if any(
        x in slug_lower for x in ["api", "authentication", "adding-", "development"]
    ):
        return "api"

    # Advanced
    if any(x in slug_lower for x in ["advanced", "custom", "extend"]):
        return "advanced"

    # Default
    return "other"


def _extract_title_from_file(file_path: Path) -> str | None:
    """Extract title from first # heading in markdown file."""
    try:
        content = file_path.read_text(encoding="utf-8")
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
    except Exception:
        pass
    return None


# Build the pages dict and categorized structure
DOC_PAGES, DOC_CATEGORIES_WITH_PAGES = _discover_doc_pages()


def _nav_pages():
    """
    Return categorized navigation structure for documentation.

    Returns a list of categories with their pages.
    """
    nav = []

    for cat_key, pages_list in DOC_CATEGORIES_WITH_PAGES.items():
        if not pages_list:  # Skip empty categories
            continue

        cat_info = DOC_CATEGORIES.get(cat_key, {"title": cat_key.title(), "order": 99})

        nav.append(
            {
                "key": cat_key,
                "title": cat_info.get("title", cat_key.title()),
                "icon": cat_info.get("icon", ""),
                "order": cat_info.get("order", 99),
                "pages": sorted(pages_list, key=lambda p: p["title"]),
            }
        )

    # Sort categories by order
    nav.sort(key=lambda c: c["order"])

    return nav


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
    """Render a specific documentation page by slug."""
    if slug not in DOC_PAGES:
        raise Http404("Page not found")

    # DOC_PAGES values are already Path objects from _discover_doc_pages
    file_path = DOC_PAGES[slug]

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


class BrandedPasswordResetView(auth_views.PasswordResetView):
    """Password reset view that ensures brand context is available to email templates.

    We pass extra_email_context on each request so templates like
    registration/password_reset_subject.txt can use {{ brand.title }}.
    Additionally, we ensure an HTML alternative is attached via
    html_email_template_name.
    """

    template_name = "registration/password_reset_form.html"
    subject_template_name = "registration/password_reset_subject.txt"
    email_template_name = "registration/password_reset_email.txt"
    html_email_template_name = "registration/password_reset_email.html"

    def get_email_options(self):
        opts = super().get_email_options()
        # Merge in brand context so email templates can use {{ brand.* }}.
        try:
            from census_app.context_processors import branding as _branding

            ctx = _branding(self.request)
            brand = ctx.get("brand", {})
        except Exception:
            brand = {"title": getattr(settings, "BRAND_TITLE", "Census")}
        extra = opts.get("extra_email_context") or {}
        # Avoid mutating the original dict in place across requests
        merged = {**extra, "brand": brand}
        opts["extra_email_context"] = merged
        return opts


## Removed DirectPasswordResetConfirmView to use Django's standard confirm flow.
