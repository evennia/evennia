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
import re
import traceback
import weakref

from django.db import models
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.utils.encoding import smart_str

from src.utils.idmapper.models import SharedMemoryModel
from src.server.caches import get_prop_cache, set_prop_cache
#from src.server.caches import set_attr_cache

#from src.server.caches import call_ndb_hooks
from src.server.models import ServerConfig
from src.typeclasses import managers
from src.locks.lockhandler import LockHandler
from src.utils import logger
from src.utils.utils import (
    make_iter, is_iter, to_str, inherits_from, lazy_property)
from src.utils.dbserialize import to_pickle, from_pickle
from src.utils.picklefield import PickledObjectField

__all__ = ("Attribute", "TypeNick", "TypedObject")

TICKER_HANDLER = None

_PERMISSION_HIERARCHY = [p.lower() for p in settings.PERMISSION_HIERARCHY]
_TYPECLASS_AGGRESSIVE_CACHE = settings.TYPECLASS_AGGRESSIVE_CACHE

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
    db_value = PickledObjectField(
        'value', null=True,
        help_text="The data returned when the attribute is accessed. Must be "
                  "written as a Python literal if editing through the admin "
                  "interface. Attribute values which are not Python literals "
                  "cannot be edited through the admin interface.")
    db_strvalue = models.TextField(
        'strvalue', null=True, blank=True,
        help_text="String-specific storage for quick look-up")
    db_category = models.CharField(
        'category', max_length=128, db_index=True, blank=True, null=True,
        help_text="Optional categorization of attribute.")
    # Lock storage
    db_lock_storage = models.TextField(
        'locks', blank=True,
        help_text="Lockstrings for this object are stored here.")
    db_model = models.CharField(
        'model', max_length=32, db_index=True, blank=True, null=True,
        help_text="Which model of object this attribute is attached to (A "
                  "natural key like objects.dbobject). You should not change "
                  "this value unless you know what you are doing.")
    # subclass of Attribute (None or nick)
    db_attrtype = models.CharField(
        'attrtype', max_length=16, db_index=True, blank=True, null=True,
        help_text="Subclass of Attribute (None or nick)")
    # time stamp
    db_date_created = models.DateTimeField(
        'date_created', editable=False, auto_now_add=True)

    # Database manager
    objects = managers.AttributeManager()

    @lazy_property
    def locks(self):
        return LockHandler(self)

    class Meta:
        "Define Django meta options"
        verbose_name = "Evennia Attribute"

    # read-only wrappers
    key = property(lambda self: self.db_key)
    strvalue = property(lambda self: self.db_strvalue)
    category = property(lambda self: self.db_category)
    model = property(lambda self: self.db_model)
    attrtype = property(lambda self: self.db_attrtype)
    date_created = property(lambda self: self.db_date_created)

    def __lock_storage_get(self):
        return self.db_lock_storage
    def __lock_storage_set(self, value):
        self.db_lock_storage = value
        self.save(update_fields=["db_lock_storage"])
    def __lock_storage_del(self):
        self.db_lock_storage = ""
        self.save(update_fields=["db_lock_storage"])
    lock_storage = property(__lock_storage_get, __lock_storage_set, __lock_storage_del)

    # Wrapper properties to easily set database fields. These are
    # @property decorators that allows to access these fields using
    # normal python operations (without having to remember to save()
    # etc). So e.g. a property 'attr' has a get/set/del decorator
    # defined that allows the user to do self.attr = value,
    # value = self.attr and del self.attr respectively (where self
    # is the object in question).

    # value property (wraps db_value)
    #@property
    def __value_get(self):
        """
        Getter. Allows for value = self.value.
        We cannot cache here since it makes certain cases (such
        as storing a dbobj which is then deleted elsewhere) out-of-sync.
        The overhead of unpickling seems hard to avoid.
        """
        return from_pickle(self.db_value, db_obj=self)

    #@value.setter
    def __value_set(self, new_value):
        """
        Setter. Allows for self.value = value. We cannot cache here,
        see self.__value_get.
        """
        self.db_value = to_pickle(new_value)
        self.save(update_fields=["db_value"])

    #@value.deleter
    def __value_del(self):
        "Deleter. Allows for del attr.value. This removes the entire attribute."
        self.delete()
    value = property(__value_get, __value_set, __value_del)

    #
    #
    # Attribute methods
    #
    #

    def __str__(self):
        return smart_str("%s(%s)" % (_GA(self, "db_key"), _GA(self, "id")))

    def __unicode__(self):
        return u"%s(%s)" % (_GA(self, "db_key"), _GA(self, "id"))

    def access(self, accessing_obj, access_type='read', default=False, **kwargs):
        """
        Determines if another object has permission to access.
        accessing_obj - object trying to access this one
        access_type - type of access sought
        default - what to return if no lock of access_type was found
        **kwargs - passed to at_access hook along with result.
        """
        result = self.locks.check(accessing_obj, access_type=access_type, default=default)
        #self.at_access(result, **kwargs)
        return result


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
    _attrtype = None

    def __init__(self, obj):
        "Initialize handler"
        self.obj = obj
        self._objid = obj.id
        self._model = to_str(obj.__class__.__name__.lower())
        self._cache = None

    def _recache(self):
        "Cache all attributes of this object"
        query = {"%s__id" % self._model : self._objid,
                 "attribute__db_attrtype" : self._attrtype}
        attrs = [conn.attribute for conn in getattr(self.obj, self._m2m_fieldname).through.objects.filter(**query)]
        self._cache = dict(("%s-%s" % (to_str(attr.db_key).lower(),
                                       attr.db_category.lower() if conn.attribute.db_category else None),
                            attr) for attr in attrs)

    def has(self, key, category=None):
        """
        Checks if the given Attribute (or list of Attributes) exists on
        the object.

        If an iterable is given, returns list of booleans.
        """
        if self._cache is None or not _TYPECLASS_AGGRESSIVE_CACHE:
            self._recache()
        key = [k.strip().lower() for k in make_iter(key) if k]
        category = category.strip().lower() if category is not None else None
        searchkeys = ["%s-%s" % (k, category) for k in make_iter(key)]
        ret = [self._cache.get(skey) for skey in searchkeys if skey in self._cache]
        return ret[0] if len(ret) == 1 else ret

    def get(self, key=None, category=None, default=None, return_obj=False,
            strattr=False, raise_exception=False, accessing_obj=None,
            default_access=True, not_found_none=False):
        """
        Returns the value of the given Attribute or list of Attributes.
        strattr will cause the string-only value field instead of the normal
        pickled field data. Use to get back values from Attributes added with
        the strattr keyword.
        If return_obj=True, return the matching Attribute object
        instead. Returns default if no matches (or [ ] if key was a list
        with no matches). If raise_exception=True, failure to find a
        match will raise AttributeError instead.

        If accessing_obj is given, its "attrread" permission lock will be
        checked before displaying each looked-after Attribute. If no
        accessing_obj is given, no check will be done.
        """

        class RetDefault(object):
            "Holds default values"
            def __init__(self):
                self.value = default
                self.strvalue = str(default) if default is not None else None

        if self._cache is None or not _TYPECLASS_AGGRESSIVE_CACHE:
            self._recache()
        ret = []
        key = [k.strip().lower() for k in make_iter(key) if k]
        category = category.strip().lower() if category is not None else None
        #print "cache:", self._cache.keys(), key
        if not key:
            # return all with matching category (or no category)
            catkey = "-%s" % category if category is not None else None
            ret = [attr for key, attr in self._cache.items() if key and key.endswith(catkey)]
        else:
            for searchkey in ("%s-%s" % (k, category) for k in key):
                attr_obj = self._cache.get(searchkey)
                if attr_obj:
                    ret.append(attr_obj)
                else:
                    if raise_exception:
                        raise AttributeError
                    else:
                        ret.append(RetDefault())
        if accessing_obj:
            # check 'attrread' locks
            ret = [attr for attr in ret if attr.access(accessing_obj, self._attrread, default=default_access)]
        if strattr:
            ret = ret if return_obj else [attr.strvalue for attr in ret if attr]
        else:
            ret = ret if return_obj else [attr.value for attr in ret if attr]
        if not ret:
            return ret if len(key) > 1 else default
        return ret[0] if len(ret)==1 else ret


    def add(self, key, value, category=None, lockstring="",
            strattr=False, accessing_obj=None, default_access=True):
        """
        Add attribute to object, with optional lockstring.

        If strattr is set, the db_strvalue field will be used (no pickling).
        Use the get() method with the strattr keyword to get it back.

        If accessing_obj is given, self.obj's  'attrcreate' lock access
        will be checked against it. If no accessing_obj is given, no check
        will be done.
        """
        if accessing_obj and not self.obj.access(accessing_obj,
                                      self._attrcreate, default=default_access):
            # check create access
            return
        if self._cache is None:
            self._recache()
        if not key:
            return

        category = category.strip().lower() if category is not None else None
        keystr = key.strip().lower()
        cachekey = "%s-%s" % (keystr, category)
        attr_obj = self._cache.get(cachekey)

        if attr_obj:
            # update an existing attribute object
            if strattr:
                # store as a simple string (will not notify OOB handlers)
                attr_obj.db_strvalue = value
                attr_obj.save(update_fields=["db_strvalue"])
            else:
                # store normally (this will also notify OOB handlers)
                attr_obj.value = value
        else:
            # create a new Attribute (no OOB handlers can be notified)
            kwargs = {"db_key" : keystr, "db_category" : category,
                      "db_model" : self._model, "db_attrtype" : self._attrtype,
                      "db_value" : None if strattr else to_pickle(value),
                      "db_strvalue" : value if strattr else None}
            new_attr = Attribute(**kwargs)
            new_attr.save()
            getattr(self.obj, self._m2m_fieldname).add(new_attr)
            self._cache[cachekey] = new_attr


    def batch_add(self, key, value, category=None, lockstring="",
            strattr=False, accessing_obj=None, default_access=True):
        """
        Batch-version of add(). This is more efficient than
        repeat-calling add.

        key and value must be sequences of the same length, each
        representing a key-value pair.

        """
        if accessing_obj and not self.obj.access(accessing_obj,
                                      self._attrcreate, default=default_access):
            # check create access
            return
        if self._cache is None:
            self._recache()
        if not key:
            return

        keys, values= make_iter(key), make_iter(value)

        if len(keys) != len(values):
            raise RuntimeError("AttributeHandler.add(): key and value of different length: %s vs %s" % key, value)
        category = category.strip().lower() if category is not None else None
        new_attrobjs = []
        for ikey, keystr in enumerate(keys):
            keystr = keystr.strip().lower()
            new_value = values[ikey]
            cachekey = "%s-%s" % (keystr, category)
            attr_obj = self._cache.get(cachekey)

            if attr_obj:
                # update an existing attribute object
                if strattr:
                    # store as a simple string (will not notify OOB handlers)
                    attr_obj.db_strvalue = new_value
                    attr_obj.save(update_fields=["db_strvalue"])
                else:
                    # store normally (this will also notify OOB handlers)
                    attr_obj.value = new_value
            else:
                # create a new Attribute (no OOB handlers can be notified)
                kwargs = {"db_key" : keystr, "db_category" : category,
                          "db_attrtype" : self._attrtype,
                          "db_value" : None if strattr else to_pickle(new_value),
                          "db_strvalue" : value if strattr else None}
                new_attr = Attribute(**kwargs)
                new_attr.save()
                new_attrobjs.append(new_attr)
        if new_attrobjs:
            # Add new objects to m2m field all at once
            getattr(self.obj, self._m2m_fieldname).add(*new_attrobjs)
            self._recache()


    def remove(self, key, raise_exception=False, category=None,
               accessing_obj=None, default_access=True):
        """Remove attribute or a list of attributes from object.

        If accessing_obj is given, will check against the 'attredit' lock.
        If not given, this check is skipped.
        """
        if self._cache is None or not _TYPECLASS_AGGRESSIVE_CACHE:
            self._recache()
        key = [k.strip().lower() for k in make_iter(key) if k]
        category = category.strip().lower() if category is not None else None
        for searchstr in ("%s-%s" % (k, category) for k in key):
            attr_obj = self._cache.get(searchstr)
            if attr_obj:
                if not (accessing_obj and not attr_obj.access(accessing_obj,
                        self._attredit, default=default_access)):
                    attr_obj.delete()
            elif not attr_obj and raise_exception:
                raise AttributeError
        self._recache()

    def clear(self, category=None, accessing_obj=None, default_access=True):
        """
        Remove all Attributes on this object. If accessing_obj is
        given, check the 'attredit' lock on each Attribute before
        continuing. If not given, skip check.
        """
        if self._cache is None or not _TYPECLASS_AGGRESSIVE_CACHE:
            self._recache()
        if accessing_obj:
            [attr.delete() for attr in self._cache.values()
             if attr.access(accessing_obj, self._attredit, default=default_access)]
        else:
            [attr.delete() for attr in self._cache.values()]
        self._recache()

    def all(self, accessing_obj=None, default_access=True):
        """
        Return all Attribute objects on this object.

        If accessing_obj is given, check the "attrread" lock on
        each attribute before returning them. If not given, this
        check is skipped.
        """
        if self._cache is None or not _TYPECLASS_AGGRESSIVE_CACHE:
            self._recache()
        attrs = sorted(self._cache.values(), key=lambda o: o.id)
        if accessing_obj:
            return [attr for attr in attrs
                    if attr.access(accessing_obj, self._attredit, default=default_access)]
        else:
            return attrs


