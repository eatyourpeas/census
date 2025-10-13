# Translation Files

This directory contains translation files for the Census application.

## Supported Languages

The application currently supports the following languages:

- **English** (`en`) - Default English
- **English (UK)** (`en_GB`) - British English
- **Welsh** (`cy`) - Cymraeg
- **French** (`fr`) - Français
- **Spanish** (`es`) - Español
- **German** (`de`) - Deutsch
- **Italian** (`it`) - Italiano
- **Portuguese** (`pt`) - Português
- **Polish** (`pl`) - Polski
- **Arabic** (`ar`) - العربية
- **Simplified Chinese** (`zh_Hans`) - 简体中文
- **Hindi** (`hi`) - हिन्दी
- **Urdu** (`ur`) - اردو

## Working with Translations

### Generate translation files for all languages

```bash
python manage.py makemessages -l en -l en_GB -l cy -l fr -l es -l de -l it -l pt -l pl -l ar -l zh_Hans -l hi -l ur
```

### Compile translation files

```bash
python manage.py compilemessages
```

### Add a new language

1. Add the language code to `LANGUAGES` in `settings.py`
2. Run `makemessages -l <language_code>`
3. Translate the strings in `locale/<language_code>/LC_MESSAGES/django.po`
4. Run `compilemessages`

## Translation Status

Currently, 222 strings are marked for translation across the application. English source strings are complete. Other language translations need to be provided by translators.

See `docs/i18n.md` for detailed internationalization documentation.
