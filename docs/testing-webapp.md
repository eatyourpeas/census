# Testing the Web Application

This document provides guidance on testing the Census webapp, including patterns for testing views, forms, question builder functionality, and HTMX interactions.

## Overview

The Census webapp is tested using pytest with Django's test client. Tests verify that web pages render correctly, forms work as expected, permissions are enforced, and interactive features function properly.

## Test Location

Webapp tests are organized by app:

- `/census_app/surveys/tests/` - Survey-related webapp tests
  - `test_builder_question_creation.py` - Question creation via builder (23 tests)
  - `test_builder_editing.py` - Question editing functionality
  - `test_permissions.py` - Access control and permissions
  - `test_groups_reorder.py` - Question group reordering
  - `test_anonymous_access.py` - Anonymous user behavior
  - And more...
- `/census_app/core/tests/` - Core app tests
- `/tests/` - General integration tests

## Running Webapp Tests

```bash
# Run all webapp tests for surveys app
docker compose exec web pytest census_app/surveys/tests/

# Run specific test file
docker compose exec web pytest census_app/surveys/tests/test_builder_question_creation.py

# Run with verbose output
docker compose exec web pytest census_app/surveys/tests/test_builder_question_creation.py -v

# Run specific test class or test
docker compose exec web pytest census_app/surveys/tests/test_builder_question_creation.py::TestWebappQuestionCreation
docker compose exec web pytest census_app/surveys/tests/test_builder_question_creation.py::TestWebappQuestionCreation::test_create_text_question
```

## Test Structure

### Basic Test Class Pattern

```python
import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from census_app.surveys.models import Survey, SurveyQuestion

@pytest.mark.django_db
class TestMyView:
    """Test suite for my view."""
    
    def setup_survey(self, client):
        """Create test user and survey, log in user."""
        user = User.objects.create_user(username="testuser", password="testpass")
        survey = Survey.objects.create(owner=user, name="Test", slug="test")
        client.force_login(user)
        return user, survey
    
    def test_view_renders(self, client):
        """Test that view renders successfully."""
        user, survey = self.setup_survey(client)
        url = reverse("surveys:survey_detail", kwargs={"slug": survey.slug})
        
        response = client.get(url)
        
        assert response.status_code == 200
        assert "Test" in response.content.decode()
```

## Authentication and Permissions

Webapp tests use Django's authentication system. Tests should:

1. Create test users with appropriate permissions
2. Use `client.force_login(user)` to authenticate
3. Test both authenticated and unauthenticated access

### Example: Authentication Setup

```python
def test_authenticated_access(self, client):
    """Test that authenticated users can access the page."""
    user = User.objects.create_user(username="user", password="pass")
    survey = Survey.objects.create(owner=user, name="Test", slug="test")
    
    # Log in the user
    client.force_login(user)
    
    url = reverse("surveys:survey_detail", kwargs={"slug": survey.slug})
    response = client.get(url)
    
    assert response.status_code == 200

def test_unauthenticated_redirects(self, client):
    """Test that unauthenticated users are redirected."""
    user = User.objects.create_user(username="user", password="pass")
    survey = Survey.objects.create(owner=user, name="Test", slug="test")
    
    # Don't log in
    url = reverse("surveys:survey_detail", kwargs={"slug": survey.slug})
    response = client.get(url)
    
    # Should redirect to login
    assert response.status_code == 302
```

**Note:** Permission tests are extensively covered in:

- `census_app/surveys/tests/test_permissions.py` - Survey access permissions
- `census_app/surveys/tests/test_question_conditions_permissions.py` - Condition editing permissions
- `census_app/surveys/tests/test_anonymous_access.py` - Anonymous user access

Refer to these files for examples of testing role-based permissions, ownership checks, and access control.

## Question Creation Tests

The question builder allows creating questions through web forms. Tests verify all question types work correctly.

### Testing Basic Question Types

