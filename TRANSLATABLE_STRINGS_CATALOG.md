# Complete Translatable Strings Catalog

This document contains all **259 unique translatable strings** in the Census application that need to be translated into 11 languages.

## Overview

**Total strings to translate:** 259 unique strings

**Target languages:**

- Arabic (ar) - 0% complete
- Welsh (cy) - 0% complete
- German (de) - 0% complete
- Spanish (es) - 0% complete
- French (fr) - **45% complete** (149/330 strings including duplicates)
- Hindi (hi) - 0% complete
- Italian (it) - 0% complete
- Polish (pl) - 0% complete
- Portuguese (pt) - 0% complete
- Urdu (ur) - 0% complete
- Simplified Chinese (zh-hans) - 0% complete

**Total translation work needed:** 259 strings × 11 languages = **2,849 translations**

**Note:** The French .po file contains 330 entries (some strings appear multiple times in different templates). This catalog lists the 259 unique strings.

---

## Translation by Category

### Authentication & Account Management (30 strings)

User authentication, login, password reset, and account creation.

- Login to start
- Email preferences updated successfully.
- There was an error updating your email preferences.
- Authenticated: login required · Public: open link · Unlisted: secret link · Invite: token required
- Admin login
- Forgotten your password or username?
- Password
- Forgot password?
- Password updated
- Your password has been changed successfully.
- Change password
- Change your password
- Save new password
- Go to login
- Password reset complete
- Your password has been set. You can now log in with your new password.
- This password reset link is invalid or has expired.
- Check your email
- If an account exists with that email, we've sent a password reset link. Please follow the instructions in the email to reset your password.
- In development, the reset email is printed to the console.
- Reset email sent
- Enter the email address associated with your account.
- Reset your password
- Account Type
- Already have an account?
- Create account
- Create your account
- Organisation Account
- Sign up
- Sign up to start creating surveys and collecting responses.

### Survey Management (80 strings)

Survey creation, editing, publishing, deletion, and management.

- Create a survey
- Drag-and-drop groups and questions, apply DaisyUI themes per survey, and control collection repeats.
- Go to Surveys
- Invite your team, scope visibility by organisation and survey membership, and manage roles.
- Manage surveys
- Surveys for health care
- This application is in development currently and should NOT be used for live surveys where patient identifiable information is collected.
- Organisation created. You are now an organisation admin and can host surveys and add members.
- All Questions
- Create and manage groups, then add questions inside each group.
- Open a group
- Question Group Builder
- `# Group Title`, followed by a line for the group description
- `## Question Title`, followed by a line for the question description
- Assign stable IDs by placing them in curly braces at the end of group or question titles
- Branching rules must start with `? when` and reference a question or group ID
- Groups and questions are assigned unique IDs as you edit. Use these IDs to reassign existing groups/questions if you need to regenerate them from markdown.
- Groups without REPEAT are normal, non-collection groups.
- Import questions
- Importing from Markdown will delete all existing question groups, questions, branching rules, and repeats. This action cannot be undone.
- Mark a question as required by adding an asterisk `*` immediately after the question title
- Operators mirror the survey builder: `equals`, `not_equals`, `contains`, `not_contains`, `greater_than`, `less_than`
- Optional: Questions with conditional branching
- Optional: Required questions
- Overwrite survey questions?
- Place the asterisk immediately after the question title text
- Point to a group ID to jump to that group, or a question ID to jump directly to that question
- Required questions must be answered before the form can be submitted
- Start typing (or use the sample markdown) to see the survey structure.
- To define a child collection nested under a repeatable parent, indent with `>` before the child's REPEAT line and `#` heading
- To mark a group as repeatable, add a line with **REPEAT** (or **REPEAT-min-max**, e.g., **REPEAT-1-5**) immediately before the `#` heading
- Use `>` before REPEAT and the group heading to indicate one level of nesting (e.g., child collection under a parent)
- Works with all question types
- Create Survey
- Create a new survey
- **Groups** are reusable sets of questions. You can mark one or more groups as a **repeat** (collection), allowing users to add multiple instances of those groups when filling out the survey.
- Delete this survey
- Draft: build only · Published: accept submissions · Closed: stop submissions
- I confirm no **patient-identifiable data** is collected in this survey
- Keep track of survey status, number of responses and control styling.
- Max responses
- No submissions yet
- Once deleted, all data, responses, groups, and permissions will be permanently removed. This action cannot be undone.
- Require CAPTCHA for anonymous submissions
- Survey style
- Total responses
- All associated groups and questions
- All survey data and responses
- Delete Survey Permanently
- Deleting this survey will permanently remove:
- To confirm deletion, please type the survey name exactly as shown above:
- Type survey name here
- You are about to permanently delete the survey:
- You must type the survey name to confirm deletion.
- Manage Questions
- No questions in this group yet.
- Question Group
- Question Groups
- Questions in this group
- Create new question group
- Delete this group?
- New group name
- No groups yet. Create one to get started.
- Question Groups are reusable sets of questions. Arrange them here to control the order in which participants see them.
- Remove this group from its repeat?
- Tip: Select groups by clicking their row or checkbox, then click 'Create repeat' to set a name. Selected groups become part of the repeat.
- Groups
- No surveys yet.
- Survey users
- Back to survey
- Your response has been recorded.
- Enter the one-time survey key to decrypt sensitive fields for this session.
- Survey Dashboard
- Survey key
- Unlock Survey
- Add user to survey
- No surveys yet
- Survey slug
- Users by survey
- Create surveys and manage your own responses

