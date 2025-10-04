# Generated migration for UserEmailPreferences model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0003_sitebranding_dark_icon"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserEmailPreferences",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "send_welcome_email",
                    models.BooleanField(
                        default=True,
                        help_text="Send welcome email when account is created (recommended)",
                    ),
                ),
                (
                    "send_password_change_email",
                    models.BooleanField(
                        default=True,
                        help_text="Send notification when password is changed (security feature)",
                    ),
                ),
                (
                    "send_survey_created_email",
                    models.BooleanField(
                        default=False,
                        help_text="Send notification when you create a new survey",
                    ),
                ),
                (
                    "send_survey_deleted_email",
                    models.BooleanField(
                        default=False,
                        help_text="Send notification when you delete a survey",
                    ),
                ),
                (
                    "send_survey_published_email",
                    models.BooleanField(
                        default=False,
                        help_text="Send notification when a survey is published",
                    ),
                ),
                (
                    "send_team_invitation_email",
                    models.BooleanField(
                        default=True,
                        help_text="Send notification when you're invited to an organization",
                    ),
                ),
                (
                    "send_survey_invitation_email",
                    models.BooleanField(
                        default=True,
                        help_text="Send notification when you're added to a survey team",
                    ),
                ),
                (
                    "notify_on_error",
                    models.BooleanField(
                        default=True,
                        help_text="Send email notifications for system errors affecting your surveys",
                    ),
                ),
                (
                    "notify_on_critical",
                    models.BooleanField(
                        default=True,
                        help_text="Send email notifications for critical issues",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="email_preferences",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "User Email Preference",
                "verbose_name_plural": "User Email Preferences",
            },
        ),
    ]
