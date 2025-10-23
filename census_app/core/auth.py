"""
Custom OIDC Authentication Backend for Healthcare Workers

Integrates Google and Azure OIDC authentication with the existing
patient data encryption system. Maintains your custom user model
as the source of truth while enabling SSO convenience.
"""

import logging
from typing import Any, Dict, Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import SuspiciousOperation
from mozilla_django_oidc.auth import OIDCAuthenticationBackend

User = get_user_model()
logger = logging.getLogger(__name__)


def generate_username(email: str) -> str:
    """
    Generate a username from email for OIDC users.

    Healthcare workers may have multiple accounts (hospital + personal),
    so we use email as the primary identifier.
    """
    return email.lower()


class CustomOIDCAuthenticationBackend(OIDCAuthenticationBackend):
    """
    Custom OIDC backend that integrates with healthcare encryption system.

    Features:
    - Links OIDC accounts to existing custom user model
    - Preserves encryption keys tied to stable user IDs
    - Supports both Google and Azure authentication
    - Allows multiple OIDC providers per user
    """

    def authenticate(self, request, **credentials):
        """Override to ensure backend is used during OIDC callback."""
        logger.info("CustomOIDCAuthenticationBackend.authenticate called")
        self.request = request
        result = super().authenticate(request, **credentials)
        logger.info(f"Authentication result: {result}")
        return result

    def get_userinfo(self, access_token: str, id_token: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Get user info from the appropriate provider based on session or token issuer."""

        # For now, let's use the default implementation and add provider detection later
        logger.info("Getting OIDC userinfo...")

        # Try default implementation first
        try:
            # Get user information from OIDC provider
            userinfo = super().get_userinfo(access_token, id_token, payload)
            logger.info(f"Got userinfo: {userinfo}")

            # Handle Azure-specific email extraction
            provider = None
            if hasattr(self, 'request') and self.request.session.get('oidc_provider'):
                provider = self.request.session.get('oidc_provider')

            if provider == 'azure' and userinfo:
                # For Azure, handle email extraction from userPrincipalName if mail is None
                if ('email' not in userinfo or not userinfo.get('email')) and ('mail' not in userinfo or not userinfo.get('mail')):
                    if 'userPrincipalName' in userinfo:
                        upn = userinfo['userPrincipalName']
                        logger.info(f"Extracting email from Azure UPN: {upn}")

                        if '#EXT#' in upn:
                            # Extract email before #EXT# and convert underscores back to @
                            email_part = upn.split('#EXT#')[0]
                            if '_' in email_part:
                                # Convert first underscore back to @
                                email = email_part.replace('_', '@', 1)
                                userinfo['email'] = email
                                logger.info(f"Extracted email from UPN: {email}")
                            else:
                                userinfo['email'] = upn
                        else:
                            userinfo['email'] = upn

            return userinfo
        except Exception as e:
            logger.error(f"Error getting userinfo: {e}")

            # Fallback to manual provider detection
            provider = None
            if hasattr(self, 'request') and self.request.session.get('oidc_provider'):
                provider = self.request.session.get('oidc_provider')

            # Fallback to determining provider from token issuer
            if not provider:
                issuer = payload.get('iss', '')
                if 'accounts.google.com' in issuer:
                    provider = 'google'
                elif 'login.microsoftonline.com' in issuer:
                    provider = 'azure'

            if provider == 'google':
                return self._get_google_userinfo(access_token)
            elif provider == 'azure':
                return self._get_azure_userinfo(access_token)
            else:
                logger.warning(f"Unknown OIDC provider: {provider}")
                raise

    def _get_google_userinfo(self, access_token: str) -> Dict[str, Any]:
        """Get user info from Google's userinfo endpoint."""
        import requests

        response = requests.get(
            'https://openidconnect.googleapis.com/v1/userinfo',
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    def _get_azure_userinfo(self, access_token):
        """Get userinfo from Microsoft Graph /me endpoint which includes email."""
        try:
            import requests
            response = requests.get(
                'https://graph.microsoft.com/v1.0/me',
                headers={'Authorization': f'Bearer {access_token}'}
            )
            response.raise_for_status()
            userinfo = response.json()
            logger.info(f"Azure Graph userinfo: {list(userinfo.keys())}")

            # Microsoft Graph returns 'mail' or 'userPrincipalName' for email
            if 'mail' in userinfo and userinfo['mail']:
                userinfo['email'] = userinfo['mail']
            elif 'userPrincipalName' in userinfo:
                # For external users, userPrincipalName might be like:
                # 'eatyourpeasapps_gmail.com#EXT#@eatyourpeasappsgmail.onmicrosoft.com'
                # Extract the original email
                upn = userinfo['userPrincipalName']
                if '#EXT#' in upn:
                    # Extract email before #EXT# and convert underscores back to @
                    email_part = upn.split('#EXT#')[0]
                    if '_' in email_part:
                        # Convert first underscore back to @
                        email = email_part.replace('_', '@', 1)
                        userinfo['email'] = email
                        logger.info(f"Extracted email from UPN: {email}")
                    else:
                        userinfo['email'] = upn
                else:
                    userinfo['email'] = upn

            return userinfo
        except Exception as e:
            logger.error(f"Failed to get Azure userinfo: {e}")
            return None

    def create_user(self, claims: Dict[str, Any]) -> User:
        """
        Create a new user from OIDC claims.

        Integrates with existing custom user model while preserving
        the ability to use traditional password authentication.
        """
        email = claims.get('email')
        if not email:
            raise SuspiciousOperation('OIDC user missing email claim')

        # Determine provider from claims
        provider = self._get_provider_from_claims(claims)

        # Generate username from email
        username = generate_username(email)

        # Create user with OIDC info
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=claims.get('given_name', ''),
                last_name=claims.get('family_name', ''),
            )

            # Store OIDC provider info for future linking
            self._link_oidc_account(user, provider, claims)

            logger.info(f"Successfully created new healthcare user via {provider} OIDC: {email}")
            return user
        except Exception as e:
            logger.error(f"Failed to create OIDC user {email}: {e}")
            raise

    def update_user(self, user: User, claims: Dict[str, Any]) -> User:
        """
        Update existing user with latest OIDC claims.

        Preserves encryption keys and core user data while updating
        profile information from the OIDC provider.
        """
        # Update basic profile info (preserve encryption data)
        user.first_name = claims.get('given_name', user.first_name)
        user.last_name = claims.get('family_name', user.last_name)
        user.email = claims.get('email', user.email)

        # Link this OIDC account if not already linked
        provider = self._get_provider_from_claims(claims)
        self._link_oidc_account(user, provider, claims)

        user.save()
        return user

    def get_or_create_user(self, access_token: str, id_token: str, payload: Dict[str, Any]) -> Optional[User]:
        """
        Get or create user, integrating with existing custom user model.

        This allows healthcare workers to:
        1. Link OIDC to existing accounts (preserves encryption keys)
        2. Create new accounts via OIDC
        3. Use multiple OIDC providers with same account
        """
        try:
            claims = self.get_userinfo(access_token, id_token, payload)
            email = claims.get('email')

            if not email:
                logger.warning("OIDC claims missing email")
                return None

            # Try to find existing user by email (primary linking method)
            try:
                user = User.objects.get(email=email)
                logger.info(f"Found existing user for OIDC login: {email}")
                return self.update_user(user, claims)
            except User.DoesNotExist:
                # Create new user if allowed
                if getattr(settings, 'OIDC_CREATE_USER', True):
                    logger.info(f"Creating new user via OIDC: {email}")
                    return self.create_user(claims)
                else:
                    logger.warning(f"OIDC user creation disabled, rejecting: {email}")
                    return None
        except Exception as e:
            logger.error(f"Error in OIDC get_or_create_user: {e}")
            return None

    def _get_provider_from_claims(self, claims: Dict[str, Any]) -> str:
        """Determine OIDC provider from claims."""
        issuer = claims.get('iss', '')

        if 'accounts.google.com' in issuer:
            return 'google'
        elif 'login.microsoftonline.com' in issuer:
            return 'azure'
        else:
            return 'unknown'

    def _link_oidc_account(self, user: User, provider: str, claims: Dict[str, Any]) -> None:
        """
        Link OIDC account to user for future authentication.

        This allows the same healthcare worker to authenticate via:
        - Google account (personal)
        - Azure account (hospital)
        - Traditional password
        """
        # Store provider-specific subject ID for future linking
        subject_id = claims.get('sub')
        if not subject_id:
            return

        # You could extend User model to store these, or use a separate model
        # For now, we rely on email matching for linking
        logger.info(f"Linked {provider} account to user {user.email}")