### Form Elements & Validation (16 strings)

Form fields, inputs, validation, and configuration options.

- Choose your preferred language. This affects all text in the application.
- Choose your theme. This only affects your view and is saved in your browser.
- Add a follow-up text input to any option by adding an indented line starting with `+`
- For `yesno`, provide exactly 2 options (Yes/No) with optional follow-ups
- For Likert number scales, add key-value lines: `min:`, `max:`, and optional `min_label:`, `max_label:`
- Optional: Collections with REPEAT
- Optional: Follow-up text inputs
- The text after `+` becomes the label for the follow-up input field
- provide `min`/`max` and optional labels
- select menu
- URL Name or 'Slug' (optional)
- Create repeat from selection
- Nest under existing (optional)
- Selected for repeat
- selected
- (optional)

### UI Components & Navigation (16 strings)

Buttons, links, menus, and navigation elements.

- Monitor dashboards, export CSV, and audit changes. Everything runs on a secure platform designed for health research.
- View dashboards
- Organisation created. You are an organisation admin.
- Live structure preview
- Preview (read-only)
- Public link
- Unlisted link
- Back to dashboard
- Create
- Create repeat
- Delete
- Preview
- Created
- Request a new link
- Send reset link
- Create an organisation to collaborate with a team

### Documentation & Help Text (3 strings)

Long-form explanatory text and documentation.

- For options that should have follow-up text input, add an indented line starting with `+` followed by the label text
- Works with `mc_single`, `mc_multi`, `dropdown`, and `yesno` question types
- Organisation names don't need to be unique. Multiple organisations can have the same name—you'll only see and manage your own.

### General UI Text (114 strings)

Labels, headings, status messages, and other general interface text.

