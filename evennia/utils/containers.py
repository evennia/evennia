"""
Containers

"""


from django.conf import settings
from evennia.utils.utils import class_from_module
from evennia.utils import logger


class GlobalScriptContainer(object):
    """
    Simple Handler object loaded by the Evennia API to contain and manage a
    game's Global Scripts. Scripts to start are defined by
    `settings.GLOBAL_SCRIPTS`.

    Example:
        import evennia
        evennia.GLOBAL_SCRIPTS.scriptname

    """

    def __init__(self):
        """
        Initialize the container by preparing scripts. Lazy-load only when the
        script is requested.

        """
        self.script_data = {key: {} if data is None else data
                            for key, data in settings.GLOBAL_SCRIPTS.items()}
        self.script_storage = {}
        self.typeclass_storage = {}

        for key, data in self.script_data.items():
            try:
                typeclass = data.get('typeclass', settings.BASE_SCRIPT_TYPECLASS)
                self.typeclass_storage[key] = class_from_module(typeclass)
            except ImportError as err:
                logger.log_err(f"GlobalContainer could not start global script {key}: {err}")

    def __getitem__(self, key):

        if key not in self.typeclass_storage:
            # this script is unknown to the container
            return None

        # (re)create script on-demand
        return self.script_storage.get(key) or self._load_script(key)

    def __getattr__(self, key):
        return self[key]

    def _load_script(self, key):
        typeclass = self.typeclass_storage[key]
        found = typeclass.objects.filter(db_key=key).first()
        interval = self.script_data[key].get('interval', None)
        start_delay = self.script_data[key].get('start_delay', None)
        repeats = self.script_data[key].get('repeats', 0)
        desc = self.script_data[key].get('desc', '')

        if not found:
            new_script, errors = typeclass.create(key=key, persistent=True,
                                                  interval=interval,
                                                  start_delay=start_delay,
                                                  repeats=repeats, desc=desc)
            if errors:
                logger.log_err("\n".join(errors))
                return None

            new_script.start()
            self.script_storage[key] = new_script
            return new_script

        if ((found.interval != interval) or
                (found.start_delay != start_delay) or
                (found.repeats != repeats)):
            found.restart(interval=interval, start_delay=start_delay, repeats=repeats)
        if found.desc != desc:
            found.desc = desc
        self.script_storage[key] = found
        return found

    def get(self, key):
        """
        Retrive script by key (in case of not knowing it beforehand).

        Args:
            key (str): The name of the script.

        Returns:
            script (Script): The named global script.

        """
        # note that this will recreate the script if it doesn't exist/was lost
        return self[key]

    def all(self):
        """
        Get all scripts.

        Returns:
            scripts (list): All global script objects stored on the container.

        """
        return list(self.script_storage.values())


# Create singleton of the GlobalHandler for the API.
GLOBAL_SCRIPTS = GlobalScriptContainer()
