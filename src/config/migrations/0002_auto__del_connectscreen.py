# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from src.utils import utils

class Migration(SchemaMigration):

    def forwards(self, orm):        
        # Deleting model 'ConnectScreen'
        db.delete_table('config_connectscreen')

    def backwards(self, orm):
        
        # Adding model 'ConnectScreen'
        db.create_table('config_connectscreen', (
            ('db_key', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('db_is_active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('db_text', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('config', ['ConnectScreen'])


    models = {
        'config.configvalue': {
            'Meta': {'object_name': 'ConfigValue'},
            'db_key': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'db_value': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['config']
