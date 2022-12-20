"""
This is the *abstract* django models for many of the database objects
in Evennia. A django abstract (obs, not the same as a Python metaclass!) is
a model which is not actually created in the database, but which only exists
for other models to inherit from, to avoid code duplication. Any model can
import and inherit from these classes.

Attributes are database objects stored on other objects. The implementing
class needs to supply a ForeignKey field attr_object pointing to the kind
of object being mapped. Attributes storing iterables actually store special
types of iterables named PackedList/PackedDict respectively. These make
sure to save changes to them to database - this is criticial in order to
allow for obj.db.mylist[2] = data. Also, all dbobjects are saved as
dbrefs but are also aggressively cached.

TypedObjects are objects 'decorated' with a typeclass - that is, the typeclass
(which is a normal Python class implementing some special tricks with its
get/set attribute methods, allows for the creation of all sorts of different
objects all with the same database object underneath. Usually attributes are
used to permanently store things not hard-coded as field on the database object.
The admin should usually not have to deal directly  with the database object
layer.

This module also contains the Managers for the respective models; inherit from
these to create custom managers.

"""
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import signals
from django.db.models.base import ModelBase
from django.urls import reverse
from django.utils.encoding import smart_str
from django.utils.text import slugify

from evennia.locks.lockhandler import LockHandler
from evennia.server.signals import SIGNAL_TYPED_OBJECT_POST_RENAME
from evennia.typeclasses import managers
from evennia.typeclasses.attributes import (
    Attribute,
    AttributeHandler,
    AttributeProperty,
    DbHolder,
    InMemoryAttributeBackend,
    ModelAttributeBackend,
)
from evennia.typeclasses.tags import (
    AliasHandler,
    PermissionHandler,
    Tag,
    TagHandler,
    TagProperty,
)
from evennia.utils.idmapper.models import SharedMemoryModel, SharedMemoryModelBase
from evennia.utils.logger import log_trace
from evennia.utils.utils import class_from_module, inherits_from, is_iter, lazy_property

__all__ = ("TypedObject",)

TICKER_HANDLER = None

_PERMISSION_HIERARCHY = [p.lower() for p in settings.PERMISSION_HIERARCHY]
_TYPECLASS_AGGRESSIVE_CACHE = settings.TYPECLASS_AGGRESSIVE_CACHE
_GA = object.__getattribute__
_SA = object.__setattr__


# signal receivers. Connected in __new__


def call_at_first_save(sender, instance, created, **kwargs):
    """
    Receives a signal just after the object is saved.

    """
    if created:
        instance.at_first_save()


def remove_attributes_on_delete(sender, instance, **kwargs):
    """
    Wipe object's Attributes when it's deleted

    """
    instance.db_attributes.all().delete()


# ------------------------------------------------------------
#
# Typed Objects
#
# ------------------------------------------------------------


#
# Meta class for typeclasses
#


class TypeclassBase(SharedMemoryModelBase):
    """
    Metaclass which should be set for the root of model proxies
    that don't define any new fields, like Object, Script etc. This
    is the basis for the typeclassing system.

    """

    def __new__(cls, name, bases, attrs):
        """
        We must define our Typeclasses as proxies. We also store the
        path directly on the class, this is required by managers.
        """

        # storage of stats
        attrs["typename"] = name
        attrs["path"] = "%s.%s" % (attrs["__module__"], name)

        def _get_dbmodel(bases):
            """Recursively get the dbmodel"""
            if not hasattr(bases, "__iter__"):
                bases = [bases]
            for base in bases:
                try:
                    if base._meta.proxy or base._meta.abstract:
                        for kls in base._meta.parents:
                            return _get_dbmodel(kls)
                except AttributeError:
                    # this happens if trying to parse a non-typeclass mixin parent,
                    # without a _meta
                    continue
                else:
                    return base
                return None

        dbmodel = _get_dbmodel(bases)

        if not dbmodel:
            raise TypeError(f"{name} does not appear to inherit from a database model.")

        # typeclass proxy setup
        # first check explicit __applabel__ on the typeclass, then figure
        # it out from the dbmodel
        if "__applabel__" not in attrs:
            # find the app-label in one of the bases, usually the dbmodel
            attrs["__applabel__"] = dbmodel._meta.app_label

        if "Meta" not in attrs:

            class Meta:
                proxy = True
                app_label = attrs.get("__applabel__", "typeclasses")

            attrs["Meta"] = Meta
        attrs["Meta"].proxy = True

        new_class = ModelBase.__new__(cls, name, bases, attrs)

        # django doesn't support inheriting proxy models so we hack support for
        # it here by injecting `proxy_for_model` to the actual dbmodel.
        # Unfortunately we cannot also set the correct model_name, because this
        # would block multiple-inheritance of typeclasses (Django doesn't allow
        # multiple bases of the same model).
        if dbmodel:
            new_class._meta.proxy_for_model = dbmodel
            # Maybe Django will eventually handle this in the future:
            # new_class._meta.model_name = dbmodel._meta.model_name

        # attach signals
        signals.post_save.connect(call_at_first_save, sender=new_class)
        signals.pre_delete.connect(remove_attributes_on_delete, sender=new_class)
        return new_class


