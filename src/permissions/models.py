"""
The PermissionGroup model clumps permissions together into
manageable chunks. 
"""

from django.db import models
from src.utils.idmapper.models import SharedMemoryModel
from src.permissions.manager import PermissionGroupManager
from src.utils.utils import is_iter

#------------------------------------------------------------
#
# PermissionGroup
#
#------------------------------------------------------------

class PermissionGroup(SharedMemoryModel):
    """
    This groups permissions into a clump.

    The following properties are defined:
      key - main ident for group
      desc - optional description of group
      group_permissions - the perms stored in group
      permissions - the group's own permissions

    """

    # 
    # PermissionGroup database model setup
    # 
    # These database fields are all set using their corresponding properties,
    # named same as the field, but withtout the db_* prefix.
    #

    # identifier for the group
    db_key = models.CharField(max_length=80, unique=True)
    # description of the group's permission contents
    db_desc = models.CharField(max_length=255, null=True, blank=True)
    # the permissions stored in this group; comma separated string 
    # (NOT to be confused with the group object's own permissions!)
    db_group_permissions = models.TextField(blank=True)    
    # OBS - this is the groups OWN permissions, for accessing/changing
    # the group object itself (comma-separated string)! 
    db_permissions = models.CharField(max_length=256, blank=True)

    # Database manager 
    objects = PermissionGroupManager()

    # Wrapper properties to easily set database fields. These are
    # @property decorators that allows to access these fields using
    # normal python operations (without having to remember to save()
    # etc). So e.g. a property 'attr' has a get/set/del decorator
    # defined that allows the user to do self.attr = value, 
    # value = self.attr and del self.attr respectively (where self 
    # is the object in question).

    # key property (wraps db_key)
    #@property
    def key_get(self):
        "Getter. Allows for value = self.key"
        return self.db_key
    #@key.setter
    def key_set(self, value):
        "Setter. Allows for self.key = value"
        self.db_key = value
        self.save()
    #@key.deleter
    def key_del(self):
        "Deleter. Allows for del self.key"
        self.db_key = None
        self.save()
    key = property(key_get, key_set, key_del)

    # desc property (wraps db_desc)
    #@property
    def desc_get(self):
        "Getter. Allows for value = self.desc"
        return self.db_desc
    #@desc.setter
    def desc_set(self, value):
        "Setter. Allows for self.desc = value"
        self.db_desc = value
        self.save()
    #@desc.deleter
    def desc_del(self):
        "Deleter. Allows for del self.desc"
        self.db_desc = None
        self.save()
    desc = property(desc_get, desc_set, desc_del)

    # group_permissions property
    #@property
    def group_permissions_get(self):
        "Getter. Allows for value = self.name. Returns a list of group_permissions."
        if self.db_group_permissions:
            return [perm.strip() for perm in self.db_group_permissions.split(',')]
        return []
    #@group_permissions.setter
    def group_permissions_set(self, value):
        "Setter. Allows for self.name = value. Stores as a comma-separated string."
        if is_iter(value):
            value = ",".join([str(val).strip().lower() for val in value])
        self.db_group_permissions = value
        self.save()        
    #@group_permissions.deleter
    def group_permissions_del(self):
        "Deleter. Allows for del self.name"
        self.db_group_permissions = ""
        self.save()
    group_permissions = property(group_permissions_get, group_permissions_set, group_permissions_del)

    # permissions property
    #@property
    def permissions_get(self):
        "Getter. Allows for value = self.name. Returns a list of permissions."
        if self.db_permissions:
            return [perm.strip() for perm in self.db_permissions.split(',')]
        return []
    #@permissions.setter
    def permissions_set(self, value):
        "Setter. Allows for self.name = value. Stores as a comma-separated string."
        if is_iter(value):
            value = ",".join([str(val).strip().lower() for val in value])
        self.db_permissions = value
        self.save()        
    #@permissions.deleter
    def permissions_del(self):
        "Deleter. Allows for del self.name"
        self.db_permissions = ""
        self.save()
    permissions = property(permissions_get, permissions_set, permissions_del)


    class Meta:
        "Define Django meta options"
        verbose_name = "Permission Group"
        verbose_name_plural = "Permission Groups"
  
    #
    # PermissionGroup help method
    #
    #

    def contains(self, permission):
        """
        Checks if the given permission string is defined in the
        permission group.
        """
        return permission in self.group_permissions
