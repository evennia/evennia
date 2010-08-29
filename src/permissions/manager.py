"""
A simple manager for Permission groups
"""

from django.db import models

class PermissionGroupManager(models.Manager):
    "Adds a search method to the default manager"

    def search_permgroup(self, ostring):
        """
        Find a permission group

        ostring = permission group name (case sensitive)
                  or database dbref
        """
        groups = []
        try: 
            dbref = int(ostring.strip('#'))
            groups = self.filter(id=dbref)
        except Exception:
            pass
        if not groups:
            groups = self.filter(db_key=ostring)
        return groups
