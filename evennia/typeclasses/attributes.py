"""
Attributes are arbitrary data stored on objects. Attributes supports
both pure-string values and pickled arbitrary data.

Attributes are also used to implement Nicks. This module also contains
the Attribute- and NickHandlers as well as the `NAttributeHandler`,
which is a non-db version of Attributes.


"""
import fnmatch
import re
from collections import defaultdict

from django.conf import settings
from django.db import models
from django.utils.encoding import smart_str

from evennia.locks.lockhandler import LockHandler
from evennia.utils.dbserialize import from_pickle, to_pickle
from evennia.utils.idmapper.models import SharedMemoryModel
from evennia.utils.picklefield import PickledObjectField
from evennia.utils.utils import is_iter, lazy_property, make_iter, to_str

_TYPECLASS_AGGRESSIVE_CACHE = settings.TYPECLASS_AGGRESSIVE_CACHE

# -------------------------------------------------------------
#
#   Attributes
#
# -------------------------------------------------------------


class IAttribute:
    """
    Attributes are things that are specific to different types of objects. For
    example, a drink container needs to store its fill level, whereas an exit
    needs to store its open/closed/locked/unlocked state. These are done via
    attributes, rather than making different classes for each object type and
    storing them directly. The added benefit is that we can add/remove
    attributes on the fly as we like.

    The Attribute class defines the following properties:
     - key (str): Primary identifier.
     - lock_storage (str): Perm strings.
     - model (str): A string defining the model this is connected to. This
        is a natural_key, like "objects.objectdb"
     - date_created (datetime): When the attribute was created.
     - value (any): The data stored in the attribute, in pickled form
        using wrappers to be able to store/retrieve models.
     - strvalue (str): String-only data. This data is not pickled and
        is thus faster to search for in the database.
     - category (str): Optional character string for grouping the
        Attribute.

    This class is an API/Interface/Abstract base class; do not instantiate it directly.
    """

    @lazy_property
    def locks(self):
        return LockHandler(self)

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

    def __lock_storage_del(self):
        self.db_lock_storage = ""

    lock_storage = property(__lock_storage_get, __lock_storage_set, __lock_storage_del)

    def access(self, accessing_obj, access_type="read", default=False, **kwargs):
        """
        Determines if another object has permission to access.

        Args:
            accessing_obj (object): Entity trying to access this one.
            access_type (str, optional): Type of access sought, see
                the lock documentation.
            default (bool, optional): What result to return if no lock
                of access_type was found. The default, `False`, means a lockdown
                policy, only allowing explicit access.
            kwargs (any, optional): Not used; here to make the API consistent with
                other access calls.

        Returns:
            result (bool): If the lock was passed or not.

        """
        result = self.locks.check(accessing_obj, access_type=access_type, default=default)
        return result

    #
    #
    # Attribute methods
    #
    #

    def __str__(self):
        return smart_str("%s(%s)" % (self.db_key, self.id))

    def __repr__(self):
        return "%s(%s)" % (self.db_key, self.id)


class InMemoryAttribute(IAttribute):
    """
    This Attribute is used purely for NAttributes/NAttributeHandler. It has no database backend.

    """

    # Primary Key has no meaning for an InMemoryAttribute. This merely serves to satisfy other code.

    def __init__(self, pk, **kwargs):
        """
        Create an Attribute that exists only in Memory.

        Args:
            pk (int): This is a fake 'primary key' / id-field. It doesn't actually have to be
                unique, but is fed an incrementing number from the InMemoryBackend by default. This
                is needed only so Attributes can be sorted. Some parts of the API also see the lack
                of a .pk field as a sign that the Attribute was deleted.
            **kwargs: Other keyword arguments are used to construct the actual Attribute.

        """
        self.id = pk
        self.pk = pk

        # Copy all kwargs to local properties. We use db_ for compatability here.
        for key, value in kwargs.items():
            # Value and locks are special. We must call the wrappers.
            if key == "value":
                self.value = value
            elif key == "lock_storage":
                self.lock_storage = value
            else:
                setattr(self, f"db_{key}", value)

    # value property (wraps db_value)
    def __value_get(self):
        return self.db_value

    def __value_set(self, new_value):
        self.db_value = new_value

    def __value_del(self):
        pass

    value = property(__value_get, __value_set, __value_del)


class AttributeProperty:
    """
    Attribute property descriptor. Allows for specifying Attributes as Django-like 'fields'
    on the class level. Note that while one can set a lock on the Attribute,
    there is no way to *check* said lock when accessing via the property - use
    the full AttributeHandler if you need to do access checks.

    Example:
    ::

        class Character(DefaultCharacter):
            foo = AttributeProperty(default="Bar")

    """

    attrhandler_name = "attributes"

    def __init__(self, default=None, category=None, strattr=False, lockstring="", autocreate=True):
        """
        Initialize an Attribute as a property descriptor.

        Keyword Args:
            default (any): A default value if the attr is not set.
            category (str): The attribute's category. If unset, use class default.
            strattr (bool): If set, this Attribute *must* be a simple string, and will be
                stored more efficiently.
            lockstring (str): This is not itself useful with the property, but only if
                using the full AttributeHandler.get(accessing_obj=...) to access the
                Attribute.
            autocreate (bool): True by default; this means Evennia makes sure to create a new
                copy of the Attribute (with the default value) whenever a new object with this
                property is created. If `False`, no Attribute will be created until the property
                is explicitly assigned a value. This makes it more efficient while it retains
                its default (there's no db access), but without an actual Attribute generated,
                one cannot access it via .db, the AttributeHandler or see it with `examine`.

        """
        self._default = default
        self._category = category
        self._strattr = strattr
        self._lockstring = lockstring
        self._autocreate = autocreate
        self._key = ""

    @property
    def _default(self):
        """
        Tries returning a new instance of default if callable.

        """
        if callable(self.__default):
            return self.__default()

        return self.__default

    @_default.setter
    def _default(self, value):
        self.__default = value

    def __set_name__(self, cls, name):
        """
        Called when descriptor is first assigned to the class. It is called with
        the name of the field.

        """
        self._key = name

    def __get__(self, instance, owner):
        """
        Called when the attrkey is retrieved from the instance.

        """
        value = self._default
        try:
            value = self.at_get(
                getattr(instance, self.attrhandler_name).get(
                    key=self._key,
                    default=self._default,
                    category=self._category,
                    strattr=self._strattr,
                    raise_exception=self._autocreate,
                ),
                instance,
            )
        except AttributeError:
            if self._autocreate:
                # attribute didn't exist and autocreate is set
                self.__set__(instance, self._default)
            else:
                raise
        return value

    def __set__(self, instance, value):
        """
        Called when assigning to the property (and when auto-creating an Attribute).

        """
        (
            getattr(instance, self.attrhandler_name).add(
                self._key,
                self.at_set(value, instance),
                category=self._category,
                lockstring=self._lockstring,
                strattr=self._strattr,
            )
        )

    def __delete__(self, instance):
        """
        Called when running `del` on the property. Will remove/clear the Attribute. Note that
        the Attribute will be recreated next retrieval unless the AttributeProperty is also
        removed in code!

        """
        getattr(instance, self.attrhandler_name).remove(key=self._key, category=self._category)

    def at_set(self, value, obj):
        """
        The value to set is passed through the method. It can be used to customize/validate
        the input in a custom child class.

        Args:
            value (any): The value about to the stored in this Attribute.
            obj (object): Object the attribute is attached to

        Returns:
            any: The value to store.

        Raises:
            AttributeError: If the value is invalid to store.

        """
        return value

    def at_get(self, value, obj):
        """
        The value returned from the Attribute is passed through this method. It can be used
        to react to the retrieval or modify the result in some way.

        Args:
            value (any): Value returned from the Attribute.
            obj (object): Object the attribute is attached to

        Returns:
            any: The value to return to the caller.

        """
        return value


