"""
Custom OIDC views for healthcare worker authentication.

Provides Google and Azure SSO integration while maintaining
compatibility with existing encryption and authentication systems.
"""

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View
from mozilla_django_oidc.views import OIDCAuthenticationRequestView, OIDCAuthenticationCallbackView
import logging

logger = logging.getLogger(__name__)


class HealthcareOIDCCallbackView(OIDCAuthenticationCallbackView):
    """
    Custom OIDC callback view that ensures our authentication backend is used.
    """

    def get(self, request):
        """Handle OIDC callback with custom authentication backend."""
        logger.info("Processing OIDC callback...")

        # Get provider from session and configure accordingly
        provider = request.session.get('oidc_provider', 'google')
        logger.info(f"Processing callback for provider: {provider}")

        # Temporarily modify Django settings for this request
        original_settings = {}
        try:
            if provider == 'azure':
                logger.info("Temporarily setting Django settings for Azure")
                # Store original values
                original_settings['OIDC_RP_CLIENT_ID'] = settings.OIDC_RP_CLIENT_ID
                original_settings['OIDC_RP_CLIENT_SECRET'] = settings.OIDC_RP_CLIENT_SECRET
                original_settings['OIDC_OP_TOKEN_ENDPOINT'] = settings.OIDC_OP_TOKEN_ENDPOINT
                original_settings['OIDC_OP_USER_ENDPOINT'] = settings.OIDC_OP_USER_ENDPOINT
                original_settings['OIDC_OP_JWKS_ENDPOINT'] = settings.OIDC_OP_JWKS_ENDPOINT
                original_settings['OIDC_RP_SCOPES'] = getattr(settings, 'OIDC_RP_SCOPES', 'openid email')

                # Set Azure values
                settings.OIDC_RP_CLIENT_ID = settings.OIDC_RP_CLIENT_ID_AZURE
                settings.OIDC_RP_CLIENT_SECRET = settings.OIDC_RP_CLIENT_SECRET_AZURE
                settings.OIDC_OP_TOKEN_ENDPOINT = f'https://login.microsoftonline.com/{settings.OIDC_OP_TENANT_ID_AZURE}/oauth2/v2.0/token'
                settings.OIDC_OP_USER_ENDPOINT = 'https://graph.microsoft.com/v1.0/me'
                settings.OIDC_OP_JWKS_ENDPOINT = settings.OIDC_OP_JWKS_ENDPOINT_AZURE
                settings.OIDC_RP_SCOPES = 'openid email profile User.Read'

                logger.info(f"Set Azure token endpoint: {settings.OIDC_OP_TOKEN_ENDPOINT}")

            response = super().get(request)
            logger.info(f"OIDC callback processed, redirecting to: {response.get('Location', 'unknown')}")
            return response

        except Exception as e:
            logger.error(f"OIDC callback failed: {e}")
            return redirect('/accounts/login/?error=oidc_failed')
        finally:
            # Restore original settings
            for key, value in original_settings.items():
                setattr(settings, key, value)
                logger.info(f"Restored {key} to original value")



