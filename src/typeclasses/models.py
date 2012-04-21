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

import sys
try:
    import cPickle as pickle
except ImportError:
    import pickle
import traceback
from django.db import models
from django.conf import settings
from django.utils.encoding import smart_str
from django.contrib.contenttypes.models import ContentType
from src.utils.idmapper.models import SharedMemoryModel
from src.server.models import ServerConfig
from src.typeclasses import managers
from src.locks.lockhandler import LockHandler
from src.utils import logger, utils
from src.utils.utils import make_iter, is_iter, to_unicode, to_str

__all__ = ("Attribute", "TypeNick", "TypedObject")

_PERMISSION_HIERARCHY = [p.lower() for p in settings.PERMISSION_HIERARCHY]

_CTYPEGET = ContentType.objects.get
_GA = object.__getattribute__
_SA = object.__setattr__
_DA = object.__delattr__
_PLOADS = pickle.loads
_PDUMPS = pickle.dumps

# Property Cache mechanism.

def _get_cache(obj, name):
    "On-model Cache handler."
    try:
        return _GA(obj, "_cached_db_%s" % name)
    except AttributeError:
        val = _GA(obj, "db_%s" % name)
        if val: _SA(obj, "_cached_db_%s" % name, val)
        return val
def _set_cache(obj, name, val):
    "On-model Cache setter"
    _SA(obj, "db_%s" % name, val)
    _GA(obj, "save")()
    _SA(obj, "_cached_db_%s" % name, val)

def _del_cache(obj, name):
    "On-model cache deleter"
    try:
        _DA(obj, "_cached_db_%s" % name)
    except AttributeError:
        pass

#------------------------------------------------------------
#
#   Attributes
#
#------------------------------------------------------------

class PackedDBobject(object):
    """
    Attribute helper class.
    A container for storing and easily identifying database objects in
    the database (which doesn't suppport storing db_objects directly).
    """
    def __init__(self, ID, db_model, db_key):
        self.id = ID
        self.db_model = db_model
        self.key = db_key
    def __str__(self):
        return "%s(#%s)" % (self.key, self.id)
    def __unicode__(self):
        return u"%s(#%s)" % (self.key, self.id)

class PackedDict(dict):
    """
    Attribute helper class.
    A variant of dict that stores itself to the database when
    updating one of its keys. This is called and handled by
    Attribute.validate_data().
    """
    def __init__(self, db_obj, *args, **kwargs):
        """
        Sets up the packing dict. The db_store variable
        is set by Attribute.validate_data() when returned in
        order to allow custom updates to the dict.

         db_obj - the Attribute object storing this dict.

         The 'parent' property is set to 'init' at creation,
         this stops the system from saving itself over and over
         when first assigning the dict. Once initialization
         is over, the Attribute from_attr() method will assign
         the parent (or None, if at the root)

        """
        self.db_obj = db_obj
        self.parent = 'init'
        super(PackedDict, self).__init__(*args, **kwargs)
    def __str__(self):
        return "{%s}" % ", ".join("%s:%s" % (key, str(val)) for key, val in self.items())
    def save(self):
        "Relay save operation upwards in tree until we hit the root."
        if self.parent == 'init':
            pass
        elif self.parent:
            self.parent.save()
        else:
            self.db_obj.value = self
    def __setitem__(self, *args, **kwargs):
        "assign item to this dict"
        super(PackedDict, self).__setitem__(*args, **kwargs)
        self.save()
    def clear(self, *args, **kwargs):
        "Custom clear"
        super(PackedDict, self).clear(*args, **kwargs)
        self.save()
    def pop(self, *args, **kwargs):
        "Custom pop"
        super(PackedDict, self).pop(*args, **kwargs)
        self.save()
    def popitem(self, *args, **kwargs):
        "Custom popitem"
        super(PackedDict, self).popitem(*args, **kwargs)
        self.save()
    def update(self, *args, **kwargs):
        "Custom update"
        super(PackedDict, self).update(*args, **kwargs)
        self.save()

class PackedList(list):
    """
    Attribute helper class.
    A variant of list that stores itself to the database when
    updating one of its keys. This is called and handled by
    Attribute.validate_data().
    """
    def __init__(self, db_obj, *args, **kwargs):
        """
        Sets up the packing list.
         db_obj - the Attribute object storing this dict.

         The 'parent' property is set to 'init' at creation,
         this stops the system from saving itself over and over
         when first assigning the dict. Once initialization
         is over, the Attribute from_attr() method will assign
         the parent (or None, if at the root)

        """
        self.db_obj = db_obj
        self.parent = 'init'
        super(PackedList, self).__init__(*args, **kwargs)
    def __str__(self):
        return "[%s]" % ", ".join(str(val) for val in self)
    def save(self):
        "Relay save operation upwards in tree until we hit the root."
        if self.parent == 'init':
            pass
        elif self.parent:
            self.parent.save()
        else:
            self.db_obj.value = self
    def __setitem__(self, *args, **kwargs):
        "Custom setitem that stores changed list to database."
        super(PackedList, self).__setitem__(*args, **kwargs)
        self.save()
    def append(self, *args, **kwargs):
        "Custom append"
        super(PackedList, self).append(*args, **kwargs)
        self.save()
    def extend(self, *args, **kwargs):
        "Custom extend"
        super(PackedList, self).extend(*args, **kwargs)
        self.save()
    def insert(self, *args, **kwargs):
        "Custom insert"
        super(PackedList, self).insert(*args, **kwargs)
        self.save()
    def remove(self, *args, **kwargs):
        "Custom remove"
        super(PackedList, self).remove(*args, **kwargs)
        self.save()
    def pop(self, *args, **kwargs):
        "Custom pop"
        super(PackedList, self).pop(*args, **kwargs)
        self.save()
    def reverse(self, *args, **kwargs):
        "Custom reverse"
        super(PackedList, self).reverse(*args, **kwargs)
        self.save()
    def sort(self, *args, **kwargs):
        "Custom sort"
        super(PackedList, self).sort(*args, **kwargs)
        self.save()

