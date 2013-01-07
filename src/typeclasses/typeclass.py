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

from src.utils.logger import log_trace, log_errmsg

__all__ = ("TypeClass",)

# these are called so many times it's worth to avoid lookup calls
_GA = object.__getattribute__
_SA = object.__setattr__
_DA = object.__delattr__

# To ensure the sanity of the model, there are a
# few property names we won't allow the admin to
# set on the typeclass just like that. Note that these are *not* related
# to *in-game* safety (if you can edit typeclasses you have
# full access anyway), so no protection against changing
# e.g. 'locks' or 'permissions' should go here.
PROTECTED = ('id', 'dbobj', 'db', 'ndb', 'objects', 'typeclass',
             'attr', 'save', 'delete', 'db_model_name','attribute_class',
             'typeclass_paths')

# If this is true, all non-protected property assignments
# are directly stored to a database attribute

class MetaTypeClass(type):
    """
    This metaclass just makes sure the class object gets
    printed in a nicer way (it might end up having no name at all
    otherwise due to the magics being done with get/setattribute).
    """
    def __init__(mcs, *args, **kwargs):
        """
        Adds some features to typeclassed objects
        """
        super(MetaTypeClass, mcs).__init__(*args, **kwargs)
        mcs.typename = mcs.__name__
        mcs.path = "%s.%s" % (mcs.__module__, mcs.__name__)

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
        # typecheck of dbobj - we can't allow it to be added here
        # unless it's really a TypedObject.
        dbobj_cls = _GA(dbobj, '__class__')
        dbobj_mro = _GA(dbobj_cls, '__mro__')
        if not any('src.typeclasses.models.TypedObject' in str(mro) for mro in dbobj_mro):
            raise Exception("dbobj is not a TypedObject: %s: %s" % (dbobj_cls, dbobj_mro))

        # store the reference to the database model instance
        _SA(self, 'dbobj', dbobj)

    def __getattribute__(self, propname):
        """
        Change the normal property access to
        transparently include the properties on
        self.dbobj. Note that dbobj properties have
        priority, so if you define a same-named


        property on the class, it will NOT be
        accessible through getattr.
        """
        if propname == 'dbobj':
            return _GA(self, 'dbobj')
        if propname.startswith('__') and propname.endswith('__'):
            # python specials are parsed as-is (otherwise things like
            # isinstance() fail to identify the typeclass)
            return _GA(self, propname)
        #print "get %s (dbobj:%s)" % (propname, type(dbobj))
        try:
            return _GA(self, propname)
        except AttributeError:
            try:
                dbobj = _GA(self, 'dbobj')
            except AttributeError:
                log_trace("Typeclass CRITICAL ERROR! dbobj not found for Typeclass %s!" % self)
                raise
            try:
                return _GA(dbobj, propname)
            except AttributeError:
                string = "Object: '%s' not found on %s(#%s), nor on its typeclass %s."
                raise AttributeError(string % (propname, dbobj, _GA(dbobj, "dbid"), _GA(dbobj, "typeclass_path")))

    def __setattr__(self, propname, value):
        """
        Transparently save data to the dbobj object in
        all situations. Note that this does not
        necessarily mean storing it to the database.
        """
        #print "set %s -> %s" % (propname, value)
        if propname in PROTECTED:
            string = "%s: '%s' is a protected attribute name."
            string += " (protected: [%s])" % (", ".join(PROTECTED))
            log_errmsg(string % (self.name, propname))
            return
        try:
            dbobj = _GA(self, 'dbobj')
        except AttributeError:
            dbobj = None
            log_trace("This is probably due to an unsafe reload.")
        if dbobj:
            _SA(dbobj, propname, value)
        else:
            # only as a last resort do we save on the typeclass object
            _SA(self, propname, value)

    def __eq__(self, other):
        """
        dbobj-recognized comparison
        """
        try:
            return _GA(_GA(self, "dbobj"), "dbid") == _GA(_GA(other, "dbobj"), "dbid")
        except AttributeError:
            return id(self) == id(other)


    def __delattr__(self, propname):
        """
        Transparently deletes data from the typeclass or dbobj by first searching on the typeclass,
        secondly on the dbobj.db.
        Will not allow deletion of properties stored directly on dbobj.
        """
        if propname in PROTECTED:
            string = "%s: '%s' is a protected attribute name."
            string += " (protected: [%s])" % (", ".join(PROTECTED))
            log_errmsg(string % (self.name, propname))
            return

        try:
            _DA(self, propname)
        except AttributeError:
            # not on typeclass, try to delete on db/ndb
            try:
                dbobj = _GA(self, 'dbobj')
            except AttributeError:
                log_trace("This is probably due to an unsafe reload.")
                return # ignore delete
            try:
                dbobj.del_attribute_raise(propname)
            except AttributeError:
                string = "Object: '%s' not found on %s(#%s), nor on its typeclass %s."
                raise AttributeError(string % (propname, dbobj,
                                               dbobj.dbid,
                                               dbobj.typeclass_path,))

    def __str__(self):
        "represent the object"
        return self.key
    def __unicode__(self):
        return u"%s" % self.key
