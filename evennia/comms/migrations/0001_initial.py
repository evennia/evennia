# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ChannelDB",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID", serialize=False, auto_created=True, primary_key=True
                    ),
                ),
                ("db_key", models.CharField(max_length=255, verbose_name="key", db_index=True)),
                (
                    "db_typeclass_path",
                    models.CharField(
                        help_text="this defines what 'type' of entity this is. This variable holds a Python path to a module with a valid Evennia Typeclass.",
                        max_length=255,
                        null=True,
                        verbose_name="typeclass",
                    ),
                ),
                (
                    "db_date_created",
                    models.DateTimeField(auto_now_add=True, verbose_name="creation date"),
                ),
                (
                    "db_lock_storage",
                    models.TextField(
                        help_text="locks limit access to an entity. A lock is defined as a 'lock string' on the form 'type:lockfunctions', defining what functionality is locked and how to determine access. Not defining a lock means no access is granted.",
                        verbose_name="locks",
                        blank=True,
                    ),
                ),
            ],
            options={"verbose_name": "Channel", "verbose_name_plural": "Channels"},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="Msg",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID", serialize=False, auto_created=True, primary_key=True
                    ),
                ),
                (
                    "db_sender_external",
                    models.CharField(
                        help_text="identifier for external sender, for example a sender over an IRC connection (i.e. someone who doesn't have an exixtence in-game).",
                        max_length=255,
                        null=True,
                        verbose_name="external sender",
                        db_index=True,
                    ),
                ),
                ("db_header", models.TextField(null=True, verbose_name="header", blank=True)),
                ("db_message", models.TextField(verbose_name="messsage")),
                (
                    "db_date_sent",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="date sent", db_index=True
                    ),
                ),
                (
                    "db_lock_storage",
                    models.TextField(
                        help_text="access locks on this message.", verbose_name="locks", blank=True
                    ),
                ),
                (
                    "db_hide_from_channels",
                    models.ManyToManyField(
                        related_name="hide_from_channels_set", null=True, to="comms.ChannelDB"
                    ),
                ),
            ],
            options={"verbose_name": "Message"},
            bases=(models.Model,),
        ),
    ]
