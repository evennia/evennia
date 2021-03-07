"""
The custom manager for Scripts.
"""

from django.db.models import Q
from evennia.typeclasses.managers import TypedObjectManager, TypeclassManager
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
        account = _GA(_GA(obj, "__dbclass__"), "__name__") == "AccountDB"
        if key:
            dbref = self.dbref(key)
            if dbref or dbref == 0:
                if account:
                    return self.filter(db_account=obj, id=dbref)
                else:
                    return self.filter(db_obj=obj, id=dbref)
            elif account:
                return self.filter(db_account=obj, db_key=key)
            else:
                return self.filter(db_obj=obj, db_key=key)
        elif account:
            return self.filter(db_account=obj)
        else:
            return self.filter(db_obj=obj)

    def get_all_scripts(self, key=None):
        """
        Get all scripts in the database.

        Args:
            key (str or int, optional): Restrict result to only those
                with matching key or dbref.

        Returns:
            scripts (list): All scripts found, or those matching `key`.

        """
        if key:
            script = []
            dbref = self.dbref(key)
            if dbref:
                return self.filter(id=dbref)
            return self.filter(db_key__iexact=key.strip())
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
            script.delete()

    def update_scripts_after_server_start(self):
        """
        Update/sync/restart/delete scripts after server shutdown/restart.

        """
        for script in self.filter(db_is_active=True, db_persistent=False):
            script._stop_task()

        for script in self.filter(db_is_active=True):
            script._unpause_task(auto_unpause=True)
            script.at_server_start()

        for script in self.filter(db_is_active=False):
            script.at_server_start()

    def search_script(self, ostring, obj=None, only_timed=False, typeclass=None):
        """
        Search for a particular script.

        Args:
            ostring (str): Search criterion - a script dbef or key.
            obj (Object, optional): Limit search to scripts defined on
                this object
            only_timed (bool): Limit search only to scripts that run
                on a timer.
            typeclass (class or str): Typeclass or path to typeclass.

        """

        ostring = ostring.strip()

        dbref = self.dbref(ostring)
        if dbref:
            # this is a dbref, try to find the script directly
            dbref_match = self.dbref_search(dbref)
            if dbref_match and not (
                (obj and obj != dbref_match.obj) or (only_timed and dbref_match.interval)
            ):
                return [dbref_match]

        if typeclass:
            if callable(typeclass):
                typeclass = "%s.%s" % (typeclass.__module__, typeclass.__name__)
            else:
                typeclass = "%s" % typeclass

        # not a dbref; normal search
        obj_restriction = obj and Q(db_obj=obj) or Q()
        timed_restriction = only_timed and Q(db_interval__gt=0) or Q()
        typeclass_restriction = typeclass and Q(db_typeclass_path=typeclass) or Q()
        scripts = self.filter(
            timed_restriction & obj_restriction & typeclass_restriction & Q(db_key__iexact=ostring)
        )
        return scripts

    # back-compatibility alias
    script_search = search_script

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

        new_script = create.create_script(
            typeclass, key=new_key, obj=new_obj, locks=new_locks, autostart=True
        )
        return new_script


class ScriptManager(ScriptDBManager, TypeclassManager):
    pass
