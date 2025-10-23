# Generated migration for Option 2 encryption strategy
# Adds fields for password-encrypted and recovery-phrase-encrypted KEKs

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("surveys", "0010_surveyquestioncondition"),
    ]

    operations = [
        migrations.AddField(
            model_name="survey",
            name="encrypted_kek_password",
            field=models.BinaryField(
                blank=True,
                null=True,
                editable=False,
                help_text="Survey encryption key encrypted with password-derived key",
            ),
        ),
        migrations.AddField(
            model_name="survey",
            name="encrypted_kek_recovery",
            field=models.BinaryField(
                blank=True,
                null=True,
                editable=False,
                help_text="Survey encryption key encrypted with recovery-phrase-derived key",
            ),
        ),
        migrations.AddField(
            model_name="survey",
            name="recovery_code_hint",
            field=models.CharField(
                max_length=255,
                blank=True,
                help_text="First and last word of recovery phrase (e.g., 'apple...zebra')",
            ),
        ),
    ]
