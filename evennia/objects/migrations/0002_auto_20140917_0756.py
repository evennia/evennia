# -*- coding: utf-8 -*-


from django.db import models, migrations
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ("objects", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("typeclasses", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="objectdb",
            name="db_account",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.SET_NULL,
                verbose_name="account",
                to=settings.AUTH_USER_MODEL,
                help_text="an Account connected to this object, if any.",
                null=True,
            ),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name="objectdb",
            name="db_tags",
            field=models.ManyToManyField(
                help_text="tags on this object. Tags are simple string markers to identify, group and alias objects.",
                to="typeclasses.Tag",
                null=True,
            ),
            preserve_default=True,
        ),
    ]
