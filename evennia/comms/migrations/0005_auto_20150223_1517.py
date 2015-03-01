# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

def convert_channelnames(apps, schema_editor):
    ChannelDB = apps.get_model("comms", "ChannelDB")
    for chan in ChannelDB.objects.filter(db_key="MUDinfo"):
        # remove the old MUDinfo default channel
        chan.delete()
    for chan in ChannelDB.objects.filter(db_key__iexact="MUDconnections"):
        # change the old mudconnections to MudInfo instead
        chan.db_key = "MudInfo"
        chan.save()

class Migration(migrations.Migration):

    dependencies = [
        ('comms', '0004_auto_20150118_1631'),
    ]

    operations = [
            migrations.RunPython(convert_channelnames),
    ]
