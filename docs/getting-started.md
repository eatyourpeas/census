# Getting started

This guide lists configuration variables you can set to customize branding, themes, and behavior. Values are read from Django settings and the SiteBranding record (set via the Profile page).

## Branding and theme settings


- BRAND_TITLE (str) — Default site title. Example: "Census"
- BRAND_ICON_URL (str) — URL or static path to the site icon shown in the navbar and as favicon if no uploaded icon. Example: "/static/favicon.ico" or <https://example.com/icon.svg>
- BRAND_ICON_URL_DARK (str) — Optional dark-mode icon URL. Shown when the active theme contains `census-dark`.
- BRAND_ICON_ALT (str) — Alt text for the brand icon. Defaults to BRAND_TITLE.
- BRAND_ICON_TITLE (str) — Title/tooltip for the brand icon. Defaults to BRAND_TITLE.
- BRAND_ICON_SIZE_CLASS (str) — Tailwind size classes for the icon. Example: "w-8 h-8". If omitted, BRAND_ICON_SIZE is used.
- BRAND_ICON_SIZE (int or str) — Numeric size that maps to `w-{n} h-{n}`. Example: 6, 8. Ignored if BRAND_ICON_SIZE_CLASS is set.
- BRAND_THEME (str) — Default theme name. Example: "census-light".
- BRAND_FONT_HEADING (str) — CSS font stack for headings.
- BRAND_FONT_BODY (str) — CSS font stack for body.
- BRAND_FONT_CSS_URL (str) — Optional font CSS href (e.g., Google Fonts).
- BRAND_THEME_CSS_LIGHT (str) — DaisyUI variable overrides for light theme.
- BRAND_THEME_CSS_DARK (str) — DaisyUI variable overrides for dark theme.

Notes:

- The Profile page (admin) writes values into the `SiteBranding` model. For icons, precedence is:
  1) Uploaded file (`icon_file` for light/default, `icon_file_dark` for dark)
  2) URL in the DB (`icon_url`, `icon_url_dark`)
  3) Django settings (`BRAND_ICON_URL`, `BRAND_ICON_URL_DARK`)
  4) Built-in fallback SVG
- Per-survey overrides can set icon URL, fonts, and per-page DaisyUI variable overrides.

## Survey style fields (per-survey)

- title — Optional page title override
- icon_url — Optional per-survey favicon/icon
- theme_name — DaisyUI theme name for the survey pages
- primary_color — Hex color (e.g., #ff3366); normalized to the correct color variables
- font_heading — CSS font stack
- font_body — CSS font stack
- font_css_url — Optional font CSS href
- theme_css_light — Light theme DaisyUI variable overrides (from builder)
- theme_css_dark — Dark theme DaisyUI variable overrides (from builder)

## Where to look in the code

- Base template: `census_app/templates/base.html`
- Branding context: `census_app/context_processors.py` (builds the `brand` object)
- Profile UI: `census_app/core/templates/core/profile.html`
- Survey dashboard style form: `census_app/surveys/templates/surveys/dashboard.html`
- Tailwind entry: `census_app/static/src/tailwind.css`

## Rebuilding the CSS

- After changing Tailwind/DaisyUI config or adding templates, rebuild CSS.

```bash
npm run build:css
```

If running in Docker, ensure the image build step or a volume-mounted build runs the same.
