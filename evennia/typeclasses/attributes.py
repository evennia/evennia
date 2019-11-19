"""
Attributes are arbitrary data stored on objects. Attributes supports
both pure-string values and pickled arbitrary data.

Attributes are also used to implement Nicks. This module also contains
the Attribute- and NickHandlers as well as the `NAttributeHandler`,
which is a non-db version of Attributes.


"""
import re
import fnmatch
import weakref

from django.db import models
from django.conf import settings
from django.utils.encoding import smart_str

from evennia.locks.lockhandler import LockHandler
from evennia.utils.idmapper.models import SharedMemoryModel
from evennia.utils.dbserialize import to_pickle, from_pickle
from evennia.utils.picklefield import PickledObjectField
from evennia.utils.utils import lazy_property, to_str, make_iter, is_iter

_TYPECLASS_AGGRESSIVE_CACHE = settings.TYPECLASS_AGGRESSIVE_CACHE

# -------------------------------------------------------------
#
#   Attributes
#
# -------------------------------------------------------------


class Attribute(SharedMemoryModel):
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

    """

    #
    # Attribute Database Model setup
    #
    # These database fields are all set using their corresponding properties,
    # named same as the field, but withtout the db_* prefix.
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

    @lazy_property
    def locks(self):
        return LockHandler(self)

    class Meta(object):
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
    # @property
    def __value_get(self):
        """
        Getter. Allows for `value = self.value`.
        We cannot cache here since it makes certain cases (such
        as storing a dbobj which is then deleted elsewhere) out-of-sync.
        The overhead of unpickling seems hard to avoid.
        """
        return from_pickle(self.db_value, db_obj=self)

    # @value.setter
    def __value_set(self, new_value):
        """
        Setter. Allows for self.value = value. We cannot cache here,
        see self.__value_get.
        """
        self.db_value = to_pickle(new_value)
        # print("value_set, self.db_value:", repr(self.db_value))  # DEBUG
        self.save(update_fields=["db_value"])

    # @value.deleter
    def __value_del(self):
        """Deleter. Allows for del attr.value. This removes the entire attribute."""
        self.delete()

    value = property(__value_get, __value_set, __value_del)

    #
    #
    # Attribute methods
    #
    #

    def __str__(self):
        return smart_str("%s(%s)" % (self.db_key, self.id))

    def __repr__(self):
        return "%s(%s)" % (self.db_key, self.id)

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
        """Initialize handler."""
        self.obj = obj
        self._objid = obj.id
        self._model = to_str(obj.__dbclass__.__name__.lower())
        self._cache = {}
        # store category names fully cached
        self._catcache = {}
        # full cache was run on all attributes
        self._cache_complete = False

    def _fullcache(self):
        """Cache all attributes of this object"""
        query = {
            "%s__id" % self._model: self._objid,
            "attribute__db_model__iexact": self._model,
            "attribute__db_attrtype": self._attrtype,
        }
        attrs = [
            conn.attribute
            for conn in getattr(self.obj, self._m2m_fieldname).through.objects.filter(**query)
        ]
        self._cache = dict(
            (
                "%s-%s"
                % (
                    to_str(attr.db_key).lower(),
                    attr.db_category.lower() if attr.db_category else None,
                ),
                attr,
            )
            for attr in attrs
        )
        self._cache_complete = True

    def _getcache(self, key=None, category=None):
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
        category = category.strip().lower() if category else None
        if key:
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
            if cachefound:
                if attr:
                    return [attr]  # return cached entity
                else:
                    return []  # no such attribute: return an empty list
            else:
                query = {
                    "%s__id" % self._model: self._objid,
                    "attribute__db_model__iexact": self._model,
                    "attribute__db_attrtype": self._attrtype,
                    "attribute__db_key__iexact": key.lower(),
                    "attribute__db_category__iexact": category.lower() if category else None,
                }
                if not self.obj.pk:
                    return []
                conn = getattr(self.obj, self._m2m_fieldname).through.objects.filter(**query)
                if conn:
                    attr = conn[0].attribute
                    self._cache[cachekey] = attr
                    return [attr] if attr.pk else []
                else:
                    # There is no such attribute. We will explicitly save that
                    # in our cache to avoid firing another query if we try to
                    # retrieve that (non-existent) attribute again.
                    self._cache[cachekey] = None
                    return []
        else:
            # only category given (even if it's None) - we can't
            # assume the cache to be complete unless we have queried
            # for this category before
            catkey = "-%s" % category
            if _TYPECLASS_AGGRESSIVE_CACHE and catkey in self._catcache:
                return [attr for key, attr in self._cache.items() if key.endswith(catkey) and attr]
            else:
                # we have to query to make this category up-date in the cache
                query = {
                    "%s__id" % self._model: self._objid,
                    "attribute__db_model__iexact": self._model,
                    "attribute__db_attrtype": self._attrtype,
                    "attribute__db_category__iexact": category.lower() if category else None,
                }
                attrs = [
                    conn.attribute
                    for conn in getattr(self.obj, self._m2m_fieldname).through.objects.filter(
                        **query
                    )
                ]
                for attr in attrs:
                    if attr.pk:
                        cachekey = "%s-%s" % (attr.db_key, category)
                        self._cache[cachekey] = attr
                # mark category cache as up-to-date
                self._catcache[catkey] = True
                return attrs

    def _setcache(self, key, category, attr_obj):
        """
        Update cache.

        Args:
            key (str): A cleaned key string
            category (str or None): A cleaned category name
            attr_obj (Attribute): The newly saved attribute

        """
        if not key:  # don't allow an empty key in cache
            return
        cachekey = "%s-%s" % (key, category)
        catkey = "-%s" % category
        self._cache[cachekey] = attr_obj
        # mark that the category cache is no longer up-to-date
        self._catcache.pop(catkey, None)
        self._cache_complete = False

    def _delcache(self, key, category):
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
            ret.extend(bool(attr) for attr in self._getcache(keystr, category))
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
            category (str, optional): the category within which to
                retrieve attribute(s).
            default (any, optional): The value to return if an
                Attribute was not defined. If set, it will be returned in
                a one-item list.
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
            return_list (bool, optional):

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
            attr_objs = self._getcache(keystr, category)
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
        attr_obj = self._getcache(key, category)

        if attr_obj:
            # update an existing attribute object
            attr_obj = attr_obj[0]
            if strattr:
                # store as a simple string (will not notify OOB handlers)
                attr_obj.db_strvalue = value
                attr_obj.save(update_fields=["db_strvalue"])
            else:
                # store normally (this will also notify OOB handlers)
                attr_obj.value = value
        else:
            # create a new Attribute (no OOB handlers can be notified)
            kwargs = {
                "db_key": keystr,
                "db_category": category,
                "db_model": self._model,
                "db_attrtype": self._attrtype,
                "db_value": None if strattr else to_pickle(value),
                "db_strvalue": value if strattr else None,
            }
            new_attr = Attribute(**kwargs)
            new_attr.save()
            getattr(self.obj, self._m2m_fieldname).add(new_attr)
            # update cache
            self._setcache(keystr, category, new_attr)

    def batch_add(self, *args, **kwargs):
        """
        Batch-version of `add()`. This is more efficient than
        repeat-calling add when having many Attributes to add.

        Args:
            indata (list): List of tuples of varying length representing the
                Attribute to add to this object. Supported tuples are
                    - `(key, value)`
                    - `(key, value, category)`
                    - `(key, value, category, lockstring)`
                    - `(key, value, category, lockstring, default_access)`

        Kwargs:
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

            attr_objs = self._getcache(keystr, category)

            if attr_objs:
                attr_obj = attr_objs[0]
                # update an existing attribute object
                attr_obj.db_category = category
                attr_obj.db_lock_storage = lockstring or ""
                attr_obj.save(update_fields=["db_category", "db_lock_storage"])
                if strattr:
                    # store as a simple string (will not notify OOB handlers)
                    attr_obj.db_strvalue = new_value
                    attr_obj.save(update_fields=["db_strvalue"])
                else:
                    # store normally (this will also notify OOB handlers)
                    attr_obj.value = new_value
            else:
                # create a new Attribute (no OOB handlers can be notified)
                kwargs = {
                    "db_key": keystr,
                    "db_category": category,
                    "db_model": self._model,
                    "db_attrtype": self._attrtype,
                    "db_value": None if strattr else to_pickle(new_value),
                    "db_strvalue": new_value if strattr else None,
                    "db_lock_storage": lockstring or "",
                }
                new_attr = Attribute(**kwargs)
                new_attr.save()
                new_attrobjs.append(new_attr)
                self._setcache(keystr, category, new_attr)
        if new_attrobjs:
            # Add new objects to m2m field all at once
            getattr(self.obj, self._m2m_fieldname).add(*new_attrobjs)

    def remove(
        self,
        key=None,
        raise_exception=False,
        category=None,
        accessing_obj=None,
        default_access=True,
    ):
        """
        Remove attribute or a list of attributes from object.

        Args:
            key (str or list, optional): An Attribute key to remove or a list of keys. If
                multiple keys, they must all be of the same `category`. If None and
                category is not given, remove all Attributes.
            raise_exception (bool, optional): If set, not finding the
                Attribute to delete will raise an exception instead of
                just quietly failing.
            category (str, optional): The category within which to
                remove the Attribute.
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

            attr_objs = self._getcache(keystr, category)
            for attr_obj in attr_objs:
                if not (
                    accessing_obj
                    and not attr_obj.access(accessing_obj, self._attredit, default=default_access)
                ):
                    try:
                        attr_obj.delete()
                    except AssertionError:
                        print("Assertionerror for attr.delete()")
                        # this happens if the attr was already deleted
                        pass
                    finally:
                        self._delcache(keystr, category)
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
        category = category.strip().lower() if category is not None else None

        if not self._cache_complete:
            self._fullcache()

        if category is not None:
            attrs = [attr for attr in self._cache.values() if attr.category == category]
        else:
            attrs = self._cache.values()

        if accessing_obj:
            [
                attr.delete()
                for attr in attrs
                if attr and attr.access(accessing_obj, self._attredit, default=default_access)
            ]
        else:
            [attr.delete() for attr in attrs if attr and attr.pk]
        self._cache = {}
        self._catcache = {}
        self._cache_complete = False

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
        if not self._cache_complete:
            self._fullcache()
        attrs = sorted([attr for attr in self._cache.values() if attr], key=lambda o: o.id)
        if accessing_obj:
            return [
                attr
                for attr in attrs
                if attr.access(accessing_obj, self._attredit, default=default_access)
            ]
        else:
            return attrs


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
_RE_NICK_ARG = re.compile(r"\\(\$)([1-9][0-9]?)")
_RE_NICK_TEMPLATE_ARG = re.compile(r"(\$)([1-9][0-9]?)")
_RE_NICK_SPACE = re.compile(r"\\ ")


class NickTemplateInvalid(ValueError):
    pass


def initialize_nick_templates(in_template, out_template):
    """
    Initialize the nick templates for matching and remapping a string.

    Args:
        in_template (str): The template to be used for nick recognition.
        out_template (str): The template to be used to replace the string
            matched by the in_template.

    Returns:
        regex  (regex): Regex to match against strings
        template (str): Template with markers {arg1}, {arg2}, etc for
            replacement using the standard .format method.

    Raises:
        NickTemplateInvalid: If the in/out template does not have a matching
            number of $args.

    """

    # create the regex for in_template
    regex_string = fnmatch.translate(in_template)
    # we must account for a possible line break coming over the wire

    # NOTE-PYTHON3: fnmatch.translate format changed since Python2
    regex_string = regex_string[:-2] + r"(?:[\n\r]*?)\Z"

    # validate the templates
    regex_args = [match.group(2) for match in _RE_NICK_ARG.finditer(regex_string)]
    temp_args = [match.group(2) for match in _RE_NICK_TEMPLATE_ARG.finditer(out_template)]
    if set(regex_args) != set(temp_args):
        # We don't have the same $-tags in input/output.
        raise NickTemplateInvalid

    regex_string = _RE_NICK_SPACE.sub(r"\\s+", regex_string)
    regex_string = _RE_NICK_ARG.sub(lambda m: "(?P<arg%s>.+?)" % m.group(2), regex_string)
    template_string = _RE_NICK_TEMPLATE_ARG.sub(lambda m: "{arg%s}" % m.group(2), out_template)

    return regex_string, template_string


def parse_nick_template(string, template_regex, outtemplate):
    """
    Parse a text using a template and map it to another template

    Args:
        string (str): The input string to processj
        template_regex (regex): A template regex created with
            initialize_nick_template.
        outtemplate (str): The template to which to map the matches
            produced by the template_regex. This should have $1, $2,
            etc to match the regex.

    """
    match = template_regex.match(string)
    if match:
        return True, outtemplate.format(**match.groupdict())
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

    def add(self, key, replacement, category="inputline", **kwargs):
        """
        Add a new nick.

        Args:
            key (str): A key (or template) for the nick to match for.
            replacement (str): The string (or template) to replace `key` with (the "nickname").
            category (str, optional): the category within which to
                retrieve the nick. The "inputline" means replacing data
                sent by the user.
            kwargs (any, optional): These are passed on to `AttributeHandler.get`.

        """
        if category == "channel":
            nick_regex, nick_template = initialize_nick_templates(key + " $1", replacement + " $1")
        else:
            nick_regex, nick_template = initialize_nick_templates(key, replacement)
        super().add(key, (nick_regex, nick_template, key, replacement), category=category, **kwargs)

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


class NAttributeHandler(object):
    """
    This stand-alone handler manages non-database saving.
    It is similar to `AttributeHandler` and is used
    by the `.ndb` handler in the same way as `.db` does
    for the `AttributeHandler`.
    """

    def __init__(self, obj):
        """
        Initialized on the object
        """
        self._store = {}
        self.obj = weakref.proxy(obj)

    def has(self, key):
        """
        Check if object has this attribute or not.

        Args:
            key (str): The Nattribute key to check.

        Returns:
            has_nattribute (bool): If Nattribute is set or not.

        """
        return key in self._store

    def get(self, key):
        """
        Get the named key value.

        Args:
            key (str): The Nattribute key to get.

        Returns:
            the value of the Nattribute.

        """
        return self._store.get(key, None)

    def add(self, key, value):
        """
        Add new key and value.

        Args:
            key (str): The name of Nattribute to add.
            value (any): The value to store.

        """
        self._store[key] = value

    def remove(self, key):
        """
        Remove Nattribute from storage.

        Args:
            key (str): The name of the Nattribute to remove.

        """
        if key in self._store:
            del self._store[key]

    def clear(self):
        """
        Remove all NAttributes from handler.

        """
        self._store = {}

    def all(self, return_tuples=False):
        """
        List the contents of the handler.

        Args:
            return_tuples (bool, optional): Defines if the Nattributes
                are returns as a list of keys or as a list of `(key, value)`.

        Returns:
            nattributes (list): A list of keys `[key, key, ...]` or a
                list of tuples `[(key, value), ...]` depending on the
                setting of `return_tuples`.

        """
        if return_tuples:
            return [(key, value) for (key, value) in self._store.items() if not key.startswith("_")]
        return [key for key in self._store if not key.startswith("_")]
