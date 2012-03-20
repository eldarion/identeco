import datetime

try:
    from django.utils.timezone import now as nowfn
except ImportError:
    nowfn = datetime.datetime.now
