"""
A typeclass is the companion of a TypedObject django model.
It 'decorates' the model without actually having to add new
fields to the model - transparently storing data onto its
associated model without the admin/user just having to deal
with a 'normal' Python class. The only restrictions is that
the typeclass must inherit from TypeClass and not reimplement
the get/setters defined below. There are also a few properties
that are protected, so as to not overwrite property names
used by the typesystem or django itself. 
"""

from src.utils import logger
from django.conf import settings

# To ensure the sanity of the model, there are a
# few property names we won't allow the admin to
# set just like that. 
PROTECTED = ['id', 'dbobj', 'db', 'objects', 'typeclass',
             'attr', 'save', 'delete']
# If this is true, all non-protected property assignments
# are directly stored to a database attribute
try:
    FULL_PERSISTENCE = settings.FULL_PERSISTENCE
except AttributeError:
    FULL_PERSISTENCE = True


class MetaTypeClass(type):
    """
    This metaclass just makes sure the class object gets
    printed in a nicer way (it might end up having no name at all
    otherwise due to the magics being done with get/setattribute).
    """
    def __str__(cls):
        return "%s" % cls.__name__
    

class TypeClass(object):
    """
    This class implements a 'typeclass' object. This is connected
    to a database object inheriting from TypedObject.
    the TypeClass allows for all customization.
    Most of the time this means that the admin never has to
    worry about database access but only deal with extending
    TypeClasses to create diverse objects in the game. 

    The ObjectType class has all functionality for wrapping a
    database object transparently. 

    It's up to its child classes to implement eventual custom hooks
    and other functions called by the engine. 
    
    """
    __metaclass__ = MetaTypeClass

    def __init__(self, dbobj):
        """
        Initialize the object class. There are two ways to call this class.
        o = object_class(dbobj) : this is used to initialize dbobj with the class name
        o = dbobj.object_class(dbobj) : this is used when dbobj.object_class is already set. 
        
        """
        # typecheck of dbobj - we can't allow it to be added here unless 
        # unless it's really a TypedObject. 
        dbobj_cls = object.__getattribute__(dbobj, '__class__')
        dbobj_mro = object.__getattribute__(dbobj_cls, '__mro__')
        if not any('src.typeclasses.models.TypedObject' 
                   in str(mro) for mro in dbobj_mro):
            raise Exception("dbobj is not a TypedObject: %s: %s" % \
                                (dbobj_cls, dbobj_mro))
        object.__setattr__(self, 'dbobj', dbobj) 

        # store the needed things on the typeclass
        object.__setattr__(self, '_protected_attrs', PROTECTED)

        # sync the database object to this typeclass. 
        cls = object.__getattribute__(self, '__class__')
        db_typeclass_path = "%s.%s" % (object.__getattribute__(cls, '__module__'),
                                       object.__getattribute__(cls, '__name__'))        
        if not dbobj.db_typeclass_path == db_typeclass_path:
            dbobj.db_typeclass_path = db_typeclass_path
            dbobj.save()

        # (The inheriting typed object classes often extend this __init__ to
        # add handlers etc.) 

    def __getattribute__(self, propname):
        """
        Change the normal property access to
        transparently include the properties on
        self.dbobj. Note that dbobj properties have
        priority, so if you define a same-named
        property on the class, it will NOT be
        accessible through getattr. 
        """
        try:
            dbobj = object.__getattribute__(self, 'dbobj')
        except AttributeError:
            dbobj = None 
            logger.log_trace("This is probably due to an unsafe reload.")            
            raise 
        if propname == 'dbobj':
            return dbobj
        if propname.startswith('__') and propname.endswith('__'):
            # python specials are parsed as-is (otherwise things like
            # isinstance() fail to identify the typeclass)
            return object.__getattribute__(self, propname)
        #print "get %s (dbobj:%s)" % (propname, type(dbobj))        
        try:
            #print "Typeclass: looking for %s on dbobj %s" % (propname, dbobj)
            #print "  <-- dbobj"            
            return object.__getattribute__(dbobj, propname)
        except AttributeError:
            try:
                return object.__getattribute__(self, propname)
            except AttributeError:
                try:
                    if FULL_PERSISTENCE and propname != 'ndb':       
                        db = object.__getattribute__(dbobj, 'db')
                        value = object.__getattribute__(db, propname)
                    else:
                        # Not FULL_PERSISTENCE
                        ndb = object.__getattribute__(dbobj, 'ndb')
                        value = object.__getattribute__(ndb, propname) 
                    return value
                except AttributeError:
                    string = "Object: '%s' not found on %s(%s), nor on its typeclass %s."
                    raise AttributeError(string % (propname, dbobj,
                                                   dbobj.dbref,
                                                   dbobj.typeclass_path,))
                    
    def __setattr__(self, propname, value):
        """
        Transparently save data to the dbobj object in
        all situations. Note that this does not
        necessarily mean storing it to the database
        unless data is stored into a propname
        corresponding to a field on ObjectDB model. 
        """
        #print "set %s -> %s" % (propname, value)
        try:            
            protected = object.__getattribute__(self, '_protected_attrs')
        except AttributeError:
            protected = PROTECTED
            logger.log_trace("This is probably due to an unsafe reload.")                    
        if propname in protected:
            string = "%s: '%s' is a protected attribute name." 
            string += " (protected: [%s])" % (", ".join(protected))
            logger.log_errmsg(string % (self.name, propname))
        else:
            try:
                dbobj = object.__getattribute__(self, 'dbobj')
            except AttributeError:
                dbobj = None 
                logger.log_trace("This is probably due to an unsafe reload.")            
            if dbobj: # and hasattr(dbobj, propname):        
                #print "   ---> dbobj"
                if hasattr(dbobj, propname):
                    # if attr already exists on dbobj, assign to it.
                    object.__setattr__(dbobj, propname, value)
                elif FULL_PERSISTENCE:
                    #print "full __setattr__1", propname
                    db = object.__getattribute__(dbobj, 'db')
                    #print "full __setattr__2", propname
                    object.__setattr__(db, propname, value)
                else:                    
                    # not FULL_PERSISTENCE
                    ndb = object.__getattribute__(dbobj, 'ndb')                    
                    object.__setattr__(ndb, propname, value)
            else:
                object.__setattr__(self, propname, value)

        def __eq__(self, other):
            """
            dbobj-recognized comparison
            """            
            if hasattr(other, 'user'):
                return other == self or other == self.dbobj or other == self.dbobj.user
            else:
                return other == self or other == self.dbobj
     
    def __str__(self):
        "represent the object"
        return self.key
