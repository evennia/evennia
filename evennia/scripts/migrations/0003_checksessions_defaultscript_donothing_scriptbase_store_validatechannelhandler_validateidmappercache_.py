# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [("scripts", "0002_auto_20150118_1625")]

    operations = [
        migrations.CreateModel(
            name="ScriptBase", fields=[], options={"proxy": True}, bases=("scripts.scriptdb",)
        ),
        migrations.CreateModel(
            name="DefaultScript", fields=[], options={"proxy": True}, bases=("scripts.scriptbase",)
        ),
        migrations.CreateModel(
            name="DoNothing", fields=[], options={"proxy": True}, bases=("scripts.defaultscript",)
        ),
        migrations.CreateModel(
            name="CheckSessions",
            fields=[],
            options={"proxy": True},
            bases=("scripts.defaultscript",),
        ),
        migrations.CreateModel(
            name="Store", fields=[], options={"proxy": True}, bases=("scripts.defaultscript",)
        ),
        migrations.CreateModel(
            name="ValidateChannelHandler",
            fields=[],
            options={"proxy": True},
            bases=("scripts.defaultscript",),
        ),
        migrations.CreateModel(
            name="ValidateIdmapperCache",
            fields=[],
            options={"proxy": True},
            bases=("scripts.defaultscript",),
        ),
        migrations.CreateModel(
            name="ValidateScripts",
            fields=[],
            options={"proxy": True},
            bases=("scripts.defaultscript",),
        ),
    ]
