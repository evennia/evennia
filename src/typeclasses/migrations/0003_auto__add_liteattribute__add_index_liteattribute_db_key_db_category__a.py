# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'LiteAttribute'
        db.create_table(u'typeclasses_liteattribute', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('db_key', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('db_category', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('db_data', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'typeclasses', ['LiteAttribute'])

        # Adding index on 'LiteAttribute', fields ['db_key', 'db_category']
        db.create_index(u'typeclasses_liteattribute', ['db_key', 'db_category'])

        # Adding model 'Tag'
        db.create_table(u'typeclasses_tag', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('db_key', self.gf('django.db.models.fields.CharField')(max_length=255, null=True)),
            ('db_category', self.gf('django.db.models.fields.CharField')(max_length=64, null=True)),
            ('db_data', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'typeclasses', ['Tag'])

        # Adding unique constraint on 'Tag', fields ['db_key', 'db_category']
        db.create_unique(u'typeclasses_tag', ['db_key', 'db_category'])

        # Adding index on 'Tag', fields ['db_key', 'db_category']
        db.create_index(u'typeclasses_tag', ['db_key', 'db_category'])


    def backwards(self, orm):
        # Removing index on 'Tag', fields ['db_key', 'db_category']
        db.delete_index(u'typeclasses_tag', ['db_key', 'db_category'])

        # Removing unique constraint on 'Tag', fields ['db_key', 'db_category']
        db.delete_unique(u'typeclasses_tag', ['db_key', 'db_category'])

        # Removing index on 'LiteAttribute', fields ['db_key', 'db_category']
        db.delete_index(u'typeclasses_liteattribute', ['db_key', 'db_category'])

        # Deleting model 'LiteAttribute'
        db.delete_table(u'typeclasses_liteattribute')

        # Deleting model 'Tag'
        db.delete_table(u'typeclasses_tag')


    models = {
        u'typeclasses.attribute': {
            'Meta': {'object_name': 'Attribute'},
            'db_date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'db_key': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'db_lock_storage': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'db_value': ('src.utils.picklefield.PickledObjectField', [], {'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'typeclasses.liteattribute': {
            'Meta': {'object_name': 'LiteAttribute', 'index_together': "(('db_key', 'db_category'),)"},
            'db_category': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'db_data': ('django.db.models.fields.TextField', [], {}),
            'db_key': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'typeclasses.tag': {
            'Meta': {'unique_together': "(('db_key', 'db_category'),)", 'object_name': 'Tag', 'index_together': "(('db_key', 'db_category'),)"},
            'db_category': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True'}),
            'db_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'db_key': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['typeclasses']