class NickHandler(AttributeHandler):
    """
    Handles the addition and removal of Nicks
    (uses Attributes' strvalue and category fields)

    Nicks are stored as Attributes
    with categories nick_<nicktype>
    """
    _attrtype = "nick"

    def has(self, key, category="inputline"):
        return super(NickHandler, self).has(key, category=category)

    def get(self, key=None, category="inputline", **kwargs):
        "Get the replacement value matching the given key and category"
        return super(NickHandler, self).get(key=key, category=category, strattr=True, **kwargs)

    def add(self, key, replacement, category="inputline", **kwargs):
        "Add a new nick"
        super(NickHandler, self).add(key, replacement, category=category, strattr=True, **kwargs)

    def remove(self, key, category="inputline", **kwargs):
        "Remove Nick with matching category"
        super(NickHandler, self).remove(key, category=category, **kwargs)

    def nickreplace(self, raw_string, categories=("inputline", "channel"), include_player=True):
        "Replace entries in raw_string with nick replacement"
        raw_string
        obj_nicks, player_nicks = [], []
        for category in make_iter(categories):
            obj_nicks.extend([n for n in make_iter(self.get(category=category, return_obj=True)) if n])
        if include_player and self.obj.has_player:
            for category in make_iter(categories):
                player_nicks.extend([n for n in make_iter(self.obj.player.nicks.get(category=category, return_obj=True)) if n])
        for nick in obj_nicks + player_nicks:
            # make a case-insensitive match here
            match = re.match(re.escape(nick.db_key), raw_string, re.IGNORECASE)
            if match:
                raw_string = raw_string.replace(match.group(), nick.db_strvalue, 1)
                break
        return raw_string


