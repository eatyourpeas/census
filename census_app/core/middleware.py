"""Custom middleware for Census application."""

from django.utils import translation


class UserLanguageMiddleware:
    """Middleware to set language based on user's saved preference.

    This middleware should be placed after LocaleMiddleware in the
    MIDDLEWARE setting. It checks if the user is authenticated and
    has a language preference saved, then activates that language
    for the request.

    This takes precedence over browser language detection but can
    still be overridden by explicit session language setting.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only apply if user is authenticated and has a preference
        if request.user.is_authenticated:
            try:
                # Import here to avoid circular imports
                from census_app.core.models import UserLanguagePreference

                preference = UserLanguagePreference.objects.filter(
                    user=request.user
                ).first()
                if preference:
                    # Activate the user's preferred language
                    translation.activate(preference.language)
                    request.LANGUAGE_CODE = preference.language
            except Exception:
                # If anything goes wrong (e.g., table doesn't exist yet during migration),
                # just continue without setting language preference
                pass

        response = self.get_response(request)
        return response
