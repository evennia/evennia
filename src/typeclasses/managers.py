"""
This implements the common managers that are used by the
abstract models in dbobjects.py (and which are thus shared by
all Attributes and TypedObjects).
"""
from functools import update_wrapper
from django.db import models
from django.db.models import Q
from src.utils import idmapper
from src.utils.utils import make_iter
from src.utils.dbserialize import to_pickle

__all__ = ("AttributeManager", "TypedObjectManager")
_GA = object.__getattribute__

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

    def get_attrs_on_obj(self, searchstr, obj, exact_match=True):
        """
        Searches the object's attributes for attribute key matches.

        searchstr: (str) A string to search for.
        """
        # Retrieve the list of attributes for this object.

        if exact_match:
            return _GA("obj", "db_attributes").filter(db_key__iexact=searchstr)
        else:
            return _GA("obj", "db_attributes").filter(db_key__icontains=searchstr)

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
# LiteAttributeManager
#

class LiteAttributeManager(models.Manager):
    """
    Manager methods for LiteAttributes
    """
    def get_lattrs_on_obj(self, obj, search_key=None, category=None):
        """
        Get all lattrs on obj, optionally limited by key and/or category
        """
        if search_key or category:
            key_cands = Q(db_key__iexact=search_key.lower().strip()) if search_key!=None else Q()
            cat_cands = Q(db_category__iexact=category.lower.strip()) if search_key!=None else Q()
            return _GA(obj, "db_liteattributes").filter(cat_cands & key_cands)
        else:
            return list(_GA(obj, "db_liteattributes").all())

    def get_lattr(self, search_key=None, category=None):
        """
        Search and return all liteattrs matching any combination of
        the search criteria.
         search_key (string) - the lattr identifier
         category (string) - the lattr category
        """
        key_cands = Q(db_key__iexact=search_key.lower().strip()) if search_key!=None else Q()
        cat_cands = Q(db_category__iexact=category.lower.strip()) if search_key!=None else Q()
        return list(self.filter(key_cands & cat_cands))

    def get_lattr_data(self, obj=None, search_key=None, category=None):
        """
        Retrieve data from found lattrs in an efficient way. Returns a list of data
        matching the search criterions
        """
        key_cands = Q(db_key__iexact=search_key.lower().strip()) if search_key!=None else Q()
        cat_cands = Q(db_category__iexact=category.lower.strip()) if search_key!=None else Q()
        if obj:
            query = _GA(obj, "db_liteattributes").filter(key_cands & cat_cands).prefetch_related("db_data")
        else:
            query = self.filter(key_cands & cat_cands).prefetch_related("db_data")
        return [q.db_data for q in query]

    def create_lattr(self, key, category=None, data=None, obj=None):
        """
        Create a LiteAttribute. This makes sure the create case-insensitive keys.
        """

        lattr = self.objects.create(db_key=key.lower().strip(),
                                    db_category=category.lower().strip() if category!=None else None,
                                    db_data=str(data) if data!=None else None)
        lattr.save()
        if obj:
            obj.db_liteattributes.add(lattr)
        return lattr

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
        if key or category:
            key_cands = Q(db_key__iexact=key.lower().strip()) if key!=None else Q()
            cat_cands = Q(db_category__iexact=category.lower.strip()) if key!=None else Q()
            return _GA(obj, "db_tags").filter(cat_cands & key_cands)
        else:
            return list(_GA(obj, "db_tags").all())

    def get_tag(self, key=None, category=None):
        """
        Search and return all tags matching any combination of
        the search criteria.
         search_key (string) - the tag identifier
         category (string) - the tag category

        Returns a single Tag (or None) if both key and category is given, otherwise
        it will return a list.
        """
        key_cands = Q(db_key__iexact=key.lower().strip()) if key!=None else Q()
        cat_cands = Q(db_category__iexact=category.lower().strip()) if category!=None else Q()
        tags = self.filter(key_cands & cat_cands)
        if key and category:
            return tags[0] if tags else None
        else:
            return list(tags)

    def get_objs_with_tag(self, objclass, key=None, category=None):
        """
        Search and return all objects of objclass that has tags matching
        the given search criteria.
         objclass (dbmodel) - the object class to search
         key (string) - the tag identifier
         category (string) - the tag category
        """
        key_cands = Q(db_tags__db_key__iexact=key.lower().strip()) if search_key!=None else Q()
        cat_cands = Q(db_tags__db_category__iexact=category.lower().strip()) if category!=None else Q()
        return objclass.objects.filter(key_cands & cat_cands)

    def create_tag(self, key=None, category=None, data=None):
        """
        Create a tag. This makes sure the create case-insensitive tags.
        Note that if the exact same tag configuration (key+category)
        exists, it will be re-used. A data keyword will overwrite existing
        data on a tag (it is not part of what makes the tag unique).

        """
        data = str(data) if data!=None else None

        tag = self.get_tag(key=key, category=category)
        if tag and data != None:
            tag.db_data = data
            tag.save()
        elif not tag:
            tag = self.create(db_key=key.lower().strip() if key!=None else None,
                              db_category=category.lower().strip() if key!=None else None,
                              db_data=str(data) if data!=None else None)
            tag.save()
        return tag

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
        matches = method(self, *args, **kwargs)
        return [(hasattr(dbobj, "typeclass") and dbobj.typeclass) or dbobj for dbobj in make_iter(matches)]
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
        if min_dbref != None:
            retval = retval.filter(id__gte=self.dbref(min_dbref, reqhash=False))
        if max_dbref != None:
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
    def typeclass_search(self, typeclass):
        """
        Searches through all objects returning those which has a certain
        typeclass. If location is set, limit search to objects in
        that location.
        """
        if callable(typeclass):
            cls = typeclass.__class__
            typeclass = "%s.%s" % (cls.__module__, cls.__name__)
        return self.filter(db_typeclass_path__exact=typeclass)
