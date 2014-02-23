# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'ScriptDB.db_player'
        db.add_column(u'scripts_scriptdb', 'db_player',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['players.PlayerDB'], null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'ScriptDB.db_player'
        db.delete_column(u'scripts_scriptdb', 'db_player_id')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'objects.objectdb': {
            'Meta': {'object_name': 'ObjectDB'},
            'db_attributes': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['typeclasses.Attribute']", 'null': 'True', 'symmetrical': 'False'}),
            'db_cmdset_storage': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'db_date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'db_destination': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'destinations_set'", 'null': 'True', 'to': u"orm['objects.ObjectDB']"}),
            'db_home': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'homes_set'", 'null': 'True', 'to': u"orm['objects.ObjectDB']"}),
            'db_key': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'db_location': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'locations_set'", 'null': 'True', 'to': u"orm['objects.ObjectDB']"}),
            'db_lock_storage': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'db_player': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['players.PlayerDB']", 'null': 'True', 'blank': 'True'}),
            'db_sessid': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'db_tags': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['typeclasses.Tag']", 'null': 'True', 'symmetrical': 'False'}),
            'db_typeclass_path': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'players.playerdb': {
            'Meta': {'object_name': 'PlayerDB'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'db_attributes': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['typeclasses.Attribute']", 'null': 'True', 'symmetrical': 'False'}),
            'db_cmdset_storage': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'db_date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'db_is_bot': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'db_is_connected': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'db_key': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'db_lock_storage': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'db_tags': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['typeclasses.Tag']", 'null': 'True', 'symmetrical': 'False'}),
            'db_typeclass_path': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'scripts.scriptdb': {
            'Meta': {'object_name': 'ScriptDB'},
            'db_attributes': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['typeclasses.Attribute']", 'null': 'True', 'symmetrical': 'False'}),
            'db_date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'db_desc': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'db_interval': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'db_is_active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'db_key': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'db_lock_storage': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'db_obj': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['objects.ObjectDB']", 'null': 'True', 'blank': 'True'}),
            'db_persistent': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'db_player': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['players.PlayerDB']", 'null': 'True', 'blank': 'True'}),
            'db_repeats': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'db_start_delay': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'db_tags': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['typeclasses.Tag']", 'null': 'True', 'symmetrical': 'False'}),
            'db_typeclass_path': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
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

    complete_apps = ['scripts']