class NAttributeProperty(AttributeProperty):
    """
    NAttribute property descriptor. Allows for specifying NAttributes as Django-like 'fields'
    on the class level.

    Example:
    ::

        class Character(DefaultCharacter):
            foo = NAttributeProperty(default="Bar")

    """

    attrhandler_name = "nattributes"


class Attribute(IAttribute, SharedMemoryModel):
    """
    This attribute is stored via Django. Most Attributes will be using this class.

    """

    #
    # Attribute Database Model setup
    #
    # These database fields are all set using their corresponding properties,
    # named same as the field, but without the db_* prefix.
    db_key = models.CharField("key", max_length=255, db_index=True)
    db_value = PickledObjectField(
        "value",
        null=True,
        help_text="The data returned when the attribute is accessed. Must be "
        "written as a Python literal if editing through the admin "
        "interface. Attribute values which are not Python literals "
        "cannot be edited through the admin interface.",
    )
    db_strvalue = models.TextField(
        "strvalue", null=True, blank=True, help_text="String-specific storage for quick look-up"
    )
    db_category = models.CharField(
        "category",
        max_length=128,
        db_index=True,
        blank=True,
        null=True,
        help_text="Optional categorization of attribute.",
    )
    # Lock storage
    db_lock_storage = models.TextField(
        "locks", blank=True, help_text="Lockstrings for this object are stored here."
    )
    db_model = models.CharField(
        "model",
        max_length=32,
        db_index=True,
        blank=True,
        null=True,
        help_text="Which model of object this attribute is attached to (A "
        "natural key like 'objects.objectdb'). You should not change "
        "this value unless you know what you are doing.",
    )
    # subclass of Attribute (None or nick)
    db_attrtype = models.CharField(
        "attrtype",
        max_length=16,
        db_index=True,
        blank=True,
        null=True,
        help_text="Subclass of Attribute (None or nick)",
    )
    # time stamp
    db_date_created = models.DateTimeField("date_created", editable=False, auto_now_add=True)

    # Database manager
    # objects = managers.AttributeManager()

    class Meta:
        "Define Django meta options"
        verbose_name = "Attribute"

    # Wrapper properties to easily set database fields. These are
    # @property decorators that allows to access these fields using
    # normal python operations (without having to remember to save()
    # etc). So e.g. a property 'attr' has a get/set/del decorator
    # defined that allows the user to do self.attr = value,
    # value = self.attr and del self.attr respectively (where self
    # is the object in question).

    # lock_storage wrapper. Overloaded for saving to database.
    def __lock_storage_get(self):
        return self.db_lock_storage

    def __lock_storage_set(self, value):
        self.db_lock_storage = value
        self.save(update_fields=["db_lock_storage"])

    def __lock_storage_del(self):
        self.db_lock_storage = ""
        self.save(update_fields=["db_lock_storage"])

    lock_storage = property(__lock_storage_get, __lock_storage_set, __lock_storage_del)

    # value property (wraps db_value)
    @property
    def value(self):
        """
        Getter. Allows for `value = self.value`.
        We cannot cache here since it makes certain cases (such
        as storing a dbobj which is then deleted elsewhere) out-of-sync.
        The overhead of unpickling seems hard to avoid.
        """
        return from_pickle(self.db_value, db_obj=self)

    @value.setter
    def value(self, new_value):
        """
        Setter. Allows for self.value = value. We cannot cache here,
        see self.__value_get.
        """
        self.db_value = to_pickle(new_value)
        self.save(update_fields=["db_value"])

    @value.deleter
    def value(self):
        """Deleter. Allows for del attr.value. This removes the entire attribute."""
        self.delete()


#
# Handlers making use of the Attribute model
#


