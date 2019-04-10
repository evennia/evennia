from django.conf import settings
from evennia.utils.utils import callables_from_module


class ValidHandler(object):

    def __init__(self):
        self.valid_storage = {}
        for module in settings.VALIDFUNC_MODULES:
            self.valid_storage.update(callables_from_module(module))

    def __getitem__(self, item):
        return self.valid_storage.get(item, None)


VALID_HANDLER = ValidHandler()
