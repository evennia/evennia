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
#try:
#    import cPickle as pickle
#except ImportError:
#    import pickle
import traceback
#from collections import defaultdict

from django.db import models
from django.conf import settings
from django.utils.encoding import smart_str
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.db.models.signals import m2m_changed

from src.utils.idmapper.models import SharedMemoryModel
from src.server.caches import get_field_cache, set_field_cache, del_field_cache
from src.server.caches import get_attr_cache, del_attr_cache, set_attr_cache
from src.server.caches import get_prop_cache, set_prop_cache, flush_attr_cache
from src.server.caches import post_attr_update

#from src.server.caches import call_ndb_hooks
from src.server.models import ServerConfig
from src.typeclasses import managers
from src.locks.lockhandler import LockHandler
from src.utils import logger, utils
from src.utils.utils import make_iter, is_iter, to_str
from src.utils.dbserialize import to_pickle, from_pickle
from src.utils.picklefield import PickledObjectField

__all__ = ("Attribute", "TypeNick", "TypedObject")

_PERMISSION_HIERARCHY = [p.lower() for p in settings.PERMISSION_HIERARCHY]

_CTYPEGET = ContentType.objects.get
_GA = object.__getattribute__
_SA = object.__setattr__
_DA = object.__delattr__


#------------------------------------------------------------
#
#   Attributes
#
#------------------------------------------------------------

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
      lock_storage - perm strings
      obj - which object the attribute is defined on
      date_created - when the attribute was created.
      value - the data stored in the attribute, in pickled form
              using wrappers to be able to store/retrieve models.
      strvalue - string-only data. This data is not pickled and is
                 thus faster to search for in the database.
      category - optional character string for grouping the Attribute

    """

    #
    # Attribute Database Model setup
    #
    # These database fields are all set using their corresponding properties,
    # named same as the field, but withtout the db_* prefix.
    db_key = models.CharField('key', max_length=255, db_index=True)
    # access through the value property
    db_value = PickledObjectField('value', null=True)
    # string-specific storage for quick look-up
    db_strvalue = models.TextField('strvalue', null=True, blank=True)
    # optional categorization of attribute
    db_category = models.CharField('category', max_length=128, db_index=True, blank=True, null=True)
    # Lock storage
    db_lock_storage = models.TextField('locks', blank=True)
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
    #def __key_get(self):
    #    "Getter. Allows for value = self.key"
    #    return get_field_cache(self, "key")
    ##@key.setter
    #def __key_set(self, value):
    #    "Setter. Allows for self.key = value"
    #    set_field_cache(self, "key", value)
    ##@key.deleter
    #def __key_del(self):
    #    "Deleter. Allows for del self.key"
    #    raise Exception("Cannot delete attribute key!")
    #key = property(__key_get, __key_set, __key_del)

    ## obj property (wraps db_obj)
    ##@property
    #def __obj_get(self):
    #    "Getter. Allows for value = self.obj"
    #    return get_field_cache(self, "obj")
    ##@obj.setter
    #def __obj_set(self, value):
    #    "Setter. Allows for self.obj = value"
    #    set_field_cache(self, "obj", value)
    ##@obj.deleter
    #def __obj_del(self):
    #    "Deleter. Allows for del self.obj"
    #    self.db_obj = None
    #    self.save()
    #    del_field_cache(self, "obj")
    #obj = property(__obj_get, __obj_set, __obj_del)

    ## date_created property (wraps db_date_created)
    ##@property
    #def __date_created_get(self):
    #    "Getter. Allows for value = self.date_created"
    #    return get_field_cache(self, "date_created")
    ##@date_created.setter
    #def __date_created_set(self, value):
    #    "Setter. Allows for self.date_created = value"
    #    raise Exception("Cannot edit date_created!")
    ##@date_created.deleter
    #def __date_created_del(self):
    #    "Deleter. Allows for del self.date_created"
    #    raise Exception("Cannot delete date_created!")
    #date_created = property(__date_created_get, __date_created_set, __date_created_del)

    # value property (wraps db_value)
    #@property
    def __value_get(self):
        """
        Getter. Allows for value = self.value. Reads from cache if possible.
        """
        if self.no_cache:
            # re-create data from database and cache it
            value = from_pickle(self.db_value, db_obj=self)
            self.cached_value = value
            self.no_cache = False
        return self.cached_value

    #@value.setter
    def __value_set(self, new_value):
        """
        Setter. Allows for self.value = value. We make sure to cache everything.
        """
        to_store = to_pickle(new_value)
        self.cached_value = from_pickle(to_store, db_obj=self)
        self.no_cache = False
        self.db_value = to_store
        self.save()

        try:
            self._track_db_value_change.update(self.cached_value)
        except AttributeError:
            pass

    #@value.deleter
    def __value_del(self):
        "Deleter. Allows for del attr.value. This removes the entire attribute."
        self.delete()
    value = property(__value_get, __value_set, __value_del)

    # lock_storage property (wraps db_lock_storage)
    #@property
    #def __lock_storage_get(self):
    #    "Getter. Allows for value = self.lock_storage"
    #    return get_field_cache(self, "lock_storage")
    ##@lock_storage.setter
    #def __lock_storage_set(self, value):
    #    """Saves the lock_storage. This is usually not called directly, but through self.lock()"""
    #    self.db_lock_storage = value
    #    self.save()
    ##@lock_storage.deleter
    #def __lock_storage_del(self):
    #    "Deleter is disabled. Use the lockhandler.delete (self.lock.delete) instead"""
    #    logger.log_errmsg("Lock_Storage (on %s) cannot be deleted. Use obj.lock.delete() instead." % self)
    #lock_storage = property(__lock_storage_get, __lock_storage_set, __lock_storage_del)


    #
    #
    # Attribute methods
    #
    #

    def __str__(self):
        return smart_str("%s(%s)" % (_GA(self, "db_key"), _GA(self, "id")))

    def __unicode__(self):
        return u"%s(%s)" % (_GA(self, "db_key"), _GA(self, "id"))

    def access(self, accessing_obj, access_type='read', default=False):
        """
        Determines if another object has permission to access.
        accessing_obj - object trying to access this one
        access_type - type of access sought
        default - what to return if no lock of access_type was found
        """
        return self.locks.check(accessing_obj, access_type=access_type, default=default)

    def at_set(self, new_value):
        """
        Hook method called when the attribute changes value.
        """
        pass

