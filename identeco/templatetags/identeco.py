from django import template
from django.core.urlresolvers import reverse

register = template.Library()


@register.inclusion_tag("identeco/discovery.html", takes_context=True)
def discovery_meta(context, username=None):
    if username is not None:
        _xrds_url = reverse("identeco_identity_xrds", kwargs={"username": username})
    else:
        _xrds_url = reverse("identeco_xrds")
    return {
        "xrds_url": context["request"].build_absolute_uri(_xrds_url),
    }