```python
def test_create_text_question(self, client):
    """Test creating a basic text question."""
    user = User.objects.create_user(username="testuser", password="testpass")
    survey = Survey.objects.create(owner=user, name="Test Survey", slug="test")
    client.force_login(user)
    
    url = reverse("surveys:builder_question_create", kwargs={"slug": survey.slug})
    
    response = client.post(
        url,
        {
            "text": "What is your name?",
            "type": "text",
            "text_format": "free",
            "required": "on",
        },
        HTTP_HX_REQUEST="true",  # HTMX request header
    )
    
    assert response.status_code == 200
    assert b"Question created." in response.content
    
    # Verify database
    question = SurveyQuestion.objects.get(survey=survey)
    assert question.text == "What is your name?"
    assert question.type == SurveyQuestion.Types.TEXT
    assert question.required is True
    assert question.options == [{"type": "text", "format": "free"}]
```

### Testing Multiple Choice Questions

Multiple choice questions require options:

```python
def test_create_mc_single_question(self, client):
    """Test creating a multiple choice (single) question."""
    user, survey = self.setup_survey(client)
    url = reverse("surveys:builder_question_create", kwargs={"slug": survey.slug})
    
    response = client.post(
        url,
        {
            "text": "What is your favorite color?",
            "type": "mc_single",
            "options": "Red\nBlue\nGreen\n",  # Newline-separated
            "required": "on",
        },
        HTTP_HX_REQUEST="true",
    )
    
    assert response.status_code == 200
    question = SurveyQuestion.objects.get(survey=survey)
    assert question.type == SurveyQuestion.Types.MULTIPLE_CHOICE_SINGLE
    
    # Webapp creates options with label/value structure
    assert len(question.options) == 3
    assert question.options[0] == {"label": "Red", "value": "Red"}
    assert question.options[1] == {"label": "Blue", "value": "Blue"}
    assert question.options[2] == {"label": "Green", "value": "Green"}
```

### Testing Follow-up Text Inputs

The webapp uses a different format than the API for follow-up text:

```python
def test_create_mc_single_with_followup_text(self, client):
    """Test creating MC question with follow-up text input."""
    user, survey = self.setup_survey(client)
    url = reverse("surveys:builder_question_create", kwargs={"slug": survey.slug})
    
    response = client.post(
        url,
        {
            "text": "How did you hear about us?",
            "type": "mc_single",
            "options": "Friend\nSocial Media\nOther",
            # Follow-up on option index 2 ("Other")
            "option_2_followup": "on",
            "option_2_followup_label": "Please specify",
        },
        HTTP_HX_REQUEST="true",
    )
    
    assert response.status_code == 200
    question = SurveyQuestion.objects.get(survey=survey)
    
    # First two options have no follow-up
    assert "followup_text" not in question.options[0]
    assert "followup_text" not in question.options[1]
    
    # Third option has follow-up
    assert "followup_text" in question.options[2]
    assert question.options[2]["followup_text"]["enabled"] is True
    assert question.options[2]["followup_text"]["label"] == "Please specify"
```

### Testing Yes/No Follow-ups

Yes/No questions use a different format for follow-ups:

```python
def test_create_yesno_with_followup_on_yes(self, client):
    """Test creating yes/no question with follow-up on yes."""
    user, survey = self.setup_survey(client)
    url = reverse("surveys:builder_question_create", kwargs={"slug": survey.slug})
    
    response = client.post(
        url,
        {
            "text": "Do you have allergies?",
            "type": "yesno",
            "yesno_yes_followup": "on",  # Note the different format
            "yesno_yes_followup_label": "List allergies",
        },
        HTTP_HX_REQUEST="true",
    )
    
    assert response.status_code == 200
    question = SurveyQuestion.objects.get(survey=survey)
    
    # "Yes" option (index 0) has follow-up
    assert "followup_text" in question.options[0]
    assert question.options[0]["followup_text"]["enabled"] is True
    assert question.options[0]["followup_text"]["label"] == "List allergies"
    
    # "No" option (index 1) does not
    assert "followup_text" not in question.options[1]
```

### Testing Likert Scale Questions

Likert scales can use numeric ranges or categories:

