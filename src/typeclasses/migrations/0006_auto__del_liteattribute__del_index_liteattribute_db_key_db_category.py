# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    depends_on = (("scripts", "0014_create_db_liteattributes_db_tags"),
                  ("objects", "0022_add_db_liteattributes_db_tags"),
                  ("players", "0025_auto__add_db_liteattributes_db_tags"))

    def forwards(self, orm):
        # Deleting model 'LiteAttribute'
        db.delete_table(u'typeclasses_liteattribute')

    def backwards(self, orm):
        # Adding index on 'LiteAttribute', fields ['db_key', 'db_category']
        db.create_index(u'typeclasses_liteattribute', ['db_key', 'db_category'])

        # Adding model 'LiteAttribute'
        db.create_table(u'typeclasses_liteattribute', (
            ('db_category', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('db_key', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('db_data', self.gf('django.db.models.fields.TextField')()),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal(u'typeclasses', ['LiteAttribute'])


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
        u'typeclasses.tag': {
            'Meta': {'unique_together': "(('db_key', 'db_category'),)", 'object_name': 'Tag', 'index_together': "(('db_key', 'db_category'),)"},
            'db_category': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'db_index': 'True'}),
            'db_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'db_key': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['typeclasses']
