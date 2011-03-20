"""
The custom manager for Scripts.
"""

from src.typeclasses.managers import TypedObjectManager
from src.typeclasses.managers import returns_typeclass_list

VALIDATE_ITERATION = 0

class ScriptManager(TypedObjectManager):
    """
    ScriptManager get methods
    """
    @returns_typeclass_list
    def get_all_scripts_on_obj(self, obj, key=None):
        """
        Returns as result all the Scripts related to a particular object
        """
        if not obj:
            return []
        scripts = self.filter(db_obj=obj)
        if key:           
            return scripts.filter(db_key=key)
        return scripts 

    @returns_typeclass_list
    def get_all_scripts(self, key=None):
        """
        Return all scripts, alternative only
        scripts with a certain key/dbref or path. 
        """
        if key:
            dbref = self.dbref(key)
            if dbref:
                # try to see if this is infact a dbref
                script = self.dbref_search(dbref)
                if script:
                    return script
            # not a dbref. Normal key search
            scripts = self.filter(db_key=key)
        else:
            scripts = list(self.all())
        return scripts

    def delete_script(self, dbref):
        """
        This stops and deletes a specific script directly
        from the script database. This might be
        needed for global scripts not tied to
        a specific game object. 
        """
        scripts = self.get_id(dbref)
        for script in scripts:
            script.stop()

    def remove_non_persistent(self):
        """
        This cleans up the script database of all non-persistent
        scripts. It is called every time the server restarts. 
        """
        nr_deleted = 0
        for script in [script for script in self.get_all_scripts()
                       if not script.persistent]:
            script.stop()
            nr_deleted += 1 
        return nr_deleted 


    def validate(self, scripts=None, obj=None, key=None, dbref=None, 
                 init_mode=False):
        """
        This will step through the script database and make sure
        all objects run scripts that are still valid in the context
        they are in. This is called by the game engine at regular
        intervals but can also be initiated by player scripts. 
        If key and/or obj is given, only update the related
        script/object.

        Only one of the arguments are supposed to be supplied
        at a time, since they are exclusive to each other.
        
        scripts = a list of scripts objects obtained somewhere.
        obj = validate only scripts defined on a special object.
        key = validate only scripts with a particular key
        dbref = validate only the single script with this particular id. 

        init_mode - When this mode is active, non-persistent scripts
                    will be removed and persistent scripts will be
                    force-restarted.

        This method also makes sure start any scripts it validates,
        this should be harmless, since already-active scripts
        have the property 'is_running' set and will be skipped. 
        """

        # we store a variable that tracks if we are calling a 
        # validation from within another validation (avoids 
        # loops). 
        global VALIDATE_ITERATION        
        if VALIDATE_ITERATION > 0:
            # we are in a nested validation. Exit.
            VALIDATE_ITERATION -= 1
            return None, None 
        VALIDATE_ITERATION += 1

        # not in a validation - loop. Validate as normal.
        
        nr_started = 0
        nr_stopped = 0        

        if init_mode:
            # special mode when server starts or object logs in. 
            # This deletes all non-persistent scripts from database
            nr_stopped += self.remove_non_persistent()

        if dbref and self.dbref(dbref):
            scripts = self.get_id(dbref)
        elif scripts:
            pass
        elif obj:
            scripts = self.get_all_scripts_on_obj(obj, key=key)            
        else:
            scripts = self.model.get_all_cached_instances()#get_all_scripts(key=key)        
        if not scripts:
            VALIDATE_ITERATION -= 1
            return None, None
        #print "scripts to validate: [%s]" % (", ".join(script.key for script in scripts))        
        for script in scripts:
            if script.is_valid():
                #print "validating %s (%i)" % (script.key, id(script.dbobj)) 
                nr_started += script.start(force_restart=init_mode) 
                #print "back from start."
            else:
                script.stop()
                nr_stopped += 1
        VALIDATE_ITERATION -= 1
        return nr_started, nr_stopped
            
    @returns_typeclass_list
    def script_search(self, ostring, obj=None, only_timed=False):
        """
        Search for a particular script.
        
        ostring - search criterion - a script ID or key
        obj - limit search to scripts defined on this object
        only_timed - limit search only to scripts that run
                     on a timer.         
        """

        ostring = ostring.strip()
        
        dbref = self.dbref(ostring)
        if dbref:
            # this is a dbref, try to find the script directly
            dbref_match = self.dbref_search(dbref)
            if dbref_match:
                ok = True 
                if obj and obj != dbref_match.obj:
                    ok = False
                if only_timed and dbref_match.interval:
                    ok = False 
                if ok:
                    return [dbref_match]
        # not a dbref; normal search
        scripts = self.filter(db_key__iexact=ostring)
        
        if obj:
            scripts = scripts.exclude(db_obj=None).filter(db_obj__db_key__iexact=ostring)
        if only_timed:
            scripts = scripts.exclude(interval=0)
        return scripts
