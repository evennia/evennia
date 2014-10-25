"""
This implements the common managers that are used by the
abstract models in dbobjects.py (and which are thus shared by
all Attributes and TypedObjects).
"""
from functools import update_wrapper
from django.db.models import Q
from src.utils import idmapper
from src.utils.utils import make_iter, variable_from_module

__all__ = ("AttributeManager", "TypedObjectManager")
_GA = object.__getattribute__
_Tag = None

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


class TypedObjectManager(idmapper.manager.SharedMemoryManager):
    """
    Common ObjectManager for all dbobjects.
    """

    # Attribute manager methods
    def get_attribute(self, key=None, category=None, value=None, strvalue=None, obj=None, attrtype=None):
        """
        Return Attribute objects by key, by category, by value, by
        strvalue, by object (it is stored on) or with a combination of
        those criteria.

        attrtype - one of None (normal Attributes) or "nick"
        """
        query = [("attribute__db_attrtype", attrtype)]
        if obj:
            query.append(("%s__id" % self.model.__name__.lower(), obj.id))
        if key:
            query.append(("attribute__db_key", key))
        if category:
            query.append(("attribute__db_category", category))
        if strvalue:
            query.append(("attribute__db_strvalue", value))
        elif value:
            # strvalue and value are mutually exclusive
            query.append(("attribute__db_value", value))
        return [th.attribute for th in self.model.db_attributes.through.objects.filter(**dict(query))]

    def get_nick(self, key=None, category=None, value=None, strvalue=None, obj=None):
        return self.get_attribute(key=key, category=category, value=value, strvalue=strvalue, obj=obj)

    @returns_typeclass_list
    def get_by_attribute(self, key=None, category=None, value=None, strvalue=None, attrtype=None):
        """
        Return objects having attributes with the given key, category, value,
        strvalue or combination of those criteria.
        """
        query = [("db_attributes__db_attrtype", attrtype)]
        if key:
            query.append(("db_attributes__db_key", key))
        if category:
            query.append(("db_attributes__db_category", category))
        if strvalue:
            query.append(("db_attributes__db_strvalue", value))
        elif value:
            # strvalue and value are mutually exclusive
            query.append(("db_attributes__db_value", value))
        return self.filter(**dict(query))

    def get_by_nick(self, key=None, nick=None, category="inputline"):
        "Get object based on its key or nick."
        return self.get_by_attribute(key=key, category=category, strvalue=nick, attrtype="nick")

    # Tag manager methods

    def get_tag(self, key=None, category=None, obj=None, tagtype=None):
        """
        Return Tag objects by key, by category, by object (it is
        stored on) or with a combination of those criteria.

        tagtype - one of None (normal tags), "alias" or "permission"
        """
        query = [("tag__db_tagtype", tagtype)]
        if obj:
            query.append(("%s__id" % self.model.__name__.lower(), obj.id))
        if key:
            query.append(("tag__db_key", key))
        if category:
            query.append(("tag__db_category", category))
        return [th.tag for th in self.model.db_tags.through.objects.filter(**dict(query))]

    def get_permission(self, key=None, category=None, obj=None):
        return self.get_tag(key=key, category=category, obj=obj, tagtype="permission")

    def get_alias(self, key=None, category=None, obj=None):
        return self.get_tag(key=key, category=category, obj=obj, tagtype="alias")

    @returns_typeclass_list
    def get_by_tag(self, key=None, category=None, tagtype=None):
        """
        Return objects having tags with a given key or category or
        combination of the two.

        tagtype = None, alias or permission
        """
        query = [("db_tags__db_tagtype", tagtype)]
        if key:
            query.append(("db_tags__db_key", key))
        if category:
            query.append(("db_tags__db_category", category))
        return self.filter(**dict(query))

    def get_by_permission(self, key=None, category=None):
        return self.get_by_tag(key=key, category=category, tagtype="permission")

    def get_by_alias(self, key=None, category=None):
        return self.get_by_tag(key=key, category=category, tagtype="alias")

    def create_tag(self, key=None, category=None, data=None, tagtype=None):
        """
        Create a new Tag of the base type associated with this typedobject.
        This makes sure to create case-insensitive tags. If the exact same
        tag configuration (key+category+tagtype) exists on the model, a
        new tag will not be created, but an old one returned.  A data
        keyword is not part of the uniqueness of the tag and setting one
        on an existing tag will overwrite the old data field.
        """
        data = str(data) if data is not None else None
        # try to get old tag
        tag = self.get_tag(key=key, category=category, tagtype=tagtype)
        if tag and data is not None:
            # overload data on tag
            tag.db_data = data
            tag.save()
        elif not tag:
            # create a new tag
            global _Tag
            if not _Tag:
                from src.typeclasses.models import Tag as _Tag
            tag = _Tag.objects.create(
                db_key=key.strip().lower() if key is not None else None,
                db_category=category.strip().lower() if category and key is not None else None,
                db_data=data,
                db_tagtype=tagtype.strip().lower() if tagtype is not None else None)
            tag.save()
        return make_iter(tag)[0]

    # object-manager methods

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
