from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("surveys", "0002_questiongroup_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="survey",
            name="style",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
