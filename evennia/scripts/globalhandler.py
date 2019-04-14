from django.conf import settings
from evennia.utils.utils import class_from_module


class GlobalContainer(object):
    """
    Simple Handler object loaded by the Evennia API to contain and manage a game's Global Scripts.

    This is accessed like a dictionary. Alternatively you can access Properties on it.

    Example:
        import evennia
        evennia.GLOBAL_SCRIPTS['key']
    """

    def __init__(self):
        self.script_data = dict()
        self.script_storage = dict()
        self.script_data.update(settings.GLOBAL_SCRIPTS)
        self.typeclass_storage = dict()

        for key, data in settings.GLOBAL_SCRIPTS.items():
            self.typeclass_storage[key] = class_from_module(data['typeclass'])
        for key in self.script_data.keys():
            self._load_script(key)

    def __getitem__(self, item):

        # Likely to only reach this if someone called the API wrong.
        if item not in self.typeclass_storage:
            return None

        # The most common outcome next!
        if self.script_storage[item]:
            return self.script_storage[item]
        else:
            # Oops, something happened to our Global Script. Let's re-create it.
            return self._load_script(item)

    def __getattr__(self, item):
        return self[item]

    def _load_script(self, item):
        typeclass = self.typeclass_storage[item]
        found = typeclass.objects.filter(db_key=item).first()
        interval = self.script_data[item].get('interval', None)
        start_delay = self.script_data[item].get('start_delay', None)
        repeats = self.script_data[item].get('repeats', 0)
        desc = self.script_data[item].get('desc', '')

        if not found:
            new_script = typeclass.create(key=item, persistent=True, interval=interval, start_delay=start_delay,
                                          repeats=repeats, desc=desc)
            new_script.start()
            self.script_storage[item] = new_script
            return new_script

        if (found.interval != interval) or (found.start_delay != start_delay) or (found.repeats != repeats):
            found.restart(interval=interval, start_delay=start_delay, repeats=repeats)
        if found.desc != desc:
            found.desc = desc
        self.script_storage[item] = found
        return found




# Create singleton of the GlobalHandler for the API.
GLOBAL_SCRIPTS = GlobalContainer()
