"""
Test for follow-up question feature in markdown import.
Run with: docker compose exec -T web pytest test_followup_import.py -v
"""

import pytest

from census_app.surveys.markdown_import import parse_bulk_markdown_with_collections


@pytest.fixture
def test_markdown():
    """Sample markdown with follow-up questions across different question types."""
    return """
# Employment Survey {employment}
Questions about employment status

## Employment status* {employment-status}
What is your current employment status?
(mc_single)
- Employed full-time
- Employed part-time
  + Please specify your hours per week
- Self-employed
  + What type of business?
- Unemployed
  + Are you actively seeking employment?
- Student
- Retired

## Skills {employment-skills}
Select all that apply
(mc_multi)
- Python
  + Years of experience?
- JavaScript
- SQL
  + Which databases?
- Other

## Preferred work mode* {work-mode}
How do you prefer to work?
(dropdown)
- Office-based
  + Which location?
- Remote
  + Do you have a dedicated workspace?
- Hybrid

## Open to relocation {relocation}
Would you relocate for the right opportunity?
(yesno)
- Yes
  + Which regions are you considering?
- No
  + Is there anything that would change your mind?
"""


@pytest.fixture
def test_markdown_required():
    """Sample markdown testing required field parsing."""
    return """
# Contact Information {contact}

## Full name* {contact-name}
(text)

## Email address* {contact-email}
(text)

## Phone number {contact-phone}
Optional contact number
(text number)

## Preferred contact method*
(mc_single)
- Email
- Phone
- Text message
"""


def test_followup_import_parses_successfully(test_markdown):
    """Test that markdown with follow-up questions parses without errors."""
    parsed = parse_bulk_markdown_with_collections(test_markdown)
    assert parsed is not None
    groups = parsed.get("groups", [])
    assert len(groups) == 1


def test_followup_import_creates_correct_group_structure(test_markdown):
    """Test that the parsed structure contains the expected group and questions."""
    parsed = parse_bulk_markdown_with_collections(test_markdown)
    groups = parsed.get("groups", [])

    employment_group = groups[0]
    assert employment_group["name"] == "Employment Survey"
    assert employment_group["ref"] == "employment"

    questions = employment_group.get("questions", [])
    assert len(questions) == 4


def test_followup_mc_single_option_structure(test_markdown):
    """Test mc_single question with follow-up questions."""
    parsed = parse_bulk_markdown_with_collections(test_markdown)
    employment_group = parsed["groups"][0]
    employment_status_q = employment_group["questions"][0]

    assert employment_status_q["type"] == "mc_single"
    assert employment_status_q["title"] == "Employment status"

    options = employment_status_q["final_options"]
    assert len(options) == 6

    # Check option without follow-up
    full_time_opt = options[0]
    assert full_time_opt["label"] == "Employed full-time"
    # Options without follow-ups may not have followup_text key or have it disabled
    assert full_time_opt.get("followup_text", {}).get("enabled", False) is False

    # Check option with follow-up
    part_time_opt = options[1]
    assert part_time_opt["label"] == "Employed part-time"
    assert part_time_opt["followup_text"]["enabled"] is True
    assert (
        part_time_opt["followup_text"]["label"] == "Please specify your hours per week"
    )

    # Check another option with follow-up
    self_employed_opt = options[2]
    assert self_employed_opt["followup_text"]["enabled"] is True
    assert self_employed_opt["followup_text"]["label"] == "What type of business?"


def test_followup_mc_multi_option_structure(test_markdown):
    """Test mc_multi question with follow-up questions."""
    parsed = parse_bulk_markdown_with_collections(test_markdown)
    skills_q = parsed["groups"][0]["questions"][1]

    assert skills_q["type"] == "mc_multi"
    assert skills_q["title"] == "Skills"

    options = skills_q["final_options"]
    assert len(options) == 4

    # Python option has follow-up
    python_opt = options[0]
    assert python_opt["label"] == "Python"
    assert python_opt["followup_text"]["enabled"] is True
    assert python_opt["followup_text"]["label"] == "Years of experience?"

    # JavaScript option has no follow-up
    js_opt = options[1]
    assert js_opt["label"] == "JavaScript"
    assert js_opt.get("followup_text", {}).get("enabled", False) is False

    # SQL option has follow-up
    sql_opt = options[2]
    assert sql_opt["followup_text"]["enabled"] is True
    assert sql_opt["followup_text"]["label"] == "Which databases?"


