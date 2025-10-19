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

### Import Translations from Markdown Files

Census provides a convenient management command to import translations from structured markdown files:

```bash
# Preview changes (dry run)
docker compose exec web python manage.py import_translations --dry-run

# Import translations
docker compose exec web python manage.py import_translations

# Compile the updated translations
docker compose exec web python manage.py compilemessages
docker compose restart web
```

The markdown translation files are located in `docs/languages/`:
- `COMPLETE_STRINGS_LIST.md` - Master English string list (numbered 1-101)
- `arabic.md`, `chinese.md`, `french.md`, etc. - Translation files for each language

The import command:
- Matches translations by number (1-101)
- Restores HTML tags and `\n` formatting from English template
- Preserves `.po` file headers and metadata
- Updates only the `msgstr` values, leaving `msgid` and comments intact

See the "Importing Translations from Markdown Files" section in `docs/i18n.md` for detailed usage.

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
3. Create a markdown file in `docs/languages/<language>.md` with translations
4. Run `import_translations` to import from markdown
5. Run `compilemessages`

## Translation Status

Currently, 222 strings are marked for translation across the application. English source strings are complete. Other language translations need to be provided by translators.

See `docs/i18n.md` for detailed internationalization documentation.
