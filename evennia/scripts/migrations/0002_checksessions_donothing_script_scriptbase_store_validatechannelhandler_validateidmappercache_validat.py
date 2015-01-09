# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('scripts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScriptBase',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('scripts.scriptdb',),
        ),
        migrations.CreateModel(
            name='Script',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('scripts.scriptbase',),
        ),
        migrations.CreateModel(
            name='CheckSessions',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('scripts.script',),
        ),
        migrations.CreateModel(
            name='DoNothing',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('scripts.script',),
        ),
        migrations.CreateModel(
            name='Store',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('scripts.script',),
        ),
        migrations.CreateModel(
            name='ValidateChannelHandler',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('scripts.script',),
        ),
        migrations.CreateModel(
            name='ValidateIdmapperCache',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('scripts.script',),
        ),
        migrations.CreateModel(
            name='ValidateScripts',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('scripts.script',),
        ),
    ]
