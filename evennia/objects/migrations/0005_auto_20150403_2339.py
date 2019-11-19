# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [("objects", "0004_auto_20150118_1622")]

    operations = [
        migrations.DeleteModel(name="DefaultCharacter"),
        migrations.DeleteModel(name="DefaultExit"),
        migrations.DeleteModel(name="DefaultObject"),
        migrations.DeleteModel(name="DefaultRoom"),
    ]
