"""
Scripts are entities that perform some sort of action, either only
once or repeatedly. They can be directly linked to a particular
Evennia Object or be stand-alonw (in the latter case it is considered
a 'global' script). Scripts can indicate both actions related to the
game world as well as pure behind-the-scenes events and effects.
Everything that has a time component in the game (i.e. is not
hard-coded at startup or directly created/controlled by players) is
handled by Scripts.

Scripts have to check for themselves that they should be applied at a
particular moment of time; this is handled by the is_valid() hook.
Scripts can also implement at_start and at_end hooks for preparing and
cleaning whatever effect they have had on the game object.

Common examples of uses of Scripts:

- Load the default cmdset to the account object's cmdhandler
  when logging in.
- Switch to a different state, such as entering a text editor,
  start combat or enter a dark room.
- Merge a new cmdset with the default one for changing which
  commands are available at a particular time
- Give the account/object a time-limited bonus/effect

"""
from django.conf import settings
from django.db import models
from django.core.exceptions import ObjectDoesNotExist
from evennia.typeclasses.models import TypedObject
from evennia.scripts.manager import ScriptDBManager
from evennia.utils.utils import dbref, to_str

__all__ = ("ScriptDB",)
_GA = object.__getattribute__
_SA = object.__setattr__


# ------------------------------------------------------------
#
# ScriptDB
#
# ------------------------------------------------------------


class ScriptDB(TypedObject):
    """
    The Script database representation.

    The TypedObject supplies the following (inherited) properties:
      key - main name
      name - alias for key
      typeclass_path - the path to the decorating typeclass
      typeclass - auto-linked typeclass
      date_created - time stamp of object creation
      permissions - perm strings
      dbref - #id of object
      db - persistent attribute storage
      ndb - non-persistent attribute storage

    The ScriptDB adds the following properties:
      desc - optional description of script
      obj - the object the script is linked to, if any
      account - the account the script is linked to (exclusive with obj)
      interval - how often script should run
      start_delay - if the script should start repeating right away
      repeats - how many times the script should repeat
      persistent - if script should survive a server reboot
      is_active - bool if script is currently running

    """

    #
    # ScriptDB Database Model setup
    #
    # These database fields are all set using their corresponding properties,
    # named same as the field, but withtou the db_* prefix.

    # inherited fields (from TypedObject):
    # db_key, db_typeclass_path, db_date_created, db_permissions

    # optional description.
    db_desc = models.CharField("desc", max_length=255, blank=True)
    # A reference to the database object affected by this Script, if any.
    db_obj = models.ForeignKey(
        "objects.ObjectDB",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name="scripted object",
        help_text="the object to store this script on, if not a global script.",
    )
    db_account = models.ForeignKey(
        "accounts.AccountDB",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name="scripted account",
        help_text="the account to store this script on (should not be set if db_obj is set)",
    )

    # how often to run Script (secs). -1 means there is no timer
    db_interval = models.IntegerField(
        "interval", default=-1, help_text="how often to repeat script, in seconds. -1 means off."
    )
    # start script right away or wait interval seconds first
    db_start_delay = models.BooleanField(
        "start delay", default=False, help_text="pause interval seconds before starting."
    )
    # how many times this script is to be repeated, if interval!=0.
    db_repeats = models.IntegerField("number of repeats", default=0, help_text="0 means off.")
    # defines if this script should survive a reboot or not
    db_persistent = models.BooleanField("survive server reboot", default=False)
    # defines if this script has already been started in this session
    db_is_active = models.BooleanField("script active", default=False)

    # Database manager
    objects = ScriptDBManager()

    # defaults
    __settingsclasspath__ = settings.BASE_SCRIPT_TYPECLASS
    __defaultclasspath__ = "evennia.scripts.scripts.DefaultScript"
    __applabel__ = "scripts"

    class Meta(object):
        "Define Django meta options"
        verbose_name = "Script"

    #
    #
    # ScriptDB class properties
    #
    #

    # obj property
    def __get_obj(self):
        """
        Property wrapper that homogenizes access to either the
        db_account or db_obj field, using the same object property
        name.

        """
        obj = _GA(self, "db_account")
        if not obj:
            obj = _GA(self, "db_obj")
        return obj

    def __set_obj(self, value):
        """
        Set account or obj to their right database field. If
        a dbref is given, assume ObjectDB.

        """
        try:
            value = _GA(value, "dbobj")
        except AttributeError:
            # deprecated ...
            pass
        if isinstance(value, (str, int)):
            from evennia.objects.models import ObjectDB

            value = to_str(value)
            if value.isdigit() or value.startswith("#"):
                dbid = dbref(value, reqhash=False)
                if dbid:
                    try:
                        value = ObjectDB.objects.get(id=dbid)
                    except ObjectDoesNotExist:
                        # maybe it is just a name that happens to look like a dbid
                        pass
        if value.__class__.__name__ == "AccountDB":
            fname = "db_account"
            _SA(self, fname, value)
        else:
            fname = "db_obj"
            _SA(self, fname, value)
        # saving the field
        _GA(self, "save")(update_fields=[fname])

    obj = property(__get_obj, __set_obj)
    object = property(__get_obj, __set_obj)
