# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

def convert_defaults(apps, schema_editor):
    PlayerDB = apps.get_model("players", "PlayerDB")
    for player in PlayerDB.objects.filter(db_typeclass_path="src.players.player.Player"):
        player.db_typeclass_path = "typeclasses.players.Player"
        player.save()

class Migration(migrations.Migration):

    dependencies = [
        ('players', '0001_initial'),
    ]

    operations = [
            migrations.RunPython(convert_defaults),
    ]
