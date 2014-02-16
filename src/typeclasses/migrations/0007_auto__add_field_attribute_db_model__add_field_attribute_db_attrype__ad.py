# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Attribute.db_model'
        db.add_column(u'typeclasses_attribute', 'db_model',
                      self.gf('django.db.models.fields.CharField')(db_index=True, max_length=32, null=True, blank=True),
                      keep_default=False)

        # Adding field 'Attribute.db_attrtype'
        db.add_column(u'typeclasses_attribute', 'db_attrtype',
                      self.gf('django.db.models.fields.CharField')(db_index=True, max_length=16, null=True, blank=True),
                      keep_default=False)

        # Adding field 'Tag.db_model'
        db.add_column(u'typeclasses_tag', 'db_model',
                      self.gf('django.db.models.fields.CharField')(max_length=32, null=True, db_index=True),
                      keep_default=False)

        # Adding field 'Tag.db_tagtype'
        db.add_column(u'typeclasses_tag', 'db_tagtype',
                      self.gf('django.db.models.fields.CharField')(max_length=16, null=True, db_index=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Attribute.db_model'
        db.delete_column(u'typeclasses_attribute', 'db_model')

        # Deleting field 'Attribute.db_attrtype'
        db.delete_column(u'typeclasses_attribute', 'db_attrtype')

        # Deleting field 'Tag.db_model'
        db.delete_column(u'typeclasses_tag', 'db_model')

        # Deleting field 'Tag.db_tagtype'
        db.delete_column(u'typeclasses_tag', 'db_tagtype')


    models = {
        u'typeclasses.attribute': {
            'Meta': {'object_name': 'Attribute'},
            'db_attrtype': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '16', 'null': 'True', 'blank': 'True'}),
            'db_category': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'db_date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'db_key': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'db_lock_storage': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'db_model': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'db_strvalue': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'db_value': ('src.utils.picklefield.PickledObjectField', [], {'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'typeclasses.tag': {
            'Meta': {'unique_together': "(('db_key', 'db_category'),)", 'object_name': 'Tag', 'index_together': "(('db_key', 'db_category'),)"},
            'db_category': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'db_index': 'True'}),
            'db_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'db_key': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'db_index': 'True'}),
            'db_model': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'db_index': 'True'}),
            'db_tagtype': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['typeclasses']
