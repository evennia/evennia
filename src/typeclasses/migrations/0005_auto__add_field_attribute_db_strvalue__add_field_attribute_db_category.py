# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Attribute.db_strvalue'
        db.add_column(u'typeclasses_attribute', 'db_strvalue',
                      self.gf('django.db.models.fields.TextField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Attribute.db_category'
        db.add_column(u'typeclasses_attribute', 'db_category',
                      self.gf('django.db.models.fields.CharField')(db_index=True, max_length=128, null=True, blank=True),
                      keep_default=False)

        # Adding index on 'Tag', fields ['db_category']
        db.create_index(u'typeclasses_tag', ['db_category'])

        # Adding index on 'Tag', fields ['db_key']
        db.create_index(u'typeclasses_tag', ['db_key'])


    def backwards(self, orm):
        # Removing index on 'Tag', fields ['db_key']
        db.delete_index(u'typeclasses_tag', ['db_key'])

        # Removing index on 'Tag', fields ['db_category']
        db.delete_index(u'typeclasses_tag', ['db_category'])

        # Deleting field 'Attribute.db_strvalue'
        db.delete_column(u'typeclasses_attribute', 'db_strvalue')

        # Deleting field 'Attribute.db_category'
        db.delete_column(u'typeclasses_attribute', 'db_category')


    models = {
        u'typeclasses.attribute': {
            'Meta': {'object_name': 'Attribute'},
            'db_category': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'db_date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'db_key': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'db_lock_storage': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'db_strvalue': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
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
            'db_category': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'db_index': 'True'}),
            'db_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'db_key': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['typeclasses']