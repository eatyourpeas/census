"""
Custom OIDC views for clinician authentication.

Provides Google and Azure SSO integration while maintaining
compatibility with existing encryption and authentication systems.
"""

import logging

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View
from mozilla_django_oidc.views import (
    OIDCAuthenticationCallbackView,
    OIDCAuthenticationRequestView,
)

logger = logging.getLogger(__name__)


class HealthcareOIDCCallbackView(OIDCAuthenticationCallbackView):
    """
    Custom OIDC callback view that ensures our authentication backend is used.
    """

    def get(self, request):
        """Handle OIDC callback with custom authentication backend."""
        logger.info("Processing OIDC callback...")

        # Get provider from session and configure accordingly
        provider = request.session.get("oidc_provider", "google")
        signup_mode = request.session.get("oidc_signup_mode", False)
        logger.info(
            f"Processing callback for provider: {provider}, signup_mode: {signup_mode}"
        )

        # Temporarily modify Django settings for this request
        original_settings = {}
        try:
            if provider == "azure":
                logger.info("Temporarily setting Django settings for Azure")
                # Store original values
                original_settings["OIDC_RP_CLIENT_ID"] = settings.OIDC_RP_CLIENT_ID
                original_settings["OIDC_RP_CLIENT_SECRET"] = (
                    settings.OIDC_RP_CLIENT_SECRET
                )
                original_settings["OIDC_OP_TOKEN_ENDPOINT"] = (
                    settings.OIDC_OP_TOKEN_ENDPOINT
                )
                original_settings["OIDC_OP_USER_ENDPOINT"] = (
                    settings.OIDC_OP_USER_ENDPOINT
                )
                original_settings["OIDC_OP_JWKS_ENDPOINT"] = (
                    settings.OIDC_OP_JWKS_ENDPOINT
                )
                original_settings["OIDC_RP_SCOPES"] = getattr(
                    settings, "OIDC_RP_SCOPES", "openid email"
                )

                # Set Azure values
                settings.OIDC_RP_CLIENT_ID = settings.OIDC_RP_CLIENT_ID_AZURE
                settings.OIDC_RP_CLIENT_SECRET = settings.OIDC_RP_CLIENT_SECRET_AZURE
                settings.OIDC_OP_TOKEN_ENDPOINT = (
                    "https://login.microsoftonline.com/common/oauth2/v2.0/token"
                )
                settings.OIDC_OP_USER_ENDPOINT = (
                    "https://graph.microsoft.com/oidc/userinfo"
                )
                settings.OIDC_OP_JWKS_ENDPOINT = settings.OIDC_OP_JWKS_ENDPOINT_AZURE
                settings.OIDC_RP_SCOPES = "openid email profile"

                logger.info(
                    f"Set Azure token endpoint: {settings.OIDC_OP_TOKEN_ENDPOINT}"
                )

            # Store signup mode flag for callback processing
            if signup_mode:
                try:
                    request.session["oidc_signup_attempt"] = True
                except Exception as e:
                    logger.warning(f"Could not set signup attempt flag: {e}")

            try:
                response = super().get(request)
                logger.info(
                    f"OIDC parent callback response: status={response.status_code}, user_authenticated={request.user.is_authenticated}"
                )

                if not request.user.is_authenticated:
                    logger.warning(
                        "OIDC authentication failed - user not authenticated after callback"
                    )
                    # Check if there are any error parameters
                    error = request.GET.get("error")
                    error_description = request.GET.get("error_description")
                    if error:
                        logger.error(
                            f"OIDC error: {error}, description: {error_description}"
                        )

            except Exception as e:
                logger.error(f"OIDC parent callback failed with exception: {e}")
                return redirect("/accounts/login/?error=oidc_callback_failed")

            # Handle new user vs existing user flow
            if request.user.is_authenticated:
                from django.contrib import messages
                from django.utils.translation import gettext as _

                # Check if this user already existed (set by authentication backend)
                user_existed = getattr(request.user, "_oidc_user_existed", None)

                if user_existed is False:
                    # New user was created
                    if signup_mode:
                        # User came from signup page - they already made account type choice
                        # Mark signup as completed since they went through the signup page
                        if hasattr(request.user, "oidc"):
                            request.user.oidc.signup_completed = True
                            request.user.oidc.save()
                            logger.info(
                                f"Marked OIDC signup as completed for user from signup page: {request.user.email}"
                            )
                        # Check sessionStorage via JavaScript (handled in template)
                        messages.success(
                            request,
                            _(
                                "Account created successfully! Your {} account has been linked."
                            ).format(provider.title()),
                        )
                        logger.info(
                            f"New user from signup page: {request.user.email} - provider: {provider}"
                        )
                    else:
                        # User came from login page - needs to complete signup
                        logger.info(
                            f"New user from login page, redirecting to complete signup: {request.user.email}"
                        )
                        request.session["needs_signup_completion"] = True
                        return redirect("core:complete_signup")
                elif user_existed is True:
                    # Existing user was found and linked
                    # Check if OIDC user needs to complete signup
                    if (
                        hasattr(request.user, "oidc")
                        and not request.user.oidc.signup_completed
                    ):
                        logger.info(
                            f"Existing OIDC user has not completed signup, redirecting: {request.user.email}"
                        )
                        request.session["needs_signup_completion"] = True
                        return redirect("core:complete_signup")

                    messages.info(
                        request,
                        _(
                            "Welcome back! We found your existing account and linked your {} account to it."
                        ).format(provider.title()),
                    )
                    logger.info(
                        f"Added existing user message for {request.user.email} - provider: {provider}"
                    )
                else:
                    # Fallback message if flag is not set
                    # Check if OIDC user needs to complete signup
                    if (
                        hasattr(request.user, "oidc")
                        and not request.user.oidc.signup_completed
                    ):
                        logger.info(
                            f"OIDC user (fallback case) has not completed signup, redirecting: {request.user.email}"
                        )
                        request.session["needs_signup_completion"] = True
                        return redirect("core:complete_signup")

                    messages.info(
                        request,
                        _("Successfully signed in with {}.").format(provider.title()),
                    )
                    logger.info(
                        f"Added fallback message for {request.user.email} - provider: {provider}, user_existed: {user_existed}"
                    )

                # Clean up session data
                request.session.pop("oidc_signup_mode", None)

            logger.info(
                f"OIDC callback processed, redirecting to: {response.get('Location', 'unknown')}"
            )
            return response

        except Exception as e:
            logger.error(f"OIDC callback failed: {e}")
            return redirect("/accounts/login/?error=oidc_failed")
        finally:
            # Restore original settings
            for key, value in original_settings.items():
                setattr(settings, key, value)
                logger.info(f"Restored {key} to original value")


