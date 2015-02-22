# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

def convert_defaults(apps, schema_editor):
    ObjectDB = apps.get_model("objects", "ObjectDB")
    for obj in ObjectDB.objects.filter(db_typeclass_path="src.objects.objects.Object"):
        obj.db_typeclass_path = "typeclasses.objects.Object"
        obj.save()

class Migration(migrations.Migration):

    dependencies = [
        ('objects', '0003_defaultcharacter_defaultexit_defaultobject_defaultroom'),
    ]

    operations = [
            migrations.RunPython(convert_defaults),
    ]
