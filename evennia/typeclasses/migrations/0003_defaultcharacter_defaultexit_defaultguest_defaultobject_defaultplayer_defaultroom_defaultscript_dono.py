# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import evennia.players.manager


class Migration(migrations.Migration):

    dependencies = [
        ('objects', '0005_auto_20150403_2339'),
        ('scripts', '0007_auto_20150403_2339'),
        ('players', '0004_auto_20150403_2339'),
        ('typeclasses', '0002_auto_20150109_0913'),
    ]

    operations = [
        migrations.CreateModel(
            name='DefaultObject',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('objects.objectdb',),
        ),
        migrations.CreateModel(
            name='DefaultPlayer',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('players.playerdb',),
            managers=[
                (b'objects', evennia.players.manager.PlayerManager()),
            ],
        ),
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
            name='DefaultCharacter',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('typeclasses.defaultobject',),
        ),
        migrations.CreateModel(
            name='DefaultExit',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('typeclasses.defaultobject',),
        ),
        migrations.CreateModel(
            name='DefaultGuest',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('typeclasses.defaultplayer',),
            managers=[
                (b'objects', evennia.players.manager.PlayerManager()),
            ],
        ),
        migrations.CreateModel(
            name='DefaultRoom',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('typeclasses.defaultobject',),
        ),
        migrations.CreateModel(
            name='DefaultScript',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('typeclasses.scriptbase',),
        ),
        migrations.CreateModel(
            name='DoNothing',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('typeclasses.defaultscript',),
        ),
        migrations.CreateModel(
            name='Store',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('typeclasses.defaultscript',),
        ),
    ]
