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

import traceback
from django.db import models
from django.conf import settings

from src.utils.idmapper.models import SharedMemoryModel
from src.typeclasses.models import Attribute, TypedObject, TypeNick, TypeNickHandler
from src.server.caches import get_field_cache, set_field_cache, del_field_cache
from src.server.caches import get_prop_cache, set_prop_cache, del_prop_cache, hashid
from src.typeclasses.typeclass import TypeClass
from src.players.models import PlayerNick
from src.objects.manager import ObjectManager
from src.commands.cmdsethandler import CmdSetHandler
from src.commands import cmdhandler
from src.scripts.scripthandler import ScriptHandler
from src.utils import logger
from src.utils.utils import make_iter, to_unicode, variable_from_module, inherits_from

from django.utils.translation import ugettext as _

#__all__ = ("ObjAttribute", "Alias", "ObjectNick", "ObjectDB")


_AT_SEARCH_RESULT = variable_from_module(*settings.SEARCH_AT_RESULT.rsplit('.', 1))

_GA = object.__getattribute__
_SA = object.__setattr__
_DA = object.__delattr__

_ME = _("me")
_SELF = _("self")
_HERE = _("here")

#------------------------------------------------------------
#
# ObjAttribute
#
#------------------------------------------------------------

class ObjAttribute(Attribute):
    "Attributes for ObjectDB objects."
    db_obj = models.ForeignKey("ObjectDB")

    class Meta:
        "Define Django meta options"
        verbose_name = "Object Attribute"
        verbose_name_plural = "Object Attributes"

#------------------------------------------------------------
#
# Alias
#
#------------------------------------------------------------

class Alias(SharedMemoryModel):
    """
    This model holds a range of alternate names for an object.
    These are intrinsic properties of the object. The split
    is so as to allow for effective global searches also by
    alias.
    """
    db_key = models.CharField('alias', max_length=255, db_index=True)
    db_obj = models.ForeignKey("ObjectDB", verbose_name='object')

    class Meta:
        "Define Django meta options"
        verbose_name = "Object alias"
        verbose_name_plural = "Object aliases"
    def __unicode__(self):
        return u"%s" % self.db_key
    def __str__(self):
        return str(self.db_key)



#------------------------------------------------------------
#
# Object Nicks
#
#------------------------------------------------------------

class ObjectNick(TypeNick):
    """

    The default nick types used by Evennia are:
    inputline (default) - match against all input
    player - match against player searches
    obj - match against object searches
    channel - used to store own names for channels
    """
    db_obj = models.ForeignKey("ObjectDB", verbose_name='object')

    class Meta:
        "Define Django meta options"
        verbose_name = "Nickname for Objects"
        verbose_name_plural = "Nicknames for Objects"
        unique_together = ("db_nick", "db_type", "db_obj")