- Analyze
- Census
- Distribute
- Explore docs
- Home
- See capabilities
- Appearance
- Dark
- Enable JavaScript to change theme.
- Language
- Light
- Save Language Preference
- Theme
- You have full administrative access to the platform
- You have staff-level access to the platform
- Your Profile
- Your badges
- Language preference updated successfully.
- Project theme saved.
- There was an error updating your language preference.
- `(type)` on the next line in parentheses
- **REPEAT** = unlimited repeats. **REPEAT-1** means only 1 allowed, **REPEAT-1-5** allows 1 to 5.
- Add `class=\\"required\\"` to mark a question as required
- Follow-up lines must start with `+` and be indented (at least 2 spaces)
- Format reference
- IDs are normalised to lowercase slugs; keep them unique within your document.
- If the type requires options, list each on a line starting with `-`
- Markdown
- Nesting is limited to one level (Parent → Child) by design.
- Not all options need follow-ups—only add them where needed
- Supported types
- The asterisk `*` method is recommended for simplicity
- Use markdown with the following structure:
- categories listed with `-`
- free text
- image choice
- multiple choice (multi)
- multiple choice (single)
- numeric input
- orderable list
- yes/no
- Description
- If left blank, a slug will be generated from the name.
- Name
- Authenticated
- Closed
- Danger Zone
- Draft
- End at
- Invite token
- Last 14 days
- Last 7 days
- Manage invite tokens
- Public
- Publish settings
- Published
- Save publish settings
- Start at
- Status
- Today
- Unlisted
- Window
- All access permissions and tokens
- All collection and publication records
- Warning: This action cannot be undone!
- No
- Professional details
- Submit
- Yes
- Cancel
- Clear
- Help
- Maximum items
- Minimum items
- Nesting is limited to one level.
- Remove repeat
- Repeat name
- Repeats
- Unlimited
- Import
- Organisation users
- Expires
- Expires at (ISO)
- Export CSV
- Generate
- How many
- Invite Tokens
- Invite tokens
- No tokens yet.
- Token
- Used
- Used by
- Unlock
- Add user to org
- No members
- No users yet
- Organisation
- You don't have an organisation to manage yet.
- Please correct the error below.
- Username
- Branch
- Built by
- Commit
- Contributing
- GitHub
- Issues
- Logout
- Releases
- User management
- Version
- Individual User
- Leave blank to use default name
- Note:
- Organisation Name
- e.g. Acme Health Research

---

## Files Containing Translatable Strings

The strings are distributed across **28 template files** in the application:

### Core Templates (4 files)

- `census_app/core/templates/home.html` - Home page, welcome content
- `census_app/core/templates/profile.html` - User profile, language/theme settings
- `census_app/core/templates/profile_badges.html` - User badges and achievements
- `census_app/templates/base.html` - Base template with navigation and footer

### Authentication Templates (6 files)

- `census_app/templates/admin/login.html` - Admin login page
- `census_app/templates/registration/login.html` - User login page
- `census_app/templates/registration/signup.html` - User registration
- `census_app/templates/registration/password_change_form.html` - Password change
- `census_app/templates/registration/password_change_done.html` - Password change confirmation
- `census_app/templates/registration/password_reset_form.html` - Password reset request
- `census_app/templates/registration/password_reset_done.html` - Reset email sent
- `census_app/templates/registration/password_reset_confirm.html` - Set new password
- `census_app/templates/registration/password_reset_complete.html` - Reset complete

### Survey Templates (15 files)

- `census_app/surveys/templates/surveys/create.html` - Survey creation form
- `census_app/surveys/templates/surveys/dashboard.html` - Survey management dashboard
- `census_app/surveys/templates/surveys/delete_confirm.html` - Survey deletion confirmation
- `census_app/surveys/templates/surveys/detail.html` - Survey detail/response view
- `census_app/surveys/templates/surveys/group_builder.html` - Question group builder
- `census_app/surveys/templates/surveys/groups.html` - Group management interface
- `census_app/surveys/templates/surveys/list.html` - Survey list
- `census_app/surveys/templates/surveys/markdown_import.html` - Markdown import interface
- `census_app/surveys/templates/surveys/org_users.html` - Organisation user management
- `census_app/surveys/templates/surveys/survey_users.html` - Survey user management
- `census_app/surveys/templates/surveys/thank_you.html` - Submission confirmation
- `census_app/surveys/templates/surveys/tokens.html` - Invite token management
- `census_app/surveys/templates/surveys/unlock.html` - Survey unlock page
- `census_app/surveys/templates/surveys/user_management_hub.html` - User management hub

### API Templates (3 files)

- `census_app/api/templates/api_docs/getting_started.html` - API getting started
- `census_app/api/templates/api_docs/index.html` - API documentation index
- `census_app/api/templates/api_docs/testing.html` - API testing guide

---

## Translation Guidelines

### General Principles

1. **Formal vs. Informal:** Use formal address ("vous" in French, "usted" in Spanish) for all user-facing text
2. **Technical Terms:** Keep technical terms in English when they are standard in the industry (e.g., "token", "API", "CSV")
3. **HTML Tags:** Preserve all HTML tags like `<strong>`, `<code>`, `<br>` exactly as they appear
4. **Placeholders:** Keep Django template variables like `{{ variable }}` unchanged
5. **Punctuation:** Follow target language conventions (e.g., French requires spaces before `:` and `!`)

