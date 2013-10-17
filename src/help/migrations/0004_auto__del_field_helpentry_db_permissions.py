# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'HelpEntry.db_permissions'
        db.delete_column(u'help_helpentry', 'db_permissions')

        # Adding M2M table for field db_tags on 'HelpEntry'
        m2m_table_name = db.shorten_name(u'help_helpentry_db_tags')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('helpentry', models.ForeignKey(orm[u'help.helpentry'], null=False)),
            ('tag', models.ForeignKey(orm[u'typeclasses.tag'], null=False))
        ))
        db.create_unique(m2m_table_name, ['helpentry_id', 'tag_id'])


    def backwards(self, orm):
        # Adding field 'HelpEntry.db_permissions'
        db.add_column(u'help_helpentry', 'db_permissions',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=255, blank=True),
                      keep_default=False)

        # Removing M2M table for field db_tags on 'HelpEntry'
        db.delete_table(db.shorten_name(u'help_helpentry_db_tags'))


    models = {
        u'help.helpentry': {
            'Meta': {'object_name': 'HelpEntry'},
            'db_entrytext': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'db_help_category': ('django.db.models.fields.CharField', [], {'default': "'General'", 'max_length': '255'}),
            'db_key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'db_lock_storage': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'db_staff_only': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'db_tags': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['typeclasses.Tag']", 'null': 'True', 'symmetrical': 'False'}),
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

    complete_apps = ['help']