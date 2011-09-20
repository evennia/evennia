"""
This defines a the Server's generic session object. This object represents 
a connection to the outside world but don't know any details about how the 
connection actually happens (so it's the same for telnet, web, ssh etc).

It is stored on the Server side (as opposed to protocol-specific sessions which
are stored on the Portal side)
"""

import time 
from datetime import datetime
from django.conf import settings
from src.scripts.models import ScriptDB
from src.comms.models import Channel
from src.utils import logger
from src.commands import cmdhandler

IDLE_COMMAND = settings.IDLE_COMMAND 
        
from src.server.session import Session

# i18n
from django.utils.translation import ugettext as _


#------------------------------------------------------------
# Server Session
#------------------------------------------------------------

class ServerSession(Session):
    """
    This class represents a player's session and is a template for 
    individual protocols to communicate with Evennia. 

    Each player gets a session assigned to them whenever they connect
    to the game server. All communication between game and player goes
    through their session.

    """        

    def at_sync(self):
        """
        This is called whenever a session has been resynced with the portal.
        At this point all relevant attributes have already been set and self.player
        been assigned (if applicable).

        Since this is often called after a server restart we need to set up
        the session as it was. 
        """
        if not self.logged_in:
            return 

        player = self.get_player(1)
        character = self.get_character()
        if player:
            #print "sync: at_init() - player"
            player.at_init()
        if character:
            #print "sync: at_init() - character"
            character.at_init()
            # start (persistent) scripts on this object
            ScriptDB.objects.validate(obj=character)
                       
    def session_login(self, player):
        """
        Startup mechanisms that need to run at login. This is called
        by the login command (which need to have handled authentication
        already before calling this method)

        player - the connected player
        """

        # actually do the login by assigning session data

        self.player = player
        self.user = player.user
        self.uid = self.user.id
        self.uname = self.user.username
        self.logged_in = True
        self.conn_time = time.time()
        
        # Update account's last login time.
        self.user.last_login = datetime.now()        
        self.user.save()        
        
        # player init
        #print "at_init() - player"
        player.at_init()
        
        # Check if this is the first time the *player* logs in 
        if player.db.FIRST_LOGIN:
            player.at_first_login()
            del player.db.FIRST_LOGIN
        player.at_pre_login()        

        character = player.character
        #print "at_init() - character"
        character.at_init()
        if character: 
            # this player has a character. Check if it's the
            # first time *this character* logs in
            if character.db.FIRST_LOGIN:
                character.at_first_login()
                del character.db.FIRST_LOGIN            
            # run character login hook
            character.at_pre_login()

        self.log(_('Logged in: %(self)s') % {'self': self})

        # start (persistent) scripts on this object
        ScriptDB.objects.validate(obj=self.player.character)
        
        #add session to connected list
        self.sessionhandler.login(self)

        # post-login hooks 
        player.at_post_login()        
        if character:
            character.at_post_login()

    def session_disconnect(self):
        """
        Clean up the session, removing it from the game and doing some
        accounting. This method is used also for non-loggedin
        accounts.
        """
        if self.logged_in:            
            player = self.get_player()
            character = self.get_character()
            if character:
                character.at_disconnect()
            uaccount = player.user
            uaccount.last_login = datetime.now()
            uaccount.save()            
            self.logged_in = False                                        
        self.sessionhandler.disconnect(self)

    def get_player(self):
        """
        Get the player associated with this session
        """
        if self.logged_in:
            return self.player
        else:
            return None 
                       
    def get_character(self):
        """
        Returns the in-game character associated with this session.
        This returns the typeclass of the object.
        """
        player = self.get_player()
        if player:
            return player.character
        return None 

    def log(self, message, channel=True):
        """
        Emits session info to the appropriate outputs and info channels.
        """        
        if channel:
            try:
                cchan = settings.CHANNEL_CONNECTINFO
                cchan = Channel.objects.get_channel(cchan[0])
                cchan.msg("[%s]: %s" % (cchan.key, message))
            except Exception:
                pass
        logger.log_infomsg(message)

    def update_session_counters(self, idle=False):
        """
        Hit this when the user enters a command in order to update idle timers
        and command counters. 
        """
        # Store the timestamp of the user's last command.
        self.cmd_last = time.time()
        if not idle:
            # Increment the user's command counter.
            self.cmd_total += 1
            # Player-visible idle time, not used in idle timeout calcs.
            self.cmd_last_visible = time.time()

    def execute_cmd(self, command_string):
        """
        Execute a command string on the server.
        """
        # handle the 'idle' command
        if str(command_string).strip() == IDLE_COMMAND:
            self.update_session_counters(idle=True)            
            return 

        # all other inputs, including empty inputs
        character = self.get_character()        
    

        if character:
            character.execute_cmd(command_string)
        else:
            if self.logged_in:
                # there is no character, but we are logged in. Use player instead.
                self.get_player().execute_cmd(command_string)                    
            else:            
                # we are not logged in. Use special unlogged-in call. 
                cmdhandler.cmdhandler(self, command_string, unloggedin=True)
        self.update_session_counters()            

    def data_out(self, msg, data=None):
        """
        Send Evennia -> Player
        """
        self.sessionhandler.data_out(self, msg, data)

    def __eq__(self, other):
        return self.address == other.address

    def __str__(self):
        """
        String representation of the user session class. We use
        this a lot in the server logs.
        """
        if self.logged_in:
            symbol = '#'
        else:
            symbol = '?'
        try:
            address = ":".join([str(part) for part in self.address])            
        except Exception:
            address = self.address            
        return "<%s> %s@%s" % (symbol, self.uname, address)

    def __unicode__(self):
        """
        Unicode representation
        """
        return u"%s" % str(self)


    # easy-access functions

    def login(self, player):
        "alias for at_login"
        self.session_login(player)
    def disconnect(self):
        "alias for session_disconnect"
        self.session_disconnect()
    def msg(self, string='', data=None):
        "alias for at_data_out"
        self.data_out(string, data=data)
