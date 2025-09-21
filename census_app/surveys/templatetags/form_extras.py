from django import template

register = template.Library()


@register.filter(name="add_classes")
def add_classes(field, css):
    """Return a field rendered with extra CSS classes appended to the widget.

    Usage: {{ form.field|add_classes:"input input-bordered w-full" }}
    """
    widget = field.field.widget
    classes = widget.attrs.get("class", "")
    merged = (classes + " " + css).strip()
    return field.as_widget(attrs={**widget.attrs, "class": merged})


@register.filter(name="field_type")
def field_type(field):
    """Return a simple type string for deciding default classes in templates.

    Avoids accessing private attributes like __class__ in templates.
    """
    widget = getattr(field, "field", None)
    if not widget:
        return "text"
    w = field.field.widget
    # Prefer explicit input_type when present
    itype = getattr(w, "input_type", None)
    if itype:
        return itype
    name = w.__class__.__name__
    if name in ("Textarea",):
        return "textarea"
    if name in ("Select", "SelectMultiple"): 
        return "select"
    return "text"
