# -*- coding: utf-8 -*-


from django.db import models, migrations


def remove_manage_scripts(apps, schema_editor):
    ScriptDB = apps.get_model("scripts", "ScriptDB")
    for script in ScriptDB.objects.filter(
        db_typeclass_path__in=(
            "evennia.scripts.scripts.CheckSessions",
            "evennia.scripts.scripts.ValidateScripts",
            "evennia.scripts.scripts.ValidateChannelHandler",
            "evennia.scripts.scripts.ValidateIdmapperCache",
            "evennia.utils.gametime.GameTime",
        )
    ):
        script.delete()


class Migration(migrations.Migration):

    dependencies = [
        (
            "scripts",
            "0003_checksessions_defaultscript_donothing_scriptbase_store_validatechannelhandler_validateidmappercache_",
        )
    ]

    operations = [migrations.RunPython(remove_manage_scripts)]