class NAttributeHandler(object):
    """
    This stand-alone handler manages non-database saving.
    It is similar to AttributeHandler and is used
    by the .ndb handler in the same way as .db does
    for the AttributeHandler.
    """
    def __init__(self, obj):
        "initialized on the object"
        self._store = {}
        self.obj = weakref.proxy(obj)

    def has(self, key):
        "Check if object has this attribute or not"
        return key in self._store

    def get(self, key):
        "Returns named key value"
        return self._store.get(key, None)

    def add(self, key, value):
        "Add new key and value"
        self._store[key] = value
        self.obj.set_recache_protection()

    def remove(self, key):
        "Remove key from storage"
        if key in self._store:
            del self._store[key]
        self.obj.set_recache_protection(self._store)

    def clear(self):
        "Remove all nattributes from handler"
        self._store = {}

    def all(self, return_tuples=False):
        "List all keys or (keys, values) stored, except _keys"
        if return_tuples:
            return [(key, value) for (key, value) in self._store.items() if not key.startswith("_")]
        return [key for key in self._store if not key.startswith("_")]


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
    db_key = models.CharField('key', max_length=255, null=True,
                              help_text="tag identifier", db_index=True)
    db_category = models.CharField('category', max_length=64, null=True,
                                   help_text="tag category", db_index=True)
    db_data = models.TextField('data', null=True, blank=True,
                               help_text="optional data field with extra information. This is not searched for.")
    # this is "objects.objectdb" etc
    db_model = models.CharField('model', max_length=32, null=True, help_text="database model to Tag", db_index=True)
    # this is None, alias or permission
    db_tagtype = models.CharField('tagtype', max_length=16, null=True, help_text="overall type of Tag", db_index=True)
    objects = managers.TagManager()

    class Meta:
        "Define Django meta options"
        verbose_name = "Tag"
        unique_together = (('db_key', 'db_category', 'db_tagtype'),)
        index_together = (('db_key', 'db_category', 'db_tagtype'),)

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
    _tagtype = None

    def __init__(self, obj):
        """
        Tags are stored internally in the TypedObject.db_tags m2m field
        with an tag.db_model based on the obj the taghandler is stored on
        and with a tagtype given by self.handlertype
        """
        self.obj = obj
        self._objid = obj.id
        self._model = obj.__class__.__name__.lower()
        self._cache = None

    def _recache(self):
        "Cache all tags of this object"
        query = {"%s__id" % self._model : self._objid,
                 "tag__db_tagtype" : self._tagtype}
        tagobjs = [conn.tag for conn in getattr(self.obj, self._m2m_fieldname).through.objects.filter(**query)]
        self._cache = dict(("%s-%s" % (to_str(tagobj.db_key).lower(),
                                       tagobj.db_category.lower() if tagobj.db_category else None),
                            tagobj) for tagobj in tagobjs)

    def add(self, tag=None, category=None, data=None):
        "Add a new tag to the handler. Tag is a string or a list of strings."
        if not tag:
            return
        for tagstr in make_iter(tag):
            if not tagstr:
                continue
            tagstr = tagstr.strip().lower()
            category = category.strip().lower() if category is not None else None
            data = str(data) if data is not None else None
            # this will only create tag if no matches existed beforehand (it
            # will overload data on an existing tag since that is not
            # considered part of making the tag unique)
            tagobj = Tag.objects.create_tag(key=tagstr, category=category, data=data,
                                            tagtype=self._tagtype)
            getattr(self.obj, self._m2m_fieldname).add(tagobj)
            if self._cache is None:
                self._recache()
            cachestring = "%s-%s" % (tagstr, category)
            self._cache[cachestring] = tagobj

    def get(self, key, category="", return_tagobj=False):
        """
        Get the tag for the given key or list of tags. If
        return_data=True, return the matching Tag objects instead.
        Returns a single tag if a unique match, otherwise a list
        """
        if self._cache is None or not _TYPECLASS_AGGRESSIVE_CACHE:
            self._recache()
        ret = []
        category = category.strip().lower() if category is not None else None
        searchkey = ["%s-%s" % (key.strip().lower(), category) if key is not None else None for key in make_iter(key)]
        ret = [val for val in (self._cache.get(keystr) for keystr in searchkey) if val]
        ret = [to_str(tag.db_data) for tag in ret] if return_tagobj else ret
        return ret[0] if len(ret) == 1 else ret

    def remove(self, key, category=None):
        "Remove a tag from the handler based ond key and category."
        for key in make_iter(key):
            if not (key or key.strip()):  # we don't allow empty tags
                continue
            tagstr = key.strip().lower()
            category = category.strip().lower() if category is not None else None

            # This does not delete the tag object itself. Maybe it should do
            # that when no objects reference the tag anymore (how to check)?
            tagobj = self.obj.db_tags.filter(db_key=tagstr, db_category=category)
            if tagobj:
                getattr(self.obj, self._m2m_fieldname).remove(tagobj[0])
        self._recache()

    def clear(self):
        "Remove all tags from the handler"
        getattr(self.obj, self._m2m_fieldname).clear()
        self._recache()

    def all(self, category=None, return_key_and_category=False):
        """
        Get all tags in this handler.
        If category is given, return only Tags with this category.  If
        return_keys_and_categories is set, return a list of tuples [(key, category), ...]
        """
        if self._cache is None or not _TYPECLASS_AGGRESSIVE_CACHE:
            self._recache()
        if category:
            category = category.strip().lower() if category is not None else None
            matches = [tag for tag in self._cache.values() if tag.db_category == category]
        else:
            matches = self._cache.values()

        if matches:
            matches = sorted(matches, key=lambda o: o.id)
            if return_key_and_category:
                # return tuple (key, category)
                return [(to_str(p.db_key), to_str(p.db_category)) for p in matches]
            else:
                return [to_str(p.db_key) for p in matches]
        return []

    def __str__(self):
        return ",".join(self.all())

    def __unicode(self):
        return u",".join(self.all())


