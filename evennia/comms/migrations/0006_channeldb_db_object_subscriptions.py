# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [("objects", "0004_auto_20150118_1622"), ("comms", "0005_auto_20150223_1517")]

    operations = [
        migrations.AddField(
            model_name="channeldb",
            name="db_object_subscriptions",
            field=models.ManyToManyField(
                related_name="object_subscription_set",
                null=True,
                verbose_name="subscriptions",
                to="objects.ObjectDB",
                db_index=True,
            ),
            preserve_default=True,
        )
    ]
