# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):
    depends_on = (('server', '0003_add_tmpattr'),)
    no_dry_run=True
    def forwards(self, orm):
        "Write your forwards methods here."
        # Note: Remember to use orm['appname.ModelName'] rather than "from appname.models..."

        for tmpattr in orm['server.TmpAttribute'].objects.all():
            typ = tmpattr.db_obj_type
            dbid = tmpattr.db_obj_id
            if typ == 'objectdb':
                try:
                    dbobj = orm['objects.ObjectDB'].objects.get(dbid)
                except:
                    print "could not find objid %i" % objid
                    continue
            elif typ == 'playerdb':
                try:
                    dbobj = orm['players.PlayerDB'].objects.get(dbid)
                except:
                    print "could not find objid %i" % objid
                    continue
            elif typ == 'scriptdb':
                try:
                    dbobj = orm['scripts.ScriptDB'].objects.get(dbid)
                except:
                    print "could not find objid %i" % objid
                    continue
            else:
                print "Wrong object type to store on: %s" % typ
                continue
            dbattr = orm['typeclasses.Attribute'].create(db_key=tmpattr.db_key,
                                                         db_value=tmpattr.db_value,
                                                         db_lock_storage=tmpattr.db_lock_storage,
                                                         db_date_created=tmpattr.db_date)

            dbattr.save()
            dbobj.db_attributes.add(dbattr)


    def backwards(self, orm):
        "Write your backwards methods here."
        raise RuntimeError("Cannot revert this migration.")

    models = {
        u'server.serverconfig': {
            'Meta': {'object_name': 'ServerConfig'},
            'db_key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64'}),
            'db_value': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'server.tmpattribute': {
            'Meta': {'object_name': 'TmpAttribute'},
            'db_date_created': ('django.db.models.fields.DateTimeField', [], {}),
            'db_key': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'db_lock_storage': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'db_obj_id': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'db_obj_type': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True'}),
            'db_value': ('src.utils.picklefield.PickledObjectField', [], {'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'typeclasses.attribute': {
            'Meta': {'object_name': 'Attribute'},
            'db_date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'db_key': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'db_lock_storage': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'db_value': ('src.utils.picklefield.PickledObjectField', [], {'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['server', 'typeclasses']
    symmetrical = True