class IAttributeBackend:
    """
    Abstract interface for the backends used by the Attribute Handler.

    All Backends must implement this base class.
    """

    _attrcreate = "attrcreate"
    _attredit = "attredit"
    _attrread = "attrread"
    _attrclass = None

    def __init__(self, handler, attrtype):
        self.handler = handler
        self.obj = handler.obj
        self._attrtype = attrtype
        self._objid = handler.obj.id
        self._cache = {}
        # store category names fully cached
        self._catcache = {}
        # full cache was run on all attributes
        self._cache_complete = False

    def query_all(self):
        """
        Fetch all Attributes from this object.

        Returns:
            attrlist (list): A list of Attribute objects.
        """
        raise NotImplementedError()

    def query_key(self, key, category):
        """

        Args:
            key (str): The key of the Attribute being searched for.
            category (str or None): The category of the desired Attribute.

        Returns:
            attribute (IAttribute): A single Attribute.
        """
        raise NotImplementedError()

    def query_category(self, category):
        """
        Returns every matching Attribute as a list, given a category.

        This method calls up whatever storage the backend uses.

        Args:
            category (str or None): The category to query.

        Returns:
            attrs (list): The discovered Attributes.
        """
        raise NotImplementedError()

    def _full_cache(self):
        """Cache all attributes of this object"""
        if not _TYPECLASS_AGGRESSIVE_CACHE:
            return
        attrs = self.query_all()
        self._cache = {
            f"{to_str(attr.key).lower()}-{attr.category.lower() if attr.category else None}": attr
            for attr in attrs
        }
        self._cache_complete = True

    def _get_cache_key(self, key, category):
        """
        Fetch cache key.

        Args:
            key (str): The key of the Attribute being searched for.
            category (str or None): The category of the desired Attribute.

        Returns:
            attribute (IAttribute): A single Attribute.
        """
        cachekey = "%s-%s" % (key, category)
        cachefound = False
        try:
            attr = _TYPECLASS_AGGRESSIVE_CACHE and self._cache[cachekey]
            cachefound = True
        except KeyError:
            attr = None

        if attr and (not hasattr(attr, "pk") and attr.pk is None):
            # clear out Attributes deleted from elsewhere. We must search this anew.
            attr = None
            cachefound = False
            del self._cache[cachekey]
        if cachefound and _TYPECLASS_AGGRESSIVE_CACHE:
            if attr:
                return [attr]  # return cached entity
            else:
                return []  # no such attribute: return an empty list
        else:
            conn = self.query_key(key, category)
            if conn:
                attr = conn[0].attribute
                if _TYPECLASS_AGGRESSIVE_CACHE:
                    self._cache[cachekey] = attr
                return [attr] if attr.pk else []
            else:
                # There is no such attribute. We will explicitly save that
                # in our cache to avoid firing another query if we try to
                # retrieve that (non-existent) attribute again.
                if _TYPECLASS_AGGRESSIVE_CACHE:
                    self._cache[cachekey] = None
                return []

    def _get_cache_category(self, category):
        """
        Retrieves Attribute list (by category) from cache.

        Args:
            category (str or None): The category to query.

        Returns:
            attrs (list): The discovered Attributes.
        """
        catkey = "-%s" % category
        if _TYPECLASS_AGGRESSIVE_CACHE and catkey in self._catcache:
            return [attr for key, attr in self._cache.items() if key.endswith(catkey) and attr]
        else:
            # we have to query to make this category up-date in the cache
            attrs = self.query_category(category)
            if _TYPECLASS_AGGRESSIVE_CACHE:
                for attr in attrs:
                    if attr.pk:
                        cachekey = "%s-%s" % (attr.key, category)
                        self._cache[cachekey] = attr
                # mark category cache as up-to-date
                self._catcache[catkey] = True
            return attrs

    def _get_cache(self, key=None, category=None):
        """
        Retrieve from cache or database (always caches)

        Args:
            key (str, optional): Attribute key to query for
            category (str, optional): Attribiute category

        Returns:
            args (list): Returns a list of zero or more matches
                found from cache or database.
        Notes:
            When given a category only, a search for all objects
            of that cateogory is done and the category *name* is
            stored. This tells the system on subsequent calls that the
            list of cached attributes of this category is up-to-date
            and that the cache can be queried for category matches
            without missing any.
            The TYPECLASS_AGGRESSIVE_CACHE=False setting will turn off
            caching, causing each attribute access to trigger a
            database lookup.

        """
        key = key.strip().lower() if key else None
        category = category.strip().lower() if category is not None else None
        if key:
            return self._get_cache_key(key, category)
        return self._get_cache_category(category)

    def get(self, key=None, category=None):
        """
        Frontend for .get_cache. Retrieves Attribute(s).

        Args:
            key (str, optional): Attribute key to query for
            category (str, optional): Attribiute category

        Returns:
            args (list): Returns a list of zero or more matches
                found from cache or database.
        """
        return self._get_cache(key, category)

    def _set_cache(self, key, category, attr_obj):
        """
        Update cache.

        Args:
            key (str): A cleaned key string
            category (str or None): A cleaned category name
            attr_obj (IAttribute): The newly saved attribute

        """
        if not _TYPECLASS_AGGRESSIVE_CACHE:
            return
        if not key:  # don't allow an empty key in cache
            return
        cachekey = "%s-%s" % (key, category)
        catkey = "-%s" % category
        self._cache[cachekey] = attr_obj
        # mark that the category cache is no longer up-to-date
        self._catcache.pop(catkey, None)
        self._cache_complete = False

    def _delete_cache(self, key, category):
        """
        Remove attribute from cache

        Args:
            key (str): A cleaned key string
            category (str or None): A cleaned category name

        """
        catkey = "-%s" % category
        if key:
            cachekey = "%s-%s" % (key, category)
            self._cache.pop(cachekey, None)
        else:
            self._cache = {
                key: attrobj
                for key, attrobj in list(self._cache.items())
                if not key.endswith(catkey)
            }
        # mark that the category cache is no longer up-to-date
        self._catcache.pop(catkey, None)
        self._cache_complete = False

    def reset_cache(self):
        """
        Reset cache from the outside.
        """
        self._cache_complete = False
        self._cache = {}
        self._catcache = {}

    def do_create_attribute(self, key, category, lockstring, value, strvalue):
        """
        Does the hard work of actually creating Attributes, whatever is needed.

        Args:
            key (str): The Attribute's key.
            category (str or None): The Attribute's category, or None
            lockstring (str): Any locks for the Attribute.
            value (obj): The Value of the Attribute.
            strvalue (bool): Signifies if this is a strvalue Attribute. Value MUST be a string or
                this will lead to Trouble. Ignored for InMemory attributes.

        Returns:
            attr (IAttribute): The new Attribute.
        """
        raise NotImplementedError()

    def create_attribute(self, key, category, lockstring, value, strvalue=False, cache=True):
        """
        Creates Attribute (using the class specified for the backend), (optionally) caches it, and
        returns it.

        This MUST actively save the Attribute to whatever database backend is used, AND
        call self.set_cache(key, category, new_attrobj)

        Args:
            key (str): The Attribute's key.
            category (str or None): The Attribute's category, or None
            lockstring (str): Any locks for the Attribute.
            value (obj): The Value of the Attribute.
            strvalue (bool): Signifies if this is a strvalue Attribute. Value MUST be a string or
                this will lead to Trouble. Ignored for InMemory attributes.
            cache (bool): Whether to cache the new Attribute

        Returns:
            attr (IAttribute): The new Attribute.
        """
        attr = self.do_create_attribute(key, category, lockstring, value, strvalue)
        if cache:
            self._set_cache(key, category, attr)
        return attr

    def do_update_attribute(self, attr, value, strvalue):
        """
        Simply sets a new Value to an Attribute.

        Args:
            attr (IAttribute): The Attribute being changed.
            value (obj): The Value for the Attribute.
            strvalue (bool): If True, `value` is expected to be a string.

        """
        raise NotImplementedError()

    def do_batch_update_attribute(self, attr_obj, category, lock_storage, new_value, strvalue):
        """
        Called opnly by batch add. For the database backend, this is a method
        of updating that can alter category and lock-storage.

        Args:
            attr_obj (IAttribute): The Attribute being altered.
            category (str or None): The attribute's (new) category.
            lock_storage (str): The attribute's new locks.
            new_value (obj): The Attribute's new value.
            strvalue (bool): Signifies if this is a strvalue Attribute. Value MUST be a string or
                this will lead to Trouble. Ignored for InMemory attributes.
        """
        raise NotImplementedError()

    def do_batch_finish(self, attr_objs):
        """
        Called after batch_add completed. Used for handling database operations
        and/or caching complications.

        Args:
            attr_objs (list of IAttribute): The Attributes created/updated thus far.

        """
        raise NotImplementedError()

    def batch_add(self, *args, **kwargs):
        """
        Batch-version of `.add()`. This is more efficient than repeat-calling
        `.add` when having many Attributes to add.

        Args:
             *args (tuple): Tuples of varying length representing the
                Attribute to add to this object. Supported tuples are

                - (key, value)
                - (key, value, category)
                - (key, value, category, lockstring)
                - (key, value, category, lockstring, default_access)

        Raises:
            RuntimeError: If trying to pass a non-iterable as argument.

        Notes:
            The indata tuple order matters, so if you want a lockstring but no
            category, set the category to `None`. This method does not have the
            ability to check editing permissions and is mainly used internally.
            It does not use the normal `self.add` but applies the Attributes
            directly to the database.

        """
        new_attrobjs = []
        strattr = kwargs.get("strattr", False)
        for tup in args:
            if not is_iter(tup) or len(tup) < 2:
                raise RuntimeError("batch_add requires iterables as arguments (got %r)." % tup)
            ntup = len(tup)
            keystr = str(tup[0]).strip().lower()
            new_value = tup[1]
            category = str(tup[2]).strip().lower() if ntup > 2 and tup[2] is not None else None
            lockstring = tup[3] if ntup > 3 else ""

            attr_objs = self._get_cache(keystr, category)

            if attr_objs:
                attr_obj = attr_objs[0]
                # update an existing attribute object
                self.do_batch_update_attribute(attr_obj, category, lockstring, new_value, strattr)
            else:
                new_attr = self.do_create_attribute(
                    keystr, category, lockstring, new_value, strvalue=strattr
                )
                new_attrobjs.append(new_attr)
        if new_attrobjs:
            self.do_batch_finish(new_attrobjs)

    def do_delete_attribute(self, attr):
        """
        Does the hard work of actually deleting things.

        Args:
            attr (IAttribute): The attribute to delete.
        """
        raise NotImplementedError()

    def delete_attribute(self, attr):
        """
        Given an Attribute, deletes it. Also remove it from cache.

        Args:
            attr (IAttribute): The attribute to delete.
        """
        if not attr:
            return
        self._delete_cache(attr.key, attr.category)
        self.do_delete_attribute(attr)

    def update_attribute(self, attr, value, strattr=False):
        """
        Simply updates an Attribute.

        Args:
            attr (IAttribute): The attribute to delete.
            value (obj): The new value.
            strattr (bool): If set, the `value` is a raw string.
        """
        self.do_update_attribute(attr, value, strattr)

    def do_batch_delete(self, attribute_list):
        """
        Given a list of attributes, deletes them all.
        The default implementation is fine, but this is overridable since some databases may allow
        for a better method.

        Args:
            attribute_list (list of IAttribute):
        """
        for attribute in attribute_list:
            self.delete_attribute(attribute)

    def clear_attributes(self, category, accessing_obj, default_access):
        """
        Remove all Attributes on this object.

        Args:
            category (str, optional): If given, clear only Attributes
                of this category.
            accessing_obj (object, optional): If given, check the
                `attredit` lock on each Attribute before continuing.
            default_access (bool, optional): Use this permission as
                fallback if `access_obj` is given but there is no lock of
                type `attredit` on the Attribute in question.

        """
        category = category.strip().lower() if category is not None else None

        if not self._cache_complete:
            self._full_cache()

        if category is not None:
            attrs = [attr for attr in self._cache.values() if attr.category == category]
        else:
            attrs = self._cache.values()

        if accessing_obj:
            self.do_batch_delete(
                [
                    attr
                    for attr in attrs
                    if attr.access(accessing_obj, self._attredit, default=default_access)
                ]
            )
        else:
            # have to cast the results to a list or we'll get a RuntimeError for removing from the
            # dict we're iterating
            self.do_batch_delete(list(attrs))
        self.reset_cache()

    def get_all_attributes(self):
        """
        Simply returns all Attributes of this object, sorted by their IDs.

        Returns:
            attributes (list of IAttribute)
        """
        if _TYPECLASS_AGGRESSIVE_CACHE:
            if not self._cache_complete:
                self._full_cache()
            return sorted([attr for attr in self._cache.values() if attr], key=lambda o: o.id)
        else:
            return sorted([attr for attr in self.query_all() if attr], key=lambda o: o.id)


