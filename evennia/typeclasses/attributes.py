"""
Attributes are arbitrary data stored on objects. Attributes supports
both pure-string values and pickled arbitrary data.

Attributes are also used to implement Nicks. This module also contains
the Attribute- and NickHandlers as well as the `NAttributeHandler`,
which is a non-db version of Attributes.


"""
from builtins import object
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
                  "natural key like 'objects.objectdb'). You should not change "
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
        "Initialize handler."
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

        Args:
            key (str or iterable): The Attribute key or keys to check for.
            category (str): Limit the check to Attributes with this
                category (note, that `None` is the default category).

        Returns:
            has_attribute (bool or list): If the Attribute exists on
                this object or not. If `key` was given as an iterable then
                the return is a list of booleans.

        """
        if self._cache is None or not _TYPECLASS_AGGRESSIVE_CACHE:
            self._recache()
        key = [k.strip().lower() for k in make_iter(key) if k]
        category = category.strip().lower() if category is not None else None
        searchkeys = ["%s-%s" % (k, category) for k in make_iter(key)]
        ret = [self._cache.get(skey) for skey in searchkeys if skey in self._cache]
        return ret[0] if len(ret) == 1 else ret

    def get(self, key=None, default=None, category=None, return_obj=False,
            strattr=False, raise_exception=False, accessing_obj=None,
            default_access=True):
        """
        Get the Attribute.

        Args:
            key (str or list, optional): the attribute identifier or
                multiple attributes to get. if a list of keys, the
                method will return a list.
            category (str, optional): the category within which to
                retrieve attribute(s).
            default (any, optional): The value to return if an
                Attribute was not defined.
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

        Returns:
            result (any, Attribute or list): A list of varying type depending
                on the arguments given.

        Raises:
            AttributeError: If `raise_exception` is set and no matching Attribute
                was found matching `key`.

        """

        class RetDefault(object):
            "Holds default values"
            def __init__(self):
                self.key = None
                self.value = default
                self.strvalue = str(default) if default is not None else None

        if self._cache is None or not _TYPECLASS_AGGRESSIVE_CACHE:
            self._recache()
        ret = []
        key = [k.strip().lower() for k in make_iter(key) if k]
        category = category.strip().lower() if category is not None else None
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
        repeat-calling add when having many Attributes to add.

        Args:
            key (list): A list of Attribute names to add.
            value (list): A list of values. It must match the `key`
                list.  If `strattr` keyword is set, all entries *must* be
                strings.
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

        Raises:
            RuntimeError: If `key` and `value` lists are not of the
                same lengths.
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

        Args:
            key (str): An Attribute key to remove.
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
        if self._cache is None or not _TYPECLASS_AGGRESSIVE_CACHE:
            self._recache()
        attrs = sorted(self._cache.values(), key=lambda o: o.id)
        if accessing_obj:
            return [attr for attr in attrs
                    if attr.access(accessing_obj, self._attredit, default=default_access)]
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
import fnmatch
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
    regex_string = regex_string[:-7] + r"(?:[\n\r]*?)\Z(?ms)"

    # validate the templates
    regex_args = [match.group(2) for match in _RE_NICK_ARG.finditer(regex_string)]
    temp_args = [match.group(2) for match in _RE_NICK_TEMPLATE_ARG.finditer(out_template)]
    if set(regex_args) != set(temp_args):
        # We don't have the same $-tags in input/output.
        raise NickTemplateInvalid

    regex_string = _RE_NICK_SPACE.sub("\s+", regex_string)
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
        super(NickHandler, self).__init__(*args, **kwargs)
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
        return super(NickHandler, self).has(key, category=category)

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
            return super(NickHandler, self).get(key=key, category=category, **kwargs)
        else:
            retval = super(NickHandler, self).get(key=key, category=category, **kwargs)
            return retval[3] if isinstance(retval, tuple) else [tup[3] for tup in make_iter(retval)]

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
        nick_regex, nick_template = initialize_nick_templates(key, replacement)
        super(NickHandler, self).add(key, (nick_regex, nick_template, key, replacement), category=category, **kwargs)

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
        super(NickHandler, self).remove(key, category=category, **kwargs)

    def nickreplace(self, raw_string, categories=("inputline", "channel"), include_player=True):
        """
        Apply nick replacement of entries in raw_string with nick replacement.

        Args:
            raw_string (str): The string in which to perform nick
                replacement.
            categories (tuple, optional): Replacement categories in
                which to perform the replacement, such as "inputline",
                "channel" etc.
            include_player (bool, optional): Also include replacement
                with nicks stored on the Player level.
            kwargs (any, optional): Not used.

        Returns:
            string (str): A string with matching keys replaced with
                their nick equivalents.

        """
        nicks = {}
        for category in make_iter(categories):
            nicks.update({nick.key: nick
              for nick in make_iter(self.get(category=category, return_obj=True)) if nick and nick.key})
        if include_player and self.obj.has_player:
            for category in make_iter(categories):
                nicks.update({nick.key: nick
                    for nick in make_iter(self.obj.player.nicks.get(category=category, return_obj=True))
                        if nick and nick.key})
        for key, nick in nicks.iteritems():
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
        self.obj.set_recache_protection()

    def remove(self, key):
        """
        Remove Nattribute from storage.

        Args:
            key (str): The name of the Nattribute to remove.

        """
        if key in self._store:
            del self._store[key]
        self.obj.set_recache_protection(self._store)

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
