"""
This implements the common managers that are used by the
abstract models in dbobjects.py (and which are thus shared by
all Attributes and TypedObjects).
"""
from functools import update_wrapper
from django.db import models
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from src.utils import idmapper
from src.utils.utils import make_iter, variable_from_module
from src.utils.dbserialize import to_pickle

__all__ = ("AttributeManager", "TypedObjectManager")
_GA = object.__getattribute__
_ObjectDB = None

#
# helper functions for the TypedObjectManager.
#

def returns_typeclass_list(method):
    """
    Decorator: Changes return of the decorated method (which are
    TypeClassed objects) into object_classes(s) instead.  Will always
    return a list (may be empty).
    """
    def func(self, *args, **kwargs):
        "decorator. Returns a list."
        self.__doc__ = method.__doc__
        matches = make_iter(method(self, *args, **kwargs))
        return [(hasattr(dbobj, "typeclass") and dbobj.typeclass) or dbobj
                                               for dbobj in make_iter(matches)]
    return update_wrapper(func, method)


def returns_typeclass(method):
    """
    Decorator: Will always return a single typeclassed result or None.
    """
    def func(self, *args, **kwargs):
        "decorator. Returns result or None."
        self.__doc__ = method.__doc__
        matches = method(self, *args, **kwargs)
        dbobj = matches and make_iter(matches)[0] or None
        if dbobj:
            return (hasattr(dbobj, "typeclass") and dbobj.typeclass) or dbobj
        return None
    return update_wrapper(func, method)

# Managers

def _attr_pickled(method):
    """
    decorator for safely handling attribute searches
    - db_value is a pickled field and this is required
    in order to be able for pickled django objects directly.
    """
    def wrapper(self, *args, **kwargs):
        "wrap all queries searching the db_value field in some way"
        self.__doc__ = method.__doc__
        for key in (key for key in kwargs if key.startswith('db_value')):
            kwargs[key] = to_pickle(kwargs[key])
        return method(self, *args, **kwargs)
    return update_wrapper(wrapper, method)


class AttributeManager(models.Manager):
    "Manager for handling Attributes."
    @_attr_pickled
    def get(self, *args, **kwargs):
        return super(AttributeManager, self).get(*args, **kwargs)
    @_attr_pickled

    def filter(self,*args, **kwargs):
        return super(AttributeManager, self).filter(*args, **kwargs)
    @_attr_pickled

    def exclude(self,*args, **kwargs):
        return super(AttributeManager, self).exclude(*args, **kwargs)
    @_attr_pickled

    def values(self,*args, **kwargs):
        return super(AttributeManager, self).values(*args, **kwargs)
    @_attr_pickled

    def values_list(self,*args, **kwargs):
        return super(AttributeManager, self).values_list(*args, **kwargs)
    @_attr_pickled

    def exists(self,*args, **kwargs):
        return super(AttributeManager, self).exists(*args, **kwargs)

    def get_attrs_on_obj(self, searchstr, obj, category=None, exact_match=True):
        """
        Searches the object's attributes for attribute key matches.

        searchstr: (str) A string to search for.
        """
        # Retrieve the list of attributes for this object.

        category_cond = Q(db_category__iexact=category) if category else Q()
        if exact_match:
            return _GA("obj", "db_attributes").filter(db_key__iexact=searchstr & category_cond)
        else:
            return _GA("obj", "db_attributes").filter(db_key__icontains=searchstr & category_cond)

    def attr_namesearch(self, *args, **kwargs):
        "alias wrapper for backwards compatability"
        return self.get_attrs_on_obj(*args, **kwargs)

    def get_attr_by_value(self, searchstr, obj=None):
        """
        Searches obj for Attributes with a given value.
        searchstr - value to search for. This may be any suitable object.
        obj - limit to a given object instance

        If no restraint is given, all Attributes on all types of objects
                will be searched. It's highly recommended to at least
                supply the objclass argument (DBObject, DBScript or DBPlayer)
                to restrict this lookup.
        """
        if obj:
            return _GA(obj, "db_attributes").filter(db_value=searchstr)
        return self.filter(db_value=searchstr)

    def attr_valuesearch(self, *args, **kwargs):
        "alias wrapper for backwards compatability"
        return self.get_attr_by_value(self, *args, **kwargs)

#
# TagManager
#

