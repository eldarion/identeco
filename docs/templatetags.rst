.. _templatetags:

Template Tags
=============

discovery_meta
--------------

This tag takes an option username, and it will render either the IDP's XRDS metatag
or the users XRDS metatag.::

    {% discovery_meta %}

    {% discover_meta request.user.username %}
