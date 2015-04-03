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

from django.db.models import signals

from django.db import models
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.utils.encoding import smart_str

from evennia.typeclasses.attributes import Attribute, AttributeHandler, NAttributeHandler
from evennia.typeclasses.tags import Tag, TagHandler, AliasHandler, PermissionHandler

from evennia.utils.idmapper.models import SharedMemoryModel, SharedMemoryModelBase

from evennia.typeclasses import managers
from evennia.locks.lockhandler import LockHandler
from evennia.utils.utils import (
        is_iter, inherits_from, lazy_property,
        class_from_module)
from evennia.utils.logger import log_trace
from evennia.typeclasses.django_new_patch import patched_new

__all__ = ("TypedObject", )

TICKER_HANDLER = None

_PERMISSION_HIERARCHY = [p.lower() for p in settings.PERMISSION_HIERARCHY]
_TYPECLASS_AGGRESSIVE_CACHE = settings.TYPECLASS_AGGRESSIVE_CACHE
_GA = object.__getattribute__
_SA = object.__setattr__

#------------------------------------------------------------
#
# Typed Objects
#
#------------------------------------------------------------


#
# Meta class for typeclasses
#


# signal receivers. Assigned in __new__
def post_save(sender, instance, created, **kwargs):
    """
    Receives a signal just after the object is saved.
    """
    if created:
        instance.at_first_save()

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
        attrs["path"] =  "%s.%s" % (attrs["__module__"], name)

        # typeclass proxy setup
        if not "Meta" in attrs:
            class Meta:
                proxy = True
                app_label = attrs.get("__applabel__", "typeclasses")
            attrs["Meta"] = Meta
        attrs["Meta"].proxy = True

        # patch for django proxy multi-inheritance
        # this is a copy of django.db.models.base.__new__
        # with a few lines changed as per
        # https://code.djangoproject.com/ticket/11560
        new_class = patched_new(cls, name, bases, attrs)

        # attach signal
        signals.post_save.connect(post_save, sender=new_class)

        return new_class


class DbHolder(object):
    "Holder for allowing property access of attributes"
    def __init__(self, obj, name, manager_name='attributes'):
        _SA(self, name, _GA(obj, manager_name))
        _SA(self, 'name', name)

    def __getattribute__(self, attrname):
        if attrname == 'all':
            # we allow to overload our default .all
            attr = _GA(self, _GA(self, 'name')).get("all")
            if attr:
                return attr
            return self.all
        return _GA(self, _GA(self, 'name')).get(attrname)

    def __setattr__(self, attrname, value):
        _GA(self, _GA(self, 'name')).add(attrname, value)

    def __delattr__(self, attrname):
        _GA(self, _GA(self, 'name')).remove(attrname)

    def get_all(self):
        return _GA(self, _GA(self, 'name')).all()
    all = property(get_all)

#
# Main TypedObject abstraction
#


