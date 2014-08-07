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

import datetime
from django.conf import settings
from src.typeclasses.typeclass import TypeClass
from src.comms.models import ChannelDB
from src.utils import logger
__all__ = ("Player",)

_MULTISESSION_MODE = settings.MULTISESSION_MODE
_CMDSET_PLAYER = settings.CMDSET_PLAYER
_CONNECT_CHANNEL = None


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
         aliases (list of strings) - aliases to the object. Will be saved to
                            database as AliasDB entries but returned as strings.
         dbref (int, read-only) - unique #id-number. Also "id" can be used.
         dbobj (Player, read-only) - link to database model. dbobj.typeclass
                                     points back to this class
         typeclass (Player, read-only) - this links back to this class as an
                          identified only. Use self.swap_typeclass() to switch.
         date_created (string) - time stamp of object creation
         permissions (list of strings) - list of permission strings

         user (User, read-only) - django User authorization object
         obj (Object) - game object controlled by player. 'character' can also
                        be used.
         sessions (list of Sessions) - sessions connected to this player
         is_superuser (bool, read-only) - if the connected user is a superuser

        * Handlers

         locks - lock-handler: use locks.add() to add new lock strings
         db - attribute-handler: store/retrieve database attributes on this
                                 self.db.myattr=val, val=self.db.myattr
         ndb - non-persistent attribute handler: same as db but does not
                                     create a database entry when storing data
         scripts - script-handler. Add new scripts to object with scripts.add()
         cmdset - cmdset-handler. Use cmdset.add() to add new cmdsets to object
         nicks - nick-handler. New nicks with nicks.add().

        * Helper methods

         msg(outgoing_string, from_obj=None, **kwargs)
         swap_character(new_character, delete_old_character=False)
         execute_cmd(raw_string)
         search(ostring, global_search=False, attribute_name=None,
                         use_nicks=False, location=None,
                         ignore_errors=False, player=False)
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
         at_access()
         at_cmdset_get()
         at_first_login()
         at_post_login(sessid=None)
         at_disconnect()
         at_message_receive()
         at_message_send()
         at_server_reload()
         at_server_shutdown()

         """
        super(Player, self).__init__(dbobj)

    ## methods inherited from database model

    def msg(self, text=None, from_obj=None, sessid=None, **kwargs):
        """
        Evennia -> User
        This is the main route for sending data back to the user from
        the server.

        text (string) - text data to send
        from_obj (Object/Player) - source object of message to send
        sessid - the session id of the session to send to. If not given,
          return to all sessions connected to this player. This is usually only
          relevant when using msg() directly from a player-command (from
          a command on a Character, the character automatically stores and
          handles the sessid).
        kwargs - extra data to send through protocol
                 """
        self.dbobj.msg(text=text, from_obj=from_obj, sessid=sessid, **kwargs)

    def swap_character(self, new_character, delete_old_character=False):
        """
        Swaps the character controlled by this Player, if possible.

        new_character (Object) - character/object to swap to
        delete_old_character (bool) - delete the old character when swapping

        Returns: True/False depending on if swap suceeded or not.
        """
        return self.dbobj.swap_character(new_character, delete_old_character=delete_old_character)

    def execute_cmd(self, raw_string, sessid=None):
        """
        Do something as this object. This command transparently
        lets its typeclass execute the command. This method
        is -not- called by Evennia normally, it is here to be
        called explicitly in code.

        Argument:
        raw_string (string) - raw command input
        sessid (int) - id of session executing the command. This sets the
                       sessid property on the command

        Returns Deferred - this is an asynchronous Twisted object that will
            not fire until the command has actually finished executing. To
            overload this one needs to attach callback functions to it, with
            addCallback(function). This function will be called with an
            eventual return value from the command execution.

            This return is not used at all by Evennia by default, but might
            be useful for coders intending to implement some sort of nested
            command structure.
        """
        return self.dbobj.execute_cmd(raw_string, sessid=sessid)

    def search(self, searchdata, return_puppet=False, **kwargs):
        """
        This is similar to the Object search method but will search for
        Players only. Errors will be echoed, and None returned if no Player
        is found.
        searchdata - search criterion, the Player's key or dbref to search for
        return_puppet  - will try to return the object the player controls
                           instead of the Player object itself. If no
                           puppeted object exists (since Player is OOC), None will
                           be returned.
        Extra keywords are ignored, but are allowed in call in order to make
                           API more consistent with objects.models.TypedObject.search.
        """
        # handle me, self and *me, *self
        if isinstance(searchdata, basestring):
            # handle wrapping of common terms
            if searchdata.lower() in ("me", "*me", "self", "*self",):
                return self
        return self.dbobj.search(searchdata, return_puppet=return_puppet, **kwargs)

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
        self.dbobj.swap_typeclass(new_typeclass,
                    clean_attributes=clean_attributes, no_default=no_default)

    def access(self, accessing_obj, access_type='read', default=False, **kwargs):
        """
        Determines if another object has permission to access this object
        in whatever way.

          accessing_obj (Object)- object trying to access this one
          access_type (string) - type of access sought
          default (bool) - what to return if no lock of access_type was found
          **kwargs - passed to the at_access hook along with the result.
        """
        result = self.dbobj.access(accessing_obj, access_type=access_type, default=default)
        self.at_access(result, accessing_obj, access_type, **kwargs)
        return result

    def check_permstring(self, permstring):
        """
        This explicitly checks the given string against this object's
        'permissions' property without involving any locks.

        permstring (string) - permission string that need to match a permission
                              on the object. (example: 'Builders')
        Note that this method does -not- call the at_access hook.
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
        lockstring = "examine:perm(Wizards);edit:perm(Wizards);delete:perm(Wizards);boot:perm(Wizards);msg:all()"
        self.locks.add(lockstring)

        # The ooc player cmdset
        self.cmdset.add_default(_CMDSET_PLAYER, permanent=True)

    def at_player_creation(self):
        """
        This is called once, the very first time
        the player is created (i.e. first time they
        register with the game). It's a good place
        to store attributes all players should have,
        like configuration values etc.
        """
        # set an (empty) attribute holding the characters this player has
        lockstring = "attrread:perm(Admins);attredit:perm(Admins);attrcreate:perm(Admins)"
        self.attributes.add("_playable_characters", [], lockstring=lockstring)

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

    def at_access(self, result, accessing_obj, access_type, **kwargs):
        """
        This is called with the result of an access call, along with
        any kwargs used for that call. The return of this method does
        not affect the result of the lock check. It can be used e.g. to
        customize error messages in a central location or other effects
        based on the access result.
        """
        pass

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
        Called every time the user logs in, just before the actual
        login-state is set.
        """
        pass

    def _send_to_connect_channel(self, message):
        "Helper method for loading the default comm channel"
        global _CONNECT_CHANNEL
        if not _CONNECT_CHANNEL:
            try:
                _CONNECT_CHANNEL = ChannelDB.objects.filter(db_key=settings.CHANNEL_CONNECTINFO[0])[0]
            except Exception:
                logger.log_trace()
        now = datetime.datetime.now()
        now = "%02i-%02i-%02i(%02i:%02i)" % (now.year, now.month,
                                             now.day, now.hour, now.minute)
        if _CONNECT_CHANNEL:
            _CONNECT_CHANNEL.tempmsg("[%s, %s]: %s" % (_CONNECT_CHANNEL.key, now, message))
        else:
            logger.log_infomsg("[%s]: %s" % (now, message))

    def at_post_login(self, sessid=None):
        """
        Called at the end of the login process, just before letting
        them loose. This is called before an eventual Character's
        at_post_login hook.
        """
        self._send_to_connect_channel("{G%s connected{n" % self.key)
        if _MULTISESSION_MODE == 0:
            # in this mode we should have only one character available. We
            # try to auto-connect to it by calling the @ic command
            # (this relies on player.db._last_puppet being set)
            self.execute_cmd("@ic", sessid=sessid)
        elif _MULTISESSION_MODE == 1:
            # in this mode the first session to connect acts like mode 0,
            # the following sessions "share" the same view and should
            # not perform any actions
            if not self.get_all_puppets():
                self.execute_cmd("@ic", sessid=sessid)
        elif _MULTISESSION_MODE in (2, 3):
            # In this mode we by default end up at a character selection
            # screen. We execute look on the player.
            self.execute_cmd("look", sessid=sessid)

    def at_disconnect(self, reason=None):
        """
        Called just before user is disconnected.
        """
        reason = reason and "(%s)" % reason or ""
        self._send_to_connect_channel("{R%s disconnected %s{n" % (self.key, reason))

    def at_post_disconnect(self):
        """
        This is called after disconnection is complete. No messages
        can be relayed to the player from here. After this call, the
        player should not be accessed any more, making this a good
        spot for deleting it (in the case of a guest player account,
        for example).
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
        This hook is called whenever the server is shutting down for
        restart/reboot. If you want to, for example, save non-persistent
        properties across a restart, this is the place to do it.
        """
        pass

    def at_server_shutdown(self):
        """
        This hook is called whenever the server is shutting down fully
        (i.e. not for a restart).
        """
        pass

class Guest(Player):
    """
    This class is used for guest logins. Unlike Players, Guests and their
    characters are deleted after disconnection.
    """
    def at_post_login(self, sessid=None):
        """
        In theory, guests only have one character regardless of which
        MULTISESSION_MODE we're in. They don't get a choice.
        """
        self._send_to_connect_channel("{G%s connected{n" % self.key)
        self.execute_cmd("@ic", sessid=sessid)

    def at_disconnect(self):
        """
        A Guest's characters aren't meant to linger on the server. When a
        Guest disconnects, we remove its character.
        """
        super(Guest, self).at_disconnect()
        characters = self.db._playable_characters
        for character in filter(None, characters):
            character.delete()

    def at_server_shutdown(self):
        """
        We repeat at_disconnect() here just to be on the safe side.
        """
        super(Guest, self).at_server_shutdown()
        characters = self.db._playable_characters
        for character in filter(None, characters):
            character.delete()

    def at_post_disconnect(self):
        """
        Guests aren't meant to linger on the server, either. We need to wait
        until after the Guest disconnects to delete it, though.
        """
        super(Guest, self).at_post_disconnect()
        self.delete()