def test_followup_dropdown_option_structure(test_markdown):
    """Test dropdown question with follow-up questions."""
    parsed = parse_bulk_markdown_with_collections(test_markdown)
    work_mode_q = parsed["groups"][0]["questions"][2]

    assert work_mode_q["type"] == "dropdown"
    assert work_mode_q["title"] == "Preferred work mode"

    options = work_mode_q["final_options"]
    assert len(options) == 3

    # Office-based has follow-up
    office_opt = options[0]
    assert office_opt["label"] == "Office-based"
    assert office_opt["followup_text"]["enabled"] is True
    assert office_opt["followup_text"]["label"] == "Which location?"

    # Remote has follow-up
    remote_opt = options[1]
    assert remote_opt["followup_text"]["enabled"] is True
    assert remote_opt["followup_text"]["label"] == "Do you have a dedicated workspace?"

    # Hybrid has no follow-up
    hybrid_opt = options[2]
    assert hybrid_opt["label"] == "Hybrid"
    assert hybrid_opt.get("followup_text", {}).get("enabled", False) is False


def test_followup_yesno_option_structure(test_markdown):
    """Test yesno question with follow-up questions on both options."""
    parsed = parse_bulk_markdown_with_collections(test_markdown)
    relocation_q = parsed["groups"][0]["questions"][3]

    assert relocation_q["type"] == "yesno"
    assert relocation_q["title"] == "Open to relocation"

    options = relocation_q["final_options"]
    assert len(options) == 2

    # Both Yes and No have follow-ups
    yes_opt = options[0]
    assert yes_opt["label"] == "Yes"
    assert yes_opt["followup_text"]["enabled"] is True
    assert yes_opt["followup_text"]["label"] == "Which regions are you considering?"

    no_opt = options[1]
    assert no_opt["label"] == "No"
    assert no_opt["followup_text"]["enabled"] is True
    assert (
        no_opt["followup_text"]["label"]
        == "Is there anything that would change your mind?"
    )


def test_followup_data_structure_matches_api_format(test_markdown):
    """Test that the data structure matches the API/webapp format for options with follow-ups."""
    parsed = parse_bulk_markdown_with_collections(test_markdown)

    # Check every option in every question has the correct structure
    for group in parsed["groups"]:
        for question in group["questions"]:
            # Use final_options which contains the converted dict format
            options = question.get("final_options", [])
            if isinstance(options, list):
                for opt in options:
                    if isinstance(opt, dict):
                        # Every dict option must have label and value
                        assert "label" in opt
                        assert "value" in opt
                        assert isinstance(opt["label"], str)
                        assert isinstance(opt["value"], str)

                        # If followup_text exists, validate its structure
                        if "followup_text" in opt:
                            followup = opt["followup_text"]
                            assert "enabled" in followup
                            assert "label" in followup
                            assert isinstance(followup["enabled"], bool)
                            assert isinstance(followup["label"], str)


def test_required_field_parsing(test_markdown_required):
    """Test that asterisks in question titles are parsed as required flag."""
    parsed = parse_bulk_markdown_with_collections(test_markdown_required)

    assert parsed is not None
    groups = parsed.get("groups", [])
    assert len(groups) == 1

    contact_group = groups[0]
    questions = contact_group["questions"]
    assert len(questions) == 4

    # Full name - required
    name_q = questions[0]
    assert name_q["title"] == "Full name"
    assert name_q["required"] is True

    # Email - required
    email_q = questions[1]
    assert email_q["title"] == "Email address"
    assert email_q["required"] is True

    # Phone - not required
    phone_q = questions[2]
    assert phone_q["title"] == "Phone number"
    assert phone_q["required"] is False

    # Preferred contact method - required
    contact_method_q = questions[3]
    assert contact_method_q["title"] == "Preferred contact method"
    assert contact_method_q["required"] is True


def test_required_with_followup_combined(test_markdown):
    """Test that required field works together with follow-up questions."""
    parsed = parse_bulk_markdown_with_collections(test_markdown)

    employment_group = parsed["groups"][0]

    # Employment status - required with follow-ups
    employment_status_q = employment_group["questions"][0]
    assert employment_status_q["title"] == "Employment status"
    assert employment_status_q["required"] is True
    assert employment_status_q["final_options"][1]["followup_text"]["enabled"] is True

    # Skills - not required
    skills_q = employment_group["questions"][1]
    assert skills_q["title"] == "Skills"
    assert skills_q["required"] is False

    # Preferred work mode - required with follow-ups
    work_mode_q = employment_group["questions"][2]
    assert work_mode_q["title"] == "Preferred work mode"
    assert work_mode_q["required"] is True
    assert work_mode_q["final_options"][0]["followup_text"]["enabled"] is True

    # Open to relocation - not required
    relocation_q = employment_group["questions"][3]
    assert relocation_q["title"] == "Open to relocation"
    assert relocation_q["required"] is False


def test_required_asterisk_with_id(test_markdown):
    """Test that asterisk is correctly parsed when question has an ID."""
    parsed = parse_bulk_markdown_with_collections(test_markdown)

    employment_group = parsed["groups"][0]
    employment_status_q = employment_group["questions"][0]

    # Should extract asterisk, preserve title and ID
    assert employment_status_q["title"] == "Employment status"
    assert employment_status_q["ref"] == "employment-status"
    assert employment_status_q["required"] is True
