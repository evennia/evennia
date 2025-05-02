"""
Models for the help system.

The database-tied help system is only half of Evennia's help
functionality, the other one being the auto-generated command help
that is created on the fly from each command's `__doc__` string. The
persistent database system defined here is intended for all other
forms of help that do not concern commands, like information about the
game world, policy info, rules and similar.

"""

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from evennia.help.manager import HelpEntryManager
from evennia.locks.lockhandler import LockHandler
from evennia.typeclasses.models import AliasHandler, Tag, TagHandler
from evennia.utils.idmapper.models import SharedMemoryModel
from evennia.utils.utils import lazy_property

__all__ = ("HelpEntry",)


# ------------------------------------------------------------
#
# HelpEntry
#
# ------------------------------------------------------------


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
    db_key = models.CharField(
        "help key", max_length=255, unique=True, help_text="key to search for"
    )

    # help category
    db_help_category = models.CharField(
        "help category",
        max_length=255,
        default="General",
        help_text="organizes help entries in lists",
    )

    # the actual help entry text, in any formatting.
    db_entrytext = models.TextField(
        "help entry", blank=True, help_text="the main body of help text"
    )
    # lock string storage
    db_lock_storage = models.TextField("locks", blank=True, help_text="normally view:all().")
    # tags are primarily used for permissions
    db_tags = models.ManyToManyField(
        Tag,
        blank=True,
        help_text="tags on this object. Tags are simple string markers to "
        "identify, group and alias objects.",
    )
    # Creation date. This is not changed once the object is created. This is in UTC,
    # use the property date_created to get it in local time.
    db_date_created = models.DateTimeField("creation date", editable=False, auto_now=True)

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

    @property
    def date_created(self):
        """Return the field in localized time based on settings.TIME_ZONE."""
        return timezone.localtime(self.db_date_created)

    class Meta:
        "Define Django meta options"

        verbose_name = "Help Entry"
        verbose_name_plural = "Help Entries"

    #
    #
    # HelpEntry main class methods
    #
    #
    def __str__(self):
        return str(self.key)

    def __repr__(self):
        return f"<HelpEntry {self.key}>"

    def access(self, accessing_obj, access_type="read", default=True):
        """
        Determines if another object has permission to access this help entry.

        Accesses used by default:
            'read' - read the help entry itself.
            'view' - see help entry in help index.

        Args:
            accessing_obj (Object or Account): Entity trying to access this one.
            access_type (str): type of access sought.
            default (bool): What to return if no lock of `access_type` was found.

        """
        return self.locks.check(accessing_obj, access_type=access_type, default=default)

    @property
    def search_index_entry(self):
        """
        Property for easily retaining a search index entry for this object.
        """
        return {
            "key": self.db_key,
            "aliases": " ".join(self.aliases.all()),
            "no_prefix": "",
            "category": self.db_help_category,
            "text": self.db_entrytext,
            "tags": " ".join(str(tag) for tag in self.tags.all()),
        }

    #
    # Web/Django methods
    #

    def web_get_admin_url(self):
        """
        Returns the URI path for the Django Admin page for this object.

        ex. Account#1 = '/admin/accounts/accountdb/1/change/'

        Returns:
            path (str): URI path to Django Admin page for object.

        """
        content_type = ContentType.objects.get_for_model(self.__class__)
        return reverse(
            "admin:%s_%s_change" % (content_type.app_label, content_type.model), args=(self.id,)
        )

    @classmethod
    def web_get_create_url(cls):
        """
        Returns the URI path for a View that allows users to create new
        instances of this object.

        ex. Chargen = '/characters/create/'

        For this to work, the developer must have defined a named view somewhere
        in urls.py that follows the format 'modelname-action', so in this case
        a named view of 'character-create' would be referenced by this method.

        ex.
        ::

            url(r'characters/create/', ChargenView.as_view(), name='character-create')

        If no View has been created and defined in urls.py, returns an
        HTML anchor.

        This method is naive and simply returns a path. Securing access to
        the actual view and limiting who can create new objects is the
        developer's responsibility.

        Returns:
            path (str): URI path to object creation page, if defined.

        """
        try:
            return reverse("%s-create" % slugify(cls._meta.verbose_name))
        except Exception:
            return "#"

    def web_get_detail_url(self):
        r"""
        Returns the URI path for a View that allows users to view details for
        this object.

        ex. Oscar (Character) = '/characters/oscar/1/'

        For this to work, the developer must have defined a named view somewhere
        in urls.py that follows the format 'modelname-action', so in this case
        a named view of 'character-detail' would be referenced by this method.

        ex.
        ::
            url(r'characters/(?P<slug>[\w\d\-]+)/(?P<pk>[0-9]+)/$',
                CharDetailView.as_view(), name='character-detail')

        If no View has been created and defined in urls.py, returns an
        HTML anchor.

        This method is naive and simply returns a path. Securing access to
        the actual view and limiting who can view this object is the developer's
        responsibility.

        Returns:
            path (str): URI path to object detail page, if defined.

        """

        try:
            return reverse(
                "%s-detail" % slugify(self._meta.verbose_name),
                kwargs={"category": slugify(self.db_help_category), "topic": slugify(self.db_key)},
            )
        except Exception:
            return "#"

    def web_get_update_url(self):
        r"""
        Returns the URI path for a View that allows users to update this
        object.

        ex. Oscar (Character) = '/characters/oscar/1/change/'

        For this to work, the developer must have defined a named view somewhere
        in urls.py that follows the format 'modelname-action', so in this case
        a named view of 'character-update' would be referenced by this method.

        ex.
        ::

            url(r'characters/(?P<slug>[\w\d\-]+)/(?P<pk>[0-9]+)/change/$',
                CharUpdateView.as_view(), name='character-update')

        If no View has been created and defined in urls.py, returns an
        HTML anchor.

        This method is naive and simply returns a path. Securing access to
        the actual view and limiting who can modify objects is the developer's
        responsibility.

        Returns:
            path (str): URI path to object update page, if defined.

        """
        try:
            return reverse(
                "%s-update" % slugify(self._meta.verbose_name),
                kwargs={"category": slugify(self.db_help_category), "topic": slugify(self.db_key)},
            )
        except Exception:
            return "#"

    def web_get_delete_url(self):
        r"""
        Returns the URI path for a View that allows users to delete this object.

        ex. Oscar (Character) = '/characters/oscar/1/delete/'

        For this to work, the developer must have defined a named view somewhere
        in urls.py that follows the format 'modelname-action', so in this case
        a named view of 'character-detail' would be referenced by this method.

        ex.
        ::

            url(r'characters/(?P<slug>[\w\d\-]+)/(?P<pk>[0-9]+)/delete/$',
                CharDeleteView.as_view(), name='character-delete')

        If no View has been created and defined in urls.py, returns an
        HTML anchor.

        This method is naive and simply returns a path. Securing access to
        the actual view and limiting who can delete this object is the developer's
        responsibility.

        Returns:
            path (str): URI path to object deletion page, if defined.

        """
        try:
            return reverse(
                "%s-delete" % slugify(self._meta.verbose_name),
                kwargs={"category": slugify(self.db_help_category), "topic": slugify(self.db_key)},
            )
        except Exception:
            return "#"

    # Used by Django Sites/Admin
    get_absolute_url = web_get_detail_url
