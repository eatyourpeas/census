# Generated manually for i18n feature
# Run this migration after starting Docker with: python manage.py migrate

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0004_useremailpreferences"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserLanguagePreference",
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
                    "language",
                    models.CharField(
                        choices=settings.LANGUAGES,
                        default=settings.LANGUAGE_CODE,
                        help_text="Preferred language for the application interface",
                        max_length=10,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="language_preference",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "User Language Preference",
                "verbose_name_plural": "User Language Preferences",
            },
        ),
    ]
