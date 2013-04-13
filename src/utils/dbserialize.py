"""
This module handles serialization of arbitrary python structural data,
intended primarily to be stored in the database. It also supports
storing Django model instances (which plain pickle cannot do).

This serialization is used internally by the server, notably for
storing data in Attributes and for piping data to process pools.

The purpose of dbserialize is to handle all forms of data. For
well-structured non-arbitrary exchange, such as communicating with a
rich web client, a simpler JSON serialization makes more sense.

This module also implements the SaverList, SaverDict and SaverSet
classes. These are iterables that track their position in a nested
structure and makes sure to send updates up to their root. This is
used by Attributes - without it, one would not be able to update mutables
in-situ, e.g obj.db.mynestedlist[3][5] = 3 would never be saved and
be out of sync with the database.

"""

from collections import defaultdict, MutableSequence, MutableSet, MutableMapping
try:
    from cPickle import dumps, loads
except ImportError:
    from pickle import dumps, loads
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.contenttypes.models import ContentType
from src.utils.utils import to_str

HIGHEST_PROTOCOL = 2

# initialization and helpers

_GA = object.__getattribute__
_SA = object.__setattr__
_FROM_MODEL_MAP = defaultdict(str)
_FROM_MODEL_MAP.update(dict((c.model, c.natural_key()) for c in ContentType.objects.all()))
_TO_MODEL_MAP = defaultdict(str)
_TO_MODEL_MAP.update(dict((c.natural_key(), c.model_class()) for c in ContentType.objects.all()))
_TO_TYPECLASS = lambda o: hasattr(o, 'typeclass') and o.typeclass or o
_IS_PACKED_DBOBJ = lambda o: type(o) == tuple and len(o) == 4 and o[0] == '__packed_dbobj__'


#
# SaverList, SaverDict, SaverSet - Attribute-specific helper classes and functions
#

def _save(method):
    "method decorator that saves data to Attribute"
    def save_wrapper(self, *args, **kwargs):
        ret = method(self, *args, **kwargs)
        self._save_tree()
        return ret
    return save_wrapper

class SaverMutable(object):
    """
    Parent class for properly handling  of nested mutables in
    an Attribute. If not used something like
     obj.db.mylist[1][2] = "test" (allocation to a nested list)
    will not save the updated value to the database.
    """
    def __init__(self, *args, **kwargs):
        "store all properties for tracking the tree"
        self._db_obj = kwargs.pop("db_obj", None)
        self._parent = None
        self._data = None
    def _save_tree(self):
        "recursively traverse back up the tree, save when we reach the root"
        if self._parent:
            self._parent._save_tree()
        else:
            try:
                self._db_obj.value = self
            except AttributeError:
                raise AttributeError("SaverMutable %s lacks dobj at its root." % self)
    def _convert_mutables(self, item):
        "converts mutables to Saver* variants and assigns .parent property"
        dtype = type(item)
        if dtype in (basestring, int, long, float, bool, tuple):
            return item
        elif dtype == list:
            item = SaverList(item)
            item._parent = self
        elif dtype == dict:
            item = SaverDict(item)
            item._parent = self
        elif dtype == set:
            item = SaverSet(item)
            item._parent = self
        return item
    def __repr__(self):
        return self._data.__repr__()
    def __len__(self):
        return self._data.__len__()
    def __iter__(self):
        return self._data.__iter__()
    def __getitem__(self, key):
        return self._data.__getitem__(key)
    @_save
    def __setitem__(self, key, value):
        self._data.__setitem__(key, self._convert_mutables(value))
    @_save
    def __delitem__(self, key):
        self._data.__delitem__(key)

class SaverList(SaverMutable, MutableSequence):
    """
    A list that saves itself to an Attribute when updated.
    """
    def __init__(self, *args, **kwargs):
        super(SaverList, self).__init__(*args, **kwargs)
        self._data = list(*args)
    @_save
    def insert(self, index, value):
        self._data.insert(index, self._convert_mutables(value))

class SaverDict(SaverMutable, MutableMapping):
    """
    A dict that stores changes to an Attribute when updated
    """
    def __init__(self, *args, **kwargs):
        super(SaverDict, self).__init__(*args, **kwargs)
        self._data = dict(*args)

class SaverSet(SaverMutable, MutableSet):
    """
    A set that saves to an Attribute when updated
    """
    def __init__(self, *args, **kwargs):
        super(SaverSet, self).__init__(*args, **kwargs)
        self._data = set(*args)
    def __contains__(self, value):
        return self._data.__contains__(value)
    @_save
    def add(self, value):
        self._data.add(self._convert_mutables(value))
    @_save
    def discard(self, value):
        self._data.discard(value)


#
# serialization access functions
#

