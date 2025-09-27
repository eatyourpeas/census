from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

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
            raise forms.ValidationError("An account with this email already exists")
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


## Removed BrandedPasswordResetForm in favor of Django's default behavior for
## PasswordResetView with html_email_template_name.
## No custom password reset form required; use Django defaults.
