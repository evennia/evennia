"""
Session manager, handles connected players.
"""
import time

from apps.config.models import ConfigValue
from src import logger
from src.util import functions_general

# Our list of connected sessions.
session_list = []

def add_session(session):
    """
    Adds a session to the session list.
    """
    session_list.insert(0, session)
    logger.log_infomsg('Sessions active: %d' % (len(get_session_list(return_unlogged=True),)))
    
def get_session_list(return_unlogged=False):
    """
    Lists the connected session objects.
    """
    if return_unlogged:
        return session_list
    else:
        return [sess for sess in session_list if sess.is_loggedin()]

def disconnect_all_sessions():
    """
    Cleanly disconnect all of the connected sessions.
    """
    for sess in get_session_list():
        sess.handle_close()

def disconnect_duplicate_session(session):
    """
    Disconnects any existing session under the same object. This is used in
    connection recovery to help with record-keeping.
    """
    sess_list = get_session_list()
    new_pobj = session.get_pobject()
    for sess in sess_list:
        if new_pobj == sess.get_pobject() and sess != session:
            sess.msg("Your account has been logged in from elsewhere, disconnecting.")
            sess.disconnectClient()
            return True
    return False


def check_all_sessions():
    """
    Check all currently connected sessions and see if any are dead.
    """
    idle_timeout = int(ConfigValue.objects.get_configvalue('idle_timeout'))

    if len(session_list) <= 0:
        return

    if idle_timeout <= 0:
        return
    
    for sess in get_session_list(return_unlogged=True):
        if (time.time() - sess.cmd_last) > idle_timeout:
            sess.msg("Idle timeout exceeded, disconnecting.")
            sess.handle_close()

def remove_session(session):
    """
    Removes a session from the session list.
    """
    try:
        session_list.remove(session)
        logger.log_infomsg('Sessions active: %d' % (len(get_session_list()),))
    except ValueError:
        #logger.log_errmsg("Unable to remove session: %s" % (session,))
        pass
        
    
def session_from_object(targobject):
    """
    Return the session object given a object (if there is one open).
    
    session_list: (list) The server's session_list attribute.
    targobject: (Object) The object to match.
    """
    results = [prospect for prospect in session_list if prospect.get_pobject() == targobject]
    if results:
        return results[0]
    else:
        return False

def session_from_dbref(dbstring):
    """
    Return the session object given a dbref (if there is one open).
    
    dbstring: (int) The dbref number to match against.
    """
    if is_dbref(dbstring):
        results = [prospect for prospect in session_list if prospect.get_pobject().dbref_match(dbstring)]
        if results:
            return results[0]
    else:
        return False
        
def announce_all(message, with_ann_prefix=True):
    """
    Announces something to all connected players.
    """
    if with_ann_prefix:
        prefix = 'Announcement:'
    else:
        prefix = ''

    for session in get_session_list():
        session.msg('%s %s' % (prefix, message))
