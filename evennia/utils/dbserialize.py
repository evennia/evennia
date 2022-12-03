"""
This module handles serialization of arbitrary python structural data,
intended primarily to be stored in the database. It also supports
storing Django model instances (which plain pickle cannot do).

This serialization is used internally by the server, notably for
storing data in Attributes and for piping data to process pools.

The purpose of dbserialize is to handle all forms of data. For
well-structured non-arbitrary exchange, such as communicating with a
rich web client, a simpler JSON serialization makes more sense.

This module also implements the `SaverList`, `SaverDict` and `SaverSet`
classes. These are iterables that track their position in a nested
structure and makes sure to send updates up to their root. This is
used by Attributes - without it, one would not be able to update mutables
in-situ, e.g `obj.db.mynestedlist[3][5] = 3` would never be saved and
be out of sync with the database.

"""
from collections import OrderedDict, defaultdict, deque
from collections.abc import MutableMapping, MutableSequence, MutableSet
from functools import update_wrapper

try:
    from pickle import UnpicklingError, dumps, loads
except ImportError:
    from pickle import dumps, loads

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.utils.safestring import SafeString
from evennia.utils import logger
from evennia.utils.utils import is_iter, to_bytes, uses_database

__all__ = ("to_pickle", "from_pickle", "do_pickle", "do_unpickle", "dbserialize", "dbunserialize")

PICKLE_PROTOCOL = 2


# message to send if editing an already deleted Attribute in a savermutable
_ERROR_DELETED_ATTR = (
    "{cls_name} {obj} has had its root Attribute deleted. "
    "It must be cast to a {non_saver_name} before it can be modified further."
)


def _get_mysql_db_version():
    """
    This is a helper method for specifically getting the version
    string of a MySQL database.

    Returns:
        mysql_version (str): The currently used mysql database
            version.

    """
    from django.db import connection

    conn = connection.cursor()
    conn.execute("SELECT VERSION()")
    version = conn.fetchone()
    return version and str(version[0]) or ""


# initialization and helpers


_GA = object.__getattribute__
_SA = object.__setattr__
_FROM_MODEL_MAP = None
_TO_MODEL_MAP = None
_IGNORE_DATETIME_MODELS = None
_SESSION_HANDLER = None


def _IS_PACKED_DBOBJ(o):
    return isinstance(o, tuple) and len(o) == 4 and o[0] == "__packed_dbobj__"


def _IS_PACKED_SESSION(o):
    return isinstance(o, tuple) and len(o) == 3 and o[0] == "__packed_session__"


if uses_database("mysql") and _get_mysql_db_version() < "5.6.4":
    # mysql <5.6.4 don't support millisecond precision
    _DATESTRING = "%Y:%m:%d-%H:%M:%S:000000"
else:
    _DATESTRING = "%Y:%m:%d-%H:%M:%S:%f"


def _TO_DATESTRING(obj):
    """
    Creates datestring hash.

    Args:
        obj (Object): Database object.

    Returns:
        datestring (str): A datestring hash.

    """
    try:
        return _GA(obj, "db_date_created").strftime(_DATESTRING)
    except AttributeError:
        # this can happen if object is not yet saved - no datestring is then set
        try:
            obj.save()
        except AttributeError:
            # we have received a None object, for example due to an erroneous save.
            return None
        return _GA(obj, "db_date_created").strftime(_DATESTRING)


def _init_globals():
    """Lazy importing to avoid circular import issues"""
    global _FROM_MODEL_MAP, _TO_MODEL_MAP, _SESSION_HANDLER, _IGNORE_DATETIME_MODELS
    if not _FROM_MODEL_MAP:
        _FROM_MODEL_MAP = defaultdict(str)
        _FROM_MODEL_MAP.update(dict((c.model, c.natural_key()) for c in ContentType.objects.all()))
    if not _TO_MODEL_MAP:
        from django.conf import settings

        _TO_MODEL_MAP = defaultdict(str)
        _TO_MODEL_MAP.update(
            dict((c.natural_key(), c.model_class()) for c in ContentType.objects.all())
        )
        _IGNORE_DATETIME_MODELS = []
        for src_key, dst_key in settings.ATTRIBUTE_STORED_MODEL_RENAME:
            _TO_MODEL_MAP[src_key] = _TO_MODEL_MAP.get(dst_key, None)
            _IGNORE_DATETIME_MODELS.append(src_key)
    if not _SESSION_HANDLER:
        from evennia.server.sessionhandler import SESSION_HANDLER as _SESSION_HANDLER


