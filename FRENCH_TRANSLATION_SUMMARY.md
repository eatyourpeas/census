# French Translation - Summary for Future Work

## Current Status

**Progress:** 45% complete (149/330 strings translated)
**Commit:** d896989 - "feat(i18n): French translation progress - 45% complete"
**Date:** October 13, 2025

## Completed Sections ✅

The following areas have been fully translated into French:

### User Interface

- **Home page** - All promotional content, CTAs, and feature descriptions
- **Navigation** - Main menu items, breadcrumbs
- **Profile page** - User badges, organization statistics with plural forms
- **Language switcher** - UI for changing language preferences
- **Theme settings** - System/Light/Dark theme options

### Survey Management

- **Survey builder** - Main builder interface, question groups
- **Bulk import** - Complete markdown import documentation including:
  - Format reference and syntax
  - Question types (text, numeric, multiple choice, etc.)
  - Follow-up inputs configuration
  - Required questions marking
  - Collections with REPEAT
  - Conditional branching
- **Survey creation** - Form fields and labels
- **Dashboard** - Partial completion:
  - Status tracking
  - Response statistics (Today, Last 7/14 days)
  - Groups explanation
  - Survey style settings
- **Publish settings** - Partial completion:
  - Status options (Draft, Published, Closed)
  - Visibility modes (Authenticated, Public, Unlisted, Token)
  - Settings form fields

### Messages & Notifications

- Success/error messages for preferences
- Organization creation notifications
- Survey deletion warnings (partial)

## Remaining Work ⏳ (181 strings)

### High Priority - User-Facing (85 strings)

#### Authentication & Account (28 strings)

- Login form (`Log in`, `Email address`, `Password`)
- Signup form (`Sign up`, `Create account`, `Create your account`)
- Password management (`Forgot your password?`, `Reset password`, `Change password`)
- Account types (`Individual`, `Organisation`, `Account Type`)
- Confirmation messages (`Password reset complete`, `Password changed successfully`)

#### Survey Management UI (35 strings)

- Question groups (`Manage Questions`, `Question Groups`, `Questions in this group`)
- Group operations (`Create new question group`, `Delete this group?`, `Remove repeat`)
- Collections (`Create repeat`, `Repeat name`, `Minimum items`, `Maximum items`, `Unlimited`)
- Survey list (`Your Surveys`, `Preview`, `Import`, `No surveys yet.`)
- Response management (`Thank you`, `Your response has been recorded.`, `Submit`)
- Tokens (`Invite Tokens`, `Token Status`, `Redeem code`, `Type code here`)

#### User Management (12 strings)

- User lists (`Survey users`, `Organisation users`, `User`, `Role`, `Actions`)
- User operations (`Add or update user`, `Add user to org`, `Add user to survey`)
- Roles (`Admin`, `Creator`, `Viewer`)
- Form fields (`Email (preferred)`, `User ID`, `Remove`)

#### Form Elements (10 strings)

- Basic controls (`Yes`, `No`, `-- Select --`, `Save`, `Delete`, `Cancel`)
- Optional labels (`(optional)`, `Help`, `Clear`, `Back to dashboard`)

### Medium Priority - Informational (52 strings)

#### Long-form Messages

- Account creation guidance
- Password reset instructions
- Token redemption messages
- Deletion confirmations with detailed warnings
- Form validation messages

#### Survey Management Details

- Group and question instructions
- Collection nesting limitations
- Token usage explanations
- Privacy confirmations

### Low Priority - Footer/Metadata (44 strings)

#### Footer Elements

- Repository information (`Branch`, `Commit`, `Version`)
- Links (`Built by`, `Contributing`, `License`, `Repository`)

#### Metadata

- Status indicators (`Created`, `Issued`, `Redeemed`, `Revoked`, `Used`, `Uses`)
- General labels (`New`, `Add`, `Status`, `Token`, `Tokens`)

## Translation Guidelines

### Style & Tone

- **Formality:** Use "vous" form (formal) consistently
- **Technical terms:** Keep technical terms like "Census", "slug", "CAPTCHA" in English where appropriate
- **Healthcare context:** This is a medical data collection tool, use appropriate terminology

### Quality Standards

- **Pluralization:** Properly handle `msgstr[0]` (singular) and `msgstr[1]` (plural)
- **Variables:** Preserve all `%(variable)s` placeholders exactly
- **HTML:** Keep all HTML tags `<strong>`, `<em>`, `<code>` intact
- **Punctuation:** Follow French rules (space before colons, proper quotation marks)
- **Consistency:** Maintain consistency with already-translated terms

### Common Translations Established

- Survey = Enquête
- Organization = Organisation
- Group = Groupe
- Question = Question
- Dashboard = Tableau de bord
- Builder = Constructeur
- Status = Statut
- Settings = Paramètres
- Theme = Thème
- Language = Langue

## Files Modified

1. **locale/fr/LC_MESSAGES/django.po** - Main translation file (1544 lines)
2. **docs/i18n.md** - Updated with progress and remaining strings
3. **untranslated_french_strings.txt** - Complete list of remaining strings with locations

## Next Steps

1. **Continue French translation** - Focus on high-priority user-facing strings first
2. **Compile and test** - Run `docker compose exec web python manage.py compilemessages -l fr`
3. **UI Review** - Test the application in French mode to catch any missed labels
4. **Commit** - Commit French completion separately before starting other languages
5. **Other languages** - After French is 100%, repeat for Welsh, Spanish, German, etc.

## Quick Start for Resuming

```bash
# Navigate to project
cd "/Users/eatyourpeas/Development/eatyourpeas repositories/census"

# Check out i18n branch
git checkout i18n

# Edit French translation file
# Translate empty msgstr fields in:
vim locale/fr/LC_MESSAGES/django.po

# Compile to test
docker compose exec web python manage.py compilemessages -l fr

# Commit progress
git add locale/fr/LC_MESSAGES/django.po
git commit -m "feat(i18n): Continue French translations - [section completed]"
```

## Useful Commands

```bash
# Count remaining empty translations
grep -c 'msgstr ""' locale/fr/LC_MESSAGES/django.po

# Find specific untranslated string
grep -B 2 'msgid "Login"' locale/fr/LC_MESSAGES/django.po

# Test in French
# Visit http://localhost:8000/core/profile/ and select French

# Recompile after changes
docker compose exec web python manage.py compilemessages

# Generate updated POT if new strings added
docker compose exec web python manage.py makemessages -a
```

## Reference Files

- **Full untranslated list:** `untranslated_french_strings.txt` (147 strings with locations)
- **Documentation:** `docs/i18n.md` (complete i18n implementation guide)
- **Workflow:** `locale/README.md` (translation workflow and commands)

---

**Note:** This document reflects the state as of commit d896989. Update this summary after completing additional translation work.
