"""
Custom manager for Attribute objects.
"""
from django.db import models

import defines_global

class AttributeManager(models.Manager):
    def is_modifiable_attrib(self, attribname):
        """
        Check to see if a particular attribute is modifiable.

        attribname: (string) An attribute name to check.
        """
        if attribname.upper() not in defines_global.NOSET_ATTRIBS:
            return True
        else:
            return False
