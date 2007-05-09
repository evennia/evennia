import time
from session import PlayerSession
import gameconf

"""
Session manager, handles connected players.
"""
# Our list of connected sessions.
session_list = []

def new_session(server, conn, addr):
   """
   Create and return a new session.
   """
   session = PlayerSession(server, conn, addr)
   session_list.insert(0, session)
   return session
   
def get_session_list():
   """
   Lists the connected session objects.
   """
   return session_list

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
      ## This doesn't seem to provide an accurate indication of timed out
      ## sessions.
      #if not sess.writable() or not sess.readable():
      #   print 'Problematic Session:'
      #   print 'Readable ', sess.readable()
      #   print 'Writable ', sess.writable()
         
   
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
