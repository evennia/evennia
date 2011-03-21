# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'HelpEntry'
        db.create_table('help_helpentry', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('db_key', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
            ('db_help_category', self.gf('django.db.models.fields.CharField')(default='General', max_length=255)),
            ('db_entrytext', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('db_permissions', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('db_lock_storage', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('db_staff_only', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('help', ['HelpEntry'])


    def backwards(self, orm):
        
        # Deleting model 'HelpEntry'
        db.delete_table('help_helpentry')


    models = {
        'help.helpentry': {
            'Meta': {'object_name': 'HelpEntry'},
            'db_entrytext': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'db_help_category': ('django.db.models.fields.CharField', [], {'default': "'General'", 'max_length': '255'}),
            'db_key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'db_lock_storage': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'db_permissions': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'db_staff_only': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['help']
