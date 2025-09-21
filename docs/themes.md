# Theming and UI Components

This project uses Tailwind CSS with DaisyUI for components and `@tailwindcss/typography` for rich text. This guide covers theming and the shared form rendering helpers.

## DaisyUI themes

- Themes are defined in `tailwind.config.js` under `daisyui.themes`.
- The default theme is `census-light` (an alias of `census`).
- Set a theme by adding `data-theme` to `<html>` or `<body>`. The base layout applies the active theme from server settings.

Example forcing the `light` theme on a page:

```html
<html data-theme="light">
```

After changing themes in `tailwind.config.js`, rebuild CSS.

## Project-level vs Survey-level theming

There are two layers of theming you can use together:

1. Project-level (global) theming — organization branding

- Who: Organization admin (superuser) in the Profile page
- Applies to: Entire site by default
- What you can configure:
  - Default theme (System/Light/Dark default and DaisyUI theme name)
  - Site icon (favicon): upload SVG/PNG or provide a URL
  - Dark-mode icon: upload a separate SVG/PNG or provide a URL (used when the dark theme is active)
  - Fonts: heading/body stacks and an optional external Font CSS URL (e.g. Google Fonts)
  - Theme CSS overrides for light/dark produced by the DaisyUI theme builder (variables only)
- Where it’s stored: `SiteBranding` model in the database
- How it’s applied:
  - The base template (`base.html`) injects the configured icons (light and optional dark), fonts, and the normalized DaisyUI variable overrides at runtime under the correct selectors:
    - `[data-theme="census-light"] { … }`
    - `[data-theme="census-dark"] { … }`
  - These overrides affect the whole site unless a page provides a more specific override.

1. Survey-level theming — per-survey customization

- Who: Survey owners/managers
- Applies to: Specific survey views (dashboard, detail, groups, and builder)
- What you can configure:
  - Optional title/icon override
  - Fonts (heading/body stacks and font CSS URL)
  - Theme CSS overrides for light/dark from the DaisyUI builder (variables only)
- How it’s applied:
  - Survey templates include a `head_theme_overrides` block to inject per-survey font CSS and DaisyUI variable overrides, and an `icon_link` block to set a per-survey favicon.
  - Per-survey overrides take precedence on those pages because they’re injected in-page.

### Precedence and merge behavior

- Base DaisyUI theme (census-light/dark) is the foundation.
- Project-level overrides refine the base across the entire site.
- Survey-level overrides win on survey pages where they’re included.
- Avoid mixing heavy global CSS with inline colors; prefer DaisyUI variables so all layers compose cleanly.

## How to configure project-level theming

1) Go to Profile → Project theme and brand (admin-only)
1) Set defaults:
  - Default theme: System, Light, or Dark (and the theme name to apply)
  - Icon: either upload an SVG/PNG or paste an absolute URL
  - Fonts: set heading/body stacks; optionally paste a Font CSS URL (e.g. Google Fonts)
1) DaisyUI Builder CSS (optional):
  - Copy variables from the DaisyUI builder for both light and dark if you have them
  - Paste into “Light theme CSS” and “Dark theme CSS”
  - We normalize builder variables into DaisyUI runtime variables under the hood and inject them at runtime
1) Save — the base template will now serve your icon, fonts, and theme colors sitewide.

Tip: When using a Font CSS URL, keep your font stacks in sync with the families you request.

## How to configure survey-level theming

1) Open a survey → Dashboard → “Survey style”
2) Optional: set a Title override and Icon URL
3) Fonts: set heading/body stacks and optionally a Font CSS URL
4) Theme name: normally leave as-is unless you’re switching between DaisyUI themes
5) Primary color: provide a hex like `#ff3366`; the server will convert it to the appropriate color space / variables
6) If you have DaisyUI builder variables for this survey’s unique palette:
  - Paste the light/dark sets in their respective fields (where available)
  - The page will inject them under `[data-theme="census-light"]` and `[data-theme="census-dark"]`

These overrides only apply on survey pages and do not affect the rest of the site.

## Acceptable DaisyUI builder CSS

Paste only variable assignments from the builder, for example:

```txt
--color-primary: oklch(65% 0.21 25);
--radius-selector: 1rem;
--depth: 0;
```

