"""
This is the *abstract* django models for many of the database objects
in Evennia. A django abstract (obs, not the same as a Python metaclass!) is
a model which is not actually created in the database, but which only exists
for other models to inherit from, to avoid code duplication. Any model can
import and inherit from these classes. 

Attributes are database objects stored on other objects. The implementing
class needs to supply a ForeignKey field attr_object pointing to the kind
of object being mapped.

TypedObjects are objects 'decorated' with a typeclass - that is, the typeclass
(which is a normal Python class implementing some special tricks with its
get/set attribute methods, allows for the creation of all sorts of different
objects all with the same database object underneath. Usually attributes are
used to permanently store things not hard-coded as field on the database object.
The admin should usually not have to deal directly  with the database object
layer. 

This module also contains the Managers for the respective models; inherit from
these to create custom managers. 
  
"""

import sys
try:
    import cPickle as pickle
except ImportError:
    import pickle
import traceback
from django.db import models
from django.conf import settings
from django.utils.encoding import smart_str
from django.contrib.contenttypes.models import ContentType
from src.utils.idmapper.models import SharedMemoryModel
from src.server.models import ServerConfig
from src.typeclasses import managers
from src.locks.lockhandler import LockHandler
from src.utils import logger, utils
from src.utils.utils import is_iter, has_parent

PERMISSION_HIERARCHY = [p.lower() for p in settings.PERMISSION_HIERARCHY]

# used by Attribute to efficiently identify stored object types.
# Note that these have to be updated if directory structure changes.
PARENTS = {
    "typeclass":"src.typeclasses.typeclass.TypeClass",
    "objectdb":"src.objects.models.ObjectDB",
    "playerdb":"src.players.models.PlayerDB",
    "scriptdb":"src.scripts.models.ScriptDB",
    "msg":"src.comms.models.Msg",
    "channel":"src.comms.models.Channel",
    "helpentry":"src.help.models.HelpEntry"}

#------------------------------------------------------------
#
#   Attributes 
#
#------------------------------------------------------------

class PackedDBobject(object):
    """
    Attribute helper class.
    A container for storing and easily identifying database objects in 
    the database (which doesn't suppport storing db_objects directly).
    """
    def __init__(self, ID, db_model):        
        self.id = ID
        self.db_model = db_model

class PackedDict(dict):
    """
    Attribute helper class.
    A variant of dict that stores itself to the database when 
    updating one of its keys. This is called and handled by 
    Attribute.validate_data(). 
    """
    def __init__(self, db_obj, *args, **kwargs):
        """
        Sets up the packing dict. The db_store variable
        is set by Attribute.validate_data() when returned in
        order to allow custom updates to the dict. 

         db_obj - the Attribute object storing this dict.

        """
        self.db_obj = db_obj
        self.db_store = False
        super(PackedDict, self).__init__(*args, **kwargs)
    def db_save(self):
        "save data to Attribute, if db_store is active"        
        if self.db_store:
            self.db_obj.value = self
    def __setitem__(self, *args, **kwargs):                
        "Custom setitem that stores changed dict to database."        
        super(PackedDict, self).__setitem__(*args, **kwargs)
        self.db_save()
    def __getitem__(self, *args, **kwargs):        
        return super(PackedDict, self).__getitem__(*args, **kwargs)
    def clear(self, *args, **kwargs):                
        "Custom clear"
        super(PackedDict, self).clear(*args, **kwargs)
        self.db_save()
    def pop(self, *args, **kwargs):                
        "Custom pop"
        super(PackedDict, self).pop(*args, **kwargs)
        self.db_save()
    def popitem(self, *args, **kwargs):                
        "Custom popitem"
        super(PackedDict, self).popitem(*args, **kwargs)
        self.db_save()
    def update(self, *args, **kwargs):                
        "Custom update"
        super(PackedDict, self).update(*args, **kwargs)
        self.db_save()
                
class PackedList(list):
    """
    Attribute helper class.
    A variant of list that stores itself to the database when 
    updating one of its keys. This is called and handled by 
    Attribute.validate_data(). 
    """
    def __init__(self, db_obj, *args, **kwargs):
        """
        Sets up the packing list. The db_store variable
        is set by Attribute.validate_data() when returned in
        order to allow custom updates to the list. 

         db_obj - the Attribute object storing this dict.

        """
        self.db_obj = db_obj
        self.db_store = False
        super(PackedList, self).__init__(*args, **kwargs)
    def db_save(self):
        "save data to Attribute, if db_store is active"
        if self.db_store:
            self.db_obj.value = self
    def __setitem__(self, *args, **kwargs):                
        "Custom setitem that stores changed dict to database."
        super(PackedList, self).__setitem__(*args, **kwargs)
        self.db_save()
    def append(self, *args, **kwargs):
        "Custom append"
        super(PackedList, self).append(*args, **kwargs)
        self.db_save()
    def extend(self, *args, **kwargs):
        "Custom extend"
        super(PackedList, self).extend(*args, **kwargs)
        self.db_save()
    def insert(self, *args, **kwargs):
        "Custom insert"
        super(PackedList, self).insert(*args, **kwargs)
        self.db_save()
    def remove(self, *args, **kwargs):
        "Custom remove"
        super(PackedList, self).remove(*args, **kwargs)
        self.db_save()
    def pop(self, *args, **kwargs):
        "Custom pop"
        super(PackedList, self).pop(*args, **kwargs)
        self.db_save()
    def reverse(self, *args, **kwargs):
        "Custom reverse"
        super(PackedList, self).reverse(*args, **kwargs)
        self.db_save()
    def sort(self, *args, **kwargs):
        "Custom sort"
        super(PackedList, self).sort(*args, **kwargs)
        self.db_save()