#
# Handlers making use of the Attribute model
#

class AttributeHandler(object):
    """
    Handler for adding Attributes to the object.
    """
    _m2m_fieldname = "db_attributes"
    _attrcreate = "attrcreate"
    _attredit = "attredit"
    _attrread = "attrread"

    def __init__(self, obj):
        "Initialize handler"
        self.obj = obj

    def has(self, key, category=None):
        """
        Checks if the given Attribute (or list of Attributes) exists on the object.

        If an iterable is given, returns list of booleans.
        """
        ret = []
        category_cond = Q(db_category__iexact=category) if category else Q()
        cachekey = "%s%s" % (category, category)
        for keystr in make_iter(key):
            if get_attr_cache(self.obj, keystr):
                ret.append(True)
            else:
                ret.append(True if _GA(self.obj, self._m2m_fieldname).filter(Q(db_key__iexact=keystr) & category_cond) else False)
        return ret[0] if len(ret)==1 else ret

    def get(self, key=None, category=None, default=None, return_obj=False, strattr=False,
            raise_exception=False, accessing_obj=None, default_access=True):
        """
        Returns the value of the given Attribute or list of Attributes.
        strattr will cause the string-only value field instead of the normal
        pickled field data. Use to get back values from Attributes added with
        the strattr keyword.
        If return_obj=True, return the matching Attribute object
        instead. Returns None if no matches (or [ ] if key was a list
        with no matches). If raise_exception=True, failure to find a
        match will raise AttributeError instead.

        If accessing_obj is given, its "attrread" permission lock will be
        checked before displaying each looked-after Attribute. If no
        accessing_obj is given, no check will be done.
        """
        ret = []
        category_cond = Q(db_category__iexact=category) if category else Q()
        for keystr in make_iter(key):
            cachekey = "%s%s" % (category if category else "", keystr)
            attr_obj = get_attr_cache(self.obj, cachekey)
            key_cond = Q(db_key__iexact=keystr) if key!=None else Q()
            if not attr_obj:
                attr_obj = _GA(self.obj, "db_attributes").filter(key_cond & category_cond)
                if not attr_obj:
                    if raise_exception:
                        raise AttributeError
                    ret.append(default)
                    continue
                attr_obj = attr_obj[0] # query is evaluated here
                set_attr_cache(self.obj, cachekey, attr_obj)
            ret.append(attr_obj)
        if accessing_obj:
            # check 'attrread' locks
            ret = [attr for attr in ret if attr.access(accessing_obj, self._attrread, default=default_access)]
        if strattr:
            ret = ret if return_obj else [attr.strvalue if attr else None for attr in ret]
        else:
            ret = ret if return_obj else [attr.value if attr else None for attr in ret]
        return ret[0] if len(ret)==1 else ret

    def add(self, key, value, category=None, lockstring="", strattr=False, accessing_obj=None, default_access=True):
        """
        Add attribute to object, with optional lockstring.

        If strattr is set, the db_strvalue field will be used (no pickling). Use the get() method
        with the strattr keyword to get it back.

        If accessing_obj is given, self.obj's  'attrcreate' lock access
        will be checked against it. If no accessing_obj is given, no check will be done.
        """
        if accessing_obj and not self.obj.access(accessing_obj, self._attrcreate, default=default_access):
            # check create access
            return

        cachekey = "%s%s" % (category if category else "", key)
        attr_obj = get_attr_cache(self.obj, cachekey)
        if not attr_obj:
            # check if attribute already exists
            attr_obj = _GA(self.obj, self._m2m_fieldname).filter(db_key__iexact=key)
            if attr_obj.count():
                # re-use old attribute object
                attr_obj = attr_obj[0]
                set_attr_cache(self.obj, key, attr_obj) # renew cache
            else:
                # no old attr available; create new (caches automatically)
                attr_obj = Attribute(db_key=key, db_category=category)
                attr_obj.save() # important
                _GA(self.obj, self._m2m_fieldname).add(attr_obj)
        if lockstring:
            attr_obj.locks.add(lockstring)
        # we shouldn't need to fear stale objects, the field signalling should catch all cases
        if strattr:
            # store as a simple string
            attr_obj.strvalue = value
        else:
            # pickle arbitrary data
            attr_obj.value = value


    def remove(self, key, raise_exception=False, category=None, accessing_obj=None, default_access=True):
        """Remove attribute or a list of attributes from object.

        If accessing_obj is given, will check against the 'attredit' lock. If not given, this check is skipped.
        """
        keys = make_iter(key)
        category_cond = Q(db_category__iexact=category) if category else Q()
        for attrkey in keys:
            matches = _GA(self.obj, self._m2m_fieldname).filter(Q(db_key__iexact=attrkey) & Q())
            if not matches and raise_exception:
                raise AttributeError
            for attr in matches:
                if accessing_obj and not attr.access(accessing_obj, self._attredit, default=default_access):
                    continue
                del_attr_cache(self.obj, attr.db_key)
                attr.delete()

    def clear(self, category=None, accessing_obj=None, default_access=True):
        """
        Remove all Attributes on this object. If accessing_obj is
        given, check the 'attredit' lock on each Attribute before
        continuing. If not given, skip check.
        """
        if category==None:
            all_attr = _GA(self.obj, self._m2m_fieldname).all()
        else:
            all_attrs = _GA(self.obj, self._m2m_fieldname).filter(db_category=category)
        for attr in all_attrs:
            if accessing_obj and not attr.access(accessing_obj, self._attredit, default=default_access):
                continue
            del_attr_cache(self.obj, attr.db_key)
            attr.delete()

    def all(self, category=None, accessing_obj=None, default_access=True):
        """
        Return all Attribute objects on this object.

        If accessing_obj is given, check the "attrread" lock on
        each attribute before returning them. If not given, this
        check is skipped.
        """
        if category==None:
            all_attrs = _GA(self.obj, self._m2m_fieldname).all()
        else:
            all_attrs = _GA(self.obj, self._m2m_fieldname).filter(db_category=category)
        if accessing_obj:
            return [attr for attr in all_attrs if attr.access(accessing_obj, self._attrread, default=default_access)]
        else:
            return list(all_attrs)

