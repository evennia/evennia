# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('typeclasses', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ObjectDB',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('db_key', models.CharField(max_length=255, verbose_name=b'key', db_index=True)),
                ('db_typeclass_path', models.CharField(help_text=b"this defines what 'type' of entity this is. This variable holds a Python path to a module with a valid Evennia Typeclass.", max_length=255, null=True, verbose_name=b'typeclass')),
                ('db_date_created', models.DateTimeField(auto_now_add=True, verbose_name=b'creation date')),
                ('db_lock_storage', models.TextField(help_text=b"locks limit access to an entity. A lock is defined as a 'lock string' on the form 'type:lockfunctions', defining what functionality is locked and how to determine access. Not defining a lock means no access is granted.", verbose_name=b'locks', blank=True)),
                ('db_sessid', models.CommaSeparatedIntegerField(help_text=b'csv list of session ids of connected Player, if any.', max_length=32, null=True, verbose_name=b'session id')),
                ('db_cmdset_storage', models.CharField(help_text=b'optional python path to a cmdset class.', max_length=255, null=True, verbose_name=b'cmdset', blank=True)),
                ('db_attributes', models.ManyToManyField(help_text=b'attributes on this object. An attribute can hold any pickle-able python object (see docs for special cases).', to='typeclasses.Attribute', null=True)),
                ('db_destination', models.ForeignKey(related_name=b'destinations_set', on_delete=django.db.models.deletion.SET_NULL, blank=True, to='objects.ObjectDB', help_text=b'a destination, used only by exit objects.', null=True, verbose_name=b'destination')),
                ('db_home', models.ForeignKey(related_name=b'homes_set', on_delete=django.db.models.deletion.SET_NULL, verbose_name=b'home location', blank=True, to='objects.ObjectDB', null=True)),
                ('db_location', models.ForeignKey(related_name=b'locations_set', on_delete=django.db.models.deletion.SET_NULL, verbose_name=b'game location', blank=True, to='objects.ObjectDB', null=True)),
            ],
            options={
                'verbose_name': 'Object',
                'verbose_name_plural': 'Objects',
            },
            bases=(models.Model,),
        ),
    ]