#
# Main TypedObject abstraction
#


class TypedObject(SharedMemoryModel):
    """
    Abstract Django model.

    This is the basis for a typed object. It also contains all the
    mechanics for managing connected attributes.

    The TypedObject has the following properties:

    - key - main name
    - name - alias for key
    - typeclass_path - the path to the decorating typeclass
    - typeclass - auto-linked typeclass
    - date_created - time stamp of object creation
    - permissions - perm strings
    - dbref - #id of object
    - db - persistent attribute storage
    - ndb - non-persistent attribute storage

    """

    #
    # TypedObject Database Model setup
    #
    #
    # These databse fields are all accessed and set using their corresponding
    # properties, named same as the field, but without the db_* prefix
    # (no separate save() call is needed)

    # Main identifier of the object, for searching. Is accessed with self.key
    # or self.name
    db_key = models.CharField("key", max_length=255, db_index=True)
    # This is the python path to the type class this object is tied to. The
    # typeclass is what defines what kind of Object this is)
    db_typeclass_path = models.CharField(
        "typeclass",
        max_length=255,
        null=True,
        help_text=(
            "this defines what 'type' of entity this is. This variable holds "
            "a Python path to a module with a valid Evennia Typeclass."
        ),
        db_index=True,
    )
    # Creation date. This is not changed once the object is created.
    db_date_created = models.DateTimeField("creation date", editable=False, auto_now_add=True)
    # Lock storage
    db_lock_storage = models.TextField(
        "locks",
        blank=True,
        help_text=(
            "locks limit access to an entity. A lock is defined as a 'lock string' "
            "on the form 'type:lockfunctions', defining what functionality is locked and "
            "how to determine access. Not defining a lock means no access is granted."
        ),
    )
    # many2many relationships
    db_attributes = models.ManyToManyField(
        Attribute,
        help_text=(
            "attributes on this object. An attribute can hold any pickle-able "
            "python object (see docs for special cases)."
        ),
    )
    db_tags = models.ManyToManyField(
        Tag,
        help_text=(
            "tags on this object. Tags are simple string markers to identify, "
            "group and alias objects."
        ),
    )

    # Database manager
    objects = managers.TypedObjectManager()

    # quick on-object typeclass cache for speed
    _cached_typeclass = None

    # typeclass mechanism

    def set_class_from_typeclass(self, typeclass_path=None):
        if typeclass_path:
            try:
                self.__class__ = class_from_module(
                    typeclass_path, defaultpaths=settings.TYPECLASS_PATHS
                )
            except Exception:
                log_trace()
                try:
                    self.__class__ = class_from_module(self.__settingsclasspath__)
                except Exception:
                    log_trace()
                    try:
                        self.__class__ = class_from_module(self.__defaultclasspath__)
                    except Exception:
                        log_trace()
                        self.__class__ = self._meta.concrete_model or self.__class__
            finally:
                self.db_typeclass_path = typeclass_path
        elif self.db_typeclass_path:
            try:
                self.__class__ = class_from_module(self.db_typeclass_path)
            except Exception:
                log_trace()
                try:
                    self.__class__ = class_from_module(self.__defaultclasspath__)
                except Exception:
                    log_trace()
                    self.__dbclass__ = self._meta.concrete_model or self.__class__
        else:
            self.db_typeclass_path = "%s.%s" % (self.__module__, self.__class__.__name__)
        # important to put this at the end since _meta is based on the set __class__
        try:
            self.__dbclass__ = self._meta.concrete_model or self.__class__
        except AttributeError:
            err_class = repr(self.__class__)
            self.__class__ = class_from_module("evennia.objects.objects.DefaultObject")
            self.__dbclass__ = class_from_module("evennia.objects.models.ObjectDB")
            self.db_typeclass_path = "evennia.objects.objects.DefaultObject"
            log_trace(
                "Critical: Class %s of %s is not a valid typeclass!\nTemporarily falling back"
                " to %s." % (err_class, self, self.__class__)
            )

    def __init__(self, *args, **kwargs):
        """
        The `__init__` method of typeclasses is the core operational
        code of the typeclass system, where it dynamically re-applies
        a class based on the db_typeclass_path database field rather
        than use the one in the model.

        Args:
            Passed through to parent.

        Keyword Args:
            Passed through to parent.

        Notes:
            The loading mechanism will attempt the following steps:

            1. Attempt to load typeclass given on command line
            2. Attempt to load typeclass stored in db_typeclass_path
            3. Attempt to load `__settingsclasspath__`, which is by the
               default classes defined to be the respective user-set
               base typeclass settings, like `BASE_OBJECT_TYPECLASS`.
            4. Attempt to load `__defaultclasspath__`, which is the
               base classes in the library, like DefaultObject etc.
            5. If everything else fails, use the database model.

            Normal operation is to load successfully at either step 1
            or 2 depending on how the class was called. Tracebacks
            will be logged for every step the loader must take beyond
            2.

        """
        typeclass_path = kwargs.pop("typeclass", None)
        super().__init__(*args, **kwargs)
        self.set_class_from_typeclass(typeclass_path=typeclass_path)

    def init_evennia_properties(self):
        """
        Called by creation methods; makes sure to initialize Attribute/TagProperties
        by fetching them once.
        """
        for propkey, prop in self.__class__.__dict__.items():
            if isinstance(prop, (AttributeProperty, TagProperty)):
                try:
                    getattr(self, propkey)
                except Exception:
                    log_trace()

    # initialize all handlers in a lazy fashion
    @lazy_property
    def attributes(self):
        return AttributeHandler(self, ModelAttributeBackend)

    @lazy_property
    def locks(self):
        return LockHandler(self)

    @lazy_property
    def tags(self):
        return TagHandler(self)

    @lazy_property
    def aliases(self):
        return AliasHandler(self)

    @lazy_property
    def permissions(self):
        return PermissionHandler(self)

    @lazy_property
    def nattributes(self):
        return AttributeHandler(self, InMemoryAttributeBackend)

    class Meta:
        """
        Django setup info.
        """

        abstract = True
        verbose_name = "Evennia Database Object"
        ordering = ["-db_date_created", "id", "db_typeclass_path", "db_key"]

    # wrapper
    # Wrapper properties to easily set database fields. These are
    # @property decorators that allows to access these fields using
    # normal python operations (without having to remember to save()
    # etc). So e.g. a property 'attr' has a get/set/del decorator
    # defined that allows the user to do self.attr = value,
    # value = self.attr and del self.attr respectively (where self
    # is the object in question).

    # name property (alias to self.key)
    def __name_get(self):
        return self.key

    def __name_set(self, value):
        self.key = value

    def __name_del(self):
        raise Exception("Cannot delete name")

    name = property(__name_get, __name_set, __name_del)

    # key property (overrides's the idmapper's db_key for the at_rename hook)
    @property
    def key(self):
        return self.db_key

    @key.setter
    def key(self, value):
        oldname = str(self.db_key)
        self.db_key = value
        self.save(update_fields=["db_key"])
        self.at_rename(oldname, value)
        SIGNAL_TYPED_OBJECT_POST_RENAME.send(sender=self, old_key=oldname, new_key=value)

    #
    #
    # TypedObject main class methods and properties
    #
    #

    def __eq__(self, other):
        try:
            return self.__dbclass__ == other.__dbclass__ and self.dbid == other.dbid
        except AttributeError:
            return False

    def __hash__(self):
        # this is required to maintain hashing
        return super().__hash__()

    def __str__(self):
        return smart_str("%s" % self.db_key)

    def __repr__(self):
        return "%s" % self.db_key

    # @property
    def __dbid_get(self):
        """
        Caches and returns the unique id of the object.
        Use this instead of self.id, which is not cached.
        """
        return self.id

    def __dbid_set(self, value):
        raise Exception("dbid cannot be set!")

    def __dbid_del(self):
        raise Exception("dbid cannot be deleted!")

    dbid = property(__dbid_get, __dbid_set, __dbid_del)

    # @property
    def __dbref_get(self):
        """
        Returns the object's dbref on the form #NN.
        """
        return "#%s" % self.id

    def __dbref_set(self):
        raise Exception("dbref cannot be set!")

    def __dbref_del(self):
        raise Exception("dbref cannot be deleted!")

    dbref = property(__dbref_get, __dbref_set, __dbref_del)

    def at_idmapper_flush(self):
        """
        This is called when the idmapper cache is flushed and
        allows customized actions when this happens.

        Returns:
            do_flush (bool): If True, flush this object as normal. If
                False, don't flush and expect this object to handle
                the flushing on its own.

        Notes:
            The default implementation relies on being able to clear
            Django's Foreignkey cache on objects not affected by the
            flush (notably objects with an NAttribute stored). We rely
            on this cache being stored on the format "_<fieldname>_cache".
            If Django were to change this name internally, we need to
            update here (unlikely, but marking just in case).

        """
        if self.nattributes.all():
            # we can't flush this object if we have non-persistent
            # attributes stored - those would get lost! Nevertheless
            # we try to flush as many references as we can.
            self.attributes.reset_cache()
            self.tags.reset_cache()
            # flush caches for all related fields
            for field in self._meta.fields:
                name = "_%s_cache" % field.name
                if field.is_relation and name in self.__dict__:
                    # a foreignkey - remove its cache
                    del self.__dict__[name]
            return False
        # a normal flush
        return True

    #
    # Object manipulation methods
    #

    def at_init(self):
        """
        Called when this object is loaded into cache. This is  more reliable
        than to override `__init__`.

        """
        pass

    @classmethod
    def search(cls, query, **kwargs):
        """
        Overridden by class children. This implements a common API.

        Args:
            query (str): A search query.
            **kwargs: Other search parameters.

        Returns:
            list: A list of 0, 1 or more matches, only of this typeclass.

        """
        if cls.objects.dbref(query):
            return [cls.objects.get_id(query)]
        return list(cls.objects.filter(db_key__lower=query))

    def is_typeclass(self, typeclass, exact=False):
        """
        Returns true if this object has this type OR has a typeclass
        which is an subclass of the given typeclass. This operates on
        the actually loaded typeclass (this is important since a
        failing typeclass may instead have its default currently
        loaded) typeclass - can be a class object or the python path
        to such an object to match against.

        Args:
            typeclass (str or class): A class or the full python path
                to the class to check.
            exact (bool, optional): Returns true only if the object's
                type is exactly this typeclass, ignoring parents.

        Returns:
            is_typeclass (bool): If this typeclass matches the given
                typeclass.

        """
        if isinstance(typeclass, str):
            typeclass = [typeclass] + [
                "%s.%s" % (prefix, typeclass) for prefix in settings.TYPECLASS_PATHS
            ]
        else:
            typeclass = [typeclass.path]

        selfpath = self.path
        if exact:
            # check only exact match
            return selfpath in typeclass
        else:
            # check parent chain
            return any(
                hasattr(cls, "path") and cls.path in typeclass for cls in self.__class__.mro()
            )

    def swap_typeclass(
        self,
        new_typeclass,
        clean_attributes=False,
        run_start_hooks="all",
        no_default=True,
        clean_cmdsets=False,
    ):
        """
        This performs an in-situ swap of the typeclass. This means
        that in-game, this object will suddenly be something else.
        Account will not be affected. To 'move' an account to a different
        object entirely (while retaining this object's type), use
        self.account.swap_object().

        Note that this might be an error prone operation if the
        old/new typeclass was heavily customized - your code
        might expect one and not the other, so be careful to
        bug test your code if using this feature! Often its easiest
        to create a new object and just swap the account over to
        that one instead.

        Args:
            new_typeclass (str or classobj): Type to switch to.
            clean_attributes (bool or list, optional): Will delete all
                attributes stored on this object (but not any of the
                database fields such as name or location). You can't get
                attributes back, but this is often the safest bet to make
                sure nothing in the new typeclass clashes with the old
                one. If you supply a list, only those named attributes
                will be cleared.
            run_start_hooks (str or None, optional): This is either None,
                to not run any hooks, "all" to run all hooks defined by
                at_first_start, or a string with space-separated hook-names to run
                (for example 'at_object_creation'). This will
                always be called without arguments.
            no_default (bool, optiona): If set, the swapper will not
                allow for swapping to a default typeclass in case the
                given one fails for some reason. Instead the old one will
                be preserved.
            clean_cmdsets (bool, optional): Delete all cmdsets on the object.

        """

        if not callable(new_typeclass):
            # this is an actual class object - build the path
            new_typeclass = class_from_module(new_typeclass, defaultpaths=settings.TYPECLASS_PATHS)

        # if we get to this point, the class is ok.

        if inherits_from(self, "evennia.scripts.models.ScriptDB"):
            if self.interval > 0:
                raise RuntimeError(
                    "Cannot use swap_typeclass on time-dependent "
                    "Script '%s'.\nStop and start a new Script of the "
                    "right type instead." % self.key
                )

        self.typeclass_path = new_typeclass.path
        self.__class__ = new_typeclass

        if clean_attributes:
            # Clean out old attributes
            if is_iter(clean_attributes):
                for attr in clean_attributes:
                    self.attributes.remove(attr)
                for nattr in clean_attributes:
                    if hasattr(self.ndb, nattr):
                        self.nattributes.remove(nattr)
            else:
                self.attributes.clear()
                self.nattributes.clear()
        if clean_cmdsets:
            # purge all cmdsets
            self.cmdset.clear()
            self.cmdset.remove_default()

        if run_start_hooks == "all":
            # fake this call to mimic the first save
            self.at_first_save()
        elif run_start_hooks:
            # a custom hook-name to call.
            for start_hook in str(run_start_hooks).split():
                getattr(self, run_start_hooks)()

    #
    # Lock / permission methods
    #

    def access(
        self, accessing_obj, access_type="read", default=False, no_superuser_bypass=False, **kwargs
    ):
        """
        Determines if another object has permission to access this one.

        Args:
            accessing_obj (str): Object trying to access this one.
            access_type (str, optional): Type of access sought.
            default (bool, optional): What to return if no lock of
                access_type was found
            no_superuser_bypass (bool, optional): Turn off the
                superuser lock bypass (be careful with this one).

        Keyword Args:
            kwar (any): Ignored, but is there to make the api
                consistent with the object-typeclass method access, which
                use it to feed to its hook methods.

        """
        return self.locks.check(
            accessing_obj,
            access_type=access_type,
            default=default,
            no_superuser_bypass=no_superuser_bypass,
        )

    def check_permstring(self, permstring):
        """
        This explicitly checks if we hold particular permission
        without involving any locks.

        Args:
            permstring (str): The permission string to check against.

        Returns:
            result (bool): If the permstring is passed or not.

        """
        if hasattr(self, "account"):
            if (
                self.account
                and self.account.is_superuser
                and not self.account.attributes.get("_quell")
            ):
                return True
        else:
            if self.is_superuser and not self.attributes.get("_quell"):
                return True

        if not permstring:
            return False
        perm = permstring.lower()
        perms = [p.lower() for p in self.permissions.all()]
        if perm in perms:
            # simplest case - we have a direct match
            return True
        if perm in _PERMISSION_HIERARCHY:
            # check if we have a higher hierarchy position
            ppos = _PERMISSION_HIERARCHY.index(perm)
            return any(
                True
                for hpos, hperm in enumerate(_PERMISSION_HIERARCHY)
                if hperm in perms and hpos > ppos
            )
        # we ignore pluralization (english only)
        if perm.endswith("s"):
            return self.check_permstring(perm[:-1])

        return False

    #
    # Deletion methods
    #

    def _deleted(self, *args, **kwargs):
        """
        Scrambling method for already deleted objects
        """
        raise ObjectDoesNotExist("This object was already deleted!")

    def delete(self):
        """
        Cleaning up handlers on the typeclass level

        """
        global TICKER_HANDLER
        self.permissions.clear()
        self.attributes.clear()
        self.aliases.clear()
        if hasattr(self, "nicks"):
            self.nicks.clear()
        # scrambling properties
        self.delete = self._deleted
        super().delete()

    #
    # Attribute storage
    #

    @property
    def db(self):
        """
        Attribute handler wrapper. Allows for the syntax

        ```python
           obj.db.attrname = value
           # and
           value = obj.db.attrname
           # and
           del obj.db.attrname
           # and
           all_attr = obj.db.all()
           # (unless there is an attribute
           #  named 'all', in which case that will be returned instead).
        ```

        """
        try:
            return self._db_holder
        except AttributeError:
            self._db_holder = DbHolder(self, "attributes")
            return self._db_holder

    @db.setter
    def db(self, value):
        "Stop accidentally replacing the db object"
        string = "Cannot assign directly to db object! "
        string += "Use db.attr=value instead."
        raise Exception(string)

    @db.deleter
    def db(self):
        "Stop accidental deletion."
        raise Exception("Cannot delete the db object!")

    #
    # Non-persistent (ndb) storage
    #

    @property
    def ndb(self):
        """
        A non-attr_obj store (ndb: NonDataBase). Everything stored
        to this is guaranteed to be cleared when a server is shutdown.
        Syntax is same as for the _get_db_holder() method and
        property, e.g. obj.ndb.attr = value etc.
        """
        try:
            return self._ndb_holder
        except AttributeError:
            self._ndb_holder = DbHolder(self, "nattrhandler", manager_name="nattributes")
            return self._ndb_holder

    @ndb.setter
    def ndb(self, value):
        "Stop accidentally replacing the ndb object"
        string = "Cannot assign directly to ndb object! "
        string += "Use ndb.attr=value instead."
        raise Exception(string)

    @ndb.deleter
    def ndb(self):
        "Stop accidental deletion."
        raise Exception("Cannot delete the ndb object!")

    def get_display_name(self, looker, **kwargs):
        """
        Displays the name of the object in a viewer-aware manner.

        Args:
            looker (TypedObject, optional): The object or account that is looking
                at/getting inforamtion for this object. If not given, some
                'safe' minimum level should be returned.

        Returns:
            name (str): A string containing the name of the object,
                including the DBREF if this user is privileged to control
                said object.

        Notes:
            This function could be extended to change how object names
            appear to users in character, but be wary. This function
            does not change an object's keys or aliases when
            searching, and is expected to produce something useful for
            builders.

        """
        if self.access(looker, access_type="controls"):
            return "{}(#{})".format(self.name, self.id)
        return self.name

    def get_extra_info(self, looker, **kwargs):
        """
        Used when an object is in a list of ambiguous objects as an
        additional information tag.

        For instance, if you had potions which could have varying
        levels of liquid left in them, you might want to display how
        many drinks are left in each when selecting which to drop, but
        not in your normal inventory listing.

        Args:
            looker (TypedObject): The object or account that is looking
                at/getting information for this object.

        Returns:
            info (str): A string with disambiguating information,
                conventionally with a leading space.

        """

        if self.location == looker:
            return " (carried)"
        return ""

    def at_rename(self, oldname, newname):
        """
        This Hook is called by @name on a successful rename.

        Args:
            oldname (str): The instance's original name.
            newname (str): The new name for the instance.

        """
        pass

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
        """
        Returns the URI path for a View that allows users to view details for
        this object.

        Returns:
            path (str): URI path to object detail page, if defined.

        Examples:

            ```python
            Oscar (Character) = '/characters/oscar/1/'
            ```

            For this to work, the developer must have defined a named view somewhere
            in urls.py that follows the format 'modelname-action', so in this case
            a named view of 'character-detail' would be referenced by this method.


            ```python
            url(r'characters/(?P<slug>[\w\d\-]+)/(?P<pk>[0-9]+)/$',
                CharDetailView.as_view(), name='character-detail')
            ```

            If no View has been created and defined in urls.py, returns an
            HTML anchor.

            This method is naive and simply returns a path. Securing access to
            the actual view and limiting who can view this object is the
            developer's responsibility.

        """
        try:
            return reverse(
                "%s-detail" % slugify(self._meta.verbose_name),
                kwargs={"pk": self.pk, "slug": slugify(self.name)},
            )
        except Exception:
            return "#"

    def web_get_puppet_url(self):
        """
        Returns the URI path for a View that allows users to puppet a specific
        object.

        Returns:
            str: URI path to object puppet page, if defined.

        Examples:
            ::

                Oscar (Character) = '/characters/oscar/1/puppet/'

            For this to work, the developer must have defined a named view somewhere
            in urls.py that follows the format 'modelname-action', so in this case
            a named view of 'character-puppet' would be referenced by this method.
            ::

                url(r'characters/(?P<slug>[\w\d\-]+)/(?P<pk>[0-9]+)/puppet/$',
                    CharPuppetView.as_view(), name='character-puppet')

            If no View has been created and defined in urls.py, returns an
            HTML anchor.

            This method is naive and simply returns a path. Securing access to
            the actual view and limiting who can view this object is the developer's
            responsibility.


        """
        try:
            return reverse(
                "%s-puppet" % slugify(self._meta.verbose_name),
                kwargs={"pk": self.pk, "slug": slugify(self.name)},
            )
        except Exception:
            return "#"

    def web_get_update_url(self):
        """
        Returns the URI path for a View that allows users to update this
        object.

        Returns:
            str: URI path to object update page, if defined.

        Examples:

            ```python
            Oscar (Character) = '/characters/oscar/1/change/'
            ```

            For this to work, the developer must have defined a named view somewhere
            in urls.py that follows the format 'modelname-action', so in this case
            a named view of 'character-update' would be referenced by this method.
            ::

                url(r'characters/(?P<slug>[\w\d\-]+)/(?P<pk>[0-9]+)/change/$',
                CharUpdateView.as_view(), name='character-update')

            If no View has been created and defined in urls.py, returns an
            HTML anchor.

            This method is naive and simply returns a path. Securing access to
            the actual view and limiting who can modify objects is the developer's
            responsibility.


        """
        try:
            return reverse(
                "%s-update" % slugify(self._meta.verbose_name),
                kwargs={"pk": self.pk, "slug": slugify(self.name)},
            )
        except Exception:
            return "#"

    def web_get_delete_url(self):
        """
        Returns the URI path for a View that allows users to delete this object.

        Returns:
            path (str): URI path to object deletion page, if defined.

        Examples:

            ```python
            Oscar (Character) = '/characters/oscar/1/delete/'
            ```

            For this to work, the developer must have defined a named view
            somewhere in urls.py that follows the format 'modelname-action', so
            in this case a named view of 'character-detail' would be referenced
            by this method.
            ::

                url(r'characters/(?P<slug>[\w\d\-]+)/(?P<pk>[0-9]+)/delete/$',
                CharDeleteView.as_view(), name='character-delete')

            If no View has been created and defined in urls.py, returns an HTML
            anchor.

            This method is naive and simply returns a path. Securing access to
            the actual view and limiting who can delete this object is the
            developer's responsibility.


        """
        try:
            return reverse(
                "%s-delete" % slugify(self._meta.verbose_name),
                kwargs={"pk": self.pk, "slug": slugify(self.name)},
            )
        except Exception:
            return "#"

    # Used by Django Sites/Admin
    get_absolute_url = web_get_detail_url
