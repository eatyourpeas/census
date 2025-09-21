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

- Question Groups: logical sections in a survey (e.g., Demographics, Background, Outcomes). These contain several questions that tend to go together.
- Questions: individual prompts within a group. There are different question types that can be selected from a menu.

You can bulk import questions if you have a survey already to go in an document. You can use Markdown (see Bulk upload in the survey). Groups help keep longer surveys organized and can enable per-section instructions.

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

## Managing access to surveys

- Add survey members with roles (Creator, Viewer)
- Organization Admins can manage any survey within their org
- Survey Creators can edit structure and manage members for that survey

## Next steps

- See Branding and Theme Settings to customize appearance
- See Getting Started with the API to seed questions programmatically
