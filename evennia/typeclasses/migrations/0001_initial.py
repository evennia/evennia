# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import evennia.utils.picklefield


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Attribute',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('db_key', models.CharField(max_length=255, verbose_name=b'key', db_index=True)),
                ('db_value', evennia.utils.picklefield.PickledObjectField(help_text=b'The data returned when the attribute is accessed. Must be written as a Python literal if editing through the admin interface. Attribute values which are not Python literals cannot be edited through the admin interface.', null=True, verbose_name=b'value')),
                ('db_strvalue', models.TextField(help_text=b'String-specific storage for quick look-up', null=True, verbose_name=b'strvalue', blank=True)),
                ('db_category', models.CharField(max_length=128, blank=True, help_text=b'Optional categorization of attribute.', null=True, verbose_name=b'category', db_index=True)),
                ('db_lock_storage', models.TextField(help_text=b'Lockstrings for this object are stored here.', verbose_name=b'locks', blank=True)),
                ('db_model', models.CharField(max_length=32, blank=True, help_text=b'Which model of object this attribute is attached to (A natural key like objects.dbobject). You should not change this value unless you know what you are doing.', null=True, verbose_name=b'model', db_index=True)),
                ('db_attrtype', models.CharField(max_length=16, blank=True, help_text=b'Subclass of Attribute (None or nick)', null=True, verbose_name=b'attrtype', db_index=True)),
                ('db_date_created', models.DateTimeField(auto_now_add=True, verbose_name=b'date_created')),
            ],
            options={
                'verbose_name': 'Evennia Attribute',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('db_key', models.CharField(help_text=b'tag identifier', max_length=255, null=True, verbose_name=b'key', db_index=True)),
                ('db_category', models.CharField(help_text=b'tag category', max_length=64, null=True, verbose_name=b'category', db_index=True)),
                ('db_data', models.TextField(help_text=b'optional data field with extra information. This is not searched for.', null=True, verbose_name=b'data', blank=True)),
                ('db_model', models.CharField(help_text=b'database model to Tag', max_length=32, null=True, verbose_name=b'model', db_index=True)),
                ('db_tagtype', models.CharField(help_text=b'overall type of Tag', max_length=16, null=True, verbose_name=b'tagtype', db_index=True)),
            ],
            options={
                'verbose_name': 'Tag',
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='tag',
            unique_together=set([('db_key', 'db_category', 'db_tagtype')]),
        ),
        migrations.AlterIndexTogether(
            name='tag',
            index_together=set([('db_key', 'db_category', 'db_tagtype')]),
        ),
    ]
    # if we are using Oracle, we need to remove the AlterIndexTogether operation
    # since Oracle seems to create its own index already at AlterUniqueTogether, meaning
    # there is a conflict (see issue #732).
    if settings.DATABASES['default']['ENGINE'] == "django.db.backends.oracle":
        del operations[3]