class Attribute(SharedMemoryModel):
    """
    Abstract django model.

    Attributes are things that are specific to different types of objects. For
    example, a drink container needs to store its fill level, whereas an exit
    needs to store its open/closed/locked/unlocked state. These are done via
    attributes, rather than making different classes for each object type and
    storing them directly. The added benefit is that we can add/remove 
    attributes on the fly as we like.

    The Attribute class defines the following properties:
      key - primary identifier
      mode - which type of data is stored in attribute
      permissions - perm strings
      obj - which object the attribute is defined on
      date_created - when the attribute was created
      value - the data stored in the attribute

    """

    #
    # Attribute Database Model setup
    #
    #
    # These databse fields are all set using their corresponding properties,
    # named same as the field, but withtout the db_* prefix.

    db_key = models.CharField(max_length=255)
    # access through the value property 
    db_value = models.TextField(blank=True, null=True)
    # Lock storage 
    db_lock_storage = models.CharField(max_length=512, blank=True)    
    # references the object the attribute is linked to (this is set 
    # by each child class to this abstact class)
    db_obj =  None # models.ForeignKey("RefencedObject")
    # time stamp
    db_date_created = models.DateTimeField(editable=False, auto_now_add=True)
    
    # Database manager 
    objects = managers.AttributeManager()
            
    # Lock handler self.locks
    def __init__(self, *args, **kwargs):
        "Initializes the parent first -important!"
        SharedMemoryModel.__init__(self, *args, **kwargs)
        self.locks = LockHandler(self)
        self.value_cache = None 

    class Meta:
        "Define Django meta options"
        abstract = True 
        verbose_name = "Evennia Attribute"
        verbose_name_plural = "Evennia Attributes"
    
    # Wrapper properties to easily set database fields. These are
    # @property decorators that allows to access these fields using
    # normal python operations (without having to remember to save()
    # etc). So e.g. a property 'attr' has a get/set/del decorator
    # defined that allows the user to do self.attr = value, 
    # value = self.attr and del self.attr respectively (where self 
    # is the object in question).

    # key property (wraps db_key)
    #@property
    def key_get(self):
        "Getter. Allows for value = self.key"
        return self.db_key
    #@key.setter
    def key_set(self, value):
        "Setter. Allows for self.key = value"
        self.db_key = value
        self.save()
    #@key.deleter
    def key_del(self):
        "Deleter. Allows for del self.key"
        raise Exception("Cannot delete attribute key!")
    key = property(key_get, key_set, key_del)

    # obj property (wraps db_obj)
    #@property
    def obj_get(self):
        "Getter. Allows for value = self.obj"
        return self.db_obj
    #@obj.setter
    def obj_set(self, value):
        "Setter. Allows for self.obj = value"
        self.db_obj = value
        self.save()
    #@obj.deleter
    def obj_del(self):
        "Deleter. Allows for del self.obj"
        self.db_obj = None
        self.save()
    obj = property(obj_get, obj_set, obj_del)   

    # date_created property (wraps db_date_created)
    #@property
    def date_created_get(self):
        "Getter. Allows for value = self.date_created"
        return self.db_date_created
    #@date_created.setter
    def date_created_set(self, value):
        "Setter. Allows for self.date_created = value"
        raise Exception("Cannot edit date_created!")
    #@date_created.deleter
    def date_created_del(self):
        "Deleter. Allows for del self.date_created"
        raise Exception("Cannot delete date_created!")
    date_created = property(date_created_get, date_created_set, date_created_del)

    # value property (wraps db_value)
    #@property
    def value_get(self):
        """
        Getter. Allows for value = self.value.
        """                
        try:
            return utils.to_unicode(self.validate_data(pickle.loads(utils.to_str(self.db_value))))
        except pickle.UnpicklingError:
            return self.db_value
    #@value.setter
    def value_set(self, new_value):
        "Setter. Allows for self.value = value"                        
        self.db_value = utils.to_unicode(pickle.dumps(utils.to_str(self.validate_data(new_value, setmode=True))))
        #self.db_value = utils.to_unicode(pickle.dumps(utils.to_str(self.validate_data(new_value))))        
        self.save()
    #@value.deleter
    def value_del(self):
        "Deleter. Allows for del attr.value. This removes the entire attribute."
        self.delete()
    value = property(value_get, value_set, value_del)

    # lock_storage property (wraps db_lock_storage)
    #@property 
    def lock_storage_get(self):
        "Getter. Allows for value = self.lock_storage"
        return self.db_lock_storage
    #@lock_storage.setter
    def lock_storage_set(self, value):
        """Saves the lock_storage. This is usually not called directly, but through self.lock()"""
        self.db_lock_storage = value
        self.save()
    #@lock_storage.deleter
    def lock_storage_del(self):
        "Deleter is disabled. Use the lockhandler.delete (self.lock.delete) instead"""
        logger.log_errmsg("Lock_Storage (on %s) cannot be deleted. Use obj.lock.delete() instead." % self)
    lock_storage = property(lock_storage_get, lock_storage_set, lock_storage_del)
        

    #
    #
    # Attribute methods
    #
    #

    def __str__(self):
        return smart_str("%s(%s)" % (self.key, self.id))
        
    def __unicode__(self):
        return u"%s(%s)" % (self.key, self.id)

    def validate_data(self, item, niter=0, setmode=False):
        """
        We have to make sure to not store database objects raw, since
        this will crash the system. Instead we must store their IDs
        and make sure to convert back when the attribute is read back
        later.

        Due to this it's criticial that we check all iterables
        recursively, converting all found database objects to a form
        the database can handle. We handle lists, tuples and dicts
        (and any nested combination of them) this way, all other
        iterables are stored and returned as lists.

        setmode - used for iterables; when first assigning, this settings makes
           sure that it's a normal built-in python object that is stored in the db,
           not the custom one. This will then just be updated later, assuring the
           pickling works as it should. 
        niter - iteration counter for recursive iterable search. 
        """        
        if isinstance(item, basestring):
            # a string is unmodified 
            ret = item        
        elif type(item) == PackedDBobject:
            # unpack a previously packed db_object
            try:
                #print "unpack:", item.id, item.db_model
                mclass = ContentType.objects.get(model=item.db_model).model_class()
                try:
                    ret = mclass.objects.dbref_search(item.id)
                except AttributeError:
                    ret = mclass.objects.get(id=item.id)
            except Exception:
                logger.log_trace("Attribute error: %s, %s" % (item.db_model, item.id)) #TODO: Remove when stable?
                ret = None
        elif type(item) == tuple:
            # handle tuples 
            ret = []
            for it in item:
                ret.append(self.validate_data(it))
            ret = tuple(ret)
        elif type(item) == dict or type(item) == PackedDict:            
            # handle dictionaries            
            if setmode:
                ret = {}
                for key, it in item.items():
                    ret[key] = self.validate_data(it, niter=niter+1, setmode=True)
            else:
                ret = PackedDict(self)
                for key, it in item.items():
                    ret[key] = self.validate_data(it, niter=niter+1)
                if niter == 0:
                    ret.db_store = True                    
        elif is_iter(item):
            # Note: ALL other iterables except dicts and tuples are stored&retrieved as lists!
            if setmode:
                ret = []
                for it in item:
                    ret.append(self.validate_data(it, niter=niter+1setmode=True))
            else:
                ret = PackedList(self)
                for it in item:
                    ret.append(self.validate_data(it, niter=niter+1))
                if niter == 0:
                    ret.db_store = True 
        elif has_parent('django.db.models.base.Model', item) or has_parent(PARENTS['typeclass'], item):
            # db models must be stored as dbrefs
            db_model = [parent for parent, path in PARENTS.items() if has_parent(path, item)]
            #print "db_model", db_model
            if db_model and db_model[0] == 'typeclass':
                # the typeclass alone can't help us, we have to know the db object.
                db_model = [parent for parent, path in PARENTS.items()
                            if has_parent(path, item.dbobj)]
            #print "db_model2", db_model 
            if db_model:
                # store the object in an easily identifiable container 
                ret = PackedDBobject(str(item.id), db_model[0])
            else:
                # not a valid object - some third-party class or primitive?
                ret = item
        else:
            ret = item             
        return ret
                    
    def access(self, accessing_obj, access_type='read', default=False):
        """
        Determines if another object has permission to access.
        accessing_obj - object trying to access this one
        access_type - type of access sought
        default - what to return if no lock of access_type was found
        """        
        return self.locks.check(accessing_obj, access_type=access_type, default=default)


