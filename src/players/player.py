"""
Typeclass for Player objects

Note that this object is primarily intended to
store OOC information, not game info! This
object represents the actual user (not their
character) and has NO actual precence in the
game world (this is handled by the associated
character object, so you should customize that
instead for most things).

"""
from django.conf import settings
from src.typeclasses.typeclass import TypeClass
__all__ = ("Player",)
CMDSET_OOC = settings.CMDSET_OOC

class Player(TypeClass):
    """
    Base typeclass for all Players.
    """
    def __init__(self, dbobj):
        """
        This is the base Typeclass for all Players. Players represent
        the person playing the game and tracks account info, password
        etc. They are OOC entities without presence in-game. A Player
        can connect to a Character Object in order to "enter" the
        game.

        Player Typeclass API:

        * Available properties (only available on initiated typeclass objects)

         key (string) - name of player
         name (string)- wrapper for user.username
         aliases (list of strings) - aliases to the object. Will be saved to database as AliasDB entries but returned as strings.
         dbref (int, read-only) - unique #id-number. Also "id" can be used.
         dbobj (Player, read-only) - link to database model. dbobj.typeclass points back to this class
         typeclass (Player, read-only) - this links back to this class as an identified only. Use self.swap_typeclass() to switch.
         date_created (string) - time stamp of object creation
         permissions (list of strings) - list of permission strings

         user (User, read-only) - django User authorization object
         obj (Object) - game object controlled by player. 'character' can also be used.
         sessions (list of Sessions) - sessions connected to this player
         is_superuser (bool, read-only) - if the connected user is a superuser

        * Handlers

         locks - lock-handler: use locks.add() to add new lock strings
         db - attribute-handler: store/retrieve database attributes on this self.db.myattr=val, val=self.db.myattr
         ndb - non-persistent attribute handler: same as db but does not create a database entry when storing data
         scripts - script-handler. Add new scripts to object with scripts.add()
         cmdset - cmdset-handler. Use cmdset.add() to add new cmdsets to object
         nicks - nick-handler. New nicks with nicks.add().

        * Helper methods

         msg(outgoing_string, from_obj=None, data=None)
         swap_character(new_character, delete_old_character=False)
         execute_cmd(raw_string)
         search(ostring, global_search=False, attribute_name=None, use_nicks=False, location=None, ignore_errors=False, player=False)
         is_typeclass(typeclass, exact=False)
         swap_typeclass(new_typeclass, clean_attributes=False, no_default=True)
         access(accessing_obj, access_type='read', default=False)
         check_permstring(permstring)

        * Hook methods

         basetype_setup()
         at_player_creation()

         - note that the following hooks are also found on Objects and are
           usually handled on the character level:

         at_init()
         at_cmdset_get()
         at_first_login()
         at_post_login()
         at_disconnect()
         at_message_receive()
         at_message_send()
         at_server_reload()
         at_server_shutdown()

         """
        super(Player, self).__init__(dbobj)

    ## methods inherited from database model

    def msg(self, outgoing_string, from_obj=None, data=None):
        """
        Evennia -> User
        This is the main route for sending data back to the user from the server.

        outgoing_string (string) - text data to send
        from_obj (Object/Player) - source object of message to send
        data (?) - arbitrary data object containing eventual protocol-specific options

        """
        self.dbobj.msg(outgoing_string, from_obj=from_obj, data=data)

    def swap_character(self, new_character, delete_old_character=False):
        """
        Swaps the character controlled by this Player, if possible.

        new_character (Object) - character/object to swap to
        delete_old_character (bool) - delete the old character when swapping

        Returns: True/False depending on if swap suceeded or not.
        """
        return self.dbobj.swap_character(new_character, delete_old_character=delete_old_character)

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
        return self.dbobj.execute_cmd(raw_string)

    def search(self, ostring, return_character=False):
        """
        This method mimicks object.search if self.character is set. Otherwise only
        other Players can be searched with this method.
        """
        return self.dbobj.search(ostring, return_character=return_character)

    def is_typeclass(self, typeclass, exact=False):
        """
        Returns true if this object has this type
          OR has a typeclass which is an subclass of
          the given typeclass.

        typeclass - can be a class object or the
                python path to such an object to match against.

        exact - returns true only if the object's
               type is exactly this typeclass, ignoring
               parents.

        Returns: Boolean
        """
        return self.dbobj.is_typeclass(typeclass, exact=exact)

    def swap_typeclass(self, new_typeclass, clean_attributes=False, no_default=True):
        """
        This performs an in-situ swap of the typeclass. This means
        that in-game, this object will suddenly be something else.
        Player will not be affected. To 'move' a player to a different
        object entirely (while retaining this object's type), use
        self.player.swap_object().

        Note that this might be an error prone operation if the
        old/new typeclass was heavily customized - your code
        might expect one and not the other, so be careful to
        bug test your code if using this feature! Often its easiest
        to create a new object and just swap the player over to
        that one instead.

        Arguments:
        new_typeclass (path/classobj) - type to switch to
        clean_attributes (bool/list) - will delete all attributes
                           stored on this object (but not any
                           of the database fields such as name or
                           location). You can't get attributes back,
                           but this is often the safest bet to make
                           sure nothing in the new typeclass clashes
                           with the old one. If you supply a list,
                           only those named attributes will be cleared.
        no_default - if this is active, the swapper will not allow for
                     swapping to a default typeclass in case the given
                     one fails for some reason. Instead the old one
                     will be preserved.
        Returns:
          boolean True/False depending on if the swap worked or not.


        """
        self.dbobj.swap_typeclass(new_typeclass, clean_attributes=clean_attributes, no_default=no_default)

    def access(self, accessing_obj, access_type='read', default=False):
        """
        Determines if another object has permission to access this object in whatever way.

          accessing_obj (Object)- object trying to access this one
          access_type (string) - type of access sought
          default (bool) - what to return if no lock of access_type was found
        """
        return self.dbobj.access(accessing_obj, access_type=access_type, default=default)

    def check_permstring(self, permstring):
        """
        This explicitly checks the given string against this object's
        'permissions' property without involving any locks.

        permstring (string) - permission string that need to match a permission on the object.
                              (example: 'Builders')
        """
        return self.dbobj.check_permstring(permstring)

    ## player hooks

    def basetype_setup(self):
        """
        This sets up the basic properties for a player.
        Overload this with at_player_creation rather than
        changing this method.

        """
        # the text encoding to use.
        self.db.encoding = "utf-8"

        # A basic security setup
        self.locks.add("examine:perm(Wizards)")
        self.locks.add("edit:perm(Wizards)")
        self.locks.add("delete:perm(Wizards)")
        self.locks.add("boot:perm(Wizards)")
        self.locks.add("msg:all()")

        # The ooc player cmdset
        self.cmdset.add_default(CMDSET_OOC, permanent=True)

    def at_player_creation(self):
        """
        This is called once, the very first time
        the player is created (i.e. first time they
        register with the game). It's a good place
        to store attributes all players should have,
        like configuration values etc.
        """
        pass


    def at_init(self):
        """
        This is always called whenever this object is initiated --
        that is, whenever it its typeclass is cached from memory. This
        happens on-demand first time the object is used or activated
        in some way after being created but also after each server
        restart or reload. In the case of player objects, this usually
        happens the moment the player logs in or reconnects after a
        reload.
        """
        pass

    # Note that the hooks below also exist in the character object's
    # typeclass. You can often ignore these and rely on the character
    # ones instead, unless you are implementing a multi-character game
    # and have some things that should be done regardless of which
    # character is currently connected to this player.

    def at_cmdset_get(self):
        """
        Called just before cmdsets on this player are requested by the
        command handler. If changes need to be done on the fly to the cmdset
        before passing them on to the cmdhandler, this is the place to do it.
        This is called also if the player currently have no cmdsets.
        """
        pass

    def at_first_login(self):
        """
        Only called once, the very first
        time the user logs in.
        """
        pass

    def at_pre_login(self):
        """
        Called every time the user logs in,
        before they are actually logged in.
        """
        pass

    def at_post_login(self):
        """
        Called at the end of the login process, just before letting
        them loose. This is called before an eventual Character's
        at_post_login hook.
        """
        # Character.at_post_login also looks around. Only use
        # this as a backup when logging in without a character
        if not self.character:
            self.execute_cmd("look")

    def at_disconnect(self, reason=None):
        """
        Called just before user
        is disconnected.
        """
        pass

    def at_message_receive(self, message, from_obj=None):
        """
        Called when any text is emitted to this
        object. If it returns False, no text
        will be sent automatically.
        """
        return True

    def at_message_send(self, message, to_object):
        """
        Called whenever this object tries to send text
        to another object. Only called if the object supplied
        itself as a sender in the msg() call.
        """
        pass

    def at_server_reload(self):
        """
        This hook is called whenever the server is shutting down for restart/reboot.
        If you want to, for example, save non-persistent properties across a restart,
        this is the place to do it.
        """
        pass

    def at_server_shutdown(self):
        """
        This hook is called whenever the server is shutting down fully (i.e. not for
        a restart).
        """
        pass
