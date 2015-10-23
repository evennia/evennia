"""
The script handler makes sure to check through all stored scripts to
make sure they are still relevant. A scripthandler is automatically
added to all game objects. You access it through the property
`scripts` on the game object.

"""
from builtins import object

from evennia.scripts.models import ScriptDB
from evennia.utils import create
from evennia.utils import logger

from django.utils.translation import ugettext as _

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
                except:
                    next_repeat = "?"
            string += _("\n '%(key)s' (%(next_repeat)s/%(interval)s, %(repeats)s repeats): %(desc)s") % \
              {"key": script.key, "next_repeat": next_repeat,
               "interval": interval, "repeats": repeats, "desc": script.desc}
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

        """
        if self.obj.__dbclass__.__name__ == "PlayerDB":
            # we add to a Player, not an Object
            script = create.create_script(scriptclass, key=key, player=self.obj,
                                          autostart=autostart)
        else:
            # the normal - adding to an Object
            script = create.create_script(scriptclass, key=key, obj=self.obj,
                                      autostart=autostart)
        if not script:
            logger.log_err("Script %s could not be created and/or started." % scriptclass)
            return False
        return True

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
            num += script.start()
        return num

    def get(self, key):
        """
        Search scripts on this object.

        Args:
            key (str): Search criterion, the script's key or dbref.

        Returns:
            scripts (list): The found scripts matching `key`.

        """
        return ScriptDB.objects.get_all_scripts_on_obj(self.obj, key=key)

    def delete(self, key=None):
        """
        Forcibly delete a script from this object.

        Args:
            key (str, optional): A script key or the path to a script (in the
                latter case all scripts with this path will be deleted!)
                If no key is given, delete *all* scripts on the object!

        """
        delscripts = ScriptDB.objects.get_all_scripts_on_obj(self.obj, key=key)
        if not delscripts:
            delscripts = [script for script in ScriptDB.objects.get_all_scripts_on_obj(self.obj) if script.path == key]
        num = 0
        for script in delscripts:
            num += script.stop()
        return num
    # alias to delete
    stop = delete

    def all(self):
        """
        Get all scripts stored in this handler.

        """
        return ScriptDB.objects.get_all_scripts_on_obj(self.obj)

    def validate(self, init_mode=False):
        """
        Runs a validation on this object's scripts only.  This should
        be called regularly to crank the wheels.

        Args:
            init_mode (str, optional): - This is used during server
                upstart and can have three values:
                - `False` (no init mode). Called during run.
                - `"reset"` - server reboot. Kill non-persistent scripts
                - `"reload"` - server reload. Keep non-persistent scripts.

        """
        ScriptDB.objects.validate(obj=self.obj, init_mode=init_mode)
