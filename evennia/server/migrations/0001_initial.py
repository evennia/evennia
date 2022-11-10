# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ServerConfig",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID", serialize=False, auto_created=True, primary_key=True
                    ),
                ),
                ("db_key", models.CharField(unique=True, max_length=64)),
                ("db_value", models.TextField(blank=True)),
            ],
            options={
                "verbose_name": "Server Config value",
                "verbose_name_plural": "Server Config values",
            },
            bases=(models.Model,),
        )
    ]