class NickHandler(AttributeHandler):
    """
    Handles the addition and removal of Nicks
    (uses Attributes' strvalue and category fields)

    Nicks are stored as Attributes
    with categories nick_<nicktype>
    """
    def has(self, key, category="inputline"):
        categry = "nick_%s" % category
        return super(NickHandler, self).has(key, category=category)
    def add(self, key, replacement, category="inputline", **kwargs):
        "Add a new nick"
        category = "nick_%s" % category
        super(NickHandler, self).add(key, replacement, category=category, strattr=True, **kwargs)
    def get(self, key=None, category="inputline", **kwargs):
        "Get the replacement value matching the given key and category"
        category = "nick_%s" % category
        return super(NickHandler, self).get(key=key, category=category, strattr=True, **kwargs)
    def remove(self, key, category="inputline", **kwargs):
        "Remove Nick with matching category"
        category = "nick_%s" % category
        super(NickHandler, self).remove(key, category=category, **kwargs)


#------------------------------------------------------------
#
# Tags
#
#------------------------------------------------------------

class Tag(models.Model):
    """
    Tags are quick markers for objects in-game. An typeobject
    can have any number of tags, stored via its db_tags property.
    Tagging similar objects will make it easier to quickly locate the
    group later (such as when implementing zones). The main advantage
    of tagging as opposed to using Attributes is speed; a tag is very
    limited in what data it can hold, and the tag key+category is
    indexed for efficient lookup in the database. Tags are shared between
    objects - a new tag is only created if the key+category combination
    did not previously exist, making them unsuitable for storing
    object-related data (for this a full Attribute
    should be used).
    The 'db_data' field is intended as a documentation
    field for the tag itself, such as to document what this tag+category
    stands for and display that in a web interface or similar.

    The main default use for Tags is to implement Aliases for objects.
    this uses the 'aliases' tag category, which is also checked by the
    default search functions of Evennia to allow quick searches by alias.
    """
    db_key = models.CharField('key', max_length=255, null=True, help_text="tag identifier", db_index=True)
    db_category = models.CharField('category', max_length=64, null=True, help_text="tag category", db_index=True)
    db_data = models.TextField('data', null=True, blank=True, help_text="optional data field with extra information. This is not searched for.")

    objects = managers.TagManager()
    class Meta:
        "Define Django meta options"
        verbose_name = "Tag"
        unique_together =(('db_key', 'db_category'),)
        index_together = (('db_key', 'db_category'),)
    def __unicode__(self):
        return u"%s" % self.db_key
    def __str__(self):
        return str(self.db_key)


