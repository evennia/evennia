# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('scripts', '0002_checksessions_donothing_script_scriptbase_store_validatechannelhandler_validateidmappercache_validat'),
        ('players', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='BotStarter',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('scripts.script',),
        ),
        migrations.CreateModel(
            name='DefaultPlayer',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('players.playerdb',),
        ),
        migrations.CreateModel(
            name='DefaultGuest',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('players.defaultplayer',),
        ),
        migrations.CreateModel(
            name='Bot',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('players.defaultplayer',),
        ),
        migrations.CreateModel(
            name='IMC2Bot',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('players.bot',),
        ),
        migrations.CreateModel(
            name='IRCBot',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('players.bot',),
        ),
        migrations.CreateModel(
            name='RSSBot',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('players.bot',),
        ),
        migrations.AlterModelOptions(
            name='playerdb',
            options={'verbose_name': 'Player'},
        ),
    ]
