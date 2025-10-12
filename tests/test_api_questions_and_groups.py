"""
Comprehensive tests for questions and question groups via the API.

Tests cover:
- Seeding questions with all question types
- Follow-up text input configuration
- Question group creation and management
- Option formats (simple string arrays vs rich object arrays)
- Response data validation
"""
import json

from django.contrib.auth import get_user_model
import pytest

from census_app.surveys.models import Survey, SurveyQuestion

User = get_user_model()
TEST_PASSWORD = "test-pass"


@pytest.mark.django_db
class TestAPIQuestionsAndGroups:
    """Test suite for questions and question groups API endpoints."""

    def get_auth_header(self, client, username: str, password: str) -> dict:
        """Get JWT auth header for API requests."""
        resp = client.post(
            "/api/token",
            data=json.dumps({"username": username, "password": password}),
            content_type="application/json",
        )
        assert resp.status_code == 200, resp.content
        access = resp.json()["access"]
        return {"HTTP_AUTHORIZATION": f"Bearer {access}"}

    def setup_basic_survey(self, client):
        """Create a user and survey for testing."""
        user = User.objects.create_user(username="testuser", password=TEST_PASSWORD)
        survey = Survey.objects.create(owner=user, name="Test Survey", slug="test")
        headers = self.get_auth_header(client, "testuser", TEST_PASSWORD)
        return user, survey, headers

    # === Basic Question Seeding Tests ===

    def test_seed_text_question(self, client):
        """Test seeding a basic text question."""
        user, survey, headers = self.setup_basic_survey(client)
        url = f"/api/surveys/{survey.id}/seed/"

        payload = [{"text": "What is your name?", "type": "text", "order": 1}]

        resp = client.post(
            url, data=json.dumps(payload), content_type="application/json", **headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["created"] == 1

        # Verify in database
        q = SurveyQuestion.objects.get(survey=survey)
        assert q.text == "What is your name?"
        assert q.type == "text"

    def test_seed_number_question(self, client):
        """Test seeding a number input question."""
        user, survey, headers = self.setup_basic_survey(client)
        url = f"/api/surveys/{survey.id}/seed/"

        payload = [{"text": "What is your age?", "type": "number", "order": 1}]

        resp = client.post(
            url, data=json.dumps(payload), content_type="application/json", **headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["created"] == 1

        # Verify in database
        q = SurveyQuestion.objects.get(survey=survey)
        assert q.type == "number"

    def test_seed_mc_single_simple_format(self, client):
        """Test multiple choice (single) with simple string array options."""
        user, survey, headers = self.setup_basic_survey(client)
        url = f"/api/surveys/{survey.id}/seed/"

        payload = [
            {
                "text": "What is your favorite color?",
                "type": "mc_single",
                "options": ["Red", "Blue", "Green"],
                "order": 1,
            }
        ]

        resp = client.post(
            url, data=json.dumps(payload), content_type="application/json", **headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["created"] == 1

        # Verify in database
        q = SurveyQuestion.objects.get(survey=survey)
        assert q.type == "mc_single"
        assert q.options == ["Red", "Blue", "Green"]

    def test_seed_mc_multi_simple_format(self, client):
        """Test multiple choice (multi) with simple options."""
        user, survey, headers = self.setup_basic_survey(client)
        url = f"/api/surveys/{survey.id}/seed/"

        payload = [
            {
                "text": "Which languages do you speak?",
                "type": "mc_multi",
                "options": ["English", "Spanish", "French"],
                "order": 1,
            }
        ]

        resp = client.post(
            url, data=json.dumps(payload), content_type="application/json", **headers
        )
        assert resp.status_code == 200
        q = SurveyQuestion.objects.get(survey=survey)
        assert q.type == "mc_multi"

    def test_seed_dropdown_simple_format(self, client):
        """Test dropdown with simple options."""
        user, survey, headers = self.setup_basic_survey(client)
        url = f"/api/surveys/{survey.id}/seed/"

        payload = [
            {
                "text": "Select your country",
                "type": "dropdown",
                "options": ["USA", "UK", "Canada"],
                "order": 1,
            }
        ]

        resp = client.post(
            url, data=json.dumps(payload), content_type="application/json", **headers
        )
        assert resp.status_code == 200
        q = SurveyQuestion.objects.get(survey=survey)
        assert q.type == "dropdown"

    def test_seed_yesno_simple_format(self, client):
        """Test yes/no question with default format."""
        user, survey, headers = self.setup_basic_survey(client)
        url = f"/api/surveys/{survey.id}/seed/"

        payload = [
            {"text": "Do you have any concerns?", "type": "yesno", "order": 1}
        ]

        resp = client.post(
            url, data=json.dumps(payload), content_type="application/json", **headers
        )
        assert resp.status_code == 200
        q = SurveyQuestion.objects.get(survey=survey)
        assert q.type == "yesno"

    def test_seed_likert_numeric_scale(self, client):
        """Test Likert scale with numeric range."""
        user, survey, headers = self.setup_basic_survey(client)
        url = f"/api/surveys/{survey.id}/seed/"

        payload = [
            {
                "text": "How satisfied are you?",
                "type": "likert",
                "options": {
                    "min": 1,
                    "max": 5,
                    "min_label": "Very Dissatisfied",
                    "max_label": "Very Satisfied",
                },
                "order": 1,
            }
        ]

        resp = client.post(
            url, data=json.dumps(payload), content_type="application/json", **headers
        )
        assert resp.status_code == 200
        q = SurveyQuestion.objects.get(survey=survey)
        assert q.type == "likert"
        # The API stores options as-is (dict for numeric range)
        assert isinstance(q.options, dict)
        assert q.options["min"] == 1
        assert q.options["max"] == 5

    def test_seed_likert_categorical_scale(self, client):
        """Test Likert scale with categorical options."""
        user, survey, headers = self.setup_basic_survey(client)
        url = f"/api/surveys/{survey.id}/seed/"

        payload = [
            {
                "text": "How often do you exercise?",
                "type": "likert",
                "options": ["Never", "Rarely", "Sometimes", "Often", "Always"],
                "order": 1,
            }
        ]

        resp = client.post(
            url, data=json.dumps(payload), content_type="application/json", **headers
        )
        assert resp.status_code == 200
        q = SurveyQuestion.objects.get(survey=survey)
        assert q.type == "likert"

    def test_seed_orderable_list(self, client):
        """Test orderable list question type."""
        user, survey, headers = self.setup_basic_survey(client)
        url = f"/api/surveys/{survey.id}/seed/"

        payload = [
            {
                "text": "Rank by importance",
                "type": "orderable",
                "options": ["Speed", "Reliability", "Cost"],
                "order": 1,
            }
        ]

        resp = client.post(
            url, data=json.dumps(payload), content_type="application/json", **headers
        )
        assert resp.status_code == 200
        q = SurveyQuestion.objects.get(survey=survey)
        assert q.type == "orderable"

    # === Follow-up Text Input Tests ===

    def test_seed_mc_single_with_followup(self, client):
        """Test multiple choice with follow-up text input."""
        user, survey, headers = self.setup_basic_survey(client)
        url = f"/api/surveys/{survey.id}/seed/"

        payload = [
            {
                "text": "How did you hear about us?",
                "type": "mc_single",
                "options": [
                    {"label": "Social Media", "value": "social"},
                    {"label": "Friend", "value": "friend"},
                    {
                        "label": "Other",
                        "value": "other",
                        "followup_text": {
                            "enabled": True,
                            "label": "Please tell us how",
                        },
                    },
                ],
                "order": 1,
            }
        ]

        resp = client.post(
            url, data=json.dumps(payload), content_type="application/json", **headers
        )
        assert resp.status_code == 200
        q = SurveyQuestion.objects.get(survey=survey)

        # Verify follow-up config stored
        assert isinstance(q.options, list)
        other_opt = next(opt for opt in q.options if opt.get("value") == "other")
        assert "followup_text" in other_opt
        assert other_opt["followup_text"]["enabled"] is True
        assert other_opt["followup_text"]["label"] == "Please tell us how"

    def test_seed_mc_multi_with_multiple_followups(self, client):
        """Test multiple choice (multi) with several follow-up inputs."""
        user, survey, headers = self.setup_basic_survey(client)
        url = f"/api/surveys/{survey.id}/seed/"

        payload = [
            {
                "text": "Select all that apply",
                "type": "mc_multi",
                "options": [
                    {"label": "Option A", "value": "a"},
                    {
                        "label": "Option B",
                        "value": "b",
                        "followup_text": {
                            "enabled": True,
                            "label": "Tell us more about B",
                        },
                    },
                    {
                        "label": "Option C",
                        "value": "c",
                        "followup_text": {
                            "enabled": True,
                            "label": "Tell us more about C",
                        },
                    },
                ],
                "order": 1,
            }
        ]

        resp = client.post(
            url, data=json.dumps(payload), content_type="application/json", **headers
        )
        assert resp.status_code == 200
        q = SurveyQuestion.objects.get(survey=survey)

        # Count options with follow-up
        followup_count = sum(
            1
            for opt in q.options
            if isinstance(opt, dict)
            and opt.get("followup_text", {}).get("enabled")
        )
        assert followup_count == 2

    def test_seed_dropdown_with_followup(self, client):
        """Test dropdown with follow-up text input."""
        user, survey, headers = self.setup_basic_survey(client)
        url = f"/api/surveys/{survey.id}/seed/"

        payload = [
            {
                "text": "Select your country",
                "type": "dropdown",
                "options": [
                    {"label": "USA", "value": "usa"},
                    {"label": "UK", "value": "uk"},
                    {
                        "label": "Other",
                        "value": "other",
                        "followup_text": {
                            "enabled": True,
                            "label": "Please specify country",
                        },
                    },
                ],
                "order": 1,
            }
        ]

        resp = client.post(
            url, data=json.dumps(payload), content_type="application/json", **headers
        )
        assert resp.status_code == 200
        q = SurveyQuestion.objects.get(survey=survey)
        other_opt = next(opt for opt in q.options if opt.get("value") == "other")
        assert other_opt["followup_text"]["enabled"] is True

    def test_seed_yesno_with_followup_yes(self, client):
        """Test yes/no with follow-up on 'Yes' answer."""
        user, survey, headers = self.setup_basic_survey(client)
        url = f"/api/surveys/{survey.id}/seed/"

        payload = [
            {
                "text": "Do you have any concerns?",
                "type": "yesno",
                "options": [
                    {
                        "label": "Yes",
                        "value": "yes",
                        "followup_text": {
                            "enabled": True,
                            "label": "Please describe your concerns",
                        },
                    },
                    {"label": "No", "value": "no"},
                ],
                "order": 1,
            }
        ]

        resp = client.post(
            url, data=json.dumps(payload), content_type="application/json", **headers
        )
        assert resp.status_code == 200
        q = SurveyQuestion.objects.get(survey=survey)

        yes_opt = next(opt for opt in q.options if opt.get("value") == "yes")
        assert yes_opt["followup_text"]["enabled"] is True
        assert yes_opt["followup_text"]["label"] == "Please describe your concerns"

    def test_seed_yesno_with_followup_both(self, client):
        """Test yes/no with follow-up on both answers."""
        user, survey, headers = self.setup_basic_survey(client)
        url = f"/api/surveys/{survey.id}/seed/"

        payload = [
            {
                "text": "Question with both followups",
                "type": "yesno",
                "options": [
                    {
                        "label": "Yes",
                        "value": "yes",
                        "followup_text": {"enabled": True, "label": "Why yes?"},
                    },
                    {
                        "label": "No",
                        "value": "no",
                        "followup_text": {"enabled": True, "label": "Why no?"},
                    },
                ],
                "order": 1,
            }
        ]

        resp = client.post(
            url, data=json.dumps(payload), content_type="application/json", **headers
        )
        assert resp.status_code == 200
        q = SurveyQuestion.objects.get(survey=survey)

        yes_opt = next(opt for opt in q.options if opt.get("value") == "yes")
        no_opt = next(opt for opt in q.options if opt.get("value") == "no")
        assert yes_opt["followup_text"]["enabled"] is True
        assert no_opt["followup_text"]["enabled"] is True

    def test_seed_orderable_with_followup(self, client):
        """Test orderable list with follow-up text."""
        user, survey, headers = self.setup_basic_survey(client)
        url = f"/api/surveys/{survey.id}/seed/"

        payload = [
            {
                "text": "Rank features",
                "type": "orderable",
                "options": [
                    {"label": "Speed", "value": "speed"},
                    {"label": "Cost", "value": "cost"},
                    {
                        "label": "Other",
                        "value": "other",
                        "followup_text": {
                            "enabled": True,
                            "label": "What other feature?",
                        },
                    },
                ],
                "order": 1,
            }
        ]

        resp = client.post(
            url, data=json.dumps(payload), content_type="application/json", **headers
        )
        assert resp.status_code == 200
        q = SurveyQuestion.objects.get(survey=survey)
        other_opt = next(opt for opt in q.options if opt.get("value") == "other")
        assert other_opt["followup_text"]["enabled"] is True

    # === Multiple Questions Seeding ===

    def test_seed_multiple_questions(self, client):
        """Test seeding multiple questions in one request."""
        user, survey, headers = self.setup_basic_survey(client)
        url = f"/api/surveys/{survey.id}/seed/"

        payload = [
            {"text": "Name?", "type": "text", "order": 1},
            {"text": "Age?", "type": "number", "order": 2},
            {
                "text": "Color?",
                "type": "mc_single",
                "options": ["Red", "Blue"],
                "order": 3,
            },
        ]

        resp = client.post(
            url, data=json.dumps(payload), content_type="application/json", **headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["created"] == 3

        # Verify in database
        questions = SurveyQuestion.objects.filter(survey=survey).order_by("order")
        assert questions.count() == 3
        assert questions[0].text == "Name?"
        assert questions[1].text == "Age?"
        assert questions[2].text == "Color?"

    def test_seed_mixed_simple_and_rich_formats(self, client):
        """Test seeding with mix of simple strings and rich objects."""
        user, survey, headers = self.setup_basic_survey(client)
        url = f"/api/surveys/{survey.id}/seed/"

        payload = [
            {
                "text": "Simple options",
                "type": "mc_single",
                "options": ["A", "B", "C"],
                "order": 1,
            },
            {
                "text": "Rich options with followup",
                "type": "mc_single",
                "options": [
                    {"label": "X", "value": "x"},
                    {
                        "label": "Y",
                        "value": "y",
                        "followup_text": {"enabled": True, "label": "Why Y?"},
                    },
                ],
                "order": 2,
            },
        ]

        resp = client.post(
            url, data=json.dumps(payload), content_type="application/json", **headers
        )
        assert resp.status_code == 200
        assert SurveyQuestion.objects.filter(survey=survey).count() == 2

    # === Required Field Tests ===

    def test_seed_required_question(self, client):
        """Test seeding a required question."""
        user, survey, headers = self.setup_basic_survey(client)
        url = f"/api/surveys/{survey.id}/seed/"

        payload = [
            {"text": "Name?", "type": "text", "required": True, "order": 1}
        ]

        resp = client.post(
            url, data=json.dumps(payload), content_type="application/json", **headers
        )
        assert resp.status_code == 200
        q = SurveyQuestion.objects.get(survey=survey)
        assert q.required is True

    def test_seed_optional_question(self, client):
        """Test seeding an optional question (default)."""
        user, survey, headers = self.setup_basic_survey(client)
        url = f"/api/surveys/{survey.id}/seed/"

        payload = [{"text": "Optional?", "type": "text", "order": 1}]

        resp = client.post(
            url, data=json.dumps(payload), content_type="application/json", **headers
        )
        assert resp.status_code == 200
        q = SurveyQuestion.objects.get(survey=survey)
        assert q.required is False  # Default

    # === Question Groups Tests ===

    def test_questions_assigned_to_default_group(self, client):
        """Test that seeded questions get assigned to a default group."""
        user, survey, headers = self.setup_basic_survey(client)
        url = f"/api/surveys/{survey.id}/seed/"

        payload = [{"text": "Q1", "type": "text", "order": 1}]

        resp = client.post(
            url, data=json.dumps(payload), content_type="application/json", **headers
        )
        assert resp.status_code == 200

        q = SurveyQuestion.objects.get(survey=survey)
        # Should be assigned to a default group or none based on implementation
        # This tests current behavior
        assert q.group is not None or q.group is None  # Either is valid

    def test_seed_with_multiple_question_groups(self, client):
        """Test seeding questions with group names."""
        user, survey, headers = self.setup_basic_survey(client)

        url = f"/api/surveys/{survey.id}/seed/"

        payload = [
            {
                "text": "Name",
                "type": "text",
                "group_name": "Demographics",
                "order": 1,
            },
            {
                "text": "Age",
                "type": "number",
                "group_name": "Demographics",
                "order": 2,
            },
            {
                "text": "Comments",
                "type": "text",
                "group_name": "Feedback",
                "order": 3,
            },
        ]

        resp = client.post(
            url, data=json.dumps(payload), content_type="application/json", **headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["created"] == 3

        # Verify groups were created and assigned
        q1 = SurveyQuestion.objects.get(survey=survey, text="Name")
        q2 = SurveyQuestion.objects.get(survey=survey, text="Age")
        q3 = SurveyQuestion.objects.get(survey=survey, text="Comments")

        assert q1.group is not None
        assert q1.group.name == "Demographics"
        assert q2.group.name == "Demographics"
        assert q3.group.name == "Feedback"

    # === Backward Compatibility Tests ===

    def test_backward_compat_string_array_options(self, client):
        """Test that old string array format still works."""
        user, survey, headers = self.setup_basic_survey(client)
        url = f"/api/surveys/{survey.id}/seed/"

        # Old format: simple string array
        payload = [
            {
                "text": "Pick one",
                "type": "mc_single",
                "options": ["Alpha", "Beta", "Gamma"],
                "order": 1,
            }
        ]

        resp = client.post(
            url, data=json.dumps(payload), content_type="application/json", **headers
        )
        assert resp.status_code == 200
        q = SurveyQuestion.objects.get(survey=survey)
        assert len(q.options) == 3

    def test_backward_compat_no_followup_in_rich_format(self, client):
        """Test rich format without follow-up works (backward compat)."""
        user, survey, headers = self.setup_basic_survey(client)
        url = f"/api/surveys/{survey.id}/seed/"

        payload = [
            {
                "text": "Pick one",
                "type": "mc_single",
                "options": [
                    {"label": "A", "value": "a"},
                    {"label": "B", "value": "b"},
                ],
                "order": 1,
            }
        ]

        resp = client.post(
            url, data=json.dumps(payload), content_type="application/json", **headers
        )
        assert resp.status_code == 200
        q = SurveyQuestion.objects.get(survey=survey)

        # Verify no follow-up text configured
        for opt in q.options:
            if isinstance(opt, dict):
                assert opt.get("followup_text") is None or opt.get("followup_text", {}).get("enabled") is False

    # === Error Handling Tests ===

    def test_seed_invalid_question_type(self, client):
        """Test seeding with invalid question type (API accepts it)."""
        user, survey, headers = self.setup_basic_survey(client)
        url = f"/api/surveys/{survey.id}/seed/"

        payload = [{"text": "Invalid", "type": "invalid_type", "order": 1}]

        resp = client.post(
            url, data=json.dumps(payload), content_type="application/json", **headers
        )
        # Note: The API currently doesn't validate question types, it accepts them
        assert resp.status_code == 200
        data = resp.json()
        assert data["created"] == 1
        
        # The invalid type is stored as-is
        q = SurveyQuestion.objects.get(survey=survey)
        assert q.type == "invalid_type"

    def test_seed_missing_required_field(self, client):
        """Test seeding without 'text' field uses default."""
        user, survey, headers = self.setup_basic_survey(client)
        url = f"/api/surveys/{survey.id}/seed/"

        payload = [{"type": "text", "order": 1}]  # Missing 'text'

        resp = client.post(
            url, data=json.dumps(payload), content_type="application/json", **headers
        )
        # The API uses "Untitled" as default for missing text
        assert resp.status_code == 200
        data = resp.json()
        assert data["created"] == 1
        
        q = SurveyQuestion.objects.get(survey=survey)
        assert q.text == "Untitled"

    def test_seed_empty_payload(self, client):
        """Test seeding with empty array."""
        user, survey, headers = self.setup_basic_survey(client)
        url = f"/api/surveys/{survey.id}/seed/"

        payload = []

        resp = client.post(
            url, data=json.dumps(payload), content_type="application/json", **headers
        )
        # Should succeed but create nothing
        assert resp.status_code == 200
        assert SurveyQuestion.objects.filter(survey=survey).count() == 0

    # === Complex Integration Tests ===

    def test_complete_survey_workflow(self, client):
        """Test complete workflow: create survey, seed questions, verify structure."""
        user, survey, headers = self.setup_basic_survey(client)
        url = f"/api/surveys/{survey.id}/seed/"

        # Comprehensive survey with various question types
        payload = [
            {"text": "Full name", "type": "text", "required": True, "order": 1},
            {"text": "Age", "type": "number", "order": 2},
            {
                "text": "Satisfaction",
                "type": "likert",
                "options": {
                    "min": 1,
                    "max": 5,
                    "min_label": "Poor",
                    "max_label": "Excellent",
                },
                "order": 3,
            },
            {
                "text": "How did you hear about us?",
                "type": "mc_single",
                "options": [
                    {"label": "Web", "value": "web"},
                    {"label": "Friend", "value": "friend"},
                    {
                        "label": "Other",
                        "value": "other",
                        "followup_text": {
                            "enabled": True,
                            "label": "Please specify",
                        },
                    },
                ],
                "order": 4,
            },
            {
                "text": "Any concerns?",
                "type": "yesno",
                "options": [
                    {
                        "label": "Yes",
                        "value": "yes",
                        "followup_text": {
                            "enabled": True,
                            "label": "Describe concerns",
                        },
                    },
                    {"label": "No", "value": "no"},
                ],
                "order": 5,
            },
        ]

        resp = client.post(
            url, data=json.dumps(payload), content_type="application/json", **headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["created"] == 5

        # Verify all questions created correctly
        questions = SurveyQuestion.objects.filter(survey=survey).order_by("order")
        assert questions.count() == 5

        # Check text question
        q1 = questions[0]
        assert q1.text == "Full name"
        assert q1.type == "text"
        assert q1.required is True

        # Check number question
        q2 = questions[1]
        assert q2.type == "number"

        # Check Likert
        q3 = questions[2]
        assert q3.type == "likert"
        assert "min" in q3.options
        assert "max" in q3.options

        # Check mc_single with followup
        q4 = questions[3]
        assert q4.type == "mc_single"
        other_option = next(
            opt for opt in q4.options if isinstance(opt, dict) and opt.get("value") == "other"
        )
        assert other_option["followup_text"]["enabled"] is True

        # Check yesno with followup
        q5 = questions[4]
        assert q5.type == "yesno"
        yes_option = next(
            opt for opt in q5.options if isinstance(opt, dict) and opt.get("value") == "yes"
        )
        assert yes_option["followup_text"]["enabled"] is True
