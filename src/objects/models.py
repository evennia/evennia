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
from django.contrib.contenttypes.models import ContentType

from src.utils.idmapper.models import SharedMemoryModel
from src.typeclasses.models import Attribute, TypedObject, TypeNick, TypeNickHandler
from src.typeclasses.typeclass import TypeClass
from src.objects.manager import ObjectManager
from src.players.models import PlayerDB
from src.server.models import ServerConfig
from src.commands.cmdsethandler import CmdSetHandler
from src.commands import cmdhandler
from src.scripts.scripthandler import ScriptHandler
from src.utils import logger
from src.utils.utils import is_iter, to_unicode, to_str, mod_import

#PlayerDB = ContentType.objects.get(app_label="players", model="playerdb").model_class()

AT_SEARCH_RESULT = mod_import(*settings.SEARCH_AT_RESULT.rsplit('.', 1))

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
        self.cmdset = CmdSetHandler(self)
        self.cmdset.update(init_mode=True)
        self.scripts = ScriptHandler(self)
        self.nicks = ObjectNickHandler(self)    
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
    def aliases_get(self):
        "Getter. Allows for value = self.aliases"
        return list(Alias.objects.filter(db_obj=self).values_list("db_key", flat=True))
    #@aliases.setter
    def aliases_set(self, aliases):
        "Setter. Allows for self.aliases = value"        
        if not is_iter(aliases):
            aliases = [aliases]            
        for alias in aliases:
            new_alias = Alias(db_key=alias, db_obj=self)
            new_alias.save()
    #@aliases.deleter
    def aliases_del(self):
        "Deleter. Allows for del self.aliases"
        for alias in Alias.objects.filter(db_obj=self):
            alias.delete()
    aliases = property(aliases_get, aliases_set, aliases_del)

    # player property (wraps db_player)
    #@property
    def player_get(self):
        """
        Getter. Allows for value = self.player.
        We have to be careful here since Player is also
        a TypedObject, so as to not create a loop.
        """
        try:
            return object.__getattribute__(self, 'db_player')
        except AttributeError:
            return None 
    #@player.setter
    def player_set(self, player):
        "Setter. Allows for self.player = value"
        if isinstance(player, TypeClass):
            player = player.dbobj
        self.db_player = player 
        self.save()
    #@player.deleter
    def player_del(self):
        "Deleter. Allows for del self.player"
        self.db_player = None
        self.save()
    player = property(player_get, player_set, player_del)

    # location property (wraps db_location)
    #@property 
    def location_get(self):
        "Getter. Allows for value = self.location."
        loc = self.db_location
        if loc:
            return loc.typeclass
        return None 
    #@location.setter
    def location_set(self, location):
        "Setter. Allows for self.location = location"
        try:
            if location == None or type(location) == ObjectDB:
                # location is None or a valid object
                loc = location                       
            elif ObjectDB.objects.dbref(location):
                # location is a dbref; search
                loc = ObjectDB.objects.dbref_search(location)
                if loc and hasattr(loc,'dbobj'):
                    loc = loc.dbobj
                else:
                    loc = location.dbobj    
            else:                
                loc = location.dbobj                        
            self.db_location = loc 
            self.save()
        except Exception:
            string = "Cannot set location: "
            string += "%s is not a valid location." 
            self.msg(string % location)
            logger.log_trace(string)
            raise         
    #@location.deleter
    def location_del(self):
        "Deleter. Allows for del self.location"
        self.db_location = None 
        self.save()
    location = property(location_get, location_set, location_del)

    # home property (wraps db_home)
    #@property 
    def home_get(self):
        "Getter. Allows for value = self.home"
        home = self.db_home 
        if home:
            return home.typeclass
        return None 
    #@home.setter
    def home_set(self, home):
        "Setter. Allows for self.home = value"
        try:
            if home == None or type(home) == ObjectDB:
                hom = home                       
            elif ObjectDB.objects.dbref(home):
                hom = ObjectDB.objects.dbref_search(home)
                if hom and hasattr(hom,'dbobj'):
                    hom = hom.dbobj
                else:
                    hom = home.dbobj    
            else:                
                hom = home.dbobj                
            self.db_home = hom        
        except Exception:
            string = "Cannot set home: "
            string += "%s is not a valid home." 
            self.msg(string % home)
            logger.log_trace(string)
            #raise 
        self.save()
    #@home.deleter
    def home_del(self):
        "Deleter. Allows for del self.home."
        self.db_home = None 
        self.save()
    home = property(home_get, home_set, home_del)

    # destination property (wraps db_destination)
    #@property 
    def destination_get(self):
        "Getter. Allows for value = self.destination."
        dest = self.db_destination
        if dest:
            return dest.typeclass
        return None 
    #@destination.setter
    def destination_set(self, destination):
        "Setter. Allows for self.destination = destination"
        try:
            if destination == None or type(destination) == ObjectDB:
                # destination is None or a valid object
                dest = destination                       
            elif ObjectDB.objects.dbref(destination):
                # destination is a dbref; search
                dest = ObjectDB.objects.dbref_search(destination)
                if dest and hasattr(dest,'dbobj'):
                    dest = dest.dbobj
                else:
                    dest = destination.dbobj    
            else:                
                dest = destination.dbobj                        
            self.db_destination = dest 
            self.save()
        except Exception:
            string = "Cannot set destination: "
            string += "%s is not a valid destination." 
            self.msg(string % destination)
            logger.log_trace(string)
            raise         
    #@destination.deleter
    def destination_del(self):
        "Deleter. Allows for del self.destination"
        self.db_destination = None 
        self.save()
    destination = property(destination_get, destination_set, destination_del)

    #@property for consistent aliases access throughout Evennia
    #@aliases.setter
    def aliases_set(self, aliases):
        "Adds an alias to object"
        if not is_iter(aliases):
            aliases = [aliases]
        for alias in aliases:
            query = Alias.objects.filter(db_obj=self, db_key__iexact=alias)
            if query.count():
                continue 
            new_alias = Alias(db_key=alias, db_obj=self)
            new_alias.save()
    #@aliases.getter
    def aliases_get(self):
        "Return a list of all aliases defined on this object."
        return list(Alias.objects.filter(db_obj=self).values_list("db_key", flat=True))
    #@aliases.deleter
    def aliases_del(self):
        "Removes aliases from object"
        query = Alias.objects.filter(db_obj=self)        
        if query:
            query.delete()
    aliases = property(aliases_get, aliases_set, aliases_del)

    # cmdset_storage property
    #@property
    def cmdset_storage_get(self):
        "Getter. Allows for value = self.name. Returns a list of cmdset_storage."
        if self.db_cmdset_storage:
            return [path.strip() for path  in self.db_cmdset_storage.split(',')]
        return []
    #@cmdset_storage.setter
    def cmdset_storage_set(self, value):
        "Setter. Allows for self.name = value. Stores as a comma-separated string."
        if is_iter(value):
            value = ",".join([str(val).strip() for val in value])
        self.db_cmdset_storage = value
        self.save()        
    #@cmdset_storage.deleter
    def cmdset_storage_del(self):
        "Deleter. Allows for del self.name"
        self.db_cmdset_storage = ""
        self.save()
    cmdset_storage = property(cmdset_storage_get, cmdset_storage_set, cmdset_storage_del)


    class Meta:
        "Define Django meta options"
        verbose_name = "Object"
        verbose_name_plural = "Objects"

    #
    # ObjectDB class access methods/properties
    # 

    # this is required to properly handle attributes and typeclass loading.
    #attribute_model_path = "src.objects.models"
    #attribute_model_name = "ObjAttribute"
    typeclass_paths = settings.OBJECT_TYPECLASS_PATHS 
    attribute_class = ObjAttribute
    db_model_name = "objectdb" # used by attributes to safely store objects

    # this is used by all typedobjects as a fallback
    try:
        default_typeclass_path = settings.BASE_OBJECT_TYPECLASS
    except Exception:
        default_typeclass_path = "src.objects.objects.Object"

    #@property
    def sessions_get(self):
        """
        Retrieve sessions connected to this object.
        """
        # if the player is not connected, this will simply be an empty list. 
        if self.player:
            return self.player.sessions
        return []
    sessions = property(sessions_get)

    #@property 
    def has_player_get(self):
        """
        Convenience function for checking if an active player is
        currently connected to this object
        """
        return any(self.sessions)
    has_player = property(has_player_get)
    is_player = property(has_player_get)

    #@property 
    def is_superuser_get(self):
        "Check if user has a player, and if so, if it is a superuser."
        return any(self.sessions) and self.player.is_superuser
    is_superuser = property(is_superuser_get)

    #@property 
    def contents_get(self, exclude=None):
        """
        Returns the contents of this object, i.e. all
        objects that has this object set as its location.
        """
        return ObjectDB.objects.get_contents(self, excludeobj=exclude)
    contents = property(contents_get)

    #@property
    def exits_get(self):
        """
        Returns all exits from this object, i.e. all objects
        at this location having the property destination != None.
        """
        return [exi for exi in self.contents
                if exi.destination]
    exits = property(exits_get)

            
    #
    # Main Search method
    #
    
    def search(self, ostring,
               global_search=False,
               attribute_name=None,
               use_nicks=False, location=None,
               ignore_errors=False, player=False):
        """
        Perform a standard object search in the database, handling
        multiple results and lack thereof gracefully.
        
        ostring: (str) The string to match object names against.
                       Obs - To find a player, append * to the
                       start of ostring. 
        global_search: Search all objects, not just the current
                       location/inventory
        attribute_name: (string) Which attribute to match
                        (if None, uses default 'name')
        use_nicks : Use nickname replace (off by default)              
        location : If None, use caller's current location
        ignore_errors : Don't display any error messages even
                        if there are none/multiple matches - 
                        just return the result as a list. 
        player :        Don't search for an Object but a Player. 
                        This will also find players that don't
                        currently have a character.

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
        if use_nicks:
            if ostring.startswith('*') or player:
                # player nick replace 
                ostring = self.nicks.get(ostring.lstrip('*'), nick_type="player")
                if not player:
                    ostring = "*%s" % ostring
            else:
                # object nick replace 
                ostring = self.nicks.get(ostring, nick_type="object")

        if player:
            if ostring in ("me", "self", "*me", "*self"):
                results = [self.player]
            else:
                results = PlayerDB.objects.player_search(ostring.lstrip('*'))
        else:
            results = ObjectDB.objects.object_search(ostring, caller=self, 
                                                     global_search=global_search,
                                                     attribute_name=attribute_name,
                                                     location=location)
    
        if ignore_errors:
            return results
        # this import is cache after the first call.
        return AT_SEARCH_RESULT(self, ostring, results, global_search)

    #
    # Execution/action methods
    #
        
    def execute_cmd(self, raw_string):
        """
        Do something as this object. This command transparently
        lets its typeclass execute the command. 
        raw_string - raw command input coming from the command line. 

        The return from this method is None for all default commands
        (it's the return value of cmd.func()) and is not used in any
        way by the engine. It might be useful for admins wanting to
        implement some sort of 'nested' command structure though,
        """        
        # nick replacement - we require full-word matching.
        
        # do text encoding conversion 
        raw_string = to_unicode(raw_string)

        raw_list = raw_string.split(None)
        raw_list = [" ".join(raw_list[:i+1]) for i in range(len(raw_list)) if raw_list[:i+1]]
        for nick in ObjectNick.objects.filter(db_obj=self, db_type__in=("inputline","channel")):           
            if nick.db_nick in raw_list:
                raw_string = raw_string.replace(nick.db_nick, nick.db_real, 1) 
                break        
        return cmdhandler.cmdhandler(self.typeclass, raw_string)

    def msg(self, message, from_obj=None, data=None):
        """
        Emits something to any sessions attached to the object.
        
        message (str): The message to send
        from_obj (obj): object that is sending.
        data (object): an optional data object that may or may not
                       be used by the protocol.                       
        """
        # This is an important function that must always work. 
        # we use a different __getattribute__ to avoid recursive loops.
                
        if object.__getattribute__(self, 'player'):
            object.__getattribute__(self, 'player').msg(message, from_obj=from_obj, data=data)

    def emit_to(self, message, from_obj=None, data=None):
        "Deprecated. Alias for msg"
        logger.log_depmsg("emit_to() is deprecated. Use msg() instead.")
        self.msg(message, from_obj, data)
        
    def msg_contents(self, message, exclude=None, from_obj=None, data=None):
        """
        Emits something to all objects inside an object.

        exclude is a list of objects not to send to. See self.msg() for more info.
        """
        contents = self.contents
        if exclude:
            if not is_iter(exclude):
                exclude = [exclude]              
            contents = [obj for obj in contents
                        if (obj not in exclude and obj not in exclude)]
        for obj in contents:
            obj.msg(message, from_obj=from_obj, data=data)

    def emit_to_contents(self, message, exclude=None, from_obj=None, data=None):
        "Deprecated. Alias for msg_contents"
        logger.log_depmsg("emit_to_contents() is deprecated. Use msg_contents() instead.")
        self.msg_contents(message, exclude=exclude, from_obj=from_obj, data=data)
            
    def move_to(self, destination, quiet=False,
                emit_to_obj=None):
        """
        Moves this object to a new location.
        
        destination: (Object) Reference to the object to move to. This
                     can also be an exit object, in which case the destination
                     property is used as destination. 
        quiet:  (bool)    If true, don't emit left/arrived messages.
        emit_to_obj: (Object) object to receive error messages
        """
        def logerr(string=""):
            trc = traceback.format_exc()
            errstring = "%s%s" % (trc, string)
            logger.log_trace()
            self.msg(errstring)

        errtxt = "Couldn't perform move ('%s'). Contact an admin."
        if not emit_to_obj:
            emit_to_obj = self

        if not destination:
            emit_to_obj.msg("The destination doesn't exist.")
            return 
        if destination.destination:
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
        source_location = self.location
        if not source_location:
            # there was some error in placing this room.
            # we have to set one or we won't be able to continue
            if self.home:
                source_location = self.home
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
            self.location = destination
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
        default_home_id = int(settings.CHARACTER_DEFAULT_HOME)
        try:
            default_home = ObjectDB.objects.get(id=default_home_id)
            if default_home.id == self.id:
                # we are deleting default home!
                default_home = None 
        except Exception:
            string = "Could not find default home '(#%d)'."
            logger.log_errmsg(string % default_home_id)
            default_home = None 

        for obj in objs:            
            home = obj.home 
            # Obviously, we can't send it back to here.
            if not home or (home and home.id == self.id):
                obj.home = default_home                
                
            # If for some reason it's still None...
            if not obj.home:
                string = "Missing default home, '%s(#%d)' "
                string += "now has a null location."
                obj.location = None 
                obj.msg("Something went wrong! You are dumped into nowhere. Contact an admin.")
                logger.log_errmsg(string % (obj.name, obj.id))
                return 
            
            if obj.has_player:
                if home:                        
                    string = "Your current location has ceased to exist,"
                    string += " moving you to %s(#%d)."
                    obj.msg(string % (home.name, home.id))
                else:
                    # Famous last words: The player should never see this.
                    string = "This place should not exist ... contact an admin."
                    obj.msg(string)
            obj.move_to(home)

    def copy(self, new_key=None):
        """ 
        Makes an identical copy of this object and returns
        it. The copy will be named <key>_copy by default. If you
        want to customize the copy by changing some settings, use
        the manager method copy_object directly.  
        """
        if not new_key:
            new_key = "%s_copy" % self.key
        return ObjectDB.objects.copy_object(self, new_key=new_key)

    delete_iter = 0
    def delete(self):    
        """
        Deletes this object. 
        Before deletion, this method makes sure to move all contained
        objects to their respective home locations, as well as clean
        up all exits to/from the object.
        """
        if self.delete_iter > 0:
            # make sure to only call delete once on this object
            # (avoid recursive loops)
            return False

        if not self.at_object_delete():
            # this is an extra pre-check
            # run before deletion mechanism
            # is kicked into gear. 
            self.delete_iter == 0
            return False

        self.delete_iter += 1

        # See if we need to kick the player off.

        for session in self.sessions:
            session.msg("Your character %s has been destroyed." % self.name)
            # no need to disconnect, Player just jumps to OOC mode.                         
        # sever the connection (important!)
        if object.__getattribute__(self, 'player') and self.player:
            self.player.character = None
        self.player = None 

        for script in self.scripts.all():
            script.stop()
        
        # if self.player:
        #     self.player.user.is_active = False 
        #     self.player.user.save(

        # Destroy any exits to and from this room, if any
        self.clear_exits()
        # Clear out any non-exit objects located within the object
        self.clear_contents()
        # Perform the deletion of the object
        super(ObjectDB, self).delete()
        return True 
