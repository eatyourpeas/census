from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from census_app.surveys.models import OrganizationMembership, SurveyMembership


def branding(request):
    """Inject platform branding defaults into all templates.

    These can be overridden per-survey by passing variables with the same names in a view.
    """
    # Compute a lightweight flag to show/hide the User management link
    user = getattr(request, "user", AnonymousUser())
    can_manage_any_users = False
    if user and user.is_authenticated:
        can_manage_any_users = (
            OrganizationMembership.objects.filter(user=user, role=OrganizationMembership.Role.ADMIN).exists()
            or SurveyMembership.objects.filter(user=user, role=SurveyMembership.Role.CREATOR).exists()
        )

    return {
        "brand": {
            "title": getattr(settings, "BRAND_TITLE", "Census"),
            "icon_url": getattr(settings, "BRAND_ICON_URL", "/static/favicon.ico"),
            "theme_name": getattr(settings, "BRAND_THEME", "census"),
            "font_heading": getattr(settings, "BRAND_FONT_HEADING", "'IBM Plex Sans', ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, 'Apple Color Emoji', 'Segoe UI Emoji'"),
            "font_body": getattr(settings, "BRAND_FONT_BODY", "Merriweather, ui-serif, Georgia, Cambria, 'Times New Roman', Times, serif"),
            "font_css_url": getattr(settings, "BRAND_FONT_CSS_URL", "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600;700&family=Merriweather:wght@300;400;700&display=swap"),
        },
        "can_manage_any_users": can_manage_any_users,
    }
