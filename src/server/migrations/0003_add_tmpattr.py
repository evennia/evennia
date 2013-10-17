# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'TmpAttribute'
        db.create_table(u'server_tmpattribute', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('db_key', self.gf('django.db.models.fields.CharField')(max_length=255, db_index=True)),
            ('db_value', self.gf('src.utils.picklefield.PickledObjectField')(null=True)),
            ('db_lock_storage', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('db_obj_id', self.gf('django.db.models.fields.IntegerField')(null=True)),
            ('db_obj_type', self.gf('django.db.models.fields.CharField')(max_length=10, null=True)),
            ('db_date_created', self.gf('django.db.models.fields.DateTimeField')(editable=True, auto_now_add=False)),
        ))
        db.send_create_signal('server', ['TmpAttribute'])


    def backwards(self, orm):
        # Deleting model 'TmpAttribute'
        db.delete_table(u'server_tmpattribute')


    models = {
        u'server.serverconfig': {
            'Meta': {'object_name': 'ServerConfig'},
            'db_key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64'}),
            'db_value': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'server.tmpattribute': {
            'Meta': {'object_name': 'TmpAttribute'},
            'db_key': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'db_lock_storage': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'db_obj_id': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'db_obj_type': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True'}),
            'db_value': ('src.utils.picklefield.PickledObjectField', [], {'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'db_date_created':('django.db.models.fields.DateTimeField',[],{'editable':'True', 'auto_now_add':'True'}),
        }
    }

    complete_apps = ['server']
