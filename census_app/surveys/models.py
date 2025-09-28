from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from .utils import decrypt_sensitive, encrypt_sensitive, make_key_hash

User = get_user_model()


class Organization(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="organizations"
    )

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class OrganizationMembership(models.Model):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        CREATOR = "creator", "Creator"
        VIEWER = "viewer", "Viewer"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="org_memberships"
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CREATOR)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("organization", "user")


class QuestionGroup(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="question_groups"
    )
    shared = models.BooleanField(default=False)
    schema = models.JSONField(
        default=dict, help_text="Definition of questions in this group"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class Survey(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="surveys")
    organization = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, null=True, blank=True
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    question_groups = models.ManyToManyField(
        QuestionGroup, blank=True, related_name="surveys"
    )
    # Per-survey style overrides (title, theme_name, icon_url, font_heading, font_body, primary_color)
    style = models.JSONField(default=dict, blank=True)
    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        CLOSED = "closed", "Closed"

    class Visibility(models.TextChoices):
        AUTHENTICATED = "authenticated", "Authenticated users only"
        PUBLIC = "public", "Public"
        UNLISTED = "unlisted", "Unlisted (secret link)"
        TOKEN = "token", "By invite token"

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.AUTHENTICATED
    )
    published_at = models.DateTimeField(null=True, blank=True)
    unlisted_key = models.CharField(max_length=64, null=True, blank=True, unique=True)
    max_responses = models.PositiveIntegerField(null=True, blank=True)
    captcha_required = models.BooleanField(default=False)
    no_patient_data_ack = models.BooleanField(
        default=False,
        help_text="Publisher confirms no patient data is collected when using non-authenticated visibility",
    )
    # One-time survey key: store only hash + salt for verification
    key_salt = models.BinaryField(blank=True, null=True, editable=False)
    key_hash = models.BinaryField(blank=True, null=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_live(self) -> bool:
        now = timezone.now()
        time_ok = (self.start_at is None or self.start_at <= now) and (
            self.end_at is None or now <= self.end_at
        )
        status_ok = self.status == self.Status.PUBLISHED
        # Respect max responses if set
        if self.max_responses is not None and hasattr(self, "responses"):
            try:
                count = self.responses.count()
            except Exception:
                count = 0
            if count >= self.max_responses:
                return False
        return status_ok and time_ok

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
        TEMPLATE_PATIENT = "template_patient", "Patient details template"
        TEMPLATE_PROFESSIONAL = "template_professional", "Professional details template"

    survey = models.ForeignKey(
        Survey, on_delete=models.CASCADE, related_name="questions"
    )
    group = models.ForeignKey(
        QuestionGroup, on_delete=models.SET_NULL, null=True, blank=True
    )
    text = models.TextField()
    type = models.CharField(max_length=50, choices=Types.choices)
    options = models.JSONField(default=list, blank=True)
    required = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]


class SurveyQuestionCondition(models.Model):
    class Operator(models.TextChoices):
        EQUALS = "eq", "Equals"
        NOT_EQUALS = "neq", "Does not equal"
        CONTAINS = "contains", "Contains"
        NOT_CONTAINS = "not_contains", "Does not contain"
        GREATER_THAN = "gt", "Greater than"
        GREATER_EQUAL = "gte", "Greater or equal"
        LESS_THAN = "lt", "Less than"
        LESS_EQUAL = "lte", "Less or equal"
        EXISTS = "exists", "Answer provided"
        NOT_EXISTS = "not_exists", "Answer missing"

    class Action(models.TextChoices):
        JUMP_TO = "jump_to", "Jump to target"
        SHOW = "show", "Show target"
        SKIP = "skip", "Skip target"

    question = models.ForeignKey(
        SurveyQuestion, on_delete=models.CASCADE, related_name="conditions"
    )
    operator = models.CharField(
        max_length=16, choices=Operator.choices, default=Operator.EQUALS
    )
    value = models.CharField(
        max_length=255,
        blank=True,
        help_text="Value to compare against the response when required by the operator.",
    )
    target_question = models.ForeignKey(
        "SurveyQuestion",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="incoming_conditions",
    )
    target_group = models.ForeignKey(
        QuestionGroup,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="incoming_conditions",
    )
    action = models.CharField(
        max_length=32, choices=Action.choices, default=Action.JUMP_TO
    )
    order = models.PositiveIntegerField(default=0)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["question", "order", "id"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(target_question__isnull=False, target_group__isnull=True)
                    | Q(target_question__isnull=True, target_group__isnull=False)
                ),
                name="surveyquestioncondition_single_target",
            )
        ]

    def clean(self):  # pragma: no cover - validated via tests
        super().clean()

        if bool(self.target_question) == bool(self.target_group):
            raise ValidationError(
                {
                    "target_question": "Specify exactly one of target_question or target_group.",
                    "target_group": "Specify exactly one of target_question or target_group.",
                }
            )

        if self.target_question and (
            self.target_question.survey_id != self.question.survey_id
        ):
            raise ValidationError(
                {
                    "target_question": "Target question must belong to the same survey as the triggering question.",
                }
            )

        if (
            self.target_group
            and not self.target_group.surveys.filter(
                id=self.question.survey_id
            ).exists()
        ):
            raise ValidationError(
                {
                    "target_group": "Target group must be attached to the same survey as the triggering question.",
                }
            )

        operators_requiring_value = {
            self.Operator.EQUALS,
            self.Operator.NOT_EQUALS,
            self.Operator.CONTAINS,
            self.Operator.NOT_CONTAINS,
            self.Operator.GREATER_THAN,
            self.Operator.GREATER_EQUAL,
            self.Operator.LESS_THAN,
            self.Operator.LESS_EQUAL,
        }
        if self.operator in operators_requiring_value and not self.value:
            raise ValidationError(
                {"value": "This operator requires a comparison value."}
            )


