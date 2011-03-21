# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'ConfigValue'
        db.create_table('config_configvalue', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('db_key', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('db_value', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('config', ['ConfigValue'])

        # Adding model 'ConnectScreen'
        db.create_table('config_connectscreen', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('db_key', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('db_text', self.gf('django.db.models.fields.TextField')()),
            ('db_is_active', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal('config', ['ConnectScreen'])


    def backwards(self, orm):
        
        # Deleting model 'ConfigValue'
        db.delete_table('config_configvalue')

        # Deleting model 'ConnectScreen'
        db.delete_table('config_connectscreen')


    models = {
        'config.configvalue': {
            'Meta': {'object_name': 'ConfigValue'},
            'db_key': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'db_value': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'config.connectscreen': {
            'Meta': {'object_name': 'ConnectScreen'},
            'db_is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'db_key': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'db_text': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['config']