#
# Handlers making use of the Tags model
#

class TagHandler(object):
    """
    Generic tag-handler. Accessed via TypedObject.tags.
    """
    _m2m_fieldname = "db_tags"
    _base_category = ""

    def __init__(self, obj, category_prefix=""):
        """
        Tags are stored internally in the TypedObject.db_tags m2m field
        using the category <category_prefix><tag_category>
        """
        self.obj = obj
        self.prefix = "%s%s" % (category_prefix.strip().lower() if category_prefix else "", self._base_category)

    def add(self, tag, category=None, data=None):
        "Add a new tag to the handler. Tag is a string or a list of strings."
        for tagstr in make_iter(tag):
            tagstr = tagstr.strip().lower() if tagstr!=None else None
            category = "%s%s" % (self.prefix, category.strip().lower()) if category!=None else None
            data = str(data) if data!=None else None
            # this will only create tag if no matches existed beforehand (it will overload
            # data on an existing tag since that is not considered part of making the tag unique)
            tagobj = Tag.objects.create_tag(key=tagstr, category=category, data=data)
            #print tagstr
            #print tagobj
            _GA(self.obj, self._m2m_fieldname).add(tagobj)

    def get(self, key, category="", return_obj=False):
        "Get the data field for the given tag or list of tags. If return_obj=True, return the matching Tag objects instead."
        ret = []
        category = "%s%s" % (self.prefix, category.strip().lower()) if category!=None else None
        for keystr in make_iter(key):
            ret.expand(_GA(self.obj, self._m2m_fieldname).filter(db_key__iexact=keystr, db_category__iexact=category))
        ret = ret if return_obj else [to_str(tag.db_data) for tag in ret]
        return ret[0] if len(ret)==1 else ret

    def remove(self, tag, category=None):
        "Remove a tag from the handler"
        for tag in make_iter(tag):
            if not tag or tag.strip(): # we don't allow empty tags
                continue
            tag = tag.strip().lower() if tag!=None else None
            category = "%s%s" % (self.prefix, category.strip().lower()) if category!=None else None
            #TODO This does not delete the tag object itself. Maybe it should do that when no
            # objects reference the tag anymore?
            tagobj = self.obj.db_tags.filter(db_key=tag, db_category=category)
            if tagobj:
                _GA(self.obj, self._m2m_fieldname).remove(tagobj[0])
    def clear(self):
        "Remove all tags from the handler"
        _GA(self.obj, self._m2m_fieldname).clear()

    def all(self):
        "Get all tags in this handler"
        return [p[0] for p in _GA(self.obj, self._m2m_fieldname).all().values_list("db_key")]

    def __str__(self):
        return ",".join(self.all())
    def __unicode(self):
        return u",".join(self.all())

