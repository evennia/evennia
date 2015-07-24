# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import evennia.players.manager
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('players', '0003_auto_20150209_2234'),
    ]

    operations = [
        migrations.DeleteModel(
            name='DefaultGuest',
        ),
        migrations.DeleteModel(
            name='DefaultPlayer',
        ),
        migrations.AlterModelManagers(
            name='playerdb',
            managers=[
                (b'objects', evennia.players.manager.PlayerDBManager()),
            ],
        ),
        migrations.AlterField(
            model_name='playerdb',
            name='email',
            field=models.EmailField(max_length=254, verbose_name='email address', blank=True),
        ),
        migrations.AlterField(
            model_name='playerdb',
            name='groups',
            field=models.ManyToManyField(related_query_name='user', related_name='user_set', to='auth.Group', blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', verbose_name='groups'),
        ),
        migrations.AlterField(
            model_name='playerdb',
            name='last_login',
            field=models.DateTimeField(null=True, verbose_name='last login', blank=True),
        ),
        migrations.AlterField(
            model_name='playerdb',
            name='username',
            field=models.CharField(error_messages={'unique': 'A user with that username already exists.'}, max_length=30, validators=[django.core.validators.RegexValidator('^[\\w.@+-]+$', 'Enter a valid username. This value may contain only letters, numbers and @/./+/-/_ characters.', 'invalid')], help_text='Required. 30 characters or fewer. Letters, digits and @/./+/-/_ only.', unique=True, verbose_name='username'),
        ),
    ]