#------------------------------------------------------------
#
# Nicks
#
#------------------------------------------------------------

class TypeNick(SharedMemoryModel):
    """
    This model holds whichever alternate names this object 
    has for OTHER objects, but also for arbitrary strings,
    channels, players etc. Setting a nick does not affect
    the nicknamed object at all (as opposed to Aliases above), 
    and only this object will be able to refer to the nicknamed
    object by the given nick. 

    The default nick types used by Evennia are: 
    inputline (default) - match against all input
    player - match against player searches
    obj - match against object searches 
    channel - used to store own names for channels

    """
    db_nick = models.CharField(max_length=255, db_index=True) # the nick
    db_real = models.TextField() # the aliased string
    db_type = models.CharField(default="inputline", max_length=16, null=True, blank=True) # the type of nick
    db_obj = None #models.ForeignKey("ObjectDB")

    class Meta:
        "Define Django meta options"
        abstract = True 
        verbose_name = "Nickname"
        verbose_name_plural = "Nicknames"
        unique_together = ("db_nick", "db_type", "db_obj")

class TypeNickHandler(object):
    """
    Handles nick access and setting. Accessed through ObjectDB.nicks
    """    

    NickClass = TypeNick 

    def __init__(self, obj):
        "Setup"
        self.obj = obj

    def add(self, nick, realname, nick_type="inputline"):
        "We want to assign a new nick"
        if not nick or not nick.strip():
            return 
        nick = nick.strip()        
        real = realname.strip() 
        query = self.NickClass.objects.filter(db_obj=self.obj, db_nick__iexact=nick, db_type__iexact=nick_type) 
        if query.count():
            old_nick = query[0]
            old_nick.db_real = real
            old_nick.save()
        else:              
            new_nick = self.NickClass(db_nick=nick, db_real=real, db_type=nick_type, db_obj=self.obj)
            new_nick.save()                
    def delete(self, nick, nick_type="inputline"):        
        "Removes a nick"
        nick = nick.strip()        
        query = self.NickClass.objects.filter(db_obj=self.obj, db_nick__iexact=nick, db_type__iexact=nick_type)        
        if query.count():
            # remove the found nick(s)
            query.delete()           
    def get(self, nick=None, nick_type="inputline"):
        if nick:
            query = self.NickClass.objects.filter(db_obj=self.obj, db_nick__iexact=nick, db_type__iexact=nick_type)        
            query = query.values_list("db_real", flat=True)
            if query.count():
                return query[0]
            else:
                return nick
        else:
            return self.NickClass.objects.filter(db_obj=self.obj)
    def has(self, nick, nick_type="inputline"):
        "Returns true/false if this nick is defined or not"
        return self.NickClass.objects.filter(db_obj=self.obj, db_nick__iexact=nick, db_type__iexact=nick_type).count()