```python
def test_create_likert_numeric_scale(self, client):
    """Test creating Likert with numeric scale."""
    user, survey = self.setup_survey(client)
    url = reverse("surveys:builder_question_create", kwargs={"slug": survey.slug})
    
    response = client.post(
        url,
        {
            "text": "Rate your satisfaction",
            "type": "likert",
            "likert_mode": "number",
            "likert_min": "1",
            "likert_max": "5",
            "likert_left_label": "Not satisfied",
            "likert_right_label": "Very satisfied",
        },
        HTTP_HX_REQUEST="true",
    )
    
    assert response.status_code == 200
    question = SurveyQuestion.objects.get(survey=survey)
    assert question.options[0]["type"] == "number-scale"
    assert question.options[0]["min"] == 1
    assert question.options[0]["max"] == 5

def test_create_likert_categories(self, client):
    """Test creating Likert with categories."""
    user, survey = self.setup_survey(client)
    url = reverse("surveys:builder_question_create", kwargs={"slug": survey.slug})
    
    response = client.post(
        url,
        {
            "text": "How do you feel?",
            "type": "likert",
            "likert_mode": "categories",
            "likert_categories": "1\n2\n3\n4\n5",
        },
        HTTP_HX_REQUEST="true",
    )
    
    assert response.status_code == 200
    question = SurveyQuestion.objects.get(survey=survey)
    assert question.options == ["1", "2", "3", "4", "5"]
```

## Testing Question Groups

Questions can be created within groups:

```python
def test_create_question_in_group(self, client):
    """Test creating a question within a specific group."""
    user, survey = self.setup_survey(client)
    group = QuestionGroup.objects.create(name="Demographics", owner=user)
    survey.question_groups.add(group)
    
    url = reverse(
        "surveys:builder_group_question_create",
        kwargs={"slug": survey.slug, "gid": group.id},
    )
    
    response = client.post(
        url,
        {
            "text": "What is your age?",
            "type": "text",
            "text_format": "number",
        },
        HTTP_HX_REQUEST="true",
    )
    
    assert response.status_code == 200
    question = SurveyQuestion.objects.get(survey=survey)
    assert question.group_id == group.id
    assert question.text == "What is your age?"
```

## Testing HTMX Interactions

Many views use HTMX for dynamic updates. Include the `HTTP_HX_REQUEST` header:

```python
def test_htmx_response(self, client):
    """Test HTMX partial response."""
    user, survey = self.setup_survey(client)
    url = reverse("surveys:builder_question_create", kwargs={"slug": survey.slug})
    
    response = client.post(
        url,
        {"text": "Test", "type": "text", "text_format": "free"},
        HTTP_HX_REQUEST="true",  # This header is important!
    )
    
    assert response.status_code == 200
    html = response.content.decode()
    
    # Should return partial HTML, not full page
    assert "Question created." in html
    assert "<!DOCTYPE html>" not in html  # Not a full page
```

## Testing Permissions and Access Control

### Owner Can Edit

```python
def test_owner_can_create_question(self, client):
    """Test that survey owner can create questions."""
    user = User.objects.create_user(username="owner", password="pass")
    survey = Survey.objects.create(owner=user, name="Test", slug="test")
    client.force_login(user)
    
    url = reverse("surveys:builder_question_create", kwargs={"slug": survey.slug})
    response = client.post(
        url,
        {"text": "Test", "type": "text", "text_format": "free"},
        HTTP_HX_REQUEST="true",
    )
    
    assert response.status_code == 200
    assert SurveyQuestion.objects.filter(survey=survey).exists()
```

### Non-Owner Cannot Edit

```python
def test_non_owner_cannot_create_question(self, client):
    """Test that non-owners cannot create questions."""
    owner = User.objects.create_user(username="owner", password="pass")
    other_user = User.objects.create_user(username="other", password="pass")
    survey = Survey.objects.create(owner=owner, name="Test", slug="test")
    
    client.force_login(other_user)  # Log in as different user
    
    url = reverse("surveys:builder_question_create", kwargs={"slug": survey.slug})
    response = client.post(
        url,
        {"text": "Test", "type": "text", "text_format": "free"},
        HTTP_HX_REQUEST="true",
    )
    
    assert response.status_code == 403  # Forbidden
    assert SurveyQuestion.objects.filter(survey=survey).count() == 0
```

### Unauthenticated Users Redirected