class SurveyMembership(models.Model):
    class Role(models.TextChoices):
        CREATOR = "creator", "Creator"
        VIEWER = "viewer", "Viewer"

    survey = models.ForeignKey(
        Survey, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="survey_memberships"
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.VIEWER)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("survey", "user")


class SurveyResponse(models.Model):
    survey = models.ForeignKey(
        Survey, on_delete=models.CASCADE, related_name="responses"
    )
    # Sensitive demographics encrypted per-survey
    enc_demographics = models.BinaryField(null=True, blank=True)
    # Non-sensitive answers stored normally
    answers = models.JSONField(default=dict)
    submitted_at = models.DateTimeField(auto_now_add=True)
    submitted_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="survey_responses",
    )
    # Optional link to an invite token to enforce one-response-per-token
    # Using OneToOne ensures the token can be consumed exactly once.
    access_token = models.OneToOneField(
        "SurveyAccessToken",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="response",
    )

    def store_demographics(self, survey_key: bytes, demographics: dict):
        self.enc_demographics = encrypt_sensitive(survey_key, demographics)

    def load_demographics(self, survey_key: bytes) -> dict:
        if not self.enc_demographics:
            return {}
        return decrypt_sensitive(survey_key, self.enc_demographics)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["survey", "submitted_by"],
                name="one_response_per_user_per_survey",
            )
        ]


class SurveyAccessToken(models.Model):
    survey = models.ForeignKey(
        Survey, on_delete=models.CASCADE, related_name="access_tokens"
    )
    token = models.CharField(max_length=64, unique=True)
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="created_access_tokens"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    used_at = models.DateTimeField(null=True, blank=True)
    used_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="used_access_tokens",
    )
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["survey", "expires_at"]),
        ]

    def is_valid(self) -> bool:  # pragma: no cover
        if self.used_at:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True


def validate_markdown_survey(md_text: str) -> list[dict]:
    if not md_text or not md_text.strip():
        raise ValidationError("Empty markdown")
    # Placeholder minimal validation
    return []


class AuditLog(models.Model):
    class Scope(models.TextChoices):
        ORGANIZATION = "organization", "Organization"
        SURVEY = "survey", "Survey"

    class Action(models.TextChoices):
        ADD = "add", "Add"
        REMOVE = "remove", "Remove"
        UPDATE = "update", "Update"

    actor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="audit_logs")
    scope = models.CharField(max_length=20, choices=Scope.choices)
    organization = models.ForeignKey(
        Organization, null=True, blank=True, on_delete=models.CASCADE
    )
    survey = models.ForeignKey(Survey, null=True, blank=True, on_delete=models.CASCADE)
    action = models.CharField(max_length=20, choices=Action.choices)
    target_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="audit_targets"
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["scope", "organization", "survey"]),
            models.Index(fields=["created_at"]),
        ]


# -------------------- Collections (definitions) --------------------


