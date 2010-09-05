"""
The script handler makes sure to check through all stored scripts
to make sure they are still relevant.
An scripthandler is automatically added to all game objects. You
access it through the property 'scripts' on the game object.  
"""

from src.scripts.models import ScriptDB
from src.utils import create 
from src.utils import logger

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

        # this is required to stop a nasty loop in some situations that
        # has the handler infinitely recursively re-added to its object.
        self.obj.scripts = self
        
        scripts = ScriptDB.objects.get_all_scripts_on_obj(self.obj)
        #print "starting scripthandler. %s has scripts %s" % (self.obj, scripts)
        if scripts:
            okscripts = [script for script in scripts if script.persistent == True]
            delscripts = [script for script in scripts if script not in okscripts]
            for script in delscripts:
                #print "stopping script %s" % script
                script.stop()
            for script in okscripts:
                #print "starting script %s" % script
                script.start()

    def __str__(self):
        "List the scripts tied to this object"
        scripts = ScriptDB.objects.get_all_scripts_on_obj(self.obj)
        string = ""
        for script in scripts:
            interval = "inf"
            next_repeat = "inf"
            repeats = "inf"
            if script.interval: 
                interval = script.interval
                if script.repeats:
                    repeats = script.repeats                    
                try: next_repeat = script.time_until_next_repeat()
                except: next_repeat = "?"
            string += "\n '%s' (%s/%s, %s repeats): %s" % (script.key,
                                                         next_repeat,
                                                         interval,
                                                         repeats,
                                                         script.desc)
        return string.strip()

    def add(self, scriptclass, key=None, autostart=True):
        """
        Add an script to this object. The scriptclass
        argument can be either a class object
        inheriting from Script, an instantiated script object
        or a python path to such a class object.

        """            
        script = create.create_script(scriptclass, key=key, obj=self.obj, autostart=autostart)
        if not script:
            logger.log_errmsg("Script %s failed to be created/start." % scriptclass)

    def start(self, scriptkey):
        """
        Find an already added script and force-start it
        """
        scripts = ScriptDB.objects.get_all_scripts_on_obj(self.obj, key=scriptkey)
        for script in scripts:
            script.start()            

    def delete(self, scriptkey):
        """
        Forcibly delete a script from this object.
        """
        delscripts = ScriptDB.objects.get_all_scripts_on_obj(self.obj, key=scriptkey)
        for script in delscripts:
            script.stop()

    def stop(self, scriptkey):
        """
        Alias for delete.
        """
        self.delete(scriptkey)

    def all(self, scriptkey=None):
        """
        Get all scripts stored in the handler, alternatively all matching a key.
        """
        return ScriptDB.objects.get_all_scripts_on_obj(self.obj, key=scriptkey)

    def validate(self):
        """
        Runs a validation on this object's scripts only.
        This should be called regularly to crank the wheels.
        """
        ScriptDB.objects.validate(obj=self.obj)
        
