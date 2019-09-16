# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("typeclasses", "0004_auto_20151101_1759"),
        ("comms", "0006_channeldb_db_object_subscriptions"),
    ]

    operations = [
        migrations.AddField(
            model_name="msg",
            name="db_tags",
            field=models.ManyToManyField(
                help_text="tags on this message. Tags are simple string markers to identify, group and alias messages.",
                to="typeclasses.Tag",
                null=True,
            ),
        )
    ]