We map these to DaisyUI runtime variables (e.g., `--p`, `--b1`, etc.) and inject them under the right data-theme selector. Avoid pasting arbitrary CSS rules; stick to variables for predictable results.

## Troubleshooting

- Colors don’t apply: Check for any hardcoded inline CSS overriding CSS variables. Prefer variables and themes.
- Wrong theme shown after changes: Your previous selection is cached locally. Use System/Light/Dark toggle or clear local storage to reset.
- Icon not showing: If you uploaded an icon, make sure media is configured. If using a URL, verify it’s reachable. The app falls back to a default SVG if none is set.

## Typography and button links

`@tailwindcss/typography` styles content in `.prose`, including links. To avoid underlines and color overrides on DaisyUI button anchors, the build loads Typography first and DaisyUI second, with a small Typography override to skip underlines on `a.btn`.

- To opt a specific element out of Typography effects, add `not-prose`.

## Rendering forms with DaisyUI

We ship a filter and partials to standardize Django form rendering.

### Template filter: `add_classes`

File: `census_app/surveys/templatetags/form_extras.py`

Usage:

```django
{% load form_extras %}
{{ form.field|add_classes:"input input-bordered w-full" }}
```

### Partial: `components/form_field.html`

File: `census_app/templates/components/form_field.html`

Context:

- `field` (required): bound Django form field
- `label` (optional)
- `help` (optional)
- `classes` (optional): override default classes

Defaults when `classes` isn’t provided:


- Text-like inputs: `input input-bordered w-full`
- Textarea: `textarea textarea-bordered w-full`
- Select: `select select-bordered w-full`

Example:

```django
{% include "components/form_field.html" with field=form.name label="Name" %}
{% include "components/form_field.html" with field=form.slug label="URL Name or 'Slug' (optional)" help="If left blank, a slug will be generated from the name." %}
{% include "components/form_field.html" with field=form.description label="Description" %}
```

### Render an entire form

Helper that iterates over visible fields:

```django
{% include "components/render_form_fields.html" with form=form %}
```

This uses `form_field` for each field. For radio/checkbox groups needing custom layout, render bespoke markup with DaisyUI components or pass `classes` explicitly.

### Choice components

For grouped choices, use the specialized components:

- `components/radio_group.html` — radios with DaisyUI
- `components/checkbox_group.html` — checkboxes with DaisyUI

Examples:

```django
{% include "components/radio_group.html" with name="account_type" label="Account type" choices=(("simple","Simple user"),("org","Organisation")) selected='simple' inline=True %}
```

```django
{% include "components/checkbox_group.html" with name="interests" label="Interests" choices=(("a","A"),("b","B")) selected=("a",) %}
```

## Rebuild CSS

Whenever you change `tailwind.config.js` or add new templates:

```bash
npm run build:css
```

If running under Docker, rebuild the image or ensure your build step runs inside the container.

### Single stylesheet entry

- Unified Tailwind/DaisyUI input: `census_app/static/src/tailwind.css`
- Built output: `census_app/static/build/styles.css`
- Loaded globally in `census_app/templates/base.html` via `{% static 'build/styles.css' %}`

Do not add other `<link rel="stylesheet">` tags or separate CSS files; extend styling through Tailwind utilities, DaisyUI components, or minimal additions inside the unified entry file.


## Breadcrumbs component

We ship a reusable DaisyUI-style breadcrumbs component with icons.

- File: `census_app/templates/components/breadcrumbs.html`
- Purpose: Provide consistent navigation crumbs across survey pages
- Icons:
  - Survey: clipboard icon
  - Question group: multiple documents icon
  - Question (current): single document icon

### How to use

There are two ways to render breadcrumbs, depending on what’s most convenient in your template.

1. Numbered crumb parameters (template-friendly)

Pass labeled crumbs in order. For any crumb you pass, you can optionally include an `*_href` to make it a link. The last crumb usually omits `*_href` to indicate the current page.

```django
{% include 'components/breadcrumbs.html' with 
  crumb1_label="Survey Dashboard" 
  crumb1_href="/surveys/"|add:survey.slug|add:"/dashboard/" 
  crumb2_label="Question Group Builder" 
  crumb2_href="/surveys/"|add:survey.slug|add:"/builder/" 
  crumb3_label="Question Builder" 
%}
```

