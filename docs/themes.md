# Theming and UI Components

This project uses Tailwind CSS with DaisyUI for components and `@tailwindcss/typography` for rich text. This guide covers theming and the shared form rendering helpers.

## DaisyUI themes

- Themes are defined in `tailwind.config.js` under `daisyui.themes`.
- The default theme is `census`.
- Set a theme by adding `data-theme` to `<html>` or `<body>`. The base layout applies the active theme from server settings.

Example forcing the `light` theme on a page:

```html
<html data-theme="light">
```

After changing themes in `tailwind.config.js`, rebuild CSS.

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

