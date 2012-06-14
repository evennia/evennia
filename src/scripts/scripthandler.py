"""
The script handler makes sure to check through all stored scripts
to make sure they are still relevant.
An scripthandler is automatically added to all game objects. You
access it through the property 'scripts' on the game object.
"""

from src.scripts.models import ScriptDB
from src.utils import create
from src.utils import logger

from django.utils.translation import ugettext as _

class ScriptHandler(object):
    """
    Implements the handler.  This sits on each game object.
    """
    def __init__(self, obj):
        """
        Set up internal state.
        obj - a reference to the object this handler is attached to.

        We retrieve all scripts attached to this object and check
        if they are all peristent. If they are not, they are just
        cruft left over from a server shutdown.
        """
        self.obj = obj

    def __str__(self):
        "List the scripts tied to this object"
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
                try: next_repeat = script.time_until_next_repeat()
                except: next_repeat = "?"
            string += _("\n '%(key)s' (%(next_repeat)s/%(interval)s, %(repeats)s repeats): %(desc)s") % \
              {"key":script.key, "next_repeat":next_repeat, "interval":interval,"repeats":repeats,"desc":script.desc}
        return string.strip()

    def add(self, scriptclass, key=None, autostart=True):
        """
        Add an script to this object.

        scriptclass - either a class object
             inheriting from Script, an instantiated script object
             or a python path to such a class object.
        key - optional identifier for the script (often set in script definition)
        autostart - start the script upon adding it
        """
        script = create.create_script(scriptclass, key=key, obj=self.obj, autostart=autostart)
        if not script:
            logger.log_errmsg("Script %s could not be created and/or started." % scriptclass)
            return False
        return True

    def start(self, scriptid):
        """
        Find an already added script and force-start it
        """
        scripts = ScriptDB.objects.get_all_scripts_on_obj(self.obj, key=scriptid)
        num = 0
        for script in scripts:
            num += script.start()
        return num

    def delete(self, scriptid):
        """
        Forcibly delete a script from this object.

        scriptid can be a script key or the path to a script (in the
                 latter case all scripts with this path will be deleted!)

        """
        delscripts = ScriptDB.objects.get_all_scripts_on_obj(self.obj, key=scriptid)
        if not delscripts:
            delscripts = [script for script in ScriptDB.objects.get_all_scripts_on_obj(self.obj) if script.path == scriptid]
        num = 0
        for script in delscripts:
            num += script.stop()
        return num

    def stop(self, scriptid):
        """
        Alias for delete. scriptid can be a script key or a script path string.
        """
        return self.delete(scriptid)

    def all(self, scriptid=None):
        """
        Get all scripts stored in the handler, alternatively all matching a key.
        """
        return ScriptDB.objects.get_all_scripts_on_obj(self.obj, key=scriptid)

    def validate(self, init_mode=False):
        """
        Runs a validation on this object's scripts only.
        This should be called regularly to crank the wheels.
        """
        ScriptDB.objects.validate(obj=self.obj, init_mode=init_mode)