#
# SaverList, SaverDict, SaverSet - Attribute-specific helper classes and functions
#


def _save(method):
    """method decorator that saves data to Attribute"""

    def save_wrapper(self, *args, **kwargs):
        self.__doc__ = method.__doc__
        ret = method(self, *args, **kwargs)
        self._save_tree()
        return ret

    return update_wrapper(save_wrapper, method)


class _SaverMutable:
    """
    Parent class for properly handling  of nested mutables in
    an Attribute. If not used something like
     obj.db.mylist[1][2] = "test" (allocation to a nested list)
    will not save the updated value to the database.
    """

    def __init__(self, *args, **kwargs):
        """store all properties for tracking the tree"""
        self._parent = kwargs.pop("_parent", None)
        self._db_obj = kwargs.pop("_db_obj", None)
        self._data = None

    def __bool__(self):
        """Make sure to evaluate as False if empty"""
        return bool(self._data)

    def _save_tree(self):
        """recursively traverse back up the tree, save when we reach the root"""
        if self._parent:
            self._parent._save_tree()
        elif self._db_obj:
            if not self._db_obj.pk:
                cls_name = self.__class__.__name__
                try:
                    non_saver_name = cls_name.split("_Saver", 1)[1].lower()
                except IndexError:
                    non_saver_name = cls_name
                raise ValueError(
                    _ERROR_DELETED_ATTR.format(
                        cls_name=cls_name, obj=self, non_saver_name=non_saver_name
                    )
                )
            self._db_obj.value = self
        else:
            logger.log_err("_SaverMutable %s has no root Attribute to save to." % self)

    def _convert_mutables(self, data):
        """converts mutables to Saver* variants and assigns ._parent property"""

        def process_tree(item, parent):
            """recursively populate the tree, storing parents"""
            dtype = type(item)
            if dtype in (str, int, float, bool, tuple):
                return item
            elif dtype == list:
                dat = _SaverList(_parent=parent)
                dat._data.extend(process_tree(val, dat) for val in item)
                return dat
            elif dtype == dict:
                dat = _SaverDict(_parent=parent)
                dat._data.update((key, process_tree(val, dat)) for key, val in item.items())
                return dat
            elif dtype == defaultdict:
                dat = _SaverDefaultDict(item.default_factory, _parent=parent)
                dat._data.update((key, process_tree(val, dat)) for key, val in item.items())
                return dat
            elif dtype == set:
                dat = _SaverSet(_parent=parent)
                dat._data.update(process_tree(val, dat) for val in item)
                return dat
            return item

        return process_tree(data, self)

    def __repr__(self):
        return self._data.__repr__()

    def __len__(self):
        return self._data.__len__()

    def __iter__(self):
        return self._data.__iter__()

    def __getitem__(self, key):
        return self._data.__getitem__(key)

    def __eq__(self, other):
        return self._data == other

    def __ne__(self, other):
        return self._data != other

    def __lt__(self, other):
        return self._data < other

    def __gt__(self, other):
        return self._data > other

    def __or__(self, other):
        return self._data | other

    def __ror__(self, other):
        return self._data | other

    @_save
    def __setitem__(self, key, value):
        self._data.__setitem__(key, self._convert_mutables(value))

    @_save
    def __delitem__(self, key):
        self._data.__delitem__(key)

    def deserialize(self):
        """Deserializes this mutable into its corresponding non-Saver type."""
        return deserialize(self)


