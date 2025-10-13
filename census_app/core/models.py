from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class SiteBranding(models.Model):
    """Singleton-ish model storing project-level branding and theme overrides.

    Use get_or_create(pk=1) to manage a single row.
    """

    DEFAULT_THEME_CHOICES = [
        ("census-light", "Census Light"),
        ("census-dark", "Census Dark"),
    ]

    default_theme = models.CharField(
        max_length=64, choices=DEFAULT_THEME_CHOICES, default="census-light"
    )
    icon_url = models.URLField(blank=True, default="")
    icon_file = models.FileField(upload_to="branding/", blank=True, null=True)
    # Optional dark icon variants
    icon_url_dark = models.URLField(blank=True, default="")
    icon_file_dark = models.FileField(upload_to="branding/", blank=True, null=True)
    font_heading = models.CharField(max_length=512, blank=True, default="")
    font_body = models.CharField(max_length=512, blank=True, default="")
    font_css_url = models.URLField(blank=True, default="")

    # Raw CSS variable declarations for themes, after normalization to DaisyUI runtime vars
    theme_light_css = models.TextField(blank=True, default="")
    theme_dark_css = models.TextField(blank=True, default="")

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"Site Branding (theme={self.default_theme})"


class UserEmailPreferences(models.Model):
    """User preferences for email notifications.

    Each user has one preferences object (created on demand).
    Controls granularity of email notifications for various system events.
    """

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="email_preferences"
    )

    # Account-related emails (always sent regardless of preferences for security)
    send_welcome_email = models.BooleanField(
        default=True,
        help_text="Send welcome email when account is created (recommended)",
    )
    send_password_change_email = models.BooleanField(
        default=True,
        help_text="Send notification when password is changed (security feature)",
    )

    # Survey-related emails (optional)
    send_survey_created_email = models.BooleanField(
        default=False,
        help_text="Send notification when you create a new survey",
    )
    send_survey_deleted_email = models.BooleanField(
        default=False,
        help_text="Send notification when you delete a survey",
    )
    send_survey_published_email = models.BooleanField(
        default=False,
        help_text="Send notification when a survey is published",
    )

    # Organization/team emails
    send_team_invitation_email = models.BooleanField(
        default=True,
        help_text="Send notification when you're invited to an organization",
    )
    send_survey_invitation_email = models.BooleanField(
        default=True,
        help_text="Send notification when you're added to a survey team",
    )

    # Future: logging-related notifications (for integration with logging system)
    # These will be used when logging/signals feature is implemented
    notify_on_error = models.BooleanField(
        default=True,
        help_text="Send email notifications for system errors affecting your surveys",
    )
    notify_on_critical = models.BooleanField(
        default=True,
        help_text="Send email notifications for critical issues",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Email Preference"
        verbose_name_plural = "User Email Preferences"

    def __str__(self) -> str:  # pragma: no cover
        return f"Email Preferences for {self.user.username}"

    @classmethod
    def get_or_create_for_user(cls, user):
        """Get or create email preferences for a user with defaults."""
        preferences, created = cls.objects.get_or_create(user=user)
        return preferences


class UserLanguagePreference(models.Model):
    """User language preference for interface localization.

    Stores the user's preferred language for the application UI.
    Used by custom middleware to set the active language.
    """

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="language_preference"
    )
    language = models.CharField(
        max_length=10,
        choices=settings.LANGUAGES,
        default=settings.LANGUAGE_CODE,
        help_text="Preferred language for the application interface",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Language Preference"
        verbose_name_plural = "User Language Preferences"

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.user.username}: {self.get_language_display()}"

    @classmethod
    def get_or_create_for_user(cls, user):
        """Get or create language preference for a user with default."""
        preference, created = cls.objects.get_or_create(
            user=user, defaults={"language": settings.LANGUAGE_CODE}
        )
        return preference
