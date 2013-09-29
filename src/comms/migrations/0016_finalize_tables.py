# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        # Note: Don't use "from appname.models import ModelName". 
        # Use orm.ModelName to refer to models in this application,
        # and orm['appname.ModelName'] for models in other applications.
        db.rename_table('comms_interimchannel', 'comms_channeldb')
        db.rename_table('comms_interimchannel_db_attributes', 'comms_channeldb_db_attributes')
        db.rename_table('comms_interimchannel_db_tags', 'comms_channeldb_db_tags')
        db.rename_column('comms_channeldb_db_attributes', 'interimchannel_id', 'channeldb_id')
        db.rename_column('comms_channeldb_db_tags', 'interimchannel_id', 'channeldb_id')


    def backwards(self, orm):
        "Write your backwards methods here."
        db.rename_column('comms_channeldb_db_attributes', 'channeldb_id', 'interimchannel_id')
        db.rename_column('comms_channeldb_db_tags', 'channeldb_id', 'interimchannel_id')
        db.rename_table('comms_channeldb', 'comms_interimchannel')
        db.rename_table('comms_channeldb_db_attributes', 'comms_interimchannel_db_attributes')
        db.rename_table('comms_channeldb_db_tags', 'comms_interimchannel_db_tags')

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
        u'comms.externalchannelconnection': {
            'Meta': {'object_name': 'ExternalChannelConnection'},
            'db_channel': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['comms.ChannelDB']"}),
            'db_external_config': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'db_external_key': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'db_external_send_code': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'db_is_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'comms.interimchannel': {
            'Meta': {'object_name': 'InterimChannel'},
            'db_attributes': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['typeclasses.Attribute']", 'null': 'True', 'symmetrical': 'False'}),
            'db_date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'db_key': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'db_lock_storage': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'db_tags': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['typeclasses.Tag']", 'null': 'True', 'symmetrical': 'False'}),
            'db_typeclass_path': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'comms.channeldb': {
            'Meta': {'object_name': 'ChannelDB'},
            'db_attributes': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['typeclasses.Attribute']", 'null': 'True', 'symmetrical': 'False'}),
            'db_date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'db_key': ('django.db.models.fields.CharField', [], {'max_length': '255', 'db_index': 'True'}),
            'db_lock_storage': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'db_tags': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['typeclasses.Tag']", 'null': 'True', 'symmetrical': 'False'}),
            'db_typeclass_path': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'comms.msg': {
            'Meta': {'object_name': 'Msg'},
            'db_date_sent': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'db_header': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'db_hide_from_channels': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'hide_from_channels_set'", 'null': 'True', 'to': u"orm['comms.ChannelDB']"}),
            'db_hide_from_objects': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'hide_from_objects_set'", 'null': 'True', 'to': u"orm['objects.ObjectDB']"}),
            'db_hide_from_players': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'hide_from_players_set'", 'null': 'True', 'to': u"orm['players.PlayerDB']"}),
            'db_lock_storage': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'db_message': ('django.db.models.fields.TextField', [], {}),
            'db_receivers_channels': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'channel_set'", 'null': 'True', 'to': u"orm['comms.ChannelDB']"}),
            'db_receivers_objects': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'receiver_object_set'", 'null': 'True', 'to': u"orm['objects.ObjectDB']"}),
            'db_receivers_players': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'receiver_player_set'", 'null': 'True', 'to': u"orm['players.PlayerDB']"}),
            'db_sender_external': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'db_index': 'True'}),
            'db_sender_objects': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'sender_object_set'", 'null': 'True', 'db_index': 'True', 'to': u"orm['objects.ObjectDB']"}),
            'db_sender_players': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'sender_player_set'", 'null': 'True', 'db_index': 'True', 'to': u"orm['players.PlayerDB']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'comms.playerchannelconnection': {
            'Meta': {'object_name': 'PlayerChannelConnection'},
            'db_channel': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['comms.ChannelDB']"}),
            'db_player': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['players.PlayerDB']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
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

    complete_apps = ['comms']
    symmetrical = True
