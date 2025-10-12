# Using the API

This guide provides comprehensive documentation for creating and managing surveys via the API, including all supported question types, JSON structure, and advanced features.

## Question Types

Census supports the following question types when creating surveys via the API:

### Text (`text`)

Free-text input for short or long answers.

```json
{
  "text": "What is your feedback?",
  "type": "text",
  "order": 1
}
```

**Optional fields:**
- `required` (boolean): Whether the question must be answered
- `help_text` (string): Additional guidance shown to respondents

### Number (`number`)

Numeric input only.

```json
{
  "text": "What is your age?",
  "type": "number",
  "order": 2
}
```

### Multiple Choice - Single Select (`mc_single`)

Radio button selection - respondents can choose only one option.

**Simple format:**

```json
{
  "text": "What is your favorite color?",
  "type": "mc_single",
  "options": ["Red", "Blue", "Green", "Other"],
  "order": 3
}
```

**Rich format with follow-up text:**

```json
{
  "text": "What is your favorite color?",
  "type": "mc_single",
  "options": [
    {"label": "Red", "value": "red"},
    {"label": "Blue", "value": "blue"},
    {"label": "Green", "value": "green"},
    {
      "label": "Other",
      "value": "other",
      "followup_text": {
        "enabled": true,
        "label": "Please specify your favorite color"
      }
    }
  ],
  "order": 3
}
```

### Multiple Choice - Multi Select (`mc_multi`)

Checkbox selection - respondents can choose multiple options.

**Simple format:**

```json
{
  "text": "Which languages do you speak?",
  "type": "mc_multi",
  "options": ["English", "Spanish", "French", "German", "Other"],
  "order": 4
}
```

**Rich format with follow-up text:**

```json
{
  "text": "Which languages do you speak?",
  "type": "mc_multi",
  "options": [
    {"label": "English", "value": "english"},
    {"label": "Spanish", "value": "spanish"},
    {"label": "French", "value": "french"},
    {
      "label": "Other",
      "value": "other",
      "followup_text": {
        "enabled": true,
        "label": "Please specify which other languages"
      }
    }
  ],
  "order": 4
}
```

### Dropdown (`dropdown`)

Select dropdown - single selection from a list.

**Simple format:**

```json
{
  "text": "Select your country",
  "type": "dropdown",
  "options": ["USA", "UK", "Canada", "Australia", "Other"],
  "order": 5
}
```

**Rich format with follow-up text:**

```json
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
        "enabled": true,
        "label": "Please specify your country"
      }
    }
  ],
  "order": 5
}
```

### Yes/No (`yesno`)

Boolean choice presented as Yes/No radio buttons.

**Simple format:**

```json
{
  "text": "Do you have any concerns?",
  "type": "yesno",
  "order": 6
}
```

**Rich format with follow-up text:**

```json
{
  "text": "Do you have any concerns?",
  "type": "yesno",
  "options": [
    {
      "label": "Yes",
      "value": "yes",
      "followup_text": {
        "enabled": true,
        "label": "Please describe your concerns"
      }
    },
    {"label": "No", "value": "no"}
  ],
  "order": 6
}
```

### Likert Scale (`likert`)

Numeric or categorical scale rating.

**Numeric scale:**

```json
{
  "text": "How satisfied are you?",
  "type": "likert",
  "options": {
    "min": 1,
    "max": 5,
    "min_label": "Very Dissatisfied",
    "max_label": "Very Satisfied"
  },
  "order": 7
}
```

**Categorical scale:**

```json
{
  "text": "How often do you exercise?",
  "type": "likert",
  "options": ["Never", "Rarely", "Sometimes", "Often", "Always"],
  "order": 8
}
```

### Orderable List (`orderable`)

Drag-and-drop list where respondents rank options.

**Simple format:**

```json
{
  "text": "Rank these features by importance",
  "type": "orderable",
  "options": ["Speed", "Reliability", "Cost", "Support"],
  "order": 9
}
```

**Rich format with follow-up text:**

```json
{
  "text": "Rank these features by importance",
  "type": "orderable",
  "options": [
    {"label": "Speed", "value": "speed"},
    {"label": "Reliability", "value": "reliability"},
    {"label": "Cost", "value": "cost"},
    {
      "label": "Other",
      "value": "other",
      "followup_text": {
        "enabled": true,
        "label": "What other feature is important to you?"
      }
    }
  ],
  "order": 9
}
```

### Image Choice (`image`)

Visual selection where respondents choose from image options.

```json
{
  "text": "Select your preferred design",
  "type": "image",
  "options": [
    {"label": "Design A", "value": "design_a", "image_url": "/static/images/design_a.png"},
    {"label": "Design B", "value": "design_b", "image_url": "/static/images/design_b.png"}
  ],
  "order": 10
}
```

## Follow-up Text Inputs

For certain question types, you can configure **follow-up text inputs** that appear conditionally based on the respondent's answer. This is useful when you need additional detail for specific options.

