# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [("typeclasses", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="HelpEntry",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID", serialize=False, auto_created=True, primary_key=True
                    ),
                ),
                (
                    "db_key",
                    models.CharField(
                        help_text="key to search for",
                        unique=True,
                        max_length=255,
                        verbose_name="help key",
                    ),
                ),
                (
                    "db_help_category",
                    models.CharField(
                        default="General",
                        help_text="organizes help entries in lists",
                        max_length=255,
                        verbose_name="help category",
                    ),
                ),
                (
                    "db_entrytext",
                    models.TextField(
                        help_text="the main body of help text",
                        verbose_name="help entry",
                        blank=True,
                    ),
                ),
                (
                    "db_lock_storage",
                    models.TextField(
                        help_text="normally view:all().", verbose_name="locks", blank=True
                    ),
                ),
                ("db_staff_only", models.BooleanField(default=False)),
                (
                    "db_tags",
                    models.ManyToManyField(
                        help_text="tags on this object. Tags are simple string markers to identify, group and alias objects.",
                        to="typeclasses.Tag",
                        null=True,
                    ),
                ),
            ],
            options={"verbose_name": "Help Entry", "verbose_name_plural": "Help Entries"},
            bases=(models.Model,),
        )
    ]
