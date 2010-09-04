"""
This module contains classes related to Sessions. sessionhandler has the things
needed to manage them.
"""
import time
from datetime import datetime
from twisted.conch.telnet import StatefulTelnetProtocol
from django.conf import settings
from src.server import sessionhandler
from src.objects.models import ObjectDB 
from src.comms.models import Channel
from src.config.models import ConnectScreen
from src.commands import cmdhandler
from src.utils import ansi
from src.utils import reloads 
from src.utils import logger
from src.utils import utils

class SessionProtocol(StatefulTelnetProtocol):
    """
    This class represents a player's session. Each player
    gets a session assigned to them whenever
    they connect to the game server. All communication
    between game and player goes through here. 
    """

    def __str__(self):
        """
        String representation of the user session class. We use
        this a lot in the server logs and stuff.
        """
        if self.logged_in:
            symbol = '#'
        else:
            symbol = '?'
        return "<%s> %s@%s" % (symbol, self.name, self.address,)

    def connectionMade(self):
        """
        What to do when we get a connection.
        """
        # setup the parameters
        self.prep_session()
        # send info
        logger.log_infomsg('New connection: %s' % self)        
        # add this new session to handler
        sessionhandler.add_session(self)
        # show a connect screen 
        self.game_connect_screen()

    def getClientAddress(self):
        """
        Returns the client's address and port in a tuple. For example
        ('127.0.0.1', 41917)
        """
        return self.transport.client

    def prep_session(self):
        """
        This sets up the main parameters of
        the session. The game will poll these
        properties to check the status of the
        connection and to be able to contact
        the connected player. 
        """
        # main server properties 
        self.server = self.factory.server
        self.address = self.getClientAddress()

        # player setup 
        self.name = None
        self.uid = None
        self.logged_in = False

        # The time the user last issued a command.
        self.cmd_last = time.time()
        # Player-visible idle time, excluding the IDLE command.
        self.cmd_last_visible = time.time()
        # Total number of commands issued.
        self.cmd_total = 0
        # The time when the user connected.
        self.conn_time = time.time()
        #self.channels_subscribed = {}

    def disconnectClient(self):
        """
        Manually disconnect the client.
        """
        self.transport.loseConnection()

    def connectionLost(self, reason):
        """
        Execute this when a client abruplty loses their connection.
        """
        logger.log_infomsg('Disconnected: %s' % self)
        self.cemit_info('Disconnected: %s.' % self)
        self.handle_close()
        
    def lineReceived(self, raw_string):
        """
        Communication Player -> Evennia
        Any line return indicates a command for the purpose of the MUD.
        So we take the user input and pass it to the Player and their currently
        connected character.
        """
        try:
            raw_string = utils.to_unicode(raw_string)
        except Exception, e:
            self.sendLine(str(e))
            return 
        self.execute_cmd(raw_string)        

    def msg(self, message, markup=True):
        """
        Communication Evennia -> Player
        Sends a message to the session.

        markup - determines if formatting markup should be 
                 parsed or not. Currently this means ANSI
                 colors, but could also be html tags for 
                 web connections etc.        
        """
        try:
            message = utils.to_str(message)
        except Exception, e:
            self.sendLine(str(e))
            return 
        if markup: 
            message = ansi.parse_ansi(message)
        else:
            message = ansi.clean_ansi(message)
        self.sendLine(message)

    def get_character(self):
        """
        Returns the in-game character associated with a session.
        This returns the typeclass of the object.
        """
        if self.logged_in: 
            character = ObjectDB.objects.get_object_with_user(self.uid)
            if not character:
                string  = "No character match for session uid: %s" % self.uid
                logger.log_errmsg(string)                
            else:
                return character
        return None 

    def execute_cmd(self, raw_string):
        """
        Sends a command to this session's
        character for processing.

        'idle' is a special command that is
        interrupted already here. It doesn't do
        anything except silently updates the
        last-active timer to avoid getting kicked
        off for idleness.
        """
        # handle the 'idle' command 
        if str(raw_string).strip() == 'idle':
            self.update_counters(idle=True)            
            return 

        # all other inputs, including empty inputs
        character = self.get_character()
        if character:
            # normal operation.            
            character.execute_cmd(raw_string)
        else:
            # we are not logged in yet
            cmdhandler.cmdhandler(self, raw_string, unloggedin=True)
        # update our command counters and idle times. 
        self.update_counters()
      
    def update_counters(self, idle=False):
        """
        Hit this when the user enters a command in order to update idle timers
        and command counters. If silently is True, the public-facing idle time
        is not updated.
        """
        # Store the timestamp of the user's last command.
        self.cmd_last = time.time()
        if not idle:
            # Increment the user's command counter.
            self.cmd_total += 1
            # Player-visible idle time, not used in idle timeout calcs.
            self.cmd_last_visible = time.time()
            
    def handle_close(self):
        """
        Break the connection and do some accounting.
        """
        character = self.get_character()
        if character:
            #call hook functions 
            character.at_disconnect()            
            character.player.at_disconnect()
            uaccount = character.player.user
            uaccount.last_login = datetime.now()
            uaccount.save()            
        self.disconnectClient()
        self.logged_in = False
        sessionhandler.remove_session(self)        
        
    def game_connect_screen(self):
        """
        Show the banner screen. Grab from the 'connect_screen'
        config directive. If more than one connect screen is
        defined in the ConnectScreen attribute, it will be
        random which screen is used. 
        """
        screen = ConnectScreen.objects.get_random_connect_screen()
        string = ansi.parse_ansi(screen.text)
        self.msg(string)
    
    def login(self, player):
        """
        After the user has authenticated, this actually
        logs them in. At this point the session has
        a User account tied to it. User is an django
        object that handles stuff like permissions and
        access, it has no visible precense in the game.
        This User object is in turn tied to a game
        Object, which represents whatever existence
        the player has in the game world. This is the
        'character' referred to in this module. 
        """
        # set the session properties 

        user = player.user
        self.uid = user.id
        self.name = user.username
        self.logged_in = True
        self.conn_time = time.time()
        
        if not settings.ALLOW_MULTISESSION:
            # disconnect previous sessions.
            sessionhandler.disconnect_duplicate_session(self)

        # start (persistent) scripts on this object
        reloads.reload_scripts(obj=self.get_character(), init_mode=True)

        logger.log_infomsg("Logged in: %s" % self)
        self.cemit_info('Logged in: %s' % self)
        
        # Update their account's last login time.
        user.last_login = datetime.now()        
        user.save()
            
    def cemit_info(self, message):
        """
        Channel emits info to the appropriate info channel. By default, this
        is MUDConnections.
        """
        try:
            cchan = settings.CHANNEL_CONNECTINFO
            cchan = Channel.objects.get_channel(cchan[0])
            cchan.msg("[%s]: %s" % (cchan.key, message))
        except Exception:
            logger.log_infomsg(message)

            
