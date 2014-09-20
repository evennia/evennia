# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('typeclasses', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='HelpEntry',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('db_key', models.CharField(help_text=b'key to search for', unique=True, max_length=255, verbose_name=b'help key')),
                ('db_help_category', models.CharField(default=b'General', help_text=b'organizes help entries in lists', max_length=255, verbose_name=b'help category')),
                ('db_entrytext', models.TextField(help_text=b'the main body of help text', verbose_name=b'help entry', blank=True)),
                ('db_lock_storage', models.TextField(help_text=b'normally view:all().', verbose_name=b'locks', blank=True)),
                ('db_staff_only', models.BooleanField(default=False)),
                ('db_tags', models.ManyToManyField(help_text=b'tags on this object. Tags are simple string markers to identify, group and alias objects.', to='typeclasses.Tag', null=True)),
            ],
            options={
                'verbose_name': 'Help Entry',
                'verbose_name_plural': 'Help Entries',
            },
            bases=(models.Model,),
        ),
    ]