class ObjectNickHandler(TypeNickHandler):
    """
    Handles nick access and setting. Accessed through ObjectDB.nicks
    """
    NickClass = ObjectNick


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
      player - optional connected player
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
    # These databse fields (including the inherited ones) are all set
    # using their corresponding properties, named same as the field,
    # but withtout the db_* prefix.

    # If this is a character object, the player is connected here.
    db_player = models.ForeignKey("players.PlayerDB", blank=True, null=True, verbose_name='player',
                                  help_text='a Player connected to this object, if any.')
    # The location in the game world. Since this one is likely
    # to change often, we set this with the 'location' property
    # to transparently handle Typeclassing.
    db_location = models.ForeignKey('self', related_name="locations_set",db_index=True,
                                     blank=True, null=True, verbose_name='game location')
    # a safety location, this usually don't change much.
    db_home = models.ForeignKey('self', related_name="homes_set",
                                 blank=True, null=True, verbose_name='home location')
    # destination of this object - primarily used by exits.
    db_destination = models.ForeignKey('self', related_name="destinations_set", db_index=True,
                                       blank=True, null=True, verbose_name='destination',
                                       help_text='a destination, used only by exit objects.')
    # database storage of persistant cmdsets.
    db_cmdset_storage = models.CharField('cmdset', max_length=255, null=True, blank=True,
                                         help_text="optional python path to a cmdset class.")

    # Database manager
    objects = ObjectManager()

    # Add the object-specific handlers

    def __init__(self, *args, **kwargs):
        "Parent must be initialized first."
        TypedObject.__init__(self, *args, **kwargs)
        # handlers
        _SA(self, "cmdset", CmdSetHandler(self))
        _GA(self, "cmdset").update(init_mode=True)
        _SA(self, "scripts", ScriptHandler(self))
        _SA(self, "nicks", ObjectNickHandler(self))
        # store the attribute class

    # Wrapper properties to easily set database fields. These are
    # @property decorators that allows to access these fields using
    # normal python operations (without having to remember to save()
    # etc). So e.g. a property 'attr' has a get/set/del decorator
    # defined that allows the user to do self.attr = value,
    # value = self.attr and del self.attr respectively (where self
    # is the object in question).

    # aliases property (wraps (db_aliases)
    #@property
    def __aliases_get(self):
        "Getter. Allows for value = self.aliases"
        aliases = get_prop_cache(self, "_aliases")
        if aliases == None:
            aliases = list(Alias.objects.filter(db_obj=self).values_list("db_key", flat=True))
            set_prop_cache(self, "_aliases", aliases)
        return aliases
    #@aliases.setter
    def __aliases_set(self, aliases):
        "Setter. Allows for self.aliases = value"
        for alias in make_iter(aliases):
            new_alias = Alias(db_key=alias, db_obj=self)
            new_alias.save()
        set_prop_cache(self, "_aliases", make_iter(aliases))
    #@aliases.deleter
    def __aliases_del(self):
        "Deleter. Allows for del self.aliases"
        for alias in Alias.objects.filter(db_obj=self):
            alias.delete()
        del_prop_cache(self, "_aliases")
    aliases = property(__aliases_get, __aliases_set, __aliases_del)

    # player property (wraps db_player)
    #@property
    def __player_get(self):
        """
        Getter. Allows for value = self.player.
        We have to be careful here since Player is also
        a TypedObject, so as to not create a loop.
        """
        return get_field_cache(self, "player")
    #@player.setter
    def __player_set(self, player):
        "Setter. Allows for self.player = value"
        if inherits_from(player, TypeClass):
            player = player.dbobj
        set_field_cache(self, "player", player)
    #@player.deleter
    def __player_del(self):
        "Deleter. Allows for del self.player"
        del_field_cache(self, "player")
    player = property(__player_get, __player_set, __player_del)

    # location property (wraps db_location)
    #@property
    def __location_get(self):
        "Getter. Allows for value = self.location."
        loc = get_field_cache(self, "location")
        if loc:
            return _GA(loc, "typeclass")
        return None
    #@location.setter
    def __location_set(self, location):
        "Setter. Allows for self.location = location"
        try:
            old_loc = _GA(self, "location")
            if ObjectDB.objects.dbref(location):
                # dbref search
                loc = ObjectDB.objects.dbref_search(location)
                loc = loc and _GA(loc, "dbobj")
            elif location and type(location) != ObjectDB:
                loc = _GA(location, "dbobj")
            else:
                loc = location

            # recursive location check
            def is_loc_loop(loc, depth=0):
                "Recursively traverse the target location to make sure we are not in it."
                if depth > 10: return
                elif loc == self: raise RuntimeError
                elif loc == None: raise RuntimeWarning # just to quickly get out
                return is_loc_loop(_GA(loc, "db_location"), depth+1)
            # check so we don't create a location loop - if so, RuntimeError will be raised.
            try: is_loc_loop(loc)
            except RuntimeWarning: pass

            # set the location
            set_field_cache(self, "location", loc)
            # update the contents of each location
            if old_loc:
                _GA(_GA(old_loc, "dbobj"), "contents_update")()
            if loc:
                _GA(loc, "contents_update")()
        except RuntimeError:
            string = "Cannot set location, "
            string += "%s.location = %s would create a location-loop." % (self.key, loc)
            _GA(self, "msg")(_(string))
            logger.log_trace(string)
            raise RuntimeError(string)
        except Exception, e:
            string = "Cannot set location (%s): " % str(e)
            string += "%s is not a valid location." % location
            _GA(self, "msg")(_(string))
            logger.log_trace(string)
            raise Exception(string)
    #@location.deleter
    def __location_del(self):
        "Deleter. Allows for del self.location"
        _GA(self, "location").contents_update()
        _SA(self, "db_location", None)
        _GA(self, "save")()
        del_field_cache(self, "location")
    location = property(__location_get, __location_set, __location_del)

    # home property (wraps db_home)
    #@property
    def __home_get(self):
        "Getter. Allows for value = self.home"
        home = get_field_cache(self, "home")
        if home:
            return _GA(home, "typeclass")
        return None
    #@home.setter
    def __home_set(self, home):
        "Setter. Allows for self.home = value"
        try:
            if home == None or type(home) == ObjectDB:
                hom = home
            elif ObjectDB.objects.dbref(home):
                hom = ObjectDB.objects.dbref_search(home)
                if hom and hasattr(hom,'dbobj'):
                    hom = _GA(hom, "dbobj")
                else:
                    hom = _GA(home, "dbobj")
            else:
                hom = _GA(home, "dbobj")
            set_field_cache(self, "home", hom)
        except Exception:
            string = "Cannot set home: "
            string += "%s is not a valid home."
            _GA(self, "msg")(_(string) % home)
            logger.log_trace(string)
            #raise
    #@home.deleter
    def __home_del(self):
        "Deleter. Allows for del self.home."
        _SA(self, "db_home", None)
        _GA(self, "save")()
        del_field_cache(self, "home")
    home = property(__home_get, __home_set, __home_del)

    # destination property (wraps db_destination)
    #@property
    def __destination_get(self):
        "Getter. Allows for value = self.destination."
        dest = get_field_cache(self, "destination")
        if dest:
            return _GA(dest, "typeclass")
        return None
    #@destination.setter
    def __destination_set(self, destination):
        "Setter. Allows for self.destination = destination"
        try:
            if destination == None or type(destination) == ObjectDB:
                # destination is None or a valid object
                dest = destination
            elif ObjectDB.objects.dbref(destination):
                # destination is a dbref; search
                dest = ObjectDB.objects.dbref_search(destination)
                if dest and _GA(self, "_hasattr")(dest,'dbobj'):
                    dest = _GA(dest, "dbobj")
                else:
                    dest = _GA(destination, "dbobj")
            else:
                dest = destination.dbobj
            set_field_cache(self, "destination", dest)
        except Exception:
            string = "Cannot set destination: "
            string += "%s is not a valid destination." % destination
            _GA(self, "msg")(string)
            logger.log_trace(string)
            raise
    #@destination.deleter
    def __destination_del(self):
        "Deleter. Allows for del self.destination"
        _SA(self, "db_destination", None)
        _GA(self, "save")()
        del_field_cache(self, "destination")
    destination = property(__destination_get, __destination_set, __destination_del)

    # cmdset_storage property.
    # This seems very sensitive to caching, so leaving it be for now. /Griatch
    #@property
    def __cmdset_storage_get(self):
        "Getter. Allows for value = self.name. Returns a list of cmdset_storage."
        if _GA(self, "db_cmdset_storage"):
            return [path.strip() for path  in _GA(self, "db_cmdset_storage").split(',')]
        return []
    #@cmdset_storage.setter
    def __cmdset_storage_set(self, value):
        "Setter. Allows for self.name = value. Stores as a comma-separated string."
        value = ",".join(str(val).strip() for val in make_iter(value))
        _SA(self, "db_cmdset_storage", value)
        _GA(self, "save")()
    #@cmdset_storage.deleter
    def __cmdset_storage_del(self):
        "Deleter. Allows for del self.name"
        _SA(self, "db_cmdset_storage", "")
        _GA(self, "save")()
    cmdset_storage = property(__cmdset_storage_get, __cmdset_storage_set, __cmdset_storage_del)

    class Meta:
        "Define Django meta options"
        verbose_name = "Object"
        verbose_name_plural = "Objects"

    #
    # ObjectDB class access methods/properties
    #

    # this is required to properly handle attributes and typeclass loading.
    _typeclass_paths = settings.OBJECT_TYPECLASS_PATHS
    _attribute_class = ObjAttribute
    _db_model_name = "objectdb" # used by attributes to safely store objects
    _default_typeclass_path = settings.BASE_OBJECT_TYPECLASS or "src.objects.objects.Object"

    #@property
    def __sessions_get(self):
        """
        Retrieve sessions connected to this object.
        """
        # if the player is not connected, this will simply be an empty list.
        if _GA(self, "player"):
            return _GA(_GA(self, "player"), "sessions")
        return []
    sessions = property(__sessions_get)

    #@property
    def __has_player_get(self):
        """
        Convenience function for checking if an active player is
        currently connected to this object
        """
        return any(_GA(self, "sessions"))
    has_player = property(__has_player_get)
    is_player = property(__has_player_get)

    #@property
    def __is_superuser_get(self):
        "Check if user has a player, and if so, if it is a superuser."
        return any(_GA(self, "sessions")) and _GA(_GA(self, "player"), "is_superuser")
    is_superuser = property(__is_superuser_get)

    # contents

    #@property
    def contents_get(self, exclude=None):
        """
        Returns the contents of this object, i.e. all
        objects that has this object set as its location.
        This should be publically available.

        exclude is one or more objects to not return
        """
        cont = get_prop_cache(self, "_contents")
        exclude = make_iter(exclude)
        if cont == None:
            cont = _GA(self, "contents_update")()
        return [obj for obj in cont if obj not in exclude]
    contents = property(contents_get)

    def contents_update(self):
        """
        Updates the contents property of the object with a new
        object Called by
        self.location_set.

        obj -
        remove (true/false) - remove obj from content list
        """
        cont = ObjectDB.objects.get_contents(self)
        set_prop_cache(self, "_contents", cont)
        return cont

    #@property
    def __exits_get(self):
        """
        Returns all exits from this object, i.e. all objects
        at this location having the property destination != None.
        """
        return [exi for exi in _GA(self, "contents")
                if exi.destination]
    exits = property(__exits_get)


    #
    # Main Search method
    #

    def search(self, ostring,
               global_search=False,
               global_dbref=False,
               attribute_name=None,
               use_nicks=False, location=None,
               player=False,
               ignore_errors=False, exact=False):
        """
        Perform a standard object search in the database, handling
        multiple results and lack thereof gracefully.

        ostring: (str) The string to match object names against.
                       Obs - To find a player, append * to the
                       start of ostring.
        global_search: Search all objects, not just the current
                       location/inventory. This is overruled if location keyword is given.
        global_dbref: Search globally -only- if a valid #dbref is given, otherwise local.
        attribute_name: (string) Which attribute to match (if None, uses default 'name')
        use_nicks : Use nickname replace (off by default)
        location : If None, use caller's current location, and caller.contents.
                   This can also be a list of locations
        player: return the Objects' controlling Player, instead, if available
        ignore_errors : Don't display any error messages even
                        if there are none/multiple matches -
                        just return the result as a list.
        exact:  Determines if the search must exactly match the key/alias of the
                given object or if partial matches the beginnings of one or more
                words in the name is enough. Exact matching is faster if using
                global search. Also, if attribute_name is set, matching is always exact.

        Returns - a unique Object/Player match or None. All error
                  messages are handled by system-commands and the parser-handlers
                  specified in settings.

        Use *<string> to search for objects controlled by a specific
        player. Note that the object controlled by the player will be
        returned, not the player object itself. This also means that
        this will not find Players without a character. Use the keyword
        player=True to find player objects.

        Note - for multiple matches, the engine accepts a number
        linked to the key in order to separate the matches from
        each other without showing the dbref explicitly. Default
        syntax for this is 'N-searchword'. So for example, if there
        are three objects in the room all named 'ball', you could
        address the individual ball as '1-ball', '2-ball', '3-ball'
        etc.
        """
        # handle some common self-references:
        if ostring == _HERE:
            return self.location
        if ostring in (_ME, _SELF, '*' + _ME, '*' + _SELF):
            return self


        if use_nicks:
            nick = None
            nicktype = "object"
            if player or ostring.startswith('*'):
                ostring = ostring.lstrip("*")
                nicktype = "player"
            # look up nicks
            nicks = ObjectNick.objects.filter(db_obj=self, db_type=nicktype)
            if self.has_player:
                nicks = list(nicks) + list(PlayerNick.objects.filter(db_obj=self.db_player, db_type=nicktype))
            for nick in nicks:
                if ostring == nick.db_nick:
                    ostring = nick.db_real
                    break

        candidates=None
        if global_search or (global_dbref and ostring.startswith("#")):
            # only allow exact matching if searching the entire database
            exact = True
        elif location:
            # location(s) were given
            candidates = []
            for obj in make_iter(location):
                candidates.extend([o.dbobj for o in obj.contents])
        else:
            # local search. Candidates are self.contents, self.location and self.location.contents
            location = self.location
            candidates = self.contents
            if location:
                candidates = candidates + [location] + location.contents
            else:
                candidates.append(self) # normally we are included in location.contents
            # db manager expects database objects
            candidates = [obj.dbobj for obj in candidates]

        results = ObjectDB.objects.object_search(ostring, caller=self,
                                                 attribute_name=attribute_name,
                                                 candidates=candidates,
                                                 exact=exact)
        if ignore_errors:
            return results
        result = _AT_SEARCH_RESULT(self, ostring, results, global_search)
        if player and result:
            return result.player
        return result


    #
    # Execution/action methods
    #

    def execute_cmd(self, raw_string):
        """
        Do something as this object. This command transparently
        lets its typeclass execute the command. Evennia also calls
        this method whenever the player sends a command on the command line.

        Argument:
        raw_string (string) - raw command input

        Returns Deferred - this is an asynchronous Twisted object that will
            not fire until the command has actually finished executing. To overload
            this one needs to attach callback functions to it, with addCallback(function).
            This function will be called with an eventual return value from the command
            execution.

            This return is not used at all by Evennia by default, but might be useful
            for coders intending to implement some sort of nested command structure.
        """
        # nick replacement - we require full-word matching.

        # do text encoding conversion
        raw_string = to_unicode(raw_string)

        raw_list = raw_string.split(None)
        raw_list = [" ".join(raw_list[:i+1]) for i in range(len(raw_list)) if raw_list[:i+1]]
        nicks = ObjectNick.objects.filter(db_obj=self, db_type__in=("inputline", "channel"))
        if self.has_player:
            nicks = list(nicks) + list(PlayerNick.objects.filter(db_obj=self.db_player, db_type__in=("inputline","channel")))
        for nick in nicks:
            if nick.db_nick in raw_list:
                raw_string = raw_string.replace(nick.db_nick, nick.db_real, 1)
                break
        return cmdhandler.cmdhandler(_GA(self, "typeclass"), raw_string)

    def msg(self, message, from_obj=None, data=None):
        """
        Emits something to any sessions attached to the object.

        message (str): The message to send
        from_obj (obj): object that is sending.
        data (object): an optional data object that may or may not
                       be used by the protocol.
        """
        if _GA(self, 'player'):
            # note that we check the typeclass' msg, otherwise one couldn't overload it.
            _GA(_GA(self, 'player'), "typeclass").msg(message, from_obj=from_obj, data=data)

    def emit_to(self, message, from_obj=None, data=None):
        "Deprecated. Alias for msg"
        logger.log_depmsg("emit_to() is deprecated. Use msg() instead.")
        _GA(self, "msg")(message, from_obj, data)

    def msg_contents(self, message, exclude=None, from_obj=None, data=None):
        """
        Emits something to all objects inside an object.

        exclude is a list of objects not to send to. See self.msg() for more info.
        """
        contents = _GA(self, "contents")
        if exclude:
            exclude = make_iter(exclude)
            contents = [obj for obj in contents
                        if (obj not in exclude and obj not in exclude)]
        for obj in contents:
            obj.msg(message, from_obj=from_obj, data=data)

    def emit_to_contents(self, message, exclude=None, from_obj=None, data=None):
        "Deprecated. Alias for msg_contents"
        logger.log_depmsg("emit_to_contents() is deprecated. Use msg_contents() instead.")
        self.msg_contents(message, exclude=exclude, from_obj=from_obj, data=data)

    def move_to(self, destination, quiet=False,
                emit_to_obj=None, use_destination=True, to_none=False):
        """
        Moves this object to a new location.

        Moves this object to a new location. Note that if <destination> is an
        exit object (i.e. it has "destination"!=None), the move_to will
        happen to this destination and -not- into the exit object itself, unless
        use_destination=False. Note that no lock checks are done by this function,
        such things are assumed to have been handled before calling move_to.

        destination: (Object) Reference to the object to move to. This
                     can also be an exit object, in which case the destination
                     property is used as destination.
        quiet:  (bool)    If true, don't emit left/arrived messages.
        emit_to_obj: (Object) object to receive error messages
        use_destination (bool): Default is for objects to use the "destination" property
                              of destinations as the target to move to. Turning off this
                              keyword allows objects to move "inside" exit objects.
        to_none - allow destination to be None. Note that no hooks are run when moving
                      to a None location. If you want to run hooks, run them manually.

        Returns True/False depending on if there were problems with the move. This method
                may also return various error messages to the emit_to_obj.
        """
        def logerr(string=""):
            trc = traceback.format_exc()
            errstring = "%s%s" % (trc, string)
            logger.log_trace()
            _GA(self, "msg")(errstring)

        errtxt = _("Couldn't perform move ('%s'). Contact an admin.")
        if not emit_to_obj:
            emit_to_obj = self

        if not destination:
            if to_none:
                # immediately move to None. There can be no hooks called since
                # there is no destination to call them with.
                self.location = None
                return True
            emit_to_obj.msg(_("The destination doesn't exist."))
            return
        if destination.destination and use_destination:
            # traverse exits
            destination = destination.destination

        # Before the move, call eventual pre-commands.
        try:
            if not self.at_before_move(destination):
                return
        except Exception:
            logerr(errtxt % "at_before_move()")
            #emit_to_obj.msg(errtxt % "at_before_move()")
            #logger.log_trace()
            return False

        # Save the old location
        source_location = _GA(self, "location")
        if not source_location:
            # there was some error in placing this room.
            # we have to set one or we won't be able to continue
            if _GA(self, "home"):
                source_location = _GA(self, "home")
            else:
                default_home = ObjectDB.objects.get_id(settings.CHARACTER_DEFAULT_HOME)
                source_location = default_home

        # Call hook on source location
        try:
            source_location.at_object_leave(self, destination)
        except Exception:
            logerr(errtxt % "at_object_leave()")
            #emit_to_obj.msg(errtxt % "at_object_leave()")
            #logger.log_trace()
            return False

        if not quiet:
            #tell the old room we are leaving
            try:
                self.announce_move_from(destination)
            except Exception:
                logerr(errtxt % "at_announce_move()")
                #emit_to_obj.msg(errtxt % "at_announce_move()" )
                #logger.log_trace()
                return False

        # Perform move
        try:
            _SA(self, "location", destination)
        except Exception:
            emit_to_obj.msg(errtxt % "location change")
            logger.log_trace()
            return False

        if not quiet:
            # Tell the new room we are there.
            try:
                self.announce_move_to(source_location)
            except Exception:
                logerr(errtxt % "announce_move_to()")
                #emit_to_obj.msg(errtxt % "announce_move_to()")
                #logger.log_trace()
                return  False

        # Perform eventual extra commands on the receiving location
        # (the object has already arrived at this point)
        try:
            destination.at_object_receive(self, source_location)
        except Exception:
            logerr(errtxt % "at_object_receive()")
            #emit_to_obj.msg(errtxt % "at_object_receive()")
            #logger.log_trace()
            return False

        # Execute eventual extra commands on this object after moving it
        # (usually calling 'look')
        try:
            self.at_after_move(source_location)
        except Exception:
            logerr(errtxt % "at_after_move")
            #emit_to_obj.msg(errtxt % "at_after_move()")
            #logger.log_trace()
            return False
        return True

    #
    # Object Swap, Delete and Cleanup methods
    #

    def clear_exits(self):
        """
        Destroys all of the exits and any exits pointing to this
        object as a destination.
        """
        for out_exit in [exi for exi in ObjectDB.objects.get_contents(self) if exi.db_destination]:
            out_exit.delete()
        for in_exit in ObjectDB.objects.filter(db_destination=self):
            in_exit.delete()

    def clear_contents(self):
        """
        Moves all objects (players/things) to their home
        location or to default home.
        """
        # Gather up everything that thinks this is its location.
        objs = ObjectDB.objects.filter(db_location=self)
        default_home_id = int(settings.CHARACTER_DEFAULT_HOME.lstrip("#"))
        try:
            default_home = ObjectDB.objects.get(id=default_home_id)
            if default_home.dbid == _GA(self, "dbid"):
                # we are deleting default home!
                default_home = None
        except Exception:
            string = _("Could not find default home '(#%d)'.")
            logger.log_errmsg(string % default_home_id)
            default_home = None

        for obj in objs:
            home = obj.home
            # Obviously, we can't send it back to here.
            if not home or (home and home.dbid == _GA(self, "dbid")):
                obj.home = default_home

            # If for some reason it's still None...
            if not obj.home:
                string = "Missing default home, '%s(#%d)' "
                string += "now has a null location."
                obj.location = None
                obj.msg(_("Something went wrong! You are dumped into nowhere. Contact an admin."))
                logger.log_errmsg(string % (obj.name, obj.dbid))
                return

            if obj.has_player:
                if home:
                    string = "Your current location has ceased to exist,"
                    string += " moving you to %s(#%d)."
                    obj.msg(_(string) % (home.name, home.dbid))
                else:
                    # Famous last words: The player should never see this.
                    string = "This place should not exist ... contact an admin."
                    obj.msg(_(string))
            obj.move_to(home)

    def copy(self, new_key=None):
        """
        Makes an identical copy of this object. If you want to customize the copy by
        changing some settings, use ObjectDB.object.copy_object() directly.

        new_key (string) - new key/name of copied object. If new_key is not specified, the copy will be named
                           <old_key>_copy by default.
        Returns: Object (copy of this one)
        """
        def find_clone_key():
            """
            Append 01, 02 etc to obj.key. Checks next higher number in the
            same location, then adds the next number available

            returns the new clone name on the form keyXX
            """
            key = _GA(self, "key")
            num = 1
            for obj in (obj for obj in self.location.contents
                        if obj.key.startswith(key) and obj.key.lstrip(key).isdigit()):
                num += 1
            return "%s%03i" % (key, num)
        new_key = new_key or find_clone_key()
        return ObjectDB.objects.copy_object(self, new_key=new_key)

    delete_iter = 0
    def delete(self):
        """
        Deletes this object.
        Before deletion, this method makes sure to move all contained
        objects to their respective home locations, as well as clean
        up all exits to/from the object.
        """
        if _GA(self, "delete_iter") > 0:
            # make sure to only call delete once on this object
            # (avoid recursive loops)
            return False

        if not self.at_object_delete():
            # this is an extra pre-check
            # run before deletion mechanism
            # is kicked into gear.
            _SA(self, "delete_iter", 0)
            return False

        self.delete_iter += 1

        # See if we need to kick the player off.

        for session in _GA(self, "sessions"):
            session.msg(_("Your character %s has been destroyed.") % _GA(self, "key"))
            # no need to disconnect, Player just jumps to OOC mode.
        # sever the connection (important!)
        if _GA(self, 'player'):
            _SA(_GA(self, "player"), "character", None)
        _SA(self, "player", None)

        for script in _GA(self, "scripts").all():
            script.stop()

        # if self.player:
        #     self.player.user.is_active = False
        #     self.player.user.save(

        # Destroy any exits to and from this room, if any
        _GA(self, "clear_exits")()
        # Clear out any non-exit objects located within the object
        _GA(self, "clear_contents")()
        old_loc = _GA(self, "location")
        # Perform the deletion of the object
        super(ObjectDB, self).delete()
        # clear object's old  location's content cache of this object
        if old_loc:
            old_loc.contents_update()
        return True
