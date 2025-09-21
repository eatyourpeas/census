from django.db import models


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
