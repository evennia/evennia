"""
Scripts are entities that perform some sort of action, either only
once or repeatedly. They can be directly linked to a particular
Evennia Object or be stand-alonw (in the latter case it is considered
a 'global' script). Scripts can indicate both actions related to the
game world as well as pure behind-the-scenes events and
effects. Everything that has a time component in the game (i.e. is not
hard-coded at startup or directly created/controlled by players) is
handled by Scripts.

Scripts have to check for themselves that they should be applied at a
particular moment of time; this is handled by the is_valid() hook.
Scripts can also implement at_start and at_end hooks for preparing and
cleaning whatever effect they have had on the game object.

Common examples of uses of Scripts:
- load the default cmdset to the player object's cmdhandler
  when logging in.
- switch to a different state, such as entering a text editor,
  start combat or enter a dark room.
- Weather patterns in-game
- merge a new cmdset with the default one for changing which
  commands are available at a particular time
- give the player/object a time-limited bonus/effect

"""
from django.conf import settings
from django.db import models
from src.typeclasses.models import Attribute, TypedObject
from django.contrib.contenttypes.models import ContentType
from src.scripts.manager import ScriptManager

__all__ = ("ScriptAttribute", "ScriptDB")

#------------------------------------------------------------
#
# ScriptAttribute
#
#------------------------------------------------------------

class ScriptAttribute(Attribute):
    "Attributes for ScriptDB objects."
    db_obj = models.ForeignKey("ScriptDB", verbose_name='script')

    class Meta:
        "Define Django meta options"
        verbose_name = "Script Attribute"
        verbose_name_plural = "Script Attributes"


