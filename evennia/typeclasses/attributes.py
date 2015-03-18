"""
Attributes are arbitrary data stored on objects. Attributes supports
both pure-string values and pickled arbitrary data.

Attributes are also used to implement Nicks. This module also contains
the Attribute- and NickHandlers as well as the `NAttributeHandler`,
which is a non-db version of Attributes.


"""
import re
import weakref

from django.db import models
from django.conf import settings
from django.utils.encoding import smart_str

from evennia.locks.lockhandler import LockHandler
from evennia.utils.idmapper.models import SharedMemoryModel
from evennia.utils.dbserialize import to_pickle, from_pickle
from evennia.utils.picklefield import PickledObjectField
from evennia.utils.utils import lazy_property, to_str, make_iter

_TYPECLASS_AGGRESSIVE_CACHE = settings.TYPECLASS_AGGRESSIVE_CACHE

#------------------------------------------------------------
#
#   Attributes
#
#------------------------------------------------------------

class Attribute(SharedMemoryModel):
    """
    Attributes are things that are specific to different types of objects. For
    example, a drink container needs to store its fill level, whereas an exit
    needs to store its open/closed/locked/unlocked state. These are done via
    attributes, rather than making different classes for each object type and
    storing them directly. The added benefit is that we can add/remove
    attributes on the fly as we like.

    The Attribute class defines the following properties:
        key - primary identifier.
        lock_storage - perm strings.
        obj - which object the attribute is defined on.
        date_created - when the attribute was created.
        value - the data stored in the attribute, in pickled form
                using wrappers to be able to store/retrieve models.
        strvalue - string-only data. This data is not pickled and is
                    thus faster to search for in the database.
        category - optional character string for grouping the Attribute.

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
                  "natural key like 'objects.dbobject'). You should not change "
                  "this value unless you know what you are doing.")
    # subclass of Attribute (None or nick)
    db_attrtype = models.CharField(
        'attrtype', max_length=16, db_index=True, blank=True, null=True,
        help_text="Subclass of Attribute (None or nick)")
    # time stamp
    db_date_created = models.DateTimeField(
        'date_created', editable=False, auto_now_add=True)

    # Database manager
    #objects = managers.AttributeManager()

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
        Getter. Allows for `value = self.value`.
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
        return smart_str("%s(%s)" % (self.db_key, self.id))

    def __unicode__(self):
        return u"%s(%s)" % (self.db_key,self.id)

    def access(self, accessing_obj, access_type='read', default=False, **kwargs):
        """
        Determines if another object has permission to access.

        Args:
            accessing_obj (object): object trying to access this one.
            access_type (optional): type of access sought.
            default (optional): what to return if no lock of access_type was found

        Kwargs:
            **kwargs: passed to `at_access` hook along with `result`.

        Returns:
            result:
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
        self._model = to_str(obj.__dbclass__.__name__.lower())
        self._cache = None

    def _recache(self):
        "Cache all attributes of this object"
        query = {"%s__id" % self._model : self._objid,
                 "attribute__db_attrtype" : self._attrtype}
        attrs = [conn.attribute for conn in getattr(self.obj, self._m2m_fieldname).through.objects.filter(**query)]
        self._cache = dict(("%s-%s" % (to_str(attr.db_key).lower(),
                                       attr.db_category.lower() if attr.db_category else None),
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
        `strattr` will cause the string-only value field instead of the normal
        pickled field data. Use to get back values from Attributes added with
        the `strattr` keyword.

        If `return_obj=True`, return the matching Attribute object
        instead. Returns `default` if no matches (or [ ] if `key` was a list
        with no matches). If `raise_exception=True`, failure to find a
        match will raise `AttributeError` instead.

        If `accessing_obj` is given, its `attrread` permission lock will be
        checked before displaying each looked-after Attribute. If no
        `accessing_obj` is given, no check will be done.
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
        Add attribute to object, with optional `lockstring`.

        If `strattr` is set, the `db_strvalue` field will be used (no pickling).
        Use the `get()` method with the `strattr` keyword to get it back.

        If `accessing_obj` is given, `self.obj`'s  `attrcreate` lock access
        will be checked against it. If no `accessing_obj` is given, no check
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
        Batch-version of `add()`. This is more efficient than
        repeat-calling add.

        `key` and `value` must be sequences of the same length, each
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
        """
        Remove attribute or a list of attributes from object.

        If `accessing_obj` is given, will check against the `attredit` lock.
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
        Remove all Attributes on this object. If `accessing_obj` is
        given, check the `attredit` lock on each Attribute before
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

        If `accessing_obj` is given, check the `attrread` lock on
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
    (uses Attributes' `strvalue` and `category` fields)

    Nicks are stored as Attributes
    with categories `nick_<nicktype>`
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
    It is similar to `AttributeHandler` and is used
    by the `.ndb` handler in the same way as `.db` does
    for the `AttributeHandler`.
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
