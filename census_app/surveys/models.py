from __future__ import annotations
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from .utils import encrypt_sensitive, decrypt_sensitive, make_key_hash


User = get_user_model()


class Organization(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="organizations")

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class OrganizationMembership(models.Model):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        CREATOR = "creator", "Creator"
        VIEWER = "viewer", "Viewer"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="org_memberships")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CREATOR)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("organization", "user")


class QuestionGroup(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="question_groups")
    shared = models.BooleanField(default=False)
    schema = models.JSONField(default=dict, help_text="Definition of questions in this group")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class Survey(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="surveys")
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    question_groups = models.ManyToManyField(QuestionGroup, blank=True, related_name="surveys")
    # Per-survey style overrides (title, theme_name, icon_url, font_heading, font_body, primary_color)
    style = models.JSONField(default=dict, blank=True)
    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    # One-time survey key: store only hash + salt for verification
    key_salt = models.BinaryField(blank=True, null=True, editable=False)
    key_hash = models.BinaryField(blank=True, null=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_live(self) -> bool:
        now = timezone.now()
        return (self.start_at is None or self.start_at <= now) and (self.end_at is None or now <= self.end_at)

    def __str__(self) -> str:  # pragma: no cover
        return self.name

    def set_key(self, key_bytes: bytes) -> None:
        digest, salt = make_key_hash(key_bytes)
        self.key_hash = digest
        self.key_salt = salt
        self.save(update_fields=["key_hash", "key_salt"])


class SurveyQuestion(models.Model):
    class Types(models.TextChoices):
        TEXT = "text", "Free text"
        MULTIPLE_CHOICE_SINGLE = "mc_single", "Multiple choice (single)"
        MULTIPLE_CHOICE_MULTI = "mc_multi", "Multiple choice (multi)"
        LIKERT = "likert", "Likert scale"
        ORDERABLE = "orderable", "Orderable list"
        YESNO = "yesno", "Yes/No"
        DROPDOWN = "dropdown", "Dropdown"
        IMAGE_CHOICE = "image", "Image choice"

    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name="questions")
    group = models.ForeignKey(QuestionGroup, on_delete=models.SET_NULL, null=True, blank=True)
    text = models.TextField()
    type = models.CharField(max_length=20, choices=Types.choices)
    options = models.JSONField(default=list, blank=True)
    required = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]


class SurveyResponse(models.Model):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name="responses")
    # Sensitive demographics encrypted per-survey
    enc_demographics = models.BinaryField(null=True, blank=True)
    # Non-sensitive answers stored normally
    answers = models.JSONField(default=dict)
    submitted_at = models.DateTimeField(auto_now_add=True)
    submitted_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="survey_responses")

    def store_demographics(self, survey_key: bytes, demographics: dict):
        self.enc_demographics = encrypt_sensitive(survey_key, demographics)

    def load_demographics(self, survey_key: bytes) -> dict:
        if not self.enc_demographics:
            return {}
        return decrypt_sensitive(survey_key, self.enc_demographics)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["survey", "submitted_by"], name="one_response_per_user_per_survey")
        ]


def validate_markdown_survey(md_text: str) -> list[dict]:
    if not md_text or not md_text.strip():
        raise ValidationError("Empty markdown")
    # Placeholder minimal validation
    return []