class AliasHandler(TagHandler):
    _base_category = "alias"

class PermissionHandler(TagHandler):
    _base_category = "permission"


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
    # These databse fields are all accessed and set using their corresponding properties,
    # named same as the field, but without the db_* prefix (no separate save() call is needed)

    # Main identifier of the object, for searching. Is accessed with self.key or self.name
    db_key = models.CharField('key', max_length=255, db_index=True)
    # This is the python path to the type class this object is tied to the type class is what defines what kind of Object this is)
    db_typeclass_path = models.CharField('typeclass', max_length=255, null=True,
            help_text="this defines what 'type' of entity this is. This variable holds a Python path to a module with a valid Evennia Typeclass.")
    # Creation date. This is not changed once the object is created.
    db_date_created = models.DateTimeField('creation date', editable=False, auto_now_add=True)
    # Permissions (access these through the 'permissions' property)
    #db_permissions = models.CharField('permissions', max_length=255, blank=True,
    #     help_text="a comma-separated list of text strings checked by in-game locks. They are often used for hierarchies, such as letting a Player have permission 'Wizards', 'Builders' etc. Character objects use 'Players' by default. Most other objects don't have any permissions.")
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

    # lock handler self.locks
    def __init__(self, *args, **kwargs):
        "We must initialize the parent first - important!"
        super(SharedMemoryModel, self).__init__(*args, **kwargs)
        #SharedMemoryModel.__init__(self, *args, **kwargs)
        _SA(self, "dbobj", self)   # this allows for self-reference
        _SA(self, "locks", LockHandler(self))
        _SA(self, "permissions", PermissionHandler(self))

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

    # key property (wraps db_key)
    #@property
    #def __key_get(self):
    #    "Getter. Allows for value = self.key"
    #    #return _GA(self, "db_key")
    #    return get_field_cache(self, "key")
    ##@key.setter
    #def __key_set(self, value):
    #    "Setter. Allows for self.key = value"
    #    set_field_cache(self, "key", value)
    ##@key.deleter
    #def __key_del(self):
    #    "Deleter. Allows for del self.key"
    #    raise Exception("Cannot delete objectdb key!")
    #key = property(__key_get, __key_set, __key_del)

    # name property (alias to self.key)
    def __name_get(self): return self.key
    def __name_set(self, value): self.key = value
    def __name_del(self): raise Exception("Cannot delete name")
    name = property(__name_get, __name_set, __name_del)

    # typeclass_path property - we manage this separately.
    #@property
    #def __typeclass_path_get(self):
    #    "Getter. Allows for value = self.typeclass_path"
    #    return _GA(self, "db_typeclass_path")
    ##@typeclass_path.setter
    #def __typeclass_path_set(self, value):
    #    "Setter. Allows for self.typeclass_path = value"
    #    _SA(self, "db_typeclass_path", value)
    #    update_fields = ["db_typeclass_path"] if _GA(self, "_get_pk_val")(_GA(self, "_meta")) is not None else None
    #    _GA(self, "save")(update_fields=update_fields)
    ##@typeclass_path.deleter
    #def __typeclass_path_del(self):
    #    "Deleter. Allows for del self.typeclass_path"
    #    self.db_typeclass_path = ""
    #    _GA(self, "save")(update_fields=["db_typeclass_path"])
    #typeclass_path = property(__typeclass_path_get, __typeclass_path_set, __typeclass_path_del)

    # date_created property
    #@property
    #def __date_created_get(self):
    #    "Getter. Allows for value = self.date_created"
    #    return get_field_cache(self, "date_created")
    ##@date_created.setter
    #def __date_created_set(self, value):
    #    "Setter. Allows for self.date_created = value"
    #    raise Exception("Cannot change date_created!")
    ##@date_created.deleter
    #def __date_created_del(self):
    #    "Deleter. Allows for del self.date_created"
    #    raise Exception("Cannot delete date_created!")
    #date_created = property(__date_created_get, __date_created_set, __date_created_del)

    # permissions property
    #@property
    #def __permissions_get(self):
    #    "Getter. Allows for value = self.name. Returns a list of permissions."
    #    perms = get_field_cache(self, "permissions")
    #    if perms:
    #        return [perm.strip() for perm in perms.split(',')]
    #    return []
    ##@permissions.setter
    #def __permissions_set(self, value):
    #    "Setter. Allows for self.name = value. Stores as a comma-separated string."
    #    value = ",".join([utils.to_unicode(val).strip() for val in make_iter(value)])
    #    set_field_cache(self, "permissions", value)
    ##@permissions.deleter
    #def __permissions_del(self):
    #    "Deleter. Allows for del self.name"
    #    self.db_permissions = ""
    #    self.save()
    #    del_field_cache(self, "permissions")
    #permissions = property(__permissions_get, __permissions_set, __permissions_del)

    # lock_storage property (wraps db_lock_storage)
    #@property
    #def __lock_storage_get(self):
    #    "Getter. Allows for value = self.lock_storage"
    #    return get_field_cache(self, "lock_storage")
    ##@lock_storage.setter
    #def __lock_storage_set(self, value):
    #    """Saves the lock_storage. This is usually not called directly, but through self.lock()"""
    #    set_field_cache(self, "lock_storage", value)
    ##@lock_storage.deleter
    #def __lock_storage_del(self):
    #    "Deleter is disabled. Use the lockhandler.delete (self.lock.delete) instead"""
    #    logger.log_errmsg("Lock_Storage (on %s) cannot be deleted. Use obj.lock.delete() instead." % self)
    #lock_storage = property(__lock_storage_get, __lock_storage_set, __lock_storage_del)



    #
    #
    # TypedObject main class methods and properties
    #
    #

    # these are identifiers for fast Attribute access and caching
    _typeclass_paths = settings.OBJECT_TYPECLASS_PATHS

    def __eq__(self, other):
        return other and hasattr(other, 'dbid') and self.dbid == other.dbid

    def __str__(self):
        return smart_str("%s" % _GA(self, "db_key"))

    def __unicode__(self):
        return u"%s" % _GA(self, "db_key")

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
            if propname.startswith('_'):
                # don't relay private/special varname lookups to the typeclass
                raise AttributeError("private property %s not found on db model (typeclass not searched)." % propname)
            # check if the attribute exists on the typeclass instead
            # (we make sure to not incur a loop by not triggering the
            # typeclass' __getattribute__, since that one would
            # try to look back to this very database object.)
            return _GA(_GA(self, 'typeclass'), propname)

    def _hasattr(self, obj, attrname):
        """
        Loop-safe version of hasattr, to avoid running a lookup that
        will be rerouted up the typeclass. Returns True/False.
        """
        try:
            _GA(obj, attrname)
            return True
        except AttributeError:
            return False

    #@property
    def __dbid_get(self):
        """
        Caches and returns the unique id of the object.
        Use this instead of self.id, which is not cached.
        """
        dbid = get_prop_cache(self, "_dbid")
        if not dbid:
            dbid = _GA(self, "id")
            set_prop_cache(self, "_dbid", dbid)
        return dbid
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
        return "#%s" % _GA(self, "_TypedObject__dbid_get")()
    def __dbref_set(self):
        raise Exception("dbref cannot be set!")
    def __dbref_del(self):
        raise Exception("dbref cannot be deleted!")
    dbref = property(__dbref_get, __dbref_set, __dbref_del)


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
                #print "typeclass:",typeclass,tpath
                if callable(typeclass):
                    # we succeeded to import. Cache and return.
                    _SA(self, "typeclass_path", tpath)
                    typeclass = typeclass(self)
                    _SA(self, "_cached_typeclass", typeclass)
                    try:
                        typeclass.at_init()
                    except AttributeError:
                        logger.log_trace("\n%s: Error initializing typeclass %s. Using default." % (self, tpath))
                        break
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


    def delete(self, *args, **kwargs):
        """
        Type-level cleanup
        """
        flush_attr_cache()
        super(TypedObject, self).delete(*args, **kwargs)


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
            cls = new_typeclass
            new_typeclass = "%s.%s" % (cls.__module__, cls.__name__)
        else:
            new_typeclass = "%s" % to_str(new_typeclass)

        # Try to set the new path
        # this will automatically save to database
        old_typeclass_path = self.typeclass_path
        _SA(self, "typeclass_path", new_typeclass.strip())
        # this will automatically use a default class if
        # there is an error with the given typeclass.
        new_typeclass = self.typeclass
        if self.typeclass_path != new_typeclass.path and no_default:
            # something went wrong; the default was loaded instead,
            # and we don't allow that; instead we return to previous.
            _SA(self, "typeclass_path", old_typeclass_path)
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

    def check_permstring(self, permstring):
        """
        This explicitly checks if we hold particular permission without involving
        any locks.
        """
        if hasattr(self, "player"):
            if self.player and self.player.is_superuser: return True
        else:
            if self.is_superuser: return True

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


    def flush_from_cache(self):
        """
        Flush this object instance from cache, forcing an object reload. Note that this
        will kill all temporary attributes on this object since it will be recreated
        as a new Typeclass instance.
        """
        self.__class__.flush_cached_instance(self)

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
            class NdbHolder(object):
                "Holder for storing non-attr_obj attributes."
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
                def __setattr__(self, key, value):
                    # hook the oob handler here
                    #call_ndb_hooks(self, key, value)
                    _SA(self, key, value)
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

    #def nattr(self, attribute_name=None, value=None, delete=False):
    #    """
    #    This allows for assigning non-persistent data on the object using
    #    a method call. Will return None if trying to access a non-existing property.
    #    """
    #    if attribute_name == None:
    #        # act as a list method
    #        if callable(self.ndb.all):
    #            return self.ndb.all()
    #        else:
    #            return [val for val in self.ndb.__dict__.keys()
    #                    if not val.startswith['_']]
    #    elif delete == True:
    #        if hasattr(self.ndb, attribute_name):
    #            _DA(_GA(self, "ndb"), attribute_name)
    #    elif value == None:
    #        # act as a getter.
    #        if hasattr(self.ndb, attribute_name):
    #            _GA(_GA(self, "ndb"), attribute_name)
    #        else:
    #            return None
    #    else:
    #        # act as a setter
    #        _SA(self.ndb, attribute_name, value)



    #
    # Attribute handler methods  - DEPRECATED!
    #

    #
    # Fully attr_obj attributes. You usually access these
    # through the obj.db.attrname method.

    # Helper methods for attr_obj attributes

    def has_attribute(self, attribute_name):
        """
        See if we have an attribute set on the object.

        attribute_name: (str) The attribute's name.
        """
        logger.log_depmsg("obj.has_attribute() is deprecated. Use obj.attributes.has().")
        return _GA(self, "attributes").has(attribute_name)

    def set_attribute(self, attribute_name, new_value=None, lockstring=""):
        """
        Sets an attribute on an object. Creates the attribute if need
        be.

        attribute_name: (str) The attribute's name.
        new_value: (python obj) The value to set the attribute to. If this is not
                                a str, the object will be stored as a pickle.
        lockstring - this sets an access restriction on the attribute object. Note that
                     this is normally NOT checked - use the secureattr() access method
                     below to perform access-checked modification of attributes. Lock
                     types checked by secureattr are 'attrread','attredit','attrcreate'.
        """
        logger.log_depmsg("obj.set_attribute() is deprecated. Use obj.db.attr=value or obj.attributes.add().")
        _GA(self, "attributes").add(attribute_name, new_value, lockstring=lockstring)

    def get_attribute_obj(self, attribute_name, default=None):
        """
        Get the actual attribute object named attribute_name
        """
        logger.log_depmsg("obj.get_attribute_obj() is deprecated. Use obj.attributes.get(..., return_obj=True)")
        return _GA(self, "attributes").get(attribute_name, default=default, return_obj=True)

    def get_attribute(self, attribute_name, default=None, raise_exception=False):
        """
        Returns the value of an attribute on an object. You may need to
        type cast the returned value from this function since the attribute
        can be of any type. Returns default if no match is found.

        attribute_name: (str) The attribute's name.
        default: What to return if no attribute is found
        raise_exception (bool) - raise an exception if no object exists instead of returning default.
        """
        logger.log_depmsg("obj.get_attribute() is deprecated. Use obj.db.attr or obj.attributes.get().")
        return _GA(self, "attributes").get(attribute_name, default=default, raise_exception=raise_exception)

    def del_attribute(self, attribute_name, raise_exception=False):
        """
        Removes an attribute entirely.

        attribute_name: (str) The attribute's name.
        raise_exception (bool) - raise exception if attribute to delete
                                 could not be found
        """
        logger.log_depmsg("obj.del_attribute() is deprecated. Use del obj.db.attr or obj.attributes.remove().")
        _GA(self, "attributes").remove(attribute_name, raise_exception=raise_exception)

    def get_all_attributes(self):
        """
        Returns all attributes defined on the object.
        """
        logger.log_depmsg("obj.get_all_attributes() is deprecated. Use obj.db.all() or obj.attributes.all().")
        return _GA(self, "attributes").all()

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
        logger.log_depmsg("obj.attr() is deprecated. Use handlers obj.db or obj.attributes.")
        if attribute_name == None:
            # act as a list method
            return _GA(self, "attributes").all()
        elif delete == True:
            _GA(self, "attributes").remove(attribute_name)
        elif value == None:
            # act as a getter.
            return _GA(self, "attributes").get(attribute_name)
        else:
            # act as a setter
            self._GA(self, "attributes").add(attribute_name, value)

    def secure_attr(self, accessing_object, attribute_name=None, value=None, delete=False,
                    default_access_read=True, default_access_edit=True, default_access_create=True):
        """
        This is a version of attr that requires the accessing object
        as input and will use that to check eventual access locks on
        the Attribute before allowing any changes or reads.

        In the cases when this method wouldn't return, it will return
        True for a successful operation, None otherwise.

        locktypes checked on the Attribute itself:
            attrread - control access to reading the attribute value
            attredit - control edit/delete access
        locktype checked on the object on which the Attribute is/will be stored:
            attrcreate - control attribute create access (this is checked *on the object*  not on the Attribute!)

        default_access_* defines which access is assumed if no
        suitable lock is defined on the Atttribute.

        """
        logger.log_depmsg("obj.secure_attr() is deprecated. Use obj.attributes methods, giving accessing_obj keyword.")
        if attribute_name == None:
            return _GA(self, "attributes").all(accessing_obj=accessing_object, default_access=default_access_read)
        elif delete == True:
            # act as deleter
            _GA(self, "attributes").remove(attribute_name, accessing_obj=accessing_object, default_access=default_access_edit)
        elif value == None:
            # act as getter
            return _GA(self, "attributes").get(attribute_name, accessing_obj=accessing_object, default_access=default_access_read)
        else:
            # act as setter
            attr = _GA(self, "attributes").get(attribute_name, return_obj=True)
            if attr:
               # attribute already exists
                _GA(self, "attributes").add(attribute_name, value, accessing_obj=accessing_object, default_access=default_access_edit)
            else:
                # creating a new attribute - check access on storing object!
                _GA(self, "attributes").add(attribute_name, value, accessing_obj=accessing_object, default_access=default_access_create)

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
           all_attr = obj.db.all (unless there is no attribute named 'all', in which
                                    case that will be returned instead).
        """
        try:
            return self._db_holder
        except AttributeError:
            class DbHolder(object):
                "Holder for allowing property access of attributes"
                def __init__(self, obj):
                    _SA(self, 'obj', obj)
                    _SA(self, "attrhandler", _GA(_GA(self, "obj"), "attributes"))
                def __getattribute__(self, attrname):
                    if attrname == 'all':
                        # we allow to overload our default .all
                        attr = _GA(self, "attrhandler").get("all")
                        if attr:
                            return attr
                        return _GA(self, 'all')
                    return _GA(self, "attrhandler").get(attrname)
                def __setattr__(self, attrname, value):
                    _GA(self, "attrhandler").add(attrname, value)
                def __delattr__(self, attrname):
                    _GA(self, "attrhandler").remove(attrname)
                def get_all(self):
                    return _GA(self, "attrhandler").all()
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



# connect to attribute cache signal
m2m_changed.connect(post_attr_update, sender=TypedObject.db_attributes.through)
