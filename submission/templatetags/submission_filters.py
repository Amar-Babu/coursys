from django import template
from django.utils.safestring import mark_safe

register = template.Library()


"A filter to get component type"
@register.filter()
def get_component_type(component):
    str = component.get_type()
    return mark_safe(str)