class _SaverList(_SaverMutable, MutableSequence):
    """
    A list that saves itself to an Attribute when updated.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._data = kwargs.pop("_class", list)()

    @_save
    def __iadd__(self, otherlist):
        self._data = self._data.__add__(otherlist)
        return self._data

    def __add__(self, otherlist):
        return list(self._data) + otherlist

    @_save
    def insert(self, index, value):
        self._data.insert(index, self._convert_mutables(value))

    def __eq__(self, other):
        try:
            return list(self._data) == list(other)
        except TypeError:
            return False

    def __ne__(self, other):
        try:
            return list(self._data) != list(other)
        except TypeError:
            return True

    def index(self, value, *args):
        return self._data.index(value, *args)

    @_save
    def sort(self, *, key=None, reverse=False):
        self._data.sort(key=key, reverse=reverse)

    def copy(self):
        return self._data.copy()


class _SaverDict(_SaverMutable, MutableMapping):
    """
    A dict that stores changes to an Attribute when updated
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._data = kwargs.pop("_class", dict)()

    def has_key(self, key):
        return key in self._data

    @_save
    def update(self, *args, **kwargs):
        self._data.update(*args, **kwargs)


class _SaverDefaultDict(_SaverDict):
    """
    A defaultdict that stores changes to an attribute when updated
    """

    def __init__(self, factory, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._data = defaultdict(factory)
        self.default_factory = factory

    def __getitem__(self, key):
        if key not in self._data.keys():
            # detect the case of db.foo['a'] with no immediate assignment
            # (important: using `key in self._data` would be always True!)
            default_value = self._data[key]
            self.__setitem__(key, default_value)
        return self._data[key]


class _SaverSet(_SaverMutable, MutableSet):
    """
    A set that saves to an Attribute when updated
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._data = set()

    def __contains__(self, value):
        return self._data.__contains__(value)

    @_save
    def add(self, value):
        self._data.add(self._convert_mutables(value))

    @_save
    def discard(self, value):
        self._data.discard(value)

    @_save
    def update(self, *others):
        self._data.update(*others)

    @_save
    def remove(self, value):
        self._data.remove(value)

    @_save
    def pop(self):
        self._data.pop()

    @_save
    def clear(self):
        self._data.clear()

    @_save
    def intersection_update(self, *others):
        self._data.intersection_update(*others)

    @_save
    def difference_update(self, *others):
        self._data.difference_update(*others)

    @_save
    def symmetric_difference_update(self, *others):
        self._data.symmetric_difference(*others)

    def isdisjoint(self, other):
        return self._data.isdisjoint(other)

    def issubset(self, other):
        return self._data.issubset(other)

    def issuperset(self, other):
        return self._data.issuperset(other)

    def union(self, *others):
        return self._data.union(*others)

    def intersection(self, *others):
        return self._data.intersection(*others)

    def difference(self, *others):
        return self._data.difference(*others)

    def symmetric_difference(self, other):
        return self._data.symmetric_difference(other)

    def copy(self):
        return self._data.copy()


class _SaverOrderedDict(_SaverMutable, MutableMapping):
    """
    An ordereddict that can be saved and operated on.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._data = OrderedDict()

    def has_key(self, key):
        return key in self._data


class _SaverDeque(_SaverMutable):
    """
    A deque that can be saved and operated on.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._data = deque()

    @_save
    def append(self, *args, **kwargs):
        self._data.append(*args, **kwargs)

    @_save
    def appendleft(self, *args, **kwargs):
        self._data.appendleft(*args, **kwargs)

    @_save
    def clear(self):
        self._data.clear()

    @_save
    def extendleft(self, *args, **kwargs):
        self._data.extendleft(*args, **kwargs)

    # maxlen property
    def _getmaxlen(self):
        return self._data.maxlen

    def _setmaxlen(self, value):
        self._data.maxlen = value

    def _delmaxlen(self):
        del self._data.maxlen

    maxlen = property(_getmaxlen, _setmaxlen, _delmaxlen)

    @_save
    def pop(self, *args, **kwargs):
        return self._data.pop(*args, **kwargs)

    @_save
    def popleft(self, *args, **kwargs):
        return self._data.popleft(*args, **kwargs)

    @_save
    def reverse(self):
        self._data.reverse()

    @_save
    def rotate(self, *args):
        self._data.rotate(*args)

    @_save
    def remove(self, *args):
        self._data.remove(*args)


_DESERIALIZE_MAPPING = {
    _SaverList.__name__: list,
    _SaverDict.__name__: dict,
    _SaverSet.__name__: set,
    _SaverOrderedDict.__name__: OrderedDict,
    _SaverDeque.__name__: deque,
    _SaverDefaultDict.__name__: defaultdict,
}


def deserialize(obj):
    """
    Make sure to *fully* decouple a structure from the database, by turning all _Saver*-mutables
    inside it back into their normal Python forms.

    """

    def _iter(obj):
        # breakpoint()
        typ = type(obj)
        tname = typ.__name__
        if tname in ("_SaverDict", "dict"):
            return {_iter(key): _iter(val) for key, val in obj.items()}
        elif tname in ("_SaverOrderedDict", "OrderedDict"):
            return OrderedDict([(_iter(key), _iter(val)) for key, val in obj.items()])
        elif tname in ("_SaverDefaultDict", "defaultdict"):
            return defaultdict(
                obj.default_factory, {_iter(key): _iter(val) for key, val in obj.items()}
            )
        elif tname in _DESERIALIZE_MAPPING:
            return _DESERIALIZE_MAPPING[tname](_iter(val) for val in obj)
        elif is_iter(obj):
            return typ(_iter(val) for val in obj)
        return obj

    return _iter(obj)


#
# serialization helpers


def pack_dbobj(item):
    """
    Check and convert django database objects to an internal representation.

    Args:
        item (any): A database entity to pack

    Returns:
        packed (any or tuple): Either returns the original input item
            or the packing tuple `("__packed_dbobj__", key, creation_time, id)`.

    """
    _init_globals()
    obj = item
    natural_key = _FROM_MODEL_MAP[
        hasattr(obj, "id")
        and hasattr(obj, "db_date_created")
        and hasattr(obj, "__dbclass__")
        and obj.__dbclass__.__name__.lower()
    ]
    # build the internal representation as a tuple
    #  ("__packed_dbobj__", key, creation_time, id)
    return (
        natural_key
        and ("__packed_dbobj__", natural_key, _TO_DATESTRING(obj), _GA(obj, "id"))
        or item
    )


def unpack_dbobj(item):
    """
    Check and convert internal representations back to Django database
    models.

    Args:
        item (packed_dbobj): The fact that item is a packed dbobj
            should be checked before this call.

    Returns:
        unpacked (any): Either the original input or converts the
            internal store back to a database representation (its
            typeclass is returned if applicable).

    """
    _init_globals()
    try:
        obj = item[3] and _TO_MODEL_MAP[item[1]].objects.get(id=item[3])
    except ObjectDoesNotExist:
        return None
    except TypeError:
        if hasattr(item, "pk"):
            # this happens if item is already an obj
            return item
        return None
    if item[1] in _IGNORE_DATETIME_MODELS:
        # if we are replacing models we ignore the datatime
        return obj
    else:
        # even if we got back a match, check the sanity of the date (some
        # databases may 're-use' the id)
        return _TO_DATESTRING(obj) == item[2] and obj or None


def pack_session(item):
    """
    Handle the safe serializion of Sessions objects (these contain
    hidden references to database objects (accounts, puppets) so they
    can't be safely serialized).

    Args:
        item (Session)): This item must have all properties of a session
            before entering this call.

    Returns:
        packed (tuple or None): A session-packed tuple on the form
            `(__packed_session__, sessid, conn_time)`. If this sessid
            does not match a session in the Session handler, None is returned.

    """
    _init_globals()
    session = _SESSION_HANDLER.get(item.sessid)
    if session and session.conn_time == item.conn_time:
        # we require connection times to be identical for the Session
        # to be accepted as actually being a session (sessids gets
        # reused all the time).
        return (
            item.conn_time
            and item.sessid
            and ("__packed_session__", _GA(item, "sessid"), _GA(item, "conn_time"))
        )
    return None


def unpack_session(item):
    """
    Check and convert internal representations back to Sessions.

    Args:
        item (packed_session): The fact that item is a packed session
            should be checked before this call.

    Returns:
        unpacked (any): Either the original input or converts the
            internal store back to a Session. If Session no longer
            exists, None will be returned.
    """
    _init_globals()
    session = _SESSION_HANDLER.get(item[1])
    if session and session.conn_time == item[2]:
        # we require connection times to be identical for the Session
        # to be accepted as the same as the one stored (sessids gets
        # reused all the time).
        return session
    return None


#
# Access methods


def to_pickle(data):
    """
    This prepares data on arbitrary form to be pickled. It handles any
    nested structure and returns data on a form that is safe to pickle
    (including having converted any database models to their internal
    representation).  We also convert any Saver*-type objects back to
    their normal representations, they are not pickle-safe.

    Args:
        data (any): Data to pickle.

    Returns:
        data (any): Pickled data.

    """

    def process_item(item):
        """Recursive processor and identification of data"""

        dtype = type(item)

        if dtype in (str, int, float, bool, bytes, SafeString):
            return item
        elif dtype == tuple:
            return tuple(process_item(val) for val in item)
        elif dtype in (list, _SaverList):
            return [process_item(val) for val in item]
        elif dtype in (dict, _SaverDict):
            return dict((process_item(key), process_item(val)) for key, val in item.items())
        elif dtype in (defaultdict, _SaverDefaultDict):
            return defaultdict(
                item.default_factory,
                ((process_item(key), process_item(val)) for key, val in item.items()),
            )
        elif dtype in (set, _SaverSet):
            return set(process_item(val) for val in item)
        elif dtype in (OrderedDict, _SaverOrderedDict):
            return OrderedDict((process_item(key), process_item(val)) for key, val in item.items())
        elif dtype in (deque, _SaverDeque):
            return deque(process_item(val) for val in item)

        # not one of the base types
        if hasattr(item, "__serialize_dbobjs__"):
            # Allows custom serialization of any dbobjects embedded in
            # the item that Evennia will otherwise not find (these would
            # otherwise lead to an error). Use the dbserialize helper from
            # this method.
            try:
                item.__serialize_dbobjs__()
            except TypeError as err:
                # we catch typerrors so we can handle both classes (requiring
                # classmethods) and instances
                pass

        if hasattr(item, "__iter__"):
            try:
                # we try to conserve the iterable class, if not convert to dict
                try:
                    return item.__class__(
                        (process_item(key), process_item(val)) for key, val in item.items()
                    )
                except (AttributeError, TypeError):
                    return {process_item(key): process_item(val) for key, val in item.items()}
            except Exception:
                # we try to conserve the iterable class, if not convert to list
                try:
                    return item.__class__([process_item(val) for val in item])
                except (AttributeError, TypeError):
                    return [process_item(val) for val in item]
        elif hasattr(item, "sessid") and hasattr(item, "conn_time"):
            return pack_session(item)
        try:
            return pack_dbobj(item)
        except TypeError:
            return item
        except Exception:
            logger.log_err(f"The object {item} of type {type(item)} could not be stored.")
            raise

    return process_item(data)


# @transaction.autocommit
def from_pickle(data, db_obj=None):
    """
    This should be fed a just de-pickled data object. It will be converted back
    to a form that may contain database objects again. Note that if a database
    object was removed (or changed in-place) in the database, None will be
    returned.

    Args:
        data (any): Pickled data to unpickle.
        db_obj (Atribute, any): This is the model instance (normally
            an Attribute) that _Saver*-type iterables (_SaverList etc)
            will save to when they update. It must have a 'value' property
            that saves assigned data to the database. Skip if not
            serializing onto a given object.  If db_obj is given, this
            function will convert lists, dicts and sets to their
            _SaverList, _SaverDict and _SaverSet counterparts.

    Returns:
        data (any): Unpickled data.

    """

    def process_item(item):
        """Recursive processor and identification of data"""
        # breakpoint()
        dtype = type(item)
        if dtype in (str, int, float, bool, bytes, SafeString):
            return item
        elif _IS_PACKED_DBOBJ(item):
            # this must be checked before tuple
            return unpack_dbobj(item)
        elif _IS_PACKED_SESSION(item):
            return unpack_session(item)
        elif dtype == tuple:
            return tuple(process_item(val) for val in item)
        elif dtype == dict:
            return dict((process_item(key), process_item(val)) for key, val in item.items())
        elif dtype == defaultdict:
            return defaultdict(
                item.default_factory,
                ((process_item(key), process_item(val)) for key, val in item.items()),
            )
        elif dtype == set:
            return set(process_item(val) for val in item)
        elif dtype == OrderedDict:
            return OrderedDict((process_item(key), process_item(val)) for key, val in item.items())
        elif dtype == deque:
            return deque(process_item(val) for val in item)
        elif hasattr(item, "__iter__"):
            try:
                # we try to conserve the iterable class, if not convert to dict
                try:
                    return item.__class__(
                        (process_item(key), process_item(val)) for key, val in item.items()
                    )
                except (AttributeError, TypeError):
                    return {process_item(key): process_item(val) for key, val in item.items()}
            except Exception:
                try:
                    # we try to conserve the iterable class if
                    # it accepts an iterator
                    return item.__class__(process_item(val) for val in item)
                except (AttributeError, TypeError):
                    return [process_item(val) for val in item]

        if hasattr(item, "__deserialize_dbobjs__"):
            # this allows the object to custom-deserialize any embedded dbobjs
            # that we previously serialized with __serialize_dbobjs__.
            # use the dbunserialize helper in this module.
            try:
                item.__deserialize_dbobjs__()
            except (TypeError, UnpicklingError):
                # handle recoveries both of classes (requiring classmethods
                # or instances. Unpickling errors can happen when re-loading the
                # data from cache (because the hidden entity was already
                # deserialized and stored back on the object, unpickling it
                # again fails). TODO: Maybe one could avoid this retry in a
                # more graceful way?
                pass

        return item

    def process_tree(item, parent):
        """Recursive processor, building a parent-tree from iterable data"""
        # breakpoint()
        dtype = type(item)
        if dtype in (str, int, float, bool, bytes, SafeString):
            return item
        elif _IS_PACKED_DBOBJ(item):
            # this must be checked before tuple
            return unpack_dbobj(item)
        elif dtype == tuple:
            return tuple(process_tree(val, item) for val in item)
        elif dtype == list:
            dat = _SaverList(_parent=parent)
            dat._data.extend(process_tree(val, dat) for val in item)
            return dat
        elif dtype == dict:
            dat = _SaverDict(_parent=parent)
            dat._data.update(
                (process_item(key), process_tree(val, dat)) for key, val in item.items()
            )
            return dat
        elif dtype == defaultdict:
            dat = _SaverDefaultDict(item.default_factory, _parent=parent)
            dat._data.update(
                (process_item(key), process_tree(val, dat)) for key, val in item.items()
            )
            return dat
        elif dtype == set:
            dat = _SaverSet(_parent=parent)
            dat._data.update(set(process_tree(val, dat) for val in item))
            return dat
        elif dtype == OrderedDict:
            dat = _SaverOrderedDict(_parent=parent)
            dat._data.update(
                (process_item(key), process_tree(val, dat)) for key, val in item.items()
            )
            return dat
        elif dtype == deque:
            dat = _SaverDeque(_parent=parent)
            dat._data.extend(process_item(val) for val in item)
            return dat
        elif hasattr(item, "__iter__"):
            try:
                # we try to conserve the iterable class, if not convert to dict
                try:
                    dat = _SaverDict(_parent=parent, _class=item.__class__)
                    dat._data.update(
                        (process_item(key), process_tree(val, dat)) for key, val in item.items()
                    )
                    return dat
                except (AttributeError, TypeError):
                    dat = _SaverDict(_parent=parent)
                    dat._data.update(
                        (process_item(key), process_tree(val, dat)) for key, val in item.items()
                    )
                    return dat
            except Exception:
                try:
                    # we try to conserve the iterable class if it
                    # accepts an iterator
                    dat = _SaverList(_parent=parent, _class=item.__class__)
                    dat._data.extend(process_tree(val, dat) for val in item)
                    return dat
                except (AttributeError, TypeError):
                    dat = _SaverList(_parent=parent)
                    dat._data.extend(process_tree(val, dat) for val in item)
                    return dat

        if hasattr(item, "__deserialize_dbobjs__"):
            try:
                item.__deserialize_dbobjs__()
            except (TypeError, UnpicklingError):
                pass

        return item

    if db_obj:
        # convert lists, dicts and sets to their Saved* counterparts. It
        # is only relevant if the "root" is an iterable of the right type.
        dtype = type(data)
        if dtype in (str, int, float, bool, bytes, SafeString, tuple):
            return process_item(data)
        elif dtype == list:
            dat = _SaverList(_db_obj=db_obj)
            dat._data.extend(process_tree(val, dat) for val in data)
            return dat
        elif dtype == dict:
            dat = _SaverDict(_db_obj=db_obj)
            dat._data.update(
                (process_item(key), process_tree(val, dat)) for key, val in data.items()
            )
            return dat
        elif dtype == defaultdict:
            dat = _SaverDefaultDict(data.default_factory, _db_obj=db_obj)
            dat._data.update(
                (process_item(key), process_tree(val, dat)) for key, val in data.items()
            )
            return dat
        elif dtype == set:
            dat = _SaverSet(_db_obj=db_obj)
            dat._data.update(process_tree(val, dat) for val in data)
            return dat
        elif dtype == OrderedDict:
            dat = _SaverOrderedDict(_db_obj=db_obj)
            dat._data.update(
                (process_item(key), process_tree(val, dat)) for key, val in data.items()
            )
            return dat
        elif dtype == deque:
            dat = _SaverDeque(_db_obj=db_obj)
            dat._data.extend(process_item(val) for val in data)
            return dat
        elif hasattr(data, "__iter__"):
            try:
                # we try to conserve the iterable class, if not convert to dict
                try:
                    dat = _SaverDict(_db_obj=db_obj, _class=data.__class__)
                    dat._data.update(
                        (process_item(key), process_tree(val, dat)) for key, val in data.items()
                    )
                    return dat
                except (AttributeError, TypeError):
                    dat = _SaverDict(_db_obj=db_obj)
                    dat._data.update(
                        (process_item(key), process_tree(val, dat)) for key, val in data.items()
                    )
                    return dat
            except Exception:
                try:
                    # we try to conserve the iterable class if it
                    # accepts an iterator
                    dat = _SaverList(_db_obj=db_obj, _class=data.__class__)
                    dat._data.extend(process_tree(val, dat) for val in data)
                    return dat

                except (AttributeError, TypeError):
                    dat = _SaverList(_db_obj=db_obj)
                    dat._data.extend(process_tree(val, dat) for val in data)
                    return dat

    return process_item(data)


def do_pickle(data):
    """Perform pickle to string"""
    try:
        return dumps(data, protocol=PICKLE_PROTOCOL)
    except Exception:
        logger.log_err(f"Could not pickle data for storage: {data}")
        raise


def do_unpickle(data):
    """Retrieve pickle from pickled string"""
    try:
        return loads(to_bytes(data))
    except Exception:
        logger.log_err(f"Could not unpickle data from storage: {data}")
        raise


def dbserialize(data):
    """Serialize to pickled form in one step"""
    return do_pickle(to_pickle(data))


def dbunserialize(data, db_obj=None):
    """Un-serialize in one step. See from_pickle for help db_obj."""
    return from_pickle(do_unpickle(data), db_obj=db_obj)
