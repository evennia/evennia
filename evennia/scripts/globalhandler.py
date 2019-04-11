from django.conf import settings
from evennia.utils.utils import class_from_module


class GlobalHandler(object):
    """
    Simple Handler object loaded by the Evennia API to contain and manage a game's Global Scripts.

    This is accessed like a dictionary. Alternatively you can access Properties on it.

    Example:
        import evennia
        evennia.GLOBAL_SCRIPTS['key']
    """

    def __init__(self):
        self.typeclass_storage = dict()
        self.script_storage = dict()
        for key, typeclass_path in settings.GLOBAL_SCRIPTS.items():
            self.typeclass_storage[key] = class_from_module(typeclass_path)
        for key, typeclass in self.typeclass_storage.items():
            found = typeclass.objects.filter(db_key=key).first()
            if not found:
                found = typeclass.create(key=key, typeclass=typeclass, persistent=True)
            self.script_storage[key] = found

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

    def __getattr__(self, item):
        return self[item]


# Create singleton of the GlobalHandler for the API.
GLOBAL_SCRIPTS = GlobalHandler()
