from django.db import models
from django.conf import settings

class GenericPerm(models.Model):
    """
    This is merely a container class for some generic permissions that don't
    fit under a particular module.
    """
    class Meta:
        permissions = settings.PERM_GENPERMS
