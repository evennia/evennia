# -*- coding: utf-8 -*-


from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("objects", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("typeclasses", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ScriptDB",
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
                ("db_desc", models.CharField(max_length=255, verbose_name="desc", blank=True)),
                (
                    "db_interval",
                    models.IntegerField(
                        default=-1,
                        help_text="how often to repeat script, in seconds. -1 means off.",
                        verbose_name="interval",
                    ),
                ),
                (
                    "db_start_delay",
                    models.BooleanField(
                        default=False,
                        help_text="pause interval seconds before starting.",
                        verbose_name="start delay",
                    ),
                ),
                (
                    "db_repeats",
                    models.IntegerField(
                        default=0, help_text="0 means off.", verbose_name="number of repeats"
                    ),
                ),
                (
                    "db_persistent",
                    models.BooleanField(default=False, verbose_name="survive server reboot"),
                ),
                ("db_is_active", models.BooleanField(default=False, verbose_name="script active")),
                (
                    "db_attributes",
                    models.ManyToManyField(
                        help_text="attributes on this object. An attribute can hold any pickle-able python object (see docs for special cases).",
                        to="typeclasses.Attribute",
                        null=True,
                    ),
                ),
                (
                    "db_obj",
                    models.ForeignKey(
                        blank=True,
                        to="objects.ObjectDB",
                        on_delete=models.CASCADE,
                        help_text="the object to store this script on, if not a global script.",
                        null=True,
                        verbose_name="scripted object",
                    ),
                ),
                (
                    "db_account",
                    models.ForeignKey(
                        blank=True,
                        to=settings.AUTH_USER_MODEL,
                        on_delete=models.CASCADE,
                        help_text="the account to store this script on (should not be set if obj is set)",
                        null=True,
                        verbose_name="scripted account",
                    ),
                ),
                (
                    "db_tags",
                    models.ManyToManyField(
                        help_text="tags on this object. Tags are simple string markers to identify, group and alias objects.",
                        to="typeclasses.Tag",
                        null=True,
                    ),
                ),
            ],
            options={"verbose_name": "Script"},
            bases=(models.Model,),
        )
    ]
