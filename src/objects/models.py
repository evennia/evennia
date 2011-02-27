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

from src.utils.idmapper.models import SharedMemoryModel
from src.typeclasses.models import Attribute, TypedObject
from src.typeclasses.typeclass import TypeClass
from src.objects.manager import ObjectManager
from src.config.models import ConfigValue
from src.permissions.permissions import has_perm
from src.utils import logger
from src.utils.utils import is_iter

FULL_PERSISTENCE = settings.FULL_PERSISTENCE 

try:
    HANDLE_SEARCH_ERRORS = __import__(
        settings.ALTERNATE_OBJECT_SEARCH_ERROR_HANDLER).handle_search_errors
except Exception:
    from src.objects.object_search_funcs \
         import handle_search_errors as HANDLE_SEARCH_ERRORS

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
    db_key = models.CharField(max_length=255)
    db_obj = models.ForeignKey("ObjectDB")
    
    class Meta:
        "Define Django meta options"
        verbose_name = "Object alias"
        verbose_name_plural = "Object aliases"

#------------------------------------------------------------
#
# Nick
#
#------------------------------------------------------------

class Nick(SharedMemoryModel):
    """
    This model holds whichever alternate names this object 
    has for OTHER objects, but also for arbitrary strings,
    channels, players etc. Setting a nick does not affect
    the nicknamed object at all (as opposed to Aliases above), 
    and only this object will be able to refer to the nicknamed
    object by the given nick. 

    The default nick types used by Evennia are: 
    inputline (default) - match against all input
    player - match against player searches
    obj - match against object searches 
    channel - used to store own names for channels

    """
    db_nick = models.CharField(max_length=255, db_index=True) # the nick
    db_real = models.TextField() # the aliased string
    db_type = models.CharField(default="inputline", max_length=16, null=True, blank=True) # the type of nick
    db_obj = models.ForeignKey("ObjectDB")

    class Meta:
        "Define Django meta options"
        verbose_name = "Nickname"
        verbose_name_plural = "Nicknames"
        unique_together = ("db_nick", "db_type", "db_obj")

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
      Dbref - #id of object 
      db - persistent attribute storage
      ndb - non-persistent attribute storage 

    The ObjectDB adds the following properties:
      aliases - alternative names for object
      player - optional connected player
      location - in-game location of object
      home - safety location for object
      nicks - this objects nicknames for *other* objects
      sessions - sessions connected to this object (see also player)
      has_player - bool if an active player is currently connected
      contents - other objects having this object as location
      
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

    # comma-separated list of alias-names of this object. Note that default
    # searches only search aliases in the same location as caller. 
    db_aliases = models.ForeignKey(Alias, blank=True, null=True, db_index=True)
    # If this is a character object, the player is connected here.
    db_player = models.ForeignKey("players.PlayerDB", blank=True, null=True)    
    # The location in the game world. Since this one is likely
    # to change often, we set this with the 'location' property
    # to transparently handle Typeclassing. 
    db_location = models.ForeignKey('self', related_name="locations_set",
                                     blank=True, null=True)
    # a safety location, this usually don't change much.
    db_home = models.ForeignKey('self', related_name="homes_set",
                                 blank=True, null=True)
    # pickled dictionary storing the object's assigned nicknames
    # (use the 'nicks' property to access)
    db_nicks = models.ForeignKey(Nick, blank=True, null=True, db_index=True)

    # Database manager
    objects = ObjectManager()

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
        return list(Alias.objects.filter(db_obj=self))
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
            return loc.typeclass(loc)
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
    location = property(location_get, location_set, location_del)

    # home property (wraps db_home)
    #@property 
    def home_get(self):
        "Getter. Allows for value = self.home"
        home = self.db_home 
        if home:
            return home.typeclass(home)
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
            if home:
                self.db_home = hom        
        except Exception:
            string = "Cannot set home: "
            string += "%s is not a valid home." 
            self.msg(string % home)
            logger.log_trace(string)
            raise 
        self.save()
    #@home.deleter
    def home_del(self):
        "Deleter. Allows for del self.home."
        self.db_home = None 
    home = property(home_get, home_set, home_del)

    # nicks property (wraps db_nicks)
    #@property 
    def nicks_get(self):
        "Getter. Allows for value = self.aliases"
        return list(Nick.objects.filter(db_obj=self))
    #@nick.setter
    def nicks_set(self, nicks):
        """Setter is disabled. Use the nickhandler instead."""
        logger.log_errmsg("Nicks (%s) cannot be set through obj.nicks. Use obj.nickhandler instead." % nicks)
    #@nick.deleter
    def nicks_del(self):
        "Deleter. Allows for del self.aliases"
        for nick in Nick.objects.filter(db_obj=self):
            nick.delete()
    nicks = property(nicks_get, nicks_set, nicks_del)


    class Meta:
        "Define Django meta options"
        verbose_name = "Object"
        verbose_name_plural = "Objects"

    #
    # ObjectDB class access methods/properties
    # 

    # this is required to properly handle attributes
    attribute_model_path = "src.objects.models"
    attribute_model_name = "ObjAttribute"

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

    #@property 
    def contents_get(self):
        """
        Returns the contents of this object, i.e. all
        objects that has this object set as its location.
        """
        return ObjectDB.objects.get_contents(self)
    contents = property(contents_get)

    #@property
    def exits_get(self):
        """
        Returns all exits from this object, i.e. all objects
        at this location having the property _destination.
        """
        return [exi for exi in self.contents
                if exi.has_attribute('_destination')]
    exits = property(exits_get)
    
    def nickhandler(self, nick, realname=None, nick_type="inputline", startswith=False, delete=False):
        """
        This is a central method for getting and setting nicks
        - mappings of nicks to strings, objects etc. This is the main
        access method, use it in preference over the 'nicks' property. 

        Map a nick to a realname. Be careful if mapping an
        existing realname into a nick - you could make that
        realname inaccessible until you deleted the alias. 
        To delete - don't set realname.
        
        nick_types can be defined freely depending on implementation.
        The default nick_types used in Evennia are: 
        inputline (default) - match nick against all input
        player - match nick against player searches
        obj - match nick against object searches 
        channel - match nick when checking for channel aliases

        the delete keyword will delete the given nick.
        """
        if not nick or not nick.strip():
            return 
        nick = nick.strip()        
        query = Nick.objects.filter(db_obj=self, db_nick__iexact=nick)        
        if nick_type:
            query = query.filter(db_type__iexact=nick_type)        
        if delete:
            # remove the found nick(s)
            query.delete()           
        elif realname == None:
            # we want to get the real name for the nick. If none is
            # found, we return the nick again
            query = query.values_list("db_real", flat=True)
            if query: 
                return query[0]            
            else:
                return nick
        else:
            # we want to assign a new nick
            real = realname.strip() 
            if query:
                old_nick = query[0]
                old_nick.db_real = real
                old_nick.save()
            else:              
                new_nick = Nick(db_nick=nick, db_real=real, db_type=nick_type, db_obj=self)
                new_nick.save()                
                
    #
    # Main Search method
    #
    
    def search(self, ostring,
               global_search=False,
               attribute_name=None,
               use_nicks=False,
               ignore_errors=False):
        """
        Perform a standard object search in the database, handling
        multiple results and lack thereof gracefully.
        
        if local_only AND search_self are both false, a global
         search is done instead. 

        ostring: (str) The string to match object names against.
                       Obs - To find a player, append * to the
                       start of ostring. 
        global_search: Search all objects, not just the current
                       location/inventory
        attribute_name: (string) Which attribute to match
                        (if None, uses default 'name')
        use_nicks : Use nickname replace (off by default)              
        ignore_errors : Don't display any error messages even
                        if there are none/multiple matches - 
                        just return the result as a list. 

        Note - for multiple matches, the engine accepts a number
        linked to the key in order to separate the matches from
        each other without showing the dbref explicitly. Default
        syntax for this is 'N-searchword'. So for example, if there
        are three objects in the room all named 'ball', you could
        address the individual ball as '1-ball', '2-ball', '3-ball'
        etc. 
        """
        if use_nicks:
            if ostring.startswith('*'):
                # player nick replace 
                ostring = "*%s" % self.nickhandler(ostring.lstrip('*'), nick_type="player")
            else:
                # object nick replace 
                ostring = self.nickhandler(ostring, nick_type="object")

        results = ObjectDB.objects.object_search(self, ostring, 
                                                 global_search=global_search,
                                                 attribute_name=attribute_name)
    
        if ignore_errors:
            return results
        return HANDLE_SEARCH_ERRORS(self, ostring, results, global_search)


    #
    # Execution/action methods
    #
    
    def has_perm(self, accessing_obj, lock_type):
        """
        Determines if another object has permission to access 
        this object.
        accessing_obj - the object trying to gain access.
        lock_type : type of access checked for
        """
        return has_perm(accessing_obj, self, lock_type)

    def has_perm_on(self, accessed_obj, lock_type):
        """
        Determines if *this* object has permission to access
        another object.
        accessed_obj - the object being accessed by this one
        lock_type : type of access checked for 
        """
        return has_perm(self, accessed_obj, lock_type)

    def execute_cmd(self, raw_string):
        """
        Do something as this object. This command transparently
        lets its typeclass execute the command. 
        raw_string - raw command input coming from the command line. 
        """        
        # nick replacement - we require full-word matching.
        raw_list = raw_string.split(None)
        raw_list = [" ".join(raw_list[:i+1]) for i in range(len(raw_list)) if raw_list[:i+1]]
        for nick in Nick.objects.filter(db_obj=self, db_type__in=("inputline","channel")):           
            if nick.db_nick in raw_list:
                raw_string = raw_string.replace(nick.db_nick, nick.db_real, 1) 
                break        
        cmdhandler.cmdhandler(self.typeclass(self), raw_string)

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
            object.__getattribute__(self, 'player').msg(message, from_obj, data)

    def emit_to(self, message, from_obj=None, data=None):
        "Deprecated. Alias for msg"
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
        self.msg_contents(message, exclude=exclude, from_obj=from_obj, data=data)
            
    def move_to(self, destination, quiet=False,
                emit_to_obj=None):
        """
        Moves this object to a new location.
        
        destination: (Object) Reference to the object to move to. This
                     can also be an exit object, in which case the _destination
                     attribute is used as destination. 
        quiet:  (bool)    If true, don't emit left/arrived messages.
        emit_to_obj: (Object) object to receive error messages
        """
        errtxt = "Couldn't perform move ('%s'). Contact an admin."
        if not emit_to_obj:
            emit_to_obj = self

        if not destination:
            emit_to_obj.msg("The destination doesn't exist.")
            return 
        if destination.has_attribute('_destination'):
            # traverse exits
            destination = destination.get_attribute('_destination')

        # Before the move, call eventual pre-commands.
        try:
            if not self.at_before_move(destination):
                return
        except Exception:
            emit_to_obj.msg(errtxt % "at_before_move()")
            logger.log_trace()
            return False
       
        # Save the old location 
        source_location = self.location
        if not source_location:
            # there was some error in placing this room.
            # we have to set one or we won't be able to continue
            if self.home:
                source_location = self.home
            else:
                default_home_id = ConfigValue.objects.conf(db_key="default_home")            
                default_home = ObjectDB.objects.get_id(default_home_id)                
                source_location = default_home

        # Call hook on source location
        try:
            source_location.at_object_leave(self, destination)
        except Exception:
            emit_to_obj.msg(errtxt % "at_object_leave()")
            logger.log_trace()
            return False
        
        if not quiet:
            #tell the old room we are leaving
            try:
                self.announce_move_from(destination)            
            except Exception:
                emit_to_obj.msg(errtxt % "at_announce_move()" )
                logger.log_trace()
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
                emit_to_obj.msg(errtxt % "announce_move_to()")
                logger.log_trace()
                return  False                   
        
        # Execute eventual extra commands on this object after moving it
        # (usually calling 'look')
        try:
            self.at_after_move(source_location)
        except Exception:
            emit_to_obj.msg(errtxt % "at_after_move()")
            logger.log_trace()
            return False                    

        # Perform eventual extra commands on the receiving location
        try:
            destination.at_object_receive(self, source_location)
        except Exception:
            emit_to_obj.msg(errtxt % "at_obj_receive()")
            logger.log_trace()
            return False                              


    #
    # Object Swap, Delete and Cleanup methods 
    #              
            
    def clear_exits(self):
        """
        Destroys all of the exits and any exits pointing to this
        object as a destination.
        """
        for out_exit in self.exits:                            
            out_exit.delete()
        for in_exit in \
                ObjectDB.objects.get_objs_with_attr_match('_destination', self):
            in_exit.delete()

    def clear_contents(self):
        """
        Moves all objects (players/things) to their home
        location or to default home. 
        """
        # Gather up everything that thinks this is its location.
        objs = ObjectDB.objects.filter(db_location=self)
        default_home_id = int(ConfigValue.objects.conf('default_home'))
        try:
            default_home = ObjectDB.objects.get(id=default_home_id)
        except Exception:
            string = "Could not find default home '(#%d)'."
            logger.log_errmsg(string % default_home_id)
            default_home = None 

        for obj in objs:            
            home = obj.home 
            # Obviously, we can't send it back to here.
            if home and home.id == self.id:
                home = default_home
                
            # If for some reason it's still None...
            if not home:
                string = "Missing default home, '%s(#%d)' "
                string += "now has a null location."
                logger.log_errmsg(string % (obj.name, obj.id))
                return 

            if self.has_player:
                if home:                        
                    string = "Your current location has ceased to exist,"
                    string += " moving you to %s(#%d)."
                    obj.msg(string % (home.name, home.id))
                else:
                    # Famous last words: The player should never see this.
                    string = "This place should not exist ... contact an admin."
                    obj.msg(string)
            obj.move_to(home)

    def delete(self):    
        """
        Deletes this object. 
        Before deletion, this method makes sure to move all contained
        objects to their respective home locations, as well as clean
        up all exits to/from the object.
        """
        if not self.at_object_delete():
            # this is an extra pre-check
            # run before deletion mechanism
            # is kicked into gear. 
            return False

        # See if we need to kick the player off.
        for session in self.sessions:
            session.msg("Your character %s has been destroyed. Goodbye." % self.name)
            session.handle_close()
            
        # # If the object is a player, set the player account
        # # object to inactive. We generally avoid deleting a
        # # player completely in case it messes with things
        # # like sent-message memory etc in some games.
        # if self.player:
        #     self.player.user.is_active = False 
        #     self.player.user.save()

        # Destroy any exits to and from this room, if any
        self.clear_exits()
        # Clear out any non-exit objects located within the object
        self.clear_contents()
        # Perform the deletion of the object
        super(ObjectDB, self).delete()
        return True 

# Deferred import to avoid circular import errors. 
from src.commands import cmdhandler