class InMemoryAttributeBackend(IAttributeBackend):
    """
    This Backend for Attributes stores NOTHING in the database. Everything is kept in memory, and
    normally lost on a crash, reload, shared memory flush, etc. It generates IDs for the Attributes
    it manages, but these are of little importance beyond sorting and satisfying the caching logic
    to know an Attribute hasn't been deleted out from under the cache's nose.

    """

    _attrclass = InMemoryAttribute

    def __init__(self, handler, attrtype):
        super().__init__(handler, attrtype)
        self._storage = dict()
        self._category_storage = defaultdict(list)
        self._id_counter = 0

    def _next_id(self):
        """
        Increments the internal ID counter and returns the new value.

        Returns:
            next_id (int): A simple integer.
        """
        self._id_counter += 1
        return self._id_counter

    def query_all(self):
        return self._storage.values()

    def query_key(self, key, category):
        found = self._storage.get((key, category), None)
        if found:
            return [found]
        return []

    def query_category(self, category):
        if category is None:
            return self._storage.values()
        return self._category_storage.get(category, [])

    def do_create_attribute(self, key, category, lockstring, value, strvalue):
        """
        See parent class.

        strvalue has no meaning for InMemory attributes.

        """
        new_attr = self._attrclass(
            pk=self._next_id(), key=key, category=category, lock_storage=lockstring, value=value
        )
        self._storage[(key, category)] = new_attr
        self._category_storage[category].append(new_attr)
        return new_attr

    def do_update_attribute(self, attr, value, strvalue):
        attr.value = value

    def do_batch_update_attribute(self, attr_obj, category, lock_storage, new_value, strvalue):
        """
        No need to bother saving anything. Just set some values.
        """
        attr_obj.db_category = category
        attr_obj.db_lock_storage = lock_storage if lock_storage else ""
        attr_obj.value = new_value

    def do_batch_finish(self, attr_objs):
        """
        Nothing to do here for In-Memory.

        Args:
            attr_objs (list of IAttribute): The Attributes created/updated thus far.
        """
        pass

    def do_delete_attribute(self, attr):
        """
        Removes the Attribute from local storage. Once it's out of the cache, garbage collection
        will handle the rest.

        Args:
            attr (IAttribute): The attribute to delete.
        """
        del self._storage[(attr.key, attr.category)]
        self._category_storage[attr.category].remove(attr)


