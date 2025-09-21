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
