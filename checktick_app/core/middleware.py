"""Custom middleware for CheckTick application."""

from django.utils import translation

# Django's session key for storing language preference
LANGUAGE_SESSION_KEY = "_language"


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
                from checktick_app.core.models import UserLanguagePreference

                preference = UserLanguagePreference.objects.filter(
                    user=request.user
                ).first()
                if preference and preference.language:
                    # Activate the user's preferred language
                    language = preference.language
                    print(
                        f"DEBUG Middleware: User {request.user.username} has language preference: {language}"
                    )
                    # Normalize language code (en-gb -> en-gb)
                    translation.activate(language)
                    request.LANGUAGE_CODE = language
                    # Also set in session so it persists across requests
                    if hasattr(request, "session"):
                        session_lang_before = request.session.get(LANGUAGE_SESSION_KEY)
                        request.session[LANGUAGE_SESSION_KEY] = language
                        request.session.modified = True
                        print(
                            f"DEBUG Middleware: Session language was: {session_lang_before}, now: {language}"
                        )
            except Exception:
                # If anything goes wrong (e.g., table doesn't exist yet during migration),
                # just continue without setting language preference
                pass

        response = self.get_response(request)
        return response