#------------------------------------------------------------
#
# ScriptDB
#
#------------------------------------------------------------

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
      interval - how often script should run
      start_delay - if the script should start repeating right away
      repeats - how many times the script should repeat
      persistent - if script should survive a server reboot
      is_active - bool if script is currently running

    """


    #
    # ScriptDB Database Model setup
    #
    # These databse fields are all set using their corresponding properties,
    # named same as the field, but withtou the db_* prefix.

    # inherited fields (from TypedObject):
    # db_key, db_typeclass_path, db_date_created, db_permissions

    # optional description.
    db_desc = models.CharField('desc', max_length=255, blank=True)
    # A reference to the database object affected by this Script, if any.
    db_obj = models.ForeignKey("objects.ObjectDB", null=True, blank=True, verbose_name='scripted object',
                               help_text='the object to store this script on, if not a global script.')
    # how often to run Script (secs). -1 means there is no timer
    db_interval = models.IntegerField('interval', default=-1, help_text='how often to repeat script, in seconds. -1 means off.')
    # start script right away or wait interval seconds first
    db_start_delay = models.BooleanField('start delay', default=False, help_text='pause interval seconds before starting.')
    # how many times this script is to be repeated, if interval!=0.
    db_repeats = models.IntegerField('number of repeats', default=0, help_text='0 means off.')
    # defines if this script should survive a reboot or not
    db_persistent = models.BooleanField('survive server reboot', default=False)
    # defines if this script has already been started in this session
    db_is_active = models.BooleanField('script active', default=False)

    # Database manager
    objects = ScriptManager()

    class Meta:
        "Define Django meta options"
        verbose_name = "Script"

    # Wrapper properties to easily set database fields. These are
    # @property decorators that allows to access these fields using
    # normal python operations (without having to remember to save()
    # etc). So e.g. a property 'attr' has a get/set/del decorator
    # defined that allows the user to do self.attr = value,
    # value = self.attr and del self.attr respectively (where self
    # is the script in question).

    # desc property (wraps db_desc)
    #@property
    def __desc_get(self):
        "Getter. Allows for value = self.desc"
        return self.db_desc
    #@desc.setter
    def __desc_set(self, value):
        "Setter. Allows for self.desc = value"
        self.db_desc = value
        self.save()
    #@desc.deleter
    def __desc_del(self):
        "Deleter. Allows for del self.desc"
        self.db_desc = ""
        self.save()
    desc = property(__desc_get, __desc_set, __desc_del)

    # obj property (wraps db_obj)
    #@property
    def __obj_get(self):
        "Getter. Allows for value = self.obj"
        return self.db_obj
    #@obj.setter
    def __obj_set(self, value):
        "Setter. Allows for self.obj = value"
        self.db_obj = value
        self.save()
    #@obj.deleter
    def __obj_del(self):
        "Deleter. Allows for del self.obj"
        self.db_obj = None
        self.save()
    obj = property(__obj_get, __obj_set, __obj_del)

    # interval property (wraps db_interval)
    #@property
    def __interval_get(self):
        "Getter. Allows for value = self.interval"
        return self.db_interval
    #@interval.setter
    def __interval_set(self, value):
        "Setter. Allows for self.interval = value"
        self.db_interval = int(value)
        self.save()
    #@interval.deleter
    def __interval_del(self):
        "Deleter. Allows for del self.interval"
        self.db_interval = 0
        self.save()
    interval = property(__interval_get, __interval_set, __interval_del)

    # start_delay property (wraps db_start_delay)
    #@property
    def __start_delay_get(self):
        "Getter. Allows for value = self.start_delay"
        return self.db_start_delay
    #@start_delay.setter
    def __start_delay_set(self, value):
        "Setter. Allows for self.start_delay = value"
        self.db_start_delay = value
        self.save()
    #@start_delay.deleter
    def __start_delay_del(self):
        "Deleter. Allows for del self.start_delay"
        self.db_start_delay = False
        self.save()
    start_delay = property(__start_delay_get, __start_delay_set, __start_delay_del)

    # repeats property (wraps db_repeats)
    #@property
    def __repeats_get(self):
        "Getter. Allows for value = self.repeats"
        return self.db_repeats
    #@repeats.setter
    def __repeats_set(self, value):
        "Setter. Allows for self.repeats = value"
        self.db_repeats = int(value)
        self.save()
    #@repeats.deleter
    def __repeats_del(self):
        "Deleter. Allows for del self.repeats"
        self.db_repeats = 0
        self.save()
    repeats = property(__repeats_get, __repeats_set, __repeats_del)

    # persistent property (wraps db_persistent)
    #@property
    def __persistent_get(self):
        "Getter. Allows for value = self.persistent"
        return self.db_persistent
    #@persistent.setter
    def __persistent_set(self, value):
        "Setter. Allows for self.persistent = value"
        self.db_persistent = value
        self.save()
    #@persistent.deleter
    def __persistent_del(self):
        "Deleter. Allows for del self.persistent"
        self.db_persistent = False
        self.save()
    persistent = property(__persistent_get, __persistent_set, __persistent_del)

    # is_active property (wraps db_is_active)
    #@property
    def __is_active_get(self):
        "Getter. Allows for value = self.is_active"
        return self.db_is_active
    #@is_active.setter
    def __is_active_set(self, value):
        "Setter. Allows for self.is_active = value"
        self.db_is_active = value
        self.save()
    #@is_active.deleter
    def __is_active_del(self):
        "Deleter. Allows for del self.is_active"
        self.db_is_active = False
        self.save()
    is_active = property(__is_active_get, __is_active_set, __is_active_del)

    #
    #
    # ScriptDB class properties
    #
    #

    # this is required to properly handle attributes and typeclass loading
    _typeclass_paths = settings.SCRIPT_TYPECLASS_PATHS
    _attribute_class = ScriptAttribute
    _db_model_name = "scriptdb" # used by attributes to safely store objects
    _default_typeclass_path = settings.BASE_SCRIPT_TYPECLASS or "src.scripts.scripts.DoNothing"

    def at_typeclass_error(self):
        """
        If this is called, it means the typeclass has a critical
        error and cannot even be loaded. We don't allow a script
        to be created under those circumstances. Already created,
        permanent scripts are set to already be active so they
        won't get activated now (next reboot the bug might be fixed)
        """
        # By setting is_active=True, we trick the script not to run "again".
        self.is_active = True
        return super(ScriptDB, self).at_typeclass_error()

    delete_iter = 0
    def delete(self):
        if self.delete_iter > 0:
            return
        self.delete_iter += 1
        super(ScriptDB, self).delete()
