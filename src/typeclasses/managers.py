"""
This implements the common managers that are used by the
abstract models in dbobjects.py (and which are thus shared by
all Attributes and TypedObjects). 
"""
from django.db import models
from src.utils import idmapper
#from src.typeclasses import idmap

# Managers 

class AttributeManager(models.Manager):
    "Manager for handling Attributes."

    def attr_namesearch(self, searchstr, obj, exact_match=True):
        """
        Searches the object's attributes for name matches. 
        
        searchstr: (str) A string to search for.
        """
        # Retrieve the list of attributes for this object.
        if exact_match:
            return self.filter(db_obj=obj).filter(
                db_key__iexact=searchstr)
        else:
            return self.filter(db_obj=obj).filter(
                db_key__icontains=searchstr)


#
# helper functions for the TypedObjectManager. 
#    

def returns_typeclass_list(method):
    """
    Decorator function that turns the return of the
    decorated method (which are ObjectDB objects)
    into object_classes(s) instead.
    Will always return a list or None. 
    """        
    def func(self, *args, **kwargs):
        """
        This overloads the relevant method.
        The return is *always* either None
        or a list. 
        """        
        match = method(self, *args, **kwargs)        
        #print "deco: %s" % match, 
        if not match:
            return []
        try:
            match = list(match)
        except TypeError:
            match = [match]
        obj_classes = []
        for dbobj in match:
            try:
                obj_classes.append(dbobj.typeclass)
            except Exception:
                obj_classes.append(dbobj)
                #logger.log_trace() 
        #print "-> %s" % obj_classes
        #if not obj_classes:
        #    return None
        return obj_classes
    return func    

def returns_typeclass(method):
    """
    Decorator: Will always return a single result or None.
    """
    def func(self, *args, **kwargs):
        "decorator"
        rfunc = returns_typeclass_list(method)
        match = rfunc(self, *args, **kwargs)
        if match:
            return match[0]
        return None 
    return func


#class TypedObjectManager(idmap.CachingManager):
#class TypedObjectManager(models.Manager):
class TypedObjectManager(idmapper.manager.SharedMemoryManager):
    """
    Common ObjectManager for all dbobjects. 
    """

    def dbref(self, dbref):
        """
        Valid forms of dbref (database reference number)
        are either a string '#N' or an integer N.
        Output is the integer part. 
        """
        if isinstance(dbref, basestring):
            dbref = dbref.lstrip('#')
        try:
            if int(dbref) < 1:
                return None 
        except Exception:
            return None
        return dbref
        
    @returns_typeclass
    def dbref_search(self, dbref):
        """
        Returns an object when given a dbref.
        """
        dbref = self.dbref(dbref)
        if dbref :
            try:
                return self.get(id=dbref)
            except self.model.DoesNotExist:
                return None
        return None

    @returns_typeclass_list
    def get_dbref_range(self, min_dbref=None, max_dbref=None):
        """
        Return all objects inside and including the
        given boundaries.
        """
        min_dbref, max_dbref = self.dbref(min_dbref), self.dbref(max_dbref)
        if not min_dbref or not max_dbref:
            return self.all()
        if not min_dbref:
            return self.filter(id__lte=max_dbref)
        elif not max_dbref:
            return self.filter(id__gte=min_dbref)
        return self.filter(id__gte=min_dbref).filter(id__lte=min_dbref)

    def get_id(self, idnum):
        """
        Alias to dbref_search
        """
        return self.dbref_search(idnum)

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
        o_query = self.filter(db_typeclass_path__exact=typeclass)      
        return o_query

