from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import UserEmailPreferences, UserLanguagePreference

User = get_user_model()


class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("email",)

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            raise forms.ValidationError("Email is required")
        if User.objects.filter(email__iexact=email).exists():
            from django.urls import reverse
            from django.utils.safestring import mark_safe

            login_url = reverse("login")
            raise forms.ValidationError(
                mark_safe(
                    f"An account with this email already exists. "
                    f'<a href="{login_url}" class="link link-primary font-medium">Sign in instead</a> '
                    f"or use a different email address."
                )
            )
        return email

    def save(self, commit=True):
        email = self.cleaned_data["email"].strip().lower()
        user = User()
        user.username = email
        user.email = email
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserEmailPreferencesForm(forms.ModelForm):
    """Form for managing user email notification preferences."""

    class Meta:
        model = UserEmailPreferences
        fields = [
            "send_welcome_email",
            "send_password_change_email",
            "send_survey_created_email",
            "send_survey_deleted_email",
            "send_survey_published_email",
            "send_team_invitation_email",
            "send_survey_invitation_email",
            "notify_on_error",
            "notify_on_critical",
        ]
        widgets = {
            "send_welcome_email": forms.CheckboxInput(
                attrs={"class": "checkbox checkbox-primary"}
            ),
            "send_password_change_email": forms.CheckboxInput(
                attrs={"class": "checkbox checkbox-primary"}
            ),
            "send_survey_created_email": forms.CheckboxInput(
                attrs={"class": "checkbox checkbox-primary"}
            ),
            "send_survey_deleted_email": forms.CheckboxInput(
                attrs={"class": "checkbox checkbox-primary"}
            ),
            "send_survey_published_email": forms.CheckboxInput(
                attrs={"class": "checkbox checkbox-primary"}
            ),
            "send_team_invitation_email": forms.CheckboxInput(
                attrs={"class": "checkbox checkbox-primary"}
            ),
            "send_survey_invitation_email": forms.CheckboxInput(
                attrs={"class": "checkbox checkbox-primary"}
            ),
            "notify_on_error": forms.CheckboxInput(
                attrs={"class": "checkbox checkbox-primary"}
            ),
            "notify_on_critical": forms.CheckboxInput(
                attrs={"class": "checkbox checkbox-primary"}
            ),
        }


class UserLanguagePreferenceForm(forms.ModelForm):
    """Form for managing user language preference."""

    class Meta:
        model = UserLanguagePreference
        fields = ["language"]
        widgets = {
            "language": forms.Select(
                attrs={"class": "select select-bordered w-full"},
                choices=settings.LANGUAGES,
            ),
        }
        labels = {
            "language": "Preferred Language",
        }


## Removed BrandedPasswordResetForm in favor of Django's default behavior for
## PasswordResetView with html_email_template_name.
## No custom password reset form required; use Django defaults.