#------------------------------------------------------------
#
# Typed Objects 
#
#------------------------------------------------------------        

class TypedObject(SharedMemoryModel):
    """
    Abstract Django model.
    
    This is the basis for a typed object. It also contains all the
    mechanics for managing connected attributes. 
       
    The TypedObject has the following properties:
      key - main name
      name - alias for key
      typeclass_path - the path to the decorating typeclass
      typeclass - auto-linked typeclass
      date_created - time stamp of object creation
      permissions - perm strings 
      dbref - #id of object 
      db - persistent attribute storage
      ndb - non-persistent attribute storage 

    """    

    # 
    # TypedObject Database Model setup
    #
    #
    # These databse fields are all set using their corresponding properties,
    # named same as the field, but withtou the db_* prefix.
    
    # Main identifier of the object, for searching. Can also
    # be referenced as 'name'. 
    db_key = models.CharField(max_length=255)
    # This is the python path to the type class this object is tied to
    # (the type class is what defines what kind of Object this is)
    db_typeclass_path = models.CharField(max_length=255, null=True)
    # Creation date
    db_date_created = models.DateTimeField(editable=False, auto_now_add=True)
    # Permissions (access these through the 'permissions' property)
    db_permissions = models.CharField(max_length=255, blank=True)
    # Lock storage 
    db_lock_storage = models.CharField(max_length=512, blank=True)    

    # Database manager
    objects = managers.TypedObjectManager()

    # object cache and flags 
    cached_typeclass_path = ""
    cached_typeclass = None 

    # lock handler self.locks
    def __init__(self, *args, **kwargs):
        "We must initialize the parent first - important!"
        SharedMemoryModel.__init__(self, *args, **kwargs)
        self.locks = LockHandler(self)
    
    class Meta:
        """
        Django setup info.
        """
        abstract = True 
        verbose_name = "Evennia Database Object"
        verbose_name_plural = "Evennia Database Objects"
        ordering = ['-db_date_created', 'id', 'db_typeclass_path', 'db_key']
    
    # Wrapper properties to easily set database fields. These are
    # @property decorators that allows to access these fields using
    # normal python operations (without having to remember to save()
    # etc). So e.g. a property 'attr' has a get/set/del decorator
    # defined that allows the user to do self.attr = value, 
    # value = self.attr and del self.attr respectively (where self 
    # is the object in question).

    # key property (wraps db_key)
    #@property
    def key_get(self):
        "Getter. Allows for value = self.key"
        return self.db_key
    #@key.setter
    def key_set(self, value):
        "Setter. Allows for self.key = value"
        self.db_key = value
        self.save()
    #@key.deleter
    def key_del(self):
        "Deleter. Allows for del self.key"
        raise Exception("Cannot delete objectdb key!")
    key = property(key_get, key_set, key_del)

    # name property (wraps db_key too - alias to self.key)
    #@property
    def name_get(self):
        "Getter. Allows for value = self.name"
        return self.db_key
    #@name.setter
    def name_set(self, value):
        "Setter. Allows for self.name = value"
        self.db_key = value
        self.save()
    #@name.deleter
    def name_del(self):
        "Deleter. Allows for del self.name"
        raise Exception("Cannot delete name!")
    name = property(name_get, name_set, name_del)

    # typeclass_path property
    #@property
    def typeclass_path_get(self):
        "Getter. Allows for value = self.typeclass_path"
        typeclass_path = object.__getattribute__(self, 'cached_typeclass_path')
        if typeclass_path: 
            return typeclass_path 
        return self.db_typeclass_path
    #@typeclass_path.setter
    def typeclass_path_set(self, value):
        "Setter. Allows for self.typeclass_path = value"
        self.db_typeclass_path = value
        self.save()
        object.__setattr__(self, "cached_typeclass_path", value)
    #@typeclass_path.deleter
    def typeclass_path_del(self):
        "Deleter. Allows for del self.typeclass_path"
        self.db_typeclass_path = ""
        self.save()
        self.cached_typeclass_path = ""
    typeclass_path = property(typeclass_path_get, typeclass_path_set, typeclass_path_del)

    # date_created property
    #@property
    def date_created_get(self):
        "Getter. Allows for value = self.date_created"
        return self.db_date_created
    #@date_created.setter
    def date_created_set(self, value):
        "Setter. Allows for self.date_created = value"
        raise Exception("Cannot change date_created!")
    #@date_created.deleter
    def date_created_del(self):
        "Deleter. Allows for del self.date_created"
        raise Exception("Cannot delete date_created!")
    date_created = property(date_created_get, date_created_set, date_created_del)

    # permissions property
    #@property
    def permissions_get(self):
        "Getter. Allows for value = self.name. Returns a list of permissions."
        if self.db_permissions:
            return [perm.strip() for perm in self.db_permissions.split(',')]
        return []
    #@permissions.setter
    def permissions_set(self, value):
        "Setter. Allows for self.name = value. Stores as a comma-separated string."
        if is_iter(value):
            value = ",".join([utils.to_unicode(val).strip() for val in value])
        self.db_permissions = value
        self.save()        
    #@permissions.deleter
    def permissions_del(self):
        "Deleter. Allows for del self.name"
        self.db_permissions = ""
        self.save()
    permissions = property(permissions_get, permissions_set, permissions_del)

    # lock_storage property (wraps db_lock_storage)
    #@property 
    def lock_storage_get(self):
        "Getter. Allows for value = self.lock_storage"
        return self.db_lock_storage
    #@lock_storage.setter
    def lock_storage_set(self, value):
        """Saves the lock_storagetodate. This is usually not called directly, but through self.lock()"""
        self.db_lock_storage = value
        self.save()
    #@lock_storage.deleter
    def lock_storage_del(self):
        "Deleter is disabled. Use the lockhandler.delete (self.lock.delete) instead"""
        logger.log_errmsg("Lock_Storage (on %s) cannot be deleted. Use obj.lock.delete() instead." % self)
    lock_storage = property(lock_storage_get, lock_storage_set, lock_storage_del)



    #
    #
    # TypedObject main class methods and properties 
    #
    #

    # Each subclass should set this property to their respective
    # attribute model (ObjAttribute, PlayerAttribute etc).
    attribute_model_path = "src.typeclasses.models"
    attribute_model_name = "Attribute"
    typeclass_paths = settings.OBJECT_TYPECLASS_PATHS 

    def __eq__(self, other):        
        return other and hasattr(other, 'id') and self.id == other.id

    def __str__(self):
        return smart_str("%s" % self.key)

    def __unicode__(self):
        return u"%s" % self.key

    def __getattribute__(self, propname):
        """
        Will predominantly look for an attribute
        on this object, but if not found we will
        check if it might exist on the typeclass instead. Since
        the typeclass refers back to the databaseobject as well, we
        have to be very careful to avoid loops.
        """
        try:
            return object.__getattribute__(self, propname)
        except AttributeError:
            # check if the attribute exists on the typeclass instead
            # (we make sure to not incur a loop by not triggering the
            # typeclass' __getattribute__, since that one would
            # try to look back to this very database object.)
            typeclass = object.__getattribute__(self, 'typeclass')                        
            if typeclass:
                return object.__getattribute__(typeclass(self), propname)            
            else:
                raise AttributeError

    #@property
    def dbref_get(self):
        """
        Returns the object's dbref id on the form #NN.
        Alternetively, use obj.id directly to get dbref
        without any #. 
        """
        return "#%s" % str(self.id)
    dbref = property(dbref_get)

    # typeclass property
    #@property
    def typeclass_get(self):
        """
        Getter. Allows for value = self.typeclass.
        The typeclass is a class object found at self.typeclass_path;
        it allows for extending the Typed object for all different
        types of objects that the game needs. This property
        handles loading and initialization of the typeclass on the fly.

        Note: The liberal use of object.__getattribute__ and __setattr__ (instead
              of normal dot notation) is due to optimization: it avoids calling 
              the custom self.__getattribute__ more than necessary. 
        """        

        path = object.__getattribute__(self, "cached_typeclass_path")
        if not path: 
            path = object.__getattribute__(self, 'db_typeclass_path')        
        typeclass = object.__getattribute__(self, "cached_typeclass")
        try:
            if typeclass and object.__getattribute__(typeclass, "path") == path:
                return typeclass
        except AttributeError:
            pass 

        errstring = ""
        if not path:
            # this means we should get the default obj without giving errors.
            return object.__getattribute__(self, "get_default_typeclass")(cache=True, silent=True, save=True)
        else:                                   
            # handle loading/importing of typeclasses, searching all paths.
            # (self.typeclass_paths is a shortcut to settings.TYPECLASS_*_PATHS
            # where '*' is either OBJECT, SCRIPT or PLAYER depending on the typed
            # entities). 
            typeclass_paths = [path] + ["%s.%s" % (prefix, path) for prefix in object.__getattribute__(self, 'typeclass_paths')]
           
            for tpath in typeclass_paths: 

                # try to import and analyze the result
                typeclass = object.__getattribute__(self, "_path_import")(tpath)
                if callable(typeclass):
                    # we succeeded to import. Cache and return.   
                    object.__setattr__(self, 'db_typeclass_path', tpath)
                    object.__getattribute__(self, 'save')()
                    object.__setattr__(self, "cached_typeclass_path", tpath)
                    object.__setattr__(self, "cached_typeclass", typeclass)                     
                    return typeclass
                elif hasattr(typeclass, '__file__'):
                    errstring += "\n%s seems to be just the path to a module. You need" % tpath
                    errstring +=  " to specify the actual typeclass name inside the module too."
                else: 
                    errstring += "\n%s" % typeclass # this will hold a growing error message. 
        # If we reach this point we couldn't import any typeclasses. Return default. It's up to the calling
        # method to use e.g. self.is_typeclass() to detect that the result is not the one asked for. 
        object.__getattribute__(self, "_display_errmsg")(errstring)
        return object.__getattribute__(self, "get_default_typeclass")(cache=False, silent=False, save=False)

    #@typeclass.deleter
    def typeclass_del(self):
        "Deleter. Disallow 'del self.typeclass'"
        raise Exception("The typeclass property should never be deleted, only changed in-place!")

    # typeclass property 
    typeclass = property(typeclass_get, fdel=typeclass_del)
   
    def _path_import(self, path):
        """
        Import a class from a python path of the
        form src.objects.object.Object
        """
        errstring = ""
        if not path:
            # this needs not be bad, it just means 
            # we should use defaults.
            return None 
        try:            
            modpath, class_name = path.rsplit('.', 1)
            module =  __import__(modpath, fromlist=[class_name])
            return module.__dict__[class_name]
        except ImportError:            
            trc = sys.exc_traceback            
            if not trc.tb_next:
                # we separate between not finding the module, and finding a buggy one.
                errstring += "(Tried path '%s')." % path
            else:
                # a bug in the module is reported normally.
                trc = traceback.format_exc()           
                errstring += "\n%sError importing '%s'." % (trc, path)
        except KeyError:
            errstring = "No class '%s' was found in module '%s'." 
            errstring = errstring % (class_name, modpath)
        except Exception:
            trc = traceback.format_exc()            
            errstring = "\n%sException importing '%s'." % (trc, path)            
        # return the error.
        return errstring

    def _display_errmsg(self, message):            
        """
        Helper function to display error.
        """
        infochan = None
        cmessage = message 
        try:
            from src.comms.models import Channel
            infochan = settings.CHANNEL_MUDINFO
            infochan = Channel.objects.get_channel(infochan[0])            
            if infochan:
                cname = infochan.key
                cmessage = "\n".join(["[%s]: %s" % (cname, line) for line in message.split('\n') if line])
                cmessage = cmessage.strip()
                infochan.msg(cmessage)
            else:
                # no mudinfo channel is found. Log instead. 
                cmessage = "\n".join(["[NO MUDINFO CHANNEL]: %s" % line for line in message.split('\n')])
            logger.log_errmsg(cmessage)
        except Exception, e:                
            if ServerConfig.objects.conf("server_starting_mode"):
                print cmessage
            else:
                logger.log_trace(cmessage)
        
    def get_default_typeclass(self, cache=False, silent=False, save=False):
        """
        This is called when a typeclass fails to 
        load for whatever reason. 
        Overload this in different entities. 

        Default operation is to load a default typeclass.
        """
        defpath = object.__getattribute__(self, "default_typeclass_path")                
        typeclass = object.__getattribute__(self, "_path_import")(defpath)
        # if not silent:
        #     #errstring = "\n\nUsing Default class '%s'." % defpath                
        #     object.__getattribute__(self, "_display_errmsg")(errstring)

        if not callable(typeclass):
            # if typeclass still doesn't exist at this point, we're in trouble.
            # fall back to hardcoded core class which is wrong for e.g. scripts/players etc. 
            failpath = defpath
            defpath = "src.objects.objects.Object"
            typeclass = object.__getattribute__(self, "_path_import")(defpath)
            if not silent:
                #errstring = "  %s\n%s" % (typeclass, errstring)
                errstring = "  Default class '%s' failed to load." % failpath
                errstring += "\n  Using Evennia's default class '%s'." % defpath            
                object.__getattribute__(self, "_display_errmsg")(errstring)
        if not callable(typeclass):
            # if this is still giving an error, Evennia is wrongly configured or buggy
            raise Exception("CRITICAL ERROR: The final fallback typeclass %s cannot load!!" % defpath)
        if save:
            object.__setattr__(self, 'db_typeclass_path', defpath)
            object.__getattribute__(self, 'save')()
        if cache:
            object.__setattr__(self, "cached_typeclass_path", defpath)
            object.__setattr__(self, "cached_typeclass", typeclass)
        return typeclass             

    def is_typeclass(self, typeclass, exact=False):
        """
        Returns true if this object has this type
          OR has a typeclass which is an subclass of
          the given typeclass.
        
        typeclass - can be a class object or the
                python path to such an object to match against. 
                
        exact - returns true only if the object's
               type is exactly this typeclass, ignoring
               parents.
        """    
        try:
            typeclass = typeclass.path
        except AttributeError:
            pass 
        if exact:
            current_path = object.__getattribute__(self, "cached_typeclass_path")            
            return typeclass and current_path == typeclass
        else:
            # check parent chain
            return any([cls for cls in self.typeclass.mro()
                        if "%s.%s" % (cls.__module__, cls.__name__) == typeclass])

    #
    # Object manipulation methods
    #              
    #

    def swap_typeclass(self, new_typeclass, clean_attributes=False):
        """
        This performs an in-situ swap of the typeclass. This means
        that in-game, this object will suddenly be something else.
        Player will not be affected. To 'move' a player to a different
        object entirely (while retaining this object's type), use 
        self.player.swap_object().

        Note that this might be an error prone operation if the 
        old/new typeclass was heavily customized - your code
        might expect one and not the other, so be careful to 
        bug test your code if using this feature! Often its easiest
        to create a new object and just swap the player over to
        that one instead. 

        new_typeclass (path/classobj) - type to switch to        
        clean_attributes (bool/list) - will delete all attributes
                           stored on this object (but not any
                           of the database fields such as name or
                           location). You can't get attributes back,
                           but this is often the safest bet to make
                           sure nothing in the new typeclass clashes
                           with the old one. If you supply a list,
                           only those named attributes will be cleared.
        """
        if callable(new_typeclass):
            # this is an actual class object - build the path
            cls = new_typeclass.__class__
            new_typeclass = "%s.%s" % (cls.__module__, cls.__name__)

        # Try to set the new path
        self.db_typeclass_path = new_typeclass.strip()        
        self.save()
        # this will automatically use a default class if
        # there is an error with the given typeclass.
        new_typeclass = self.typeclass(self)
    
        if clean_attributes:
            # Clean out old attributes
            if is_iter(clean_attributes):
                for attr in clean_attributes:
                    self.attr(attr, delete=True)
                for nattr in clean_attributes:
                    if hasattr(self.ndb, nattr):
                        self.nattr(nattr, delete=True)
            else:
                #print "deleting attrs ..."
                self.get_all_attributes()
                for attr in self.get_all_attributes():
                    attr.delete()
                for nattr in self.ndb.all():                    
                    del nattr

        # run hooks for this new typeclass
        new_typeclass.basetype_setup()
        new_typeclass.at_object_creation()
            
    #
    # Attribute handler methods 
    #

    # 
    # Fully persistent attributes. You usually access these 
    # through the obj.db.attrname method. If FULL_PERSISTENCE
    # is set, you will access these by just obj.attrname instead.
    #

    # Helper methods for persistent attributes 
    
    def has_attribute(self, attribute_name):
        """
        See if we have an attribute set on the object.
        
        attribute_name: (str) The attribute's name.
        """        
        exec("from %s import %s" % (self.attribute_model_path, 
                                    self.attribute_model_name))
        model = eval("%s" % self.attribute_model_name)
        attr = model.objects.attr_namesearch(attribute_name, self)
        return attr.count() > 0

    def set_attribute(self, attribute_name, new_value=None):
        """
        Sets an attribute on an object. Creates the attribute if need
        be.
        
        attribute_name: (str) The attribute's name.
        new_value: (python obj) The value to set the attribute to. If this is not
                                a str, the object will be stored as a pickle.  
        """
        attrib_obj = None
        if self.has_attribute(attribute_name):
            exec("from %s import %s" % (self.attribute_model_path, 
                                        self.attribute_model_name))          
            model = eval("%s" % self.attribute_model_name)
            #print "attr: model:", self.attribute_model_name
            attrib_obj = \
                model.objects.filter(
                db_obj=self).filter(
                db_key__iexact=attribute_name)[0]                        
        if attrib_obj:                
            # Save over the existing attribute's value.
            #print "attr:overwrite: %s.%s = %s" % (attrib_obj.db_obj.key, attribute_name, new_value)
            attrib_obj.value = new_value            
        else:
            # Create a new attribute            
            exec("from %s import %s" % (self.attribute_model_path, 
                                        self.attribute_model_name))          
            new_attrib = eval("%s()" % self.attribute_model_name)            
            new_attrib.db_key = attribute_name
            new_attrib.db_obj = self
            new_attrib.value = new_value            
            #print "attr:new: %s.%s = %s" % (new_attrib.db_obj.key, attribute_name, new_value)

    def get_attribute(self, attribute_name, default=None):
        """
        Returns the value of an attribute on an object. You may need to
        type cast the returned value from this function since the attribute
        can be of any type.
        
        attribute_name: (str) The attribute's name.
        default: What to return if no attribute is found
        """
        if self.has_attribute(attribute_name):            
            try:
                exec("from %s import %s" % (self.attribute_model_path, 
                                            self.attribute_model_name))          
                model = eval("%s" % self.attribute_model_name)
                attrib = model.objects.filter(
                    db_obj=self).filter(
                    db_key=attribute_name)[0]
            except Exception:
                # safety, if something goes wrong (like unsynced db), catch it.
                logger.log_trace()
                return default            
            return attrib.value
        else:
            return default
                
    def del_attribute(self, attribute_name):
        """
        Removes an attribute entirely.
        
        attribute_name: (str) The attribute's name.
        """
        exec("from %s import %s" % (self.attribute_model_path, 
                                    self.attribute_model_name))          
        model = eval("%s" % self.attribute_model_name)
        #print "delete attr", model, attribute_name

        attrs = \
           model.objects.attr_namesearch(attribute_name, self)        
        #print "found attrs:", attrs
        if attrs:
            attrs[0].delete()

    def get_all_attributes(self):
        """
        Returns all attributes defined on the object.
        """
        attr_set_all = eval("self.%s_set.all()" % (self.attribute_model_name.lower()))
        return [attr for attr in attr_set_all]

    def attr(self, attribute_name=None, value=None, delete=False):
        """
        This is a convenient wrapper for
        get_attribute, set_attribute, del_attribute
        and get_all_attributes.
        If value is None, attr will act like
        a getter, otherwise as a setter.
        set delete=True to delete the named attribute. 

        Note that you cannot set the attribute
        value to None using this method should you
        want that, use set_attribute for that. 
        """
        if attribute_name == None: 
            # act as a list method
            return self.get_all_attributes()            
        elif delete == True:
            self.del_attribute(attribute_name)
        elif value == None:
            # act as a getter.
            return self.get_attribute(attribute_name)
        else:
            # act as a setter
            self.set_attribute(attribute_name, value)

    #@property
    def db_get(self):
        """
        A second convenience wrapper for the the attribute methods. It
        allows for the syntax
           obj.db.attrname = value
             and 
           value = obj.db.attrname 
             and
           del obj.db.attrname 
             and
           all_attr = obj.db.all() (if there is no attribute named 'all', in which
                                    case that will be returned instead). 
        """
        try:
            return self._db_holder
        except AttributeError:
            class DbHolder(object):
                "Holder for allowing property access of attributes"
                def __init__(self, obj):
                    object.__setattr__(self, 'obj', obj)
                def __getattribute__(self, attrname):                   
                    obj = object.__getattribute__(self, 'obj')                    
                    if attrname == 'all':
                        # we allow for overwriting the all() method
                        # with an attribute named 'all'. 
                        attr = obj.get_attribute("all")
                        if attr:
                            return attr
                        return object.__getattribute__(self, 'all')                                        
                    return obj.get_attribute(attrname)

                def __setattr__(self, attrname, value):                    
                    obj = object.__getattribute__(self, 'obj')
                    obj.set_attribute(attrname, value)
                def __delattr__(self, attrname):                    
                    obj = object.__getattribute__(self, 'obj')                    
                    obj.del_attribute(attrname)
                def all(self):
                    obj = object.__getattribute__(self, 'obj')
                    return obj.get_all_attributes()
            self._db_holder = DbHolder(self)
            return self._db_holder
    #@db.setter
    def db_set(self, value):
        "Stop accidentally replacing the db object"
        string = "Cannot assign directly to db object! "
        string = "Use db.attr=value instead."
        raise Exception(string)
    #@db.deleter
    def db_del(self):
        "Stop accidental deletion."
        raise Exception("Cannot delete the db object!")
    db = property(db_get, db_set, db_del)

    #
    # NON-PERSISTENT store. If you run FULL_PERSISTENT but still
    # want to save something and be sure it's cleared on a server
    # reboot, you should use this explicitly. Otherwise there is 
    # little point in using the non-persistent methods. 
    #

    def nattr(self, attribute_name=None, value=None, delete=False):
        """
        This is the equivalence of self.attr but for non-persistent
        stores.
        """
        if attribute_name == None: 
            # act as a list method
            if callable(self.ndb.all):
                return self.ndb.all()
            else:
                return [val for val in self.ndb.__dict__.keys() 
                        if not val.startswith['_']]                        
        elif delete == True:
            if hasattr(self.ndb, attribute_name):
                object.__delattr__(self.db, attribute_name)
        elif value == None:
            # act as a getter.
            if hasattr(self.ndb, attribute_name):
                object.__getattribute__(self.ndb, attribute_name)
            else:
                return None 
        else:
            # act as a setter
            object.__setattr__(self.db, attribute_name, value)
            
    #@property
    def ndb_get(self):
        """
        A non-persistent store (ndb: NonDataBase). Everything stored 
        to this is guaranteed to be cleared when a server is shutdown.
        Works also if FULL_PERSISTENCE is active. Syntax is as for
        the _get_db_holder() method and property, 
        e.g. obj.ndb.attr = value etc.
        """
        try:
            return self._ndb_holder
        except AttributeError:
            class NdbHolder(object):
                "Holder for storing non-persistent attributes."
                def all(self):
                    return [val for val in self.__dict__.keys() 
                            if not val.startswith['_']]                    
                def __getattribute__(self, key):
                    # return None if no matching attribute was found. 
                    try:
                        return object.__getattribute__(self, key)
                    except AttributeError:
                        return None 
            self._ndb_holder = NdbHolder()
            return self._ndb_holder
    #@ndb.setter
    def ndb_set(self, value):
        "Stop accidentally replacing the db object"
        string = "Cannot assign directly to ndb object! "
        string = "Use ndb.attr=value instead."
        raise Exception(string)
    #@ndb.deleter
    def ndb_del(self):
        "Stop accidental deletion."
        raise Exception("Cannot delete the ndb object!")
    ndb = property(ndb_get, ndb_set, ndb_del)
        
    # Lock / permission methods

    def access(self, accessing_obj, access_type='read', default=False):
        """
        Determines if another object has permission to access.
        accessing_obj - object trying to access this one
        access_type - type of access sought
        default - what to return if no lock of access_type was found
        """        
        return self.locks.check(accessing_obj, access_type=access_type, default=default)

    def has_perm(self, accessing_obj, access_type):
        "Alias to access"
        logger.log_depmsg("has_perm() is deprecated. Use access() instead.")
        return self.access(accessing_obj, access_type)

    def check_permstring(self, permstring):
        """
        This explicitly checks if we hold particular permission without involving
        any locks.
        """
        if self.player and self.player.is_superuser:
            return True 

        if not permstring:
            return False             
        perm = permstring.lower()
        if perm in [p.lower() for p in self.permissions]:
            # simplest case - we have a direct match
            return True 
        if perm in PERMISSION_HIERARCHY:
            # check if we have a higher hierarchy position
            ppos = PERMISSION_HIERARCHY.index(perm)
            return any(True for hpos, hperm in enumerate(PERMISSION_HIERARCHY) 
                       if hperm in [p.lower() for p in self.permissions] and hpos > ppos)
        return False 
