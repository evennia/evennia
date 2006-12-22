from session import PlayerSession

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
   results = [prospect for prospect in session_list if prospect.get_pobject().id == targobject.id]
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