class AliasHandler(TagHandler):
    _tagtype = "alias"


class PermissionHandler(TagHandler):
    _tagtype = "permission"


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
    # These databse fields are all accessed and set using their corresponding
    # properties, named same as the field, but without the db_* prefix
    # (no separate save() call is needed)

    # Main identifier of the object, for searching. Is accessed with self.key
    # or self.name
    db_key = models.CharField('key', max_length=255, db_index=True)
    # This is the python path to the type class this object is tied to the
    # typeclass is what defines what kind of Object this is)
    db_typeclass_path = models.CharField('typeclass', max_length=255, null=True,
            help_text="this defines what 'type' of entity this is. This variable holds a Python path to a module with a valid Evennia Typeclass.")
    # Creation date. This is not changed once the object is created.
    db_date_created = models.DateTimeField('creation date', editable=False, auto_now_add=True)
    # Permissions (access these through the 'permissions' property)
    #db_permissions = models.CharField('permissions', max_length=255, blank=True,
    #     help_text="a comma-separated list of text strings checked by
    # in-game locks. They are often used for hierarchies, such as letting a Player have permission 'Wizards', 'Builders' etc. Character objects use 'Players' by default. Most other objects don't have any permissions.")
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
        super(TypedObject, self).__init__(*args, **kwargs)
        _SA(self, "dbobj", self)   # this allows for self-reference

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

    # the latest error string will be stored here for accessing methods to access.
    # It is set by _display_errmsg, which will print to log if error happens
    # during server startup.
    typeclass_last_errmsg = ""

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
            # where '*' is either OBJECT, SCRIPT or PLAYER depending on the
            # typed entities).
            typeclass_paths = [path] + ["%s.%s" % (prefix, path)
                                    for prefix in _GA(self, '_typeclass_paths')]

            for tpath in typeclass_paths:

                # try to import and analyze the result
                typeclass = _GA(self, "_path_import")(tpath)
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
                elif typeclass:
                    errstring += "\n%s" % typeclass.strip()    # this will hold a growing error message.
            if not errstring:
                errstring = "\nMake sure the path is set correctly. Paths tested:\n"
                errstring += ", ".join(typeclass_paths)
            errstring += "\nTypeclass code was not found or failed to load."
        # If we reach this point we couldn't import any typeclasses. Return
        # default. It's up to the calling method to use e.g. self.is_typeclass()
        # to detect that the result is not the one asked for.
        _GA(self, "_display_errmsg")(errstring.strip())
        return _GA(self, "_get_default_typeclass")(cache=False, silent=False, save=False)

    #@typeclass.deleter
    def __typeclass_del(self):
        "Deleter. Disallow 'del self.typeclass'"
        raise Exception("The typeclass property should never be deleted, only changed in-place!")

    # typeclass property
    typeclass = property(__typeclass_get, fdel=__typeclass_del)


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
            module = __import__(modpath, fromlist=["none"])
            return module.__dict__[class_name]
        except ImportError:
            trc = sys.exc_traceback
            if not trc.tb_next:
                # we separate between not finding the module, and finding
                # a buggy one.
                pass
                #errstring = "Typeclass not found trying path '%s'." % path
            else:
                # a bug in the module is reported normally.
                trc = traceback.format_exc().strip()
                errstring = "\n%sError importing '%s'." % (trc, path)
        except (ValueError, TypeError):
            errstring = "Malformed typeclass path '%s'." % path
        except KeyError:
            errstring = "No class '%s' was found in module '%s'."
            errstring = errstring % (class_name, modpath)
        except Exception:
            trc = traceback.format_exc().strip()
            errstring = "\n%sException importing '%s'." % (trc, path)
        # return the error.
        return errstring

    def _display_errmsg(self, message):
        """
        Helper function to display error.
        """
        _SA(self, "typeclass_last_errmsg", message)
        if ServerConfig.objects.conf("server_starting_mode"):
            print message
        else:
            logger.log_errmsg(message)
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
            # fall back to hardcoded core class which is wrong for e.g.
            # scripts/players etc.
            failpath = defpath
            defpath = "src.objects.objects.Object"
            typeclass = _GA(self, "_path_import")(defpath)
            if not silent:
                #errstring = "  %s\n%s" % (typeclass, errstring)
                errstring = "  Default class '%s' failed to load." % failpath
                errstring += "\n  Using Evennia's default root '%s'." % defpath
                _GA(self, "_display_errmsg")(errstring.strip())
        if not callable(typeclass):
            # if this is still giving an error, Evennia is wrongly
            # configured or buggy
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

    def is_typeclass(self, typeclass, exact=True):
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
        typeclasses = [typeclass] + ["%s.%s" % (path, typeclass)
                                     for path in _GA(self, "_typeclass_paths")]
        if exact:
            current_path = _GA(self.typeclass, "path") #"_GA(self, "_cached_db_typeclass_path")
            return typeclass and any((current_path == typec for typec in typeclasses))
        else:
            # check parent chain
            return any((cls for cls in self.typeclass.__class__.mro()
                        if any(("%s.%s" % (_GA(cls, "__module__"),
                                _GA(cls, "__name__")) == typec
                                    for typec in typeclasses))))

    #
    # Object manipulation methods
    #

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

        if inherits_from(self, "src.scripts.models.ScriptDB"):
            if self.interval > 0:
                raise RuntimeError("Cannot use swap_typeclass on time-dependent " \
                                   "Script '%s'.\nStop and start a new Script of the " \
                                   "right type instead." % self.key)

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
                    self.attributes.remove(attr)
                for nattr in clean_attributes:
                    if hasattr(self.ndb, nattr):
                        self.nattributes.remove(nattr)
            else:
                #print "deleting attrs ..."
                self.attributes.clear()
                self.nattributes.clear()

        if run_start_hooks:
            # run hooks for this new typeclass
            if inherits_from(self, "src.objects.models.ObjectDB"):
                new_typeclass.basetype_setup()
                new_typeclass.at_object_creation()
            elif inherits_from(self, "src.players.models.PlayerDB"):
                new_typeclass.basetype_setup()
                new_typeclass.at_player_creation()
            elif inherits_from(self, "src.scripts.models.ScriptDB"):
                new_typeclass.at_script_creation()
                new_typeclass.start()
            elif inherits_from(self, "src.channels.models.Channel"):
                # channels do no initial setup
                pass

        return True

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

    _is_deleted = False # this is checked by db_* wrappers

    def delete(self):
        "Cleaning up handlers on the typeclass level"
        global TICKER_HANDLER
        if not TICKER_HANDLER:
            from src.scripts.tickerhandler import TICKER_HANDLER
        TICKER_HANDLER.remove(self) # removes objects' all ticker subscriptions
        _GA(self, "permissions").clear()
        _GA(self, "attributes").clear()
        _GA(self, "aliases").clear()
        if hasattr(self, "nicks"):
            _GA(self, "nicks").clear()
        _SA(self, "_cached_typeclass", None)
        _GA(self, "flush_from_cache")()

        # scrambling properties
        self.delete = self._deleted
        self._is_deleted = True
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
            class DbHolder(object):
                "Holder for allowing property access of attributes"
                def __init__(self, obj):
                    _SA(self, "attrhandler", _GA(obj, "attributes"))

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
            class NDbHolder(object):
                "Holder for allowing property access of attributes"
                def __init__(self, obj):
                    _SA(self, "nattrhandler", _GA(obj, "nattributes"))

                def __getattribute__(self, attrname):
                    if attrname == 'all':
                        # we allow to overload our default .all
                        attr = _GA(self, "nattrhandler").get("all")
                        if attr:
                            return attr
                        return _GA(self, 'all')
                    return _GA(self, "nattrhandler").get(attrname)

                def __setattr__(self, attrname, value):
                    _GA(self, "nattrhandler").add(attrname, value)

                def __delattr__(self, attrname):
                    _GA(self, "nattrhandler").remove(attrname)

                def get_all(self):
                    return _GA(self, "nattrhandler").all()
                all = property(get_all)
            self._ndb_holder = NDbHolder(self)
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

