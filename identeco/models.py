from django.db import models


class Nonce(models.Model):

    server_url = models.CharField(max_length=2047)
    salt = models.CharField(max_length=40)
    issued = models.DateTimeField()
    expires = models.DateTimeField()

    class Meta:
        unique_together = ("server_url", "issued", "salt")


class Association(models.Model):

    type = models.CharField(max_length=64)

    server_url = models.CharField(max_length=2047)
    handle = models.CharField(max_length=255)
    secret = models.TextField()
    lifetime = models.PositiveIntegerField()
    issued = models.DateTimeField()
    expires = models.DateTimeField()

    class Meta:
        unique_together = ("server_url", "handle")


class Trust(models.Model):

    user = models.ForeignKey("auth.User")
    trust_root = models.CharField(max_length=2047)
    always_trust = models.BooleanField()

    class Meta:
        unique_together = ("user", "trust_root")
