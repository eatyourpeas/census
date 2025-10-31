"""
OIDC URL patterns for clinician authentication.

Provides:
- Google SSO authentication for personal accounts
- Azure SSO authentication for hospital/organization accounts
- Provider selection routing
- Custom callback handling
"""

import logging

from django.shortcuts import render
from django.urls import path

from .oidc_views import (
    HealthcareOIDCAuthView,
    HealthcareOIDCCallbackView,
    oidc_logout_view,
)

logger = logging.getLogger(__name__)

# Remove app_name so URLs are available globally as expected by mozilla-django-oidc


def oidc_success_debug_view(request):
    """Debug view for OIDC success."""
    logger.info(
        f"OIDC Success: user={request.user}, authenticated={request.user.is_authenticated}"
    )
    return render(request, "debug/oidc_success.html")


urlpatterns = [
    # Healthcare provider selection and authentication
    path(
        "authenticate/",
        HealthcareOIDCAuthView.as_view(),
        name="oidc_authentication_init",
    ),
    # Custom callback that uses our authentication backend - use exact name expected by mozilla-django-oidc
    path(
        "callback/",
        HealthcareOIDCCallbackView.as_view(),
        name="oidc_authentication_callback",
    ),
    # OIDC logout
    path("logout/", oidc_logout_view, name="oidc_logout"),
    # Debug success page for development
    path("success/", oidc_success_debug_view, name="oidc_success"),
]
