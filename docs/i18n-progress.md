# i18n Implementation Progress

**Date:** 13 October 2025
**Branch:** i18n
**Status:** Infrastructure complete, translation markup in progress

## Completed ✅

### 1. Settings Configuration
- ✅ Added `LocaleMiddleware` to middleware stack
- ✅ Added `LANGUAGES` list with English and English (UK)
- ✅ Added `LOCALE_PATHS` configuration
- ✅ Created custom `UserLanguageMiddleware` for user preferences

### 2. Models
- ✅ Created `UserLanguagePreference` model
- ✅ Created migration file `0004_userlanguagepreference.py`
- ✅ Added `get_or_create_for_user()` helper method

### 3. Middleware
- ✅ Created `census_app/core/middleware.py` with `UserLanguageMiddleware`
- ✅ Integrated into middleware stack after `AuthenticationMiddleware`

### 4. Directory Structure
- ✅ Created `locale/en/LC_MESSAGES/` directory
- ✅ Created `locale/en_GB/LC_MESSAGES/` directory
- ✅ Added locale README

### 5. Translation Markup - Started

#### Python Code
- ✅ **core/views.py** - All messages.success/error calls marked with `_()`
  - Email preferences updated
  - Organisation created
  - Project theme saved

#### Templates
- ✅ **core/templates/core/profile.html** - Partially complete
  - Page title translated
  - Main headings translated
  - Badge tooltips with proper pluralization using `{% blocktrans count %}`
  - All 11 tooltip messages properly internationalized

## Next Steps 🚀

### Immediate (Before Docker Start)
1. ⏳ Verify migration dependency in `0004_userlanguagepreference.py`
2. ⏳ Complete profile.html translation markup (remaining sections)

### After Docker Starts
3. ⏳ Run migration: `python manage.py migrate`
4. ⏳ Generate translation files: `python manage.py makemessages -l en`
5. ⏳ Test language detection is working

### High Priority Translation Markup
6. ⏳ Remaining profile.html sections:
   - Appearance card
   - Email preferences form
   - Branding form (superuser)
   - Upgrade to organisation card

7. ⏳ Core templates:
   - `core/home.html`
   - `registration/login.html`
   - `registration/signup.html`

8. ⏳ Survey views (surveys/views.py):
   - ~50+ messages.success/error/warning calls
   - Survey created, deleted, published messages
   - User management messages
   - Token creation messages

9. ⏳ Survey templates:
   - `surveys/detail.html`
   - `surveys/bulk_upload.html`
   - `surveys/group_builder.html`
   - All other survey templates

### Medium Priority
10. ⏳ Forms (census_app/core/forms.py):
    - Field labels
    - Help text
    - Error messages

11. ⏳ API views (census_app/api/views.py):
    - Error messages
    - Response messages

12. ⏳ Models (census_app/surveys/models.py):
    - verbose_name fields
    - help_text fields
    - Choice labels

### Low Priority
13. ⏳ JavaScript (census_app/static/js/builder.js):
    - Alert messages
    - Confirmation dialogs

14. ⏳ Email templates:
    - Subject lines
    - Email body content

### UI Features to Add
15. ⏳ Language switcher component (navbar or profile)
16. ⏳ Form to update user language preference
17. ⏳ Admin interface for UserLanguagePreference model

## Translation Statistics

### Current Coverage
- **Settings:** 100% ✅
- **Models:** 10% (1/10 models) ⏳
- **Views:** 5% (core.views partial) ⏳
- **Templates:** 5% (2/40+ templates) ⏳
- **Forms:** 0% ❌
- **API:** 0% ❌
- **JavaScript:** 0% ❌

### Estimated Remaining Work
- **Python strings:** ~200+ strings
- **Template strings:** ~500+ strings
- **JavaScript strings:** ~50+ strings
- **Total:** ~750+ strings

## How Language Detection Works

1. **User is authenticated with language preference:**
   - UserLanguageMiddleware checks database
   - Activates user's preferred language

2. **User is authenticated without preference:**
   - Falls back to LocaleMiddleware behavior

3. **Anonymous user:**
   - LocaleMiddleware checks:
     a. Session language (if set via language switcher)
     b. Cookie `django_language`
     c. HTTP Accept-Language header (browser)
     d. LANGUAGE_CODE setting (default: "en-gb")

## Testing Checklist

Once Docker is running:

```bash
# 1. Run migration
docker compose exec web python manage.py migrate

# 2. Generate message files
docker compose exec web python manage.py makemessages -l en
docker compose exec web python manage.py makemessages -l en_GB

# 3. Check .po files were created
ls -la locale/en/LC_MESSAGES/
ls -la locale/en_GB/LC_MESSAGES/

# 4. Compile messages
docker compose exec web python manage.py compilemessages

# 5. Test language detection
# - Check browser language is detected
# - Check user preference overrides browser
# - Check session language works
```

## Known Issues

1. **Icon in badges:** Using clipboard icon for surveys, but should use document icon
   - Needs update in profile.html lines ~95, ~103, ~111

2. **Migration dependency:** Need to verify the dependency chain in migration file

3. **Docker not running:** Need to start Docker to test changes

## References

- [Django i18n documentation](https://docs.djangoproject.com/en/5.2/topics/i18n/)
- [Translation in templates](https://docs.djangoproject.com/en/5.2/topics/i18n/translation/#internationalization-in-template-code)
- Project docs: `docs/themes.md` (lines 320-432)
- Analysis doc: `docs/i18n-implementation-analysis.md`
