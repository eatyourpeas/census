# Bulk survey import

The survey builder supports uploading a complete survey definition written in Markdown. This is convenient when:

- You already have the survey designed in a document and prefer to import the structure instead of dragging and dropping questions in the visual builder.
- You want to lay out complex flows with repeatable sections or branching logic before wiring the final details in the UI.

This document captures the grammar the importer recognises and the conventions that keep identifiers stable when you later edit the survey.

## Authoring overview

Place the Markdown in the **Import questions** form for the survey you are editing. When you confirm the import, the system removes all existing question groups and questions owned by that survey and replaces them with the imported content. Collections, repeat groups, and branching conditions are created automatically. You can refine question copy, options, and wiring inside the builder after the import.

A minimal survey looks like this:

```markdown
# Group title
Group description

## Question title
Question description
(type)
```

Spacing is flexible, but keep the relative order (heading → optional description → type). Blank lines are ignored.

## Group headings

- Use `# <group title>` for each group.
- The first non-empty line after the heading (if it is not a question heading or type declaration) becomes the group description.
- Optionally append a stable identifier by placing it in curly braces at the end of the heading: `# Group title {group-id}`. The importer slugifies the identifier and keeps it unique.

## Question headings

- Use `## <question title>` inside a group.
- The next non-empty line that is not a type declaration becomes the question description.
- Declare the question type on a dedicated line wrapped in parentheses: `(text)`, `(mc_single)`, etc.
- Append a stable identifier with curly braces just like groups: `## Question {question-id}`.
- **Mark a question as required** by adding an asterisk `*` after the question title (before the ID if present): `## Question title* {question-id}`.

### Supported question types

| Type name | Description |
| --- | --- |
| `text` | Free-text short answer |
| `text number` | Numeric input validation |
| `mc_single` | Multiple choice (single answer) |
| `mc_multi` | Multiple choice (multiple answers) |
| `dropdown` | Select menu |
| `orderable` | Rank the provided items |
| `yesno` | Yes/No toggle |
| `image` | Image choice |
| `likert categories` | Likert scale with category labels (one per `-` line) |
| `likert number` | Likert scale defined by number range |

### Options and Likert metadata

- For option-based questions, supply each option on its own line starting with `-` (hyphen + space).
- **Follow-up text inputs**: To add a follow-up text field for any option, add an indented line starting with `+` (plus + space) immediately after the option. The text after `+` becomes the label for the follow-up input field that appears when the participant selects that option.
- For `likert number`, add key-value metadata lines after the type:
  - `min: 1`
  - `max: 5`
  - Optional `left:` and `right:` labels.

**Example with follow-up text:**

```markdown
## Employment status
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
```

**Follow-up guidelines:**

- Follow-up lines must start with `+` and be indented (at least 2 spaces or a tab)
- The text after `+` becomes the label for the follow-up input field
- Works with `mc_single`, `mc_multi`, `dropdown`, `orderable`, and `yesno` question types
- For `yesno` questions, you can optionally provide 2 options (for Yes and No) with follow-up labels
- Not all options need follow-ups—only add them where additional context is needed
- Follow-up responses are stored alongside the selected option in the survey response

## Required questions

Mark a question as required by adding an asterisk `*` immediately after the question title. Required questions must be answered before participants can submit the form.

**Example:**

```markdown
## Age* {patient-age}
Age in years
(text number)

## Email address*
Please provide your email
(text)

## Consent to participate* {consent}
(yesno)
```

**Guidelines:**

- Place the asterisk directly after the question title, before any identifier in curly braces
- Works with all question types
- Required questions are validated on form submission
- The asterisk will appear in red in the preview

## Preview Viewer

The bulk upload also has a real-time preview viewer. As the user enters markdown the view renders it below - this is helpful because a unique identifier for each question and question-group automatically renders in the preview. This is needed if you choose to use the branching notation (see below).

## Additional Function

Users may not want to use this function and the bulk uploader works without it. Users may simply want to convert a word document to mark down and import the questions wholesale - they can add function for repeat questions (such as patients) or conditional branching in the question builder afterwards. But for those who wish to use the importer here, then it is possible to use the notation described below for some questions or groups to be iterative or show conditionally depending on answers that users give. This is detailed below.

### Repeatable collections

You can mark a group as repeatable so respondents can add multiple entries (e.g., visits, household members). Place `REPEAT` on the line immediately above the group heading.

```markdown
REPEAT-5
# Patient details

> REPEAT
> # Visit
> ...
```

Guidelines:

- `REPEAT` allows unlimited repeats; `REPEAT-5` limits the maximum to five entries; `REPEAT-1` means one allowed.
- Use `>` to indicate nested collections and repeat the `REPEAT` marker at the same depth as the child group heading.
- Nesting is limited to one level (parent → child). Deeper levels are ignored.
- Groups without a preceding `REPEAT` line become normal, non-collection groups.

### Conditional branching

Branching rules let you jump respondents to other questions or groups based on their answers. They follow this pattern, placed under the `(type)` line:

```markdown
? when <operator> <value> -> {target-id}
```

Example:

```markdown
# Intro {intro}
## Consent {intro-consent}
(text)
? when equals "Yes" -> {follow-up}
? when equals "No" -> {intro-exit}
```

Notes:

- Operators match the in-app condition builder: `equals`, `not_equals`, `contains`, `greater_than`, `greater_equal`, `less_than`, `exists`, and their `not_` variants.
- Values may be quoted. Operators like `exists` do not take a value.
- The target in curly braces can reference a group ID (jump to that group) or a question ID (jump directly to the question).
- IDs are normalised to lowercase slugs; ensure each ID is unique across all groups and questions.

## Workflow tips

1. Draft the structure in Markdown using a familiar editor or export from a specification document.
2. Paste the Markdown into the bulk import form and review the live preview to confirm IDs, repeat badges, and branch targets look correct.
3. When ready, choose **Create survey**, acknowledge the overwrite warning, and import. The importer recreates question groups, questions, branching conditions, and collections.
4. Use the visual builder to fine-tune wording, add advanced logic, or connect the imported sections with additional navigation rules.

## Troubleshooting

- **Missing (type)**: Every question must declare a type on the line immediately after the description. The importer fails with a helpful error referencing the question title.
- **Unknown IDs**: Branch targets must refer to an existing group or question ID. Check the live preview to confirm spelling.
- **Duplicate IDs**: If two headings share the same curly-brace ID, the importer automatically de-duplicates by appending `-2`, `-3`, etc. Prefer choosing distinct IDs yourself for clarity.
- **Collections without groups**: A `REPEAT` marker must be followed by a valid group heading at the same nesting level.

Refer back to this guide whenever you need to import surveys in bulk or explain the syntax to collaborators.