```python
def test_unauthenticated_cannot_create_question(self, client):
    """Test that unauthenticated users are redirected."""
    user = User.objects.create_user(username="owner", password="pass")
    survey = Survey.objects.create(owner=user, name="Test", slug="test")
    # Don't log in
    
    url = reverse("surveys:builder_question_create", kwargs={"slug": survey.slug})
    response = client.post(
        url,
        {"text": "Test", "type": "text", "text_format": "free"},
        HTTP_HX_REQUEST="true",
    )
    
    # Should redirect to login or return 403
    assert response.status_code in [302, 403]
    assert SurveyQuestion.objects.filter(survey=survey).count() == 0
```

## Testing Form Validation

### Edge Cases

```python
def test_create_question_with_empty_text(self, client):
    """Test creating a question with empty text defaults to 'Untitled'."""
    user, survey = self.setup_survey(client)
    url = reverse("surveys:builder_question_create", kwargs={"slug": survey.slug})
    
    response = client.post(
        url,
        {
            "text": "",  # Empty text
            "type": "text",
            "text_format": "free",
        },
        HTTP_HX_REQUEST="true",
    )
    
    assert response.status_code == 200
    question = SurveyQuestion.objects.get(survey=survey)
    assert question.text == "Untitled"  # Default value

def test_whitespace_trimmed_from_options(self, client):
    """Test that whitespace is trimmed from options."""
    user, survey = self.setup_survey(client)
    url = reverse("surveys:builder_question_create", kwargs={"slug": survey.slug})
    
    response = client.post(
        url,
        {
            "text": "Choose",
            "type": "mc_single",
            "options": "  Option 1  \n  Option 2  \n  \n  Option 3  ",
        },
        HTTP_HX_REQUEST="true",
    )
    
    assert response.status_code == 200
    question = SurveyQuestion.objects.get(survey=survey)
    # Empty lines filtered out, whitespace trimmed
    assert len(question.options) == 3
    assert question.options[0]["label"] == "Option 1"
    assert question.options[1]["label"] == "Option 2"
    assert question.options[2]["label"] == "Option 3"
```

## Testing Question Ordering

```python
def test_new_questions_get_incremental_order(self, client):
    """Test that new questions are assigned incremental order values."""
    user, survey = self.setup_survey(client)
    url = reverse("surveys:builder_question_create", kwargs={"slug": survey.slug})
    
    for i in range(3):
        client.post(
            url,
            {
                "text": f"Question {i + 1}",
                "type": "text",
                "text_format": "free",
            },
            HTTP_HX_REQUEST="true",
        )
    
    questions = SurveyQuestion.objects.filter(survey=survey).order_by("order")
    assert questions.count() == 3
    assert questions[0].order == 1
    assert questions[1].order == 2
    assert questions[2].order == 3
```

## Testing Response Content

### Success Messages

```python
def test_create_returns_success_message(self, client):
    """Test that create returns success message in response."""
    user, survey = self.setup_survey(client)
    url = reverse("surveys:builder_question_create", kwargs={"slug": survey.slug})
    
    response = client.post(
        url,
        {"text": "Test Question", "type": "text", "text_format": "free"},
        HTTP_HX_REQUEST="true",
    )
    
    assert response.status_code == 200
    html = response.content.decode()
    assert "Question created." in html
    assert "Test Question" in html
```

### Script Payloads for JavaScript

```python
def test_create_includes_builder_payload(self, client):
    """Test that response includes data payload for JavaScript."""
    user, survey = self.setup_survey(client)
    url = reverse("surveys:builder_question_create", kwargs={"slug": survey.slug})
    
    response = client.post(
        url,
        {"text": "Test", "type": "text", "text_format": "free"},
        HTTP_HX_REQUEST="true",
    )
    
    assert response.status_code == 200
    question = SurveyQuestion.objects.get(survey=survey)
    html = response.content.decode()
    
    # Should have a script tag with question data
    script_id = f"question-data-{question.id}"
    assert script_id in html
```

## Best Practices

### 1. Use URL Reverse Lookups

Always use `reverse()` instead of hardcoding URLs:

```python
# Good
url = reverse("surveys:builder_question_create", kwargs={"slug": survey.slug})

# Avoid
url = f"/surveys/{survey.slug}/builder/question/create/"
```

### 2. Test Database Changes

Don't just check HTTP responses - verify database state:

```python
response = client.post(url, data)
assert response.status_code == 200

# Also check database
question = SurveyQuestion.objects.get(survey=survey)
assert question.text == "Expected"
```

### 3. Test Both GET and POST

```python
def test_form_displays(self, client):
    """Test that form page displays."""
    user, survey = self.setup_survey(client)
    url = reverse("surveys:some_form", kwargs={"slug": survey.slug})
    
    response = client.get(url)
    assert response.status_code == 200
    assert "form" in response.context

def test_form_submission(self, client):
    """Test form submission."""
    user, survey = self.setup_survey(client)
    url = reverse("surveys:some_form", kwargs={"slug": survey.slug})
    
    response = client.post(url, {"field": "value"})
    assert response.status_code == 302  # Redirect after success
```

### 4. Use `force_login()` for Authenticated Tests

```python
# Good - faster, more direct
client.force_login(user)

# Avoid - slower, indirect
client.login(username="user", password="pass")
```

### 5. Clean Test Names

```python
# Good
def test_owner_can_edit_question(self, client):

# Avoid
def test_edit(self, client):
```

## Common Patterns

### Testing All Question Types

```python
@pytest.mark.parametrize("qtype,extra_data", [
    ("text", {"text_format": "free"}),
    ("mc_single", {"options": "A\nB\nC"}),
    ("mc_multi", {"options": "A\nB\nC"}),
    ("dropdown", {"options": "A\nB\nC"}),
    ("yesno", {}),
    ("orderable", {"options": "A\nB\nC"}),
])
def test_create_all_question_types(self, client, qtype, extra_data):
    """Test creating all valid question types."""
    user, survey = self.setup_survey(client)
    url = reverse("surveys:builder_question_create", kwargs={"slug": survey.slug})
    
    data = {"text": f"Test {qtype}", "type": qtype}
    data.update(extra_data)
    
    response = client.post(url, data, HTTP_HX_REQUEST="true")
    assert response.status_code == 200
```

### Testing Context Data

```python
def test_view_context(self, client):
    """Test that view provides correct context."""
    user, survey = self.setup_survey(client)
    url = reverse("surveys:survey_detail", kwargs={"slug": survey.slug})
    
    response = client.get(url)
    
    assert response.status_code == 200
    assert "survey" in response.context
    assert response.context["survey"] == survey
    assert "questions" in response.context
```

## Differences from API Testing

| Aspect | API Tests | Webapp Tests |
|--------|-----------|--------------|
| Authentication | JWT tokens in headers | `client.force_login()` |
| Request format | JSON with `content_type` | Form data (dict) |
| Headers | `HTTP_AUTHORIZATION` | `HTTP_HX_REQUEST` for HTMX |
| Response | JSON data | HTML content |
| Options format | Simple arrays/objects | `{label, value}` structure |
| Follow-up format | `has_followup`, `followup_label` | `followup_text: {enabled, label}` |
| Follow-up keys | In options array | `option_N_followup` form fields |

## Troubleshooting

### Test Fails with 302 Redirect

- User not logged in - use `client.force_login(user)`
- Check if view requires authentication

### Test Fails with 403 Forbidden

- User lacks permissions - check ownership/roles
- See permission test files for examples

### HTMX Response Differs

- Ensure `HTTP_HX_REQUEST="true"` header is included
- HTMX responses return partials, not full pages

### Options Format Different Than Expected

- Webapp creates `{label, value}` structure
- API uses simpler formats
- Follow-up text structure differs between webapp and API

## Reference Tests

For comprehensive examples, see:

- `census_app/surveys/tests/test_builder_question_creation.py` - 23 tests covering question creation
- `census_app/surveys/tests/test_builder_editing.py` - Question editing and copying
- `census_app/surveys/tests/test_permissions.py` - Permission patterns
- `census_app/surveys/tests/test_groups_reorder.py` - HTMX interactions and reordering
- `census_app/surveys/tests/test_anonymous_access.py` - Anonymous user handling