class TypedObject(SharedMemoryModel):
    """
    Abstract Django model.

    This is the basis for a typed object. It also contains all the
    mechanics for managing connected attributes.

    The TypedObject has the following properties:
      key - main name
      name - alias for key
      typeclass_path - the path to the decorating typeclass
      typeclass - auto-linked typeclass
      date_created - time stamp of object creation
      permissions - perm strings
      dbref - #id of object
      db - persistent attribute storage
      ndb - non-persistent attribute storage

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
    db_key = models.CharField('key', max_length=255, db_index=True)
    # This is the python path to the type class this object is tied to. The
    # typeclass is what defines what kind of Object this is)
    db_typeclass_path = models.CharField('typeclass', max_length=255, null=True,
            help_text="this defines what 'type' of entity this is. This variable holds a Python path to a module with a valid Evennia Typeclass.")
    # Creation date. This is not changed once the object is created.
    db_date_created = models.DateTimeField('creation date', editable=False, auto_now_add=True)
    # Lock storage
    db_lock_storage = models.TextField('locks', blank=True,
            help_text="locks limit access to an entity. A lock is defined as a 'lock string' on the form 'type:lockfunctions', defining what functionality is locked and how to determine access. Not defining a lock means no access is granted.")
    # many2many relationships
    db_attributes = models.ManyToManyField(Attribute, null=True,
            help_text='attributes on this object. An attribute can hold any pickle-able python object (see docs for special cases).')
    db_tags = models.ManyToManyField(Tag, null=True,
            help_text='tags on this object. Tags are simple string markers to identify, group and alias objects.')

    # Database manager
    objects = managers.TypedObjectManager()

    # quick on-object typeclass cache for speed
    _cached_typeclass = None

    # typeclass mechanism

    def __init__(self, *args, **kwargs):
        """
        The `__init__` method of typeclasses is the core operational
        code of the typeclass system, where it dynamically re-applies
        a class based on the db_typeclass_path database field rather
        than use the one in the model.

        Args:
            Passed through to parent.

        Kwargs:
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
        super(TypedObject, self).__init__(*args, **kwargs)
        if typeclass_path:
            try:
                self.__class__ = class_from_module(typeclass_path, defaultpaths=settings.TYPECLASS_PATHS)
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
                        self.__class__ = self._meta.proxy_for_model or self.__class__
            finally:
                self.db_typclass_path = typeclass_path
        elif self.db_typeclass_path:
            try:
                self.__class__ = class_from_module(self.db_typeclass_path)
            except Exception:
                log_trace()
                try:
                    self.__class__ = class_from_module(self.__defaultclasspath__)
                except Exception:
                    log_trace()
                    self.__dbclass__ = self._meta.proxy_for_model or self.__class__
        else:
            self.db_typeclass_path = "%s.%s" % (self.__module__, self.__class__.__name__)
        # important to put this at the end since _meta is based on the set __class__
        self.__dbclass__ = self._meta.proxy_for_model or self.__class__

    # initialize all handlers in a lazy fashion
    @lazy_property
    def attributes(self):
        return AttributeHandler(self)

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
        return NAttributeHandler(self)


    class Meta:
        """
        Django setup info.
        """
        abstract = True
        verbose_name = "Evennia Database Object"
        ordering = ['-db_date_created', 'id', 'db_typeclass_path', 'db_key']

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

    #
    #
    # TypedObject main class methods and properties
    #
    #

    def __eq__(self, other):
        return other and hasattr(other, 'dbid') and self.dbid == other.dbid

    def __str__(self):
        return smart_str("%s" % self.db_key)

    def __unicode__(self):
        return u"%s" % self.db_key

    #@property
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

    #@property
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

    #
    # Object manipulation methods
    #

    def is_typeclass(self, typeclass, exact=True):
        """
        Returns true if this object has this type OR has a typeclass
        which is an subclass of the given typeclass. This operates on
        the actually loaded typeclass (this is important since a
        failing typeclass may instead have its default currently
        loaded) typeclass - can be a class object or the python path
        to such an object to match against.

        typeclass - a class or the full python path to the class
        exact - returns true only
                if the object's type is exactly this typeclass, ignoring
                parents.
        """
        if isinstance(typeclass, basestring):
            typeclass = [typeclass] + ["%s.%s" % (prefix, typeclass) for prefix in settings.TYPECLASS_PATHS]
        else:
            typeclass = [typeclass.path]

        selfpath = self.path
        if exact:
            # check only exact match
            return selfpath in typeclass
        else:
            # check parent chain
            return any(hasattr(cls, "path") and cls.path in typeclass for cls in self.__class__.mro())

    def swap_typeclass(self, new_typeclass, clean_attributes=False,
                       run_start_hooks=True, no_default=True):
        """
        This performs an in-situ swap of the typeclass. This means
        that in-game, this object will suddenly be something else.
        Player will not be affected. To 'move' a player to a different
        object entirely (while retaining this object's type), use
        self.player.swap_object().

        Note that this might be an error prone operation if the
        old/new typeclass was heavily customized - your code
        might expect one and not the other, so be careful to
        bug test your code if using this feature! Often its easiest
        to create a new object and just swap the player over to
        that one instead.

        Arguments:
        new_typeclass (path/classobj) - type to switch to
        clean_attributes (bool/list) - will delete all attributes
                           stored on this object (but not any
                           of the database fields such as name or
                           location). You can't get attributes back,
                           but this is often the safest bet to make
                           sure nothing in the new typeclass clashes
                           with the old one. If you supply a list,
                           only those named attributes will be cleared.
        run_start_hooks - trigger the start hooks of the object, as if
                          it was created for the first time.
        no_default - if this is active, the swapper will not allow for
                     swapping to a default typeclass in case the given
                     one fails for some reason. Instead the old one
                     will be preserved.
        Returns:
          boolean True/False depending on if the swap worked or not.

        """

        if not callable(new_typeclass):
            # this is an actual class object - build the path
            new_typeclass = class_from_module(new_typeclass, defaultpaths=settings.TYPECLASS_PATHS)

        # if we get to this point, the class is ok.


        if inherits_from(self, "evennia.scripts.models.ScriptDB"):
            if self.interval > 0:
                raise RuntimeError("Cannot use swap_typeclass on time-dependent " \
                                   "Script '%s'.\nStop and start a new Script of the " \
                                   "right type instead." % self.key)

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
                #print "deleting attrs ..."
                self.attributes.clear()
                self.nattributes.clear()

        if run_start_hooks:
            # fake this call to mimic the first save
            self.at_first_save()

    #
    # Lock / permission methods
    #

    def access(self, accessing_obj, access_type='read', default=False, **kwargs):
        """
        Determines if another object has permission to access.
        accessing_obj - object trying to access this one
        access_type - type of access sought
        default - what to return if no lock of access_type was found
        **kwargs - this is ignored, but is there to make the api consistent with the
                   object-typeclass method access, which use it to feed to its hook methods.
        """
        return self.locks.check(accessing_obj, access_type=access_type, default=default)

    def check_permstring(self, permstring):
        """
        This explicitly checks if we hold particular permission without
        involving any locks. It does -not- trigger the at_access hook.
        """
        if hasattr(self, "player"):
            if self.player and self.player.is_superuser:
                return True
        else:
            if self.is_superuser:
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
            return any(True for hpos, hperm in enumerate(_PERMISSION_HIERARCHY)
                       if hperm in perms and hpos > ppos)
        return False

    #
    # Deletion methods
    #

    def _deleted(self, *args, **kwargs):
        "Scrambling method for already deleted objects"
        raise ObjectDoesNotExist("This object was already deleted!")

    def delete(self):
        "Cleaning up handlers on the typeclass level"
        global TICKER_HANDLER
        if not TICKER_HANDLER:
            from evennia.scripts.tickerhandler import TICKER_HANDLER
        TICKER_HANDLER.remove(self) # removes objects' all ticker subscriptions
        self.permissions.clear()
        self.attributes.clear()
        self.aliases.clear()
        if hasattr(self, "nicks"):
            self.nicks.clear()

        # scrambling properties
        self.delete = self._deleted
        super(TypedObject, self).delete()

    #
    # Memory management
    #

    def flush_from_cache(self):
        """
        Flush this object instance from cache, forcing an object reload.
        Note that this will kill all temporary attributes on this object
         since it will be recreated as a new Typeclass instance.
        """
        self.__class__.flush_cached_instance(self)

    #
    # Attribute storage
    #

    #@property db
    def __db_get(self):
        """
        Attribute handler wrapper. Allows for the syntax
           obj.db.attrname = value
             and
           value = obj.db.attrname
             and
           del obj.db.attrname
             and
           all_attr = obj.db.all() (unless there is an attribute
                      named 'all', in which case that will be returned instead).
        """
        try:
            return self._db_holder
        except AttributeError:
            self._db_holder = DbHolder(self, 'attributes')
            return self._db_holder

    #@db.setter
    def __db_set(self, value):
        "Stop accidentally replacing the db object"
        string = "Cannot assign directly to db object! "
        string += "Use db.attr=value instead."
        raise Exception(string)

    #@db.deleter
    def __db_del(self):
        "Stop accidental deletion."
        raise Exception("Cannot delete the db object!")
    db = property(__db_get, __db_set, __db_del)

    #
    # Non-persistent (ndb) storage
    #

    #@property ndb
    def __ndb_get(self):
        """
        A non-attr_obj store (ndb: NonDataBase). Everything stored
        to this is guaranteed to be cleared when a server is shutdown.
        Syntax is same as for the _get_db_holder() method and
        property, e.g. obj.ndb.attr = value etc.
        """
        try:
            return self._ndb_holder
        except AttributeError:
            self._ndb_holder = DbHolder(self, "nattrhandler", manager_name='nattributes')
            return self._ndb_holder

    #@db.setter
    def __ndb_set(self, value):
        "Stop accidentally replacing the ndb object"
        string = "Cannot assign directly to ndb object! "
        string += "Use ndb.attr=value instead."
        raise Exception(string)

    #@db.deleter
    def __ndb_del(self):
        "Stop accidental deletion."
        raise Exception("Cannot delete the ndb object!")
    ndb = property(__ndb_get, __ndb_set, __ndb_del)

