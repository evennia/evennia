# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ("typeclasses", "0001_initial"),
        ("auth", "0007_alter_validators_add_error_messages"),
    ]

    operations = [
        migrations.AlterField(
            model_name="attribute",
            name="db_model",
            field=models.CharField(
                max_length=32,
                blank=True,
                help_text="Which model of object this attribute is attached to (A natural key like 'objects.dbobject'). You should not change this value unless you know what you are doing.",
                null=True,
                verbose_name="model",
                db_index=True,
            ),
        )
    ]
