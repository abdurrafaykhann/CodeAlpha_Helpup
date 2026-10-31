from django import template

register = template.Library()


@register.inclusion_tag('partials/avatar.html')
def avatar(user, size='md'):
    """Profile picture, or a coloured initial when the user has none. size: xs, sm, md, lg, xl."""
    return {'u': user, 'size': size}


@register.simple_tag(takes_context=True)
def qs_with(context, **kwargs):
    """Current query string with some parameters replaced - used by pagination links."""
    query = context['request'].GET.copy()
    for key, value in kwargs.items():
        query[key] = value
    return query.urlencode()
