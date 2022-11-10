# -*- coding: utf-8 -*-


from django.db import migrations, models


def remove_manage_scripts(apps, schema_editor):
    ScriptDB = apps.get_model("scripts", "ScriptDB")
    for script in ScriptDB.objects.filter(
        db_typeclass_path__in=(
            "src.scripts.scripts.CheckSessions",
            "src.scripts.scripts.ValidateScripts",
            "src.scripts.scripts.ValidateChannelHandler",
            "src.scripts.scripts.ValidateIdmapperCache",
            "src.utils.gametime.GameTime",
        )
    ):
        script.delete()


class Migration(migrations.Migration):

    dependencies = [("scripts", "0005_auto_20150306_1441")]

    operations = [migrations.RunPython(remove_manage_scripts)]
