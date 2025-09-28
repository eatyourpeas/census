# Surveys

This guide explains how to create an organization, create a survey, and how content is structured into question groups and questions.

## Organizations

Organizations own surveys and manage access. Each organization has:

- Owner — the user who created the org
- Members — users with roles: Admin, Creator, Viewer

Admins can manage members and surveys. Creators can build and manage surveys. Viewers can view responses/analytics (when enabled) but cannot edit structure.

## Create an organization

1. Sign up or log in
2. Go to Profile
3. Click “Upgrade to organization” and enter a name

You’ll become an Admin and can invite others from the User management area.

## Create a survey

1. Go to Surveys
2. Click “Create survey”
3. Choose an organisation (optional), name, and slug (this is the name that appears in the url so should have no spaces but words can be hyphenated)
4. Save to open the survey dashboard

From the dashboard you can set style/branding, manage members, and build content.

## Question groups vs questions

Question Groups are the building blocks for structuring a survey. They act like chapters: each group has a title, optional description, and an ordered list of questions. Groups keep longer surveys manageable, let you show section-specific instructions, and provide obvious breakpoints when branching to different parts of a journey. Questions can be reordered within a group, and groups themselves can be reordered from the builder sidebar.

Questions live inside a single group. When you add a question, the builder automatically associates it with the group you have open. Moving a question to another group updates that association immediately—there is no detached “question bank.” If you delete a group, its questions are also deleted. This ensures that every question always has a clear place in the survey hierarchy.

You can bulk import questions when you already have content drafted. Uploading Markdown via the bulk upload option lets you specify groups and questions in a single document: top-level headings become groups, and nested headings/items become questions. After import you can continue refining groups and questions in the builder UI.

## Question types

Supported types (as of now):

- Free text (`text`) or (`number`): short/long text answers or numbers
- Multiple choice — single (`mc_single`)
- Multiple choice — multiple (`mc_multi`)
- Dropdown (`dropdown`)
- Likert scale (`likert`): numeric or descriptor/categorical scales
- Yes/No (`yesno`)
- Orderable list (`orderable`): reorder options
- Image choice (`image`): choose from visual options

Some types use options metadata. Examples:

- `mc_single` / `mc_multi` / `dropdown` / `image`: provide a list of options
- `likert`: provide min/max, labels (e.g., 1–5 with left/right captions)
- `text`: optional format hint (e.g., constrained formats) used in previews

You can preview questions in the builder, reorder them, and group them as needed.

### Conditional branching

Individual questions can define conditional logic that determines what a respondent sees next. Branching is configured per question from the “Logic” tab in the builder:

- **Show/Hide conditions** — Display a question only when previous answers match the criteria you set (e.g., show follow-up questions when someone answers "Yes").
- **Skip logic** — Jump the respondent to another question group once they pick a certain answer. This is useful for ending a survey early or routing different audiences to tailored sections.
- **Option-level rules** — For multiple-choice questions you can create separate rules for each option. For free-text or numeric answers, use comparators (equals, greater than, contains, etc.) to match values.

The logic engine evaluates conditions in order, so place the most specific rule first. A question without any conditions simply follows the survey’s default ordering. When branching sends a respondent to a later group, intervening groups are skipped automatically.

**Tip:** Keep at least one unconditional path through every group so respondents cannot get trapped. In testing environments the builder logs a warning when conditional tables are missing—run the latest migrations before enabling branching in production.

## Managing access to surveys

- Add survey members with roles (Creator, Viewer)
- Organization Admins can manage any survey within their org
- Survey Creators can edit structure and manage members for that survey

## Next steps

- See Branding and Theme Settings to customize appearance
- See Getting Started with the API to seed questions programmatically
