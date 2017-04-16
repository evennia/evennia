# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='personal_objects',
            fields=[
                ('key', models.CharField(max_length=255, serialize=False, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('alias', models.CharField(max_length=255, blank=True)),
                ('typeclass', models.CharField(max_length=255)),
                ('desc', models.TextField(blank=True)),
                ('location', models.CharField(max_length=255, blank=True)),
                ('home', models.CharField(max_length=255, blank=True)),
                ('lock', models.CharField(max_length=255, blank=True)),
                ('attributes', models.TextField(blank=True)),
                ('tutorial_info', models.TextField(blank=True)),
                ('destination', models.CharField(max_length=255, blank=True)),
            ],
            options={
                'verbose_name': 'Personal Object List',
                'verbose_name_plural': 'Personal Object List',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='world_details',
            fields=[
                ('key', models.CharField(max_length=255, serialize=False, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('desc', models.TextField(blank=True)),
                ('location', models.CharField(max_length=255, blank=True)),
            ],
            options={
                'verbose_name': 'World Detail List',
                'verbose_name_plural': 'World Detail List',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='world_exits',
            fields=[
                ('key', models.CharField(max_length=255, serialize=False, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('alias', models.CharField(max_length=255, blank=True)),
                ('typeclass', models.CharField(max_length=255)),
                ('desc', models.TextField(blank=True)),
                ('location', models.CharField(max_length=255, blank=True)),
                ('home', models.CharField(max_length=255, blank=True)),
                ('lock', models.CharField(max_length=255, blank=True)),
                ('attributes', models.TextField(blank=True)),
                ('tutorial_info', models.TextField(blank=True)),
                ('destination', models.CharField(max_length=255, blank=True)),
            ],
            options={
                'verbose_name': 'World Exit List',
                'verbose_name_plural': 'World Exit List',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='world_objects',
            fields=[
                ('key', models.CharField(max_length=255, serialize=False, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('alias', models.CharField(max_length=255, blank=True)),
                ('typeclass', models.CharField(max_length=255)),
                ('desc', models.TextField(blank=True)),
                ('location', models.CharField(max_length=255, blank=True)),
                ('home', models.CharField(max_length=255, blank=True)),
                ('lock', models.CharField(max_length=255, blank=True)),
                ('attributes', models.TextField(blank=True)),
                ('tutorial_info', models.TextField(blank=True)),
                ('destination', models.CharField(max_length=255, blank=True)),
            ],
            options={
                'verbose_name': 'World Object List',
                'verbose_name_plural': 'World Object List',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='world_rooms',
            fields=[
                ('key', models.CharField(max_length=255, serialize=False, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('alias', models.CharField(max_length=255, blank=True)),
                ('typeclass', models.CharField(max_length=255)),
                ('desc', models.TextField(blank=True)),
                ('location', models.CharField(max_length=255, blank=True)),
                ('home', models.CharField(max_length=255, blank=True)),
                ('lock', models.CharField(max_length=255, blank=True)),
                ('attributes', models.TextField(blank=True)),
                ('tutorial_info', models.TextField(blank=True)),
                ('destination', models.CharField(max_length=255, blank=True)),
            ],
            options={
                'verbose_name': 'World Room List',
                'verbose_name_plural': 'World Room List',
            },
            bases=(models.Model,),
        ),
    ]
