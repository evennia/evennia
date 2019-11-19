# -*- coding: utf-8 -*-


from django.db import models, migrations


def convert_defaults(apps, schema_editor):
    ScriptDB = apps.get_model("scripts", "ScriptDB")
    for script in ScriptDB.objects.filter(db_typeclass_path="src.scripts.scripts.Script"):
        script.db_typeclass_path = "typeclasses.scripts.Script"
        script.save()
    for script in ScriptDB.objects.filter(db_typeclass_path="src.utils.gametime.GameTime"):
        script.db_typeclass_path = "evennia.utils.gametime.GameTime"
        script.save()


class Migration(migrations.Migration):

    dependencies = [("scripts", "0001_initial")]

    operations = [migrations.RunPython(convert_defaults)]
