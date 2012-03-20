from django.conf.urls import patterns, url

from identeco import views

urlpatterns = patterns("",
    url(r"^xrds\.xml$", views.XRDS.as_view(), name="identeco_xrds"),
    url(r"^endpoint/$", views.Endpoint.as_view(), name="identeco_endpoint"),
    url(r"^decide/$", views.DecideTrust.as_view(), name="identeco_decide_trust"),
    url(r"^(?P<username>[^/]+)/$", views.Identity.as_view(), name="identeco_identity"),
    url(r"^(?P<username>[^/]+)/xrds\.xml$", views.XRDS.as_view(identity=True), name="identeco_identity_xrds"),
)
