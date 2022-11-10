# -*- coding: utf-8 -*-


import django.core.validators
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("auth", "0001_initial"), ("typeclasses", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="AccountDB",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID", serialize=False, auto_created=True, primary_key=True
                    ),
                ),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                (
                    "last_login",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="last login"
                    ),
                ),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text="Designates that this user has all permissions without explicitly assigning them.",
                        verbose_name="superuser status",
                    ),
                ),
                (
                    "username",
                    models.CharField(
                        help_text="Required. 30 characters or fewer. Letters, digits and @/./+/-/_ only.",
                        unique=True,
                        max_length=30,
                        verbose_name="username",
                        validators=[
                            django.core.validators.RegexValidator(
                                "^[\\w.@+-]+$", "Enter a valid username.", "invalid"
                            )
                        ],
                    ),
                ),
                (
                    "first_name",
                    models.CharField(max_length=30, verbose_name="first name", blank=True),
                ),
                (
                    "last_name",
                    models.CharField(max_length=30, verbose_name="last name", blank=True),
                ),
                (
                    "email",
                    models.EmailField(max_length=75, verbose_name="email address", blank=True),
                ),
                (
                    "is_staff",
                    models.BooleanField(
                        default=False,
                        help_text="Designates whether the user can log into this admin site.",
                        verbose_name="staff status",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Designates whether this user should be treated as active. Unselect this instead of deleting accounts.",
                        verbose_name="active",
                    ),
                ),
                (
                    "date_joined",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="date joined"
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
                (
                    "db_is_connected",
                    models.BooleanField(
                        default=False,
                        help_text="If account is connected to game or not",
                        verbose_name="is_connected",
                    ),
                ),
                (
                    "db_cmdset_storage",
                    models.CharField(
                        help_text="optional python path to a cmdset class. If creating a Character, this will default to settings.CMDSET_CHARACTER.",
                        max_length=255,
                        null=True,
                        verbose_name="cmdset",
                    ),
                ),
                (
                    "db_is_bot",
                    models.BooleanField(
                        default=False,
                        help_text="Used to identify irc/rss bots",
                        verbose_name="is_bot",
                    ),
                ),
                (
                    "db_attributes",
                    models.ManyToManyField(
                        help_text="attributes on this object. An attribute can hold any pickle-able python object (see docs for special cases).",
                        to="typeclasses.Attribute",
                        null=True,
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
                (
                    "groups",
                    models.ManyToManyField(
                        related_query_name="user",
                        related_name="user_set",
                        to="auth.Group",
                        blank=True,
                        help_text="The groups this user belongs to. A user will get all permissions granted to each of his/her group.",
                        verbose_name="groups",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        related_query_name="user",
                        related_name="user_set",
                        to="auth.Permission",
                        blank=True,
                        help_text="Specific permissions for this user.",
                        verbose_name="user permissions",
                    ),
                ),
            ],
            options={"verbose_name": "Account", "verbose_name_plural": "Accounts"},
            bases=(models.Model,),
        )
    ]