class Attribute(SharedMemoryModel):
    """
    Abstract django model.

    Attributes are things that are specific to different types of objects. For
    example, a drink container needs to store its fill level, whereas an exit
    needs to store its open/closed/locked/unlocked state. These are done via
    attributes, rather than making different classes for each object type and
    storing them directly. The added benefit is that we can add/remove
    attributes on the fly as we like.

    The Attribute class defines the following properties:
      key - primary identifier
      mode - which type of data is stored in attribute
      permissions - perm strings
      obj - which object the attribute is defined on
      date_created - when the attribute was created
      value - the data stored in the attribute
         what is actually stored in the field is a dict

           {type : nodb|dbobj|dbiter,
            data : <data>}

         where type is info for the loader, telling it if holds a single
         dbobject (dbobj), have to do a full scan for dbrefs (dbiter) or
         if it is a normal Python structure without any dbobjs inside it
         and can thus return it without further action (nodb).
    """

    #
    # Attribute Database Model setup
    #
    #
    # These databse fields are all set using their corresponding properties,
    # named same as the field, but withtout the db_* prefix.

    db_key = models.CharField('key', max_length=255, db_index=True)
    # access through the value property
    db_value = models.TextField('value', blank=True, null=True)
    # Lock storage
    db_lock_storage = models.CharField('locks', max_length=512, blank=True)
    # references the object the attribute is linked to (this is set
    # by each child class to this abstact class)
    db_obj =  None # models.ForeignKey("RefencedObject")
    # time stamp
    db_date_created = models.DateTimeField('date_created', editable=False, auto_now_add=True)

    # Database manager
    objects = managers.AttributeManager()

    # Lock handler self.locks
    def __init__(self, *args, **kwargs):
        "Initializes the parent first -important!"
        SharedMemoryModel.__init__(self, *args, **kwargs)
        self.locks = LockHandler(self)
        self.no_cache = True
        self.cached_value = None

    class Meta:
        "Define Django meta options"
        abstract = True
        verbose_name = "Evennia Attribute"

    # Wrapper properties to easily set database fields. These are
    # @property decorators that allows to access these fields using
    # normal python operations (without having to remember to save()
    # etc). So e.g. a property 'attr' has a get/set/del decorator
    # defined that allows the user to do self.attr = value,
    # value = self.attr and del self.attr respectively (where self
    # is the object in question).

    # key property (wraps db_key)
    #@property
    def __key_get(self):
        "Getter. Allows for value = self.key"
        return _get_cache(self, "key")
    #@key.setter
    def __key_set(self, value):
        "Setter. Allows for self.key = value"
        _set_cache(self, "key", value)
    #@key.deleter
    def __key_del(self):
        "Deleter. Allows for del self.key"
        raise Exception("Cannot delete attribute key!")
    key = property(__key_get, __key_set, __key_del)

    # obj property (wraps db_obj)
    #@property
    def __obj_get(self):
        "Getter. Allows for value = self.obj"
        return _get_cache(self, "obj")
    #@obj.setter
    def __obj_set(self, value):
        "Setter. Allows for self.obj = value"
        _set_cache(self, "obj", value)
    #@obj.deleter
    def __obj_del(self):
        "Deleter. Allows for del self.obj"
        self.db_obj = None
        self.save()
        _del_cache(self, "obj")
    obj = property(__obj_get, __obj_set, __obj_del)

    # date_created property (wraps db_date_created)
    #@property
    def __date_created_get(self):
        "Getter. Allows for value = self.date_created"
        return _get_cache(self, "date_created")
    #@date_created.setter
    def __date_created_set(self, value):
        "Setter. Allows for self.date_created = value"
        raise Exception("Cannot edit date_created!")
    #@date_created.deleter
    def __date_created_del(self):
        "Deleter. Allows for del self.date_created"
        raise Exception("Cannot delete date_created!")
    date_created = property(__date_created_get, __date_created_set, __date_created_del)

    # value property (wraps db_value)
    #@property
    def __value_get(self):
        """
        Getter. Allows for value = self.value. Reads from cache if possible.
        """
        if self.no_cache:
            # re-create data from database and cache it
            try:
                value = self.__from_attr(_PLOADS(to_str(self.db_value)))
            except pickle.UnpicklingError:
                value = self.db_value
            self.cached_value = value
            self.no_cache = False
            return value
        else:
            # normally the memory cache holds the latest data so no db access is needed.
            return self.cached_value

    #@value.setter
    def __value_set(self, new_value):
        """
        Setter. Allows for self.value = value. We make sure to cache everything.
        """
        new_value = self.__to_attr(new_value)
        self.cached_value = self.__from_attr(new_value)
        self.no_cache = False
        self.db_value = to_unicode(_PDUMPS(to_str(new_value)))
        self.save()
    #@value.deleter
    def __value_del(self):
        "Deleter. Allows for del attr.value. This removes the entire attribute."
        self.delete()
    value = property(__value_get, __value_set, __value_del)

    # lock_storage property (wraps db_lock_storage)
    #@property
    def __lock_storage_get(self):
        "Getter. Allows for value = self.lock_storage"
        return _get_cache(self, "lock_storage")
    #@lock_storage.setter
    def __lock_storage_set(self, value):
        """Saves the lock_storage. This is usually not called directly, but through self.lock()"""
        self.db_lock_storage = value
        self.save()
    #@lock_storage.deleter
    def __lock_storage_del(self):
        "Deleter is disabled. Use the lockhandler.delete (self.lock.delete) instead"""
        logger.log_errmsg("Lock_Storage (on %s) cannot be deleted. Use obj.lock.delete() instead." % self)
    lock_storage = property(__lock_storage_get, __lock_storage_set, __lock_storage_del)


    #
    #
    # Attribute methods
    #
    #

    def __str__(self):
        return smart_str("%s(%s)" % (self.key, self.id))

    def __unicode__(self):
        return u"%s(%s)" % (self.key, self.id)

    # operators on various data

    def __to_attr(self, data):
        """
        Convert data to proper attr data format before saving

        We have to make sure to not store database objects raw, since
        this will crash the system. Instead we must store their IDs
        and make sure to convert back when the attribute is read back
        later.

        Due to this it's criticial that we check all iterables
        recursively, converting all found database objects to a form
        the database can handle. We handle lists, tuples and dicts
        (and any nested combination of them) this way, all other
        iterables are stored and returned as lists.

        data storage format:
           (simple|dbobj|iter, <data>)
        where
           simple - a single non-db object, like a string or number
           dbobj - a single dbobj
           iter - any iterable object - will be looped over recursively
                  to convert dbobj->id.

        """

        def iter_db2id(item):
            """
            recursively looping through stored iterables, replacing objects with ids.
            (Python only builds nested functions once, so there is no overhead for nesting)
            """
            dtype = type(item)
            if dtype in (basestring, int, float): # check the most common types first, for speed
                return item
            elif hasattr(item, "id") and hasattr(item, "_db_model_name") and hasattr(item, "db_key"):
                db_model_name = item._db_model_name # don't use _GA here, could be typeclass
                if db_model_name == "typeclass":
                    db_model_name = _GA(item.dbobj, "_db_model_name")
                return PackedDBobject(item.id, db_model_name, item.db_key)
            elif dtype == tuple:
                return tuple(iter_db2id(val) for val in item)
            elif dtype in (dict, PackedDict):
                return dict((key, iter_db2id(val)) for key, val in item.items())
            elif hasattr(item, '__iter__'):
                return list(iter_db2id(val) for val in item)
            else:
                return item

        dtype = type(data)

        if dtype in (basestring, int, float):
            return ("simple",data)
        elif hasattr(data, "id") and hasattr(data, "_db_model_name") and hasattr(data, 'db_key'):
            # all django models (objectdb,scriptdb,playerdb,channel,msg,typeclass)
            # have the protected property _db_model_name hardcoded on themselves for speed.
            db_model_name = data._db_model_name # don't use _GA here, could be typeclass
            if db_model_name == "typeclass":
                # typeclass cannot help us, we want the actual child object model name
                db_model_name = _GA(data.dbobj,"_db_model_name")
            return ("dbobj", PackedDBobject(data.id, db_model_name, data.db_key))
        elif hasattr(data, "__iter__"):
            return ("iter", iter_db2id(data))
        else:
            return ("simple", data)


    def __from_attr(self, datatuple):
        """
        Retrieve data from a previously stored attribute. This
        is always a dict with keys type and data.

        datatuple comes from the database storage and has
        the following format:
           (simple|dbobj|iter, <data>)
        where
            simple - a single non-db object, like a string. is returned as-is.
            dbobj - a single dbobj-id. This id is retrieved back from the database.
            iter - an iterable. This is traversed iteratively, converting all found
                   dbobj-ids back to objects. Also, all lists and dictionaries are
                   returned as their PackedList/PackedDict counterparts in order to
                   allow in-place assignment such as obj.db.mylist[3] = val. Mylist
                   is then a PackedList that saves the data on the fly.
        """
        # nested functions
        def id2db(data):
            """
            Convert db-stored dbref back to object
            """
            mclass = _CTYPEGET(model=data.db_model).model_class()
            try:
                return mclass.objects.dbref_search(data.id)

            except AttributeError:
                try:
                    return mclass.objects.get(id=data.id)
                except mclass.DoesNotExist: # could happen if object was deleted in the interim.
                    return None

        def iter_id2db(item, parent=None):
            """
            Recursively looping through stored iterables, replacing ids with actual objects.
            We return PackedDict and PackedLists instead of normal lists; this is needed in order for
            the user to do dynamic saving of nested in-place, such as obj.db.attrlist[2]=3. What is
            stored in the database are however always normal python primitives.
            """
            dtype = type(item)
            if dtype in (basestring, int, float): # check the most common types first, for speed
                return item
            elif dtype == PackedDBobject:
                return id2db(item)
            elif dtype == tuple:
                return tuple([iter_id2db(val) for val in item])
            elif dtype in (dict, PackedDict):
                pdict = PackedDict(self)
                pdict.update(dict(zip([key for key in item.keys()],
                                      [iter_id2db(val, pdict) for val in item.values()])))
                pdict.parent = parent
                return pdict
            elif hasattr(item, '__iter__'):
                plist = PackedList(self)
                plist.extend(list(iter_id2db(val, plist) for val in item))
                plist.parent = parent
                return plist
            else:
                return item

        typ, data = datatuple

        if typ == 'simple':
            # single non-db objects
            return data
        elif typ == 'dbobj':
            # a single stored dbobj
            return id2db(data)
        elif typ == 'iter':
            # all types of iterables
            return iter_id2db(data)

    def access(self, accessing_obj, access_type='read', default=False):
        """
        Determines if another object has permission to access.
        accessing_obj - object trying to access this one
        access_type - type of access sought
        default - what to return if no lock of access_type was found
        """
        return self.locks.check(accessing_obj, access_type=access_type, default=default)


