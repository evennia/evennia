# -*- coding: utf-8 -*-


from django.db import models, migrations
from django.conf import settings
import evennia.utils.picklefield


class Migration(migrations.Migration):

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Attribute",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID", serialize=False, auto_created=True, primary_key=True
                    ),
                ),
                ("db_key", models.CharField(max_length=255, verbose_name="key", db_index=True)),
                (
                    "db_value",
                    evennia.utils.picklefield.PickledObjectField(
                        help_text="The data returned when the attribute is accessed. Must be written as a Python literal if editing through the admin interface. Attribute values which are not Python literals cannot be edited through the admin interface.",
                        null=True,
                        verbose_name="value",
                    ),
                ),
                (
                    "db_strvalue",
                    models.TextField(
                        help_text="String-specific storage for quick look-up",
                        null=True,
                        verbose_name="strvalue",
                        blank=True,
                    ),
                ),
                (
                    "db_category",
                    models.CharField(
                        max_length=128,
                        blank=True,
                        help_text="Optional categorization of attribute.",
                        null=True,
                        verbose_name="category",
                        db_index=True,
                    ),
                ),
                (
                    "db_lock_storage",
                    models.TextField(
                        help_text="Lockstrings for this object are stored here.",
                        verbose_name="locks",
                        blank=True,
                    ),
                ),
                (
                    "db_model",
                    models.CharField(
                        max_length=32,
                        blank=True,
                        help_text="Which model of object this attribute is attached to (A natural key like objects.dbobject). You should not change this value unless you know what you are doing.",
                        null=True,
                        verbose_name="model",
                        db_index=True,
                    ),
                ),
                (
                    "db_attrtype",
                    models.CharField(
                        max_length=16,
                        blank=True,
                        help_text="Subclass of Attribute (None or nick)",
                        null=True,
                        verbose_name="attrtype",
                        db_index=True,
                    ),
                ),
                (
                    "db_date_created",
                    models.DateTimeField(auto_now_add=True, verbose_name="date_created"),
                ),
            ],
            options={"verbose_name": "Evennia Attribute"},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="Tag",
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
                        help_text="tag identifier",
                        max_length=255,
                        null=True,
                        verbose_name="key",
                        db_index=True,
                    ),
                ),
                (
                    "db_category",
                    models.CharField(
                        help_text="tag category",
                        max_length=64,
                        null=True,
                        verbose_name="category",
                        db_index=True,
                    ),
                ),
                (
                    "db_data",
                    models.TextField(
                        help_text="optional data field with extra information. This is not searched for.",
                        null=True,
                        verbose_name="data",
                        blank=True,
                    ),
                ),
                (
                    "db_model",
                    models.CharField(
                        help_text="database model to Tag",
                        max_length=32,
                        null=True,
                        verbose_name="model",
                        db_index=True,
                    ),
                ),
                (
                    "db_tagtype",
                    models.CharField(
                        help_text="overall type of Tag",
                        max_length=16,
                        null=True,
                        verbose_name="tagtype",
                        db_index=True,
                    ),
                ),
            ],
            options={"verbose_name": "Tag"},
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name="tag", unique_together=set([("db_key", "db_category", "db_tagtype")])
        ),
        migrations.AlterIndexTogether(
            name="tag", index_together=set([("db_key", "db_category", "db_tagtype")])
        ),
    ]
    # if we are using Oracle, we need to remove the AlterIndexTogether operation
    # since Oracle seems to create its own index already at AlterUniqueTogether, meaning
    # there is a conflict (see issue #732).
    if settings.DATABASES["default"]["ENGINE"] == "django.db.backends.oracle":
        del operations[3]