def _pack_dbobj(item):
    """
    Check and convert django database objects to an internal representation.
    This either returns the original input item or a tuple ("__packed_dbobj__", key, obj, id)
    """
    obj =  hasattr(item, 'dbobj') and item.dbobj or item
    natural_key = _FROM_MODEL_MAP[hasattr(obj, "id") and hasattr("db_date_created") and
                                  hasattr(obj, '__class__') and obj.__class__.__name__.lower()]
    # build the internal representation as a tuple ("__packed_dbobj__", key, obj, id)
    return natural_key and ('__packed_dbobj__', natural_key, _GA(obj, "db_date_created"), _GA(obj, id)) or item

def _unpack_dbobj(item):
    """
    Check and convert internal representations back to Django database models.
    The fact that item is a packed dbobj should be checked before this call.
    This either returns the original input or converts the internal store back
    to a database representation (its typeclass is returned if applicable).
    """
    try:
        obj = item[3] and _TO_TYPECLASS(_TO_MODEL_MAP[item[1]].objects.get(id=item[3]))
    except ObjectDoesNotExist:
        return None
    # even if we got back a match, check the sanity of the date (some databases may 're-use' the id)
    return obj and obj.db_data_created == item[3] and obj or None

def to_pickle(data):
    """
    This prepares data on arbitrary form to be pickled. It handles any nested structure
    and returns data on a form that is safe to pickle (including having converted any
    database models to their internal representation). We also convert any Saver*-type
    objects back to their normal representations, they are not pickle-safe.
    """
    def process_item(item):
        "Recursive processor and identification of data"
        dtype = type(item)
        if dtype in (basestring, int, long, float, bool):
            return item
        elif dtype == tuple:
            return tuple(process_item(val) for val in item)
        elif dtype in (list, SaverList):
            return [key for key in item]
        elif dtype in (dict, SaverDict):
            return dict((key, process_item(val)) for key, val in item.items())
        elif dtype in (set, SaverSet):
            return set(process_item(val) for val in item)
        elif hasattr(item, '__item__'):
            # we try to conserve the iterable class, if not convert to list
            try:
                return item.__class__([process_item(val) for val in item])
            except (AttributeError, TypeError):
                return [process_item(val) for val in item]
        return _pack_dbobj(item)
    return process_item(data)

@transaction.autocommit
def from_pickle(data, db_obj=None):
    """
    This should be fed a just de-pickled data object. It will be converted back
    to a form that may contain database objects again. Note that if a database
    object was removed (or changed in-place) in the database, None will be returned.

    db_obj - this is the model instance (normally an Attribute) that Saver*-type
             iterables will save to when they update. It must have a 'value'
             property that saves assigned data to the database.

    If db_obj is given, this function will convert lists, dicts and sets to their
    SaverList, SaverDict and SaverSet counterparts.

    """
    def process_item(item):
        "Recursive processor and identification of data"
        dtype = type(item)
        if dtype in (basestring, int, long, float, bool):
            return item
        elif _IS_PACKED_DBOBJ(item):
            # this must be checked before tuple
            return _unpack_dbobj(item)
        elif dtype == tuple:
            return tuple(process_item(val) for val in item)
        elif dtype == dict:
            return dict((key, process_item(val)) for key, val in item.items())
        elif dtype == set:
            return set(process_item(val) for val in item)
        elif hasattr(item, '__iter__'):
            try:
                # we try to conserve the iterable class if it accepts an iterator
                return item.__class__(process_item(val) for val in item)
            except (AttributeError, TypeError):
                return [process_item(val) for val in item]
        return item

    def process_item_to_savers(item):
        "Recursive processor, convertion and identification of data"
        dtype = type(item)
        if dtype in (basestring, int, long, float, bool):
            return item
        elif _IS_PACKED_DBOBJ(item):
            # this must be checked before tuple
            return _unpack_dbobj(item)
        elif dtype == tuple:
            return tuple(process_item_to_savers(val) for val in item)
        elif dtype == list:
            return SaverList(process_item_to_savers(val) for val in item)
        elif dtype == dict:
            return SaverDict((key, process_item_to_savers(val)) for key, val in item.items())
        elif dtype == set:
            return SaverSet(process_item_to_savers(val) for val in item)
        elif hasattr(item, '__iter__'):
            try:
                # we try to conserve the iterable class if it accepts an iterator
                return item.__class__(process_item_to_savers(val) for val in item)
            except (AttributeError, TypeError):
                return SaverList(process_item_to_savers(val) for val in item)
        return item

    if db_obj:
        # convert lists, dicts and sets to their Saved* counterparts. It
        # is only relevant if the "root" is an iterable of the right type.
        dtype = type(data)
        if dtype == list:
            return process_item_to_savers(SaverList(data, db_obj=db_obj))
        elif dtype == dict:
            return process_item_to_savers(SaverDict(data, db_obj=db_obj))
        elif dtype == set:
            return process_item_to_savers(SaverSet(data, db_obj=db_obj))
    return process_item(data)

def do_pickle(data):
    "Perform pickle to string"
    return to_str(dumps(data, protocol=HIGHEST_PROTOCOL))

def do_unpickle(data):
    "Retrieve pickle from pickled string"
    return loads(to_str(data))