class TagManager(models.Manager):
    """
    Extra manager methods for Tags
    """
    def get_tags_on_obj(self, obj, key=None, category=None):
        """
        Get all tags on obj, optionally limited by key and/or category
        """
        tags = _GA(obj, "db_tags").all()
        if key:
            tags = tags.filter(db_key__iexact=key.lower().strip())
        if category:
            tags = tags.filter(db_category__iexact=category.lower().strip())
        return list(tags)

    def get_tag(self, key=None, category=None, model="objects.objectdb", tagtype=None):
        """
        Search and return all tags matching any combination of
        the search criteria.
         search_key (string) - the tag identifier
         category (string) - the tag category
         model - the type of object tagged, on naturalkey form, like "objects.objectdb"
         tagtype - None, alias or permission

        Returns a single Tag (or None) if both key and category is given,
        otherwise it will return a list.
        """
        key_cands = Q(db_key__iexact=key.lower().strip()) if key is not None else Q()
        cat_cands = Q(db_category__iexact=category.lower().strip()) if category is not None else Q()
        tags = self.filter(db_model=model, db_tagtype=tagtype).filter(key_cands & cat_cands)
        if key and category:
            return tags[0] if tags else None
        else:
            return list(tags)

    @returns_typeclass_list
    def get_objs_with_tag(self, key=None, category=None, model="objects.objectdb", tagtype=None):
        """
        Search and return all objects of objclass that has tags matching
        the given search criteria.
         key (string) - the tag identifier
         category (string) - the tag category
         model (string) - tag model name. Defaults to "ObjectDB"
         tagtype (string) - None, alias or permission
         objclass (dbmodel) - the object class to search. If not given, use ObjectDB.
        """
        objclass = ContentType.objects.get_by_natural_key(*model.split(".", 1)).model_class()
        key_cands = Q(db_tags__db_key__iexact=key.lower().strip()) if key is not None else Q()
        cat_cands = Q(db_tags__db_category__iexact=category.lower().strip()) if category is not None else Q()
        tag_crit = Q(db_tags__db_model=model, db_tags__db_tagtype=tagtype)
        return objclass.objects.filter(tag_crit & key_cands & cat_cands)

    def create_tag(self, key=None, category=None, data=None, model="objects.objectdb", tagtype=None):
        """
        Create a tag. This makes sure the create case-insensitive tags.
        Note that if the exact same tag configuration (key+category+model+tagtype)
        exists, it will be re-used. A data keyword will overwrite existing
        data on a tag (it is not part of what makes the tag unique).

        """
        data = str(data) if data is not None else None

        tag = self.get_tag(key=key, category=category, model=model, tagtype=tagtype)
        if tag and data is not None:
            tag.db_data = data
            tag.save()
        elif not tag:
            tag = self.create(db_key=key.lower().strip() if key is not None else None,
                              db_category=category.lower().strip() if category and key is not None else None,
                              db_data=str(data) if data is not None else None,
                              db_model=model,
                              db_tagtype=tagtype)
            tag.save()
        return make_iter(tag)[0]




#class TypedObjectManager(idmap.CachingManager):
#class TypedObjectManager(models.Manager):
class TypedObjectManager(idmapper.manager.SharedMemoryManager):
    """
    Common ObjectManager for all dbobjects.
    """

    def dbref(self, dbref, reqhash=True):
        """
        Valid forms of dbref (database reference number)
        are either a string '#N' or an integer N.
        Output is the integer part.
        reqhash - require input to be on form "#N" to be
        identified as a dbref
        """
        if reqhash and not (isinstance(dbref, basestring) and dbref.startswith("#")):
            return None
        if isinstance(dbref, basestring):
            dbref = dbref.lstrip('#')
        try:
            if int(dbref) < 0:
                return None
        except Exception:
            return None
        return dbref

    @returns_typeclass
    def get_id(self, dbref):
        """
        Find object with given dbref
        """
        dbref = self.dbref(dbref, reqhash=False)
        try:
            return self.get(id=dbref)
        except self.model.DoesNotExist:
            pass
        return None

    def dbref_search(self, dbref):
        """
        Alias to get_id
        """
        return self.get_id(dbref)

    @returns_typeclass_list
    def get_dbref_range(self, min_dbref=None, max_dbref=None):
        """
        Return all objects inside and including the
        given boundaries.
        """
        retval = super(TypedObjectManager, self).all()
        if min_dbref is not None:
            retval = retval.filter(id__gte=self.dbref(min_dbref, reqhash=False))
        if max_dbref is not None:
            retval = retval.filter(id__lte=self.dbref(max_dbref, reqhash=False))
        return retval

    def object_totals(self):
        """
        Returns a dictionary with all the typeclasses active in-game
        as well as the number of such objects defined (i.e. the number
        of database object having that typeclass set on themselves).
        """
        dbtotals = {}
        typeclass_paths = set(self.values_list('db_typeclass_path', flat=True))
        for typeclass_path in typeclass_paths:
            dbtotals[typeclass_path] = \
               self.filter(db_typeclass_path=typeclass_path).count()
        return dbtotals

    @returns_typeclass_list
    def typeclass_search(self, typeclass, include_children=False, include_parents=False):
        """
        Searches through all objects returning those which has a
        certain typeclass. If location is set, limit search to objects
        in that location.

        typeclass - a typeclass class or a python path to a typeclass
        include_children - return objects with given typeclass and all
                       children inheriting from this typeclass.
        include_parents - return objects with given typeclass and all
                       parents to this typeclass
        The include_children/parents keywords are mutually exclusive.
        """

        if callable(typeclass):
            cls = typeclass.__class__
            typeclass = "%s.%s" % (cls.__module__, cls.__name__)
        elif not isinstance(typeclass, basestring) and hasattr(typeclass, "path"):
            typeclass = typeclass.path

        # query objects of exact typeclass
        query = Q(db_typeclass_path__exact=typeclass)

        if include_children:
            # build requests for child typeclass objects
            clsmodule, clsname = typeclass.rsplit(".", 1)
            cls = variable_from_module(clsmodule, clsname)
            subclasses = cls.__subclasses__()
            if subclasses:
                for child in (child for child in subclasses if hasattr(child, "path")):
                    query = query | Q(db_typeclass_path__exact=child.path)
        elif include_parents:
            # build requests for parent typeclass objects
            clsmodule, clsname = typeclass.rsplit(".", 1)
            cls = variable_from_module(clsmodule, clsname)
            parents = cls.__mro__
            if parents:
                for parent in (parent for parent in parents if hasattr(parent, "path")):
                    query = query | Q(db_typeclass_path__exact=parent.path)
        # actually query the database
        return self.filter(query)
