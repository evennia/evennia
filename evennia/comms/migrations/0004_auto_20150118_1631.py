# -*- coding: utf-8 -*-


from django.db import migrations, models


def convert_defaults(apps, schema_editor):
    ChannelDB = apps.get_model("comms", "ChannelDB")
    for channel in ChannelDB.objects.filter(db_typeclass_path="src.comms.comms.Channel"):
        channel.db_typeclass_path = "typeclasses.channels.Channel"
        channel.save()


class Migration(migrations.Migration):

    dependencies = [("comms", "0003_auto_20140917_0756")]

    operations = [migrations.RunPython(convert_defaults)]