#------------------------------------------------------------
#
# Nicks
#
#------------------------------------------------------------

class TypeNick(SharedMemoryModel):
    """
    This model holds whichever alternate names this object
    has for OTHER objects, but also for arbitrary strings,
    channels, players etc. Setting a nick does not affect
    the nicknamed object at all (as opposed to Aliases above),
    and only this object will be able to refer to the nicknamed
    object by the given nick.

    The default nick types used by Evennia are:
    inputline (default) - match against all input
    player - match against player searches
    obj - match against object searches
    channel - used to store own names for channels

    """
    db_nick = models.CharField('nickname',max_length=255, db_index=True, help_text='the alias')
    db_real = models.TextField('realname', help_text='the original string to match and replace.')
    db_type = models.CharField('nick type',default="inputline", max_length=16, null=True, blank=True,
       help_text="the nick type describes when the engine tries to do nick-replacement. Common options are 'inputline','player','obj' and 'channel'. Inputline checks everything being inserted, whereas the other cases tries to replace in various searches or when posting to channels.")
    db_obj = None #models.ForeignKey("ObjectDB")

    class Meta:
        "Define Django meta options"
        abstract = True
        verbose_name = "Nickname"
        unique_together = ("db_nick", "db_type", "db_obj")

class TypeNickHandler(object):
    """
    Handles nick access and setting. Accessed through ObjectDB.nicks
    """

    NickClass = TypeNick

    def __init__(self, obj):
        """
        This handler allows for accessing and setting nicks -
        on-the-fly replacements for various text input passing through
        this object (most often a Character)

        The default nick types used by Evennia are:

        inputline (default) - match against all input
        player - match against player searches
        obj - match against object searches
        channel - used to store own names for channels

        You can define other nicktypes by using the add() method of
        this handler and set nick_type to whatever you want. It's then
        up to you to somehow make use of this nick_type in your game
        (such as for a "recog" system).

        """
        self.obj = obj

    def add(self, nick, realname, nick_type="inputline"):
        """
        Assign a new nick for realname.
          nick_types used by Evennia are
            'inputline', 'player', 'obj' and 'channel'
        """
        if not nick or not nick.strip():
            return
        nick = nick.strip()
        real = realname.strip()
        query = self.NickClass.objects.filter(db_obj=self.obj, db_nick__iexact=nick, db_type__iexact=nick_type)
        if query.count():
            old_nick = query[0]
            old_nick.db_real = real
            old_nick.save()
        else:
            new_nick = self.NickClass(db_nick=nick, db_real=real, db_type=nick_type, db_obj=self.obj)
            new_nick.save()
    def delete(self, nick, nick_type="inputline"):
        "Removes a previously stored nick"
        nick = nick.strip()
        query = self.NickClass.objects.filter(db_obj=self.obj, db_nick__iexact=nick, db_type__iexact=nick_type)
        if query.count():
            # remove the found nick(s)
            query.delete()
    def get(self, nick=None, nick_type="inputline", obj=None):
        """
        Retrieves a given nick (with a specified nick_type) on an object. If no nick is given, returns a list
        of all nicks on the object, or the empty list.
        Defaults to searching the current object.
        """
        if not obj:
            # defaults to the current object
            obj = self.obj
        if nick:
            query = self.NickClass.objects.filter(db_obj=obj, db_nick__iexact=nick, db_type__iexact=nick_type)
            query = query.values_list("db_real", flat=True)
            if query.count():
                return query[0]
            else:
                return nick
        else:
            return self.NickClass.objects.filter(db_obj=obj)
    def has(self, nick, nick_type="inputline", obj=None):
        """
        Returns true/false if this nick and nick_type is defined on the given
        object or not. If no obj is given, default to the current object the
        handler is defined on.

        """
        if not obj:
            obj = self.obj
        return self.NickClass.objects.filter(db_obj=obj, db_nick__iexact=nick, db_type__iexact=nick_type).count()