class ModelAttributeBackend(IAttributeBackend):
    """
    Uses Django models for storing Attributes.
    """

    _attrclass = Attribute
    _m2m_fieldname = "db_attributes"

    def __init__(self, handler, attrtype):
        super().__init__(handler, attrtype)
        self._model = to_str(handler.obj.__dbclass__.__name__.lower())

    def query_all(self):
        query = {
            "%s__id" % self._model: self._objid,
            "attribute__db_model__iexact": self._model,
            "attribute__db_attrtype": self._attrtype,
        }
        return [
            conn.attribute
            for conn in getattr(self.obj, self._m2m_fieldname).through.objects.filter(**query)
        ]

    def query_key(self, key, category):
        query = {
            "%s__id" % self._model: self._objid,
            "attribute__db_model__iexact": self._model,
            "attribute__db_attrtype": self._attrtype,
            "attribute__db_key__iexact": key.lower(),
            "attribute__db_category__iexact": category.lower() if category else None,
        }
        if not self.obj.pk:
            return []
        return getattr(self.obj, self._m2m_fieldname).through.objects.filter(**query)

    def query_category(self, category):
        query = {
            "%s__id" % self._model: self._objid,
            "attribute__db_model__iexact": self._model,
            "attribute__db_attrtype": self._attrtype,
            "attribute__db_category__iexact": category.lower() if category else None,
        }
        return [
            conn.attribute
            for conn in getattr(self.obj, self._m2m_fieldname).through.objects.filter(**query)
        ]

    def do_create_attribute(self, key, category, lockstring, value, strvalue):
        kwargs = {
            "db_key": key,
            "db_category": category,
            "db_model": self._model,
            "db_lock_storage": lockstring if lockstring else "",
            "db_attrtype": self._attrtype,
        }
        if strvalue:
            kwargs["db_value"] = None
            kwargs["db_strvalue"] = value
        else:
            kwargs["db_value"] = to_pickle(value)
            kwargs["db_strvalue"] = None
        new_attr = self._attrclass(**kwargs)
        new_attr.save()
        getattr(self.obj, self._m2m_fieldname).add(new_attr)
        self._set_cache(key, category, new_attr)
        return new_attr

    def do_update_attribute(self, attr, value, strvalue):
        if strvalue:
            attr.value = None
            attr.db_strvalue = value
        else:
            attr.value = value
            attr.db_strvalue = None
        attr.save(update_fields=["db_strvalue", "db_value"])

    def do_batch_update_attribute(self, attr_obj, category, lock_storage, new_value, strvalue):
        attr_obj.db_category = category
        attr_obj.db_lock_storage = lock_storage if lock_storage else ""
        if strvalue:
            # store as a simple string (will not notify OOB handlers)
            attr_obj.db_strvalue = new_value
            attr_obj.value = None
        else:
            # store normally (this will also notify OOB handlers)
            attr_obj.value = new_value
            attr_obj.db_strvalue = None
        attr_obj.save(update_fields=["db_strvalue", "db_value", "db_category", "db_lock_storage"])

    def do_batch_finish(self, attr_objs):
        # Add new objects to m2m field all at once
        getattr(self.obj, self._m2m_fieldname).add(*attr_objs)

    def do_delete_attribute(self, attr):
        try:
            attr.delete()
        except AssertionError:
            # This could happen if the Attribute has already been deleted.
            pass


