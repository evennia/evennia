# -*- coding: utf-8 -*-


from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ("objects", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("typeclasses", "0001_initial"),
        ("comms", "0002_msg_db_hide_from_objects"),
    ]

    operations = [
        migrations.AddField(
            model_name="msg",
            name="db_hide_from_accounts",
            field=models.ManyToManyField(
                related_name="hide_from_accounts_set", null=True, to=settings.AUTH_USER_MODEL
            ),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name="msg",
            name="db_receivers_channels",
            field=models.ManyToManyField(
                help_text="channel recievers",
                related_name="channel_set",
                null=True,
                to="comms.ChannelDB",
            ),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name="msg",
            name="db_receivers_objects",
            field=models.ManyToManyField(
                help_text="object receivers",
                related_name="receiver_object_set",
                null=True,
                to="objects.ObjectDB",
            ),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name="msg",
            name="db_receivers_accounts",
            field=models.ManyToManyField(
                help_text="account receivers",
                related_name="receiver_account_set",
                null=True,
                to=settings.AUTH_USER_MODEL,
            ),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name="msg",
            name="db_sender_objects",
            field=models.ManyToManyField(
                related_name="sender_object_set",
                null=True,
                verbose_name="sender(object)",
                to="objects.ObjectDB",
                db_index=True,
            ),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name="msg",
            name="db_sender_accounts",
            field=models.ManyToManyField(
                related_name="sender_account_set",
                null=True,
                verbose_name="sender(account)",
                to=settings.AUTH_USER_MODEL,
                db_index=True,
            ),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name="channeldb",
            name="db_attributes",
            field=models.ManyToManyField(
                help_text="attributes on this object. An attribute can hold any pickle-able python object (see docs for special cases).",
                to="typeclasses.Attribute",
                null=True,
            ),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name="channeldb",
            name="db_subscriptions",
            field=models.ManyToManyField(
                related_name="subscription_set",
                null=True,
                verbose_name="subscriptions",
                to=settings.AUTH_USER_MODEL,
                db_index=True,
            ),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name="channeldb",
            name="db_tags",
            field=models.ManyToManyField(
                help_text="tags on this object. Tags are simple string markers to identify, group and alias objects.",
                to="typeclasses.Tag",
                null=True,
            ),
            preserve_default=True,
        ),
    ]
