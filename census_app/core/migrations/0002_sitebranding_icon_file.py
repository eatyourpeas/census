from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitebranding",
            name="icon_file",
            field=models.FileField(blank=True, null=True, upload_to="branding/"),
        ),
    ]