1. Items iterable (tuple list)

If you already have a list, pass `items` as an iterable of `(label, href)` tuples. Use `None` for href on the current page.

```django
{% include 'components/breadcrumbs.html' with 
  items=(("Survey Dashboard", "/surveys/"|add:survey.slug|add:"/dashboard/"),
         ("Question Group Builder", "/surveys/"|add:survey.slug|add:"/builder/"),
         ("Question Builder", None)) 
%}
```

### Styling

Breadcrumbs inherit DaisyUI theme colors and are further tuned globally so that:

- Links are lighter by default and only underline on hover
- The current (non-link) crumb is slightly lighter to indicate context

These tweaks live in the single CSS entry at `census_app/static/src/tailwind.css` in a small component layer block:

```css
@layer components {
  .breadcrumbs a {
    @apply no-underline text-base-content/70 hover:underline hover:text-base-content/90;
  }
  .breadcrumbs li > span {
    @apply text-base-content/60;
  }
  /* Ensure Typography (.prose) doesn’t re-add underlines */
  .prose :where(.breadcrumbs a):not(:where([class~="not-prose"])) {
    @apply no-underline text-base-content/70 hover:underline hover:text-base-content/90;
  }
}
```

Any updates here require a CSS rebuild.

### Page conventions

- Survey dashboard pages begin with a clipboard icon crumb (Survey)
- Survey-level builder links (groups) show multiple documents
- Group-level question builder shows a single document for the active page

Keep breadcrumb labels terse and consistent (e.g., “Survey Dashboard”, “Question Group Builder”, “Question Builder”).

## Theme selection (System/Light/Dark)

End users can choose how the UI looks on the Profile page. The selector supports:

- System — follow the operating system’s preference (auto-switches if the OS changes)
- Light — force the custom light theme (`census-light`)
- Dark — force the custom dark theme (`census-dark`)

How it works:

- The active preference is saved to `localStorage` under the key `census-theme`.
- Accepted values: `system`, `census-light`, `census-dark`.
- On first visit, the server’s default (`data-theme` on `<html>`) is used; if it matches the system preference, the selector shows `System`.
- Changing the selector immediately updates `html[data-theme]` and persists the choice.
- When `System` is selected, the UI updates automatically on OS theme changes via `prefers-color-scheme`.

Relevant files:

- Profile UI: `census_app/core/templates/core/profile.html`
- Runtime logic: `census_app/static/js/theme-toggle.js`
- Script is loaded in: `census_app/templates/base.html`

## Branding and customization

This project supports organization branding at the platform level with sensible accessibility defaults and light/dark variants.

### Navbar brand icon

- The navbar shows the brand icon next to the site title.
- Source priority (first available wins):
  1) Uploaded file on the Profile page (light: `icon_file`, dark: `icon_file_dark`)
  2) URL saved on the Profile page (light: `icon_url`, dark: `icon_url_dark`)
  3) Django settings (`BRAND_ICON_URL`, `BRAND_ICON_URL_DARK`)
  4) Inline SVG fallback (a neutral stroke-based mark)
- Dark mode: if a dark icon is set (uploaded or URL), it is shown automatically when the active theme contains `census-dark`.
- The icon includes `alt` and `title` attributes derived from `BRAND_ICON_ALT` and `BRAND_ICON_TITLE` (defaulting to the site title).
- Size can be customized with `BRAND_ICON_SIZE_CLASS` (Tailwind classes like `w-8 h-8`) or `BRAND_ICON_SIZE` (number -> `w-{n} h-{n}`). Defaults to `w-6 h-6`.

Accessibility:

- Icons are rendered with `alt`/`title` and, for inline SVG, `role="img"` and `aria-label` to ensure assistive technology support.
- Prefer high-contrast icons. If providing separate light/dark assets, test both on your themes.

### Fonts and CSS variables

- Heading/body font stacks are applied via CSS variables (`--font-heading` and `--font-body`).
- Optional `font_css_url` allows fast integration with Google Fonts or similar. Ensure stacks match the families you load.

### Survey-specific overrides

- Surveys can override icon, fonts, and DaisyUI variables on their pages. See “How to configure survey-level theming” above.

### Rebuild reminder

- Changes to Tailwind/DaisyUI configs or new templates require rebuilding the CSS bundle.

