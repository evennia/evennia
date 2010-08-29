"""
Sessionhandler, stores and handles
a list of all player connections (sessions).
"""
import time
from django.contrib.auth.models import User
from src.config.models import ConfigValue
from src.utils import logger

# Our list of connected sessions.
SESSIONS = []

def add_session(session):
    """
    Adds a session to the session list.
    """
    SESSIONS.insert(0, session)
    change_session_count(1)
    logger.log_infomsg('Sessions active: %d' % (len(get_sessions(return_unlogged=True),)))
    
def get_sessions(return_unlogged=False):
    """
    Lists the connected session objects.
    """
    if return_unlogged:
        return SESSIONS
    else:
        return [sess for sess in SESSIONS if sess.logged_in]
    
def get_session_id_list(return_unlogged=False):
    """
    Lists the connected session object ids.
    """
    if return_unlogged:
        return SESSIONS
    else:
        return [sess.uid for sess in SESSIONS if sess.logged_in]

def disconnect_all_sessions():
    """
    Cleanly disconnect all of the connected sessions.
    """
    for sess in get_sessions():
        sess.handle_close()

def disconnect_duplicate_session(session):
    """
    Disconnects any existing session under the same object. This is used in
    connection recovery to help with record-keeping.
    """
    SESSIONS = get_sessions()
    session_pobj = session.get_character()
    for other_session in SESSIONS:
        other_pobject = other_session.get_character()
        if session_pobj == other_pobject and other_session != session:
            other_session.msg("Your account has been logged in from elsewhere, disconnecting.")
            other_session.disconnectClient()
            return True
    return False

def check_all_sessions():
    """
    Check all currently connected sessions and see if any are dead.
    """
    idle_timeout = int(ConfigValue.objects.conf('idle_timeout'))

    if len(SESSIONS) <= 0:
        return

    if idle_timeout <= 0:
        return
    
    for sess in get_sessions(return_unlogged=True):
        if (time.time() - sess.cmd_last) > idle_timeout:
            sess.msg("Idle timeout exceeded, disconnecting.")
            sess.handle_close()

def change_session_count(num):
    """
    Count number of connected users by use of a config value

    num can be a positive or negative value. If 0, the counter
    will be reset to 0. 
    """

    if num == 0:
        # reset
        ConfigValue.objects.conf('nr_sessions', 0)
    
    nr = ConfigValue.objects.conf('nr_sessions')
    if nr == None: 
        nr = 0
    else:
        nr = int(nr)
    nr += num
    ConfigValue.objects.conf('nr_sessions', str(nr))


def remove_session(session):
    """
    Removes a session from the session list.
    """
    try:
        SESSIONS.remove(session)
        change_session_count(-1)
        logger.log_infomsg('Sessions active: %d' % (len(get_sessions()),))
    except ValueError:        
        # the session was already removed.
        logger.log_errmsg("Unable to remove session: %s" % (session,))
        return 
       
def find_sessions_from_username(username):
    """
    Given a username, return any matching sessions.
    """
    try:
        uobj = User.objects.get(username=username)
        uid = uobj.id
        return [session for session in SESSIONS if session.uid == uid]
    except User.DoesNotExist:
        return None
            
def sessions_from_object(targ_object):
    """
    Returns a list of matching session objects, or None if there are no matches.
    
    targobject: (Object) The object to match.
    """
    return [session for session in SESSIONS
            if session.get_character() == targ_object]
        
def announce_all(message):
    """
    Announces something to all connected players.
    """
    for session in get_sessions():
        session.msg('%s' % message)