class CollectionDefinition(models.Model):
    class Cardinality(models.TextChoices):
        ONE = "one", "One"
        MANY = "many", "Many"

    survey = models.ForeignKey(
        Survey, on_delete=models.CASCADE, related_name="collections"
    )
    key = models.SlugField(
        help_text="Stable key used in response JSON; unique per survey"
    )
    name = models.CharField(max_length=255)
    cardinality = models.CharField(
        max_length=10, choices=Cardinality.choices, default=Cardinality.MANY
    )
    min_count = models.PositiveIntegerField(default=0)
    max_count = models.PositiveIntegerField(null=True, blank=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="children"
    )

    class Meta:
        unique_together = ("survey", "key")
        indexes = [models.Index(fields=["survey", "parent"])]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name} ({self.key})"

    def ancestors(self) -> list["CollectionDefinition"]:
        chain: list[CollectionDefinition] = []
        node = self.parent
        # Walk up the tree
        while node is not None:
            chain.append(node)
            node = node.parent
        return chain

    def clean(self):  # pragma: no cover - covered via tests
        from django.core.exceptions import ValidationError

        # Parent must be in the same survey
        if self.parent and self.parent.survey_id != self.survey_id:
            raise ValidationError(
                {"parent": "Parent collection must belong to the same survey."}
            )
        # Depth cap (2 levels: parent -> child). If parent has a parent, this would be level 3.
        if self.parent and self.parent.parent_id:
            raise ValidationError({"parent": "Maximum nesting depth is 2."})
        # Cardinality constraints
        if self.cardinality == self.Cardinality.ONE:
            if self.max_count is not None and self.max_count != 1:
                raise ValidationError(
                    {"max_count": "For cardinality 'one', max_count must be 1."}
                )
            if self.min_count not in (0, 1):
                raise ValidationError(
                    {"min_count": "For cardinality 'one', min_count must be 0 or 1."}
                )
        # min/max relationship
        if self.max_count is not None and self.min_count > self.max_count:
            raise ValidationError({"min_count": "min_count cannot exceed max_count."})
        # Cycle prevention: parent chain cannot include self
        for anc in self.ancestors():
            # If this instance already has a PK, ensure no ancestor is itself
            if self.pk and anc.pk == self.pk:
                raise ValidationError(
                    {"parent": "Collections cannot reference themselves (cycle)."}
                )


class CollectionItem(models.Model):
    class ItemType(models.TextChoices):
        GROUP = "group", "Group"
        COLLECTION = "collection", "Collection"

    collection = models.ForeignKey(
        CollectionDefinition, on_delete=models.CASCADE, related_name="items"
    )
    item_type = models.CharField(max_length=20, choices=ItemType.choices)
    group = models.ForeignKey(
        QuestionGroup, null=True, blank=True, on_delete=models.CASCADE
    )
    child_collection = models.ForeignKey(
        CollectionDefinition,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="parent_links",
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["collection", "order"],
                name="uq_collectionitem_order_per_collection",
            ),
        ]

    def __str__(self) -> str:  # pragma: no cover
        target = self.group or self.child_collection
        return f"{self.item_type}: {target}"

    def clean(self):  # pragma: no cover - covered via tests
        from django.core.exceptions import ValidationError

        # Exactly one of group or child_collection must be set
        if bool(self.group) == bool(self.child_collection):
            raise ValidationError(
                "Provide either a group or a child_collection, not both."
            )
        # item_type must match the provided field
        if self.item_type == self.ItemType.GROUP and not self.group:
            raise ValidationError({"group": "group must be set for item_type 'group'."})
        if self.item_type == self.ItemType.COLLECTION and not self.child_collection:
            raise ValidationError(
                {
                    "child_collection": "child_collection must be set for item_type 'collection'."
                }
            )
        # Group must belong to the same survey
        if self.group:
            survey_id = self.collection.survey_id
            if not self.group.surveys.filter(id=survey_id).exists():
                raise ValidationError(
                    {"group": "Selected group is not attached to this survey."}
                )
        # Child collection must be in same survey and be a direct child of this collection
        if self.child_collection:
            if self.child_collection.survey_id != self.collection.survey_id:
                raise ValidationError(
                    {
                        "child_collection": "Child collection must belong to the same survey."
                    }
                )
            if self.child_collection.parent_id != self.collection_id:
                raise ValidationError(
                    {
                        "child_collection": "Child collection's parent must be this collection."
                    }
                )