class AttributeHandler:
    """
    Handler for adding Attributes to the object.
    """

    _attrcreate = "attrcreate"
    _attredit = "attredit"
    _attrread = "attrread"
    _attrtype = None

    def __init__(self, obj, backend_class):
        """
        Setup the AttributeHandler.

        Args:
            obj (TypedObject): An Account, Object, Channel, ServerSession (not technically a typed
                object), etc.  backend_class (IAttributeBackend class): The class of the backend to
                use.
        """
        self.obj = obj
        self.backend = backend_class(self, self._attrtype)

    def has(self, key=None, category=None):
        """
        Checks if the given Attribute (or list of Attributes) exists on
        the object.

        Args:
            key (str or iterable): The Attribute key or keys to check for.
                If `None`, search by category.
            category (str or None): Limit the check to Attributes with this
                category (note, that `None` is the default category).

        Returns:
            has_attribute (bool or list): If the Attribute exists on
                this object or not. If `key` was given as an iterable then
                the return is a list of booleans.

        """
        ret = []
        category = category.strip().lower() if category is not None else None
        for keystr in make_iter(key):
            keystr = key.strip().lower()
            ret.extend(bool(attr) for attr in self.backend.get(keystr, category))
        return ret[0] if len(ret) == 1 else ret

    def get(
        self,
        key=None,
        default=None,
        category=None,
        return_obj=False,
        strattr=False,
        raise_exception=False,
        accessing_obj=None,
        default_access=True,
        return_list=False,
    ):
        """
        Get the Attribute.

        Args:
            key (str or list, optional): the attribute identifier or
                multiple attributes to get. if a list of keys, the
                method will return a list.
            default (any, optional): The value to return if an
                Attribute was not defined. If set, it will be returned in
                a one-item list.
            category (str, optional): the category within which to
                retrieve attribute(s).
            return_obj (bool, optional): If set, the return is not the value of the
                Attribute but the Attribute object itself.
            strattr (bool, optional): Return the `strvalue` field of
                the Attribute rather than the usual `value`, this is a
                string-only value for quick database searches.
            raise_exception (bool, optional): When an Attribute is not
                found, the return from this is usually `default`. If this
                is set, an exception is raised instead.
            accessing_obj (object, optional): If set, an `attrread`
                permission lock will be checked before returning each
                looked-after Attribute.
            default_access (bool, optional): If no `attrread` lock is set on
                object, this determines if the lock should then be passed or not.
            return_list (bool, optional): Always return a list, also if there is only
                one or zero matches found.

        Returns:
            result (any or list): One or more matches for keys and/or
                categories. Each match will be the value of the found Attribute(s)
                unless `return_obj` is True, at which point it will be the
                attribute object itself or None. If `return_list` is True, this
                will always be a list, regardless of the number of elements.

        Raises:
            AttributeError: If `raise_exception` is set and no matching Attribute
                was found matching `key`.

        """

        ret = []
        for keystr in make_iter(key):
            # it's okay to send a None key
            attr_objs = self.backend.get(keystr, category)
            if attr_objs:
                ret.extend(attr_objs)
            elif raise_exception:
                raise AttributeError
            elif return_obj:
                ret.append(None)

        if accessing_obj:
            # check 'attrread' locks
            ret = [
                attr
                for attr in ret
                if attr.access(accessing_obj, self._attrread, default=default_access)
            ]
        if strattr:
            ret = ret if return_obj else [attr.strvalue for attr in ret if attr]
        else:
            ret = ret if return_obj else [attr.value for attr in ret if attr]

        if return_list:
            return ret if ret else [default] if default is not None else []
        return ret[0] if ret and len(ret) == 1 else ret or default

    def add(
        self,
        key,
        value,
        category=None,
        lockstring="",
        strattr=False,
        accessing_obj=None,
        default_access=True,
    ):
        """
        Add attribute to object, with optional `lockstring`.

        Args:
            key (str): An Attribute name to add.
            value (any or str): The value of the Attribute. If
                `strattr` keyword is set, this *must* be a string.
            category (str, optional): The category for the Attribute.
                The default `None` is the normal category used.
            lockstring (str, optional): A lock string limiting access
                to the attribute.
            strattr (bool, optional): Make this a string-only Attribute.
                This is only ever useful for optimization purposes.
            accessing_obj (object, optional): An entity to check for
                the `attrcreate` access-type. If not passing, this method
                will be exited.
            default_access (bool, optional): What access to grant if
                `accessing_obj` is given but no lock of the type
                `attrcreate` is defined on the Attribute in question.

        """
        if accessing_obj and not self.obj.access(
            accessing_obj, self._attrcreate, default=default_access
        ):
            # check create access
            return

        if not key:
            return

        category = category.strip().lower() if category is not None else None
        keystr = key.strip().lower()
        attr_obj = self.backend.get(key, category)

        if attr_obj:
            # update an existing attribute object
            attr_obj = attr_obj[0]
            self.backend.update_attribute(attr_obj, value, strattr)
        else:
            # create a new Attribute (no OOB handlers can be notified)
            self.backend.create_attribute(keystr, category, lockstring, value, strattr)

    def batch_add(self, *args, **kwargs):
        """
        Batch-version of `add()`. This is more efficient than
        repeat-calling add when having many Attributes to add.

        Args:
            *args (tuple): Each argument should be a tuples (can be of varying
                length) representing the Attribute to add to this object.
                Supported tuples are

                - (key, value)
                - (key, value, category)
                - (key, value, category, lockstring)
                - (key, value, category, lockstring, default_access)

        Keyword Args:
            strattr (bool): If `True`, value must be a string. This
                will save the value without pickling which is less
                flexible but faster to search (not often used except
                internally).

        Raises:
            RuntimeError: If trying to pass a non-iterable as argument.

        Notes:
            The indata tuple order matters, so if you want a lockstring
            but no category, set the category to `None`. This method
            does not have the ability to check editing permissions like
            normal .add does, and is mainly used internally. It does not
            use the normal self.add but apply the Attributes directly
            to the database.

        """
        self.backend.batch_add(*args, **kwargs)

    def remove(
        self,
        key=None,
        category=None,
        raise_exception=False,
        accessing_obj=None,
        default_access=True,
    ):
        """
        Remove attribute or a list of attributes from object.

        Args:
            key (str or list, optional): An Attribute key to remove or a list of keys. If
                multiple keys, they must all be of the same `category`. If None and
                category is not given, remove all Attributes.
            category (str, optional): The category within which to
                remove the Attribute.
            raise_exception (bool, optional): If set, not finding the
                Attribute to delete will raise an exception instead of
                just quietly failing.
            accessing_obj (object, optional): An object to check
                against the `attredit` lock. If not given, the check will
                be skipped.
            default_access (bool, optional): The fallback access to
                grant if `accessing_obj` is given but there is no
                `attredit` lock set on the Attribute in question.

        Raises:
            AttributeError: If `raise_exception` is set and no matching Attribute
                was found matching `key`.

        Notes:
            If neither key nor category is given, this acts as clear().

        """

        if key is None:
            self.clear(
                category=category, accessing_obj=accessing_obj, default_access=default_access
            )
            return

        category = category.strip().lower() if category is not None else None

        for keystr in make_iter(key):
            keystr = keystr.lower()

            attr_objs = self.backend.get(keystr, category)
            for attr_obj in attr_objs:
                if not (
                    accessing_obj
                    and not attr_obj.access(accessing_obj, self._attredit, default=default_access)
                ):
                    self.backend.delete_attribute(attr_obj)
            if not attr_objs and raise_exception:
                raise AttributeError

    def clear(self, category=None, accessing_obj=None, default_access=True):
        """
        Remove all Attributes on this object.

        Args:
            category (str, optional): If given, clear only Attributes
                of this category.
            accessing_obj (object, optional): If given, check the
                `attredit` lock on each Attribute before continuing.
            default_access (bool, optional): Use this permission as
                fallback if `access_obj` is given but there is no lock of
                type `attredit` on the Attribute in question.

        """
        self.backend.clear_attributes(category, accessing_obj, default_access)

    def all(self, accessing_obj=None, default_access=True):
        """
        Return all Attribute objects on this object, regardless of category.

        Args:
            accessing_obj (object, optional): Check the `attrread`
                lock on each attribute before returning them. If not
                given, this check is skipped.
            default_access (bool, optional): Use this permission as a
                fallback if `accessing_obj` is given but one or more
                Attributes has no lock of type `attrread` defined on them.

        Returns:
            Attributes (list): All the Attribute objects (note: Not
                their values!) in the handler.

        """
        attrs = self.backend.get_all_attributes()

        if accessing_obj:
            return [
                attr
                for attr in attrs
                if attr.access(accessing_obj, self._attrread, default=default_access)
            ]
        else:
            return attrs

    def reset_cache(self):
        self.backend.reset_cache()


