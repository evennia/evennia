from django.conf import settings
from evennia.utils.utils import class_from_module


class GlobalHandler(object):
    """
    Simple Handler object loaded by the Evennia API to contain and manage a game's Global Scripts.

    This is accessed like a dictionary.

    Example:
        import evennia
        evennia.GLOBAL_HANDLER['key']
    """

    def __init__(self):
        self.typeclass_storage = dict()
        self.script_storage = dict()
        for k, v in settings.GLOBAL_SCRIPTS.items():
            self.typeclass_storage[k] = class_from_module(v)
        for k, v in self.typeclass_storage.items():
            found = v.objects.filter_family(db_key=k).first()
            if not found:
                found = v.create(key=k, typeclass=v, persistent=True)
            self.script_storage[k] = found

    def __getitem__(self, item):

        # Likely to only reach this if someone called the API wrong.
        if item not in self.typeclass_storage:
            return None

        # The most common outcome next!
        if self.script_storage[item]:
            return self.script_storage[item]
        else:
            # Oops, something happened to our Global Script. Let's re-create it.
            reloaded = self.typeclass_storage[item].create(key=item, typeclass=self.typeclass_storage[item],
                                                           persistent=True)
            self.script_storage[item] = reloaded
            return reloaded


# Create singleton of the GlobalHandler for the API.
GLOBAL_HANDLER = GlobalHandler()