### Supported Question Types

Follow-up text inputs are supported for:

- `mc_single` (Multiple choice - single select)
- `mc_multi` (Multiple choice - multi select)
- `dropdown`
- `orderable`
- `yesno`

### Configuration Format

To enable a follow-up text input for a specific option, use the rich object format and add a `followup_text` property:

```json
{
  "label": "Option label",
  "value": "option_value",
  "followup_text": {
    "enabled": true,
    "label": "Custom prompt for the follow-up input"
  }
}
```

### Response Data Format

When a survey response includes follow-up text, the answers will contain both the main answer and follow-up fields:

```json
{
  "q_123": "other",
  "q_123_followup_2": "I prefer a custom solution that fits my specific needs"
}
```

Follow-up fields use the naming pattern:

- `q_{question_id}_followup_{option_index}` for multiple choice, dropdown, and orderable questions
- `q_{question_id}_followup_{yes|no}` for Yes/No questions

### Example: Multiple Choice with Follow-up

```json
{
  "text": "How did you hear about us?",
  "type": "mc_single",
  "options": [
    {"label": "Social Media", "value": "social"},
    {"label": "Friend/Colleague", "value": "referral"},
    {"label": "Search Engine", "value": "search"},
    {
      "label": "Other",
      "value": "other",
      "followup_text": {
        "enabled": true,
        "label": "Please tell us how you heard about us"
      }
    }
  ],
  "order": 1
}
```

If a respondent selects "Other" and types "Industry conference", the response data will be:

```json
{
  "q_42": "other",
  "q_42_followup_3": "Industry conference"
}
```

## Common JSON Keys

All question types support these common fields:

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `text` | string | Yes | The question text shown to respondents |
| `type` | string | Yes | Question type (see above) |
| `order` | integer | Yes | Display order within the group |
| `required` | boolean | No | Whether the question must be answered (default: false) |
| `help_text` | string | No | Additional guidance or instructions |
| `options` | array/object | Varies | Required for mc_single, mc_multi, dropdown, orderable, likert, image |

### Options Field Format

The `options` field can be:

1. **Array of strings** (simple format):
   ```json
   ["Option 1", "Option 2", "Option 3"]
   ```

2. **Array of objects** (rich format with follow-up support):
   ```json
   [
     {"label": "Option 1", "value": "opt1"},
     {"label": "Option 2", "value": "opt2", "followup_text": {"enabled": true, "label": "Please explain"}}
   ]
   ```

3. **Object with scale properties** (for likert numeric scales):
   ```json
   {
     "min": 1,
     "max": 5,
     "min_label": "Strongly Disagree",
     "max_label": "Strongly Agree"
   }
   ```

## Complete Example: Seeding a Survey

Here's a complete example of seeding a survey with multiple question types:

```json
[
  {
    "text": "What is your name?",
    "type": "text",
    "required": true,
    "order": 1
  },
  {
    "text": "What is your age?",
    "type": "number",
    "order": 2
  },
  {
    "text": "Do you have any dietary restrictions?",
    "type": "yesno",
    "options": [
      {
        "label": "Yes",
        "value": "yes",
        "followup_text": {
          "enabled": true,
          "label": "Please describe your dietary restrictions"
        }
      },
      {"label": "No", "value": "no"}
    ],
    "order": 3
  },
  {
    "text": "Which of these apply to you?",
    "type": "mc_multi",
    "options": [
      {"label": "Student", "value": "student"},
      {"label": "Employed", "value": "employed"},
      {"label": "Retired", "value": "retired"},
      {
        "label": "Other",
        "value": "other",
        "followup_text": {
          "enabled": true,
          "label": "Please specify"
        }
      }
    ],
    "order": 4
  },
  {
    "text": "How satisfied are you with our service?",
    "type": "likert",
    "options": {
      "min": 1,
      "max": 5,
      "min_label": "Very Dissatisfied",
      "max_label": "Very Satisfied"
    },
    "order": 5
  }
]
```

## API Endpoint

To seed questions for a survey, use the seed endpoint:

```
POST /api/surveys/{survey_id}/seed/
```

**Authentication:** Requires JWT token and ownership or organization ADMIN role.

**Request body:** JSON array of question objects (as shown in examples above).

**Response:** Returns the created questions with their assigned IDs.

## Best Practices

1. **Use the rich format** when you need follow-up text inputs or want explicit control over option values
2. **Use the simple format** for straightforward questions without follow-up inputs
3. **Set appropriate `order` values** to control the sequence of questions
4. **Use `required: true`** sparingly - only for essential questions
5. **Provide clear `help_text`** for complex questions
6. **Test follow-up logic** to ensure conditional inputs appear correctly

## See Also

- [Getting Started with the API](getting-started-api.md) - Authentication and basic API usage
- [Surveys](surveys.md) - Creating surveys via the web interface
