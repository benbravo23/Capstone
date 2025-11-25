from django import template

register = template.Library()

@register.filter
def upper(value):
    """Convierte un valor a mayúsculas."""
    try:
        return str(value).upper()
    except:
        return value
