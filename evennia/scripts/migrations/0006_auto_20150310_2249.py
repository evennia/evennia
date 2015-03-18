# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

def remove_manage_scripts(apps, schema_editor):
    ScriptDB = apps.get_model("scripts", "ScriptDB")
    for script in ScriptDB.objects.filter(db_typeclass_path__in=(u'src.scripts.scripts.CheckSessions',
                                                                 u'src.scripts.scripts.ValidateScripts',
                                                                 u'src.scripts.scripts.ValidateChannelHandler',
                                                                 u'src.scripts.scripts.ValidateIdmapperCache',
                                                                 u'src.utils.gametime.GameTime')):
        script.delete()

class Migration(migrations.Migration):

    dependencies = [
        ('scripts', '0005_auto_20150306_1441'),
    ]

    operations = [
        migrations.RunPython(remove_manage_scripts),
    ]
