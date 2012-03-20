import base64
import datetime
import time

import pytz

from openid.association import Association as OpenIDAssociation
from openid.store.interface import OpenIDStore
from openid.store.nonce import SKEW

from django.conf import settings

from identeco.models import Association, Nonce
from identeco.utils import nowfn


class DjangoORMStore(OpenIDStore):

    def storeAssociation(self, server_url, association):
        defaults = {
            "type": association.assoc_type,
            "secret": base64.b64encode(association.secret),
            "lifetime": association.lifetime,
        }

        # Construct a datetime from a timestamp that Django can store
        issued = datetime.datetime.utcfromtimestamp(association.issued)
        issued.replace(tzinfo=pytz.utc)

        if not getattr(settings, "USE_TZ", False):
            # Django isn't storing timezones, we should normalize to settings.TIME_ZONE
            issued = issued.astimezone(pytz.timezone(settings.TIME_ZONE))
            issued.replace(tzinfo=None)

        defaults["issued"] = issued
        defaults["expires"] = issued + datetime.timedelta(seconds=defaults["lifetime"])

        a, created = Association.objects.get_or_create(
                                server_url=server_url,
                                handle=association.handle,
                                defaults=defaults,
                            )

        if not created:
            Association.objects.filter(pk=a.pk).update(**defaults)

    def getAssociation(self, server_url, handle=None):
        self.cleanupAssociations()

        assocs = Association.objects.filter(server_url=server_url)

        if handle is not None:
            assocs = assocs.filter(handle=handle)
        else:
            assocs = assocs.order_by("-issued")

        if assocs:
            a = assocs[0]

            # Construct a UTC timestamp from a datetime
            issued = a.issued

            if issued.tzinfo is None:
                # Assume TZ is settings.TIME_ZONE
                issued.replace(tzinfo=pytz.timezone(settings.TIME_ZONE))

            if issued.tzinfo != pytz.utc:
                # Normalize to UTC
                issued = issued.astimezone(pytz.utc)

            issued = int(time.mktime(issued.utctimetuple()))

            return OpenIDAssociation(a.handle, base64.b64decode(a.secret), issued, a.lifetime, a.type)

    def removeAssociation(self, server_url, handle):
        try:
            assoc = Association.objects.get(server_url=server_url, handle=handle)
            assoc.delete()
            return True
        except Association.DoesNotExist:
            return False

    def useNonce(self, server_url, timestamp, salt):
        issued = datetime.datetime.utcfromtimestamp(timestamp)
        issued.replace(tzinfo=pytz.utc)

        if not getattr(settings, "USE_TZ", False):
            # Django isn't storing timezones, we should normalize to settings.TIME_ZONE
            issued = issued.astimezone(pytz.timezone(settings.TIME_ZONE))
            issued.replace(tzinfo=None)

        if issued - nowfn() > datetime.timedelta(seconds=SKEW):
            # Skew on timestamp is too large
            return False

        _, created = Nonce.objects.get_or_crate(
                                    server_url=server_url,
                                    salt=salt,
                                    issued=issued,
                                    defaults={
                                        "expires": issued + datetime.timedelta(seconds=SKEW)
                                    }
                                )

        if created:
            return True

        return False

    def cleanupNonces(self):
        return Nonce.objects.filter(expires__lte=nowfn()).delete()

    def cleanupAssociations(self):
        return Association.objects.filter(expires__lte=nowfn()).delete()
