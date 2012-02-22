# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

try:
    import cPickle as pickle
except ImportError:
    import pickle
from src.utils.utils import to_str, to_unicode
from src.typeclasses.models import PackedDBobject,PackedDict,PackedList

from django.contrib.contenttypes.models import ContentType
CTYPEGET = ContentType.objects.get
GA = object.__getattribute__
SA = object.__setattr__
DA = object.__delattr__

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

def from_attr(attr, datatuple):
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
        mclass = CTYPEGET(model=data.db_model).model_class()
        try:
            return mclass.objects.dbref_search(data.id)

        except AttributeError:
            try:
                return mclass.objects.get(id=data.id)
            except mclass.DoesNotExist: # could happen if object was deleted in the interim.
                return None                

    def iter_id2db(item):
        """
        Recursively looping through stored iterables, replacing ids with actual objects.
        We return PackedDict and PackedLists instead of normal lists; this is needed in order for
        the user to do dynamic saving of nested in-place, such as obj.db.attrlist[2]=3. What is
        stored in the database are however always normal python primitives. 
        """
        dtype = type(item)
        if dtype in (basestring, int, float): # check the most common types first, for speed
            return item 
        elif dtype == PackedDBobject:
            return id2db(item)
        elif dtype == tuple:                        
            return tuple([iter_id2db(val) for val in item])
        elif dtype in (dict, PackedDict):
            return PackedDict(attr, dict(zip([key for key in item.keys()],
                                             [iter_id2db(val) for val in item.values()])))
        elif hasattr(item, '__iter__'):
            return PackedList(attr, list(iter_id2db(val) for val in item))
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

class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."

        for attr in orm.ObjAttribute.objects.all():
            # repack attr into new format, and reimport
            try:
                val = pickle.loads(to_str(attr.db_value))
                if hasattr(val, '__iter__'):
                    val = ("iter", val)
                elif type(val) == PackedDBobject:
                    val = ("dbobj", val)
                else:
                    val = ("simple", val)
                attr.db_value = to_unicode(pickle.dumps(to_str(to_attr(from_attr(attr, val)))))
                attr.save()
            except TypeError, RuntimeError: 
                pass 
                                      
    def backwards(self, orm):
        "Write your backwards methods here."
        raise RuntimeError

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
            'db_lock_storage': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'}),
            'db_obj': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['objects.ObjectDB']"}),
            'db_value': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
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
            'db_lock_storage': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'}),
            'db_permissions': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'db_player': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['players.PlayerDB']", 'null': 'True', 'blank': 'True'}),
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
            'db_key': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'db_lock_storage': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'}),
            'db_obj': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['objects.ObjectDB']", 'null': 'True', 'blank': 'True'}),
            'db_permissions': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'db_typeclass_path': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'})
        }
    }

    complete_apps = ['objects']