### Medical Context

This application is designed for healthcare research and survey collection. Translations should:

- Use appropriate medical terminology
- Maintain professional, clinical tone
- Emphasize data security and privacy
- Be clear and unambiguous for healthcare professionals

### Pluralization

Some strings require plural forms (e.g., "1 survey" vs "2 surveys"). Django's gettext system handles this with `msgid_plural` entries in the .po files. Make sure to provide all required plural forms for each language.

### Testing Translations

After translating:

1. Compile translations: `docker compose exec web python manage.py compilemessages -l <lang_code>`
2. Test in the UI by selecting the language from the profile page
3. Check all major pages: home, login, signup, dashboard, survey creation
4. Verify plurals display correctly with different counts
5. Check for text overflow or layout issues

---

## Quick Reference

### Files to Edit

Each language has its own .po file in the `locale/` directory:

```text
locale/ar/LC_MESSAGES/django.po      # Arabic
locale/cy/LC_MESSAGES/django.po      # Welsh
locale/de/LC_MESSAGES/django.po      # German
locale/es/LC_MESSAGES/django.po      # Spanish
locale/fr/LC_MESSAGES/django.po      # French (45% complete)
locale/hi/LC_MESSAGES/django.po      # Hindi
locale/it/LC_MESSAGES/django.po      # Italian
locale/pl/LC_MESSAGES/django.po      # Polish
locale/pt/LC_MESSAGES/django.po      # Portuguese
locale/ur/LC_MESSAGES/django.po      # Urdu
locale/zh_Hans/LC_MESSAGES/django.po # Simplified Chinese
```

### Workflow

1. Open the appropriate `django.po` file for your target language
2. Find entries with empty `msgstr ""` values
3. Add the translation between the quotes: `msgstr "your translation"`
4. For plural forms, translate both `msgstr[0]` (singular) and `msgstr[1]` (plural)
5. Save the file
6. Compile: `docker compose exec web python manage.py compilemessages -l <code>`
7. Test in the application
8. Commit with message: `feat(i18n): <Language> translation progress`

### Common Translations Reference (French Example)

Establish consistent terminology:

- Survey → Enquête
- Question → Question
- Group → Groupe
- Dashboard → Tableau de bord
- Organisation → Organisation
- User → Utilisateur
- Response → Réponse
- Submit → Soumettre
- Create → Créer
- Delete → Supprimer
- Edit → Modifier
- Save → Enregistrer
- Cancel → Annuler
- Required → Requis
- Optional → Facultatif

---

## Progress Tracking

### Completed

- ✅ French (fr): 45% complete (149/330 entries including duplicates)

### In Progress

- 🟡 French (fr): 181 strings remaining

### Not Started

- ⏳ Arabic (ar): 0%
- ⏳ Welsh (cy): 0%
- ⏳ German (de): 0%
- ⏳ Spanish (es): 0%
- ⏳ Hindi (hi): 0%
- ⏳ Italian (it): 0%
- ⏳ Polish (pl): 0%
- ⏳ Portuguese (pt): 0%
- ⏳ Urdu (ur): 0%
- ⏳ Simplified Chinese (zh-hans): 0%

---

## Related Documentation

- [i18n Implementation Guide](docs/i18n.md) - Complete internationalization documentation
- [French Translation Summary](FRENCH_TRANSLATION_SUMMARY.md) - Detailed French translation guide
- [Contributing Guide](CONTRIBUTING.md) - General contribution guidelines

---

## Getting Help

If you need clarification on any string's context or usage:

1. Check the template file location listed with each string
2. Search the codebase for the English text to see how it's used
3. Review the French translations (45% complete) for consistency
4. Refer to the [Django i18n documentation](https://docs.djangoproject.com/en/stable/topics/i18n/)

---

**Last Updated:** October 13, 2025
**Document Version:** 1.0
**Total Strings:** 259 unique
**Languages:** 11 target languages
**Estimated Total Work:** 2,849 translations
