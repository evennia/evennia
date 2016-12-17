"""
Models for the help system.

The database-tied help system is only half of Evennia's help
functionality, the other one being the auto-generated command help
that is created on the fly from each command's `__doc__` string. The
persistent database system defined here is intended for all other
forms of help that do not concern commands, like information about the
game world, policy info, rules and similar.

"""
from builtins import object

from django.db import models
from evennia.utils.idmapper.models import SharedMemoryModel
from evennia.help.manager import HelpEntryManager
from evennia.typeclasses.models import Tag, TagHandler, AliasHandler
from evennia.locks.lockhandler import LockHandler
from evennia.utils.utils import lazy_property
__all__ = ("HelpEntry",)


#------------------------------------------------------------
#
# HelpEntry
#
#------------------------------------------------------------

class HelpEntry(SharedMemoryModel):
    """
    A generic help entry.

    An HelpEntry object has the following properties defined:
      key - main name of entry
      help_category - which category entry belongs to (defaults to General)
      entrytext - the actual help text
      permissions - perm strings

    Method:
      access

    """

    #
    # HelpEntry Database Model setup
    #
    #
    # These database fields are all set using their corresponding properties,
    # named same as the field, but withtout the db_* prefix.

    # title of the help entry
    db_key = models.CharField('help key', max_length=255, unique=True, help_text='key to search for')
    # help category
    db_help_category = models.CharField("help category", max_length=255, default="General",
        help_text='organizes help entries in lists')
    # the actual help entry text, in any formatting.
    db_entrytext = models.TextField('help entry', blank=True, help_text='the main body of help text')
    # lock string storage
    db_lock_storage = models.TextField('locks', blank=True, help_text='normally view:all().')
    # tags are primarily used for permissions
    db_tags = models.ManyToManyField(Tag, null=True,
            help_text='tags on this object. Tags are simple string markers to identify, group and alias objects.')
    # (deprecated, only here to allow MUX helpfile load (don't use otherwise)).
    # TODO: remove this when not needed anymore.
    db_staff_only = models.BooleanField(default=False)

    # Database manager
    objects = HelpEntryManager()
    _is_deleted = False

    # lazy-loaded handlers

    @lazy_property
    def locks(self):
        return LockHandler(self)

    @lazy_property
    def tags(self):
        return TagHandler(self)

    @lazy_property
    def aliases(self):
        return AliasHandler(self)

    class Meta(object):
        "Define Django meta options"
        verbose_name = "Help Entry"
        verbose_name_plural = "Help Entries"

    #
    #
    # HelpEntry main class methods
    #
    #

    def __str__(self):
        return self.key

    def __unicode__(self):
        return u'%s' % self.key

    def access(self, accessing_obj, access_type='read', default=False):
        """
        Determines if another object has permission to access.
        accessing_obj - object trying to access this one
        access_type - type of access sought
        default - what to return if no lock of access_type was found
        """
        return self.locks.check(accessing_obj, access_type=access_type, default=default)
