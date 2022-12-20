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
from collections import defaultdict

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import validate_comma_separated_integer_list
from django.db import models

from evennia.objects.manager import ObjectDBManager
from evennia.typeclasses.models import TypedObject
from evennia.utils import logger
from evennia.utils.utils import dbref, lazy_property, make_iter


class ContentsHandler:
    """
    Handles and caches the contents of an object to avoid excessive
    lookups (this is done very often due to cmdhandler needing to look
    for object-cmdsets). It is stored on the 'contents_cache' property
    of the ObjectDB.
    """

    def __init__(self, obj):
        """
        Sets up the contents handler.

        Args:
            obj (Object):  The object on which the
                handler is defined

        Notes:
            This was changed from using `set` to using `dict` internally
            in order to retain insertion order.

        """
        self.obj = obj
        self._pkcache = {}
        self._idcache = obj.__class__.__instance_cache__
        self._typecache = defaultdict(dict)
        self.init()

    def load(self):
        """
        Retrieves all objects from database. Used for initializing.

        Returns:
            Objects (list of ObjectDB)
        """
        return list(self.obj.locations_set.all())

    def init(self):
        """
        Re-initialize the content cache

        """
        objects = self.load()
        self._pkcache = {obj.pk: True for obj in objects}
        for obj in objects:
            for ctype in obj._content_types:
                self._typecache[ctype][obj.pk] = True

    def get(self, exclude=None, content_type=None):
        """
        Return the contents of the cache.

        Args:
            exclude (Object or list of Object): object(s) to ignore
            content_type (str or None): Filter list by a content-type. If None, don't filter.

        Returns:
            objects (list): the Objects inside this location

        """
        if content_type is not None:
            pks = self._typecache[content_type].keys()
        else:
            pks = self._pkcache.keys()
        if exclude:
            pks = set(pks) - {excl.pk for excl in make_iter(exclude)}
        try:
            return [self._idcache[pk] for pk in pks]
        except KeyError:
            # this can happen if the idmapper cache was cleared for an object
            # in the contents cache. If so we need to re-initialize and try again.
            self.init()
            try:
                return [self._idcache[pk] for pk in pks]
            except KeyError:
                # this means an actual failure of caching. Return real database match.
                logger.log_err("contents cache failed for %s." % self.obj.key)
                return self.load()

    def add(self, obj):
        """
        Add a new object to this location

        Args:
            obj (Object): object to add

        """
        self._pkcache[obj.pk] = obj
        for ctype in obj._content_types:
            self._typecache[ctype][obj.pk] = True

    def remove(self, obj):
        """
        Remove object from this location

        Args:
            obj (Object): object to remove

        """
        self._pkcache.pop(obj.pk, None)
        for ctype in obj._content_types:
            if obj.pk in self._typecache[ctype]:
                self._typecache[ctype].pop(obj.pk, None)

    def clear(self):
        """
        Clear the contents cache and re-initialize

        """
        self._pkcache = {}
        self._typecache = defaultdict(dict)
        self.init()


# -------------------------------------------------------------
#
# ObjectDB
#
# -------------------------------------------------------------


