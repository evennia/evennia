# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('comms', '0003_auto_20140917_0756'),
    ]

    operations = [
        migrations.CreateModel(
            name='DefaultChannel',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('comms.channeldb',),
        ),
    ]