#    #
#    # ***** DEPRECATED METHODS BELOW   *******
#    #
#
#    #
#    # Full attr_obj attributes. You usually access these
#    # through the obj.db.attrname method.
#
#    # Helper methods for attr_obj attributes
#
#    def has_attribute(self, attribute_name):
#        """
#        See if we have an attribute set on the object.
#
#        attribute_name: (str) The attribute's name.
#        """
#        logger.log_depmsg("obj.has_attribute() is deprecated. Use obj.attributes.has().")
#        return _GA(self, "attributes").has(attribute_name)
#
#    def set_attribute(self, attribute_name, new_value=None, lockstring=""):
#        """
#        Sets an attribute on an object. Creates the attribute if need
#        be.
#
#        attribute_name: (str) The attribute's name.
#        new_value: (python obj) The value to set the attribute to. If this is not
#                                a str, the object will be stored as a pickle.
#        lockstring - this sets an access restriction on the attribute object. Note that
#                     this is normally NOT checked - use the secureattr() access method
#                     below to perform access-checked modification of attributes. Lock
#                     types checked by secureattr are 'attrread','attredit','attrcreate'.
#        """
#        logger.log_depmsg("obj.set_attribute() is deprecated. Use obj.db.attr=value or obj.attributes.add().")
#        _GA(self, "attributes").add(attribute_name, new_value, lockstring=lockstring)
#
#    def get_attribute_obj(self, attribute_name, default=None):
#        """
#        Get the actual attribute object named attribute_name
#        """
#        logger.log_depmsg("obj.get_attribute_obj() is deprecated. Use obj.attributes.get(..., return_obj=True)")
#        return _GA(self, "attributes").get(attribute_name, default=default, return_obj=True)
#
#    def get_attribute(self, attribute_name, default=None, raise_exception=False):
#        """
#        Returns the value of an attribute on an object. You may need to
#        type cast the returned value from this function since the attribute
#        can be of any type. Returns default if no match is found.
#
#        attribute_name: (str) The attribute's name.
#        default: What to return if no attribute is found
#        raise_exception (bool) - raise an exception if no object exists instead of returning default.
#        """
#        logger.log_depmsg("obj.get_attribute() is deprecated. Use obj.db.attr or obj.attributes.get().")
#        return _GA(self, "attributes").get(attribute_name, default=default, raise_exception=raise_exception)
#
#    def del_attribute(self, attribute_name, raise_exception=False):
#        """
#        Removes an attribute entirely.
#
#        attribute_name: (str) The attribute's name.
#        raise_exception (bool) - raise exception if attribute to delete
#                                 could not be found
#        """
#        logger.log_depmsg("obj.del_attribute() is deprecated. Use del obj.db.attr or obj.attributes.remove().")
#        _GA(self, "attributes").remove(attribute_name, raise_exception=raise_exception)
#
#    def get_all_attributes(self):
#        """
#        Returns all attributes defined on the object.
#        """
#        logger.log_depmsg("obj.get_all_attributes() is deprecated. Use obj.db.all() or obj.attributes.all().")
#        return _GA(self, "attributes").all()
#
#    def attr(self, attribute_name=None, value=None, delete=False):
#        """
#        This is a convenient wrapper for
#        get_attribute, set_attribute, del_attribute
#        and get_all_attributes.
#        If value is None, attr will act like
#        a getter, otherwise as a setter.
#        set delete=True to delete the named attribute.
#
#        Note that you cannot set the attribute
#        value to None using this method. Use set_attribute.
#        """
#        logger.log_depmsg("obj.attr() is deprecated. Use handlers obj.db or obj.attributes.")
#        if attribute_name is None:
#            # act as a list method
#            return _GA(self, "attributes").all()
#        elif delete is True:
#            _GA(self, "attributes").remove(attribute_name)
#        elif value is None:
#            # act as a getter.
#            return _GA(self, "attributes").get(attribute_name)
#        else:
#            # act as a setter
#            self._GA(self, "attributes").add(attribute_name, value)
#
#    def secure_attr(self, accessing_object, attribute_name=None, value=None, delete=False,
#                    default_access_read=True, default_access_edit=True, default_access_create=True):
#        """
#        This is a version of attr that requires the accessing object
#        as input and will use that to check eventual access locks on
#        the Attribute before allowing any changes or reads.
#
#        In the cases when this method wouldn't return, it will return
#        True for a successful operation, None otherwise.
#
#        locktypes checked on the Attribute itself:
#            attrread - control access to reading the attribute value
#            attredit - control edit/delete access
#        locktype checked on the object on which the Attribute is/will be stored:
#            attrcreate - control attribute create access (this is checked *on the object*  not on the Attribute!)
#
#        default_access_* defines which access is assumed if no
#        suitable lock is defined on the Atttribute.
#
#        """
#        logger.log_depmsg("obj.secure_attr() is deprecated. Use obj.attributes methods, giving accessing_obj keyword.")
#        if attribute_name is None:
#            return _GA(self, "attributes").all(accessing_obj=accessing_object, default_access=default_access_read)
#        elif delete is True:
#            # act as deleter
#            _GA(self, "attributes").remove(attribute_name, accessing_obj=accessing_object, default_access=default_access_edit)
#        elif value is None:
#            # act as getter
#            return _GA(self, "attributes").get(attribute_name, accessing_obj=accessing_object, default_access=default_access_read)
#        else:
#            # act as setter
#            attr = _GA(self, "attributes").get(attribute_name, return_obj=True)
#            if attr:
#               # attribute already exists
#                _GA(self, "attributes").add(attribute_name, value, accessing_obj=accessing_object, default_access=default_access_edit)
#            else:
#                # creating a new attribute - check access on storing object!
#                _GA(self, "attributes").add(attribute_name, value, accessing_obj=accessing_object, default_access=default_access_create)
#
#    def nattr(self, attribute_name=None, value=None, delete=False):
#        """
#        This allows for assigning non-persistent data on the object using
#        a method call. Will return None if trying to access a non-existing property.
#        """
#        logger.log_depmsg("obj.nattr() is deprecated. Use obj.nattributes instead.")
#        if attribute_name is None:
#            # act as a list method
#            if callable(self.ndb.all):
#                return self.ndb.all()
#            else:
#                return [val for val in self.ndb.__dict__.keys()
#                        if not val.startswith['_']]
#        elif delete is True:
#            if hasattr(self.ndb, attribute_name):
#                _DA(_GA(self, "ndb"), attribute_name)
#        elif value is None:
#            # act as a getter.
#            if hasattr(self.ndb, attribute_name):
#                _GA(_GA(self, "ndb"), attribute_name)
#            else:
#                return None
#        else:
#            # act as a setter
#            _SA(self.ndb, attribute_name, value)
#
#

