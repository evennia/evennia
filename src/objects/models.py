"""
This module defines the database models for all in-game objects, that
is, all objects that has an actual existence in-game.

Each database object is 'decorated' with a 'typeclass', a normal
python class that implements all the various logics needed by the game
in question. Objects created of this class transparently communicate
with its related database object for storing all attributes. The
admin should usually not have to deal directly with this database
object layer.

Attributes are separate objects that store values persistently onto
the database object. Like everything else, they can be accessed
transparently through the decorating TypeClass.
"""

from django.db import models
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from src.typeclasses.models import TypedObject
from src.objects.manager import ObjectDBManager
from src.utils import logger
from src.utils.utils import (make_iter, dbref)


#------------------------------------------------------------
#
# ObjectDB
#
#------------------------------------------------------------

class ObjectDB(TypedObject):
    """
    All objects in the game use the ObjectDB model to store
    data in the database. This is handled transparently through
    the typeclass system.

    Note that the base objectdb is very simple, with
    few defined fields. Use attributes to extend your
    type class with new database-stored variables.

    The TypedObject supplies the following (inherited) properties:
      key - main name
      name - alias for key
      typeclass_path - the path to the decorating typeclass
      typeclass - auto-linked typeclass
      date_created - time stamp of object creation
      permissions - perm strings
      locks - lock definitions (handler)
      dbref - #id of object
      db - persistent attribute storage
      ndb - non-persistent attribute storage

    The ObjectDB adds the following properties:
      player - optional connected player (always together with sessid)
      sessid - optional connection session id (always together with player)
      location - in-game location of object
      home - safety location for object (handler)

      scripts - scripts assigned to object (handler from typeclass)
      cmdset - active cmdset on object (handler from typeclass)
      aliases - aliases for this object (property)
      nicks - nicknames for *other* things in Evennia (handler)
      sessions - sessions connected to this object (see also player)
      has_player - bool if an active player is currently connected
      contents - other objects having this object as location
      exits - exits from this object
    """
    #
    # ObjectDB Database model setup
    #
    #
    # inherited fields (from TypedObject):
    # db_key (also 'name' works), db_typeclass_path, db_date_created,
    # db_permissions
    #
    # These databse fields (including the inherited ones) should normally be
    # managed by their corresponding wrapper properties, named same as the
    # field, but without the db_* prefix (e.g. the db_key field is set with
    # self.key instead). The wrappers are created at the metaclass level and
    # will automatically save and cache the data more efficiently.

    # If this is a character object, the player is connected here.
    db_player = models.ForeignKey("players.PlayerDB", null=True, verbose_name='player', on_delete=models.SET_NULL,
                                  help_text='a Player connected to this object, if any.')
    # the session id associated with this player, if any
    db_sessid = models.CommaSeparatedIntegerField(null=True, max_length=32, verbose_name="session id",
                                    help_text="csv list of session ids of connected Player, if any.")
    # The location in the game world. Since this one is likely
    # to change often, we set this with the 'location' property
    # to transparently handle Typeclassing.
    db_location = models.ForeignKey('self', related_name="locations_set", db_index=True, on_delete=models.SET_NULL,
                                     blank=True, null=True, verbose_name='game location')
    # a safety location, this usually don't change much.
    db_home = models.ForeignKey('self', related_name="homes_set", on_delete=models.SET_NULL,
                                 blank=True, null=True, verbose_name='home location')
    # destination of this object - primarily used by exits.
    db_destination = models.ForeignKey('self', related_name="destinations_set", db_index=True, on_delete=models.SET_NULL,
                                       blank=True, null=True, verbose_name='destination',
                                       help_text='a destination, used only by exit objects.')
    # database storage of persistant cmdsets.
    db_cmdset_storage = models.CharField('cmdset', max_length=255, null=True, blank=True,
                                         help_text="optional python path to a cmdset class.")

    # Database manager
    objects = ObjectDBManager()

    # cmdset_storage property handling
    def __cmdset_storage_get(self):
        "getter"
        storage = self.db_cmdset_storage
        return [path.strip() for path in storage.split(',')] if storage else []

    def __cmdset_storage_set(self, value):
        "setter"
        self.db_cmdset_storage =  ",".join(str(val).strip() for val in make_iter(value))
        self.save(update_fields=["db_cmdset_storage"])

    def __cmdset_storage_del(self):
        "deleter"
        self.db_cmdset_storage = None
        self.save(update_fields=["db_cmdset_storage"])
    cmdset_storage = property(__cmdset_storage_get, __cmdset_storage_set, __cmdset_storage_del)

    # location getsetter
    def __location_get(self):
        "Get location"
        return self.db_location

    def __location_set(self, location):
        "Set location, checking for loops and allowing dbref"
        if isinstance(location, (basestring, int)):
            # allow setting of #dbref
            dbid = dbref(location, reqhash=False)
            if dbid:
                try:
                    location = ObjectDB.objects.get(id=dbid)
                except ObjectDoesNotExist:
                    # maybe it is just a name that happens to look like a dbid
                    pass
        try:
            def is_loc_loop(loc, depth=0):
                "Recursively traverse target location, trying to catch a loop."
                if depth > 10:
                    return
                elif loc == self:
                    raise RuntimeError
                elif loc == None:
                    raise RuntimeWarning
                return is_loc_loop(loc.db_location, depth + 1)
            try:
                is_loc_loop(location)
            except RuntimeWarning:
                pass
            # actually set the field
            self.db_location = location
            self.save(update_fields=["db_location"])
        except RuntimeError:
            errmsg = "Error: %s.location = %s creates a location loop." % (self.key, location)
            logger.log_errmsg(errmsg)
            raise RuntimeError(errmsg)
        except Exception, e:
            errmsg = "Error (%s): %s is not a valid location." % (str(e), location)
            logger.log_errmsg(errmsg)
            raise Exception(errmsg)

    def __location_del(self):
        "Cleanly delete the location reference"
        self.db_location = None
        self.save(update_fields=["db_location"])
    location = property(__location_get, __location_set, __location_del)

    class Meta:
        "Define Django meta options"
        verbose_name = "Object"
        verbose_name_plural = "Objects"

