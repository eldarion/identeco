.. _installation:

Installation
============

* To install ::

    pip install identeco

* Add ``"identeco"`` to your ``INSTALLED_APPS`` setting::

    INSTALLED_APPS = (
        # other apps
        "identeco",
    )

* Include Identeco in your ``urls.py``::

    urlpatterns = patterns('',
        url(r'^identeco/', include('identeco.urls')),
    )

* Add the Template Tags to your desired IDP page
