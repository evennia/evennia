"""
This module handles sessions of users connecting
to the server. 

Since Evennia supports several different connection 
protocols, it is important to have a joint place 
to store session info. It also makes it easier 
to dispatch data. 

Whereas server.py handles all setup of the server
and database itself, this file handles all that
comes after initial startup.

All new sessions (of whatever protocol) are responsible for 
registering themselves with this module.

"""
from django.conf import settings
from django.contrib.auth.models import User
from src.server.models import ServerConfig

ALLOW_MULTISESSION = settings.ALLOW_MULTISESSION

#------------------------------------------------------------
# SessionHandler class
#------------------------------------------------------------

class SessionHandler(object):
    """
    This object holds the stack of sessions active in the game at
    any time. 

    A session register with the handler in two steps, first by
    registering itself with the connect() method. This indicates an
    non-authenticated session. Whenever the session is authenticated
    the session together with the related player is sent to the login()
    method. 

    """

    def __init__(self):
        """
        Init the handler. We track two types of sessions, those 
        who have just connected (unloggedin) and those who have 
        logged in (authenticated).
        """
        self.unloggedin = []
        self.loggedin = []

        # we keep a link to the server here, for the rest of the game to access.
        self.server = None 

    def add_unloggedin_session(self, session):
        """
        Call at first connect. This adds a not-yet authenticated session.
        """        
        self.unloggedin.insert(0, session)
        
    def add_loggedin_session(self, session):
        """
        Log in the previously unloggedin session and the player we by
        now should know is connected to it. After this point we
        assume the session to be logged in one way or another.
        """
        # prep the session with player/user info


        if not ALLOW_MULTISESSION:
            # disconnect previous sessions.
            self.disconnect_duplicate_sessions(session)
      
        # store/move the session to the right list
        try:
            self.unloggedin.remove(session)
        except ValueError:
            pass 
        self.loggedin.insert(0, session)
        self.session_count(1)

    def remove_session(self, session):
        """
        Remove session from the handler
        """
        removed = False
        try:
            self.unloggedin.remove(session)
        except Exception:
            try:
                self.loggedin.remove(session)
            except Exception:
                return
        self.session_count(-1)

    def get_sessions(self, include_unloggedin=False):
        """
        Returns the connected session objects.
        """
        if include_unloggedin:
            return self.loggedin + self.unloggedin 
        else:
            return self.loggedin        

    def disconnect_all_sessions(self, reason="You have been disconnected."):
        """
        Cleanly disconnect all of the connected sessions.
        """
        sessions = self.get_sessions(include_unloggedin=True)        
        for session in sessions:
            session.at_data_out(reason)
            session.session_disconnect()
        self.session_count(0)

    def disconnect_duplicate_sessions(self, curr_session):
        """
        Disconnects any existing sessions with the same game object. 
        """
        reason = "Your account has been logged in from elsewhere. Disconnecting." 
        curr_char = curr_session.get_character()
        doublet_sessions = [sess for sess in self.get_sessions() 
                            if sess.get_character() == curr_char and sess != curr_session]
        logged_out = 0
        for session in doublet_sessions:
            session.msg(reason)
            self.remove_session(session)
            logged_out += 1                
        self.session_count(-logged_out)
        return logged_out

    def validate_sessions(self):
        """
        Check all currently connected sessions (logged in and not) 
        and see if any are dead.
        """
        for session in self.get_sessions(include_unloggedin=True):
            session.session_validate()

    def session_count(self, num=None):
        """
        Count up/down the number of connected, authenticated users. 
        If num is None, the current number of sessions is returned.

        num can be a positive or negative value to be added to the current count. 
        If 0, the counter will be reset to 0. 
        """
        if num == None:
            # show the current value. This also syncs it.                         
            return int(ServerConfig.objects.conf('nr_sessions', default=0))            
        elif num == 0:
            # reset value to 0
            ServerConfig.objects.conf('nr_sessions', 0)
        else:
            # add/remove session count from value
            add = int(ServerConfig.objects.conf('nr_sessions', default=0))
            num = max(0, num + add)
            ServerConfig.objects.conf('nr_sessions', str(num))

    def player_count(self):
        """
        Get the number of connected players (not sessions since a player
        may have more than one session connected if ALLOW_MULTISESSION is True)
        Only logged-in players are counted here.
        """
        return len(set(sess.uid for sess in self.get_sessions()))
        
    def sessions_from_player(self, player):
        """
        Given a player, return any matching sessions.
        """
        username = player.user.username
        try:
            uobj = User.objects.get(username=username)
        except User.DoesNotExist:
            return None
        uid = uobj.id
        return [session for session in self.loggedin if session.uid == uid]

    def sessions_from_character(self, character):
        """
        Given a game character, return any matching sessions.
        """
        player = character.player
        if player:
            return self.sessions_from_player(player)
        return None 

    def session_from_suid(self, suid):
        """
        Given a session id, retrieve the session (this is primarily
        intended to be called by web clients)
        """
        return [sess for sess in self.get_sessions(include_unloggedin=True) if sess.suid and sess.suid == suid]

    def announce_all(self, message):
        """
        Send message to all connected sessions
        """
        for sess in self.get_sessions(include_unloggedin=True):
            sess.msg(message)

SESSIONS = SessionHandler()


