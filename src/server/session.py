"""
This defines a generic session class.

All protocols should implement this class and its hook methods.
"""

import time 
from datetime import datetime
#from django.contrib.auth.models import User
from django.conf import settings
#from src.objects.models import ObjectDB
from src.comms.models import Channel
from src.utils import logger, reloads
from src.commands import cmdhandler
from src.server import sessionhandler

IDLE_TIMEOUT = settings.IDLE_TIMEOUT 
IDLE_COMMAND = settings.IDLE_COMMAND 



class IOdata(object):
    """
    A simple storage object that allows for storing 
    new attributes on it at creation.
    """
    def __init__(self, **kwargs):
        "Give keyword arguments to store as new arguments on the object."
        self.__dict__.update(**kwargs)
        

#------------------------------------------------------------
# SessionBase class
#------------------------------------------------------------

class SessionBase(object):
    """
    This class represents a player's session and is a template for 
    individual protocols to communicate with Evennia. 

    Each player gets a session assigned to them whenever they connect
    to the game server. All communication between game and player goes
    through their session.

    """

    # use this to uniquely identify the protocol name, e.g. "telnet" or "comet"
    protocol_key = "BaseProtocol"

    def session_connect(self, address, suid=None):
        """
        The setup of the session. An address (usually an IP address) on any form is required.

        This should be called by the protocol at connection time.

        suid = this is a session id. Needed by some transport protocols.
        """
        self.address = address

        # user setup 
        self.name = None
        self.uid = None
        self.suid = suid
        self.logged_in = False
        self.encoding = "utf-8"

        current_time = time.time()

        # The time the user last issued a command.
        self.cmd_last = current_time
        # Player-visible idle time, excluding the IDLE command.
        self.cmd_last_visible = current_time
        # The time when the user connected.
        self.conn_time = current_time
        # Total number of commands issued.
        self.cmd_total = 0
        #self.channels_subscribed = {}
        sessionhandler.SESSIONS.add_unloggedin_session(self)
        # call hook method
        self.at_connect()

    def session_login(self, player):
        """
        Private startup mechanisms that need to run at login

        player - the connected player
        """
        self.player = player
        self.user = player.user
        self.uid = self.user.id
        self.name = self.user.username
        self.logged_in = True
        self.conn_time = time.time()
        
        # Update account's last login time.
        self.user.last_login = datetime.now()        
        self.user.save()        
        self.log('Logged in: %s' % self)

        # start (persistent) scripts on this object
        reloads.reload_scripts(obj=self.player.character, init_mode=True)
        
        #add session to connected list
        sessionhandler.SESSIONS.add_loggedin_session(self)

        #call hook
        self.at_login()       

    def session_disconnect(self, reason=None):
        """
        Clean up the session, removing it from the game and doing some
        accounting. This method is used also for non-loggedin
        accounts.

        Note that this methods does not close the connection - this is protocol-dependent 
        and have to be done right after this function!
        """
        if self.logged_in:            
            character = self.get_character()
            if character:
                character.player.at_disconnect(reason)
                uaccount = character.player.user
                uaccount.last_login = datetime.now()
                uaccount.save()            
                self.logged_in = False                        
        sessionhandler.SESSIONS.remove_session(self)                

    def session_validate(self):
        """
        Validate the session to make sure they have not been idle for too long
        """        
        if IDLE_TIMEOUT > 0 and (time.time() - self.cmd_last) > IDLE_TIMEOUT:            
            self.msg("Idle timeout exceeded, disconnecting.")
            self.session_disconnect()

    def get_player(self):
        """
        Get the player associated with this session
        """
        if self.logged_in:
            return self.player
        else:
            return None 

        # if self.logged_in:
        #     character = ObjectDB.objects.get_object_with_user(self.uid)
        #     if not character:
        #         string  = "No player match for session uid: %s" % self.uid
        #         logger.log_errmsg(string)
        #         return None
        #     return character.player
        # return None
                       
    def get_character(self):
        """
        Returns the in-game character associated with a session.
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
        Execute a command string.
        """

        # handle the 'idle' command
        if str(command_string).strip() == IDLE_COMMAND:
            self.update_session_counters(idle=True)            
            return 

        # all other inputs, including empty inputs
        character = self.get_character()

        if character:
            #print "loggedin _execute_cmd: '%s' __ %s" % (command_string, character)
            # normal operation.            
            character.execute_cmd(command_string)
        else:
            #print "unloggedin _execute_cmd: '%s' __ %s" % (command_string, character)
            # we are not logged in yet; call cmdhandler directly
            cmdhandler.cmdhandler(self, command_string, unloggedin=True)

    def get_data_obj(self, **kwargs):
        """
        Create a data object, storing keyword arguments on itself as arguments.
        """
        return IOdata(**kwargs)        

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
        return "<%s> %s@%s" % (symbol, self.name, self.address,)

    def __unicode__(self):
        """
        Unicode representation
        """
        return u"%s" % str(self)



#------------------------------------------------------------
# Session class - inherit from this
#------------------------------------------------------------ 
   
class Session(SessionBase):
    """
    The main class to inherit from. Overload the methods here.
    """

    # exchange this for a unique name you can use to identify the
    # protocol type this session uses
    protocol_key = "TemplateProtocol"
            
    #
    # Hook methods 
    # 

    def at_connect(self):
        """
        This method is called by the connection mechanic after
        connection has been made. The session is added to the
        sessionhandler and basic accounting has been made at this
        point.

        This is the place to put e.g. welcome screens specific to the
        protocol.
        """        
        pass

    def at_login(self, player):
        """
        This method is called by the login mechanic whenever the user
        has finished authenticating. The user has been moved to the 
        right sessionhandler list and basic book keeping has been 
        done at this point (so logged_in=True). 
        """
        pass

    def at_disconnect(self, reason=None):
        """
        This method is called just before cleaning up the session 
        (so still logged_in=True at this point).        
        """
        pass

    def at_data_in(self, string="", data=None):
        """
        Player -> Evennia
        """
        pass

    def at_data_out(self, string="", data=None):
        """
        Evennia -> Player 

        string - an string of any form to send to the player
        data - a data structure of any form 

        """
        pass 

    # easy-access functions
    def login(self, player):
        "alias for at_login"
        self.at_login(player)
    def logout(self):
        "alias for at_logout"
        self.at_disconnect()
    def msg(self, string='', data=None):
        "alias for at_data_out"
        self.at_data_out(string, data)
