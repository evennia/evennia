from django.conf import settings
from evennia.utils.utils import callables_from_module


class ValidatorContainer(object):
    """
    Loads and stores the final list of VALIDATOR FUNCTIONS.

    Can access these as properties or dictionary-contents.
    """

    def __init__(self):
        self.valid_storage = {}
        for module in settings.VALIDATOR_MODULES:
            self.valid_storage.update(callables_from_module(module))

    def __getitem__(self, item):
        return self.valid_storage.get(item, None)

    def __getattr__(self, item):
        return self[item]


# Ensure that we have a Singleton of ValidHandler that is always loaded... and only needs to be loaded once.
VALIDATOR_CONTAINER = ValidatorContainer()


class OptionContainer(object):
    """
    Loads and stores the final list of OPTION CLASSES.

    Can access these as properties or dictionary-contents.
    """
    def __init__(self):
        self.option_storage = {}
        for module in settings.OPTION_MODULES:
            self.option_storage.update(callables_from_module(module))

    def __getitem__(self, item):
        return self.option_storage.get(item, None)

    def __getattr__(self, item):
        return self[item]


# Ensure that we have a Singleton that keeps all loaded Options.
OPTION_CONTAINER = OptionContainer()
