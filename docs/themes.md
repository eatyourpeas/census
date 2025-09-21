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

1) Numbered crumb parameters (template-friendly)

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

2) Items iterable (tuple list)

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