#------------------------------------------------------------
#
# Typed Objects
#
#------------------------------------------------------------

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
    # These databse fields are all set using their corresponding properties,
    # named same as the field, but withtou the db_* prefix.

    # Main identifier of the object, for searching. Can also
    # be referenced as 'name'.
    db_key = models.CharField('key', max_length=255, db_index=True)
    # This is the python path to the type class this object is tied to
    # (the type class is what defines what kind of Object this is)
    db_typeclass_path = models.CharField('typeclass', max_length=255, null=True, help_text="this defines what 'type' of entity this is. This variable holds a Python path to a module with a valid Evennia Typeclass.")
    # Creation date
    db_date_created = models.DateTimeField('creation date', editable=False, auto_now_add=True)
    # Permissions (access these through the 'permissions' property)
    db_permissions = models.CharField('permissions', max_length=255, blank=True, help_text="a comma-separated list of text strings checked by certain locks. They are often used for hierarchies, such as letting a Player have permission 'Wizards', 'Builders' etc. Character objects use 'Players' by default. Most other objects don't have any permissions.")
    # Lock storage
    db_lock_storage = models.CharField('locks', max_length=512, blank=True, help_text="locks limit access to an entity. A lock is defined as a 'lock string' on the form 'type:lockfunctions', defining what functionality is locked and how to determine access. Not defining a lock means no access is granted.")

    # Database manager
    objects = managers.TypedObjectManager()

    # object cache and flags
    _cached_typeclass = None

    # lock handler self.locks
    def __init__(self, *args, **kwargs):
        "We must initialize the parent first - important!"
        SharedMemoryModel.__init__(self, *args, **kwargs)
        self.locks = LockHandler(self)

    class Meta:
        """
        Django setup info.
        """
        abstract = True
        verbose_name = "Evennia Database Object"
        ordering = ['-db_date_created', 'id', 'db_typeclass_path', 'db_key']

    # Wrapper properties to easily set database fields. These are
    # @property decorators that allows to access these fields using
    # normal python operations (without having to remember to save()
    # etc). So e.g. a property 'attr' has a get/set/del decorator
    # defined that allows the user to do self.attr = value,
    # value = self.attr and del self.attr respectively (where self
    # is the object in question).

    # key property (wraps db_key)
    #@property
    def __key_get(self):
        "Getter. Allows for value = self.key"
        return _get_cache(self, "key")
    #@key.setter
    def __key_set(self, value):
        "Setter. Allows for self.key = value"
        _set_cache(self, "key", value)
    #@key.deleter
    def __key_del(self):
        "Deleter. Allows for del self.key"
        raise Exception("Cannot delete objectdb key!")
    key = property(__key_get, __key_set, __key_del)

    # name property (wraps db_key too - alias to self.key)
    #@property
    def __name_get(self):
        "Getter. Allows for value = self.name"
        return _get_cache(self, "key")
    #@name.setter
    def __name_set(self, value):
        "Setter. Allows for self.name = value"
        _set_cache(self, "key", value)
    #@name.deleter
    def __name_del(self):
        "Deleter. Allows for del self.name"
        raise Exception("Cannot delete name!")
    name = property(__name_get, __name_set, __name_del)

    # typeclass_path property
    #@property
    def __typeclass_path_get(self):
        "Getter. Allows for value = self.typeclass_path"
        return _get_cache(self, "typeclass_path")
    #@typeclass_path.setter
    def __typeclass_path_set(self, value):
        "Setter. Allows for self.typeclass_path = value"
        _set_cache(self, "typeclass_path", value)
    #@typeclass_path.deleter
    def __typeclass_path_del(self):
        "Deleter. Allows for del self.typeclass_path"
        self.db_typeclass_path = ""
        self.save()
        _del_cache(self, "typeclass_path")
    typeclass_path = property(__typeclass_path_get, __typeclass_path_set, __typeclass_path_del)

    # date_created property
    #@property
    def __date_created_get(self):
        "Getter. Allows for value = self.date_created"
        return _get_cache(self, "date_created")
    #@date_created.setter
    def __date_created_set(self, value):
        "Setter. Allows for self.date_created = value"
        raise Exception("Cannot change date_created!")
    #@date_created.deleter
    def __date_created_del(self):
        "Deleter. Allows for del self.date_created"
        raise Exception("Cannot delete date_created!")
    date_created = property(__date_created_get, __date_created_set, __date_created_del)

    # permissions property
    #@property
    def __permissions_get(self):
        "Getter. Allows for value = self.name. Returns a list of permissions."
        perms = _get_cache(self, "permissions")
        if perms:
            return [perm.strip() for perm in perms.split(',')]
        return []
    #@permissions.setter
    def __permissions_set(self, value):
        "Setter. Allows for self.name = value. Stores as a comma-separated string."
        value = ",".join([utils.to_unicode(val).strip() for val in make_iter(value)])
        _set_cache(self, "permissions", value)
    #@permissions.deleter
    def __permissions_del(self):
        "Deleter. Allows for del self.name"
        self.db_permissions = ""
        self.save()
        _del_cache(self, "permissions")
    permissions = property(__permissions_get, __permissions_set, __permissions_del)

    # lock_storage property (wraps db_lock_storage)
    #@property
    def __lock_storage_get(self):
        "Getter. Allows for value = self.lock_storage"
        return _get_cache(self, "lock_storage")
    #@lock_storage.setter
    def __lock_storage_set(self, value):
        """Saves the lock_storagetodate. This is usually not called directly, but through self.lock()"""
        _set_cache(self, "lock_storage", value)
    #@lock_storage.deleter
    def __lock_storage_del(self):
        "Deleter is disabled. Use the lockhandler.delete (self.lock.delete) instead"""
        logger.log_errmsg("Lock_Storage (on %s) cannot be deleted. Use obj.lock.delete() instead." % self)
    lock_storage = property(__lock_storage_get, __lock_storage_set, __lock_storage_del)



    #
    #
    # TypedObject main class methods and properties
    #
    #

    # these are identifiers for fast Attribute access and caching
    _typeclass_paths = settings.OBJECT_TYPECLASS_PATHS
    _attribute_class = Attribute # replaced by relevant attribute class for child
    _db_model_name = "typeclass" # used by attributes to safely store objects

    def __eq__(self, other):
        return other and hasattr(other, 'id') and self.id == other.id

    def __str__(self):
        return smart_str("%s" % self.key)

    def __unicode__(self):
        return u"%s" % self.key

    def __getattribute__(self, propname):
        """
        Will predominantly look for an attribute
        on this object, but if not found we will
        check if it might exist on the typeclass instead. Since
        the typeclass refers back to the databaseobject as well, we
        have to be very careful to avoid loops.
        """
        try:
            return _GA(self, propname)
        except AttributeError:
            # check if the attribute exists on the typeclass instead
            # (we make sure to not incur a loop by not triggering the
            # typeclass' __getattribute__, since that one would
            # try to look back to this very database object.)
            typeclass = _GA(self, 'typeclass')
            if typeclass:
                return _GA(typeclass, propname)
            else:
                raise AttributeError

    #@property
    def __dbref_get(self):
        """
        Returns the object's dbref id on the form #NN.
        Alternetively, use obj.id directly to get dbref
        without any #.
        """
        return "#%s" % str(_GA(self, "id"))
    dbref = property(__dbref_get)

    # typeclass property
    #@property
    def __typeclass_get(self):
        """
        Getter. Allows for value = self.typeclass.
        The typeclass is a class object found at self.typeclass_path;
        it allows for extending the Typed object for all different
        types of objects that the game needs. This property
        handles loading and initialization of the typeclass on the fly.

        Note: The liberal use of _GA and __setattr__ (instead
              of normal dot notation) is due to optimization: it avoids calling
              the custom self.__getattribute__ more than necessary.
        """

        path = _GA(self, "typeclass_path")
        typeclass = _GA(self, "_cached_typeclass")
        try:
            if typeclass and _GA(typeclass, "path") == path:
                # don't call at_init() when returning from cache
                return typeclass
        except AttributeError:
            pass

        errstring = ""
        if not path:
            # this means we should get the default obj without giving errors.
            return _GA(self, "_get_default_typeclass")(cache=True, silent=True, save=True)
        else:
            # handle loading/importing of typeclasses, searching all paths.
            # (self._typeclass_paths is a shortcut to settings.TYPECLASS_*_PATHS
            # where '*' is either OBJECT, SCRIPT or PLAYER depending on the typed
            # entities).
            typeclass_paths = [path] + ["%s.%s" % (prefix, path) for prefix in _GA(self, '_typeclass_paths')]

            for tpath in typeclass_paths:

                # try to import and analyze the result
                typeclass = _GA(self, "_path_import")(tpath)
                if callable(typeclass):
                    # we succeeded to import. Cache and return.
                    _SA(self, 'db_typeclass_path', tpath)
                    _GA(self, 'save')()
                    _SA(self, "_cached_db_typeclass_path", tpath)
                    typeclass = typeclass(self)
                    _SA(self, "_cached_typeclass", typeclass)
                    try:
                        typeclass.at_init()
                    except Exception:
                        logger.log_trace()
                    return typeclass
                elif hasattr(typeclass, '__file__'):
                    errstring += "\n%s seems to be just the path to a module. You need" % tpath
                    errstring +=  " to specify the actual typeclass name inside the module too."
                else:
                    errstring += "\n%s" % typeclass # this will hold a growing error message.
        # If we reach this point we couldn't import any typeclasses. Return default. It's up to the calling
        # method to use e.g. self.is_typeclass() to detect that the result is not the one asked for.
        _GA(self, "_display_errmsg")(errstring)
        _SA(self, "typeclass_lasterrmsg", errstring)
        return _GA(self, "_get_default_typeclass")(cache=False, silent=False, save=False)

    #@typeclass.deleter
    def __typeclass_del(self):
        "Deleter. Disallow 'del self.typeclass'"
        raise Exception("The typeclass property should never be deleted, only changed in-place!")

    # typeclass property
    typeclass = property(__typeclass_get, fdel=__typeclass_del)

    # the last error string will be stored here for accessing methods to access.
    # It is set by _display_errmsg, which will print to log if error happens
    # during server startup.
    typeclass_last_errmsg = ""

    def _path_import(self, path):
        """
        Import a class from a python path of the
        form src.objects.object.Object
        """
        errstring = ""
        if not path:
            # this needs not be bad, it just means
            # we should use defaults.
            return None
        try:
            modpath, class_name = path.rsplit('.', 1)
            module =  __import__(modpath, fromlist=["none"])
            return module.__dict__[class_name]
        except ImportError:
            trc = sys.exc_traceback
            if not trc.tb_next:
                # we separate between not finding the module, and finding a buggy one.
                errstring = "Typeclass not found trying path '%s'." % path
            else:
                # a bug in the module is reported normally.
                trc = traceback.format_exc()
                errstring = "\n%sError importing '%s'." % (trc, path)
        except (ValueError, TypeError):
            errstring = "Malformed typeclass path '%s'." % path
        except KeyError:
            errstring = "No class '%s' was found in module '%s'."
            errstring = errstring % (class_name, modpath)
        except Exception:
            trc = traceback.format_exc()
            errstring = "\n%sException importing '%s'." % (trc, path)
        # return the error.
        return errstring

    def _display_errmsg(self, message):
        """
        Helper function to display error.
        """
        if ServerConfig.objects.conf("server_starting_mode"):
            print message.strip()
        else:
            _SA(self, "typeclass_last_errmsg", message.strip())
        return

        #infochan = None
        #cmessage = message
        #try:
        #    from src.comms.models import Channel
        #    infochan = settings.CHANNEL_MUDINFO
        #    infochan = Channel.objects.get_channel(infochan[0])
        #    if infochan:
        #        cname = infochan.key
        #        cmessage = "\n".join(["[%s]: %s" % (cname, line) for line in message.split('\n') if line])
        #        cmessage = cmessage.strip()
        #        infochan.msg(cmessage)
        #    else:
        #        # no mudinfo channel is found. Log instead.
        #        cmessage = "\n".join(["[NO MUDINFO CHANNEL]: %s" % line for line in message.split('\n')])
        #    logger.log_errmsg(cmessage)
        #except Exception:
        #    if ServerConfig.objects.conf("server_starting_mode"):
        #        print cmessage
        #    else:
        #        logger.log_trace(cmessage)

    def _get_default_typeclass(self, cache=False, silent=False, save=False):
        """
        This is called when a typeclass fails to
        load for whatever reason.
        Overload this in different entities.

        Default operation is to load a default typeclass.
        """
        defpath = _GA(self, "_default_typeclass_path")
        typeclass = _GA(self, "_path_import")(defpath)
        # if not silent:
        #     #errstring = "\n\nUsing Default class '%s'." % defpath
        #     _GA(self, "_display_errmsg")(errstring)

        if not callable(typeclass):
            # if typeclass still doesn't exist at this point, we're in trouble.
            # fall back to hardcoded core class which is wrong for e.g. scripts/players etc.
            failpath = defpath
            defpath = "src.objects.objects.Object"
            typeclass = _GA(self, "_path_import")(defpath)
            if not silent:
                #errstring = "  %s\n%s" % (typeclass, errstring)
                errstring = "  Default class '%s' failed to load." % failpath
                errstring += "\n  Using Evennia's default class '%s'." % defpath
                _GA(self, "_display_errmsg")(errstring)
        if not callable(typeclass):
            # if this is still giving an error, Evennia is wrongly configured or buggy
            raise Exception("CRITICAL ERROR: The final fallback typeclass %s cannot load!!" % defpath)
        typeclass = typeclass(self)
        if save:
            _SA(self, 'db_typeclass_path', defpath)
            _GA(self, 'save')()
        if cache:
            _SA(self, "_cached_db_typeclass_path", defpath)

            _SA(self, "_cached_typeclass", typeclass)
        try:
            typeclass.at_init()
        except Exception:
            logger.log_trace()
        return typeclass

    def is_typeclass(self, typeclass, exact=False):
        """
        Returns true if this object has this type
          OR has a typeclass which is an subclass of
          the given typeclass. This operates on the actually
          loaded typeclass (this is important since a failing
          typeclass may instead have its default currently loaded)

        typeclass - can be a class object or the
                python path to such an object to match against.

        exact - returns true only if the object's
               type is exactly this typeclass, ignoring
               parents.
        """
        try:
            typeclass = _GA(typeclass, "path")
        except AttributeError:
            pass
        typeclasses = [typeclass] + ["%s.%s" % (path, typeclass) for path in _GA(self, "_typeclass_paths")]
        if exact:
            current_path = _GA(self.typeclass, "path") #"_GA(self, "_cached_db_typeclass_path")
            return typeclass and any((current_path == typec for typec in typeclasses))
        else:
            # check parent chain
            return any((cls for cls in self.typeclass.__class__.mro()
                        if any(("%s.%s" % (_GA(cls,"__module__"), _GA(cls,"__name__")) == typec for typec in typeclasses))))

    #
    # Object manipulation methods
    #
    #

    def swap_typeclass(self, new_typeclass, clean_attributes=False, no_default=True):
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
        no_default - if this is active, the swapper will not allow for
                     swapping to a default typeclass in case the given
                     one fails for some reason. Instead the old one
                     will be preserved.
        Returns:
          boolean True/False depending on if the swap worked or not.

        """
        if callable(new_typeclass):
            # this is an actual class object - build the path
            cls = new_typeclass.__class__
            new_typeclass = "%s.%s" % (cls.__module__, cls.__name__)

        # Try to set the new path
        # this will automatically save to database

        old_typeclass_path = self.typeclass_path
        self.typeclass_path = new_typeclass.strip()
        # this will automatically use a default class if
        # there is an error with the given typeclass.
        new_typeclass = self.typeclass
        if self.typeclass_path == new_typeclass.path:
            # the typeclass loading worked as expected
            _DA(self, "_cached_db_typeclass_path")
            _SA(self, "_cached_typeclass", None)
        elif no_default:
            # something went wrong; the default was loaded instead,
            # and we don't allow that; instead we return to previous.
            _SA(self, "typeclass_path", old_typeclass_path)
            _SA(self, "_cached_typeclass", None)
            return False

        if clean_attributes:
            # Clean out old attributes
            if is_iter(clean_attributes):
                for attr in clean_attributes:
                    self.attr(attr, delete=True)
                for nattr in clean_attributes:
                    if hasattr(self.ndb, nattr):
                        self.nattr(nattr, delete=True)
            else:
                #print "deleting attrs ..."
                for attr in self.get_all_attributes():
                    attr.delete()
                for nattr in self.ndb.all:
                    del nattr

        # run hooks for this new typeclass
        new_typeclass.basetype_setup()
        new_typeclass.at_object_creation()
        return True

    #
    # Attribute handler methods
    #

    #
    # Fully persistent attributes. You usually access these
    # through the obj.db.attrname method.

    # Helper methods for persistent attributes

    def has_attribute(self, attribute_name):
        """
        See if we have an attribute set on the object.

        attribute_name: (str) The attribute's name.
        """
        return _GA(self, "_attribute_class").objects.filter(db_obj=self).filter(
            db_key__iexact=attribute_name).count()

    def set_attribute(self, attribute_name, new_value=None):
        """
        Sets an attribute on an object. Creates the attribute if need
        be.

        attribute_name: (str) The attribute's name.
        new_value: (python obj) The value to set the attribute to. If this is not
                                a str, the object will be stored as a pickle.
        """
        attrib_obj = None
        attrclass = _GA(self, "_attribute_class")
        try:
            # use old attribute
            attrib_obj = attrclass.objects.filter(
                db_obj=self).filter(db_key__iexact=attribute_name)[0]
        except IndexError:
            # no match; create new attribute
            attrib_obj = attrclass(db_key=attribute_name, db_obj=self)
        # re-set an old attribute value
        attrib_obj.value = new_value

    def get_attribute(self, attribute_name, default=None):
        """
        Returns the value of an attribute on an object. You may need to
        type cast the returned value from this function since the attribute
        can be of any type. Returns default if no match is found.

        attribute_name: (str) The attribute's name.
        default: What to return if no attribute is found
        """
        attrib_obj = default
        try:
            attrib_obj = _GA(self, "_attribute_class").objects.filter(
                db_obj=self).filter(db_key__iexact=attribute_name)[0]
        except IndexError:
            return default
        return attrib_obj.value

    def get_attribute_raise(self, attribute_name):
        """
        Returns value of an attribute. Raises AttributeError
        if no match is found.

        attribute_name: (str) The attribute's name.
        """
        try:
            return _GA(self, "_attribute_class").objects.filter(
                db_obj=self).filter(db_key__iexact=attribute_name)[0].value
        except IndexError:
            raise AttributeError

    def del_attribute(self, attribute_name):
        """
        Removes an attribute entirely.

        attribute_name: (str) The attribute's name.
        """
        try:
            _GA(self, "_attribute_class").objects.filter(
                db_obj=self).filter(db_key__iexact=attribute_name)[0].delete()
        except IndexError:
            pass

    def del_attribute_raise(self, attribute_name):
        """
        Removes and attribute. Raises AttributeError if
        attribute is not found.

        attribute_name: (str) The attribute's name.
        """
        try:
            _GA(self, "_attribute_class").objects.filter(
                db_obj=self).filter(db_key__iexact=attribute_name)[0].delete()
        except IndexError:
            raise AttributeError

    def get_all_attributes(self):
        """
        Returns all attributes defined on the object.
        """
        return list(_GA(self,"_attribute_class").objects.filter(db_obj=self))

    def attr(self, attribute_name=None, value=None, delete=False):
        """
        This is a convenient wrapper for
        get_attribute, set_attribute, del_attribute
        and get_all_attributes.
        If value is None, attr will act like
        a getter, otherwise as a setter.
        set delete=True to delete the named attribute.

        Note that you cannot set the attribute
        value to None using this method. Use set_attribute.
        """
        if attribute_name == None:
            # act as a list method
            return self.get_all_attributes()
        elif delete == True:
            self.del_attribute(attribute_name)
        elif value == None:
            # act as a getter.
            return self.get_attribute(attribute_name)
        else:
            # act as a setter
            self.set_attribute(attribute_name, value)

    #@property
    def __db_get(self):
        """
        A second convenience wrapper for the the attribute methods. It
        allows for the syntax
           obj.db.attrname = value
             and
           value = obj.db.attrname
             and
           del obj.db.attrname
             and
           all_attr = obj.db.all() (if there is no attribute named 'all', in which
                                    case that will be returned instead).
        """
        try:
            return self._db_holder
        except AttributeError:
            class DbHolder(object):
                "Holder for allowing property access of attributes"
                def __init__(self, obj):
                    _SA(self, 'obj', obj)
                def __getattribute__(self, attrname):
                    if attrname == 'all':
                        # we allow for overwriting the all() method
                        # with an attribute named 'all'.
                        attr = _GA(self, 'obj').get_attribute("all")
                        if attr:
                            return attr
                        return _GA(self, 'all')
                    return _GA(self, 'obj').get_attribute(attrname)
                def __setattr__(self, attrname, value):
                    _GA(self, 'obj').set_attribute(attrname, value)
                def __delattr__(self, attrname):
                    _GA(self, 'obj').del_attribute(attrname)
                def get_all(self):
                    return _GA(self, 'obj').get_all_attributes()
                all = property(get_all)
            self._db_holder = DbHolder(self)
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
    # NON-PERSISTENT storage methods
    #

    def nattr(self, attribute_name=None, value=None, delete=False):
        """
        This is the equivalence of self.attr but for non-persistent
        stores.
        """
        if attribute_name == None:
            # act as a list method
            if callable(self.ndb.all):
                return self.ndb.all()
            else:
                return [val for val in self.ndb.__dict__.keys()
                        if not val.startswith['_']]
        elif delete == True:
            if hasattr(self.ndb, attribute_name):
                _DA(self.db, attribute_name)
        elif value == None:
            # act as a getter.
            if hasattr(self.ndb, attribute_name):
                _GA(self.ndb, attribute_name)
            else:
                return None
        else:
            # act as a setter
            _SA(self.db, attribute_name, value)

    #@property
    def __ndb_get(self):
        """
        A non-persistent store (ndb: NonDataBase). Everything stored
        to this is guaranteed to be cleared when a server is shutdown.
        Syntax is same as for the _get_db_holder() method and
        property, e.g. obj.ndb.attr = value etc.
        """
        try:
            return self._ndb_holder
        except AttributeError:
            class NdbHolder(object):
                "Holder for storing non-persistent attributes."
                def get_all(self):
                    return [val for val in self.__dict__.keys()
                            if not val.startswith('_')]
                all = property(get_all)
                def __getattribute__(self, key):
                    # return None if no matching attribute was found.
                    try:
                        return _GA(self, key)
                    except AttributeError:
                        return None
            self._ndb_holder = NdbHolder()
            return self._ndb_holder
    #@ndb.setter
    def __ndb_set(self, value):
        "Stop accidentally replacing the db object"
        string = "Cannot assign directly to ndb object! "
        string = "Use ndb.attr=value instead."
        raise Exception(string)
    #@ndb.deleter
    def __ndb_del(self):
        "Stop accidental deletion."
        raise Exception("Cannot delete the ndb object!")
    ndb = property(__ndb_get, __ndb_set, __ndb_del)

    #
    # Lock / permission methods
    #

    def access(self, accessing_obj, access_type='read', default=False):
        """
        Determines if another object has permission to access.
        accessing_obj - object trying to access this one
        access_type - type of access sought
        default - what to return if no lock of access_type was found
        """
        return self.locks.check(accessing_obj, access_type=access_type, default=default)

    def has_perm(self, accessing_obj, access_type):
        "Alias to access"
        logger.log_depmsg("has_perm() is deprecated. Use access() instead.")
        return self.access(accessing_obj, access_type)

    def check_permstring(self, permstring):
        """
        This explicitly checks if we hold particular permission without involving
        any locks.
        """
        if self.player and self.player.is_superuser:
            return True

        if not permstring:
            return False
        perm = permstring.lower()
        if perm in [p.lower() for p in self.permissions]:
            # simplest case - we have a direct match
            return True
        if perm in _PERMISSION_HIERARCHY:
            # check if we have a higher hierarchy position
            ppos = _PERMISSION_HIERARCHY.index(perm)
            return any(True for hpos, hperm in enumerate(_PERMISSION_HIERARCHY)
                       if hperm in [p.lower() for p in self.permissions] and hpos > ppos)
        return False

    def flush_from_cache(self):
        """
        Flush this object instance from cache, forcing an object reload. Note that this
        will kill all temporary attributes on this object since it will be recreated
        as a new Typeclass instance.
        """
        self.__class__.flush_cached_instance(self)
