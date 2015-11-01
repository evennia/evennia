# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('typeclasses', '0003_defaultcharacter_defaultexit_defaultguest_defaultobject_defaultplayer_defaultroom_defaultscript_dono'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attribute',
            name='db_model',
            field=models.CharField(max_length=32, blank=True, help_text=b"Which model of object this attribute is attached to (A natural key like 'objects.objectdb'). You should not change this value unless you know what you are doing.", null=True, verbose_name=b'model', db_index=True),
        ),
    ]
