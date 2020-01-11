# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [("accounts", "0002_move_defaults")]

    operations = [
        migrations.CreateModel(
            name="DefaultAccount", fields=[], options={"proxy": True}, bases=("accounts.accountdb",)
        ),
        migrations.CreateModel(
            name="DefaultGuest",
            fields=[],
            options={"proxy": True},
            bases=("accounts.defaultaccount",),
        ),
        migrations.AlterModelOptions(name="accountdb", options={"verbose_name": "Account"}),
    ]
