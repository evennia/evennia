# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [("scripts", "0006_auto_20150310_2249")]

    operations = [
        migrations.DeleteModel(name="DefaultScript"),
        migrations.DeleteModel(name="DoNothing"),
        migrations.DeleteModel(name="ScriptBase"),
        migrations.DeleteModel(name="Store"),
    ]
