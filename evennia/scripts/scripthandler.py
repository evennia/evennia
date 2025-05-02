"""
The script handler makes sure to check through all stored scripts to
make sure they are still relevant. A scripthandler is automatically
added to all game objects. You access it through the property
`scripts` on the game object.

"""

from django.utils.translation import gettext as _

from evennia.scripts.models import ScriptDB
from evennia.utils import create, logger


class ScriptHandler(object):
    """
    Implements the handler.  This sits on each game object.

    """

    def __init__(self, obj):
        """
        Set up internal state.

        Args:
            obj (Object): A reference to the object this handler is
                attached to.

        """
        self.obj = obj

    def __str__(self):
        """
        List the scripts tied to this object.

        """
        scripts = ScriptDB.objects.get_all_scripts_on_obj(self.obj)
        string = ""
        for script in scripts:
            interval = "inf"
            next_repeat = "inf"
            repeats = "inf"
            if script.interval > 0:
                interval = script.interval
                if script.repeats:
                    repeats = script.repeats
                try:
                    next_repeat = script.time_until_next_repeat()
                except Exception:
                    next_repeat = "?"
            string += _("\n '{key}' ({next_repeat}/{interval}, {repeats} repeats): {desc}").format(
                key=script.key,
                next_repeat=next_repeat,
                interval=interval,
                repeats=repeats,
                desc=script.desc,
            )
        return string.strip()

    def add(self, scriptclass, key=None, autostart=True):
        """
        Add a script to this object.

        Args:
            scriptclass (Scriptclass, Script or str): Either a class
                object inheriting from DefaultScript, an instantiated
                script object or a python path to such a class object.
            key (str, optional): Identifier for the script (often set
                in script definition and listings)
            autostart (bool, optional): Start the script upon adding it.

        Returns:
            Script: The newly created Script.

        """
        if isinstance(scriptclass, str) or callable(scriptclass):
            # a str or class to use create before adding to an Object. We wait to autostart
            # so we can differentiate a failing creation from a script that immediately starts/stops.
            if self.obj.__dbclass__.__name__ == "AccountDB":
                # we add to an Account, not an Object
                script = create.create_script(
                    scriptclass, key=key, account=self.obj, autostart=False
                )
            else:
                script = create.create_script(scriptclass, key=key, obj=self.obj, autostart=False)
        else:
            # already an instantiated class
            script = scriptclass
            if script.db_obj and script.db_obj != self.obj:
                logger.log_err(
                    f"Script instance {script} already belongs to "
                    f"another object: {script.db_obj}."
                )
                return None
            script.db_obj = self.obj
            script.save()

        if not script:
            logger.log_err(f"Script {scriptclass} failed to be created.")
            return None
        if autostart:
            script.start()
        if not script.id:
            # this can happen if the script has repeats=1 or calls stop() in at_repeat.
            logger.log_info(
                f"Script {scriptclass} started and then immediately stopped; "
                "it could probably be a normal function."
            )
        return script

    def start(self, key):
        """
        Find scripts and force-start them

        Args:
            key (str): The script's key or dbref.

        Returns:
            nr_started (int): The number of started scripts found.

        """
        scripts = ScriptDB.objects.get_all_scripts_on_obj(self.obj, key=key)
        num = 0
        for script in scripts:
            script.start()
            num += 1
        return num

    def has(self, key):
        """
        Determine if a given script exists on this object.

        Args:
            key (str): Search criterion, the script's key or dbref.

        Returns:
            bool: If the script exists or not.

        """
        return ScriptDB.objects.get_all_scripts_on_obj(self.obj, key=key).exists()

    def get(self, key):
        """
        Search scripts on this object.

        Args:
            key (str): Search criterion, the script's key or dbref.

        Returns:
            scripts (queryset): The found scripts matching `key`.

        """
        return ScriptDB.objects.get_all_scripts_on_obj(self.obj, key=key)

    def remove(self, key=None):
        """
        Forcibly delete a script from this object.

        Args:
            key (str, optional): A script key or the path to a script (in the
                latter case all scripts with this path will be deleted!)
                If no key is given, delete *all* scripts on the object!

        """
        delscripts = ScriptDB.objects.get_all_scripts_on_obj(self.obj, key=key)
        if not delscripts:
            delscripts = [
                script
                for script in ScriptDB.objects.get_all_scripts_on_obj(self.obj)
                if script.path == key
            ]
        num = 0
        for script in delscripts:
            script.delete()
            num += 1
        return num

    # legacy aliases to remove
    delete = remove
    stop = delete

    def all(self):
        """
        Get all scripts stored in this handler.

        """
        return ScriptDB.objects.get_all_scripts_on_obj(self.obj)
