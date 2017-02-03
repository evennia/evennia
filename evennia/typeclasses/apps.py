from __future__ import unicode_literals

from django.apps import AppConfig


class TypeclassesConfig(AppConfig):
    name = 'typeclasses'

    def ready(self):
        from . import signals