class ObjectDB(TypedObject):
    """
    All objects in the game use the ObjectDB model to store
    data in the database. This is handled transparently through
    the typeclass system.

    Note that the base objectdb is very simple, with
    few defined fields. Use attributes to extend your
    type class with new database-stored variables.

    The TypedObject supplies the following (inherited) properties:

      - key - main name
      - name - alias for key
      - db_typeclass_path - the path to the decorating typeclass
      - db_date_created - time stamp of object creation
      - permissions - perm strings
      - locks - lock definitions (handler)
      - dbref - #id of object
      - db - persistent attribute storage
      - ndb - non-persistent attribute storage

    The ObjectDB adds the following properties:

      - account - optional connected account (always together with sessid)
      - sessid - optional connection session id (always together with account)
      - location - in-game location of object
      - home - safety location for object (handler)
      - scripts - scripts assigned to object (handler from typeclass)
      - cmdset - active cmdset on object (handler from typeclass)
      - aliases - aliases for this object (property)
      - nicks - nicknames for *other* things in Evennia (handler)
      - sessions - sessions connected to this object (see also account)
      - has_account - bool if an active account is currently connected
      - contents - other objects having this object as location
      - exits - exits from this object

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

    # If this is a character object, the account is connected here.
    db_account = models.ForeignKey(
        "accounts.AccountDB",
        null=True,
        verbose_name="account",
        on_delete=models.SET_NULL,
        help_text="an Account connected to this object, if any.",
    )

    # the session id associated with this account, if any
    db_sessid = models.CharField(
        null=True,
        max_length=32,
        validators=[validate_comma_separated_integer_list],
        verbose_name="session id",
        help_text="csv list of session ids of connected Account, if any.",
    )
    # The location in the game world. Since this one is likely
    # to change often, we set this with the 'location' property
    # to transparently handle Typeclassing.
    db_location = models.ForeignKey(
        "self",
        related_name="locations_set",
        db_index=True,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name="game location",
    )
    # a safety location, this usually don't change much.
    db_home = models.ForeignKey(
        "self",
        related_name="homes_set",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name="home location",
    )
    # destination of this object - primarily used by exits.
    db_destination = models.ForeignKey(
        "self",
        related_name="destinations_set",
        db_index=True,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name="destination",
        help_text="a destination, used only by exit objects.",
    )
    # database storage of persistant cmdsets.
    db_cmdset_storage = models.CharField(
        "cmdset",
        max_length=255,
        null=True,
        blank=True,
        help_text="optional python path to a cmdset class.",
    )

    # Database manager
    objects = ObjectDBManager()

    # defaults
    __settingsclasspath__ = settings.BASE_OBJECT_TYPECLASS
    __defaultclasspath__ = "evennia.objects.objects.DefaultObject"
    __applabel__ = "objects"

    @lazy_property
    def contents_cache(self):
        return ContentsHandler(self)

    # cmdset_storage property handling
    def __cmdset_storage_get(self):
        """getter"""
        storage = self.db_cmdset_storage
        return [path.strip() for path in storage.split(",")] if storage else []

    def __cmdset_storage_set(self, value):
        """setter"""
        self.db_cmdset_storage = ",".join(str(val).strip() for val in make_iter(value))
        self.save(update_fields=["db_cmdset_storage"])

    def __cmdset_storage_del(self):
        """deleter"""
        self.db_cmdset_storage = None
        self.save(update_fields=["db_cmdset_storage"])

    cmdset_storage = property(__cmdset_storage_get, __cmdset_storage_set, __cmdset_storage_del)

    # location getsetter
    def __location_get(self):
        """Get location"""
        return self.db_location

    def __location_set(self, location):
        """Set location, checking for loops and allowing dbref"""
        if isinstance(location, (str, int)):
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
                """Recursively traverse target location, trying to catch a loop."""
                if depth > 10:
                    return None
                elif loc == self:
                    raise RuntimeError
                elif loc is None:
                    raise RuntimeWarning
                return is_loc_loop(loc.db_location, depth + 1)

            try:
                is_loc_loop(location)
            except RuntimeWarning:
                # we caught an infinite location loop!
                # (location1 is in location2 which is in location1 ...)
                pass

            # if we get to this point we are ready to change location

            old_location = self.db_location

            # this is checked in _db_db_location_post_save below
            self._safe_contents_update = True

            # actually set the field (this will error if location is invalid)
            self.db_location = location
            self.save(update_fields=["db_location"])

            # remove the safe flag
            del self._safe_contents_update

            # update the contents cache
            if old_location:
                old_location.contents_cache.remove(self)
            if self.db_location:
                self.db_location.contents_cache.add(self)

        except RuntimeError:
            errmsg = "Error: %s.location = %s creates a location loop." % (self.key, location)
            raise RuntimeError(errmsg)
        except Exception:
            # raising here gives more info for now
            raise
            # errmsg = "Error (%s): %s is not a valid location." % (str(e), location)
            # raise RuntimeError(errmsg)
        return

    def __location_del(self):
        """Cleanly delete the location reference"""
        self.db_location = None
        self.save(update_fields=["db_location"])

    location = property(__location_get, __location_set, __location_del)

    def at_db_location_postsave(self, new):
        """
        This is called automatically after the location field was
        saved, no matter how. It checks for a variable
        _safe_contents_update to know if the save was triggered via
        the location handler (which updates the contents cache) or
        not.

        Args:
            new (bool): Set if this location has not yet been saved before.

        """
        if not hasattr(self, "_safe_contents_update"):
            # changed/set outside of the location handler
            if new:
                # if new, there is no previous location to worry about
                if self.db_location:
                    self.db_location.contents_cache.add(self)
            else:
                # Since we cannot know at this point was old_location was, we
                # trigger a full-on contents_cache update here.
                logger.log_warn(
                    "db_location direct save triggered contents_cache.init() for all objects!"
                )
                [o.contents_cache.init() for o in self.__dbclass__.get_all_cached_instances()]

    class Meta:
        """Define Django meta options"""

        verbose_name = "Object"
        verbose_name_plural = "Objects"