class HealthcareOIDCAuthView(OIDCAuthenticationRequestView):
    """
    Custom OIDC authentication view for clinicians.

    Supports both Google and Azure authentication with provider selection.
    """

    def get(self, request: HttpRequest) -> HttpResponse:
        """
        Initiate OIDC authentication for specified provider.
        """
        provider = request.GET.get("provider", "google")
        signup_mode = request.GET.get("signup") == "true"
        logger.info(
            f"Starting OIDC authentication for provider: {provider}, signup_mode: {signup_mode}"
        )

        # Store provider and signup mode in session for callback processing
        request.session["oidc_provider"] = provider
        if signup_mode:
            request.session["oidc_signup_mode"] = True

        # Configure OIDC settings based on provider - use instance variables
        if provider == "azure":
            self._configure_azure_settings()
        else:
            self._configure_google_settings()

        return super().get(request)

    def _configure_google_settings(self) -> None:
        """Configure instance variables for Google OIDC."""
        logger.info("Configuring Google OIDC settings")
        # Set the attributes that the parent class reads directly
        self.OIDC_RP_CLIENT_ID = settings.OIDC_RP_CLIENT_ID_GOOGLE
        self.OIDC_RP_CLIENT_SECRET = settings.OIDC_RP_CLIENT_SECRET_GOOGLE
        self.OIDC_OP_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
        self.OIDC_OP_AUTHORIZATION_ENDPOINT = (
            "https://accounts.google.com/o/oauth2/v2/auth"
        )
        self.OIDC_OP_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
        self.OIDC_OP_USER_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"
        self.OIDC_OP_JWKS_ENDPOINT = settings.OIDC_OP_JWKS_ENDPOINT_GOOGLE
        self.OIDC_RP_SCOPES = "openid email profile"

    def _configure_azure_settings(self) -> None:
        """Configure instance variables for Azure OIDC."""
        logger.info("Configuring Azure OIDC settings")
        # Set the attributes that the parent class reads directly
        self.OIDC_RP_CLIENT_ID = settings.OIDC_RP_CLIENT_ID_AZURE
        self.OIDC_RP_CLIENT_SECRET = settings.OIDC_RP_CLIENT_SECRET_AZURE
        self.OIDC_OP_AUTH_ENDPOINT = (
            "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
        )
        self.OIDC_OP_AUTHORIZATION_ENDPOINT = (
            "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
        )
        self.OIDC_OP_TOKEN_ENDPOINT = (
            "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        )
        self.OIDC_OP_USER_ENDPOINT = "https://graph.microsoft.com/oidc/userinfo"
        self.OIDC_OP_JWKS_ENDPOINT = settings.OIDC_OP_JWKS_ENDPOINT_AZURE
        # Use only OIDC protocol scopes - no Graph API permissions needed
        self.OIDC_RP_SCOPES = "openid email profile"

    # Override get_settings to use instance variables
    def get_settings(self, attr, *args):
        """Override to use instance-specific OIDC settings instead of global Django settings."""
        # Map Django settings names to our instance variables
        instance_attr_map = {
            "OIDC_RP_CLIENT_ID": "OIDC_RP_CLIENT_ID",
            "OIDC_RP_CLIENT_SECRET": "OIDC_RP_CLIENT_SECRET",
            "OIDC_OP_AUTHORIZATION_ENDPOINT": "OIDC_OP_AUTHORIZATION_ENDPOINT",
            "OIDC_OP_TOKEN_ENDPOINT": "OIDC_OP_TOKEN_ENDPOINT",
            "OIDC_OP_USER_ENDPOINT": "OIDC_OP_USER_ENDPOINT",
            "OIDC_OP_JWKS_ENDPOINT": "OIDC_OP_JWKS_ENDPOINT",
            "OIDC_RP_SCOPES": "OIDC_RP_SCOPES",
        }

        if attr in instance_attr_map and hasattr(self, instance_attr_map[attr]):
            return getattr(self, instance_attr_map[attr])

        # Fall back to Django settings for other attributes
        return super().get_settings(attr, *args)


class HealthcareLoginView(View):
    """
    Clinician login page with multiple authentication options.

    Provides:
    - Traditional email/password (preserves existing encryption)
    - Google SSO (for personal accounts)
    - Azure SSO (for hospital accounts)
    """

    template_name = "registration/healthcare_login.html"

    def get(self, request: HttpRequest) -> HttpResponse:
        """Display healthcare login options."""
        context = {
            "google_login_url": reverse("oidc:oidc_authentication_init")
            + "?provider=google",
            "azure_login_url": reverse("oidc:oidc_authentication_init")
            + "?provider=azure",
            "traditional_login_url": reverse("login"),
            "next": request.GET.get("next", "/surveys/"),
        }
        return render(request, self.template_name, context)


def oidc_logout_view(request: HttpRequest) -> HttpResponse:
    """
    Custom OIDC logout that preserves session cleanup.

    Ensures encryption session data is properly cleared.
    """
    # Clear any encryption session data
    if "survey_encryption_keys" in request.session:
        del request.session["survey_encryption_keys"]

    # Standard logout redirect
    return redirect(settings.LOGOUT_REDIRECT_URL)
