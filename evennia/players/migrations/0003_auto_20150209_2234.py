# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('players', '0002_move_defaults'),
    ]

    operations = [
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
        migrations.AlterModelOptions(
            name='playerdb',
            options={'verbose_name': 'Player'},
        ),
    ]
