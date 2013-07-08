# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Attribute'
        db.create_table(u'typeclasses_attribute', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('db_key', self.gf('django.db.models.fields.CharField')(max_length=255, db_index=True)),
            ('db_value', self.gf('src.utils.picklefield.PickledObjectField')(null=True)),
            ('db_lock_storage', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('db_date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal(u'typeclasses', ['Attribute'])


    def backwards(self, orm):
        # Deleting model 'Attribute'
        db.delete_table(u'typeclasses_attribute')


    models = {
        u'typeclasses.attribute': {
            'Meta': {'object_name': 'Attribute'},
            'db_date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'db_key': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'db_lock_storage': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'db_value': ('src.utils.picklefield.PickledObjectField', [], {'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['typeclasses']