# DbHolders for .db and .ndb properties on Typeclasses.

_GA = object.__getattribute__
_SA = object.__setattr__


class DbHolder:
    "Holder for allowing property access of attributes"

    def __init__(self, obj, name, manager_name="attributes"):
        _SA(self, name, _GA(obj, manager_name))
        _SA(self, "name", name)

    def __getattribute__(self, attrname):
        if attrname == "all":
            # we allow to overload our default .all
            attr = _GA(self, _GA(self, "name")).get("all")
            return attr if attr else _GA(self, "all")
        return _GA(self, _GA(self, "name")).get(attrname)

    def __setattr__(self, attrname, value):
        _GA(self, _GA(self, "name")).add(attrname, value)

    def __delattr__(self, attrname):
        _GA(self, _GA(self, "name")).remove(attrname)

    def get_all(self):
        return _GA(self, _GA(self, "name")).backend.get_all_attributes()

    all = property(get_all)


#
# Nick templating
#

"""
This supports the use of replacement templates in nicks:

This happens in two steps:

1) The user supplies a template that is converted to a regex according
   to the unix-like templating language.
2) This regex is tested against nicks depending on which nick replacement
   strategy is considered (most commonly inputline).
3) If there is a template match and there are templating markers,
   these are replaced with the arguments actually given.

@desc $1 $2 $3

This will be converted to the following regex:

    \@desc (?P<1>\w+) (?P<2>\w+) $(?P<3>\w+)

Supported template markers (through fnmatch)
   *       matches anything (non-greedy)     -> .*?
   ?       matches any single character      ->
   [seq]   matches any entry in sequence
   [!seq]  matches entries not in sequence
Custom arg markers
   $N      argument position (1-99)

"""
_RE_OR = re.compile(r"(?<!\\)\|")
_RE_NICK_RE_ARG = re.compile(r"arg([1-9][0-9]?)")
_RE_NICK_ARG = re.compile(r"\\(\$)([1-9][0-9]?)")
_RE_NICK_RAW_ARG = re.compile(r"(\$)([1-9][0-9]?)")
_RE_NICK_SPACE = re.compile(r"\\ ")


class NickTemplateInvalid(ValueError):
    pass


def initialize_nick_templates(pattern, replacement, pattern_is_regex=False):
    """
    Initialize the nick templates for matching and remapping a string.

    Args:
        pattern (str): The pattern to be used for nick recognition. This will
            be parsed for shell patterns into a regex, unless `pattern_is_regex`
            is `True`, in which case it must be an already valid regex string. In
            this case, instead of `$N`, numbered arguments must instead be given
            as matching groups named as `argN`, such as `(?P<arg1>.+?)`.
        replacement (str): The template to be used to replace the string
            matched by the pattern. This can contain `$N` markers and is never
            parsed into a regex.
        pattern_is_regex (bool): If set, `pattern` is a full regex string
            instead of containing shell patterns.

    Returns:
        regex, template  (str): Regex to match against strings and template
            with markers ``{arg1}, {arg2}``, etc for replacement using the standard
            `.format` method.

    Raises:
        evennia.typecalasses.attributes.NickTemplateInvalid: If the in/out
        template does not have a matching number of `$args`.

    Examples:
        - `pattern` (shell syntax): `"grin $1"`
        - `pattern` (regex): `"grin (?P<arg1.+?>)"`
        - `replacement`: `"emote gives a wicked grin to $1"`

    """

    # create the regex from the pattern
    if pattern_is_regex:
        # Note that for a regex we can't validate in the way we do for the shell
        # pattern, since you may have complex OR statements or optional arguments.

        # Explicit regex given from the onset - this already contains argN
        # groups.  we need to split out any | - separated parts so we can
        # attach the line-break/ending extras all regexes require.
        pattern_regex_string = r"|".join(
            or_part + r"(?:[\n\r]*?)\Z" for or_part in _RE_OR.split(pattern)
        )

    else:
        # Shell pattern syntax - convert $N to argN groups
        # for the shell pattern we make sure we have matching $N on both sides
        pattern_args = [match.group(1) for match in _RE_NICK_RAW_ARG.finditer(pattern)]
        replacement_args = [match.group(1) for match in _RE_NICK_RAW_ARG.finditer(replacement)]
        if set(pattern_args) != set(replacement_args):
            # We don't have the same amount of argN/$N tags in input/output.
            raise NickTemplateInvalid("Nicks: Both in/out-templates must contain the same $N tags.")

        # generate regex from shell pattern
        pattern_regex_string = fnmatch.translate(pattern)
        pattern_regex_string = _RE_NICK_SPACE.sub(r"\\s+", pattern_regex_string)
        pattern_regex_string = _RE_NICK_ARG.sub(
            lambda m: "(?P<arg%s>.+?)" % m.group(2), pattern_regex_string
        )
        # we must account for a possible line break coming over the wire
        pattern_regex_string = pattern_regex_string[:-2] + r"(?:[\n\r]*?)\Z"

    # map the replacement to match the arg1 group-names, to make replacement easy
    replacement_string = _RE_NICK_RAW_ARG.sub(lambda m: "{arg%s}" % m.group(2), replacement)

    return pattern_regex_string, replacement_string


