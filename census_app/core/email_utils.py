"""Email utilities for sending branded, themed emails.

Supports both platform-level branding (for account emails) and survey-level
theming (for survey-specific emails).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import markdown
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


def get_platform_branding() -> Dict[str, Any]:
    """Get platform-level branding configuration.

    Returns brand settings from settings.py or SiteBranding model.
    Used for account-related emails (welcome, password change, etc.)
    """
    from census_app.core.models import SiteBranding

    # Try to get from database first
    try:
        branding = SiteBranding.objects.first()
        if branding:
            return {
                "title": getattr(settings, "BRAND_TITLE", "Census"),
                "theme_name": branding.default_theme,
                "icon_url": branding.icon_url
                or getattr(settings, "BRAND_ICON_URL", "/static/favicon.ico"),
                "font_heading": branding.font_heading
                or getattr(
                    settings,
                    "BRAND_FONT_HEADING",
                    "'IBM Plex Sans', sans-serif",
                ),
                "font_body": branding.font_body
                or getattr(settings, "BRAND_FONT_BODY", "Merriweather, serif"),
                "primary_color": "#3b82f6",  # Default blue
            }
    except Exception:
        pass

    # Fall back to settings
    return {
        "title": getattr(settings, "BRAND_TITLE", "Census"),
        "theme_name": getattr(settings, "BRAND_THEME", "census-light"),
        "icon_url": getattr(settings, "BRAND_ICON_URL", "/static/favicon.ico"),
        "font_heading": getattr(
            settings, "BRAND_FONT_HEADING", "'IBM Plex Sans', sans-serif"
        ),
        "font_body": getattr(settings, "BRAND_FONT_BODY", "Merriweather, serif"),
        "primary_color": "#3b82f6",
    }


def get_survey_branding(survey) -> Dict[str, Any]:
    """Get survey-level branding configuration.

    Returns survey-specific theme overrides for survey-related emails.
    Falls back to platform branding if no survey overrides exist.
    """
    platform_brand = get_platform_branding()

    if not survey:
        return platform_brand

    style = survey.style or {}

    return {
        "title": style.get("title") or survey.name or platform_brand["title"],
        "theme_name": style.get("theme_name") or platform_brand["theme_name"],
        "icon_url": style.get("icon_url") or platform_brand["icon_url"],
        "font_heading": style.get("font_heading") or platform_brand["font_heading"],
        "font_body": style.get("font_body") or platform_brand["font_body"],
        "primary_color": style.get("primary_color") or platform_brand["primary_color"],
        "survey_name": survey.name,
        "survey_slug": survey.slug,
    }


def markdown_to_html(markdown_text: str) -> str:
    """Convert markdown text to HTML.

    Supports standard markdown features including:
    - Headers
    - Bold, italic
    - Lists
    - Links
    - Code blocks
    """
    return markdown.markdown(
        markdown_text,
        extensions=["extra", "nl2br", "sane_lists"],
    )


def send_branded_email(
    to_email: str,
    subject: str,
    markdown_content: str,
    branding: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
    from_email: Optional[str] = None,
) -> bool:
    """Send a branded email with markdown content.

    Args:
        to_email: Recipient email address
        subject: Email subject line
        markdown_content: Email body in markdown format
        branding: Brand configuration (platform or survey-level)
        context: Additional template context variables
        from_email: Sender email (defaults to DEFAULT_FROM_EMAIL)

    Returns:
        True if email sent successfully, False otherwise
    """
    if not branding:
        branding = get_platform_branding()

    if not context:
        context = {}

    # Convert markdown to HTML
    html_content = markdown_to_html(markdown_content)

    # Build full context for template
    email_context = {
        "subject": subject,
        "content": html_content,
        "brand": branding,
        "site_url": getattr(settings, "SITE_URL", "http://localhost:8000"),
        **context,
    }

    # Render HTML email with branding
    try:
        html_message = render_to_string(
            "emails/base_email.html",
            email_context,
        )
    except Exception as e:
        logger.error(f"Failed to render email template: {e}")
        # Fallback to simple HTML
        html_message = f"""
        <html>
            <body style="font-family: {branding.get('font_body', 'sans-serif')};">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: {branding.get('primary_color', '#3b82f6')};">
                        {branding.get('title', 'Census')}
                    </h1>
                    {html_content}
                </div>
            </body>
        </html>
        """

    # Generate plain text version
    plain_message = strip_tags(html_content)

    # Send email
    try:
        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=from_email or settings.DEFAULT_FROM_EMAIL,
            to=[to_email],
        )
        email.attach_alternative(html_message, "text/html")
        email.send()
        logger.info(f"Email sent to {to_email}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


def send_welcome_email(user) -> bool:
    """Send welcome email to newly registered user.

    Uses platform-level branding.
    """
    from census_app.core.models import UserEmailPreferences

    prefs = UserEmailPreferences.get_or_create_for_user(user)
    if not prefs.send_welcome_email:
        logger.info(f"Welcome email skipped for {user.username} (user preference)")
        return False

    branding = get_platform_branding()

    subject = f"Welcome to {branding['title']}!"

    markdown_content = render_to_string(
        "emails/welcome.md",
        {
            "user": user,
            "brand_title": branding["title"],
        },
    )

    return send_branded_email(
        to_email=user.email,
        subject=subject,
        markdown_content=markdown_content,
        branding=branding,
        context={"user": user},
    )


def send_password_change_email(user) -> bool:
    """Send security notification when password is changed.

    Uses platform-level branding.
    Note: This is a security feature and respects user preferences.
    """
    from census_app.core.models import UserEmailPreferences

    prefs = UserEmailPreferences.get_or_create_for_user(user)
    if not prefs.send_password_change_email:
        logger.info(
            f"Password change email skipped for {user.username} (user preference)"
        )
        return False

    branding = get_platform_branding()

    subject = "Password Changed - Security Notification"

    markdown_content = render_to_string(
        "emails/password_changed.md",
        {
            "user": user,
            "brand_title": branding["title"],
        },
    )

    return send_branded_email(
        to_email=user.email,
        subject=subject,
        markdown_content=markdown_content,
        branding=branding,
        context={"user": user},
    )


def send_survey_created_email(user, survey) -> bool:
    """Send notification when survey is created.

    Uses survey-level branding if configured, otherwise platform branding.
    """
    from census_app.core.models import UserEmailPreferences

    prefs = UserEmailPreferences.get_or_create_for_user(user)
    if not prefs.send_survey_created_email:
        logger.info(
            f"Survey created email skipped for {user.username} (user preference)"
        )
        return False

    branding = get_survey_branding(survey)

    subject = f"Survey Created: {survey.name}"

    markdown_content = render_to_string(
        "emails/survey_created.md",
        {
            "user": user,
            "survey": survey,
            "brand_title": branding["title"],
        },
    )

    return send_branded_email(
        to_email=user.email,
        subject=subject,
        markdown_content=markdown_content,
        branding=branding,
        context={"user": user, "survey": survey},
    )


def send_survey_deleted_email(user, survey_name: str, survey_slug: str) -> bool:
    """Send notification when survey is deleted.

    Note: Survey object is already deleted, so we use name/slug.
    Uses platform branding since survey no longer exists.
    """
    from census_app.core.models import UserEmailPreferences

    prefs = UserEmailPreferences.get_or_create_for_user(user)
    if not prefs.send_survey_deleted_email:
        logger.info(
            f"Survey deleted email skipped for {user.username} (user preference)"
        )
        return False

    branding = get_platform_branding()

    subject = f"Survey Deleted: {survey_name}"

    markdown_content = render_to_string(
        "emails/survey_deleted.md",
        {
            "user": user,
            "survey_name": survey_name,
            "survey_slug": survey_slug,
            "brand_title": branding["title"],
        },
    )

    return send_branded_email(
        to_email=user.email,
        subject=subject,
        markdown_content=markdown_content,
        branding=branding,
        context={
            "user": user,
            "survey_name": survey_name,
            "survey_slug": survey_slug,
        },
    )
