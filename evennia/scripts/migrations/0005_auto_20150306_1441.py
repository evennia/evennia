# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [("scripts", "0004_auto_20150306_1354")]

    operations = [
        migrations.DeleteModel(name="CheckSessions"),
        migrations.DeleteModel(name="ValidateChannelHandler"),
        migrations.DeleteModel(name="ValidateIdmapperCache"),
        migrations.DeleteModel(name="ValidateScripts"),
    ]
