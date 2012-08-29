# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from south import orm

class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Msg.db_hide_from_channels'
        db.delete_column('comms_msg', 'db_hide_from_channels')

        # Deleting field 'Msg.db_hide_from_receivers'
        db.delete_column('comms_msg', 'db_hide_from_receivers')

        # Deleting field 'Msg.db_receivers'
        db.delete_column('comms_msg', 'db_receivers')

        # Deleting field 'Msg.db_channels'
        db.delete_column('comms_msg', 'db_channels')

        # Deleting field 'Msg.db_hide_from_sender'
        db.delete_column('comms_msg', 'db_hide_from_sender')

        # Deleting field 'Msg.db_sender'
        db.delete_column('comms_msg', 'db_sender_id')

        # Adding field 'Msg.db_title'
        db.add_column('comms_msg', 'db_title',
                      self.gf('django.db.models.fields.CharField')(db_index=True, max_length=512, null=True, blank=True),
                      keep_default=False)

        # Adding M2M table for field db_sender_players on 'Msg'
        db.create_table('comms_msg_db_sender_players', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('msg', models.ForeignKey(orm['comms.msg'], null=False)),
            ('playerdb', models.ForeignKey(orm['players.playerdb'], null=False))
        ))
        db.create_unique('comms_msg_db_sender_players', ['msg_id', 'playerdb_id'])

        # Adding M2M table for field db_sender_objects on 'Msg'
        db.create_table('comms_msg_db_sender_objects', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('msg', models.ForeignKey(orm['comms.msg'], null=False)),
            ('objectdb', models.ForeignKey(orm['objects.objectdb'], null=False))
        ))
        db.create_unique('comms_msg_db_sender_objects', ['msg_id', 'objectdb_id'])

        # Adding M2M table for field db_receivers_players on 'Msg'
        db.create_table('comms_msg_db_receivers_players', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('msg', models.ForeignKey(orm['comms.msg'], null=False)),
            ('playerdb', models.ForeignKey(orm['players.playerdb'], null=False))
        ))
        db.create_unique('comms_msg_db_receivers_players', ['msg_id', 'playerdb_id'])

        # Adding M2M table for field db_receivers_objects on 'Msg'
        db.create_table('comms_msg_db_receivers_objects', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('msg', models.ForeignKey(orm['comms.msg'], null=False)),
            ('objectdb', models.ForeignKey(orm['objects.objectdb'], null=False))
        ))
        db.create_unique('comms_msg_db_receivers_objects', ['msg_id', 'objectdb_id'])

        # Adding M2M table for field db_receivers_channels on 'Msg'
        db.create_table('comms_msg_db_receivers_channels', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('msg', models.ForeignKey(orm['comms.msg'], null=False)),
            ('channel', models.ForeignKey(orm['comms.channel'], null=False))
        ))
        db.create_unique('comms_msg_db_receivers_channels', ['msg_id', 'channel_id'])

        # Adding M2M table for field db_hide_from_players on 'Msg'
        db.create_table('comms_msg_db_hide_from_players', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('msg', models.ForeignKey(orm['comms.msg'], null=False)),
            ('playerdb', models.ForeignKey(orm['players.playerdb'], null=False))
        ))
        db.create_unique('comms_msg_db_hide_from_players', ['msg_id', 'playerdb_id'])

        # Adding M2M table for field db_hide_from_objects on 'Msg'
        db.create_table('comms_msg_db_hide_from_objects', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('msg', models.ForeignKey(orm['comms.msg'], null=False)),
            ('objectdb', models.ForeignKey(orm['objects.objectdb'], null=False))
        ))
        db.create_unique('comms_msg_db_hide_from_objects', ['msg_id', 'objectdb_id'])

        # Adding M2M table for field db_hide_from_channles on 'Msg'
        db.create_table('comms_msg_db_hide_from_channles', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('msg', models.ForeignKey(orm['comms.msg'], null=False)),
            ('channel', models.ForeignKey(orm['comms.channel'], null=False))
        ))
        db.create_unique('comms_msg_db_hide_from_channles', ['msg_id', 'channel_id'])

        # Adding index on 'Msg', fields ['db_date_sent']
        db.create_index('comms_msg', ['db_date_sent'])

        # Adding index on 'Msg', fields ['db_sender_external']
        db.create_index('comms_msg', ['db_sender_external'])

        # moving data to new fields

        if not db.dry_run:
            if orm["comms.Msg"].objects.count():
                print "deleting old Msgs before migrating ..."
            for msg in orm["comms.Msg"].objects.all():
                msg.delete()

    def backwards(self, orm):
        # Removing index on 'Msg', fields ['db_sender_external']
        db.delete_index('comms_msg', ['db_sender_external'])

        # Removing index on 'Msg', fields ['db_date_sent']
        db.delete_index('comms_msg', ['db_date_sent'])

        # Adding field 'Msg.db_hide_from_channels'
        db.add_column('comms_msg', 'db_hide_from_channels',
                      self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True),
                      keep_default=False)

        # Adding field 'Msg.db_hide_from_receivers'
        db.add_column('comms_msg', 'db_hide_from_receivers',
                      self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True),
                      keep_default=False)

        # Adding field 'Msg.db_receivers'
        db.add_column('comms_msg', 'db_receivers',
                      self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True),
                      keep_default=False)

        # Adding field 'Msg.db_channels'
        db.add_column('comms_msg', 'db_channels',
                      self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True),
                      keep_default=False)

        # Adding field 'Msg.db_hide_from_sender'
        db.add_column('comms_msg', 'db_hide_from_sender',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

        # Adding field 'Msg.db_sender'
        db.add_column('comms_msg', 'db_sender',
                      self.gf('django.db.models.fields.related.ForeignKey')(related_name='sender_set', null=True, to=orm['players.PlayerDB']),
                      keep_default=False)

        # Deleting field 'Msg.db_title'
        db.delete_column('comms_msg', 'db_title')

        # Removing M2M table for field db_sender_players on 'Msg'
        db.delete_table('comms_msg_db_sender_players')

        # Removing M2M table for field db_sender_objects on 'Msg'
        db.delete_table('comms_msg_db_sender_objects')

        # Removing M2M table for field db_receivers_players on 'Msg'
        db.delete_table('comms_msg_db_receivers_players')

        # Removing M2M table for field db_receivers_objects on 'Msg'
        db.delete_table('comms_msg_db_receivers_objects')

        # Removing M2M table for field db_receivers_channels on 'Msg'
        db.delete_table('comms_msg_db_receivers_channels')

        # Removing M2M table for field db_hide_from_players on 'Msg'
        db.delete_table('comms_msg_db_hide_from_players')

        # Removing M2M table for field db_hide_from_objects on 'Msg'
        db.delete_table('comms_msg_db_hide_from_objects')

        # Removing M2M table for field db_hide_from_channles on 'Msg'
        db.delete_table('comms_msg_db_hide_from_channles')


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
        'comms.channel': {
            'Meta': {'object_name': 'Channel'},
            'db_aliases': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'db_desc': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'db_keep_log': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'db_key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'db_lock_storage': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'comms.externalchannelconnection': {
            'Meta': {'object_name': 'ExternalChannelConnection'},
            'db_channel': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['comms.Channel']"}),
            'db_external_config': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'db_external_key': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'db_external_send_code': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'db_is_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'comms.msg': {
            'Meta': {'object_name': 'Msg'},
            'db_date_sent': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'db_hide_from_channles': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'hide_from_channels_set'", 'null': 'True', 'to': "orm['comms.Channel']"}),
            'db_hide_from_objects': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'hide_from_objects_set'", 'null': 'True', 'to': "orm['objects.ObjectDB']"}),
            'db_hide_from_players': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'hide_from_players_set'", 'null': 'True', 'to': "orm['players.PlayerDB']"}),
            'db_lock_storage': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'}),
            'db_message': ('django.db.models.fields.TextField', [], {}),
            'db_receivers_channels': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'channel_set'", 'null': 'True', 'to': "orm['comms.Channel']"}),
            'db_receivers_objects': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'receiver_object_set'", 'null': 'True', 'to': "orm['objects.ObjectDB']"}),
            'db_receivers_players': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'receiver_player_set'", 'null': 'True', 'to': "orm['players.PlayerDB']"}),
            'db_sender_external': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'db_index': 'True'}),
            'db_sender_objects': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'sender_object_set'", 'null': 'True', 'db_index': 'True', 'to': "orm['objects.ObjectDB']"}),
            'db_sender_players': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'sender_player_set'", 'null': 'True', 'db_index': 'True', 'to': "orm['players.PlayerDB']"}),
            'db_title': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '512', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'comms.playerchannelconnection': {
            'Meta': {'object_name': 'PlayerChannelConnection'},
            'db_channel': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['comms.Channel']"}),
            'db_player': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['players.PlayerDB']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
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

    complete_apps = ['comms']
