# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models
from django.contrib.contenttypes.models import ContentType

from src.utils.utils import to_str
from src.utils.dbserialize import to_pickle
try:
    import cPickle as pickle
except ImportError:
    import pickle
CTYPEGET = ContentType.objects.get
GA = object.__getattribute__
SA = object.__setattr__
DA = object.__delattr__


# overloading pickle to have it find the PackedDBobj in this module
import pickle

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

renametable = {
        'src.typeclasses.models': 'src.objects.migrations.0019_convert_attrdata',
        'PackedDBobject': 'PackedDBobject',
}

def mapname(name):
    if name in renametable:
        return renametable[name]
    return name

def mapped_load_global(self):
    module = mapname(self.readline()[:-1])
    name = mapname(self.readline()[:-1])
    klass = self.find_class(module, name)
    self.append(klass)

def loads(str):
    file = StringIO(str)
    unpickler = pickle.Unpickler(file)
    unpickler.dispatch[pickle.GLOBAL] = mapped_load_global
    return unpickler.load()



class PackedDBobject(object):
    """
    Attribute helper class.
    A container for storing and easily identifying database objects in
    the database (which doesn't suppport storing db_objects directly).
    """
    def __init__(self, ID, db_model, db_key):
        self.id = ID
        self.db_model = db_model
        self.key = db_key
    def __str__(self):
        return "%s(#%s)" % (self.key, self.id)
    def __unicode__(self):
        return u"%s(#%s)" % (self.key, self.id)

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

         The 'parent' property is set to 'init' at creation,
         this stops the system from saving itself over and over
         when first assigning the dict. Once initialization
         is over, the Attribute from_attr() method will assign
         the parent (or None, if at the root)

        """
        self.db_obj = db_obj
        self.parent = 'init'
        super(PackedDict, self).__init__(*args, **kwargs)
    def __str__(self):
        return "{%s}" % ", ".join("%s:%s" % (key, str(val)) for key, val in self.items())
    def save(self):
        "Relay save operation upwards in tree until we hit the root."
        if self.parent == 'init':
            pass
        elif self.parent:
            self.parent.save()
        else:
            self.db_obj.value = self
    def __setitem__(self, *args, **kwargs):
        "assign item to this dict"
        super(PackedDict, self).__setitem__(*args, **kwargs)
        self.save()
    def __delitem__(self, *args, **kwargs):
        "delete with del self[key]"
        super(PackedDict, self).__delitem__(*args, **kwargs)
        self.save()
    def clear(self, *args, **kwargs):
        "Custom clear"
        super(PackedDict, self).clear(*args, **kwargs)
        self.save()
    def pop(self, *args, **kwargs):
        "Custom pop"
        ret = super(PackedDict, self).pop(*args, **kwargs)
        self.save()
        return ret
    def popitem(self, *args, **kwargs):
        "Custom popitem"
        ret = super(PackedDict, self).popitem(*args, **kwargs)
        self.save()
        return ret
    def setdefault(self, *args, **kwargs):
        "Custom setdefault"
        super(PackedDict, self).setdefault(*args, **kwargs)
        self.save()
    def update(self, *args, **kwargs):
        "Custom update"
        super(PackedDict, self).update(*args, **kwargs)
        self.save()

class PackedList(list):
    """
    Attribute helper class.
    A variant of list that stores itself to the database when
    updating one of its keys. This is called and handled by
    Attribute.validate_data().
    """
    def __init__(self, db_obj, *args, **kwargs):
        """
        sets up the packing list.
         db_obj - the attribute object storing this list.

         the 'parent' property is set to 'init' at creation,
         this stops the system from saving itself over and over
         when first assigning the dict. once initialization
         is over, the attribute from_attr() method will assign
         the parent (or none, if at the root)

        """
        self.db_obj = db_obj
        self.parent = 'init'
        super(PackedList, self).__init__(*args, **kwargs)
    def __str__(self):
        return "[%s]" % ", ".join(str(val) for val in self)
    def save(self):
        "relay save operation upwards in tree until we hit the root."
        if self.parent == 'init':
            pass
        elif self.parent:
            self.parent.save()
        else:
            self.db_obj.value = self
    def __setitem__(self, *args, **kwargs):
        "Custom setitem that stores changed list to database."
        super(PackedList, self).__setitem__(*args, **kwargs)
        self.save()
    def __delitem__(self, *args, **kwargs):
        "delete with del self[index]"
        super(PackedList, self).__delitem__(*args, **kwargs)
        self.save()
    def append(self, *args, **kwargs):
        "Custom append"
        super(PackedList, self).append(*args, **kwargs)
        self.save()
    def extend(self, *args, **kwargs):
        "Custom extend"
        super(PackedList, self).extend(*args, **kwargs)
        self.save()
    def insert(self, *args, **kwargs):
        "Custom insert"
        super(PackedList, self).insert(*args, **kwargs)
        self.save()
    def remove(self, *args, **kwargs):
        "Custom remove"
        super(PackedList, self).remove(*args, **kwargs)
        self.save()
    def pop(self, *args, **kwargs):
        "Custom pop"
        ret = super(PackedList, self).pop(*args, **kwargs)
        self.save()
        return ret
    def reverse(self, *args, **kwargs):
        "Custom reverse"
        super(PackedList, self).reverse(*args, **kwargs)
        self.save()
    def sort(self, *args, **kwargs):
        "Custom sort"
        super(PackedList, self).sort(*args, **kwargs)
        self.save()

class PackedSet(set):
    """
    A variant of Set that stores new updates to the databse.
    """
    def __init__(self, db_obj, *args, **kwargs):
        """
        sets up the packing set.
         db_obj - the attribute object storing this set

         the 'parent' property is set to 'init' at creation,
         this stops the system from saving itself over and over
         when first assigning the dict. once initialization
         is over, the attribute from_attr() method will assign
         the parent (or none, if at the root)

        """
        self.db_obj = db_obj
        self.parent = 'init'
        super(PackedSet, self).__init__(*args, **kwargs)
    def __str__(self):
        return "{%s}" % ", ".join(str(val) for val in self)
    def save(self):
        "relay save operation upwards in tree until we hit the root."
        if self.parent == 'init':
            pass
        elif self.parent:
            self.parent.save()
        else:
            self.db_obj.value = self
    def add(self, *args, **kwargs):
        "Add an element to the set"
        super(PackedSet, self).add(*args, **kwargs)
        self.save()
    def clear(self, *args, **kwargs):
        "Remove all elements from this set"
        super(PackedSet, self).clear(*args, **kwargs)
        self.save()
    def difference_update(self, *args, **kwargs):
        "Remove all elements of another set from this set."
        super(PackedSet, self).difference_update(*args, **kwargs)
        self.save()
    def discard(self, *args, **kwargs):
        "Remove an element from a set if it is a member.\nIf not a member, do nothing."
        super(PackedSet, self).discard(*args, **kwargs)
        self.save()
    def intersection_update(self, *args, **kwargs):
        "Update a set with the intersection of itself and another."
        super(PackedSet, self).intersection_update(*args, **kwargs)
        self.save()
    def pop(self, *args, **kwargs):
        "Remove and return an arbitrary set element.\nRaises KeyError if the set is empty."
        super(PackedSet, self).pop(*args, **kwargs)
        self.save()
    def remove(self, *args, **kwargs):
        "Remove an element from a set; it must be a member.\nIf the element is not a member, raise a KeyError."
        super(PackedSet, self).remove(*args, **kwargs)
        self.save()
    def symmetric_difference_update(self, *args, **kwargs):
        "Update a set with the symmetric difference of itself and another."
        super(PackedSet, self).symmetric_difference_update(*args, **kwargs)
        self.save()
    def update(self, *args, **kwargs):
        "Update a set with the union of itself and others."
        super(PackedSet, self).update(*args, **kwargs)
        self.save()

def to_attr(data):
    """
    Convert data to proper attr data format before saving

    We have to make sure to not store database objects raw, since
    this will crash the system. Instead we must store their IDs
    and make sure to convert back when the attribute is read back
    later.

    Due to this it's criticial that we check all iterables
    recursively, converting all found database objects to a form
    the database can handle. We handle lists, tuples and dicts
    (and any nested combination of them) this way, all other
    iterables are stored and returned as lists.

    data storage format:
       (simple|dbobj|iter, <data>)
    where
       simple - a single non-db object, like a string or number
       dbobj - a single dbobj
       iter - any iterable object - will be looped over recursively
              to convert dbobj->id.

    """

    def iter_db2id(item):
        """
        recursively looping through stored iterables, replacing objects with ids.
        (Python only builds nested functions once, so there is no overhead for nesting)
        """
        dtype = type(item)
        if dtype in (basestring, int, float): # check the most common types first, for speed
            return item
        elif hasattr(item, "id") and hasattr(item, "db_model_name") and hasattr(item, "db_key"):
            db_model_name = item.db_model_name
            if db_model_name == "typeclass":
                db_model_name = GA(item.dbobj, "db_model_name")
            return PackedDBobject(item.id, db_model_name, item.db_key)
        elif dtype == tuple:
            return tuple(iter_db2id(val) for val in item)
        elif dtype in (dict, PackedDict):
            return dict((key, iter_db2id(val)) for key, val in item.items())
        elif hasattr(item, '__iter__'):
            return list(iter_db2id(val) for val in item)
        else:
            return item

    dtype = type(data)

    if dtype in (basestring, int, float):
        return ("simple",data)
    elif hasattr(data, "id") and hasattr(data, "db_model_name") and hasattr(data, 'db_key'):
        # all django models (objectdb,scriptdb,playerdb,channel,msg,typeclass)
        # have the protected property db_model_name hardcoded on themselves for speed.
        db_model_name = data.db_model_name
        if db_model_name == "typeclass":
            # typeclass cannot help us, we want the actual child object model name
            db_model_name = GA(data.dbobj, "db_model_name")
        return ("dbobj", PackedDBobject(data.id, db_model_name, data.db_key))
    elif hasattr(data, "__iter__"):
        return ("iter", iter_db2id(data))
    else:
        return ("simple", data)


class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        # Note: Remember to use orm['appname.ModelName'] rather than "from appname.models..."

        # modified for migration - converts to plain python properties
        def from_attr(datatuple):
            """
            Retrieve data from a previously stored attribute. This
            is always a dict with keys type and data.

            datatuple comes from the database storage and has
            the following format:
               (simple|dbobj|iter, <data>)
            where
                simple - a single non-db object, like a string. is returned as-is.
                dbobj - a single dbobj-id. This id is retrieved back from the database.
                iter - an iterable. This is traversed iteratively, converting all found
                       dbobj-ids back to objects. Also, all lists and dictionaries are
                       returned as their PackedList/PackedDict counterparts in order to
                       allow in-place assignment such as obj.db.mylist[3] = val. Mylist
                       is then a PackedList that saves the data on the fly.
            """
            # nested functions
            def id2db(data):
                """
                Convert db-stored dbref back to object
                """
                #app_map = {'objectdb':".objects.objectdb", "scriptdb":"scripts.scriptdb", "playerdb":"players.playerdb"}
                #print "data.db_model:", data.db_model
                #mclass = orm[data.db_model].model_class()
                mclass = CTYPEGET(model=data.db_model).model_class()
                try:
                    return mclass.objects.get(id=data.id)
                except AttributeError:
                    try:
                        return mclass.objects.get(id=data.id)
                    except mclass.DoesNotExist: # could happen if object was deleted in the interim.
                        return None
                except TypeError, e:
                    print e

            def iter_id2db(item):
                """
                Recursively looping through stored iterables, replacing ids with actual objects.
                We return PackedDict and PackedLists instead of normal lists; this is needed in order for
                the user to do dynamic saving of nested in-place, such as obj.db.attrlist[2]=3. What is
                stored in the database are however always normal python primitives.
                """
                dtype = type(item)
                if dtype in (basestring, int, float, long, bool): # check the most common types first, for speed
                    return item
                elif dtype == PackedDBobject or hasattr(item, '__class__') and item.__class__.__name__ == "PackedDBobject":
                    return id2db(item)
                elif dtype == tuple:
                    return tuple([iter_id2db(val) for val in item])
                elif dtype in (dict, PackedDict):
                    return dict(zip([key for key in item.keys()],
                                                     [iter_id2db(val) for val in item.values()]))
                elif hasattr(item, '__iter__'):
                    return list(iter_id2db(val) for val in item)
                else:
                    return item

            typ, data = datatuple

            if typ == 'simple':
                # single non-db objects
                return data
            elif typ == 'dbobj':
                # a single stored dbobj
                return id2db(data)
            elif typ == 'iter':
                # all types of iterables
                return iter_id2db(data)

        if not db.dry_run:
            for attr in orm['objects.ObjAttribute'].objects.all():
                # repack attr into new format and reimport
                datatuple = loads(to_str(attr.db_value))
                python_data = from_attr(datatuple)
                new_data = to_pickle(python_data)
                attr.db_value2 = new_data # new pickleObjectField
                attr.save()

    def backwards(self, orm):
        "Write your backwards methods here."
        raise RuntimeError("This migration cannot be reversed.")

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'objects.alias': {
            'Meta': {'object_name': 'Alias'},
            'db_key': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'db_obj': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['objects.ObjectDB']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'objects.objattribute': {
            'Meta': {'object_name': 'ObjAttribute'},
            'db_date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'db_key': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'db_lock_storage': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'db_obj': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['objects.ObjectDB']"}),
            'db_value': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'db_value2': ('src.utils.picklefield.PickledObjectField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'objects.objectdb': {
            'Meta': {'object_name': 'ObjectDB'},
            'db_cmdset_storage': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'db_date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'db_destination': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'destinations_set'", 'null': 'True', 'to': "orm['objects.ObjectDB']"}),
            'db_home': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'homes_set'", 'null': 'True', 'to': "orm['objects.ObjectDB']"}),
            'db_key': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'db_location': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'locations_set'", 'null': 'True', 'to': "orm['objects.ObjectDB']"}),
            'db_lock_storage': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'db_permissions': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'db_player': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['players.PlayerDB']", 'null': 'True', 'blank': 'True'}),
            'db_sessid': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'db_typeclass_path': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'objects.objectnick': {
            'Meta': {'unique_together': "(('db_nick', 'db_type', 'db_obj'),)", 'object_name': 'ObjectNick'},
            'db_nick': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'db_obj': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['objects.ObjectDB']"}),
            'db_real': ('django.db.models.fields.TextField', [], {}),
            'db_type': ('django.db.models.fields.CharField', [], {'default': "'inputline'", 'max_length': '16', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'players.playerdb': {
            'Meta': {'object_name': 'PlayerDB'},
            'db_cmdset_storage': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'db_date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'db_is_connected': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'db_key': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'db_lock_storage': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'db_permissions': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'db_typeclass_path': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'})
        }
    }

    complete_apps = ['objects']
    symmetrical = True
