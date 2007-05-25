import time
import gameconf

"""
Session manager, handles connected players.
"""
# Our list of connected sessions.
session_list = []

def add_session(session):
   """
   Adds a session to the session list.
   """
   session_list.insert(0, session)
   print 'Sessions active:', len(get_session_list())
   
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

def check_all_sessions():
   """
   Check all currently connected sessions and see if any are dead.
   """
   idle_timeout = int(gameconf.get_configvalue('idle_timeout'))

   if len(session_list) <= 0:
      return

   if idle_timeout <= 0:
      return
   
   for sess in get_session_list():
      if (time.time() - sess.cmd_last) > idle_timeout:
         sess.msg("Idle timeout exceeded, disconnecting.")
         sess.handle_close()

def remove_session(session):
   """
   Removes a session from the session list.
   """
   session_list.remove(session)
   
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