def parse_nick_template(string, template_regex, outtemplate):
    """
    Parse a text using a template and map it to another template

    Args:
        string (str): The input string to process
        template_regex (regex): A template regex created with
            initialize_nick_template.
        outtemplate (str): The template to which to map the matches
            produced by the template_regex. This should have $1, $2,
            etc to match the template-regex. Un-found $N-markers (possible if
            the regex has optional matching groups) are replaced with empty
            strings.

    """
    match = template_regex.match(string)
    if match:
        matchdict = {
            key: value if value is not None else "" for key, value in match.groupdict().items()
        }
        return True, outtemplate.format_map(matchdict)
    return False, string


class NickHandler(AttributeHandler):
    """
    Handles the addition and removal of Nicks. Nicks are special
    versions of Attributes with an `_attrtype` hardcoded to `nick`.
    They also always use the `strvalue` fields for their data.

    """

    _attrtype = "nick"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._regex_cache = {}

    def has(self, key, category="inputline"):
        """
        Args:
            key (str or iterable): The Nick key or keys to check for.
            category (str): Limit the check to Nicks with this
                category (note, that `None` is the default category).

        Returns:
            has_nick (bool or list): If the Nick exists on this object
                or not. If `key` was given as an iterable then the return
                is a list of booleans.

        """
        return super().has(key, category=category)

    def get(self, key=None, category="inputline", return_tuple=False, **kwargs):
        """
        Get the replacement value matching the given key and category

        Args:
            key (str or list, optional): the attribute identifier or
                multiple attributes to get. if a list of keys, the
                method will return a list.
            category (str, optional): the category within which to
                retrieve the nick. The "inputline" means replacing data
                sent by the user.
            return_tuple (bool, optional): return the full nick tuple rather
                than just the replacement. For non-template nicks this is just
                a string.
            kwargs (any, optional): These are passed on to `AttributeHandler.get`.

        Returns:
            str or tuple:  The nick replacement string or nick tuple.

        """
        if return_tuple or "return_obj" in kwargs:
            return super().get(key=key, category=category, **kwargs)
        else:
            retval = super().get(key=key, category=category, **kwargs)
            if retval:
                return (
                    retval[3]
                    if isinstance(retval, tuple)
                    else [tup[3] for tup in make_iter(retval)]
                )
            return None

    def add(self, pattern, replacement, category="inputline", pattern_is_regex=False, **kwargs):
        """
        Add a new nick, a mapping pattern -> replacement.

        Args:
            pattern (str): A pattern to match for. This will be parsed for
                shell patterns using the `fnmatch` library and can contain
                `$N`-markers to indicate the locations of arguments to catch. If
                `pattern_is_regex=True`, this must instead be a valid regular
                expression and the `$N`-markers must be named `argN` that matches
                numbered regex groups (see examples).
            replacement (str): The string (or template) to replace `key` with
                (the "nickname"). This may contain `$N` markers to indicate where to
                place the argument-matches
            category (str, optional): the category within which to
                retrieve the nick. The "inputline" means replacing data
                sent by the user.
            pattern_is_regex (bool): If `True`, the `pattern` will be parsed as a
                raw regex string. Instead of using `$N` markers in this string, one
                then must mark numbered arguments as a named regex-groupd named `argN`.
                For example, `(?P<arg1>.+?)` will match the behavior of using `$1`
                in the shell pattern.
            **kwargs (any, optional): These are passed on to `AttributeHandler.get`.

        Notes:
            For most cases, the shell-pattern is much shorter and easier. The
            regex pattern form can be useful for more complex matchings though,
            for example in order to add optional arguments, such as with
            `(?P<argN>.*?)`.

        Example:
            - pattern (default shell syntax): `"gr $1 at $2"`
            - pattern (with pattern_is_regex=True): `r"gr (?P<arg1>.+?) at (?P<arg2>.+?)"`
            - replacement: `"emote With a flourish, $1 grins at $2."`

        """
        nick_regex, nick_template = initialize_nick_templates(
            pattern, replacement, pattern_is_regex=pattern_is_regex
        )
        super().add(
            pattern, (nick_regex, nick_template, pattern, replacement), category=category, **kwargs
        )

    def remove(self, key, category="inputline", **kwargs):
        """
        Remove Nick with matching category.

        Args:
            key (str): A key for the nick to match for.
            category (str, optional): the category within which to
                removethe nick. The "inputline" means replacing data
                sent by the user.
            kwargs (any, optional): These are passed on to `AttributeHandler.get`.

        """
        super().remove(key, category=category, **kwargs)

    def nickreplace(self, raw_string, categories=("inputline", "channel"), include_account=True):
        """
        Apply nick replacement of entries in raw_string with nick replacement.

        Args:
            raw_string (str): The string in which to perform nick
                replacement.
            categories (tuple, optional): Replacement categories in
                which to perform the replacement, such as "inputline",
                "channel" etc.
            include_account (bool, optional): Also include replacement
                with nicks stored on the Account level.
            kwargs (any, optional): Not used.

        Returns:
            string (str): A string with matching keys replaced with
                their nick equivalents.

        """
        nicks = {}
        for category in make_iter(categories):
            nicks.update(
                {
                    nick.key: nick
                    for nick in make_iter(self.get(category=category, return_obj=True))
                    if nick and nick.key
                }
            )
        if include_account and self.obj.has_account:
            for category in make_iter(categories):
                nicks.update(
                    {
                        nick.key: nick
                        for nick in make_iter(
                            self.obj.account.nicks.get(category=category, return_obj=True)
                        )
                        if nick and nick.key
                    }
                )
        for key, nick in nicks.items():
            nick_regex, template, _, _ = nick.value
            regex = self._regex_cache.get(nick_regex)
            if not regex:
                regex = re.compile(nick_regex, re.I + re.DOTALL + re.U)
                self._regex_cache[nick_regex] = regex

            is_match, raw_string = parse_nick_template(raw_string.strip(), regex, template)
            if is_match:
                break
        return raw_string