class HealthcareOIDCAuthView(OIDCAuthenticationRequestView):
    """
    Custom OIDC authentication view for healthcare workers.

    Supports both Google and Azure authentication with provider selection.
    """

    def get(self, request: HttpRequest) -> HttpResponse:
        """
        Initiate OIDC authentication for specified provider.
        """
        provider = request.GET.get('provider', 'google')
        logger.info(f"Starting OIDC authentication for provider: {provider}")

        # Store provider in session for callback processing
        request.session['oidc_provider'] = provider

        # Configure OIDC settings based on provider - use instance variables
        if provider == 'azure':
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
        self.OIDC_OP_AUTH_ENDPOINT = 'https://accounts.google.com/o/oauth2/v2/auth'
        self.OIDC_OP_AUTHORIZATION_ENDPOINT = 'https://accounts.google.com/o/oauth2/v2/auth'
        self.OIDC_OP_TOKEN_ENDPOINT = 'https://oauth2.googleapis.com/token'
        self.OIDC_OP_USER_ENDPOINT = 'https://openidconnect.googleapis.com/v1/userinfo'
        self.OIDC_OP_JWKS_ENDPOINT = settings.OIDC_OP_JWKS_ENDPOINT_GOOGLE
        self.OIDC_RP_SCOPES = 'openid email profile'

    def _configure_azure_settings(self) -> None:
        """Configure instance variables for Azure OIDC."""
        logger.info("Configuring Azure OIDC settings")
        # Set the attributes that the parent class reads directly
        self.OIDC_RP_CLIENT_ID = settings.OIDC_RP_CLIENT_ID_AZURE
        self.OIDC_RP_CLIENT_SECRET = settings.OIDC_RP_CLIENT_SECRET_AZURE
        self.OIDC_OP_AUTH_ENDPOINT = f'https://login.microsoftonline.com/{settings.OIDC_OP_TENANT_ID_AZURE}/oauth2/v2.0/authorize'
        self.OIDC_OP_AUTHORIZATION_ENDPOINT = f'https://login.microsoftonline.com/{settings.OIDC_OP_TENANT_ID_AZURE}/oauth2/v2.0/authorize'
        self.OIDC_OP_TOKEN_ENDPOINT = f'https://login.microsoftonline.com/{settings.OIDC_OP_TENANT_ID_AZURE}/oauth2/v2.0/token'
        self.OIDC_OP_USER_ENDPOINT = 'https://graph.microsoft.com/oidc/userinfo'
        self.OIDC_OP_JWKS_ENDPOINT = settings.OIDC_OP_JWKS_ENDPOINT_AZURE
        # Azure requires specific scope for email
        self.OIDC_RP_SCOPES = 'openid email profile User.Read'

    # Override get_settings to use instance variables
    def get_settings(self, attr, *args):
        """Override to use instance-specific OIDC settings instead of global Django settings."""
        # Map Django settings names to our instance variables
        instance_attr_map = {
            'OIDC_RP_CLIENT_ID': 'OIDC_RP_CLIENT_ID',
            'OIDC_RP_CLIENT_SECRET': 'OIDC_RP_CLIENT_SECRET',
            'OIDC_OP_AUTHORIZATION_ENDPOINT': 'OIDC_OP_AUTHORIZATION_ENDPOINT',
            'OIDC_OP_TOKEN_ENDPOINT': 'OIDC_OP_TOKEN_ENDPOINT',
            'OIDC_OP_USER_ENDPOINT': 'OIDC_OP_USER_ENDPOINT',
            'OIDC_OP_JWKS_ENDPOINT': 'OIDC_OP_JWKS_ENDPOINT',
            'OIDC_RP_SCOPES': 'OIDC_RP_SCOPES',
        }

        if attr in instance_attr_map and hasattr(self, instance_attr_map[attr]):
            return getattr(self, instance_attr_map[attr])

        # Fall back to Django settings for other attributes
        return super().get_settings(attr, *args)


class HealthcareLoginView(View):
    """
    Healthcare worker login page with multiple authentication options.

    Provides:
    - Traditional email/password (preserves existing encryption)
    - Google SSO (for personal accounts)
    - Azure SSO (for hospital accounts)
    """

    template_name = 'registration/healthcare_login.html'

    def get(self, request: HttpRequest) -> HttpResponse:
        """Display healthcare login options."""
        context = {
            'google_login_url': reverse('oidc:oidc_authentication_init') + '?provider=google',
            'azure_login_url': reverse('oidc:oidc_authentication_init') + '?provider=azure',
            'traditional_login_url': reverse('login'),
            'next': request.GET.get('next', '/surveys/'),
        }
        return render(request, self.template_name, context)


def oidc_logout_view(request: HttpRequest) -> HttpResponse:
    """
    Custom OIDC logout that preserves session cleanup.

    Ensures encryption session data is properly cleared.
    """
    # Clear any encryption session data
    if 'survey_encryption_keys' in request.session:
        del request.session['survey_encryption_keys']

    # Standard logout redirect
    return redirect(settings.LOGOUT_REDIRECT_URL)
