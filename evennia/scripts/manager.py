"""
The custom manager for Scripts.
"""

from django.db.models import Q
from evennia.typeclasses.managers import TypedObjectManager, TypeclassManager
from evennia.typeclasses.managers import returns_typeclass_list
from evennia.utils.utils import make_iter
__all__ = ("ScriptManager",)
_GA = object.__getattribute__

VALIDATE_ITERATION = 0


class ScriptDBManager(TypedObjectManager):
    """
    This Scriptmanager implements methods for searching
    and manipulating Scripts directly from the database.

    Evennia-specific search methods (will return Typeclasses or
    lists of Typeclasses, whereas Django-general methods will return
    Querysets or database objects).

    dbref (converter)
    get_id  (or dbref_search)
    get_dbref_range
    object_totals
    typeclass_search
    get_all_scripts_on_obj
    get_all_scripts
    delete_script
    remove_non_persistent
    validate
    script_search (equivalent to evennia.search_script)
    copy_script

    """
    @returns_typeclass_list
    def get_all_scripts_on_obj(self, obj, key=None):
        """
        Find all Scripts related to a particular object.

        Args:
            obj (Object): Object whose Scripts we are looking for.
            key (str, optional): Script identifier - can be given as a
                dbref or name string. If given, only scripts matching the
                key on the object will be returned.
        Returns:
            matches (list): Matching scripts.

        """
        if not obj:
            return []
        player = _GA(_GA(obj, "__dbclass__"), "__name__") == "PlayerDB"
        if key:
            dbref = self.dbref(key)
            if dbref or dbref == 0:
                if player:
                    return self.filter(db_player=obj, id=dbref)
                else:
                    return self.filter(db_obj=obj, id=dbref)
            elif player:
                return self.filter(db_player=obj, db_key=key)
            else:
                return self.filter(db_obj=obj, db_key=key)
        elif player:
            return self.filter(db_player=obj)
        else:
            return self.filter(db_obj=obj)

    @returns_typeclass_list
    def get_all_scripts(self, key=None):
        """
        Get all scripts in the database.

        Args:
            key (str, optional): Restrict result to only those
                with matching key or dbref.

        Returns:
            scripts (list): All scripts found, or those matching `key`.

        """
        if key:
            script = []
            dbref = self.dbref(key)
            if dbref or dbref == 0:
                script = [self.dbref_search(dbref)]
            if not script:
                script = self.filter(db_key=key)
            return script
        return self.all()

    def delete_script(self, dbref):
        """
        This stops and deletes a specific script directly from the
        script database.

        Args:
            dbref (int): Database unique id.

        Notes:
            This might be needed for global scripts not tied to a
            specific game object

        """
        scripts = self.get_id(dbref)
        for script in make_iter(scripts):
            script.stop()

    def remove_non_persistent(self, obj=None):
        """
        This cleans up the script database of all non-persistent
        scripts. It is called every time the server restarts.

        Args:
            obj (Object, optional): Only remove non-persistent scripts
                assigned to this object.

        """
        if obj:
            to_stop = self.filter(db_obj=obj, db_persistent=False, db_is_active=True)
            to_delete = self.filter(db_obj=obj, db_persistent=False, db_is_active=False)
        else:
            to_stop = self.filter(db_persistent=False, db_is_active=True)
            to_delete = self.filter(db_persistent=False, db_is_active=False)
        nr_deleted = to_stop.count() + to_delete.count()
        for script in to_stop:
            script.stop()
        for script in to_delete:
            script.delete()
        return nr_deleted

    def validate(self, scripts=None, obj=None, key=None, dbref=None,
                 init_mode=False):
        """
        This will step through the script database and make sure
        all objects run scripts that are still valid in the context
        they are in. This is called by the game engine at regular
        intervals but can also be initiated by player scripts.

        Only one of the arguments are supposed to be supplied
        at a time, since they are exclusive to each other.

        Args:
            scripts (list, optional): A list of script objects to
                validate.
            obj (Object, optional): Validate only scripts defined on
                this object.
            key (str): Validate only scripts with this key.
            dbref (int): Validate only the single script with this
                particular id.
            init_mode (str, optional): This is used during server
                upstart and can have three values:
                - `False` (no init mode). Called during run.
                - `"reset"` - server reboot. Kill non-persistent scripts
                - `"reload"` - server reload. Keep non-persistent scripts.
        Returns:
            nr_started, nr_stopped (tuple): Statistics on how many objects
                where started and stopped.

        Notes:
            This method also makes sure start any scripts it validates
            which should be harmless, since already-active scripts have
            the property 'is_running' set and will be skipped.

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
            if init_mode == 'reset':
                # special mode when server starts or object logs in.
                # This deletes all non-persistent scripts from database
                nr_stopped += self.remove_non_persistent(obj=obj)
            # turn off the activity flag for all remaining scripts
            scripts = self.get_all_scripts()
            for script in scripts:
                script.is_active = False

        elif not scripts:
            # normal operation
            if dbref and self.dbref(dbref, reqhash=False):
                scripts = self.get_id(dbref)
            elif obj:
                scripts = self.get_all_scripts_on_obj(obj, key=key)
            else:
                scripts = self.get_all_scripts(key=key) #self.model.get_all_cached_instances()

        if not scripts:
            # no scripts available to validate
            VALIDATE_ITERATION -= 1
            return None, None

        for script in scripts:
            if script.is_valid():
                nr_started += script.start(force_restart=init_mode)
            else:
                script.stop()
                nr_stopped += 1
        VALIDATE_ITERATION -= 1
        return nr_started, nr_stopped

    @returns_typeclass_list
    def script_search(self, ostring, obj=None, only_timed=False):
        """
        Search for a particular script.

        Args:
            ostring (str): Search criterion - a script dbef or key.
            obj (Object, optional): Limit search to scripts defined on
                this object
            only_timed (bool): Limit search only to scripts that run
                on a timer.

        """

        ostring = ostring.strip()

        dbref = self.dbref(ostring)
        if dbref or dbref == 0:
            # this is a dbref, try to find the script directly
            dbref_match = self.dbref_search(dbref)
            if dbref_match and not ((obj and obj != dbref_match.obj)
                                     or (only_timed and dbref_match.interval)):
                return [dbref_match]

        # not a dbref; normal search
        obj_restriction = obj and Q(db_obj=obj) or Q()
        timed_restriction = only_timed and Q(interval__gt=0) or Q()
        scripts = self.filter(timed_restriction & obj_restriction & Q(db_key__iexact=ostring))
        return scripts

    def copy_script(self, original_script, new_key=None, new_obj=None, new_locks=None):
        """
        Make an identical copy of the original_script.

        Args:
            original_script (Script): The Script to copy.
            new_key (str, optional): Rename the copy.
            new_obj (Object, optional): Place copy on different Object.
            new_locks (str, optional): Give copy different locks from
                the original.

        Returns:
            script_copy (Script): A new Script instance, copied from
                the original.
        """
        typeclass = original_script.typeclass_path
        new_key = new_key if new_key is not None else original_script.key
        new_obj = new_obj if new_obj is not None else original_script.obj
        new_locks = new_locks if new_locks is not None else original_script.db_lock_storage

        from evennia.utils import create
        new_script = create.create_script(typeclass, key=new_key, obj=new_obj,
                                          locks=new_locks, autostart=True)
        return new_script

class ScriptManager(ScriptDBManager, TypeclassManager):
    pass
