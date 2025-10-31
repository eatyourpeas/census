# Documentation System

The CheckTick documentation system automatically discovers and organizes all markdown files in the `docs/` folder.

## How It Works

### Auto-Discovery

Simply add a new `.md` file to the `docs/` folder and it will automatically appear in the documentation navigation. No code changes needed!

**Example:**
```bash
# Add a new guide
touch docs/my-new-feature.md

# Edit the file with your content
echo "# My New Feature\n\nThis is a guide..." > docs/my-new-feature.md

# Restart the web container
docker compose restart web

# The page will now appear in the docs!
```

### Automatic Categorization

The system automatically categorizes documentation based on filename patterns:

| Category | Pattern Keywords | Examples |
|----------|-----------------|----------|
| **Getting Started** 📚 | `getting-started`, `quickstart`, `setup` | `getting-started.md`, `quickstart-guide.md` |
| **Features** ✨ | `surveys`, `collections`, `groups`, `import`, `publish` | `surveys.md`, `collections.md` |
| **Configuration** ⚙️ | `branding`, `theme`, `user-management`, `setup` | `branding-and-theme-settings.md` |
| **Security** 🔒 | `security`, `encryption`, `patient-data`, `authentication`, `permissions` | `patient-data-encryption.md`, `authentication-and-permissions.md` |
| **API & Development** 🔧 | `api`, `adding-`, `development` | `api.md`, `adding-external-datasets.md` |
| **Testing** 🧪 | `testing`, `test-` | `testing-api.md`, `testing-webapp.md` |
| **Internationalization** 🌍 | `i18n`, `internationalization`, `translation`, `locale` | `i18n.md` |
| **Advanced Topics** 🚀 | `advanced`, `custom`, `extend` | `advanced-config.md` |
| **Other** 📄 | Everything else | `releases.md` |

### Title Extraction

The system extracts the page title from the first `# Heading` in your markdown file. For example:

```markdown
# My Awesome Feature Guide

This guide shows you how to...
```

Will display as **"My Awesome Feature Guide"** in the navigation.

If no heading is found, the filename is converted to title case (e.g., `my-feature.md` → "My Feature").

## Manual Overrides

If you need more control, you can override settings in `census_app/core/views.py`:

### Custom Category Assignment

Edit the `DOC_PAGE_OVERRIDES` dictionary:

```python
DOC_PAGE_OVERRIDES = {
    "my-special-doc": {
        "file": "my-special-doc.md",
        "category": "api",  # Force into API category
        "title": "Custom Display Title",  # Optional custom title
    },
}
```

### External Files

You can include files from outside the `docs/` folder:

```python
DOC_PAGE_OVERRIDES = {
    "changelog": {
        "file": REPO_ROOT / "CHANGELOG.md",
        "category": "other",
    },
}
```

### New Categories

Add new categories in the `DOC_CATEGORIES` dictionary:

```python
DOC_CATEGORIES = {
    "my-category": {
        "title": "My Custom Category",
        "order": 10,  # Controls display order
        "icon": "🎯",  # Optional emoji icon
    },
}
```

## Best Practices

### 1. Descriptive Filenames

Use descriptive, kebab-case filenames:
- ✅ `prefilled-datasets-quickstart.md`
- ✅ `authentication-and-permissions.md`
- ❌ `doc1.md`
- ❌ `README.md` (reserved for index)

### 2. Clear First Heading

Always start your document with a clear `# Heading`:

```markdown
# Prefilled Datasets Quick Start

A quick guide to using prefilled dropdown options...
```

### 3. Consistent Naming Patterns

Use consistent prefixes for related docs:
- `prefilled-datasets-quickstart.md`
- `prefilled-datasets-setup.md`
- `adding-external-datasets.md`

This helps with auto-categorization and keeps related docs together.

### 4. Category Hints in Filenames

Include category keywords in filenames to ensure correct categorization:
- API guides: `api-reference.md`, `authentication-guide.md`
- Setup guides: `getting-started-api.md`, `quickstart-deploy.md`
- Configuration: `theme-settings.md`, `branding-guide.md`

## Navigation Structure

The documentation sidebar is organized hierarchically:

```
Documentation
├── 📚 Getting Started
│   ├── Getting Started
│   └── Getting Started Api
├── ✨ Features
│   ├── Collections
│   ├── Groups View
│   └── Surveys
├── ⚙️ Configuration
│   ├── Branding And Theme Settings
│   └── User Management
├── 🔒 Security
│   ├── Authentication And Permissions
│   └── Patient Data Encryption
├── 🔧 API & Development
│   ├── Adding External Datasets
│   └── Api
├── 🧪 Testing
│   ├── Testing Api
│   └── Testing Webapp
├── 🌍 Internationalization
│   ├── I18n
│   └── I18n Progress
└── 📄 Other
    └── Releases
```

Categories are sorted by their `order` value (lower numbers appear first).

## Troubleshooting

### Page Not Appearing

1. **Check the filename**: Must be `.md` extension
2. **Restart the container**: `docker compose restart web`
3. **Check for errors**: `docker compose logs web | grep -i error`

### Wrong Category

1. Check filename patterns in `_infer_category()` function
2. Add manual override in `DOC_PAGE_OVERRIDES`
3. Update filename to include category keywords

### Custom Title Not Showing

1. Check the first line starts with `# ` (must have space after #)
2. Verify markdown syntax is correct
3. Add manual title override in `DOC_PAGE_OVERRIDES`

## Implementation Details

The system consists of three main components:

1. **`_discover_doc_pages()`**: Scans `docs/` folder and builds page registry
2. **`_infer_category()`**: Categorizes pages based on filename patterns
3. **`_nav_pages()`**: Builds categorized navigation structure for templates

This runs once at Django startup, so changes require a container restart.

## Migration from Old System

The old system required manually updating the `DOC_PAGES` dictionary. The new system is backward compatible:

- Old manual entries moved to `DOC_PAGE_OVERRIDES`
- All existing docs auto-discovered
- No changes needed to existing markdown files

## Future Enhancements

Potential improvements:

- **Frontmatter support**: Add YAML metadata to markdown files for explicit categorization
- **Hot reload**: Auto-discover without container restart (development mode)
- **Search**: Full-text search across all documentation
- **Related pages**: Suggest related documentation based on content
- **Breadcrumbs**: Show navigation path for nested topics

## Related Files

- `census_app/core/views.py` - Documentation discovery logic
- `census_app/core/templates/core/docs.html` - Navigation template
- `census_app/core/urls.py` - URL routing for docs
- `docs/README.md` - Documentation index page
