from django import template
from django.http import QueryDict

register = template.Library()

@register.simple_tag
def url_replace(request, field, value):
    """
    Replace or add a query parameter while preserving others
    """
    dict_ = request.GET.copy()
    dict_[field] = value
    return dict_.urlencode() 