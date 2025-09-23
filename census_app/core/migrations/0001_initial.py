from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="SiteBranding",
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
                    "default_theme",
                    models.CharField(
                        choices=[
                            ("census-light", "Census Light"),
                            ("census-dark", "Census Dark"),
                        ],
                        default="census-light",
                        max_length=64,
                    ),
                ),
                ("icon_url", models.URLField(blank=True, default="")),
                (
                    "font_heading",
                    models.CharField(blank=True, default="", max_length=512),
                ),
                ("font_body", models.CharField(blank=True, default="", max_length=512)),
                ("font_css_url", models.URLField(blank=True, default="")),
                ("theme_light_css", models.TextField(blank=True, default="")),
                ("theme_dark_css", models.TextField(blank=True, default="")),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
