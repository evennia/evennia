"""
Containers

Containers are storage classes usually initialized from a setting. They
represent Singletons and acts as a convenient place to find resources (
available as properties on the singleton)

evennia.GLOBAL_SCRIPTS
evennia.OPTION_CLASSES

"""

from pickle import dumps

from django.conf import settings
from django.db.utils import OperationalError, ProgrammingError
from evennia.scripts.models import ScriptDB
from evennia.utils import logger
from evennia.utils.utils import callables_from_module, class_from_module

SCRIPTDB = None


class Container:
    """
    Base container class. A container is simply a storage object whose
    properties can be acquired as a property on it. This is generally
    considered a read-only affair.

    The container is initialized by a list of modules containing callables.

    """

    storage_modules = []

    def __init__(self):
        """
        Read data from module.

        """
        self.loaded_data = None

    def load_data(self):
        """
        Delayed import to avoid eventual circular imports from inside
        the storage modules.

        """
        if self.loaded_data is None:
            self.loaded_data = {}
            for module in self.storage_modules:
                self.loaded_data.update(callables_from_module(module))

    def __getattr__(self, key):
        return self.get(key)

    def get(self, key, default=None):
        """
        Retrive data by key (in case of not knowing it beforehand).

        Args:
            key (str): The name of the script.
            default (any, optional): Value to return if key is not found.

        Returns:
            any (any): The data loaded on this container.

        """
        self.load_data()
        return self.loaded_data.get(key, default)

    def all(self):
        """
        Get all stored data

        Returns:
            scripts (list): All global script objects stored on the container.

        """
        self.load_data()
        return list(self.loaded_data.values())


class OptionContainer(Container):
    """
    Loads and stores the final list of OPTION CLASSES.

    Can access these as properties or dictionary-contents.
    """

    storage_modules = settings.OPTION_CLASS_MODULES


class GlobalScriptContainer(Container):
    """
    Simple Handler object loaded by the Evennia API to contain and manage a
    game's Global Scripts. This will list global Scripts created on their own
    but will also auto-(re)create scripts defined in `settings.GLOBAL_SCRIPTS`.

    Example:
        import evennia
        evennia.GLOBAL_SCRIPTS.scriptname

    Note:
        This does not use much of the BaseContainer since it's not loading
        callables from settings but a custom dict of tuples.

    """

    def __init__(self):
        """
        Note: We must delay loading of typeclasses since this module may get
        initialized before Scripts are actually initialized.

        """
        self.typeclass_storage = dict()
        self.loaded_data = {
            key: {} if data is None else data for key, data in settings.GLOBAL_SCRIPTS.items()
        }
        self.loaded = False

    def _load_script(self, key):
        typeclass = self.typeclass_storage[key]
        script = typeclass.objects.filter(
            db_key=key, db_account__isnull=True, db_obj__isnull=True
        ).first()

        kwargs = {**self.loaded_data[key]}
        kwargs["key"] = key
        kwargs["persistent"] = kwargs.get("persistent", True)

        compare_hash = str(dumps(kwargs, protocol=4))

        if script:
            script_hash = script.attributes.get("global_script_settings", category="settings_hash")
            if script_hash is None:
                # legacy - store the hash anew and assume no change
                script.attributes.add(
                    "global_script_settings", compare_hash, category="settings_hash"
                )
            elif script_hash != compare_hash:
                # wipe the old version and create anew
                logger.log_info(f"GLOBAL_SCRIPTS: Settings changed for {key} ({typeclass}).")
                script.stop()
                script.delete()
                script = None

        if not script:
            logger.log_info(f"GLOBAL_SCRIPTS: (Re)creating {key} ({typeclass}).")

            script, errors = typeclass.create(**kwargs)
            if errors:
                logger.log_err("\n".join(errors))
                return None

            # store a hash representation of the setup
            script.attributes.add("global_script_settings", compare_hash, category="settings_hash")

        return script

    def start(self):
        """
        Called last in evennia.__init__ to initialize the container late
        (after script typeclasses have finished loading).

        We include all global scripts in the handler and
        make sure to auto-load time-based scripts.

        """
        # populate self.typeclass_storage
        if not self.loaded:
            self.load_data()

        # make sure settings-defined scripts are loaded
        scripts_to_run = []
        for key in self.loaded_data:
            script = self._load_script(key)
            if script:
                scripts_to_run.append(script)
        # start all global scripts
        try:
            for script in scripts_to_run:
                script.start()
        except (OperationalError, ProgrammingError):
            # this can happen if db is not loaded yet (such as when building docs)
            pass

    def load_data(self):
        """
        This delayed import avoids trying to load Scripts before they are
        initialized.

        """
        if self.loaded:
            return
        if not self.typeclass_storage:
            for key, data in list(self.loaded_data.items()):
                typeclass = data.get("typeclass", settings.BASE_SCRIPT_TYPECLASS)
                self.typeclass_storage[key] = class_from_module(
                    typeclass, fallback=settings.BASE_SCRIPT_TYPECLASS
                )
        self.loaded = True

    def get(self, key, default=None):
        """
        Retrive data by key (in case of not knowing it beforehand). Any
        scripts that are in settings.GLOBAL_SCRIPTS that are not found
        will be recreated on-demand.

        Args:
            key (str): The name of the script.
            default (any, optional): Value to return if key is not found
                at all on this container (i.e it cannot be loaded at all).

        Returns:
            any (any): The data loaded on this container.
        """
        if not self.loaded:
            self.load_data()
        script_found = None
        if key in self.loaded_data:
            if key not in self.typeclass_storage:
                # this means we are trying to load in a loop
                raise RuntimeError(
                    f"Trying to access `GLOBAL_SCRIPTS.{key}` before scripts have finished "
                    "initializing. This can happen if accessing GLOBAL_SCRIPTS from the same "
                    "module the script is defined in."
                )
            # recreate if we have the info
            script_found = self._load_script(key)
            if script_found:
                out_value = script_found
        else:
            # script not found in settings, see if one exists in database (not
            # auto-started/recreated)
            script_found = ScriptDB.objects.filter(db_key__iexact=key, db_obj__isnull=True).first()

        return script_found if script_found is not None else default

    def all(self):
        """
        Get all global scripts. Note that this will not auto-start
        scripts defined in settings.

        Returns:
            list: All global script objects in game (both managed and unmanaged),
                sorted alphabetically.

        """
        if not self.loaded:
            self.load_data()
        managed_scripts = [self._load_script(key) for key in self.typeclass_storage.keys()]
        unmanaged_scripts = list(
            ScriptDB.objects.filter(db_obj__isnull=True).exclude(
                id__in=[scr.id for scr in managed_scripts]
            )
        )
        return list(sorted(managed_scripts + unmanaged_scripts, key=lambda scr: scr.db_key))


# Create all singletons

GLOBAL_SCRIPTS = GlobalScriptContainer()
OPTION_CLASSES = OptionContainer()
